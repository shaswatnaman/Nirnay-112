"""
Decision Engine: Conversation Manager

This module implements a hybrid system where:
- OpenAI is used ONLY for perception (signal processing)
- All decision-making is deterministic and local (decision engine)

Naming Philosophy:
- We use "decision_engine" instead of "ai_agent" to emphasize that this is
  a deterministic decision-making system, not an autonomous AI agent.
- Decision engine clearly describes our role: orchestrating decisions based on
  explicit rules and formulas, not autonomous agent behavior.

Architecture:
1. Signal processing extracts signals (intent, entities, emotion, clarity)
2. Context memory merges signals over time
3. Decision engine calculates urgency using deterministic formula
4. Decision engine checks escalation using deterministic rules
5. Conversation control is local (not OpenAI)
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import uuid
from pathlib import Path

from app.nlp.signal_extraction import extract_signals
from app.logic.context_memory import ContextMemory, get_or_create_context
from app.logic.urgency_scoring import calculate_urgency_score
from app.logic.escalation import check_escalation_required, detect_explicit_human_request
from app.ml.stress_estimator import estimate_stress
from app.logic.explainability import explain_decision

logger = logging.getLogger(__name__)

# Lazy-loaded intent classifier (loaded on first use)
_intent_classifier = None
_intent_classifier_path = None


def _get_intent_classifier():
    """
    Get or load the intent classifier (lazy loading).
    
    Naming Philosophy:
    - We use "external_model_api" conceptually instead of "ml_model" to emphasize
      that this classifier is a local model, but the concept applies: we're using
      a model (local or external) for classification, not making decisions directly.
    - The intent classifier is a local ML model, but we treat it as part of our
      signal processing pipeline, not as a decision-making component.
    
    Returns:
        IntentClassifier: Loaded intent classifier instance
    
    Raises:
        RuntimeError: If model file not found or loading fails
    """
    global _intent_classifier, _intent_classifier_path
    
    if _intent_classifier is not None:
        return _intent_classifier
    
    try:
        from app.ml.intent_classifier import load_classifier
        
        # Default model path
        if _intent_classifier_path is None:
            _intent_classifier_path = Path(__file__).parent.parent / "ml" / "models" / "intent_classifier.pkl"
        
        logger.info(f"Loading intent classifier from {_intent_classifier_path}")
        _intent_classifier = load_classifier(_intent_classifier_path)
        logger.info("Intent classifier loaded successfully")
        
        return _intent_classifier
        
    except FileNotFoundError as e:
        logger.warning(f"Intent classifier model not found: {e}. Using fallback intent='unclear'")
        return None
    except Exception as e:
        logger.error(f"Failed to load intent classifier: {e}", exc_info=True)
        return None


class HybridMLConversationManager:
    """
    Decision Engine: Conversation Manager for emergency call triage.
    
    Naming Philosophy:
    - We use "decision_engine" conceptually instead of "ai_agent" to emphasize
      that this is a deterministic decision-making system, not an autonomous AI agent.
    - Decision engine clearly describes our role: orchestrating decisions based on
      explicit rules and formulas, not autonomous agent behavior.
    - This class coordinates signal processing (perception) with decision engine (decisions).
    
    Uses OpenAI ONLY for perception (signal processing).
    All decisions are made deterministically by the decision engine in our code.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize conversation manager for a session.
        
        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # Context memory (persistent state)
        self.context: ContextMemory = get_or_create_context(session_id)
        
        # Conversation state
        self.conversation_history: List[Dict[str, str]] = []
        self.question_count: int = 0
        self.last_question: Optional[str] = None
        self.user_input_buffer: str = ""  # Accumulated user input for context
        
        # Escalation state
        self.escalation_required: bool = False
        self.escalation_reason: Optional[str] = None
        self.escalation_priority: Optional[str] = None
        self.escalation_message_sent: bool = False  # Track if escalation message was already sent
        
        # Intent tracking (for ML-based intent classification)
        self.last_intent: Optional[str] = None
        self.last_intent_confidence: float = 0.0
        
        logger.info(f"HybridMLConversationManager initialized for session: {session_id}")
    
    def _get_local_ml_intent(self, transcript: str) -> Optional[Dict[str, any]]:
        """
        Get intent prediction from local ML classifier.
        
        Args:
            transcript: Text to classify
        
        Returns:
            dict: Intent prediction with keys:
                - "intent": str - Predicted intent class
                - "confidence": float - Confidence score (0.0 to 1.0)
                - "probabilities": dict - Probability scores for all classes
            None if classifier not available
        """
        try:
            classifier = _get_intent_classifier()
            if classifier is None:
                return None
            
            result = classifier.predict(transcript)
            logger.debug(f"Local ML intent prediction: {result['intent']} (confidence: {result['confidence']:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get local ML intent: {e}", exc_info=True)
            return None
    
    def process_transcript(self, transcript: str) -> Dict[str, any]:
        """
        Process new transcript through decision engine pipeline.
        
        Naming Philosophy:
        - We use "decision_engine" instead of "ai_agent" to emphasize that
          this is a deterministic decision-making system, not an autonomous AI agent.
        - Decision engine clearly describes our role: making decisions based on
          explicit rules and formulas, not autonomous agent behavior.
        
        Pipeline:
        1. Signal processing: Extract signals using OpenAI (perception only)
        2. Context memory: Merge signals over time
        3. Decision engine: Calculate urgency score (deterministic formula)
        4. Decision engine: Check escalation (deterministic rules)
        5. Decision engine: Generate next question (local logic)
        
        Args:
            transcript: New transcribed text from user
        
        Returns:
            dict: Processing result with:
                - "signals": extracted signals
                - "context": updated context
                - "urgency": urgency score and level
                - "escalation": escalation decision
                - "next_question": next AI question
        """
        if not transcript or not transcript.strip():
            return self._get_current_state()
        
        # Step 1: Extract signals using OpenAI (perception only)
        # OpenAI extracts signals but makes NO decisions
        previous_context = self.context.to_dict() if self.context else None
        signals = extract_signals(transcript, previous_context)
        
        # Step 1.5: Get intent from local ML classifier (replaces OpenAI intent)
        # Use local ML intent classifier instead of OpenAI-based intent
        # Naming: We use "external_model_api" conceptually - this is a local model,
        # but the concept is that we're using a model (local or external) for classification
        ml_intent_result = self._get_local_ml_intent(transcript)
        
        # Store intent and confidence
        if ml_intent_result:
            ml_intent = ml_intent_result["intent"]
            ml_confidence = ml_intent_result["confidence"]
            
            # Don't overwrite existing intent if new confidence is lower
            # Check against last stored intent (from previous transcripts)
            if self.last_intent and self.last_intent != "unclear" and self.last_intent != "uncertain":
                if self.last_intent_confidence > ml_confidence:
                    # Keep existing intent if it has higher confidence
                    ml_intent = self.last_intent
                    ml_confidence = self.last_intent_confidence
                    logger.debug(f"Keeping existing intent '{self.last_intent}' (confidence: {self.last_intent_confidence:.3f}) "
                               f"over new ML intent '{ml_intent_result['intent']}' (confidence: {ml_intent_result['confidence']:.3f})")
            
            # If confidence < 0.6, mark intent as "uncertain" (after checking against existing intent)
            if ml_confidence < 0.6:
                ml_intent = "uncertain"
            
            # Use new ML intent (or kept existing if confidence was higher)
            signals["intent"] = ml_intent
            signals["intent_confidence"] = ml_confidence
            signals["intent_source"] = "local_ml"
            
            # Update stored intent for next comparison (only if not "uncertain")
            if ml_intent != "uncertain":
                self.last_intent = ml_intent
                self.last_intent_confidence = ml_confidence
            
            logger.info(f"Intent from local ML: '{ml_intent}' (confidence: {ml_confidence:.3f})")
        else:
            # Fallback: keep OpenAI intent or use "unclear"
            if "intent" not in signals:
                signals["intent"] = "unclear"
            signals["intent_confidence"] = 0.0
            signals["intent_source"] = "fallback"
            logger.warning("Local ML intent classifier not available, using fallback")
        
        # Add transcript to signals for context memory (needed for repetition tracking)
        if not signals:
            signals = {}
        signals["transcript"] = transcript
        
        # Step 2: Update context memory (merge signals over time)
        self.context.update_from_signals(signals)
        
        # Update user input buffer for context
        self.user_input_buffer += (" " + transcript).strip()
        
        # Step 3: Decision engine - Calculate urgency score (deterministic formula)
        # Naming: We use "decision_engine" instead of "ai_agent" - this is deterministic
        # decision-making, not autonomous agent behavior
        time_elapsed = (datetime.now() - self.created_at).total_seconds()
        
        # Calculate deterministic stress score (replaces LLM emotion labels)
        # This is safer and more reliable than LLM emotion classification
        stress_result = estimate_stress(
            transcript=transcript,
            repetition_count=self.context.repetition_count,
            time_elapsed_seconds=time_elapsed,
            previous_transcripts=self.context.previous_transcripts[-5:] if self.context.previous_transcripts else None
        )
        stress_score = stress_result.get("stress_score", 0.0)
        
        # Add transcript to context for urgency signal detection
        context_dict = self.context.to_dict()
        context_dict["transcript"] = transcript
        context_dict["user_input_buffer"] = self.user_input_buffer
        
        urgency_result = calculate_urgency_score(
            intent=signals.get("intent", "unclear"),
            stress_score=stress_score,  # Use deterministic stress_score instead of LLM emotion
            repetition_count=self.context.repetition_count,
            clarity_avg=self.context.clarity_avg,
            time_elapsed_seconds=time_elapsed,
            context=context_dict
        )
        
        # Update urgency in context memory (so it's available for frontend)
        self.context.urgency_score = urgency_result["urgency_score"]
        self.context.urgency_level = urgency_result["urgency_level"]
        
        # Step 4: Decision engine - Check escalation (deterministic rules)
        # Naming: We use "decision_engine" instead of "ai_agent" - this is deterministic
        # decision-making, not autonomous agent behavior
        # Only check escalation if we haven't already sent the escalation message (to prevent re-escalation)
        if not self.escalation_message_sent:
            explicit_request = detect_explicit_human_request(transcript)
            escalation_result = check_escalation_required(
                urgency_score=urgency_result["urgency_score"],
                urgency_level=urgency_result["urgency_level"],
                clarity_avg=self.context.clarity_avg,
                emotion_history=self.context.emotion_history[-5:],  # Last 5 emotions
                missing_fields=self.context.get_missing_fields(),
                question_count=self.question_count,
                explicit_human_request=explicit_request,
                immediate_danger=self.context.immediate_danger  # Layer 2 field: triggers escalation
            )
            
            # Update escalation state (only if not already sent escalation message)
            self.escalation_required = escalation_result["human_required"]
            self.escalation_reason = escalation_result.get("reason")
            self.escalation_priority = escalation_result.get("priority")
            
            # Log escalation event if escalation was triggered
            if escalation_result["human_required"]:
                try:
                    from app.logic.event_log import log_escalation_triggered
                    log_escalation_triggered(
                        session_id=self.session_id,
                        reason=escalation_result.get("reason", "unknown"),
                        priority=escalation_result.get("priority", "medium"),
                        urgency_score=urgency_result["urgency_score"]
                    )
                except ImportError:
                    pass  # Event log not available, continue silently
        else:
            # Already sent escalation message - use previous escalation result but don't re-escalate
            escalation_result = {
                "human_required": True,
                "reason": self.escalation_reason,
                "priority": self.escalation_priority
            }
            # Keep escalation_required = True for incident summary, but don't check again
            self.escalation_required = True
        
        # Step 4.5: Generate decision explanation (deterministic, no ML/OpenAI)
        # This explains WHY decisions were made without changing the decision logic
        decision_explanation = explain_decision(
            context=self.context,
            urgency_score=urgency_result["urgency_score"],
            escalation_decision=escalation_result
        )
        
        # Step 5: Generate next question (local logic, not OpenAI)
        next_question = self._generate_next_question()
        
        # CRITICAL: Always generate a question to maintain conversational flow
        # If question generation returns empty, use a default follow-up question
        if not next_question or not next_question.strip():
            logger.warning(f"Session {self.session_id}: Question generation returned empty, using default question")
            next_question = "कृपया बताएं कि क्या हुआ है?"
            self.last_question = next_question
        
        # Update conversation history
        self.conversation_history.append({
            "speaker": "user",
            "text": transcript,
            "timestamp": datetime.now().isoformat()
        })
        if next_question:
            self.conversation_history.append({
                "speaker": "ai",
                "text": next_question,
                "timestamp": datetime.now().isoformat()
            })
        
        self.last_updated = datetime.now()
        
        result = {
            "signals": signals,
            "context": self.context.to_dict(),
            "urgency": urgency_result,
            "escalation": escalation_result,
            "explanation": decision_explanation,  # Decision explainability
            "next_question": next_question
        }
        return result
    
    def _generate_next_question(self) -> str:
        """
        Generate next AI question using local logic.
        
        This is deterministic - OpenAI is NOT used for question generation.
        
        Returns:
            str: Next question in Hindi
        """
        # If escalation required, acknowledge ONCE and then continue conversation
        # Don't repeat escalation message - continue asking questions
        if self.escalation_message_sent:
            # Already sent escalation message, continue with questions (don't repeat)
            # Continue to normal question generation below
            pass
        elif self.escalation_required:
            # First time escalation - send message once, then continue
            escalation_msg = (
                "मैं समझ गया। आपकी मदद के लिए एक व्यक्ति जल्द ही आपसे बात करेगा। "
                "इस बीच, कृपया मुझे कुछ जानकारी दें।"
            )
            self.last_question = escalation_msg
            # Mark that we've sent escalation message (prevents re-escalation)
            self.escalation_message_sent = True
            # Keep escalation_required = True for incident summary, but don't check again
            return escalation_msg
        
        # Increment question count
        self.question_count += 1
        
        # First question (greeting) - only if no previous question
        if self.question_count == 1 and not self.last_question:
            greeting = (
                "नमस्ते, मैं आपकी मदद के लिए यहाँ हूँ। "
                "कृपया बताएं कि क्या हुआ है?"
            )
            self.last_question = greeting
            return greeting
        
        # Get missing fields
        missing_fields = self.context.get_missing_fields()
        
        # Don't repeat the same question - check if last question was already asked
        # and no new information was provided
        if self.last_question and self.last_question not in [
            "नमस्ते, मैं आपकी मदद के लिए यहाँ हूँ। कृपया बताएं कि क्या हुआ है?",
            "मैं समझ गया। आपकी मदद के लिए एक व्यक्ति जल्द ही आपसे बात करेगा। इस बीच, कृपया मुझे कुछ जानकारी दें।"
        ]:
            # Check if we should ask a different question
            pass
        
        # Priority-based question generation
        # Priority 1: Location (critical for emergency response)
        if "location" in missing_fields:
            location_questions = [
                "कृपया बताएं कि यह घटना कहाँ हुई है?",
                "आप कहाँ हैं? कृपया स्थान बताएं।",
                "मुझे जगह बताएं - कौन सी जगह, कौन सा शहर?"
            ]
            # Rotate questions to avoid repetition
            question_index = (self.question_count - 2) % len(location_questions)
            question = location_questions[question_index]
            # Don't repeat the same question
            if question == self.last_question:
                question_index = (question_index + 1) % len(location_questions)
                question = location_questions[question_index]
            self.last_question = question
            return question
        
        # Priority 2: Incident Type (critical for routing)
        if "incident_type" in missing_fields:
            incident_questions = [
                "कृपया बताएं कि क्या हुआ है?",
                "किस तरह की समस्या है?",
                "आप किस बारे में बता रहे हैं - दुर्घटना, अपराध, या चिकित्सा समस्या?"
            ]
            question_index = (self.question_count - 2) % len(incident_questions)
            question = incident_questions[question_index]
            if question == self.last_question:
                question_index = (question_index + 1) % len(incident_questions)
                question = incident_questions[question_index]
            self.last_question = question
            return question
        
        # Priority 3: Layer 2 - People Affected (operational, strongly recommended)
        # Only ask if incident type suggests multiple people might be affected
        if self.context.people_affected is None and self.context.incident_type in ["road_accident", "fire", "natural_disaster"]:
            people_questions = [
                "कितने लोग प्रभावित हैं?",
                "कितने लोगों को चोट लगी है?",
                "कितने लोग जख्मी हैं?"
            ]
            question_index = (self.question_count - 2) % len(people_questions)
            question = people_questions[question_index]
            if question == self.last_question:
                question_index = (question_index + 1) % len(people_questions)
                question = people_questions[question_index]
            self.last_question = question
            return question
        
        # Priority 4: Layer 2 - Name (optional but valuable, never force full name)
        missing_operational = self.context.get_missing_operational_fields()
        if "name" in missing_operational and self.question_count > 2:
            name_questions = [
                "कृपया अपना नाम बताएं।",
                "आपका नाम क्या है?",
                "मैं आपको कैसे संबोधित करूं?"
            ]
            question_index = (self.question_count - 3) % len(name_questions)
            question = name_questions[question_index]
            if question == self.last_question:
                question_index = (question_index + 1) % len(name_questions)
                question = name_questions[question_index]
            self.last_question = question
            return question
        
        # After Layer 1 (critical) fields are collected, continue asking Layer 2 (operational) fields
        # Always maintain conversational flow - never return empty string
        missing_operational = self.context.get_missing_operational_fields()
        
        # If we have Layer 1 fields but still missing Layer 2 fields, continue asking
        if not self.context.get_missing_fields() and missing_operational:
            # Layer 1 complete, but Layer 2 fields missing - continue asking
            if "name" in missing_operational and self.question_count > 2:
                name_questions = [
                    "कृपया अपना नाम बताएं।",
                    "आपका नाम क्या है?",
                    "मैं आपको कैसे संबोधित करूं?"
                ]
                question_index = (self.question_count - 3) % len(name_questions)
                question = name_questions[question_index]
                if question == self.last_question:
                    question_index = (question_index + 1) % len(name_questions)
                    question = name_questions[question_index]
                self.last_question = question
                return question
        
        # If all critical fields collected, ask follow-up questions to gather more details
        # Maintain conversational flow - always ask something
        if not self.context.get_missing_fields():
            # All critical fields collected - ask for more details or confirmation
            follow_up_questions = [
                "क्या आप कुछ और बताना चाहेंगे?",
                "क्या कोई और जानकारी है जो आप देना चाहेंगे?",
                "कृपया बताएं अगर कुछ और जानकारी है।"
            ]
            # Rotate questions to maintain conversation
            question_index = (self.question_count - 2) % len(follow_up_questions)
            question = follow_up_questions[question_index]
            # Don't repeat the exact same question immediately
            if question == self.last_question and self.question_count > 3:
                question_index = (question_index + 1) % len(follow_up_questions)
                question = follow_up_questions[question_index]
            self.last_question = question
            return question
        
        # Fallback: If we somehow reach here, ask a generic question to maintain flow
        # NEVER return empty string - always maintain conversation
        generic_questions = [
            "कृपया बताएं कि क्या हुआ है?",
            "मुझे और जानकारी दें।",
            "क्या आप कुछ और बता सकते हैं?"
        ]
        question_index = (self.question_count - 1) % len(generic_questions)
        question = generic_questions[question_index]
        if question == self.last_question:
            question_index = (question_index + 1) % len(generic_questions)
            question = generic_questions[question_index]
        self.last_question = question
        return question
    
    def _get_current_state(self) -> Dict[str, any]:
        """Get current conversation state."""
        time_elapsed = (datetime.now() - self.created_at).total_seconds()
        
        # Calculate stress score (use empty transcript for default state)
        stress_result = estimate_stress(
            transcript="",
            repetition_count=self.context.repetition_count,
            time_elapsed_seconds=time_elapsed,
            previous_transcripts=self.context.previous_transcripts[-5:] if self.context.previous_transcripts else None
        )
        stress_score = stress_result.get("stress_score", 0.0)
        
        urgency_result = calculate_urgency_score(
            intent="unclear",
            stress_score=stress_score,  # Use deterministic stress_score instead of LLM emotion
            repetition_count=self.context.repetition_count,
            clarity_avg=self.context.clarity_avg,
            time_elapsed_seconds=time_elapsed,
            context=self.context.to_dict()
        )
        
        return {
            "signals": None,
            "context": self.context.to_dict(),
            "urgency": urgency_result,
            "escalation": {
                "human_required": self.escalation_required,
                "reason": self.escalation_reason,
                "priority": self.escalation_priority
            },
            "next_question": None
        }
    
    def get_incident_summary(self) -> Dict[str, any]:
        """
        Get structured incident summary.
        
        Returns:
            dict: Incident summary with all collected information
        """
        # Use urgency from context memory (already calculated and stored)
        # Don't recalculate with hardcoded values - use the actual stored urgency
        urgency_level = self.context.urgency_level
        urgency_score = self.context.urgency_score
        
        # If urgency not yet calculated OR if we have an incident_type but urgency is still medium/unclear,
        # recalculate using actual context values
        if urgency_score == 0.0 or (urgency_level == "medium" and self.context.incident_type and self.context.incident_type != "unknown"):
            # Recalculate using actual context values (not hardcoded)
            time_elapsed = (datetime.now() - self.created_at).total_seconds()
            context_dict = self.context.to_dict()
            context_dict["transcript"] = self.user_input_buffer
            context_dict["user_input_buffer"] = self.user_input_buffer
            
            # Get actual intent from last signals or context
            # If we have an incident type, map it to intent
            intent = "unclear"
            if self.context.incident_type:
                incident_to_intent = {
                    "medical_emergency": "medical_emergency",
                    "fire": "fire",
                    "road_accident": "road_accident",
                    "crime": "crime",
                    "domestic_emergency": "domestic_emergency",
                    "natural_disaster": "natural_disaster",
                    "industrial_accident": "industrial_accident",
                    "public_transport": "public_transport"
                }
                intent = incident_to_intent.get(self.context.incident_type, "unclear")
            
            # Calculate deterministic stress score (replaces LLM emotion labels)
            stress_result = estimate_stress(
                transcript=self.user_input_buffer,
                repetition_count=self.context.repetition_count,
                time_elapsed_seconds=time_elapsed,
                previous_transcripts=self.context.previous_transcripts[-5:] if self.context.previous_transcripts else None
            )
            stress_score = stress_result.get("stress_score", 0.0)
            
            urgency_result = calculate_urgency_score(
                intent=intent,
                stress_score=stress_score,  # Use deterministic stress_score instead of LLM emotion
                repetition_count=self.context.repetition_count,
                clarity_avg=self.context.clarity_avg,
                time_elapsed_seconds=time_elapsed,
                context=context_dict
            )
            
            # Update context with calculated urgency
            self.context.urgency_score = urgency_result["urgency_score"]
            self.context.urgency_level = urgency_result["urgency_level"]
            urgency_level = urgency_result["urgency_level"]
            urgency_score = urgency_result["urgency_score"]
        
        return {
            "incident": {
                # Layer 1: Critical Fields
                "incident_type": self.context.incident_type,
                "location": self.context.location,
                "urgency": urgency_level,
                "urgency_score": urgency_score,
                
                # Layer 2: Operational Fields
                "name": self.context.caller_name,
                "caller_contact": self.context.caller_contact,
                "people_affected": self.context.people_affected,
                "immediate_danger": self.context.immediate_danger,
                
                # Escalation
                "human_required": self.escalation_required
            },
            "missing_fields": self.context.get_missing_fields(),
            "missing_operational_fields": self.context.get_missing_operational_fields(),
            "confidence": {
                "name": self.context.name_confidence,
                "location": self.context.location_confidence,
                "incident_type": self.context.incident_confidence,
                "people_affected": self.context.people_affected_confidence,
                "immediate_danger": self.context.immediate_danger_confidence
            },
            # Layer 3: ML Signals (for dispatcher view)
            "ml_signals": {
                "emotion": self.context.get_dominant_emotion(),
                "clarity_avg": self.context.clarity_avg,
                "language": self.context.language,
                "repetition_count": self.context.repetition_count
            }
        }
    
    def next_question(self) -> str:
        """
        Get the next question (for welcome message or initial greeting).
        
        This is a convenience method that generates the next question
        without processing a transcript first.
        
        Returns:
            str: Next question in Hindi
        """
        return self._generate_next_question()
    
    def get_current_user_input(self) -> str:
        """
        Get the current accumulated user input buffer.
        
        This is used as context for transcription to improve accuracy.
        
        Returns:
            str: Accumulated user input text
        """
        return self.user_input_buffer
    
    def reset(self) -> None:
        """Reset conversation state."""
        self.conversation_history = []
        self.question_count = 0
        self.last_question = None
        self.user_input_buffer = ""
        self.escalation_required = False
        self.escalation_reason = None
        self.escalation_priority = None
        self.last_intent = None
        self.last_intent_confidence = 0.0
        # Note: Context memory persists across resets (by design)


# Global session storage
_active_sessions: Dict[str, HybridMLConversationManager] = {}


def get_or_create_session(session_id: Optional[str] = None) -> HybridMLConversationManager:
    """Get existing session or create a new one."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    if session_id not in _active_sessions:
        _active_sessions[session_id] = HybridMLConversationManager(session_id)
        logger.info(f"Created new HybridMLConversationManager for session: {session_id}")
    
    return _active_sessions[session_id]


def remove_session(session_id: str) -> None:
    """Remove session."""
    if session_id in _active_sessions:
        del _active_sessions[session_id]
        logger.info(f"Removed HybridMLConversationManager for session: {session_id}")

