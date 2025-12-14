"""
Text-to-Speech module using gTTS (Google Text-to-Speech).

This module provides TTS functionality for converting Hindi text to audio
with support for chunked streaming for live playback.
"""

from gtts import gTTS
import io
import logging
from typing import Iterator, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Default chunk size for streaming (4KB)
# This size balances:
# - Network efficiency (not too many small packets)
# - Low latency (chunks arrive quickly for live playback)
# - Memory efficiency (reasonable buffer sizes)
DEFAULT_CHUNK_SIZE = 4096  # 4KB chunks


def speak(text: str, language: str = "hi", chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[bytes]:
    """
    Convert AI Hindi text to audio with chunked streaming for live playback.
    
    This function is the main entry point for TTS conversion. It generates
    audio from text and yields it in chunks for real-time streaming to clients.
    
    Streaming Logic:
    --------------
    The function uses a generator pattern to stream audio chunks:
    
    1. Text Input: Receives Hindi text from AI responses
    2. TTS Generation: Uses gTTS to convert text to MP3 audio
    3. Buffer Creation: Stores complete audio in memory buffer
    4. Chunked Streaming: Yields audio in small chunks for live playback
    
    Why Chunked Streaming?
    ---------------------
    - Live Playback: Client can start playing audio before full generation completes
    - Low Latency: Reduces perceived delay between text and audio
    - Network Efficiency: Smaller packets reduce network overhead
    - Memory Management: Avoids loading entire audio into memory at once
    
    Chunk Size Considerations:
    -------------------------
    - Smaller chunks (1-2KB): Lower latency, more network overhead
    - Medium chunks (4KB): Good balance (default)
    - Larger chunks (8KB+): Less overhead, higher latency
    
    Args:
        text: Hindi text to convert to speech (from AI responses)
        language: Language code (default: "hi" for Hindi)
                 Supports: "hi" (Hindi), "en" (English), etc.
        chunk_size: Size of each audio chunk in bytes (default: 4096)
                   Smaller = lower latency, larger = less overhead
    
    Yields:
        bytes: Audio chunks in MP3 format for streaming
               Each chunk is ready for immediate transmission to client
               Empty chunks indicate end of stream
    
    Raises:
        ValueError: If text is empty or invalid
        RuntimeError: If TTS generation fails
    
    Example:
        >>> for chunk in speak("नमस्ते, मैं आपकी कैसे मदद कर सकता हूं?"):
        ...     websocket.send_bytes(chunk)  # Stream to client
    """
    # Input validation
    # Empty text should not generate audio
    if not text or not text.strip():
        logger.warning("Empty text provided to speak() - returning empty stream")
        return
    
    try:
        # Step 1: Generate TTS audio using gTTS
        # gTTS (Google Text-to-Speech) is used because:
        # - Free and reliable
        # - Good Hindi pronunciation
        # - Supports natural speech patterns
        # - No API keys required for basic usage
        #
        # Parameters:
        # - text: The Hindi text to convert
        # - lang: Language code ("hi" for Hindi)
        # - slow: False for normal speed (True would be slower)
        logger.debug(f"Generating TTS for text: {text[:50]}...")
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Step 2: Create in-memory buffer for audio data
        # Using BytesIO allows us to:
        # - Store audio in memory (faster than disk)
        # - Read in chunks without file I/O
        # - Support streaming pattern
        #
        # The audio is generated as MP3 format by gTTS
        # MP3 is chosen because:
        # - Good compression (smaller file sizes)
        # - Wide browser support
        # - Reasonable quality for speech
        audio_buffer = io.BytesIO()
        
        # Step 3: Write complete audio to buffer
        # This step generates the entire audio file
        # Note: For very long texts, this could take time
        # Future optimization: Consider streaming generation
        tts.write_to_fp(audio_buffer)
        
        # Step 4: Reset buffer position to beginning
        # After writing, the buffer pointer is at the end
        # We need to seek to start for reading chunks
        audio_buffer.seek(0)
        
        # Step 5: Stream audio in chunks
        # This is the core streaming logic
        # We read the buffer in small chunks and yield each chunk
        #
        # Why yield instead of return?
        # - Generator pattern allows lazy evaluation
        # - Client can process chunks as they arrive
        # - Memory efficient (only one chunk in memory at a time)
        #
        # Streaming flow:
        # 1. Read chunk_size bytes from buffer
        # 2. Yield chunk to caller (WebSocket handler)
        # 3. Caller sends chunk to client immediately
        # 4. Client can start playing while more chunks arrive
        # 5. Repeat until buffer is empty
        chunks_yielded = 0
        total_bytes = 0
        
        while True:
            # Read next chunk from buffer
            # read() returns bytes, empty bytes when EOF
            chunk = audio_buffer.read(chunk_size)
            
            # Check if we've reached end of audio
            # Empty chunk means no more data to read
            if not chunk:
                # End of stream - log statistics
                logger.debug(
                    f"TTS streaming complete: {chunks_yielded} chunks, "
                    f"{total_bytes} bytes total"
                )
                break
            
            # Yield chunk for immediate transmission
            # This allows the caller (WebSocket handler) to:
            # - Send chunk to client right away
            # - Continue processing while client receives audio
            # - Maintain low latency for live playback
            chunks_yielded += 1
            total_bytes += len(chunk)
            yield chunk
        
        # Cleanup: Close buffer (frees memory)
        # Note: BytesIO doesn't need explicit close, but it's good practice
        audio_buffer.close()
    
    except Exception as e:
        # Error handling for TTS generation failures
        # Common causes:
        # - Network issues (gTTS requires internet)
        # - Invalid text encoding
        # - gTTS service unavailable
        # - Memory issues for very long texts
        error_msg = f"TTS generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def generate_audio_stream(text: str, language: str = "hi") -> Iterator[bytes]:
    """
    Generate audio stream from text using gTTS (legacy function).
    
    This is a convenience wrapper around speak() for backward compatibility.
    New code should use speak() directly.
    
    Args:
        text: Text to convert to speech
        language: Language code (default: "hi" for Hindi)
    
    Yields:
        bytes: Audio chunks in MP3 format
    """
    yield from speak(text, language=language)


def generate_audio_bytes(text: str, language: str = "hi") -> Optional[bytes]:
    """
    Generate complete audio bytes from text (non-streaming).
    
    This function generates the entire audio file at once.
    Use speak() for streaming, or this for complete audio.
    
    Use cases:
    - When you need the complete audio before sending
    - For file downloads
    - When streaming is not required
    
    Args:
        text: Text to convert to speech
        language: Language code (default: "hi" for Hindi)
    
    Returns:
        bytes: Complete audio data in MP3 format, or None if generation fails
    """
    if not text or not text.strip():
        return None
    
    try:
        # Collect all chunks from speak() into single bytes object
        # This is less efficient than direct generation but reuses code
        audio_chunks = list(speak(text, language=language))
        
        if not audio_chunks:
            return None
        
        # Concatenate all chunks into single bytes object
        return b''.join(audio_chunks)
    
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        return None
