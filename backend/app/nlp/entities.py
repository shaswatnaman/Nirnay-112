"""
Entity Extraction module for extracting structured information from text.

This module extracts entities from fragmented, vague, incomplete, or emotional
Hindi/Hinglish speech and returns structured data with confidence scores.

Extracts:
- name: Person names
- location: Places, addresses, landmarks
- incident_type: Type of incident/emergency
- urgency: Urgency level of the request
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class UrgencyLevel(Enum):
    """Urgency levels for incidents."""
    CRITICAL = "critical"  # Life-threatening, immediate response needed
    HIGH = "high"  # Urgent, response needed soon
    MEDIUM = "medium"  # Important but not immediately urgent
    LOW = "low"  # Non-urgent, can wait


# Location keywords and patterns (Hindi, English, Hinglish)
LOCATION_KEYWORDS = {
    # Hindi location indicators
    "में": 0.6,  # in/at
    "पर": 0.6,  # on/at
    "के पास": 0.7,  # near
    "के पीछे": 0.7,  # behind
    "के सामने": 0.7,  # in front of
    "के बगल": 0.7,  # beside
    "रोड": 0.8,  # road
    "सड़क": 0.8,  # road
    "मार्ग": 0.8,  # route
    "गली": 0.7,  # lane
    "चौक": 0.7,  # square
    "चौराहा": 0.7,  # crossing
    "होटल": 0.6,  # hotel
    "मंदिर": 0.6,  # temple
    "स्कूल": 0.6,  # school
    "अस्पताल": 0.6,  # hospital
    "मार्केट": 0.6,  # market
    "बाजार": 0.6,  # market
    "पार्क": 0.6,  # park
    "स्टेशन": 0.7,  # station
    "बस स्टॉप": 0.7,  # bus stop
    "मेट्रो": 0.7,  # metro
    
    # English location indicators
    "at": 0.6,
    "near": 0.7,
    "beside": 0.7,
    "behind": 0.7,
    "in front of": 0.7,
    "road": 0.8,
    "street": 0.8,
    "lane": 0.7,
    "avenue": 0.8,
    "crossing": 0.7,
    "square": 0.7,
    "hotel": 0.6,
    "temple": 0.6,
    "school": 0.6,
    "hospital": 0.6,
    "market": 0.6,
    "park": 0.6,
    "station": 0.7,
    "bus stop": 0.7,
    "metro": 0.7,
    
    # Common location names (examples - can be expanded)
    "दिल्ली": 0.9,  # Delhi
    "new delhi": 0.9,  # New Delhi
    "नई दिल्ली": 0.9,  # New Delhi (Hindi)
    "मुंबई": 0.9,  # Mumbai
    "बंगलौर": 0.9,  # Bangalore
    "चेन्नई": 0.9,  # Chennai
    "कोलकाता": 0.9,  # Kolkata
    "पुणे": 0.9,  # Pune
    "हैदराबाद": 0.9,  # Hyderabad
    "जयपुर": 0.9,  # Jaipur
    "लखनऊ": 0.9,  # Lucknow
    "कानपुर": 0.9,  # Kanpur
    "railway station": 0.8,  # Railway station
    "रेलवे स्टेशन": 0.8,  # Railway station (Hindi)
}

# Urgency indicators (Hindi, English, Hinglish)
URGENCY_KEYWORDS = {
    UrgencyLevel.CRITICAL: {
        # Hindi
        "तुरंत": 1.0,  # immediately
        "अभी": 1.0,  # now
        "जल्दी": 0.9,  # quickly
        "तत्काल": 1.0,  # immediately
        "बहुत जरूरी": 1.0,  # very urgent
        "जान का खतरा": 1.0,  # life-threatening
        "मर रहा": 0.9,  # dying
        "बेहोश": 0.8,  # unconscious
        "खून बह रहा": 0.9,  # bleeding
        "सांस नहीं": 0.9,  # can't breathe
        
        # English
        "immediately": 1.0,
        "now": 1.0,
        "urgent": 1.0,
        "critical": 1.0,
        "emergency": 1.0,
        "dying": 0.9,
        "unconscious": 0.8,
        "bleeding": 0.9,
        "can't breathe": 0.9,
        "life threatening": 1.0,
        
        # Hinglish
        "तुरंत आओ": 1.0,  # come immediately
        "urgent है": 1.0,  # is urgent
        "emergency है": 1.0,  # is emergency
    },
    
    UrgencyLevel.HIGH: {
        # Hindi
        "जल्दी": 0.8,  # quickly
        "शीघ्र": 0.8,  # soon
        "जरूरी": 0.9,  # urgent
        "तुरंत": 0.7,  # immediately (less emphasis)
        "जल्द": 0.8,  # soon
        
        # English
        "soon": 0.8,
        "quickly": 0.8,
        "asap": 0.9,
        "fast": 0.7,
        "quick": 0.7,
    },
    
    UrgencyLevel.MEDIUM: {
        # Hindi
        "जल्द ही": 0.6,  # soon
        "समय पर": 0.5,  # on time
        "जरूरत": 0.5,  # need
        
        # English
        "when possible": 0.5,
        "need": 0.5,
        "required": 0.5,
    },
    
    UrgencyLevel.LOW: {
        # Hindi
        "बाद में": 0.7,  # later
        "जब भी": 0.6,  # whenever
        "कोई जल्दी नहीं": 0.8,  # no hurry
        
        # English
        "later": 0.7,
        "whenever": 0.6,
        "no hurry": 0.8,
        "not urgent": 0.8,
    }
}

# Incident type patterns (can be expanded based on intent detection)
INCIDENT_TYPE_PATTERNS = {
    "accident": [
        r"दुर्घटना", r"हादसा", r"crash", r"accident", r"collision",
        r"टक्कर", r"गिर गया", r"गिर गई"
    ],
    "crime": [
        r"चोरी", r"डकैती", r"theft", r"robbery", r"crime",
        r"हत्या", r"murder", r"assault", r"मारपीट"
    ],
    "medical": [
        r"दर्द", r"pain", r"बुखार", r"fever", r"heart", r"दिल",
        r"सांस", r"breath", r"unconscious", r"बेहोश", r"injured", r"घायल"
    ],
    "fire": [
        r"आग", r"fire", r"जलन", r"burn", r"धुआं", r"smoke"
    ],
    "other": []  # Catch-all for other incidents
}

# Name patterns (common name indicators and patterns)
# Support both Hindi and English indicators in English transcripts
NAME_INDICATORS = [
    r"मेरा नाम",  # my name (Hindi)
    r"नाम है",  # name is (Hindi)
    r"मैं",  # I (followed by name, Hindi)
    r"name is",  # name is (English)
    r"my name is",  # my name is (English)
    r"i am",  # I am (English)
    r"i'm",  # I'm (English)
    r"call me",  # call me (English)
    r"मुझे कहते हैं",  # they call me (Hindi)
    r"this is",  # this is (English, e.g., "this is Rahul")
]

# Common Indian name patterns (first names)
COMMON_NAMES = [
    # Common first names (examples - can be expanded with database)
    r"राम", r"श्याम", r"मोहन", r"राज", r"अमित", r"राहुल",
    r"प्रिया", r"अनु", r"सीता", r"गीता", r"राधा",
    r"ram", r"shyam", r"mohan", r"raj", r"amit", r"rahul",
    r"priya", r"anu", r"sita", r"geeta", r"radha",
]


def normalize_text(text: str) -> str:
    """
    Normalize text for entity extraction.
    
    Handles:
    - Case normalization
    - Whitespace cleanup
    - Common variations
    
    Args:
        text: Input text
    
    Returns:
        str: Normalized text
    """
    if not text:
        return ""
    
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_name(text: str) -> Tuple[Optional[str], float]:
    """
    Extract person name from text.
    
    Handles:
    - Explicit name mentions ("मेरा नाम राम है")
    - Implicit names in context
    - Vague references ("मैं राम")
    - Emotional speech with incomplete names
    
    Args:
        text: Input text (may be fragmented or emotional)
    
    Returns:
        Tuple[Optional[str], float]: (name, confidence)
    """
    if not text:
        return None, 0.0
    
    normalized = normalize_text(text)
    name = None
    confidence = 0.0
    
    # Pattern 1: Explicit name indicators
    # "मेरा नाम X है" or "name is X" or "my name is X" or "I am X"
    # Support both Hindi and English names in English transcripts
    for indicator in NAME_INDICATORS:
        # Pattern for Hindi/English names: allow Unicode characters (Hindi) and ASCII
        # Handle English transcripts: "my name is Rahul" or "I am Rahul"
        pattern = rf"{indicator}\s+([\u0900-\u097F\w]+(?:\s+[\u0900-\u097F\w]+)?)"
        match = re.search(pattern, normalized, re.IGNORECASE | re.UNICODE)
        if match:
            potential_name = match.group(1).strip()
            # Filter out common words that might be captured
            if len(potential_name) > 1 and potential_name.lower() not in ["is", "am", "are", "the", "a", "an"]:
                name = potential_name  # Keep original case/script
                confidence = 0.9
                logger.debug(f"Name extracted via indicator: {name}")
                return name, confidence
    
    # Pattern 2: Common name patterns
    # Look for known common names in text
    for name_pattern in COMMON_NAMES:
        match = re.search(rf"\b{name_pattern}\b", normalized, re.IGNORECASE)
        if match:
            potential_name = match.group(0).strip()
            name = potential_name.title()
            confidence = 0.7  # Lower confidence for pattern matching
            logger.debug(f"Name extracted via pattern: {name}")
            return name, confidence
    
    # Pattern 3: Capitalized words (potential names)
    # In emotional speech, names might be mentioned without indicators
    words = normalized.split()
    for i, word in enumerate(words):
        # Check if word looks like a name (2-15 chars, mostly letters)
        if 2 <= len(word) <= 15 and word.isalpha():
            # Check if it's not a common word
            if word not in ["मैं", "तुम", "वह", "यह", "i", "you", "he", "she", "it"]:
                name = word.title()
                confidence = 0.5  # Low confidence for vague extraction
                logger.debug(f"Name extracted via word analysis: {name}")
                return name, confidence
    
    return None, 0.0


def extract_location(text: str) -> Tuple[Optional[str], float]:
    """
    Extract location from text.
    
    Handles:
    - Explicit locations ("दिल्ली में", "near hospital")
    - Landmarks and places
    - Vague references ("वहाँ", "there")
    - Incomplete location mentions
    
    Args:
        text: Input text (may be fragmented)
    
    Returns:
        Tuple[Optional[str], float]: (location, confidence)
    """
    if not text:
        return None, 0.0
    
    normalized = normalize_text(text)
    location = None
    confidence = 0.0
    
    # Pattern 1: Location keywords with following text
    # "में X", "near X", "at X", "in X", "at railway station X"
    # Support both Hindi and English location names
    # Handle English transcripts with Hindi words mixed in
    for keyword, weight in LOCATION_KEYWORDS.items():
        # Pattern: keyword followed by location name (Hindi Unicode + English + spaces)
        # More flexible pattern to capture locations in English transcripts
        pattern = rf"{re.escape(keyword)}\s+([\u0900-\u097F\w\s]+?)(?:\s|$|,|\.|!|\?)"
        match = re.search(pattern, normalized, re.IGNORECASE | re.UNICODE)
        if match:
            potential_location = match.group(1).strip()
            # Filter out very short or common words
            if len(potential_location) > 2 and potential_location.lower() not in ["the", "a", "an", "is", "are", "was", "were"]:
                location = potential_location  # Keep original case/script
                confidence = weight
                logger.debug(f"Location extracted via keyword '{keyword}': {location}")
                return location, confidence
    
    # Pattern 2: Known location names
    # Check if text contains known city/place names
    for loc_name, weight in LOCATION_KEYWORDS.items():
        if weight >= 0.8:  # High-weight locations (cities)
            pattern = rf"\b{re.escape(loc_name)}\b"
            if re.search(pattern, normalized, re.IGNORECASE):
                location = loc_name.title()
                confidence = weight
                logger.debug(f"Location extracted via known name: {location}")
                return location, confidence
    
    # Pattern 3: Common location patterns
    # "X road", "X street", "X market", "railway station X", "X station"
    # Handle English transcripts with location names
    location_patterns = [
        r"([\u0900-\u097F\w\s]+?)\s+(road|street|lane|avenue|market|bazar|station|मार्केट|बाजार|सड़क|रोड|स्टेशन)",
        r"(road|street|lane|avenue|market|bazar|station|railway station|मार्केट|बाजार|सड़क|रोड|स्टेशन|रेलवे स्टेशन)\s+([\u0900-\u097F\w\s]+?)",
        r"(railway|रेलवे)\s+(station|स्टेशन)\s+([\u0900-\u097F\w\s]+?)",  # "railway station New Delhi"
        r"([\u0900-\u097F\w\s]+?)\s+(railway|रेलवे)\s+(station|स्टेशन)",  # "New Delhi railway station"
        r"(at|in|near|beside|behind|in front of)\s+([\u0900-\u097F\w\s]+?)\s+(railway|रेलवे)?\s*(station|स्टेशन)?",  # "at New Delhi railway station"
        r"(railway|रेलवे)\s+(station|स्टेशन)\s+(of|in|at)?\s*([\u0900-\u097F\w\s]+?)",  # "railway station of New Delhi"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE | re.UNICODE)
        if match:
            # Handle different group positions (some patterns have location in group 1, others in group 2 or 3)
            potential_location = None
            skip_words = ["road", "street", "lane", "avenue", "market", "bazar", "station", "railway", "मार्केट", "बाजार", "सड़क", "रोड", "स्टेशन", "रेलवे", "रेलवे स्टेशन"]
            for i in range(1, len(match.groups()) + 1):
                group = match.group(i)
                if group and group.strip() and group.strip().lower() not in [w.lower() for w in skip_words]:
                    # Check if it's a meaningful location (not just a single common word)
                    words = group.strip().split()
                    if len(words) > 0:
                        potential_location = group.strip()
                        break
            
            if potential_location and len(potential_location) > 1:
                location = potential_location  # Keep original case/script
                confidence = 0.7
                logger.debug(f"Location extracted via pattern: {location}")
                return location, confidence
    
    return None, 0.0


def extract_incident_type(text: str) -> Tuple[Optional[str], float]:
    """
    Extract incident type from text.
    
    Handles:
    - Explicit incident mentions
    - Vague references
    - Emotional descriptions
    
    Args:
        text: Input text (may be fragmented or emotional)
    
    Returns:
        Tuple[Optional[str], float]: (incident_type, confidence)
    """
    if not text:
        return None, 0.0
    
    normalized = normalize_text(text)
    incident_type = None
    max_confidence = 0.0
    
    # Check each incident type pattern
    for inc_type, patterns in INCIDENT_TYPE_PATTERNS.items():
        if not patterns:
            continue
        
        matches = 0
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                matches += 1
        
        if matches > 0:
            # Confidence based on number of matches
            confidence = min(0.5 + (matches * 0.2), 1.0)
            if confidence > max_confidence:
                max_confidence = confidence
                incident_type = inc_type
                logger.debug(f"Incident type extracted: {incident_type} (confidence: {confidence})")
    
    return incident_type, max_confidence


def extract_urgency(text: str) -> Tuple[Optional[str], float]:
    """
    Extract urgency level from text.
    
    Handles:
    - Explicit urgency indicators
    - Emotional urgency ("तुरंत!", "urgent!")
    - Vague urgency mentions
    
    Args:
        text: Input text (may be emotional or fragmented)
    
    Returns:
        Tuple[Optional[str], float]: (urgency_level, confidence)
    """
    if not text:
        return None, 0.0
    
    normalized = normalize_text(text)
    urgency = None
    max_confidence = 0.0
    
    # Check each urgency level
    for level, keywords in URGENCY_KEYWORDS.items():
        total_score = 0.0
        matches = 0
        
        for keyword, weight in keywords.items():
            # Check for keyword in text
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, normalized, re.IGNORECASE):
                total_score += weight
                matches += 1
        
        if matches > 0:
            # Calculate confidence (average weight, boosted by multiple matches)
            confidence = min((total_score / matches) + (matches * 0.1), 1.0)
            if confidence > max_confidence:
                max_confidence = confidence
                urgency = level.value
                logger.debug(f"Urgency extracted: {urgency} (confidence: {confidence})")
    
    # Default to MEDIUM if no urgency indicators found
    if urgency is None:
        urgency = UrgencyLevel.MEDIUM.value
        max_confidence = 0.3  # Low confidence for default
    
    return urgency, max_confidence


def extract_entities(text: str) -> Dict[str, any]:
    """
    Extract all entities from text.
    
    This is the main function for entity extraction. It extracts:
    - name: Person names
    - location: Places, addresses, landmarks
    - incident_type: Type of incident/emergency
    - urgency: Urgency level
    
    Handles:
    - Vague, incomplete, or emotional speech
    - Fragmented text from streaming audio
    - Hindi/Hinglish code-switching
    
    Args:
        text: Input text (may be fragmented, vague, or emotional)
    
    Returns:
        dict: JSON with keys:
            - "entities": dict - Extracted entities
                - "name": str or None
                - "location": str or None
                - "incident_type": str or None
                - "urgency": str
            - "confidence": dict - Confidence scores for each entity
                - "name": float
                - "location": float
                - "incident_type": float
                - "urgency": float
    
    Example:
        >>> extract_entities("मेरा नाम राम है, दिल्ली में दुर्घटना हुई, तुरंत आओ")
        {
            "entities": {
                "name": "Ram",
                "location": "Delhi",
                "incident_type": "accident",
                "urgency": "critical"
            },
            "confidence": {
                "name": 0.9,
                "location": 0.8,
                "incident_type": 0.7,
                "urgency": 1.0
            }
        }
    """
    if not text or not text.strip():
        # Return empty entities with low confidence
        return {
            "entities": {
                "name": None,
                "location": None,
                "incident_type": None,
                "urgency": UrgencyLevel.MEDIUM.value
            },
            "confidence": {
                "name": 0.0,
                "location": 0.0,
                "incident_type": 0.0,
                "urgency": 0.3
            }
        }
    
    logger.debug(f"Extracting entities from text: {text[:100]}...")
    
    # Extract each entity type
    name, name_confidence = extract_name(text)
    location, location_confidence = extract_location(text)
    incident_type, incident_confidence = extract_incident_type(text)
    urgency, urgency_confidence = extract_urgency(text)
    
    # Build result dictionary
    result = {
        "entities": {
            "name": name,
            "location": location,
            "incident_type": incident_type,
            "urgency": urgency
        },
        "confidence": {
            "name": round(float(name_confidence), 3),
            "location": round(float(location_confidence), 3),
            "incident_type": round(float(incident_confidence), 3),
            "urgency": round(float(urgency_confidence), 3)
        }
    }
    
    # Log extraction results
    logger.info(
        f"Entities extracted - name: {name}, location: {location}, "
        f"incident_type: {incident_type}, urgency: {urgency}"
    )
    
    return result

