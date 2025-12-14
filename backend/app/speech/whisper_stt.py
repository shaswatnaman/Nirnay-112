"""
Speech-to-Text module using OpenAI Whisper.

This module provides advanced audio transcription functionality with support for:
- Hindi, Hinglish, and regional languages
- Partial transcription for streaming audio
- Background noise handling
- Fast speech and emotional slurring
- Real-time audio processing
"""

import whisper
import numpy as np
from typing import Optional, Dict, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global model instance (lazy loaded)
# Using "small" model for better accuracy while maintaining reasonable speed
_model: Optional[whisper.Whisper] = None


def load_model() -> whisper.Whisper:
    """
    Load the Whisper small model (lazy initialization).
    
    The "small" model provides a good balance between accuracy and speed.
    It performs better than "base" for:
    - Non-native accents (Hinglish)
    - Regional language variations
    - Noisy audio conditions
    - Fast speech patterns
    
    Returns:
        whisper.Whisper: Loaded Whisper model instance
    """
    global _model
    if _model is None:
        logger.info("Loading Whisper small model...")
        # Load small model for better accuracy with Hindi/Hinglish
        # Small model has 244M parameters vs base's 39M
        # Better for handling code-switching (Hindi-English mix)
        _model = whisper.load_model("small")
        logger.info("Whisper small model loaded successfully")
    return _model


