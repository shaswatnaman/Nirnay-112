"""
FastAPI application entry point.

This module sets up the FastAPI application with CORS, health check endpoint,
and WebSocket support.
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.websocket import websocket_call_endpoint

# Initialize FastAPI application
app = FastAPI(
    title="Nirnay API",
    description="API for Nirnay application",
    version="1.0.0"
)

# Configure CORS middleware
# Allow requests from the frontend running on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status object indicating the API is running
    """
    return {"status": "ok"}


@app.get("/admin/session/{session_id}/events")
async def get_session_events(session_id: str):
    """
    Get event log for a session (demo/debug only - no authentication).
    
    This endpoint provides access to the append-only audit log for a session.
    Events include transcription, context updates, escalations, rollbacks, and API failures.
    
    Args:
        session_id: Session identifier
    
    Returns:
        dict: Event log with list of events ordered by timestamp
    """
    from app.logic.event_log import get_session_events
    
    events = get_session_events(session_id)
    
    return {
        "session_id": session_id,
        "event_count": len(events),
        "events": events
    }


@app.websocket("/ws/call")
async def websocket_call(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio call processing.
    
    This endpoint handles audio streaming, transcription, conversation management,
    and TTS response generation. See app.websocket.websocket_call_endpoint for
    detailed implementation.
    
    Args:
        websocket: WebSocket connection instance
    """
    await websocket_call_endpoint(websocket)

