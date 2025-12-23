"""
OpenAI Signal Extraction Layer (Perception Only)

This module uses OpenAI to extract structured signals from transcripts.
OpenAI is used ONLY for perception - extracting signals, NOT making decisions.

All decision-making logic is implemented deterministically in our code.

Expected OpenAI Response Format:
{
  "language": "Hindi | Hinglish",
  "intent": "medical_emergency | police | fire | non_emergency | unclear",
  "entities": {
    "name": null,
    "location": null,
    "incident": null
  },
  "emotion": "panic | stressed | calm | angry",
  "clarity": 0.0
}

This response is validated and normalized before use.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI client instance."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized for signal extraction")
    return _client


def extract_signals(transcript: str, previous_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract structured signals from transcript using OpenAI.
    
    This function uses OpenAI ONLY for perception - extracting signals from text.
    It does NOT make any decisions about urgency, escalation, or control flow.
    
    All decisions are made deterministically in our code based on these signals.
    
    Args:
        transcript: User's transcribed speech (may be fragmented, emotional)
        previous_context: Optional previous context for better extraction
    
    Returns:
        dict: Structured signals with keys:
            - "language": str - "Hindi" | "Hinglish" | "English"
            - "intent": str - "medical_emergency" | "police" | "fire" | "non_emergency" | "unclear"
            - "entities": dict - {"name": str|None, "location": str|None, "incident": str|None}
            - "emotion": str - "panic" | "stressed" | "calm" | "angry"
            - "clarity": float - 0.0 to 1.0 (how clear/understandable the speech is)
    
    Raises:
        RuntimeError: If OpenAI API call fails
    """
    if not transcript or not transcript.strip():
        return {
            "language": "unclear",
            "intent": "unclear",
            "entities": {"name": None, "location": None, "incident": None},
            "emotion": "calm",
            "clarity": 0.0
        }
    
    try:
        client = get_client()
        
        # Build prompt for OpenAI to extract signals only
        # Explicitly instruct OpenAI to NOT make decisions
        system_prompt = """You are a signal extraction system for an emergency call triage system in India.

Your ONLY job is to extract structured signals from the user's speech. You MUST NOT make any decisions.

Extract the following signals:
1. Language: "Hindi", "Hinglish", or "English"
2. Intent: "medical_emergency", "police", "fire", "non_emergency", or "unclear"
3. Entities: Extract name, location, and incident type if mentioned
4. Emotion: "panic", "stressed", "calm", or "angry"
5. Clarity: Score 0.0-1.0 indicating how clear/understandable the speech is

Return ONLY a JSON object with these signals. Do NOT make any decisions about urgency or escalation."""

        user_prompt = f"""Extract signals from this emergency call transcript:

"{transcript}"

Previous context: {json.dumps(previous_context) if previous_context else "None"}

Return a JSON object with:
- language: "Hindi" | "Hinglish" | "English"
- intent: "medical_emergency" | "police" | "fire" | "non_emergency" | "unclear"
- entities: {{"name": string or null, "location": string or null, "incident": string or null}}
- emotion: "panic" | "stressed" | "calm" | "angry"
- clarity: float between 0.0 and 1.0

Do NOT make decisions. Only extract signals."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use fast, cost-effective model for signal extraction
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Low temperature for consistent extraction
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        # Parse response
        content = response.choices[0].message.content
        # #region agent log
        import logging
        logger = logging.getLogger(__name__)
        try:
            with open("/Users/naman/Documents/projects/Nirnay-112/.cursor/debug.log", "a") as f:
                from datetime import datetime
                f.write(json.dumps({"location":"signal_extraction.py:128","message":"OpenAI signal extraction response received","data":{"content_preview":content[:200],"content_length":len(content)},"timestamp":datetime.now().isoformat(),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"})+"\n")
        except: pass
        # #endregion
        signals = json.loads(content)
        # #region agent log
        try:
            with open("/Users/naman/Documents/projects/Nirnay-112/.cursor/debug.log", "a") as f:
                from datetime import datetime
                f.write(json.dumps({"location":"signal_extraction.py:131","message":"Signals parsed","data":{"language":signals.get("language"),"intent":signals.get("intent"),"entities":signals.get("entities"),"emotion":signals.get("emotion"),"clarity":signals.get("clarity")},"timestamp":datetime.now().isoformat(),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"})+"\n")
        except: pass
        # #endregion
        
        # Validate and normalize response
        signals = _validate_and_normalize_signals(signals)
        
        logger.debug(f"Extracted signals: {signals}")
        return signals
        
    except Exception as e:
        logger.error(f"OpenAI signal extraction failed: {e}", exc_info=True)
        # Return safe defaults on error
        return {
            "language": "unclear",
            "intent": "unclear",
            "entities": {"name": None, "location": None, "incident": None},
            "emotion": "calm",
            "clarity": 0.0
        }


def _validate_and_normalize_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize signals from OpenAI response.
    
    Ensures all required fields are present and within valid ranges.
    
    Args:
        signals: Raw signals from OpenAI
    
    Returns:
        dict: Validated and normalized signals
    """
    # Default values
    default_signals = {
        "language": "unclear",
        "intent": "unclear",
        "entities": {"name": None, "location": None, "incident": None},
        "emotion": "calm",
        "clarity": 0.0
    }
    
    # Validate language
    valid_languages = ["Hindi", "Hinglish", "English", "unclear"]
    language = signals.get("language", "unclear")
    if language not in valid_languages:
        language = "unclear"
    
    # Validate intent
    valid_intents = ["medical_emergency", "police", "fire", "non_emergency", "unclear"]
    intent = signals.get("intent", "unclear")
    if intent not in valid_intents:
        intent = "unclear"
    
    # Validate entities
    entities = signals.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}
    entities = {
        "name": entities.get("name") if entities.get("name") else None,
        "location": entities.get("location") if entities.get("location") else None,
        "incident": entities.get("incident") if entities.get("incident") else None
    }
    
    # Validate emotion
    valid_emotions = ["panic", "stressed", "calm", "angry"]
    emotion = signals.get("emotion", "calm")
    if emotion not in valid_emotions:
        emotion = "calm"
    
    # Validate clarity (0.0 to 1.0)
    clarity = signals.get("clarity", 0.0)
    try:
        clarity = float(clarity)
        clarity = max(0.0, min(1.0, clarity))  # Clamp to [0.0, 1.0]
    except (ValueError, TypeError):
        clarity = 0.0
    
    return {
        "language": language,
        "intent": intent,
        "entities": entities,
        "emotion": emotion,
        "clarity": clarity
    }

