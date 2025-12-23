"""
Context Memory System

Maintains persistent context object that merges partial information over time.
Never overwrites high-confidence fields with low-confidence ones.

Key Features to Prevent Hallucination Lock-in:
1. Confidence-based updates: Only update if new_confidence > existing_confidence
2. Confidence decay: Confidence decreases over time, allowing corrections
3. Source tracking: Track where each piece of information came from
4. No first-update-wins: Later high-confidence updates can replace earlier low-confidence ones

Why this prevents hallucination lock-in:
- If an LLM hallucinates a value with high confidence early, it locks in
- With confidence decay, the hallucinated value's confidence decreases over time
- A later correct value (even with moderate confidence) can replace it
- Source tracking helps identify and debug problematic sources

Context Structure:
{
  "caller_name": null,
  "location": null,
  "incident_type": null,
  "emotion_history": [],
  "clarity_avg": 0.0,
  "repetition_count": 0,
  "last_updated": timestamp
}
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import copy

logger = logging.getLogger(__name__)


@dataclass
class ContextSnapshot:
    """
    Snapshot of ContextMemory state for rollback capability.
    
    Stores a complete copy of context state at a point in time.
    Used to restore context if an update is determined to be unsafe.
    """
    # Layer 1: Critical Fields
    incident_type: Optional[str] = None
    location: Optional[str] = None
    urgency_score: float = 0.0
    urgency_level: str = "medium"
    
    # Layer 2: Operational Fields
    caller_name: Optional[str] = None
    caller_contact: Optional[str] = None
    people_affected: Optional[int] = None
    immediate_danger: bool = False
    
    # Confidence scores
    name_confidence: float = 0.0
    location_confidence: float = 0.0
    incident_confidence: float = 0.0
    people_affected_confidence: float = 0.0
    immediate_danger_confidence: float = 0.0
    
    # Source tracking
    name_source: Optional[str] = None
    location_source: Optional[str] = None
    incident_source: Optional[str] = None
    people_affected_source: Optional[str] = None
    immediate_danger_source: Optional[str] = None
    
    # Timestamps
    name_last_updated: Optional[datetime] = None
    location_last_updated: Optional[datetime] = None
    incident_last_updated: Optional[datetime] = None
    people_affected_last_updated: Optional[datetime] = None
    immediate_danger_last_updated: Optional[datetime] = None
    
    # Layer 3: ML Signals
    emotion_history: List[str] = field(default_factory=list)
    emotion_counts: Dict[str, int] = field(default_factory=dict)
    clarity_scores: List[float] = field(default_factory=list)
    clarity_avg: float = 0.0
    language: str = "Hindi"
    language_history: List[str] = field(default_factory=list)
    repetition_count: int = 0
    previous_transcripts: List[str] = field(default_factory=list)
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    
    def restore_to(self, context: 'ContextMemory') -> None:
        """
        Restore a ContextMemory instance from this snapshot.
        
        Args:
            context: ContextMemory instance to restore
        """
        # Layer 1: Critical Fields
        context.incident_type = self.incident_type
        context.location = self.location
        context.urgency_score = self.urgency_score
        context.urgency_level = self.urgency_level
        
        # Layer 2: Operational Fields
        context.caller_name = self.caller_name
        context.caller_contact = self.caller_contact
        context.people_affected = self.people_affected
        context.immediate_danger = self.immediate_danger
        
        # Confidence scores
        context.name_confidence = self.name_confidence
        context.location_confidence = self.location_confidence
        context.incident_confidence = self.incident_confidence
        context.people_affected_confidence = self.people_affected_confidence
        context.immediate_danger_confidence = self.immediate_danger_confidence
        
        # Source tracking
        context.name_source = self.name_source
        context.location_source = self.location_source
        context.incident_source = self.incident_source
        context.people_affected_source = self.people_affected_source
        context.immediate_danger_source = self.immediate_danger_source
        
        # Timestamps
        context.name_last_updated = self.name_last_updated
        context.location_last_updated = self.location_last_updated
        context.incident_last_updated = self.incident_last_updated
        context.people_affected_last_updated = self.people_affected_last_updated
        context.immediate_danger_last_updated = self.immediate_danger_last_updated
        
        # Layer 3: ML Signals (deep copy to avoid reference issues)
        context.emotion_history = copy.deepcopy(self.emotion_history)
        context.emotion_counts = copy.deepcopy(self.emotion_counts)
        context.clarity_scores = copy.deepcopy(self.clarity_scores)
        context.clarity_avg = self.clarity_avg
        context.language = self.language
        context.language_history = copy.deepcopy(self.language_history)
        context.repetition_count = self.repetition_count
        context.previous_transcripts = copy.deepcopy(self.previous_transcripts)
        
        # Metadata
        context.last_updated = self.last_updated


@dataclass
class ContextMemory:
    """
    Persistent context object for emergency call triage.
    
    Implements 3-Layer Information Model:
    - Layer 1 (Critical): incident_type, location, urgency
    - Layer 2 (Operational): caller_name, caller_contact, people_affected, immediate_danger
    - Layer 3 (ML Signals): emotion, clarity, language, repetition (hidden from user)
    
    Maintains state across multiple conversation turns, merging partial
    information and improving over time.
    """
    session_id: str
    
    # Layer 1: Critical Fields (Must Capture OR Escalate)
    incident_type: Optional[str] = None  # medical_emergency, road_accident, fire, crime, domestic, natural_disaster, unknown
    location: Optional[str] = None  # City/town, landmark, area, optional pincode
    urgency_score: float = 0.0  # System-derived (0.0 to 1.0)
    urgency_level: str = "medium"  # critical, high, medium, low
    
    # Layer 2: Operational Fields (Strongly Recommended)
    caller_name: Optional[str] = None  # First name or alias (never force full name)
    caller_contact: Optional[str] = None  # Phone number (optional, future scope)
    people_affected: Optional[int] = None  # Number of people affected
    immediate_danger: bool = False  # Fire spreading, weapon, bleeding, trapped
    
    # Confidence scores for each field (0.0 to 1.0)
    # Confidence decays over time to prevent hallucination lock-in
    name_confidence: float = 0.0
    location_confidence: float = 0.0
    incident_confidence: float = 0.0
    people_affected_confidence: float = 0.0
    immediate_danger_confidence: float = 0.0
    
    # Source tracking for each field (tracks where the information came from)
    # This helps debug and prevents overwriting high-confidence data with low-confidence hallucinations
    name_source: Optional[str] = None  # e.g., "openai_entities", "user_explicit", "ml_classifier"
    location_source: Optional[str] = None
    incident_source: Optional[str] = None
    people_affected_source: Optional[str] = None
    immediate_danger_source: Optional[str] = None
    
    # Timestamps for each field (for confidence decay calculation)
    name_last_updated: Optional[datetime] = None
    location_last_updated: Optional[datetime] = None
    incident_last_updated: Optional[datetime] = None
    people_affected_last_updated: Optional[datetime] = None
    immediate_danger_last_updated: Optional[datetime] = None
    
    # Layer 3: ML Signals (Hidden from User - NOT asked directly)
    emotion_history: List[str] = field(default_factory=list)  # panic, distress, calm, aggression
    emotion_counts: Dict[str, int] = field(default_factory=lambda: {"panic": 0, "stressed": 0, "calm": 0, "angry": 0})
    
    # Clarity tracking (how understandable the user is)
    clarity_scores: List[float] = field(default_factory=list)
    clarity_avg: float = 0.0
    
    # Language/Dialect tracking
    language: str = "Hindi"  # Hindi, Hinglish, Punjabi-Hindi mix, etc.
    language_history: List[str] = field(default_factory=list)
    
    # Repetition tracking (if user repeats same thing - indicates stress/urgency)
    repetition_count: int = 0
    previous_transcripts: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Hallucination tracking (in-memory, per session)
    hallucination_detected: bool = False  # Flag if hallucination was detected earlier in session
    
    def _apply_confidence_decay(self, confidence: float, last_updated: Optional[datetime], decay_rate: float = 0.05) -> float:
        """
        Apply linear confidence decay over time.
        
        This prevents hallucination lock-in by allowing corrections:
        - Early hallucinations with high confidence will decay over time
        - Later correct values can replace decayed hallucinations
        
        Args:
            confidence: Current confidence value (0.0 to 1.0)
            last_updated: Timestamp when confidence was last set
            decay_rate: Confidence decay per minute (default: 0.05 = 5% per minute)
        
        Returns:
            float: Decayed confidence value
        """
        if last_updated is None:
            return confidence
        
        # Calculate time elapsed in minutes
        time_elapsed_minutes = (datetime.now() - last_updated).total_seconds() / 60.0
        
        # Apply linear decay (clamp to 0.0 minimum)
        decayed_confidence = max(0.0, confidence - (decay_rate * time_elapsed_minutes))
        
        return decayed_confidence
    
    def create_snapshot(self) -> ContextSnapshot:
        """
        Create a snapshot of current context state for rollback capability.
        
        Returns:
            ContextSnapshot: Snapshot of current context state
        """
        return ContextSnapshot(
            # Layer 1: Critical Fields
            incident_type=self.incident_type,
            location=self.location,
            urgency_score=self.urgency_score,
            urgency_level=self.urgency_level,
            
            # Layer 2: Operational Fields
            caller_name=self.caller_name,
            caller_contact=self.caller_contact,
            people_affected=self.people_affected,
            immediate_danger=self.immediate_danger,
            
            # Confidence scores
            name_confidence=self.name_confidence,
            location_confidence=self.location_confidence,
            incident_confidence=self.incident_confidence,
            people_affected_confidence=self.people_affected_confidence,
            immediate_danger_confidence=self.immediate_danger_confidence,
            
            # Source tracking
            name_source=self.name_source,
            location_source=self.location_source,
            incident_source=self.incident_source,
            people_affected_source=self.people_affected_source,
            immediate_danger_source=self.immediate_danger_source,
            
            # Timestamps
            name_last_updated=self.name_last_updated,
            location_last_updated=self.location_last_updated,
            incident_last_updated=self.incident_last_updated,
            people_affected_last_updated=self.people_affected_last_updated,
            immediate_danger_last_updated=self.immediate_danger_last_updated,
            
            # Layer 3: ML Signals (deep copy to avoid reference issues)
            emotion_history=copy.deepcopy(self.emotion_history),
            emotion_counts=copy.deepcopy(self.emotion_counts),
            clarity_scores=copy.deepcopy(self.clarity_scores),
            clarity_avg=self.clarity_avg,
            language=self.language,
            language_history=copy.deepcopy(self.language_history),
            repetition_count=self.repetition_count,
            previous_transcripts=copy.deepcopy(self.previous_transcripts),
            
            # Metadata
            last_updated=self.last_updated
        )
    
    def _check_entity_contradiction(
        self, 
        entities: Dict[str, Any], 
        snapshot: ContextSnapshot,
        signals: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if extracted entities contradict previous values.
        
        Args:
            entities: New entities from signals
            snapshot: Previous context snapshot
            signals: Full signals dict (for intent checking)
        
        Returns:
            str: Contradiction reason if found, None otherwise
        """
        # Check name contradiction
        new_name = entities.get("name")
        if new_name and snapshot.caller_name:
            # Check if names are significantly different (not just variations)
            if new_name.lower().strip() != snapshot.caller_name.lower().strip():
                # Check if they're similar enough to be variations (e.g., "Ramesh" vs "Ramesh Kumar")
                name_words_new = set(new_name.lower().split())
                name_words_old = set(snapshot.caller_name.lower().split())
                # If no common words, it's a contradiction
                if not name_words_new.intersection(name_words_old):
                    return f"Name contradiction: '{snapshot.caller_name}' vs '{new_name}'"
        
        # Check location contradiction
        new_location = entities.get("location")
        if new_location and snapshot.location:
            # Check if locations are significantly different
            if new_location.lower().strip() != snapshot.location.lower().strip():
                # Check if they're similar enough (e.g., "Mumbai" vs "Mumbai, Maharashtra")
                location_words_new = set(new_location.lower().split())
                location_words_old = set(snapshot.location.lower().split())
                # If no common words, it's a contradiction
                if not location_words_new.intersection(location_words_old):
                    return f"Location contradiction: '{snapshot.location}' vs '{new_location}'"
        
        # Check incident type contradiction
        new_incident = entities.get("incident")
        intent_from_signals = signals.get("intent", "")  # Get intent from signals, not entities
        if new_incident and snapshot.incident_type:
            # Normalize both for comparison (use function defined at module level)
            normalized_new = _normalize_incident_type(new_incident)
            normalized_old = _normalize_incident_type(snapshot.incident_type)
            
            if normalized_new != normalized_old and normalized_old != "unknown":
                return f"Incident type contradiction: '{snapshot.incident_type}' vs '{new_incident}'"
        
        # Check intent contradiction if incident is not available
        if intent_from_signals and snapshot.incident_type:
            intent_to_incident = {
                "medical_emergency": "medical_emergency",
                "fire": "fire",
                "road_accident": "road_accident",
                "crime": "crime",
                "domestic_emergency": "domestic_emergency",
                "natural_disaster": "natural_disaster"
            }
            intent_incident = intent_to_incident.get(intent_from_signals)
            if intent_incident and intent_incident != snapshot.incident_type and snapshot.incident_type != "unknown":
                return f"Intent contradiction: intent '{intent_from_signals}' conflicts with incident '{snapshot.incident_type}'"
        
        return None
    
    def _should_rollback(
        self,
        signals: Dict[str, Any],
        snapshot: ContextSnapshot
    ) -> Optional[str]:
        """
        Determine if context update should be rolled back.
        
        Rollback conditions:
        1. Extracted entities contradict previous values
        2. Clarity < 0.3 (very low clarity indicates unreliable transcription)
        3. Hallucination flag was raised earlier in session
        
        Args:
            signals: New signals being applied
            snapshot: Previous context snapshot
        
        Returns:
            str: Rollback reason if rollback needed, None otherwise
        """
        entities = signals.get("entities", {})
        clarity = signals.get("clarity", 0.0)
        
        # Condition 1: Check for entity contradictions
        contradiction = self._check_entity_contradiction(entities, snapshot, signals)
        if contradiction:
            return f"Entity contradiction: {contradiction}"
        
        # Condition 2: Very low clarity (< 0.3)
        if clarity < 0.3:
            return f"Very low clarity ({clarity:.2f}) - transcription may be unreliable"
        
        # Condition 3: Hallucination flag was raised earlier in session
        if self.hallucination_detected:
            return "Hallucination detected earlier in session - being cautious with updates"
        
        return None
    
    def rollback_to_snapshot(self, snapshot: ContextSnapshot, reason: str) -> None:
        """
        Rollback context to a previous snapshot.
        
        This restores the context state to the snapshot and logs the rollback.
        Rollback is safe and will not crash the session.
        
        Args:
            snapshot: ContextSnapshot to restore
            reason: Reason for rollback (for logging)
        """
        try:
            # Track which fields were rolled back
            rolled_back_fields = []
            if snapshot.caller_name != self.caller_name:
                rolled_back_fields.append("caller_name")
            if snapshot.location != self.location:
                rolled_back_fields.append("location")
            if snapshot.incident_type != self.incident_type:
                rolled_back_fields.append("incident_type")
            
            snapshot.restore_to(self)
            logger.warning(
                f"Context rolled back for session {self.session_id}: {reason}. "
                f"Context restored to state from {snapshot.last_updated.isoformat()}"
            )
            
            # Log rollback event
            try:
                from app.logic.event_log import log_rollback_occurred
                log_rollback_occurred(self.session_id, reason, rolled_back_fields)
            except ImportError:
                pass  # Event log not available, continue silently
        except Exception as rollback_error:
            # Rollback must NOT crash the session
            logger.error(
                f"Error during context rollback for session {self.session_id}: {rollback_error}. "
                f"Reason: {reason}. Session will continue with current state.",
                exc_info=True
            )
    
    def update_from_signals(self, signals: Dict[str, Any]) -> None:
        """
        Update context from extracted signals with safety checks and rollback capability.
        
        Merges new information with existing context, never overwriting
        high-confidence fields with low-confidence ones.
        
        Safety Features:
        - Creates snapshot before update
        - Checks for contradictions, low clarity, or previous hallucinations
        - Rolls back if unsafe conditions detected
        
        Args:
            signals: Extracted signals from OpenAI (perception layer)
        """
        # Create snapshot before update for rollback capability
        snapshot = self.create_snapshot()
        
        # Check if update should be rolled back
        rollback_reason = self._should_rollback(signals, snapshot)
        if rollback_reason:
            # Rollback to snapshot (safe, won't crash session)
            self.rollback_to_snapshot(snapshot, rollback_reason)
            # Mark hallucination flag if contradiction detected
            if "contradiction" in rollback_reason.lower():
                self.hallucination_detected = True
            # Don't proceed with update if rollback occurred
            return
        
        # Proceed with normal update (no rollback needed)
        entities = signals.get("entities", {})
        emotion = signals.get("emotion", "calm")
        clarity = signals.get("clarity", 0.0)
        
        # Track which fields are being updated for event logging
        updated_fields = []
        
        # Apply confidence decay to existing fields before comparing
        # This allows corrections to replace decayed hallucinations
        decayed_name_confidence = self._apply_confidence_decay(
            self.name_confidence, 
            self.name_last_updated
        )
        decayed_location_confidence = self._apply_confidence_decay(
            self.location_confidence,
            self.location_last_updated
        )
        decayed_incident_confidence = self._apply_confidence_decay(
            self.incident_confidence,
            self.incident_last_updated
        )
        decayed_people_affected_confidence = self._apply_confidence_decay(
            self.people_affected_confidence,
            self.people_affected_last_updated
        )
        decayed_immediate_danger_confidence = self._apply_confidence_decay(
            self.immediate_danger_confidence,
            self.immediate_danger_last_updated
        )
        
        # Update name (only if new confidence is higher than decayed existing confidence)
        # This prevents hallucination lock-in: early hallucinations decay, allowing corrections
        new_name = entities.get("name")
        if new_name:
            # Get confidence from signals if available, otherwise use default
            new_name_confidence = entities.get("name_confidence", signals.get("name_confidence", 0.6))
            new_name_source = entities.get("name_source", signals.get("name_source", "openai_entities"))
            
            # Only update if new confidence is higher than decayed existing confidence
            if new_name_confidence > decayed_name_confidence:
                self.caller_name = new_name
                self.name_confidence = new_name_confidence
                self.name_source = new_name_source
                self.name_last_updated = datetime.now()
                updated_fields.append("caller_name")
                logger.debug(f"Updated name: {new_name} (confidence: {new_name_confidence:.3f}, source: {new_name_source})")
            else:
                logger.debug(f"Skipping name update: new confidence {new_name_confidence:.3f} <= decayed existing {decayed_name_confidence:.3f}")
        else:
            # Apply decay even if no new value (update confidence)
            if decayed_name_confidence < self.name_confidence:
                self.name_confidence = decayed_name_confidence
        
        # Update location (only if new confidence is higher than decayed existing confidence)
        new_location = entities.get("location")
        if new_location:
            new_location_confidence = entities.get("location_confidence", signals.get("location_confidence", 0.6))
            new_location_source = entities.get("location_source", signals.get("location_source", "openai_entities"))
            
            if new_location_confidence > decayed_location_confidence:
                self.location = new_location
                self.location_confidence = new_location_confidence
                self.location_source = new_location_source
                self.location_last_updated = datetime.now()
                updated_fields.append("location")
                logger.debug(f"Updated location: {new_location} (confidence: {new_location_confidence:.3f}, source: {new_location_source})")
            else:
                logger.debug(f"Skipping location update: new confidence {new_location_confidence:.3f} <= decayed existing {decayed_location_confidence:.3f}")
        else:
            # Apply decay even if no new value
            if decayed_location_confidence < self.location_confidence:
                self.location_confidence = decayed_location_confidence
        
        # Update incident type (only if new confidence is higher)
        # Map OpenAI incident types to our standard categories
        # Also check intent from signals (OpenAI might classify intent but not extract incident entity)
        new_incident = entities.get("incident")
        intent_from_signals = signals.get("intent", "")
        
        # Use intent if incident entity is not available but intent is clear
        if not new_incident and intent_from_signals and intent_from_signals != "unclear" and intent_from_signals != "non_emergency":
            # Map intent to incident type
            intent_to_incident = {
                "medical_emergency": "medical_emergency",
                "fire": "fire",
                "road_accident": "road_accident",
                "crime": "crime",
                "domestic_emergency": "domestic_emergency",
                "natural_disaster": "natural_disaster",
                "industrial_accident": "industrial_accident",
                "public_transport": "public_transport",
                "mental_health": "medical_emergency"  # Mental health maps to medical
            }
            new_incident = intent_to_incident.get(intent_from_signals, intent_from_signals)
            logger.debug(f"Using intent '{intent_from_signals}' as incident type: {new_incident}")
        
        if new_incident:
            # Normalize incident type to standard categories
            # IMPORTANT: Normalize BEFORE checking confidence to ensure correct categorization
            incident_normalized = _normalize_incident_type(new_incident)
            
            # Get confidence from signals (intent_confidence if from intent, otherwise entity confidence)
            new_incident_confidence = (
                signals.get("intent_confidence", 0.0) if intent_from_signals else 
                entities.get("incident_confidence", signals.get("incident_confidence", 0.6))
            )
            new_incident_source = (
                signals.get("intent_source", "local_ml") if intent_from_signals else
                entities.get("incident_source", signals.get("incident_source", "openai_entities"))
            )
            
            # Only update if new confidence is higher than decayed existing confidence
            # This prevents hallucination lock-in: early incorrect classifications decay over time
            if new_incident_confidence > decayed_incident_confidence:
                self.incident_type = incident_normalized
                self.incident_confidence = new_incident_confidence
                self.incident_source = new_incident_source
                self.incident_last_updated = datetime.now()
                updated_fields.append("incident_type")
                logger.debug(f"Updated incident_type: {incident_normalized} (from: {new_incident}, intent: {intent_from_signals}, confidence: {new_incident_confidence:.3f}, source: {new_incident_source})")
            else:
                logger.debug(f"Skipping incident_type update: new confidence {new_incident_confidence:.3f} <= decayed existing {decayed_incident_confidence:.3f}")
        else:
            # Apply decay even if no new value
            if decayed_incident_confidence < self.incident_confidence:
                self.incident_confidence = decayed_incident_confidence
        
        # Update Layer 2: People affected (if mentioned, only if new confidence is higher)
        people_affected = entities.get("people_affected")
        if people_affected is not None:
            new_people_affected_confidence = entities.get("people_affected_confidence", signals.get("people_affected_confidence", 0.6))
            new_people_affected_source = entities.get("people_affected_source", signals.get("people_affected_source", "openai_entities"))
            
            # Only update if new confidence is higher than decayed existing confidence
            if new_people_affected_confidence > decayed_people_affected_confidence:
                try:
                    # Try to extract number
                    extracted_value = None
                    if isinstance(people_affected, (int, float)):
                        extracted_value = int(people_affected)
                    elif isinstance(people_affected, str):
                        # Extract number from string like "3", "तीन", "three"
                        import re
                        numbers = re.findall(r'\d+', people_affected)
                        if numbers:
                            extracted_value = int(numbers[0])
                        else:
                            # Try Hindi number words
                            hindi_numbers = {"एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10}
                            for word, num in hindi_numbers.items():
                                if word in people_affected.lower():
                                    extracted_value = num
                                    break
                    
                    if extracted_value is not None:
                        self.people_affected = extracted_value
                        self.people_affected_confidence = new_people_affected_confidence
                        self.people_affected_source = new_people_affected_source
                        self.people_affected_last_updated = datetime.now()
                        logger.debug(f"Updated people_affected: {self.people_affected} (confidence: {new_people_affected_confidence:.3f}, source: {new_people_affected_source})")
                except (ValueError, TypeError):
                    pass
            else:
                logger.debug(f"Skipping people_affected update: new confidence {new_people_affected_confidence:.3f} <= decayed existing {decayed_people_affected_confidence:.3f}")
        else:
            # Apply decay even if no new value
            if decayed_people_affected_confidence < self.people_affected_confidence:
                self.people_affected_confidence = decayed_people_affected_confidence
        
        # Update Layer 2: Immediate danger indicator (only if new confidence is higher)
        immediate_danger = entities.get("immediate_danger")
        if immediate_danger is not None:
            new_immediate_danger_confidence = entities.get("immediate_danger_confidence", signals.get("immediate_danger_confidence", 0.6))
            new_immediate_danger_source = entities.get("immediate_danger_source", signals.get("immediate_danger_source", "openai_entities"))
            
            # Only update if new confidence is higher than decayed existing confidence
            if new_immediate_danger_confidence > decayed_immediate_danger_confidence:
                if isinstance(immediate_danger, bool):
                    self.immediate_danger = immediate_danger
                elif isinstance(immediate_danger, str):
                    # Check for danger keywords
                    danger_keywords = ["fire spreading", "weapon", "bleeding", "trapped", "आग फैल", "हथियार", "खून", "फंसा"]
                    self.immediate_danger = any(kw in immediate_danger.lower() for kw in danger_keywords)
                self.immediate_danger_confidence = new_immediate_danger_confidence
                self.immediate_danger_source = new_immediate_danger_source
                self.immediate_danger_last_updated = datetime.now()
                logger.debug(f"Updated immediate_danger: {self.immediate_danger} (confidence: {new_immediate_danger_confidence:.3f}, source: {new_immediate_danger_source})")
            else:
                logger.debug(f"Skipping immediate_danger update: new confidence {new_immediate_danger_confidence:.3f} <= decayed existing {decayed_immediate_danger_confidence:.3f}")
        else:
            # Apply decay even if no new value
            if decayed_immediate_danger_confidence < self.immediate_danger_confidence:
                self.immediate_danger_confidence = decayed_immediate_danger_confidence
        
        # Update Layer 3: Language/Dialect
        language = signals.get("language", "Hindi")
        if language:
            self.language = language
            self.language_history.append(language)
            # Keep only last 5 language detections
            if len(self.language_history) > 5:
                self.language_history = self.language_history[-5:]
        
        # Track emotion history
        self.emotion_history.append(emotion)
        if emotion in self.emotion_counts:
            self.emotion_counts[emotion] += 1
        
        # Track clarity scores
        self.clarity_scores.append(clarity)
        self.clarity_avg = sum(self.clarity_scores) / len(self.clarity_scores) if self.clarity_scores else 0.0
        
        # Track repetition (simple check: if same transcript appears multiple times)
        transcript = signals.get("transcript", "")
        if transcript in self.previous_transcripts:
            self.repetition_count += 1
        self.previous_transcripts.append(transcript)
        # Keep only last 10 transcripts
        if len(self.previous_transcripts) > 10:
            self.previous_transcripts = self.previous_transcripts[-10:]
        
        self.last_updated = datetime.now()
        
        # Log context update event if any fields were updated
        if updated_fields:
            try:
                from app.logic.event_log import log_context_updated
                log_context_updated(self.session_id, updated_fields, signals)
            except ImportError:
                pass  # Event log not available, continue silently
    
    def get_missing_fields(self) -> List[str]:
        """
        Get list of missing critical fields (Layer 1 only).
        
        Layer 1 fields are critical - if missing, system should escalate.
        Layer 2 fields are optional but recommended.
        """
        missing = []
        # Layer 1: Critical fields
        if not self.location:
            missing.append("location")
        if not self.incident_type or self.incident_type == "unknown":
            missing.append("incident_type")
        # Note: urgency is always system-derived, so never "missing"
        return missing
    
    def get_missing_operational_fields(self) -> List[str]:
        """Get list of missing Layer 2 (operational) fields."""
        missing = []
        if not self.caller_name:
            missing.append("name")
        if self.people_affected is None:
            missing.append("people_affected")
        # caller_contact and immediate_danger are optional, not tracked as "missing"
        return missing
    
    def get_dominant_emotion(self) -> str:
        """Get the most frequently observed emotion."""
        if not self.emotion_counts:
            return "calm"
        return max(self.emotion_counts.items(), key=lambda x: x[1])[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            # Layer 1: Critical Fields
            "incident_type": self.incident_type,
            "location": self.location,
            "urgency_score": self.urgency_score,
            "urgency_level": self.urgency_level,
            "incident_confidence": self.incident_confidence,
            "location_confidence": self.location_confidence,
            "incident_source": self.incident_source,
            "location_source": self.location_source,
            
            # Layer 2: Operational Fields
            "caller_name": self.caller_name,
            "caller_contact": self.caller_contact,
            "people_affected": self.people_affected,
            "immediate_danger": self.immediate_danger,
            "name_confidence": self.name_confidence,
            "people_affected_confidence": self.people_affected_confidence,
            "immediate_danger_confidence": self.immediate_danger_confidence,
            "name_source": self.name_source,
            "people_affected_source": self.people_affected_source,
            "immediate_danger_source": self.immediate_danger_source,
            
            # Layer 3: ML Signals (for dispatcher view)
            "emotion_history": self.emotion_history[-5:],  # Last 5 emotions
            "dominant_emotion": self.get_dominant_emotion(),
            "clarity_avg": self.clarity_avg,
            "language": self.language,
            "repetition_count": self.repetition_count,
            
            # Metadata
            "missing_fields": self.get_missing_fields(),
            "missing_operational_fields": self.get_missing_operational_fields(),
            "last_updated": self.last_updated.isoformat()
        }


def _normalize_incident_type(incident: str) -> str:
    """
    Normalize incident type to standard categories using India-specific keywords.
    
    Uses comprehensive keyword matching from india_keywords.py as fallback.
    Maps various incident descriptions to standard types:
    - medical_emergency
    - road_accident
    - fire
    - crime
    - domestic_emergency
    - natural_disaster
    - industrial_accident
    - public_transport
    - mental_health
    - unknown
    """
    if not incident:
        return "unknown"
    
    # Use India-specific keyword classification (fallback rule engine)
    from app.nlp.india_keywords import classify_incident_by_keywords
    
    # Classify using keyword matching
    classified = classify_incident_by_keywords(incident)
    
    # Map to standard categories (some categories map to existing ones)
    category_mapping = {
        "medical_emergency": "medical_emergency",
        "road_accident": "road_accident",
        "fire": "fire",
        "crime": "crime",
        "domestic_emergency": "domestic_emergency",
        "natural_disaster": "natural_disaster",
        "industrial_accident": "road_accident",  # Map industrial to road_accident for now
        "public_transport": "road_accident",  # Map public transport to road_accident for now
        "mental_health": "medical_emergency",  # Map mental health to medical_emergency
        "unknown": "unknown"
    }
    
    return category_mapping.get(classified, "unknown")


# Global session storage (in production, use Redis or database)
_active_contexts: Dict[str, ContextMemory] = {}


def get_or_create_context(session_id: str) -> ContextMemory:
    """Get existing context or create a new one."""
    if session_id not in _active_contexts:
        _active_contexts[session_id] = ContextMemory(session_id=session_id)
        logger.info(f"Created new ContextMemory for session: {session_id}")
    return _active_contexts[session_id]


def remove_context(session_id: str) -> None:
    """Remove context for a session."""
    if session_id in _active_contexts:
        del _active_contexts[session_id]
        logger.info(f"Removed ContextMemory for session: {session_id}")

