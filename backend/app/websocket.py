"""
WebSocket endpoint for real-time audio call processing.

This module handles WebSocket connections for audio streaming, transcription,
conversation management, and TTS response generation.
"""

import json
import asyncio
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import WebSocket, WebSocketDisconnect
from app.speech.openai_stt import transcribe_streaming
from app.logic.conversation import get_or_create_session, remove_session
from app.speech.tts import speak
from app.models.schemas import IncidentSummary, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Active WebSocket connections by session ID
# This dictionary tracks all active WebSocket connections
# Key: session_id, Value: WebSocket instance
_active_connections: Dict[str, WebSocket] = {}

# Thread pool executor for CPU-bound operations (transcription)
# This prevents blocking the async event loop
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="transcribe")


async def websocket_call_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for /ws/call.
    
    This endpoint handles:
    - Multiple simultaneous sessions using session IDs
    - Binary audio chunk reception from frontend
    - Audio transcription via Whisper STT
    - Conversation state updates
    - Dynamic AI question generation
    - TTS audio streaming
    - Incident summary JSON transmission
    - Disconnect handling, retries, and error management
    
    Session Management:
    - Each connection requires a session_id (sent as first message)
    - Sessions are isolated and can run concurrently
    - Session state is maintained in ConversationManager
    - Sessions are cleaned up on disconnect
    
    Streaming Flow:
    1. Client sends session_id (JSON message)
    2. Client sends binary audio chunks
    3. Server transcribes each chunk
    4. Server updates conversation state
    5. Server generates AI question
    6. Server streams TTS audio
    7. Server sends incident summary (JSON)
    8. Repeat from step 2
    
    Args:
        websocket: WebSocket connection instance
    """
    session_id: Optional[str] = None
    conversation_manager = None
    
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        logger.info(f"WebSocket connection accepted from {websocket.client}")
        
        # Wait for session initialization message
        # First message should be JSON with session_id
        init_message = await websocket.receive_text()
        
        try:
            init_data = json.loads(init_message)
            session_id = init_data.get("session_id")
            
            if not session_id:
                # Generate new session ID if not provided
                import uuid
                session_id = str(uuid.uuid4())
                logger.info(f"Generated new session_id: {session_id}")
            
            # Get or create conversation manager for this session
            conversation_manager = get_or_create_session(session_id)
            _active_connections[session_id] = websocket
            
            # Send session confirmation
            await websocket.send_json({
                "type": "session_initialized",
                "session_id": session_id,
                "status": "ready"
            })
            logger.info(f"Session {session_id} initialized and ready")
        
        except json.JSONDecodeError:
            # If first message is not JSON, treat as new session
            import uuid
            session_id = str(uuid.uuid4())
            conversation_manager = get_or_create_session(session_id)
            _active_connections[session_id] = websocket
            
            await websocket.send_json({
                "type": "session_initialized",
                "session_id": session_id,
                "status": "ready"
            })
            logger.info(f"Session {session_id} auto-initialized")
        
        # Main message processing loop
        # Handles both binary audio chunks and text messages
        while True:
            try:
                # Receive message (can be binary or text)
                message = await websocket.receive()
                
                # Handle binary audio chunks
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    
                    if not audio_chunk or len(audio_chunk) == 0:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Empty audio chunk received"
                        })
                        continue
                    
                    # Validate audio chunk size (prevent abuse)
                    if len(audio_chunk) > 1024 * 1024:  # 1MB limit
                        await websocket.send_json({
                            "type": "error",
                            "message": "Audio chunk too large"
                        })
                        continue
                    
                    try:
                        # Transcribe audio chunk using Whisper STT with streaming support
                        # This is the core transcription step
                        # Run in executor to avoid blocking the event loop
                        # Whisper transcription is CPU-bound and can take time
                        # Use previous user input as context for better partial transcription
                        previous_text = conversation_manager.get_current_user_input()
                        transcription_result = await asyncio.get_event_loop().run_in_executor(
                            _executor,
                            transcribe_streaming,
                            audio_chunk,
                            previous_text
                        )
                        # `openai_stt.transcribe_streaming` may return either:
                        # - str (legacy behavior)
                        # - {"text": str, "status": "ok"|"silence"|"api_error"|"filtered", "confidence": float}
                        # Keep API contract stable by treating non-ok statuses as "no transcription".
                        transcribed_text = ""
                        if isinstance(transcription_result, dict):
                            status = transcription_result.get("status", "api_error")
                            transcribed_text = (transcription_result.get("text") or "").strip()
                            if status != "ok" or not transcribed_text:
                                logger.warning(
                                    f"Session {session_id}: Transcription not ok (status={status}, "
                                    f"confidence={transcription_result.get('confidence', 0.0):.2f})"
                                )
                                await websocket.send_json({
                                    "type": "audio_processed",
                                    "session_id": session_id,
                                    "transcribed": False,
                                    "status": status
                                })
                                continue
                        else:
                            transcribed_text = (str(transcription_result) if transcription_result else "").strip()
                        
                        if transcribed_text:
                            # Update conversation manager with transcribed text
                            # This accumulates user input across chunks
                            conversation_manager.update_user_input(transcribed_text)
                            
                            logger.info(f"Session {session_id}: Transcribed: {transcribed_text}")
                            
                            # Generate next AI question dynamically
                            # Based on conversation context and history
                            next_question = conversation_manager.generate_next_question()
                            
                            # Stream TTS audio for the AI question
                            # This sends audio chunks to the frontend for live playback
                            # Using speak() for chunked streaming with low latency
                            tts_chunks_sent = 0
                            for audio_chunk_tts in speak(next_question, language="hi"):
                                if audio_chunk_tts:
                                    # Send binary audio chunk immediately for live playback
                                    # Client can start playing while more chunks arrive
                                    await websocket.send_bytes(audio_chunk_tts)
                                    tts_chunks_sent += 1
                            
                            # Send incident summary as JSON after processing chunk
                            # This provides real-time updates to the frontend
                            incident_summary = conversation_manager.get_incident_summary()
                            summary_dict = {
                                "type": "incident_summary",
                                "session_id": session_id,
                                "summary": incident_summary
                            }
                            
                            await websocket.send_json(summary_dict)
                            logger.info(f"Session {session_id}: Sent incident summary")
                        
                        else:
                            # Empty transcription - send acknowledgment
                            await websocket.send_json({
                                "type": "audio_processed",
                                "session_id": session_id,
                                "transcribed": False
                            })
                    
                    except ValueError as e:
                        # Invalid audio data
                        error_response = ErrorResponse(
                            error="invalid_audio",
                            message=str(e),
                            session_id=session_id
                        )
                        await websocket.send_json(error_response.dict())
                        logger.warning(f"Session {session_id}: Invalid audio - {str(e)}")
                    
                    except Exception as e:
                        # Transcription error - send error but continue
                        error_response = ErrorResponse(
                            error="transcription_error",
                            message=f"Transcription failed: {str(e)}",
                            session_id=session_id
                        )
                        await websocket.send_json(error_response.dict())
                        logger.error(f"Session {session_id}: Transcription error - {str(e)}")
                
                # Handle text messages (for control commands)
                elif "text" in message:
                    text_data = message["text"]
                    
                    try:
                        command = json.loads(text_data)
                        command_type = command.get("type")
                        
                        if command_type == "ping":
                            # Health check / keepalive
                            await websocket.send_json({
                                "type": "pong",
                                "session_id": session_id
                            })
                        
                        elif command_type == "reset":
                            # Reset conversation
                            if conversation_manager:
                                conversation_manager.reset()
                                await websocket.send_json({
                                    "type": "conversation_reset",
                                    "session_id": session_id
                                })
                        
                        elif command_type == "get_summary":
                            # Get current summary
                            if conversation_manager:
                                summary = conversation_manager.get_incident_summary()
                                await websocket.send_json({
                                    "type": "incident_summary",
                                    "session_id": session_id,
                                    "summary": summary
                                })
                    
                    except json.JSONDecodeError:
                        # Invalid JSON - ignore
                        pass
            
            except asyncio.CancelledError:
                # Connection cancelled
                logger.info(f"Session {session_id}: Connection cancelled")
                break
            
            except Exception as e:
                # Unexpected error - log and continue
                logger.error(f"Session {session_id}: Unexpected error in message loop - {str(e)}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Processing error: {str(e)}",
                        "session_id": session_id
                    })
                except:
                    # Can't send error - connection likely broken
                    break
    
    except WebSocketDisconnect:
        # Normal disconnect - clean up session
        logger.info(f"Session {session_id}: Client disconnected")
    
    except Exception as e:
        # Fatal error - log and clean up
        logger.error(f"Session {session_id}: Fatal error - {str(e)}")
    
    finally:
        # Cleanup: Remove session and connection
        # This ensures no memory leaks and proper resource cleanup
        if session_id:
            if session_id in _active_connections:
                del _active_connections[session_id]
            
            # Optionally remove conversation manager
            # In production, you might want to persist sessions
            # remove_session(session_id)
            
            logger.info(f"Session {session_id}: Cleaned up")

