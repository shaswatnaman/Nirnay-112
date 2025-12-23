"""
India-Specific Incident Keywords and Phrases

This module provides comprehensive keyword mappings for incident classification
in the Indian context, supporting Hindi, Hinglish, and regional variations.

Used for:
1. NLP seed list (entity extraction)
2. Fallback rule engine (when OpenAI fails)
3. OpenAI grounding context (improve accuracy)
4. Recruiter-visible "India-aware design"
"""

from typing import Dict, List, Set
from enum import Enum


class IncidentCategory(Enum):
    """Standard incident categories."""
    MEDICAL_EMERGENCY = "medical_emergency"
    ROAD_ACCIDENT = "road_accident"
    FIRE_EMERGENCY = "fire"
    CRIME_VIOLENCE = "crime"
    DOMESTIC_VIOLENCE = "domestic_emergency"
    NATURAL_DISASTER = "natural_disaster"
    INDUSTRIAL_ACCIDENT = "industrial_accident"
    PUBLIC_TRANSPORT = "public_transport"
    MENTAL_HEALTH = "mental_health"
    UNKNOWN = "unknown"


# 🔴 1. MEDICAL EMERGENCY
MEDICAL_KEYWORDS = {
    # Hindi / Hinglish
    "saans nahi aa rahi", "saans nahi aa raha", "breathing problem", "breathing nahi ho rahi",
    "behosh ho gaya", "behosh ho gayi", "behosh", "unconscious",
    "heart problem", "dil ki problem", "heart attack lag raha hai", "heart attack",
    "chest pain", "chhati mein dard", "chest mein dard",
    "khoon nikal raha hai", "khoon beh raha hai", "bleeding ho rahi hai", "bleeding",
    "chakkar aa rahe hain", "chakkar aa raha hai", "dizziness", "dizzy",
    "sugar low", "sugar high", "sugar kam hai", "sugar zyada hai",
    "bp badh gaya", "bp kam hai", "bp high", "bp low", "blood pressure",
    "fit aa gaya", "fit", "seizure", "fits",
    "ulti ho rahi hai", "vomiting", "vomit",
    "bukhar bahut zyada", "fever", "high fever", "temperature",
    "pregnant pain", "delivery ka pain", "delivery", "pregnancy pain",
    "baccha paida hone wala hai", "delivery time",
    "dog bite", "dog_bite", "dogbite", "कुत्ते ने काट", "कुत्ता काट", "कुत्ते काट", "कुत्ता ने काट",
    "कुत्ते", "कुत्ता", "bite", "काट लिया", "काटा", "काट गया",
    "चोट", "injury", "injured", "hurt",
    # English
    "unconscious", "severe pain", "medical emergency", "critical condition",
    "patient serious", "emergency medical", "ambulance needed", "hospital needed"
}

# 🚗 2. ROAD ACCIDENT
ROAD_ACCIDENT_KEYWORDS = {
    # Hindi / Hinglish
    "accident ho gaya", "accident", "gaadi takra gayi", "car accident",
    "bike slip ho gayi", "bike accident", "motorcycle accident",
    "truck ne maar diya", "truck accident", "truck hit",
    "road pe gir gaya", "road pe accident", "highway accident",
    "flyover pe accident", "flyover accident",
    "footpath pe hit ho gaya", "footpath accident",
    "helmet nahi tha", "no helmet",
    "khoon beh raha hai", "bleeding from accident",
    # English
    "road accident", "collision", "hit and run", "injured badly",
    "car crash", "vehicle accident", "traffic accident"
}

# 🔥 3. FIRE EMERGENCY
FIRE_KEYWORDS = {
    # Hindi / Hinglish
    "aag lag gayi", "aag", "fire lag gaya", "fire",
    "gas cylinder blast", "cylinder phat gaya", "cylinder blast", "gas blast",
    "short circuit", "bijli se aag", "electric fire",
    "kitchen fire", "kitchen mein aag",
    "factory mein aag", "factory fire",
    "smoke aa raha hai", "dhuan bhar gaya", "smoke",
    "log phanse hue hain", "people trapped", "trapped in fire",
    # English
    "fire outbreak", "building on fire", "explosion", "smoke everywhere",
    "fire emergency", "burning"
}

