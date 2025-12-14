"""
Intent Detection module for classifying user requests.

This module detects user intent from fragmented Hindi/Hinglish text and
classifies requests into categories: Accident, Crime, Medical, Non-Urgent.

Handles:
- Fragmented speech (incomplete sentences from streaming audio)
- Code-switching (Hindi-English mix / Hinglish)
- Multiple keywords and variations
- Confidence scoring based on keyword matches
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class Intent(Enum):
    """Intent categories for user requests."""
    ACCIDENT = "Accident"
    CRIME = "Crime"
    MEDICAL = "Medical"
    NON_URGENT = "Non-Urgent"


# Keyword mapping for intent detection
# Organized by intent category with Hindi, English, and Hinglish variations
# Each keyword has a weight indicating its importance for that intent

INTENT_KEYWORDS: Dict[Intent, Dict[str, float]] = {
    Intent.ACCIDENT: {
        # Hindi keywords for accidents
        "दुर्घटना": 1.0,  # accident
        "हादसा": 1.0,  # incident/accident
        "गाड़ी": 0.8,  # vehicle
        "कार": 0.8,  # car
        "बस": 0.7,  # bus
        "ट्रक": 0.7,  # truck
        "मोटरसाइकिल": 0.7,  # motorcycle
        "टक्कर": 0.9,  # collision
        "दुर्घटना": 1.0,  # accident
        "गिर गया": 0.8,  # fell down
        "गिर गई": 0.8,  # fell down (feminine)
        "टूट गया": 0.7,  # broke
        "चोट": 0.6,  # injury
        "खून": 0.5,  # blood
        "सड़क": 0.6,  # road
        "हाइवे": 0.6,  # highway
        
        # English keywords
        "accident": 1.0,
        "crash": 0.9,
        "collision": 0.9,
        "vehicle": 0.8,
        "car": 0.8,
        "bus": 0.7,
        "truck": 0.7,
        "motorcycle": 0.7,
        "fell": 0.8,
        "broken": 0.7,
        "injury": 0.6,
        "blood": 0.5,
        "road": 0.6,
        "highway": 0.6,
        
        # Hinglish variations
        "accident हुआ": 1.0,  # accident happened
        "crash हो गया": 0.9,  # crash happened
        "गाड़ी crash": 0.9,  # car crash
        "car दुर्घटना": 0.9,  # car accident
    },
    
    Intent.CRIME: {
        # Hindi keywords for crimes
        "अपराध": 1.0,  # crime
        "चोरी": 1.0,  # theft
        "डकैती": 1.0,  # robbery
        "हत्या": 1.0,  # murder
        "मारपीट": 0.9,  # assault
        "छीन": 0.9,  # snatching
        "पर्स": 0.8,  # purse
        "मोबाइल": 0.8,  # mobile
        "फोन": 0.8,  # phone
        "पैसा": 0.7,  # money
        "जेवर": 0.8,  # jewelry
        "सोना": 0.7,  # gold
        "पुलिस": 0.6,  # police
        "थाना": 0.6,  # police station
        "गिरफ्तार": 0.7,  # arrested
        "धमकी": 0.8,  # threat
        "खतरा": 0.7,  # danger
        "लूट": 0.9,  # loot
        "बलात्कार": 1.0,  # rape
        "यौन": 0.9,  # sexual
        "हमला": 0.9,  # attack
        
        # English keywords
        "crime": 1.0,
        "theft": 1.0,
        "robbery": 1.0,
        "murder": 1.0,
        "assault": 0.9,
        "snatch": 0.9,
        "stolen": 0.9,
        "stole": 0.9,
        "purse": 0.8,
        "mobile": 0.8,
        "phone": 0.8,
        "money": 0.7,
        "jewelry": 0.8,
        "gold": 0.7,
        "police": 0.6,
        "threat": 0.8,
        "danger": 0.7,
        "loot": 0.9,
        "rape": 1.0,
        "sexual": 0.9,
        "attack": 0.9,
        
        # Hinglish variations
        "चोरी हो गई": 1.0,  # theft happened
        "mobile चोरी": 0.9,  # mobile theft
        "purse snatch": 0.9,  # purse snatching
        "robbery हुआ": 1.0,  # robbery happened
        "crime हुआ": 1.0,  # crime happened
    },
    
    Intent.MEDICAL: {
        # Hindi keywords for medical emergencies
        "दिल": 0.8,  # heart
        "दर्द": 0.9,  # pain
        "सिर": 0.7,  # head
        "पेट": 0.7,  # stomach
        "बुखार": 0.8,  # fever
        "उल्टी": 0.8,  # vomiting
        "बेहोश": 0.9,  # unconscious
        "सांस": 0.8,  # breath
        "सांस लेने": 0.9,  # breathing
        "अस्पताल": 0.7,  # hospital
        "डॉक्टर": 0.7,  # doctor
        "एम्बुलेंस": 0.9,  # ambulance
        "इलाज": 0.6,  # treatment
        "दवा": 0.6,  # medicine
        "घायल": 0.8,  # injured
        "जलन": 0.7,  # burn
        "कट": 0.7,  # cut
        "टूट": 0.7,  # broken/fracture
        "हड्डी": 0.8,  # bone
        "खून बह रहा": 0.9,  # bleeding
        "दौरा": 0.9,  # seizure/attack
        "हार्ट": 0.8,  # heart (English)
        "अस्थमा": 0.8,  # asthma
        "डायबिटीज": 0.7,  # diabetes
        "बीपी": 0.7,  # blood pressure
        "स्ट्रोक": 0.9,  # stroke
        
        # English keywords
        "heart": 0.8,
        "pain": 0.9,
        "head": 0.7,
        "stomach": 0.7,
        "fever": 0.8,
        "vomit": 0.8,
        "unconscious": 0.9,
        "breath": 0.8,
        "breathing": 0.9,
        "hospital": 0.7,
        "doctor": 0.7,
        "ambulance": 0.9,
        "treatment": 0.6,
        "medicine": 0.6,
        "injured": 0.8,
        "burn": 0.7,
        "cut": 0.7,
        "broken": 0.7,
        "bone": 0.8,
        "bleeding": 0.9,
        "seizure": 0.9,
        "attack": 0.9,
        "asthma": 0.8,
        "diabetes": 0.7,
        "blood pressure": 0.7,
        "stroke": 0.9,
        "chest": 0.8,
        "chest pain": 0.95,
        
        # Hinglish variations
        "heart attack": 1.0,  # heart attack
        "दिल का दौरा": 1.0,  # heart attack
        "सांस नहीं आ रही": 0.9,  # can't breathe
        "breathing problem": 0.9,  # breathing problem
        "बुखार है": 0.8,  # have fever
        "fever है": 0.8,  # have fever
        "doctor चाहिए": 0.8,  # need doctor
        "ambulance चाहिए": 0.9,  # need ambulance
        "hospital जाना": 0.7,  # go to hospital
    },
    
    Intent.NON_URGENT: {
        # Hindi keywords for non-urgent requests
        "सूचना": 0.6,  # information
        "जानकारी": 0.6,  # information
        "पूछना": 0.5,  # ask
        "बताना": 0.5,  # tell
        "मदद": 0.4,  # help (general)
        "सहायता": 0.4,  # assistance
        "रास्ता": 0.6,  # way/direction
        "दिशा": 0.6,  # direction
        "पता": 0.6,  # address
        "समय": 0.5,  # time
        "तारीख": 0.5,  # date
        "कब": 0.5,  # when
        "कहाँ": 0.5,  # where
        "कैसे": 0.5,  # how
        "क्या": 0.4,  # what
        "क्यों": 0.4,  # why
        "शिकायत": 0.7,  # complaint (non-urgent)
        "समस्या": 0.5,  # problem (non-urgent)
        "सवाल": 0.5,  # question
        
        # English keywords
        "information": 0.6,
        "info": 0.6,
        "ask": 0.5,
        "tell": 0.5,
        "help": 0.4,  # general help
        "assistance": 0.4,
        "direction": 0.6,
        "way": 0.6,
        "address": 0.6,
        "time": 0.5,
        "date": 0.5,
        "when": 0.5,
        "where": 0.5,
        "how": 0.5,
        "what": 0.4,
        "why": 0.4,
        "complaint": 0.7,
        "problem": 0.5,
        "question": 0.5,
        "query": 0.5,
        
        # Hinglish variations
        "information चाहिए": 0.6,  # need information
        "जानकारी चाहिए": 0.6,  # need information
        "रास्ता बताओ": 0.6,  # tell the way
        "direction दो": 0.6,  # give direction
        "help चाहिए": 0.4,  # need help (general)
    }
}


def normalize_text(text: str) -> str:
    """
    Normalize text for better keyword matching.
    
    This function handles:
    - Converting to lowercase for case-insensitive matching
    - Removing extra whitespace
    - Handling common variations in Hindi/Hinglish text
    
    Args:
        text: Input text to normalize
    
    Returns:
        str: Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase for case-insensitive matching
    # This handles both English and transliterated Hindi
    text = text.lower()
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_keywords(text: str) -> List[str]:
    """
    Extract potential keywords from fragmented text.
    
    Handles fragmented speech by:
    - Splitting on common delimiters
    - Extracting individual words
    - Preserving multi-word phrases
    
    Args:
        text: Input text (may be fragmented)
    
    Returns:
        List[str]: List of potential keywords and phrases
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    
    # Split on common delimiters
    # Handles punctuation, spaces, and common separators
    words = re.split(r'[,\s\.!?।]+', normalized)
    
    # Filter out empty strings
    words = [w.strip() for w in words if w.strip()]
    
    # Also extract 2-word and 3-word phrases for better matching
    # This helps with phrases like "heart attack", "mobile चोरी"
    phrases = []
    if len(words) >= 2:
        # 2-word phrases
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
    
    if len(words) >= 3:
        # 3-word phrases
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # Combine words and phrases
    all_keywords = words + phrases
    
    return all_keywords


def calculate_intent_score(text: str, intent: Intent) -> float:
    """
    Calculate confidence score for a specific intent.
    
    This function:
    - Extracts keywords from text
    - Matches against intent keyword dictionary
    - Calculates weighted score based on keyword matches
    - Normalizes score to 0.0-1.0 range
    
    Args:
        text: Input text to analyze
        intent: Intent category to score
    
    Returns:
        float: Confidence score (0.0 to 1.0)
    """
    if not text:
        return 0.0
    
    # Extract keywords from text
    keywords = extract_keywords(text)
    
    if not keywords:
        return 0.0
    
    # Get keyword dictionary for this intent
    intent_keywords = INTENT_KEYWORDS.get(intent, {})
    
    if not intent_keywords:
        return 0.0
    
    # Calculate weighted score
    # Each matching keyword contributes its weight to the total score
    total_score = 0.0
    matches_found = 0
    
    for keyword in keywords:
        # Check for exact match (case-insensitive)
        keyword_lower = keyword.lower()
        
        # Check all intent keywords for matches
        for intent_keyword, weight in intent_keywords.items():
            intent_keyword_lower = intent_keyword.lower()
            
            # Exact match
            if keyword_lower == intent_keyword_lower:
                total_score += weight
                matches_found += 1
                logger.debug(f"Match found: '{keyword}' -> {intent.value} (weight: {weight})")
            
            # Partial match (keyword contains intent keyword or vice versa)
            # This helps with fragmented speech
            elif keyword_lower in intent_keyword_lower or intent_keyword_lower in keyword_lower:
                # Use partial weight for partial matches
                partial_weight = weight * 0.5
                total_score += partial_weight
                matches_found += 1
                logger.debug(f"Partial match: '{keyword}' -> {intent.value} (weight: {partial_weight})")
    
    # Normalize score
    # Maximum possible score is sum of all weights
    # We normalize to 0.0-1.0 range
    max_possible_score = sum(intent_keywords.values())
    
    if max_possible_score == 0:
        return 0.0
    
    # Normalized score
    normalized_score = min(total_score / max_possible_score, 1.0)
    
    # Boost score if multiple matches found
    # Multiple keyword matches increase confidence
    if matches_found > 1:
        boost = min(matches_found * 0.1, 0.3)  # Max 30% boost
        normalized_score = min(normalized_score + boost, 1.0)
    
    return normalized_score


def detect_intent(text: str) -> Dict[str, any]:
    """
    Detect user intent from fragmented Hindi/Hinglish text.
    
    This is the main function for intent detection. It:
    1. Normalizes input text
    2. Calculates confidence scores for all intent categories
    3. Selects the intent with highest confidence
    4. Returns JSON with intent label and confidence score
    
    Handles fragmented speech by:
    - Extracting keywords from incomplete sentences
    - Matching against keyword dictionaries
    - Using weighted scoring for confidence
    
    Args:
        text: Input text (may be fragmented Hindi/Hinglish)
    
    Returns:
        dict: JSON with keys:
            - "intent": str - Intent label (Accident, Crime, Medical, Non-Urgent)
            - "confidence": float - Confidence score (0.0 to 1.0)
            - "scores": dict - Scores for all intents (for debugging)
    
    Example:
        >>> detect_intent("दुर्घटना हुई, गाड़ी crash")
        {
            "intent": "Accident",
            "confidence": 0.85,
            "scores": {
                "Accident": 0.85,
                "Crime": 0.12,
                "Medical": 0.05,
                "Non-Urgent": 0.02
            }
        }
    """
    if not text or not text.strip():
        # No text provided - default to Non-Urgent
        return {
            "intent": Intent.NON_URGENT.value,
            "confidence": 0.0,
            "scores": {
                intent.value: 0.0 for intent in Intent
            }
        }
    
    # Normalize text for matching
    normalized_text = normalize_text(text)
    
    logger.debug(f"Detecting intent for text: {normalized_text[:100]}...")
    
    # Calculate scores for all intent categories
    intent_scores = {}
    for intent in Intent:
        score = calculate_intent_score(normalized_text, intent)
        intent_scores[intent] = score
    
    # Find intent with highest score
    best_intent = max(intent_scores.items(), key=lambda x: x[1])
    detected_intent, confidence = best_intent
    
    # Convert scores to dictionary with string keys for JSON
    scores_dict = {
        intent.value: float(intent_scores[intent])
        for intent in Intent
    }
    
    # Log detection result
    logger.info(
        f"Intent detected: {detected_intent.value} "
        f"(confidence: {confidence:.2f}) for text: {normalized_text[:50]}..."
    )
    
    # Return JSON response
    return {
        "intent": detected_intent.value,
        "confidence": round(float(confidence), 3),  # Round to 3 decimal places
        "scores": scores_dict  # Include all scores for debugging/analysis
    }


def detect_intent_simple(text: str) -> Dict[str, any]:
    """
    Simplified intent detection (returns only intent and confidence).
    
    Use this when you don't need detailed scores for all intents.
    
    Args:
        text: Input text (may be fragmented Hindi/Hinglish)
    
    Returns:
        dict: JSON with keys:
            - "intent": str - Intent label
            - "confidence": float - Confidence score
    """
    result = detect_intent(text)
    return {
        "intent": result["intent"],
        "confidence": result["confidence"]
    }

