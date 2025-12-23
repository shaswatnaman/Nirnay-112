"""
Order Context Engine for maintaining incident context across conversation.

This module maintains per-session state and progressively updates incident
information (incident_type, location, urgency, name) as new information
arrives from streaming audio chunks.

Features:
- Per-session state management
- Progressive entity accumulation
- Missing field tracking
- Confidence scoring and aggregation
- Structured incident JSON output
"""

import logging
from typing import Dict, Optional, List, Set
from datetime import datetime
from app.nlp.entities import extract_entities, UrgencyLevel

# Configure logging
logger = logging.getLogger(__name__)


class OrderContextEngine:
    """
    Maintains per-session incident context and progressively updates fields.
    
    This class tracks incident information across multiple conversation turns,
    accumulating entities as they are mentioned and maintaining confidence scores.
    It tracks which fields are missing and provides structured incident data.
    
    State Management:
    - Each session has its own OrderContextEngine instance
    - State persists across multiple audio chunks
    - Fields are updated progressively as new information arrives
    - Confidence scores are aggregated over time
    """
    
    def __init__(self, session_id: str):
        """
        Initialize order context engine for a session.
        
        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session_id = session_id
        
        # Incident fields with current values
        # These are updated progressively as new information arrives
        self.incident_type: Optional[str] = None
        self.location: Optional[str] = None
        self.urgency: Optional[str] = None
        self.name: Optional[str] = None
        
        # Confidence scores for each field
        # Aggregated over multiple updates (weighted average)
        self.confidence: Dict[str, float] = {
            "incident_type": 0.0,
            "location": 0.0,
            "urgency": 0.0,
            "name": 0.0
        }
        
        # Track update counts for confidence aggregation
        # More updates with consistent values increase confidence
        self.update_counts: Dict[str, int] = {
            "incident_type": 0,
            "location": 0,
            "urgency": 0,
            "name": 0
        }
        
        # Track all values seen for each field (for conflict detection)
        self.value_history: Dict[str, List[str]] = {
            "incident_type": [],
            "location": [],
            "urgency": [],
            "name": []
        }
        
        # Timestamps
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        logger.info(f"OrderContextEngine initialized for session: {session_id}")
    
    def update(self, text: str) -> Dict[str, any]:
        """
        Update incident context with new text chunk.
        
        This method:
        1. Extracts entities from the new text
        2. Updates existing fields if new information is found
        3. Aggregates confidence scores
        4. Tracks missing fields
        5. Returns current incident state
        
        Progressive Update Logic:
        - If field is empty, set it to new value
        - If field has value, update only if new confidence is higher
        - Aggregate confidence scores (weighted average)
        - Track value history for conflict detection
        
        Args:
            text: New text chunk from user (may be fragmented)
        
        Returns:
            dict: Current incident state with entities and confidence
        """
        if not text or not text.strip():
            # No new text - return current state
            return self.get_incident()
        
        logger.debug(f"Updating context for session {self.session_id} with text: {text[:50]}...")
        
        # Extract entities from new text
        # This uses the entities.py module to extract structured information
        extraction_result = extract_entities(text)
        new_entities = extraction_result.get("entities", {})
        new_confidence = extraction_result.get("confidence", {})
        
        # Update each field progressively
        self._update_field("incident_type", new_entities.get("incident_type"), 
                          new_confidence.get("incident_type", 0.0))
        self._update_field("location", new_entities.get("location"), 
                          new_confidence.get("location", 0.0))
        self._update_field("urgency", new_entities.get("urgency"), 
                          new_confidence.get("urgency", 0.0))
        self._update_field("name", new_entities.get("name"), 
                          new_confidence.get("name", 0.0))
        
        # Update timestamp
        self.last_updated = datetime.now()
        
        # Return current incident state
        return self.get_incident()
    
    def _update_field(self, field_name: str, new_value: Optional[str], 
                     new_confidence: float) -> None:
        """
        Update a specific field with new value and confidence.
        
        Update Strategy:
        1. If field is empty, set to new value
        2. If field has value:
           - Update if new confidence is significantly higher (0.2 threshold)
           - Or if new value matches existing (consolidate confidence)
        3. Aggregate confidence scores (weighted average)
        4. Track value history
        
        Args:
            field_name: Name of field to update
            new_value: New value to consider (may be None)
            new_confidence: Confidence score for new value (0.0-1.0)
        """
        # Lower confidence threshold to capture more entities (0.2 instead of 0.3)
        # This helps with fragmented speech where confidence might be lower
        if not new_value or new_confidence < 0.2:
            # Get current value for logging (before early return)
            current_value = getattr(self, field_name)
            # Low confidence or empty value - don't update
            return
        
        current_value = getattr(self, field_name)
        current_conf = self.confidence[field_name]
        
        # Special handling for urgency (always update if higher confidence)
        if field_name == "urgency":
            if current_value is None or new_confidence > current_conf + 0.1:
                setattr(self, field_name, new_value)
                self._aggregate_confidence(field_name, new_confidence)
                self.value_history[field_name].append(new_value)
                logger.debug(f"Updated {field_name}: {new_value} (confidence: {new_confidence:.2f})")
            return
        
        # For other fields: update if empty or if new confidence is significantly higher
        if current_value is None:
            # Field is empty - set to new value
            setattr(self, field_name, new_value)
            self._aggregate_confidence(field_name, new_confidence)
            self.value_history[field_name].append(new_value)
            self.update_counts[field_name] += 1
            logger.debug(f"Set {field_name}: {new_value} (confidence: {new_confidence:.2f})")
        
        elif new_confidence > current_conf + 0.2:
            # New confidence is significantly higher - replace value
            setattr(self, field_name, new_value)
            self._aggregate_confidence(field_name, new_confidence)
            self.value_history[field_name].append(new_value)
            self.update_counts[field_name] += 1
            logger.debug(
                f"Updated {field_name}: {current_value} -> {new_value} "
                f"(confidence: {current_conf:.2f} -> {new_confidence:.2f})"
            )
        
        elif new_value.lower() == current_value.lower():
            # Same value - consolidate confidence (weighted average)
            self._aggregate_confidence(field_name, new_confidence)
            self.update_counts[field_name] += 1
            logger.debug(
                f"Consolidated {field_name}: {new_value} "
                f"(confidence: {self.confidence[field_name]:.2f})"
            )
    
    def _aggregate_confidence(self, field_name: str, new_confidence: float) -> None:
        """
        Aggregate confidence scores using weighted average.
        
        Confidence Aggregation:
        - First update: use new confidence directly
        - Subsequent updates: weighted average (existing * 0.6 + new * 0.4)
        - Multiple consistent updates increase confidence
        - Confidence capped at 1.0
        
        Args:
            field_name: Name of field
            new_confidence: New confidence score to aggregate
        """
        current_conf = self.confidence[field_name]
        update_count = self.update_counts[field_name]
        
        if update_count == 0:
            # First update - use new confidence directly
            self.confidence[field_name] = new_confidence
        else:
            # Weighted average: existing confidence weighted more (0.6) than new (0.4)
            # This prevents single high-confidence update from overriding accumulated confidence
            aggregated = (current_conf * 0.6) + (new_confidence * 0.4)
            
            # Boost confidence if multiple consistent updates
            if update_count > 1:
                boost = min(update_count * 0.05, 0.2)  # Max 20% boost
                aggregated = min(aggregated + boost, 1.0)
            
            self.confidence[field_name] = min(aggregated, 1.0)
    
    def get_missing_fields(self) -> List[str]:
        """
        Get list of fields that are still missing.
        
        Returns:
            List[str]: List of field names that are None or have low confidence
        """
        missing = []
        
        # Check each field
        if not self.incident_type or self.confidence["incident_type"] < 0.3:
            missing.append("incident_type")
        
        if not self.location or self.confidence["location"] < 0.3:
            missing.append("location")
        
        if not self.urgency or self.confidence["urgency"] < 0.3:
            missing.append("urgency")
        
        # Name is optional, but track if missing
        if not self.name or self.confidence["name"] < 0.3:
            missing.append("name")
        
        return missing
    
    def get_incident(self) -> Dict[str, any]:
        """
        Get structured JSON incident with confidence scores.
        
        This is the main output method that returns the current state
        of the incident with all fields and their confidence scores.
        
        Returns:
            dict: Structured incident JSON with keys:
                - "session_id": str - Session identifier
                - "incident": dict - Incident fields
                    - "incident_type": str or None
                    - "location": str or None
                    - "urgency": str or None
                    - "name": str or None
                - "confidence": dict - Confidence scores (0.0-1.0)
                    - "incident_type": float
                    - "location": float
                    - "urgency": float
                    - "name": float
                - "missing_fields": List[str] - Fields that are still missing
                - "completeness": float - Overall completeness score (0.0-1.0)
                - "created_at": str - ISO timestamp of creation
                - "last_updated": str - ISO timestamp of last update
        """
        missing_fields = self.get_missing_fields()
        
        # Calculate completeness score
        # Based on number of filled fields and their confidence
        total_fields = 4  # incident_type, location, urgency, name
        filled_fields = total_fields - len(missing_fields)
        
        # Completeness = (filled fields / total) * average confidence
        if filled_fields > 0:
            avg_confidence = sum(self.confidence.values()) / total_fields
            completeness = (filled_fields / total_fields) * avg_confidence
        else:
            completeness = 0.0
        
        # Build incident dictionary
        incident = {
            "session_id": self.session_id,
            "incident": {
                "incident_type": self.incident_type,
                "location": self.location,
                "urgency": self.urgency or UrgencyLevel.MEDIUM.value,  # Default to MEDIUM
                "name": self.name
            },
            "confidence": {
                "incident_type": round(self.confidence["incident_type"], 3),
                "location": round(self.confidence["location"], 3),
                "urgency": round(self.confidence["urgency"], 3),
                "name": round(self.confidence["name"], 3)
            },
            "missing_fields": missing_fields,
            "completeness": round(completeness, 3),
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }
        
        return incident
    
    def reset(self) -> None:
        """
        Reset all fields and state.
        
        Useful for starting a new incident in the same session.
        """
        self.incident_type = None
        self.location = None
        self.urgency = None
        self.name = None
        
        self.confidence = {
            "incident_type": 0.0,
            "location": 0.0,
            "urgency": 0.0,
            "name": 0.0
        }
        
        self.update_counts = {
            "incident_type": 0,
            "location": 0,
            "urgency": 0,
            "name": 0
        }
        
        self.value_history = {
            "incident_type": [],
            "location": [],
            "urgency": [],
            "name": []
        }
        
        self.last_updated = datetime.now()
        logger.info(f"OrderContextEngine reset for session: {self.session_id}")
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get summary of current context state.
        
        Returns:
            dict: Summary with fields, confidence, and statistics
        """
        return {
            "session_id": self.session_id,
            "fields": {
                "incident_type": self.incident_type,
                "location": self.location,
                "urgency": self.urgency,
                "name": self.name
            },
            "confidence": self.confidence.copy(),
            "update_counts": self.update_counts.copy(),
            "missing_fields": self.get_missing_fields(),
            "completeness": round(
                (4 - len(self.get_missing_fields())) / 4.0 * 
                (sum(self.confidence.values()) / 4.0), 
                3
            )
        }


# Global session storage for OrderContextEngine instances
# In production, use Redis or database for distributed systems
_active_contexts: Dict[str, OrderContextEngine] = {}


def get_or_create_context(session_id: str) -> OrderContextEngine:
    """
    Get existing OrderContextEngine or create a new one for session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        OrderContextEngine: Context engine instance for the session
    """
    if session_id not in _active_contexts:
        _active_contexts[session_id] = OrderContextEngine(session_id)
        logger.info(f"Created new OrderContextEngine for session: {session_id}")
    
    return _active_contexts[session_id]


def remove_context(session_id: str) -> None:
    """
    Remove OrderContextEngine for a session.
    
    Args:
        session_id: Session identifier to remove
    """
    if session_id in _active_contexts:
        del _active_contexts[session_id]
        logger.info(f"Removed OrderContextEngine for session: {session_id}")

