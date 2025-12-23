"""
Append-Only Event Log for Audit Trail

This module provides an in-memory, append-only event log for tracking
system events during emergency call triage sessions.

Key Features:
- Append-only: Events are never modified or deleted
- In-memory storage: No database required
- Per-session logs: Events grouped by session_id
- Structured events: Consistent event format with timestamps

Event Types:
- transcription_received: When transcription is received from ASR
- context_updated: When context memory is updated
- escalation_triggered: When escalation is triggered
- rollback_occurred: When context rollback occurs
- api_failure: When API calls fail (OpenAI, etc.)

This is for demo/debug purposes only - no authentication required.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# In-memory storage: session_id -> list of events
_event_logs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


def log_event(
    session_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an event to the audit trail.
    
    Events are append-only and stored in-memory per session.
    This is for demo/debug purposes - no persistence or authentication.
    
    Args:
        session_id: Session identifier
        event_type: Type of event (transcription_received, context_updated, etc.)
        payload: Optional event-specific data
    """
    if not session_id:
        logger.warning("Attempted to log event with empty session_id")
        return
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "session_id": session_id,
        "payload": payload or {}
    }
    
    # Append to session's event log (append-only)
    _event_logs[session_id].append(event)
    
    logger.debug(f"Logged event: {event_type} for session {session_id}")
    
    # Keep only last 1000 events per session to prevent memory issues
    if len(_event_logs[session_id]) > 1000:
        logger.warning(f"Event log for session {session_id} exceeded 1000 events, keeping last 1000")
        _event_logs[session_id] = _event_logs[session_id][-1000:]


def get_session_events(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all events for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        List of event dicts, ordered by timestamp (oldest first)
    """
    return _event_logs.get(session_id, [])


def get_all_sessions() -> List[str]:
    """
    Get list of all session IDs that have events.
    
    Returns:
        List of session IDs
    """
    return list(_event_logs.keys())


def clear_session_events(session_id: str) -> None:
    """
    Clear events for a session (for testing/debugging).
    
    Args:
        session_id: Session identifier
    """
    if session_id in _event_logs:
        del _event_logs[session_id]
        logger.info(f"Cleared event log for session {session_id}")


def get_event_count(session_id: str) -> int:
    """
    Get count of events for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Number of events for the session
    """
    return len(_event_logs.get(session_id, []))


# Convenience functions for common event types

def log_transcription_received(session_id: str, transcript: str, status: str, confidence: float) -> None:
    """Log transcription received event."""
    log_event(
        session_id,
        "transcription_received",
        {
            "transcript": transcript,
            "status": status,
            "confidence": confidence,
            "transcript_length": len(transcript) if transcript else 0
        }
    )


def log_context_updated(session_id: str, updated_fields: List[str], signals: Optional[Dict] = None) -> None:
    """Log context update event."""
    log_event(
        session_id,
        "context_updated",
        {
            "updated_fields": updated_fields,
            "signal_keys": list(signals.keys()) if signals else []
        }
    )


def log_escalation_triggered(session_id: str, reason: str, priority: str, urgency_score: float) -> None:
    """Log escalation triggered event."""
    log_event(
        session_id,
        "escalation_triggered",
        {
            "reason": reason,
            "priority": priority,
            "urgency_score": urgency_score
        }
    )


def log_rollback_occurred(session_id: str, reason: str, rolled_back_fields: Optional[List[str]] = None) -> None:
    """Log context rollback event."""
    log_event(
        session_id,
        "rollback_occurred",
        {
            "reason": reason,
            "rolled_back_fields": rolled_back_fields or []
        }
    )


def log_api_failure(session_id: str, api_name: str, error_type: str, error_message: str) -> None:
    """Log API failure event."""
    log_event(
        session_id,
        "api_failure",
        {
            "api_name": api_name,
            "error_type": error_type,
            "error_message": error_message
        }
    )