# 🚨 4. CRIME / VIOLENCE
CRIME_KEYWORDS = {
    # Hindi / Hinglish
    "chori ho gayi", "chori", "theft", "robbery",
    "loot liya", "loot", "robbery",
    "chain snatching", "chain chheen li", "chain snatch",
    "phone chheen liya", "phone snatch", "mobile chheen liya",
    "maar peet ho rahi hai", "maar peet", "fighting",
    "ladayi ho rahi hai", "fight", "violence",
    "gunda log", "gunda", "goons",
    "dhamki de raha hai", "threat", "threatening",
    "assault", "attack",
    "stabbing", "knife nikala", "knife", "chaku",
    "gun dikhayi", "gun", "weapon",
    # English
    "attack", "violence", "threat", "weapon involved",
    "crime", "criminal", "robbery", "theft"
}

# 🏠 5. DOMESTIC VIOLENCE / FAMILY EMERGENCY
DOMESTIC_KEYWORDS = {
    # Hindi / Hinglish
    "ghar mein jhagda", "domestic fight", "family fight",
    "husband maar raha hai", "pati maar raha hai", "husband beating",
    "wife ko maar raha", "wife beating",
    "sasural wale maar rahe", "in-laws violence",
    "abuse ho raha hai", "abuse", "domestic abuse",
    "domestic violence", "family violence",
    "mental torture", "mental abuse",
    "children crying", "bachche danger mein hain", "children in danger",
    # English
    "domestic violence", "family emergency", "abuse", "child abuse"
}

# 🌊 6. NATURAL DISASTER / WEATHER
NATURAL_DISASTER_KEYWORDS = {
    # Hindi / Hinglish
    "flood aa gaya", "flood", "paani bhar gaya", "water flooding",
    "ghar doob gaya", "house flooded", "drowning",
    "bijli gir gayi", "lightning", "thunder",
    "landslide", "pahaad se pathar gir gaya", "rockslide",
    "earthquake", "bhookamp", "earthquake",
    "cyclone", "tufaan", "storm", "cyclone",
    "baarish bahut zyada", "heavy rain", "rainfall",
    "heat stroke", "loo lag gayi", "heat wave",
    # English
    "natural disaster", "flood", "earthquake", "storm", "cyclone"
}

# 🏭 7. INDUSTRIAL / WORKPLACE ACCIDENT
INDUSTRIAL_KEYWORDS = {
    # Hindi / Hinglish
    "factory accident", "factory mein accident",
    "machine mein haath aa gaya", "machine accident", "machine injury",
    "chemical leak", "chemical spill",
    "gas leak", "gas leak ho gaya",
    "mazdoor phans gaya", "worker trapped",
    "construction site accident", "construction accident",
    "building gir gayi", "building collapse",
    # English
    "industrial accident", "workplace accident", "factory accident"
}

# 🚆 8. PUBLIC TRANSPORT INCIDENT
PUBLIC_TRANSPORT_KEYWORDS = {
    # Hindi / Hinglish
    "train accident", "train mein accident",
    "platform pe gir gaya", "platform accident",
    "metro mein problem", "metro accident", "metro issue",
    "bus accident", "bus mein accident",
    "overcrowding", "bheed zyada hai",
    "stampede", "bheed mein phas gaye", "stampede",
    # English
    "public transport", "train accident", "bus accident", "metro accident"
}

# 🧠 9. MENTAL HEALTH / DISTRESS
MENTAL_HEALTH_KEYWORDS = {
    # Hindi / Hinglish
    "suicide kar lega", "suicide", "jaan dene ki baat", "suicidal",
    "depression mein hai", "depression", "depressed",
    "mentally disturbed", "mental problem",
    "pagal ho raha hai", "mental breakdown",
    "kuchh bhi bol raha hai", "confused", "confusion",
    "ro raha hai", "crying", "crying continuously",
    "dar lag raha hai", "fear", "scared",
    # English
    "suicide", "mental health", "depression", "distress"
}

# ⚠️ 10. URGENCY / PANIC SIGNALS (Boost urgency score)
URGENCY_KEYWORDS = {
    # Hindi / Hinglish
    "jaldi bhejo", "jaldi", "fast", "quickly",
    "abhi", "now", "immediately", "right now",
    "please help", "help", "madad", "sahayata",
    "mar jayega", "mar jayegi", "will die", "dying",
    "bachao", "save", "rescue",
    "emergency", "emergency hai", "urgent",
    "kuchh karo", "do something", "help karo",
    "fast fast", "jaldi jaldi",
    "please sir", "please madam", "please",
    # English
    "urgent", "emergency", "critical", "immediate", "help needed"
}

