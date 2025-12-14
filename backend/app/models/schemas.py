"""
Pydantic schemas for data validation and type safety.

This module defines Pydantic models for:
- Incident data structures
- Transcript updates and conversation history
- WebSocket messages and API responses
- Error handling

All models include:
- Type hints for validation
- Default values where appropriate
- Detailed comments explaining fields
- JSON serialization support
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class UrgencyLevel(str, Enum):
    """
    Urgency level enumeration for incidents.
    
    Used to classify the urgency of an incident for proper prioritization.
    """
    CRITICAL = "critical"  # Life-threatening, immediate response needed
    HIGH = "high"  # Urgent, response needed soon
    MEDIUM = "medium"  # Important but not immediately urgent
    LOW = "low"  # Non-urgent, can wait


class IncidentType(str, Enum):
    """
    Incident type enumeration.
    
    Classifies the type of incident for proper routing and handling.
    """
    ACCIDENT = "accident"  # Vehicle accidents, collisions
    CRIME = "crime"  # Theft, robbery, assault
    MEDICAL = "medical"  # Health emergencies, injuries
    FIRE = "fire"  # Fire incidents
    OTHER = "other"  # Other types of incidents


class Speaker(str, Enum):
    """
    Speaker type enumeration for transcript updates.
    
    Identifies who spoke in a conversation turn.
    """
    USER = "user"  # User/caller speaking
    AI = "ai"  # AI assistant speaking


class Incident(BaseModel):
    """
    Pydantic model for incident information.
    
    This model represents a structured incident report with all relevant
    information extracted from the conversation. Used for:
    - Storing incident data
    - API responses
    - Database persistence
    - Frontend display
    
    All fields are validated and type-checked by Pydantic.
    """
    
    # Incident type: what kind of incident occurred
    # Optional because it may not be identified immediately
    type: Optional[IncidentType] = Field(
        default=None,
        description="Type of incident (accident, crime, medical, fire, other)"
    )
    
    # Location: where the incident occurred
    # Critical for emergency response routing
    location: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Location of the incident (address, landmark, city, etc.)"
    )
    
    # Urgency level: how urgent the incident is
    # Defaults to MEDIUM if not specified
    urgency: UrgencyLevel = Field(
        default=UrgencyLevel.MEDIUM,
        description="Urgency level of the incident (critical, high, medium, low)"
    )
    
    # Confidence: overall confidence in the incident data
    # Range: 0.0 (no confidence) to 1.0 (complete confidence)
    # Aggregated from individual field confidences
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for incident data (0.0 to 1.0)"
    )
    
    # Human required: whether human intervention is needed
    # True if escalation is triggered (high urgency, panic, missing fields, etc.)
    human_required: bool = Field(
        default=False,
        description="Whether human operator intervention is required"
    )
    
    # Optional fields for additional incident information
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of the person reporting the incident (optional)"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional description or details about the incident"
    )
    
    # Metadata for tracking and debugging
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for tracking this incident"
    )
    
    created_at: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Timestamp when incident was first created"
    )
    
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Timestamp when incident was last updated"
    )
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """
        Validate confidence score is within valid range.
        
        Args:
            v: Confidence value to validate
        
        Returns:
            float: Validated confidence value
        
        Raises:
            ValueError: If confidence is outside [0.0, 1.0]
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 3)  # Round to 3 decimal places
    
    @validator('location')
    def validate_location(cls, v):
        """
        Validate and normalize location string.
        
        Args:
            v: Location string to validate
        
        Returns:
            str or None: Normalized location string
        """
        if v is None:
            return None
        # Trim whitespace
        v = v.strip()
        if not v:
            return None
        return v
    
    class Config:
        """Pydantic configuration."""
        # Use enum values in JSON serialization
        use_enum_values = True
        # Validate on assignment
        validate_assignment = True
        # Example values for API documentation
        schema_extra = {
            "example": {
                "type": "accident",
                "location": "Delhi, Connaught Place",
                "urgency": "high",
                "confidence": 0.85,
                "human_required": False,
                "name": "Ram",
                "description": "Car accident on main road",
                "session_id": "abc123",
                "created_at": "2024-01-01T12:00:00",
                "last_updated": "2024-01-01T12:05:00"
            }
        }