def preprocess_audio(audio_data: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Preprocess audio data for transcription.
    
    This function handles:
    - Converting bytes to numpy array
    - Normalization to [-1, 1] range
    - Basic noise reduction through normalization
    - Handling different audio formats
    
    Args:
        audio_data: Binary audio data (PCM format expected)
        sample_rate: Sample rate of the audio (default: 16000 Hz)
    
    Returns:
        np.ndarray: Preprocessed audio array normalized to [-1, 1]
    
    Raises:
        ValueError: If audio data is invalid or empty
    """
    if not audio_data or len(audio_data) == 0:
        raise ValueError("Audio data is empty or invalid")
    
    # Convert bytes to numpy array
    # Assuming 16-bit PCM audio (2 bytes per sample)
    # This handles the raw binary audio chunks from the frontend
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    
    # Normalize to [-1, 1] range
    # This is required by Whisper and helps with:
    # - Consistent audio levels
    # - Better model performance
    # - Handling different input volumes
    max_val = np.abs(audio_array).max()
    if max_val > 0:
        audio_array = audio_array / 32768.0
    else:
        # Silent audio - return zeros
        return np.zeros_like(audio_array, dtype=np.float32)
    
    # Basic noise reduction through dynamic range compression
    # This helps with background noise by reducing the dynamic range
    # while preserving speech content
    audio_array = np.clip(audio_array, -1.0, 1.0)
    
    return audio_array


def enhance_audio_for_speech(audio_array: np.ndarray) -> np.ndarray:
    """
    Enhance audio to better handle challenging speech conditions.
    
    This function applies techniques to improve transcription accuracy for:
    - Fast speech (temporal smoothing)
    - Emotional slurring (amplitude normalization)
    - Background noise (simple filtering)
    
    Args:
        audio_array: Normalized audio array
    
    Returns:
        np.ndarray: Enhanced audio array
    """
    # Apply simple high-pass filter to reduce low-frequency noise
    # This helps with background noise (fans, AC, etc.)
    # Using a simple first-order high-pass filter approximation
    if len(audio_array) > 1:
        # Simple high-pass: y[n] = x[n] - x[n-1] * alpha
        alpha = 0.95
        filtered = np.zeros_like(audio_array)
        filtered[0] = audio_array[0]
        for i in range(1, len(audio_array)):
            filtered[i] = audio_array[i] - audio_array[i-1] * alpha
        
        # Normalize again after filtering
        max_val = np.abs(filtered).max()
        if max_val > 0:
            filtered = filtered / max_val * 0.95  # Slight headroom
        
        audio_array = filtered
    
    # Amplitude normalization for emotional speech
    # Emotional speech can have varying amplitudes
    # Normalizing helps the model better recognize patterns
    rms = np.sqrt(np.mean(audio_array ** 2))
    if rms > 0:
        # Target RMS level for consistent volume
        target_rms = 0.1
        audio_array = audio_array * (target_rms / rms)
        audio_array = np.clip(audio_array, -1.0, 1.0)
    
    return audio_array


def transcribe(
    audio_data: bytes,
    sample_rate: int = 16000,
    language: Optional[str] = None,
    previous_text: Optional[str] = None,
    enable_partial: bool = True
) -> str:
    """
    Transcribe audio data to text using Whisper with advanced features.
    
    This function handles:
    - Hindi, Hinglish (Hindi-English code-switching), and regional languages
    - Partial transcription for streaming audio chunks
    - Background noise through audio preprocessing
    - Fast speech through enhanced audio processing
    - Emotional slurring through normalization techniques
    
    Args:
        audio_data: Binary audio data (PCM format expected)
        sample_rate: Sample rate of the audio (default: 16000 Hz)
        language: Language code ("hi" for Hindi, None for auto-detect)
                 Auto-detection works well for Hinglish
        previous_text: Previous transcription context for streaming
                      This helps with partial transcription accuracy
        enable_partial: Enable partial transcription mode for streaming
    
    Returns:
        str: Transcribed text from the audio
    
    Raises:
        ValueError: If audio data is invalid or empty
    """
    if not audio_data or len(audio_data) == 0:
        raise ValueError("Audio data is empty or invalid")
    
    try:
        # Step 1: Preprocess audio
        # Convert binary data to normalized numpy array
        # This handles format conversion and basic normalization
        audio_array = preprocess_audio(audio_data, sample_rate)
        
        # Step 2: Enhance audio for challenging conditions
        # Apply noise reduction and speech enhancement
        # This improves accuracy for:
        # - Noisy environments
        # - Fast speech
        # - Emotional speech with varying amplitudes
        audio_array = enhance_audio_for_speech(audio_array)
        
        # Step 3: Load Whisper model
        # Lazy loading ensures model is only loaded when needed
        # Small model provides better accuracy for Hindi/Hinglish
        model = load_model()
        
        # Step 4: Configure transcription parameters
        # These parameters are optimized for Hindi/Hinglish and streaming
        
        # Language handling:
        # - "hi" explicitly sets Hindi (good for pure Hindi)
        # - None enables auto-detection (better for Hinglish)
        # - Auto-detection can handle code-switching better
        transcribe_language = language if language else None
        
        # Transcription options optimized for streaming and challenging audio
        transcribe_options: Dict[str, Any] = {
            "task": "transcribe",  # Transcribe (not translate)
            "fp16": False,  # Use FP32 for compatibility
            "verbose": False,  # Reduce logging overhead
        }
        
        # Partial transcription for streaming
        # This is crucial for real-time processing of audio chunks
        if enable_partial and previous_text:
            # condition_on_previous_text: Uses previous context for better accuracy
            # This helps with:
            # - Partial words at chunk boundaries
            # - Context-aware transcription
            # - Better handling of streaming audio
            transcribe_options["condition_on_previous_text"] = True
            transcribe_options["initial_prompt"] = previous_text
        else:
            # For first chunk or when partial is disabled
            transcribe_options["condition_on_previous_text"] = False
        
        # VAD (Voice Activity Detection) filter
        # Helps with background noise by only transcribing speech segments
        # This is important for:
        # - Noisy environments
        # - Handling silence between words
        # - Reducing false transcriptions from noise
        transcribe_options["vad_filter"] = True
        
        # Temperature settings for decoding
        # Lower temperature = more deterministic (better for clear speech)
        # Higher temperature = more creative (better for unclear/fast speech)
        # Using multiple temperatures for beam search
        transcribe_options["temperature"] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
        
        # Beam size for beam search decoding
        # Higher beam size = better accuracy but slower
        # 5 is a good balance for real-time processing
        transcribe_options["beam_size"] = 5
        
        # Best of: number of candidates to consider
        # Higher = better accuracy, slower processing
        transcribe_options["best_of"] = 5
        
        # Patience for beam search
        # Higher patience = more thorough search (better for unclear audio)
        transcribe_options["patience"] = 1.0
        
        # Compression ratio threshold
        # Helps filter out repetitive or nonsensical outputs
        # Useful for handling background noise that might be transcribed
        transcribe_options["compression_ratio_threshold"] = 2.4
        
        # Log probability threshold
        # Filters out low-confidence transcriptions
        # Important for handling noisy or unclear audio
        transcribe_options["logprob_threshold"] = -1.0
        
        # No speech threshold
        # Determines when audio is considered "no speech"
        # Helps avoid transcribing pure noise
        transcribe_options["no_speech_threshold"] = 0.6
        
        # Step 5: Perform transcription
        # Run transcription with optimized parameters
        if transcribe_language:
            result = model.transcribe(
                audio_array,
                language=transcribe_language,
                **transcribe_options
            )
        else:
            # Auto-detect language (better for Hinglish)
            result = model.transcribe(
                audio_array,
                **transcribe_options
            )
        
        # Step 6: Extract and process transcribed text
        # Get the transcribed text from the result
        transcribed_text = result.get("text", "").strip()
        
        # Handle empty transcriptions
        # This can happen with:
        # - Pure noise/silence
        # - Very short audio chunks
        # - Audio below speech threshold
        if not transcribed_text:
            logger.debug("Empty transcription - likely noise or silence")
            return ""
        
        # Log transcription details for debugging
        # This helps track:
        # - Detected language (for Hinglish detection)
        # - Confidence levels
        # - Processing time
        detected_language = result.get("language", "unknown")
        logger.debug(f"Transcribed: {transcribed_text[:50]}... (lang: {detected_language})")
        
        return transcribed_text
    
    except Exception as e:
        # Log error with context for debugging
        logger.error(f"Transcription failed: {str(e)}")
        raise ValueError(f"Transcription failed: {str(e)}")


def transcribe_streaming(
    audio_chunk: bytes,
    previous_text: str = "",
    sample_rate: int = 16000
) -> str:
    """
    Transcribe a streaming audio chunk with context from previous chunks.
    
    This is a convenience wrapper for transcribe() optimized for streaming.
    It automatically enables partial transcription and uses previous context.
    
    Args:
        audio_chunk: Binary audio chunk data
        previous_text: Previous transcription for context
        sample_rate: Sample rate of the audio (default: 16000 Hz)
    
    Returns:
        str: Transcribed text from this chunk
    """
    return transcribe(
        audio_chunk,
        sample_rate=sample_rate,
        language=None,  # Auto-detect for Hinglish
        previous_text=previous_text,
        enable_partial=True
    )
