"""
Conversation management module for India-context-aware live AI conversation.

This module provides ConversationManager class that handles:
- Fragmented speech from streaming audio
- Fast or emotional speech patterns
- Low literacy / vague input handling
- India-specific context awareness (Hindi/Hinglish, cultural considerations)
- Integration with NLP modules (intent, entities, order context)
- Escalation detection for human intervention

Indian Context Considerations:
- Hindi/Hinglish code-switching is common
- Regional language variations
- Low literacy users may use simpler vocabulary
- Emotional speech patterns in emergencies
- Cultural communication patterns (respectful, formal)
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import uuid

from app.nlp.intent import detect_intent
from app.nlp.entities import extract_entities
from app.nlp.order_context import OrderContextEngine, get_or_create_context
from app.logic.escalation import check_escalation_required

# Configure logging
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages India-context-aware live AI conversation with fragmented speech handling.
    
    This class orchestrates the entire conversation flow:
    1. Receives fragmented transcripts from Whisper STT
    2. Updates NLP modules (intent, entities, order context)
    3. Generates contextually appropriate Hindi questions
    4. Tracks incident information progressively
    5. Detects when human intervention is needed
    
    Indian Context Features:
    - Handles Hindi/Hinglish naturally
    - Adapts to low literacy levels (simpler questions)
    - Recognizes emotional/panic indicators
    - Respects cultural communication norms
    - Handles regional language variations
    """
    
    def __init__(self, session_id: str):
        """
        Initialize conversation manager for a session.
        
        Sets up:
        - Conversation state and history
        - Order context engine for incident tracking
        - NLP state tracking
        - Escalation flags
        
        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session_id = session_id
        
        # Conversation state
        self.conversation_history: List[Dict[str, str]] = []
        self.user_input_buffer: str = ""
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # NLP state tracking
        self.detected_intent: Optional[str] = None
        self.intent_confidence: float = 0.0
        self.question_count: int = 0
        self.last_question: Optional[str] = None
        
        # Order context engine for progressive incident building
        # This maintains state across fragmented speech chunks
        self.order_context: OrderContextEngine = get_or_create_context(session_id)
        
        # Escalation state
        self.escalation_required: bool = False
        self.escalation_reason: Optional[str] = None
        
        # Fragmented speech handling
        # Track incomplete sentences and context
        self.incomplete_sentences: List[str] = []
        self.context_buffer: str = ""
        
        logger.info(f"ConversationManager initialized for session: {session_id}")
    
    def update_user_input(self, transcript: str) -> None:
        """
        Update user input with new transcript and process through NLP pipeline.
        
        This is the core method that:
        1. Accumulates fragmented speech chunks
        2. Updates order context with extracted entities
        3. Detects intent from the conversation
        4. Handles vague/incomplete input
        5. Checks for escalation triggers
        
        Handles Fragmented Speech:
        - Accumulates text chunks into complete context
        - Handles incomplete sentences
        - Maintains conversation flow across chunks
        
        Handles Fast/Emotional Speech:
        - Processes even if transcript is unclear
        - Extracts key information despite emotional language
        - Recognizes panic indicators
        
        Handles Low Literacy/Vague Input:
        - Works with simple vocabulary
        - Extracts meaning from incomplete information
        - Asks clarifying questions when needed
        
        Args:
            transcript: New transcribed text chunk (may be fragmented, emotional, or vague)
        """
        if not transcript or not transcript.strip():
            return
        
        # Normalize and accumulate transcript
        # Handle fragmented speech by accumulating chunks
        transcript_clean = transcript.strip()
        
        # Add to user input buffer
        # This accumulates all user input for full context
        if self.user_input_buffer:
            self.user_input_buffer += " " + transcript_clean
        else:
            self.user_input_buffer = transcript_clean
        
        self.user_input_buffer = self.user_input_buffer.strip()
        self.last_updated = datetime.now()
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": transcript_clean,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"Updated user input for session {self.session_id}: {transcript_clean[:50]}...")
        
        # Step 1: Update Order Context with new transcript
        # This extracts entities (name, location, incident_type, urgency)
        # and progressively builds incident information
        # Handles fragmented speech by accumulating entities over time
        incident_update = self.order_context.update(transcript_clean)
        logger.debug(f"Order context updated: {incident_update.get('completeness', 0):.2f} complete")
        
        # Step 2: Detect Intent from accumulated conversation
        # Intent detection works better with more context
        # Fragmented speech: intent may not be clear from single chunk
        # Solution: Use accumulated buffer for better intent detection
        intent_result = detect_intent(self.user_input_buffer)
        self.detected_intent = intent_result.get("intent")
        self.intent_confidence = intent_result.get("confidence", 0.0)
        
        logger.debug(
            f"Intent detected: {self.detected_intent} "
            f"(confidence: {self.intent_confidence:.2f})"
        )
        
        # Step 3: Check for escalation triggers
        # This checks if human intervention is needed based on:
        # - Urgency level
        # - Panic indicators in speech
        # - Missing critical fields
        # - Multiple failed attempts to get information
        escalation_result = self.check_escalation()
        if escalation_result.get("human_required"):
            self.escalation_required = True
            self.escalation_reason = escalation_result.get("reason")
            logger.warning(
                f"Escalation required for session {self.session_id}: "
                f"{self.escalation_reason}"
            )
    
    def next_question(self) -> str:
        """
        Generate next AI question dynamically in Hindi based on conversation context.
        
        Question Generation Strategy:
        1. Check missing fields in order context
        2. Prioritize critical information (location, incident_type)
        3. Adapt to user's literacy level (simpler questions if needed)
        4. Handle emotional/panic situations (calming, reassuring)
        5. Progress through conversation naturally
        
        Indian Context Considerations:
        - Questions in Hindi (formal, respectful)
        - Simple vocabulary for low literacy users
        - Cultural sensitivity (respectful tone)
        - Regional variations handled naturally
        
        Returns:
            str: Next AI question in Hindi
        """
        # Get current incident state
        incident = self.order_context.get_incident()
        missing_fields = incident.get("missing_fields", [])
        
        # Increment question count
        self.question_count += 1
        
        # Handle first interaction (greeting)
        if self.question_count == 1 or not self.user_input_buffer:
            greeting = (
                "नमस्ते, मैं आपकी मदद के लिए यहाँ हूँ। "
                "कृपया बताएं कि क्या हुआ है?"
            )
            self.last_question = greeting
            return greeting
        
        # Handle escalation situation
        # If escalation is required, acknowledge and reassure
        if self.escalation_required:
            return (
                "मैं समझ गया। आपकी मदद के लिए एक व्यक्ति जल्द ही आपसे बात करेगा। "
                "कृपया प्रतीक्षा करें।"
            )
        
        # Priority-based question generation
        # Critical fields first, then supporting information
        
        # Priority 1: Location (critical for emergency response)
        if "location" in missing_fields:
            location_questions = [
                "कृपया बताएं कि यह घटना कहाँ हुई है?",
                "आप कहाँ हैं? कृपया स्थान बताएं।",
                "मुझे जगह बताएं - कौन सी जगह, कौन सा शहर?"
            ]
            # Rotate questions to avoid repetition
            question = location_questions[(self.question_count - 1) % len(location_questions)]
            self.last_question = question
            return question
        
        # Priority 2: Incident Type (critical for routing)
        if "incident_type" in missing_fields:
            incident_questions = [
                "कृपया बताएं कि क्या हुआ है?",
                "किस तरह की समस्या है?",
                "आप किस बारे में बता रहे हैं - दुर्घटना, अपराध, या चिकित्सा समस्या?"
            ]
            question = incident_questions[(self.question_count - 1) % len(incident_questions)]
            self.last_question = question
            return question
        
        # Priority 3: Urgency (important for prioritization)
        if "urgency" in missing_fields or incident.get("incident", {}).get("urgency") == "medium":
            urgency_questions = [
                "यह कितना जरूरी है?",
                "क्या यह तत्काल मदद की आवश्यकता है?",
                "क्या कोई जान का खतरा है?"
            ]
            question = urgency_questions[(self.question_count - 1) % len(urgency_questions)]
            self.last_question = question
            return question
        
        # Priority 4: Name (optional but helpful)
        if "name" in missing_fields and self.question_count > 2:
            name_questions = [
                "कृपया अपना नाम बताएं।",
                "आपका नाम क्या है?",
                "मैं आपको कैसे संबोधित करूं?"
            ]
            question = name_questions[(self.question_count - 1) % len(name_questions)]
            self.last_question = question
            return question
        
        # Follow-up questions for more details
        # After getting basic information, ask for details
        follow_up_questions = [
            "कृपया और विवरण दें।",
            "क्या आप कुछ और बता सकते हैं?",
            "और क्या हुआ? कृपया बताएं।",
            "क्या कोई और जानकारी है जो आप साझा करना चाहेंगे?"
        ]
        
        # Check if we have enough information
        completeness = incident.get("completeness", 0.0)
        if completeness >= 0.7:
            # Most information gathered - ask for final details
            question = "क्या कोई और जानकारी है जो मुझे देनी चाहिए?"
        else:
            # Still gathering information
            question = follow_up_questions[(self.question_count - 1) % len(follow_up_questions)]
        
        self.last_question = question
        return question
    
    def get_incident_summary(self) -> Dict:
        """
        Get structured JSON incident summary with all relevant information.
        
        Returns comprehensive incident information including:
        - Extracted entities (name, location, incident_type, urgency)
        - Confidence scores
        - Missing fields
        - Human intervention flag
        - Conversation context
        
        Returns:
            dict: Structured JSON with keys:
                - "session_id": str
                - "incident": dict with name, location, incident_type, urgency
                - "confidence": dict with confidence scores
                - "missing_fields": List[str]
                - "human_required": bool - Whether human intervention is needed
                - "escalation_reason": str or None - Reason for escalation
                - "intent": str - Detected intent
                - "intent_confidence": float
                - "conversation_length": int
                - "completeness": float - Overall completeness (0.0-1.0)
                - "created_at": str - ISO timestamp
                - "last_updated": str - ISO timestamp
        """
        # Get incident from order context
        incident = self.order_context.get_incident()
        
        # Check escalation status
        escalation_result = self.check_escalation()
        
        # Build comprehensive summary
        summary = {
            "session_id": self.session_id,
            
            # Incident information from order context
            "incident": {
                "name": incident.get("incident", {}).get("name"),
                "location": incident.get("incident", {}).get("location"),
                "incident_type": incident.get("incident", {}).get("incident_type"),
                "urgency": incident.get("incident", {}).get("urgency"),
            },
            
            # Confidence scores
            "confidence": incident.get("confidence", {}),
            
            # Missing fields
            "missing_fields": incident.get("missing_fields", []),
            
            # Human intervention flag
            "human_required": escalation_result.get("human_required", False),
            "escalation_reason": escalation_result.get("reason"),
            
            # Intent information
            "intent": self.detected_intent,
            "intent_confidence": round(self.intent_confidence, 3),
            
            # Conversation metadata
            "conversation_length": len(self.conversation_history),
            "question_count": self.question_count,
            "completeness": incident.get("completeness", 0.0),
            
            # Timestamps
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }
        
        return summary
    
    def check_escalation(self) -> Dict:
        """
        Check if human intervention is required based on various factors.
        
        Escalation Triggers:
        1. High urgency (critical incidents)
        2. Panic indicators in speech
        3. Missing critical fields after multiple questions
        4. Low confidence in extracted information
        5. Explicit requests for human help
        
        Indian Context Considerations:
        - Recognize panic in Hindi/Hinglish ("तुरंत!", "जल्दी!", "मदद!")
        - Understand cultural expressions of urgency
        - Handle emotional speech patterns
        
        Returns:
            dict: Escalation check result with keys:
                - "human_required": bool
                - "reason": str or None - Reason for escalation
        """
        # Get current incident state
        incident = self.order_context.get_incident()
        missing_fields = incident.get("missing_fields", [])
        completeness = incident.get("completeness", 0.0)
        urgency = incident.get("incident", {}).get("urgency", "medium")
        
        # Use escalation module to check
        # This integrates with escalation.py for escalation logic
        escalation_result = check_escalation_required(
            urgency=urgency,
            missing_fields=missing_fields,
            completeness=completeness,
            user_input=self.user_input_buffer,
            question_count=self.question_count
        )
        
        return escalation_result
    
    def get_current_user_input(self) -> str:
        """
        Get the current accumulated user input.
        
        Returns:
            str: Current user input buffer
        """
        return self.user_input_buffer
    
    def reset(self) -> None:
        """Reset the conversation state."""
        self.user_input_buffer = ""
        self.conversation_history = []
        self.detected_intent = None
        self.intent_confidence = 0.0
        self.question_count = 0
        self.last_question = None
        self.escalation_required = False
        self.escalation_reason = None
        self.incomplete_sentences = []
        self.context_buffer = ""
        
        # Reset order context
        self.order_context.reset()
        
        self.last_updated = datetime.now()
        logger.info(f"ConversationManager reset for session: {self.session_id}")


# Global session storage
# In production, use Redis or a database for distributed systems
_active_sessions: Dict[str, ConversationManager] = {}


def get_or_create_session(session_id: Optional[str] = None) -> ConversationManager:
    """
    Get existing session or create a new one.
    
    Args:
        session_id: Optional session ID. If None, creates a new session.
    
    Returns:
        ConversationManager: Conversation manager instance for the session
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    if session_id not in _active_sessions:
        _active_sessions[session_id] = ConversationManager(session_id)
        logger.info(f"Created new ConversationManager for session: {session_id}")
    
    return _active_sessions[session_id]


def remove_session(session_id: str) -> None:
    """
    Remove a session from active sessions.
    
    Args:
        session_id: Session ID to remove
    """
    if session_id in _active_sessions:
        del _active_sessions[session_id]
        logger.info(f"Removed ConversationManager for session: {session_id}")