class TranscriptUpdate(BaseModel):
    """
    Pydantic model for transcript updates in conversation.
    
    This model represents a single turn in the conversation, tracking
    what was said, by whom, and when. Used for:
    - Conversation history tracking
    - Real-time transcript updates
    - Logging and debugging
    - Frontend transcript display
    
    Each transcript update represents one speech segment from either
    the user or the AI assistant.
    """
    
    # Text: the transcribed or generated text
    # Required field - every transcript update must have text
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The transcribed or generated text content"
    )
    
    # Timestamp: when this transcript update occurred
    # Defaults to current time if not provided
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when this transcript update occurred"
    )
    
    # Speaker: who spoke (user or AI)
    # Required field - must be either "user" or "ai"
    speaker: Speaker = Field(
        ...,
        description="Who spoke: 'user' for caller, 'ai' for assistant"
    )
    
    # Optional fields for additional context
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for tracking this transcript"
    )
    
    # Confidence: confidence in transcription accuracy (for user speech)
    # Only relevant for user transcripts (AI text is always 1.0)
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in transcription accuracy (0.0 to 1.0)"
    )
    
    # Metadata for additional information
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (intent, entities, etc.)"
    )
    
    @validator('text')
    def validate_text(cls, v):
        """
        Validate and normalize text content.
        
        Args:
            v: Text string to validate
        
        Returns:
            str: Normalized text string
        
        Raises:
            ValueError: If text is empty after normalization
        """
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()
    
    @validator('confidence')
    def validate_confidence(cls, v, values):
        """
        Validate confidence score.
        
        For AI transcripts, confidence should be None or 1.0.
        For user transcripts, confidence can be any value in [0.0, 1.0].
        
        Args:
            v: Confidence value to validate
            values: Other field values (to check speaker)
        
        Returns:
            float or None: Validated confidence value
        """
        if v is None:
            return None
        
        speaker = values.get('speaker')
        if speaker == Speaker.AI and v != 1.0:
            # AI text is always accurate (confidence = 1.0)
            return 1.0
        
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        
        return round(v, 3)  # Round to 3 decimal places
    
    class Config:
        """Pydantic configuration."""
        # Use enum values in JSON serialization
        use_enum_values = True
        # Validate on assignment
        validate_assignment = True
        # Example values for API documentation
        schema_extra = {
            "example": {
                "text": "मेरा नाम राम है, दिल्ली में दुर्घटना हुई",
                "timestamp": "2024-01-01T12:00:00",
                "speaker": "user",
                "session_id": "abc123",
                "confidence": 0.92,
                "metadata": {
                    "intent": "Accident",
                    "entities": {
                        "name": "Ram",
                        "location": "Delhi"
                    }
                }
            }
        }


# Legacy models for backward compatibility
class IncidentSummary(BaseModel):
    """
    Legacy schema for incident summary (backward compatibility).
    
    This model is kept for compatibility with existing code.
    New code should use the Incident model instead.
    """
    
    session_id: str
    user_input: str
    conversation_length: int
    created_at: str
    last_updated: str
    status: str
    metadata: Optional[Dict[str, Any]] = None


class WebSocketMessage(BaseModel):
    """
    Schema for WebSocket messages.
    
    Used for structured WebSocket communication between frontend and backend.
    """
    
    type: str = Field(
        ...,
        description="Message type (e.g., 'audio_chunk', 'session_init', 'error')"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Message data payload"
    )


class ErrorResponse(BaseModel):
    """
    Schema for error responses.
    
    Used for standardized error reporting in API responses.
    """
    
    error: str = Field(
        ...,
        description="Error type or code"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier (if applicable)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp when error occurred"
    )