# 📍 11. LOCATION / ADDRESS SIGNALS (India-Specific)
LOCATION_INDICATORS = {
    # Landmark style
    "mandir ke paas", "temple near", "temple",
    "masjid ke saamne", "mosque", "masjid",
    "school ke bagal", "school near", "school",
    "petrol pump ke paas", "petrol pump", "gas station",
    "chowk pe", "chowk", "square", "crossing",
    "naka pe", "naka", "checkpoint",
    "gali number", "gali", "lane", "street",
    "sector", "sector number",
    "village name", "village", "gaon",
    "thana ke paas", "police station near", "thana",
    "hospital ke saamne", "hospital near", "hospital",
    "metro station", "metro", "railway station", "station",
    "bus stop", "bus stand"
}

# 🔁 12. REPETITION / CONFUSION SIGNALS
REPETITION_SIGNALS = {
    "wahi baat baar baar", "same thing repeating",
    "same sentence repeat", "repeating",
    "unclear words", "unclear",
    "incomplete sentences", "incomplete",
    "silence gaps", "silence",
    "crying + speaking", "crying while speaking"
}

# 🌐 13. LANGUAGE / DIALECT MARKERS
LANGUAGE_MARKERS = {
    "pure Hindi": ["है", "हूँ", "हैं", "था", "थी"],
    "Hinglish": ["is", "are", "was", "the", "a", "an"],
    "broken English": ["me", "you", "he", "she", "it"],
    "local slang": ["hau", "haan ji", "bhaiya", "anna", "dada"],
    "regional accent": ["hau", "haan ji", "bhaiya", "anna"]
}


# Complete mapping of categories to keywords
INCIDENT_KEYWORD_MAP: Dict[IncidentCategory, Set[str]] = {
    IncidentCategory.MEDICAL_EMERGENCY: MEDICAL_KEYWORDS,
    IncidentCategory.ROAD_ACCIDENT: ROAD_ACCIDENT_KEYWORDS,
    IncidentCategory.FIRE_EMERGENCY: FIRE_KEYWORDS,
    IncidentCategory.CRIME_VIOLENCE: CRIME_KEYWORDS,
    IncidentCategory.DOMESTIC_VIOLENCE: DOMESTIC_KEYWORDS,
    IncidentCategory.NATURAL_DISASTER: NATURAL_DISASTER_KEYWORDS,
    IncidentCategory.INDUSTRIAL_ACCIDENT: INDUSTRIAL_KEYWORDS,
    IncidentCategory.PUBLIC_TRANSPORT: PUBLIC_TRANSPORT_KEYWORDS,
    IncidentCategory.MENTAL_HEALTH: MENTAL_HEALTH_KEYWORDS,
}


def classify_incident_by_keywords(text: str) -> str:
    """
    Classify incident type using keyword matching (fallback rule engine).
    
    This is used when OpenAI fails or as a validation step.
    
    Args:
        text: User's transcribed speech (Hindi/Hinglish/English)
    
    Returns:
        str: Incident category (e.g., "medical_emergency", "road_accident", etc.)
    """
    if not text:
        return IncidentCategory.UNKNOWN.value
    
    text_lower = text.lower()
    
    # Count matches for each category
    category_scores: Dict[IncidentCategory, int] = {}
    
    for category, keywords in INCIDENT_KEYWORD_MAP.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 1
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        return best_category.value
    
    return IncidentCategory.UNKNOWN.value


def detect_urgency_signals(text: str) -> bool:
    """
    Detect urgency/panic signals in text.
    
    Args:
        text: User's transcribed speech
    
    Returns:
        bool: True if urgency signals detected
    """
    if not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in URGENCY_KEYWORDS)


def detect_repetition_signals(text: str) -> bool:
    """
    Detect repetition/confusion signals in text.
    
    Args:
        text: User's transcribed speech
    
    Returns:
        bool: True if repetition signals detected
    """
    if not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in REPETITION_SIGNALS)


def get_all_keywords_for_category(category: str) -> List[str]:
    """
    Get all keywords for a given incident category.
    
    Useful for OpenAI prompts and documentation.
    
    Args:
        category: Incident category (e.g., "medical_emergency")
    
    Returns:
        List[str]: List of keywords for that category
    """
    category_enum = IncidentCategory(category) if category in [c.value for c in IncidentCategory] else None
    if category_enum and category_enum in INCIDENT_KEYWORD_MAP:
        return list(INCIDENT_KEYWORD_MAP[category_enum])
    return []


def get_keywords_summary() -> Dict[str, List[str]]:
    """
    Get summary of all keywords by category.
    
    Useful for OpenAI prompts and documentation.
    
    Returns:
        Dict[str, List[str]]: Mapping of category to keywords
    """
    return {
        category.value: list(keywords)
        for category, keywords in INCIDENT_KEYWORD_MAP.items()
    }




