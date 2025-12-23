"""
Speech-to-Text module using OpenAI's official API.

This module provides real-time audio transcription with support for:
- Hindi, Hinglish, and regional languages
- Partial transcription for streaming audio
- Background noise handling
- Fast speech and emotional slurring
- Real-time audio processing
- Context-aware conversation understanding

Replaces Whisper (local model) due to:
- Poor accuracy for Hindi/Hinglish
- Inability to handle emotional emergency speech
- Poor performance with Indian regional accents
- High latency for real-time streaming
"""

import os
import io
import re
import json
import base64
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Iterator, Literal
from openai import OpenAI
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# API key should be set in environment variable OPENAI_API_KEY
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """
    Get or create OpenAI client instance (lazy initialization).
    
    Returns:
        OpenAI: OpenAI client instance
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it to use OpenAI Speech-to-Text API."
            )
        _client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    return _client


def preprocess_audio(audio_data: bytes, sample_rate: int = 16000) -> bytes:
    """
    Preprocess audio data for OpenAI API.
    
    OpenAI API expects:
    - PCM audio format
    - 16-bit signed integers
    - Sample rate: 16000 Hz (or 24000 Hz)
    - Mono channel
    
    Args:
        audio_data: Binary audio data (PCM format, Int16)
        sample_rate: Sample rate of the audio (default: 16000 Hz)
    
    Returns:
        bytes: Preprocessed audio data ready for OpenAI API
    
    Raises:
        ValueError: If audio data is invalid or empty
    """
    if not audio_data or len(audio_data) == 0:
        raise ValueError("Audio data is empty or invalid")
    
    # Ensure audio_data length is even (int16 requires 2 bytes per sample)
    if len(audio_data) % 2 != 0:
        logger.warning(f"Audio data length ({len(audio_data)}) is not even, truncating last byte")
        audio_data = audio_data[:-1]
    
    if len(audio_data) < 2:
        raise ValueError("Audio data too short (less than 2 bytes)")
    
    # Validate audio format
    # Convert to numpy array to check values
    try:
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Check if array is empty
        if len(audio_array) == 0:
            raise ValueError("Audio data is empty after conversion")
        
        # Check if audio has actual signal (not just noise floor)
        max_val = np.abs(audio_array).max()
        if max_val == 0:
            logger.warning("Audio is completely silent (max_val=0)")
            raise ValueError("Audio data is completely silent")
        
        # Calculate RMS to detect silence with background noise
        # Very low RMS indicates silence (even if max_val > 0 due to noise)
        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        # Normalize RMS to Int16 range (0 to 32768)
        rms_normalized = rms / 32768.0# Threshold: if RMS is less than 0.01% of max Int16 value, consider it silence
        # Very low threshold to allow quiet speech (emergency calls can be quiet, microphones vary)
        # This filters out only the quietest background noise that might cause hallucinations
        # Lowered significantly to allow real speech through
        SILENCE_RMS_THRESHOLD = 0.0001  # 0.01% of full scale (very permissive for quiet speech)
        if rms_normalized < SILENCE_RMS_THRESHOLD:
            logger.warning(f"Audio is too quiet (likely silence): RMS={rms_normalized:.6f}, max_val={max_val}")
            raise ValueError(f"Audio is too quiet (likely silence): RMS={rms_normalized:.6f}")
        
        # AGGRESSIVE GAIN BOOSTING: Audio is very quiet, boost it significantly
        # OpenAI needs louder audio to transcribe accurately (hallucinations occur with quiet audio)
        # Target: boost to ~30-50% of full scale for optimal transcription
        max_val_normalized = max_val / 32768.0
        gain_multiplier = 1.0
        
        if max_val_normalized < 0.05:  # Very quiet (< 5% of full scale)
            # Boost to ~30% of full scale
            gain_multiplier = 0.30 / max_val_normalized if max_val_normalized > 0 else 10.0
            gain_multiplier = min(gain_multiplier, 20.0)  # Cap at 20x to avoid distortion
            logger.info(f"Boosting very quiet audio: max_val={max_val} ({max_val_normalized:.2%}), gain={gain_multiplier:.2f}x")
        elif max_val_normalized < 0.15:  # Moderately quiet (< 15% of full scale)
            # Boost to ~40% of full scale
            gain_multiplier = 0.40 / max_val_normalized if max_val_normalized > 0 else 5.0
            gain_multiplier = min(gain_multiplier, 10.0)  # Cap at 10x
            logger.info(f"Boosting quiet audio: max_val={max_val} ({max_val_normalized:.2%}), gain={gain_multiplier:.2f}x")
        elif max_val_normalized < 0.30:  # Slightly quiet (< 30% of full scale)
            # Boost to ~50% of full scale
            gain_multiplier = 0.50 / max_val_normalized if max_val_normalized > 0 else 2.0
            gain_multiplier = min(gain_multiplier, 3.0)  # Cap at 3x
            logger.debug(f"Boosting slightly quiet audio: max_val={max_val} ({max_val_normalized:.2%}), gain={gain_multiplier:.2f}x")
        
        # Apply gain boost if needed
        if gain_multiplier > 1.0:
            # Convert to float32 for processing
            audio_float = audio_array.astype(np.float32) * gain_multiplier
            # Clip to prevent overflow
            audio_float = np.clip(audio_float, -32768.0, 32767.0)
            # Convert back to int16
            audio_array = audio_float.astype(np.int16)
            # Convert back to bytes
            audio_data = audio_array.tobytes()
            
            # Log boosted audio metrics
            boosted_max = np.abs(audio_array).max()
            boosted_rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            boosted_rms_normalized = boosted_rms / 32768.0# Audio is valid (and potentially boosted), return
        return audio_data
        
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to validate audio data: {e}, audio_data length: {len(audio_data)}")
        raise ValueError(f"Invalid audio data format: {e}")


def transcribe(
    audio_data: bytes,
    sample_rate: int = 16000,
    language: Optional[str] = None,
    previous_text: Optional[str] = None,
    enable_partial: bool = True
) -> Dict[str, Any]:
    """
    Transcribe audio data using OpenAI's Speech-to-Text API with retry logic.
    
    Naming Philosophy:
    - We use "external_model_api" instead of "ml_model" to emphasize that
      this is an external API call, not a local ML model.
    - External model API clearly describes the dependency: we're calling
      an external service (OpenAI), not using a local model.
    
    This function uses OpenAI's gpt-4o-mini-transcribe external model API (cloud-based) which provides:
    - Superior accuracy for Hindi/Hinglish
    - Better handling of emotional/fast speech
    - Support for Indian regional accents
    - Lower latency for real-time streaming
    
    Retry Logic:
    - Maximum 2 retries with exponential backoff (1s, 2s delays)
    - Retries are capped at 2 to prevent excessive API usage and latency
    - After 2 retries, we assume the failure is persistent (network issue, API outage, etc.)
    - Exponential backoff helps with transient network issues while avoiding rapid retry storms
    
    Args:
        audio_data: Binary audio data (PCM format, Int16, 16kHz, mono)
        sample_rate: Sample rate of the audio (default: 16000 Hz)
        language: Language code (e.g., "hi" for Hindi). If None, auto-detects.
        previous_text: Previous transcript for context (improves accuracy)
        enable_partial: Whether to return partial transcripts (for streaming)
    
    Returns:
        Dict with keys:
            - text: str - Transcribed text (empty if failed)
            - status: Literal["ok", "silence", "api_error", "filtered"] - Status of transcription
            - confidence: float - Confidence score (0.0-1.0)
    
    Raises:
        ValueError: If audio data is invalid (before retries)
    """
    if not audio_data or len(audio_data) == 0:
        raise ValueError("Audio data is empty or invalid")
    
    # Retry logic: max 2 retries with exponential backoff
    # Retries are capped at 2 to prevent excessive API usage and latency accumulation.
    # After 2 retries, we assume persistent failure (network issue, API outage, etc.)
    # Exponential backoff (1s, 2s) helps with transient network issues while avoiding retry storms
    MAX_RETRIES = 2
    base_delay = 1.0  # Base delay in seconds
    
    last_error = None
    
    for attempt in range(MAX_RETRIES + 1):  # 0, 1, 2 (3 attempts total)
        try:
            # Preprocess audio - may raise ValueError for silence
            try:
                processed_audio = preprocess_audio(audio_data, sample_rate)
            except ValueError as silence_error:
                # Silence detected during preprocessing
                error_msg = str(silence_error)
                if "silent" in error_msg.lower() or "quiet" in error_msg.lower() or "too quiet" in error_msg.lower():
                    logger.debug(f"Silence detected during preprocessing: {error_msg}")
                    return {
                        "text": "",
                        "status": "silence",
                        "confidence": 0.0
                    }
                # Other ValueError (invalid format, etc.) - don't retry
                raise
            
            # Create a file-like object from audio bytes
            # OpenAI API expects a file-like object with proper audio format
            # For PCM audio, we need to create a WAV file format
            # WAV header: 44 bytes + PCM data
            import struct
            
            # Create WAV file in memory
            # WAV format: RIFF header + fmt chunk + data chunk
            num_samples = len(processed_audio) // 2  # Int16 = 2 bytes per sample
            wav_file = io.BytesIO()
            
            # Write WAV header
            wav_file.write(b'RIFF')
            wav_file.write(struct.pack('<I', 36 + num_samples * 2))  # File size - 8
            wav_file.write(b'WAVE')
            wav_file.write(b'fmt ')
            wav_file.write(struct.pack('<I', 16))  # fmt chunk size
            wav_file.write(struct.pack('<H', 1))  # Audio format (1 = PCM)
            wav_file.write(struct.pack('<H', 1))  # Number of channels (1 = mono)
            wav_file.write(struct.pack('<I', sample_rate))  # Sample rate
            wav_file.write(struct.pack('<I', sample_rate * 2))  # Byte rate
            wav_file.write(struct.pack('<H', 2))  # Block align
            wav_file.write(struct.pack('<H', 16))  # Bits per sample
            wav_file.write(b'data')
            wav_file.write(struct.pack('<I', num_samples * 2))  # Data chunk size
            wav_file.write(processed_audio)  # PCM data
            
            wav_file.seek(0)
            wav_file.name = "audio.wav"  # Required for OpenAI API to detect format
            
            # Get OpenAI client
            client = get_client()
            
            # Prepare transcription parameters
            # OpenAI gpt-4o-mini-transcribe API supports:
            # - language: Optional language code (e.g., "hi" for Hindi)
            # - prompt: Optional text prompt for context (improves accuracy)
            # - response_format: "json", "text", "verbose_json", "vtt", "srt"
            # - temperature: 0.0 to 1.0 (lower = more deterministic)
            transcribe_params: Dict[str, Any] = {
                "model": "gpt-4o-mini-transcribe",  # Better accuracy for Hindi/Hinglish, accents, noisy audio, and emotional speech
                "file": wav_file,
                "response_format": "json",  # gpt-4o-mini-transcribe only supports 'json' or 'text' (not 'verbose_json')
                "temperature": 0.2,  # Slightly higher temperature (like ChatGPT) for better handling of emotional/fast speech
            }
            
            # Use the provided language parameter
            # User wants Hindi transcription (like ChatGPT), so use Hindi when requested
            if language:
                transcribe_params["language"] = language
            else:
                transcribe_params["language"] = "hi"  # Default to Hindi for Hindi transcription
            
            # Add prompt for context (improves accuracy for emergency speech)
            # ONLY use previous transcript - do NOT add emergency keywords as they cause hallucinations
            if previous_text:
                # Use previous transcript as prompt for better context (like ChatGPT)
                # This helps with continuity and improves accuracy
                transcribe_params["prompt"] = previous_text[:500]  # Increased to 500 chars for better context
            # DO NOT add emergency context phrases - they cause OpenAI to hallucinate those words
            
            # Call OpenAI API
            logger.debug(f"Calling OpenAI gpt-4o-mini-transcribe API with {len(processed_audio)} bytes of audio, language={transcribe_params.get('language', 'auto')}, prompt_length={len(transcribe_params.get('prompt', ''))}")
            
            # Log audio quality metrics before API call
            audio_array = np.frombuffer(processed_audio, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            max_val = np.max(np.abs(audio_array))
            rms_normalized = rms / 32768.0 if max_val > 0 else 0.0
            
            try:
                api_call_start = time.time()
                response = client.audio.transcriptions.create(**transcribe_params)
                api_call_duration = time.time() - api_call_start
            except Exception as api_error:
                api_call_duration = time.time() - api_call_start if 'api_call_start' in locals() else 0.0
                # Log detailed error information
                error_type = type(api_error).__name__
                error_msg = str(api_error)
                last_error = api_error
                
                # Check if we should retry (network errors, rate limits, etc.)
                # Don't retry on authentication errors or invalid requests
                should_retry = (
                    attempt < MAX_RETRIES and
                    not ("authentication" in error_msg.lower() or 
                         "invalid" in error_msg.lower() or
                         "unauthorized" in error_msg.lower())
                )
                if should_retry:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s
                    logger.warning(
                        f"OpenAI API call failed (attempt {attempt + 1}/{MAX_RETRIES + 1}): "
                        f"{error_type}: {error_msg}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue  # Retry
                else:
                    # No more retries or non-retryable error
                    logger.error(f"OpenAI API call failed: {error_type}: {error_msg}", exc_info=True)
                    # Return API error status
                    return {
                        "text": "",
                        "status": "api_error",
                        "confidence": 0.0
                    }
            
            # Extract transcribed text
            # For 'json' format, response is a dict with 'text' key
            # For 'text' format, response is a string
            if isinstance(response, dict):
                transcribed_text = response.get('text', '').strip()
                detected_language = response.get('language', 'unknown')
            elif hasattr(response, 'text'):
                transcribed_text = response.text.strip() if response.text else ""
                detected_language = getattr(response, 'language', 'unknown')
            else:
                # Fallback: treat as string
                transcribed_text = str(response).strip() if response else ""
                detected_language = 'unknown'
            
            
            # Log transcription details
            logger.info(
                f"Transcribed: '{transcribed_text[:100] if transcribed_text else '(empty)'}'... "
                f"(lang: {detected_language}, requested: {transcribe_params.get('language', 'auto')})"
            )
            # Handle empty transcriptions
            if not transcribed_text:
                logger.debug(
                    f"Empty transcription - audio array length: {len(processed_audio)}, "
                    f"detected_language: {detected_language}"
                )
                return {
                    "text": "",
                    "status": "silence",
                    "confidence": 0.0
                }
            
            # Validate transcription to filter out hallucinations/nonsense
            # OpenAI API sometimes returns false transcriptions for silence/noise
            if transcribed_text:# BEFORE filtering, check if transcription contains valid incident keywords
                # If it does, extract unique information even if repetitive (real panic speech)
                from app.nlp.india_keywords import (
                    MEDICAL_KEYWORDS, ROAD_ACCIDENT_KEYWORDS, FIRE_KEYWORDS, 
                    CRIME_KEYWORDS, DOMESTIC_KEYWORDS, NATURAL_DISASTER_KEYWORDS,
                    URGENCY_KEYWORDS
                )
                all_keywords = (
                    list(MEDICAL_KEYWORDS) + list(ROAD_ACCIDENT_KEYWORDS) + 
                    list(FIRE_KEYWORDS) + list(CRIME_KEYWORDS) + 
                    list(DOMESTIC_KEYWORDS) + list(NATURAL_DISASTER_KEYWORDS) +
                    list(URGENCY_KEYWORDS)
                )
                text_lower = transcribed_text.lower()
                # Check for keywords of any length (including short ones like "आग" = fire, 2 chars)
                # Remove spaces and punctuation for better matching (handles concatenated text)
                text_normalized = text_lower.replace(' ', '').replace(',', '').replace('।', '').replace('.', '').replace('!', '').replace('?', '')
                contains_valid_keywords = False
                matched_keyword = None
                
                # Check if any keyword appears in the text (as substring or word)
                # Prioritize longer keywords first (more specific matches)
                sorted_keywords = sorted(all_keywords, key=len, reverse=True)
                for kw in sorted_keywords:
                    kw_lower = kw.lower()
                    kw_normalized = kw_lower.replace(' ', '')
                    # Check as substring in both original and normalized text
                    # This handles: "कोड़ीमें आग लग गई" and "कोड़ीमेंआगलगगई"
                    if kw_lower in text_lower or kw_normalized in text_normalized:
                        contains_valid_keywords = True
                        matched_keyword = kw
                        break
                
                # Check for repetitive patterns (hallucination indicator)
                words = transcribed_text.split()
                # Initialize repetition variables (needed for later checks even if words <= 2)
                max_count = 0
                repetition_ratio = 0.0
                if len(words) > 2:
                    word_counts = {}
                    for word in words:
                        word_counts[word] = word_counts.get(word, 0) + 1
                    max_count = max(word_counts.values()) if word_counts else 0
                    repetition_ratio = max_count / len(words) if len(words) > 0 else 0
                    
                    # URGENT CHECK: If a single word appears 3+ times and is >12% of text
                    # BUT: If transcription contains valid incident keywords, extract unique info instead of filtering
                    if max_count >= 3 and repetition_ratio > 0.12:
                        if contains_valid_keywords:
                            # Real panic speech with valid keywords - extract unique information
                            # Get unique words/phrases (remove duplicates while preserving order)
                            unique_words = []
                            seen_words = set()
                            for word in words:
                                if word not in seen_words:
                                    unique_words.append(word)
                                    seen_words.add(word)
                            # Reconstruct with unique words only (first occurrence of each)
                            extracted_text = ' '.join(unique_words)
                            logger.info(
                                f"Extracted unique info from repetitive transcription (contains valid keywords): "
                                f"'{extracted_text[:100]}' (original had {len(words)} words, extracted {len(unique_words)} unique)"
                            )
                            return {
                                "text": extracted_text,
                                "status": "ok",
                                "confidence": 0.85  # Slightly lower confidence due to extraction
                            }  # Return extracted unique information
                        
                        # No valid keywords - likely hallucination, filter it
                        logger.warning(
                            f"Filtered repetitive transcription (urgent word check): "
                            f"'{transcribed_text[:100]}' (word repeats {max_count} times, ratio: {repetition_ratio:.2f})"
                        )
                    return {
                            "text": "",
                            "status": "filtered",
                            "confidence": 0.0
                        }  # Filter out hallucination immediately
                
                # Check for phrase-level repetition first (more accurate for detecting hallucinations)
                # BUT: If transcription contains valid incident keywords, extract unique info instead of filtering
                # This handles real panic speech where users repeat themselves
                text_normalized = transcribed_text.replace(',', ' ').replace('।', ' ').replace('.', ' ').replace('!', ' ').replace('?', ' ').strip()
                phrases = [p.strip() for p in text_normalized.split()
                if p.strip()]
                
                # Check if any phrase repeats (potential repetition)
                phrase_repeats = False
                for phrase_len in [4, 3, 2]:
                    if len(phrases) >= phrase_len * 2:
                        for i in range(min(3, len(phrases) - phrase_len + 1)):
                            test_phrase = ' '.join(phrases[i:i+phrase_len])
                            if text_normalized.lower().count(test_phrase.lower()) >= 2:

                                phrase_repeats = True
                    break  # Found a match, no need to check shorter phrases
                if phrase_repeats:
                    break
                
                # If phrase repeats AND contains valid keywords, extract unique info
                if phrase_repeats and contains_valid_keywords:
                    # Real panic speech - extract unique words/phrases
                    unique_words = []
                    seen_words = set()
                    for word in words:
                        if word not in seen_words:

                            unique_words.append(word)
                            seen_words.add(word)
                    extracted_text = ' '.join(unique_words)
                    logger.info(
                        f"Extracted unique info from repetitive panic speech: "
                        f"'{extracted_text[:100]}' (original: {len(words)} words, extracted: {len(unique_words)} unique)"
                    )
                    return {
                        "text": extracted_text,
                        "status": "ok",
                        "confidence": 0.85  # Slightly lower confidence due to extraction
                    }
                
                # SIMPLE CHECK: If any 2-4 word phrase repeats 3+ times, filter immediately (only if no valid keywords)
                # This catches obvious hallucinations like "आपको परतकते हैं" or "प्रस्तुत का नाम करते हैं" repeating
                # Also check the original text (with punctuation) for concatenated phrases
                if len(phrases) >= 4:  # Lowered from 6 to catch shorter hallucinations
                    for phrase_len in [4, 3, 2]:
                        if len(phrases) >= phrase_len * 2:  # Lowered from 3 to catch 2+ repetitions

                            # Check all possible phrases in normalized text
                            for start_idx in range(len(phrases) - phrase_len + 1):
                                test_phrase = ' '.join(phrases[start_idx:start_idx + phrase_len])
                                # Check in normalized text (spaces)
                                phrase_repeats_norm = text_normalized.lower().count(test_phrase.lower())
                                # Also check in original text (might be concatenated without spaces)
                                phrase_repeats_orig = transcribed_text.lower().count(test_phrase.lower().replace(' ', ''))
                                # Use the higher count (handles both spaced and concatenated)
                                phrase_repeats = max(phrase_repeats_norm, phrase_repeats_orig)
                                if phrase_repeats >= 2:  # Lowered to 2+ repetitions to catch more hallucinations like "अपर अपर अपर"
                                    logger.warning(
                                        f"Filtered repetitive transcription (simple phrase check): "
                                        f"'{transcribed_text[:100]}' (phrase: '{test_phrase[:50]}', repeats: {phrase_repeats})"
                                    )
                                    return {
                                        "text": "",
                                        "status": "filtered",
                                        "confidence": 0.0
                                    }  # Filter out hallucination
                        break  # Checked all positions for this phrase length
                
                # More aggressive filtering: check for phrase repetition with fewer words
                if len(phrases) >= 2:
                    # Check if first 1-5 words form a phrase that repeats (increased from 3 to catch longer phrases)
                    for phrase_len in [5, 4, 3, 2, 1]:  # Try longer phrases first, but also check single words
                        if len(phrases) >= phrase_len * 2:

                            first_phrase = ' '.join(phrases[:phrase_len])
                            # Count how many times this phrase appears (case-insensitive)
                            phrase_repeats = text_normalized.lower().count(first_phrase.lower())
                            # Stricter: if phrase repeats 2+ times AND it's more than 20% of the text, filter it (lowered from 25%)
                            phrase_ratio = (phrase_repeats * phrase_len) / len(phrases) if len(phrases) > 0 else 0

                            if phrase_repeats >= 2 and phrase_ratio > 0.20:  # Phrase repeats 2+ times AND >20% of text
                                logger.warning(
                                    f"Filtered repetitive transcription (phrase repetition): "
                                    f"'{transcribed_text[:100]}' (phrase: '{first_phrase[:50]}', repeats: {phrase_repeats}, ratio: {phrase_ratio:.2f})"
                                )
                                return {
                                    "text": "",
                                    "status": "filtered",
                                    "confidence": 0.0
                                    }  # Filter out hallucination
                                break  # Found a match, no need to check shorter phrases
                    
                    # Additional check: look for any phrase (not just first) that repeats 2+ times
                    # This catches cases like "कुत्ते ने काट लिया, आपको कुत्ते ने काट लिया" or "आपको परतकते हैं"
                    for phrase_len in [5, 4, 3, 2]:
                        if len(phrases) >= phrase_len * 2:

                            # Check all possible phrases of this length (increased range to catch more)
                            for start_idx in range(min(10, len(phrases) - phrase_len * 2 + 1)):  # Check first 10 positions
                                test_phrase = ' '.join(phrases[start_idx:start_idx + phrase_len])
                                phrase_repeats = text_normalized.lower().count(test_phrase.lower())
                                phrase_ratio = (phrase_repeats * phrase_len) / len(phrases) if len(phrases) > 0 else 0


                                # Lower threshold to 20% to catch more hallucinations
                                if phrase_repeats >= 2 and phrase_ratio > 0.20:
                                    logger.warning(
                                        f"Filtered repetitive transcription (any phrase repetition): "
                                        f"'{transcribed_text[:100]}' (phrase: '{test_phrase[:50]}', repeats: {phrase_repeats}, ratio: {phrase_ratio:.2f})"
                                    )
                                    return {
                                        "text": "",
                                        "status": "filtered",
                                        "confidence": 0.0
                                    }  # Filter out hallucination
                                break  # Checked all positions for this phrase length
                
                # Also filter if word-level repetition is very high (>30% AND word appears 2+ times)
                # This catches cases like "आपको परतकते हैं आपको" with 40% repetition (word appears 2+ times)
                # BUT: Only filter if no valid keywords found (valid speech can have some repetition)
                # AND: Require max_count >= 2 (word must actually repeat, not just appear once)
                if repetition_ratio > 0.30 and max_count >= 2 and not contains_valid_keywords:
                    logger.warning(
                        f"Filtered repetitive transcription (word repetition): "
                        f"'{transcribed_text[:100]}' (repetition ratio: {repetition_ratio:.2f}, max_count: {max_count})"
                    )
                    return {
                        "text": "",
                        "status": "filtered",
                        "confidence": 0.0
                    }  # Filter out hallucination
                
                # Check for known hallucination patterns (common OpenAI Whisper hallucinations)
                # These are words/phrases that frequently appear in hallucinations
                HALLUCINATION_PATTERNS = [
                    "परवाप", "प्रसुपादा", "प्रस्तुत्र", "प्रसुपादा", "परकनात",
                    "नमनमन", "नमनमनमन",  # Common hallucination pattern
                    "पड़पर", "पड़परमेरे",  # Common concatenated hallucination
                    "पड़कल", "पड़कलपरत", "पड़कलपड़कल",  # New patterns seen in logs (like "पड़कलपरतपड़कल...")
                    "prasupada", "parvap", "praknat", "prastutr"
                ]
                
                # Common short hallucination phrases (often appear when there's silence/noise)
                # These are short phrases that OpenAI frequently hallucinates
                SHORT_HALLUCINATION_PHRASES = [
                    "आपको।", "आपको",  # Just "to you" - common hallucination
                    "मेरे को", "मेरे को चोर", "मेरे को चोर।",  # "thief to me" - nonsensical
                    "चोर।", "चोर",  # Just "thief" - incomplete
                    "पानी।", "पानी",  # Just "water" - common hallucination
                ]
            
                # Also check for suspicious character repetition patterns (like "नमनमनमन" or "पड़कलपड़कल")
                # Check for 2-4 character sequences repeating 3+ times (increased from 2-3 to catch "पड़कल")
                suspicious_repeats = re.findall(r'(.{2,4})\1{2,}', transcribed_text)
                if suspicious_repeats:
                    logger.warning(
                        f"Filtered transcription with suspicious character repetition: "
                        f"'{transcribed_text[:100]}' (repeating patterns: {suspicious_repeats[:3]})"
                    )
                    return {
                        "text": "",
                        "status": "filtered",
                        "confidence": 0.0
                    }  # Filter out hallucination
            
                # Check for concatenated nonsense patterns (like "पड़कलपरतपड़कल" - no spaces, repeating)
                # If text has very few spaces and contains repeating character sequences, it's likely a hallucination
                if len(transcribed_text) > 20:
                    space_count = transcribed_text.count(' ')
                    char_repeats = len(re.findall(r'(.{3,5})\1+', transcribed_text.replace(' ', '')))
                    if space_count < len(transcribed_text) * 0.1 and char_repeats >= 2:  # Less than 10% spaces and 2+ repeating patterns
                        logger.warning(
                            f"Filtered concatenated hallucination: "
                            f"'{transcribed_text[:100]}' (spaces: {space_count}/{len(transcribed_text)}, repeating patterns: {char_repeats})"
                        )
                    return {
                            "text": "",
                            "status": "filtered",
                            "confidence": 0.0
                        }
            
                # Check if transcription contains known hallucination patterns
                text_lower = transcribed_text.lower()
                # Count how many times each pattern appears (not just if it exists)
                total_pattern_occurrences = sum(text_lower.count(pattern.lower()) for pattern in HALLUCINATION_PATTERNS)
            
                # If hallucination pattern appears 2+ times total, filter it out
                # This catches cases like "परवाप परवाप" or "परवापदोस्त को कुट्टे" where pattern appears multiple times
                if total_pattern_occurrences >= 2:
                    logger.warning(
                        f"Filtered transcription with hallucination patterns: "
                        f"'{transcribed_text[:100]}' (pattern occurrences: {total_pattern_occurrences})"
                    )
                    return {
                        "text": "",
                        "status": "filtered",
                        "confidence": 0.0
                    }  # Filter out hallucination
            
                # Check for suspicious concatenated text (common hallucination pattern)
                # Long transcriptions with many concatenated words (no spaces) are likely hallucinations
                # Example: "पड़परमेरे दोस्त का किसी बातकिसी ने पीनस का लियादेलीने"
                if len(transcribed_text) > 30:  # Long transcription
                    # Also check for repeated phrases that are concatenated (like "हमेरा नाम नहीं हैहमेरा नाम नहीं है")
                    # If text is long and has a phrase that appears 2+ times when we add spaces, it's likely concatenated repetition
                    text_with_spaces = transcribed_text.replace('है', ' है ').replace('नाम', ' नाम ').replace('नहीं', ' नहीं ').replace('कुट्टे', ' कुट्टे ').replace('गाट', ' गाट ')
                    # Check if any 3-5 word phrase appears 2+ times in the text
                    phrases_check = text_with_spaces.split()
                    if len(phrases_check) >= 6:
                        for plen in [5, 4, 3]:
                            if len(phrases_check) >= plen * 2:

                                for i in range(min(3, len(phrases_check) - plen + 1)):
                                    test_phrase = ' '.join(phrases_check[i:i+plen])
                                    if text_with_spaces.lower().count(test_phrase.lower()) >= 2:

                                        # Phrase repeats 2+ times - likely concatenated hallucination
                                        logger.warning(
                                            f"Filtered transcription with concatenated phrase repetition: "
                                            f"'{transcribed_text[:100]}' (phrase: '{test_phrase[:50]}')"
                                        )
                                        return {
                                            "text": "",
                                            "status": "filtered",
                                            "confidence": 0.0
                                        }  # Filter out concatenated hallucination
                                break  # Found a match, no need to check shorter phrases
                    
                    # Count spaces vs total length
                    space_count = transcribed_text.count(' ')
                    space_ratio = space_count / len(transcribed_text) if len(transcribed_text) > 0 else 0

                    # If very few spaces (< 8% of text) and text is long (>40 chars), it's likely concatenated nonsense
                    # Lowered threshold and length to catch more cases like "हमेरा नाम नहीं हैहमेरा नाम नहीं है"
                    if space_ratio < 0.08 and len(transcribed_text) > 40:

                        logger.warning(
                            f"Filtered transcription with suspicious concatenation: "
                            f"'{transcribed_text[:100]}' (space_ratio: {space_ratio:.3f})"
                        )
                    return {
                            "text": "",
                            "status": "filtered",
                            "confidence": 0.0
                        }  # Filter out concatenated hallucination
            
                # Check for very short nonsense transcriptions (common hallucinations)
                # If transcription is very short (< 3 chars) and doesn't look like valid Hindi/English
                if len(transcribed_text) < 3:
                    logger.warning(f"Filtered very short transcription (likely noise): '{transcribed_text}'")
                    return {
                        "text": "",
                        "status": "filtered",
                        "confidence": 0.0
                    }
                
                # AGGRESSIVE FILTER: Short transcriptions (< 20 chars) without valid keywords are likely hallucinations
                # OpenAI often hallucinates short phrases like "आपको।" or "मेरे को चोर।" when there's silence/noise
                
                # First check if it matches known short hallucination phrases exactly
                text_stripped = transcribed_text.strip()
                if text_stripped in SHORT_HALLUCINATION_PHRASES:
                    logger.warning(
                        f"Filtered known short hallucination phrase: '{transcribed_text}'"
                    )
                    return {

                        "text": "",
                        "status": "filtered",
                        "confidence": 0.0
                    }
                
                # Filter short transcriptions (< 20 chars) without valid keywords ONLY if they match known hallucination patterns
                # Don't filter ALL short transcriptions - many legitimate short phrases don't contain emergency keywords
                # Only filter if it's a known hallucination phrase or has suspicious patterns
                if len(transcribed_text) < 20 and not contains_valid_keywords:
                    text_stripped = transcribed_text.strip()
                    # Check if it matches known short hallucination phrases
                    if text_stripped in SHORT_HALLUCINATION_PHRASES:
                        logger.warning(
                            f"Filtered known short hallucination phrase: '{transcribed_text}'"
                        )
                        return {
                            "text": "",
                            "status": "filtered",
                            "confidence": 0.0
                        }
                    # For other short transcriptions without keywords, allow them through
                    # They might be legitimate short phrases that don't contain emergency keywords
                    # (e.g., "चालते हैं।" = "they are walking", "साइकल।" = "bicycle")
                
                # Additional check: Even if >= 20 chars, filter if it's just repeating the same few words
                # BUT: Only filter if there's clear evidence of repetition (word appears 3+ times, not 2)
                # This prevents filtering legitimate short phrases that happen to have a word appear twice
                if not contains_valid_keywords:
                    words_check = transcribed_text.split()
                    if len(words_check) <= 5:  # Very few words
                        # Check if any word appears multiple times (repetition in short text = hallucination)
                        word_counts_check = {}
                        for word in words_check:
                            word_counts_check[word] = word_counts_check.get(word, 0) + 1
                        max_repeat_check = max(word_counts_check.values()) if word_counts_check else 0

                        # If any word appears 3+ times in such short text, it's likely a hallucination
                        # (Changed from 2+ to 3+ to avoid filtering legitimate phrases like "मेरी कोचवट लग गया" where no word repeats)
                        if max_repeat_check >= 3:
                            logger.warning(
                                f"Filtered short repetitive transcription (likely hallucination): "
                                f"'{transcribed_text}' (length: {len(transcribed_text)}, words: {len(words_check)}, max_repeat: {max_repeat_check})"
                            )
                            return {
                                "text": "",
                                "status": "filtered",
                                "confidence": 0.0
                            }
                        # Also check for phrase-level repetition in short text
                        # If the same phrase appears multiple times, it's likely a hallucination
                        # BUT: Only filter if phrase appears 3+ times (not 2), to avoid filtering legitimate short phrases
                        text_normalized_check = transcribed_text.replace('।', ' ').replace('.', ' ').replace(',', ' ').strip()
                        phrases_check_short = [p.strip() for p in text_normalized_check.split()
                            if p.strip()]

                        if len(phrases_check_short) >= 2:
                            # Check if first 2-3 words form a phrase that repeats
                            for phrase_len in [3, 2]:
                                if len(phrases_check_short) >= phrase_len * 2:
                                    first_phrase_check = ' '.join(phrases_check_short[:phrase_len])
                                    phrase_count = text_normalized_check.lower().count(first_phrase_check.lower())
                                    # Changed from >= 2 to >= 3 to avoid filtering legitimate phrases
                                    if phrase_count >= 3:
                                        logger.warning(
                                            f"Filtered short transcription with repeating phrase (likely hallucination): "
                                            f"'{transcribed_text}' (phrase: '{first_phrase_check}', repeats: {phrase_count})"
                                        )
                                        return {
                                            "text": "",
                                            "status": "filtered",
                                            "confidence": 0.0
                                        }
                                break  # Found a match, no need to check shorter phrases
                
                # Transcription passed all filters
                return {
                    "text": transcribed_text,
                    "status": "ok",
                    "confidence": 0.9  # High confidence for successful transcription
                }
        
        except Exception as retry_error:
            # Unexpected error during retry loop (not API error)
            # Check if we should retry
            if attempt < MAX_RETRIES:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s
                logger.warning(
                    f"Transcription error (attempt {attempt + 1}/{MAX_RETRIES + 1}): "
                    f"{type(retry_error).__name__}: {str(retry_error)}. Retrying in {delay}s..."
                )
                time.sleep(delay)
                continue  # Retry
            else:
                # All retries exhausted
                logger.error(f"Transcription failed after {MAX_RETRIES + 1} attempts: {retry_error}", exc_info=True)
                return {
                    "text": "",
                    "status": "api_error",
                    "confidence": 0.0
                }
    
    # If we get here, all retries failed (shouldn't happen due to except above, but safety check)
    return {
        "text": "",
        "status": "api_error",
        "confidence": 0.0
    }


def transcribe_streaming(
    audio_chunk: bytes,
    previous_text: str = "",
    sample_rate: int = 16000,
    language: str = "en"  # Changed to English for better Hinglish handling
) -> Dict[str, Any]:
    """
    Transcribe audio chunk for streaming use case.
    
    This function is optimized for real-time streaming where audio chunks
    arrive continuously. It uses OpenAI's API with context from previous
    transcripts to improve accuracy.
    
    Uses English language setting which:
    - Captures both English and Hindi words better
    - Reduces hallucinations
    - Handles Hinglish code-switching more accurately
    
    Args:
        audio_chunk: Binary audio chunk (PCM format, Int16, 16kHz, mono)
        previous_text: Previous transcript for context (improves accuracy)
        sample_rate: Sample rate of the audio (default: 16000 Hz)
        language: Language code (default: "en" for English, which handles Hinglish well)
    
    Returns:
        Dict with keys:
            - text: str - Transcribed text (empty if failed)
            - status: Literal["ok", "silence", "api_error", "filtered"] - Status of transcription
            - confidence: float - Confidence score (0.0-1.0)
    
    Raises:
        ValueError: If audio data is invalid
    """
    # Use English language for better Hinglish handling
    # OpenAI API handles code-switching better when set to English
    result = transcribe(
        audio_chunk,
        sample_rate=sample_rate,
        language=language,  # Use English for better Hinglish transcription
        previous_text=previous_text,
        enable_partial=True
    )
    
    return result

