"""
Escalation module for detecting when human intervention is required.

This module determines if a human operator should take over the conversation
from the AI based on various escalation triggers.

Escalation Triggers:
- High urgency incidents (critical or high urgency levels)
- Missing critical fields (location, incident_type)
- Panic/emotional keywords in user speech
- Explicit requests for human assistance
- Low conversation progress after multiple attempts
"""

import re
import logging
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Panic and emotional keywords in Hindi/Hinglish/English
# These indicate high stress, fear, or urgent need for help
PANIC_KEYWORDS = [
    # Hindi panic indicators
    "तुरंत",  # immediately
    "जल्दी",  # quickly/hurry
    "मदद",  # help
    "बचाओ",  # save me
    "मर रहा",  # dying
    "मर रही",  # dying (feminine)
    "बेहोश",  # unconscious
    "खून",  # blood
    "आग",  # fire
    "डर",  # fear
    "भागो",  # run
    "खतरा",  # danger
    "बहुत बुरा",  # very bad
    "नहीं सहन हो रहा",  # can't bear it
    "दर्द",  # pain (severe)
    "सांस नहीं आ रही",  # can't breathe
    "सांस नहीं आ रहा",  # can't breathe
    
    # English panic indicators
    "help", "urgent", "emergency", "dying", "unconscious",
    "blood", "fire", "danger", "run", "dangerous",
    "can't breathe", "can't move", "severe pain",
    "terrible", "awful", "horrible", "scared", "afraid",
    
    # Hinglish panic indicators (code-switching)
    "help चाहिए",  # need help
    "urgent है",  # is urgent
    "emergency है",  # is emergency
    "तुरंत आओ",  # come immediately
    "जल्दी आओ",  # come quickly
    "मदद चाहिए",  # need help
    "बचाओ मुझे",  # save me
]

# Emotional distress keywords
# These indicate emotional state that may require human empathy
EMOTIONAL_KEYWORDS = [
    # Hindi emotional indicators
    "डर लग रहा",  # feeling scared
    "घबराहट",  # panic/anxiety
    "चिंता",  # worry
    "परेशान",  # troubled
    "उदास",  # sad
    "रो रहा",  # crying
    "रो रही",  # crying (feminine)
    "बहुत डर",  # very scared
    
    # English emotional indicators
    "scared", "afraid", "worried", "anxious", "panicking",
    "crying", "terrified", "frightened", "distressed",
    
    # Hinglish emotional indicators
    "डर लग रहा है",  # feeling scared
    "scared हूं",  # I am scared
    "worried हूं",  # I am worried
]

# Explicit requests for human help
# User directly asking to speak with a human operator
HUMAN_HELP_REQUESTS = [
    # Hindi requests
    "इंसान से बात",  # talk to human
    "व्यक्ति से बात",  # talk to person
    "मानव से बात",  # talk to human
    "ऑपरेटर",  # operator
    "एजेंट",  # agent
    "कर्मचारी",  # staff/employee
    "व्यक्ति",  # person
    "इंसान",  # human
    
    # English requests
    "human", "person", "operator", "agent", "staff",
    "talk to human", "speak to person", "real person",
    "actual person", "human operator", "human agent",
    
    # Hinglish requests
    "human से बात",  # talk to human
    "operator चाहिए",  # need operator
    "person से बात",  # talk to person
]

# Critical fields that must be present for proper incident handling
# Missing these after multiple questions indicates need for human help
CRITICAL_FIELDS = ["location", "incident_type"]


def check_escalation_required(
    urgency: str,
    missing_fields: List[str],
    completeness: float,
    user_input: str,
    question_count: int
) -> Dict:
    """
    Determine if human intervention is required based on escalation triggers.
    
    This function checks multiple conditions to determine if the conversation
    should be escalated to a human operator. Returns JSON with human_required
    flag and reason for escalation.
    
    Escalation Triggers (any one can trigger escalation):
    1. High urgency: critical or high urgency levels
    2. Missing critical fields: location or incident_type missing after multiple questions
    3. Panic/emotional keywords: multiple panic indicators or emotional distress
    4. Explicit human help requests: user directly asking for human operator
    5. Low progress: very low completeness after many questions
    
    Args:
        urgency: Urgency level string ("critical", "high", "medium", "low")
        missing_fields: List of missing field names (e.g., ["location", "name"])
        completeness: Overall completeness score (0.0 to 1.0)
        user_input: Accumulated user input text (may be fragmented)
        question_count: Number of questions asked so far
    
    Returns:
        dict: JSON with keys:
            - "human_required": bool - True if human intervention needed
            - "reason": str or None - Reason for escalation (None if no escalation)
    
    Example:
        >>> check_escalation_required(
        ...     urgency="critical",
        ...     missing_fields=["name"],
        ...     completeness=0.6,
        ...     user_input="तुरंत मदद चाहिए",
        ...     question_count=2
        ... )
        {
            "human_required": True,
            "reason": "Critical urgency level detected"
        }
    """
    # Initialize result
    # Default: no escalation needed
    human_required = False
    reason = None
    
    # Check 1: High Urgency
    # Critical or high urgency incidents require immediate human attention
    # These are life-threatening or time-sensitive situations
    if urgency in ["critical", "high"]:
        human_required = True
        if urgency == "critical":
            reason = "Critical urgency level detected - immediate human intervention required"
        else:
            reason = "High urgency level detected - human intervention recommended"
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason
        }
    
    # Check 2: Missing Critical Fields
    # Location and incident_type are essential for proper emergency response
    # If these are missing after multiple questions, user may need human help
    # to clarify or provide information more naturally
    critical_fields = CRITICAL_FIELDS
    missing_critical = [f for f in missing_fields if f in critical_fields]
    
    if missing_critical:
        # Escalate if critical fields missing after 4+ questions
        # This indicates the AI is struggling to extract essential information
        if question_count >= 4:
            human_required = True
            reason = (
                f"Missing critical fields ({', '.join(missing_critical)}) "
                f"after {question_count} questions - human assistance needed"
            )
            logger.warning(f"Escalation triggered: {reason}")
            return {
                "human_required": True,
                "reason": reason
            }
    
    # Check 3: Panic/Emotional Keywords
    # Multiple panic indicators or emotional distress signals need for human empathy
    # Panic can make it difficult for users to provide clear information
    if user_input:
        user_lower = user_input.lower()
        
        # Count panic keywords
        # Multiple panic indicators (2+) suggest high stress
        panic_count = sum(
            1 for keyword in PANIC_KEYWORDS 
            if keyword.lower() in user_lower
        )
        
        # Count emotional keywords
        emotional_count = sum(
            1 for keyword in EMOTIONAL_KEYWORDS 
            if keyword.lower() in user_lower
        )
        
        # Escalate if multiple panic indicators
        # Panic makes it hard to communicate effectively - human needed
        if panic_count >= 2:
            human_required = True
            reason = (
                f"Multiple panic indicators detected in speech "
                f"({panic_count} keywords) - human intervention needed"
            )
            logger.warning(f"Escalation triggered: {reason}")
            return {
                "human_required": True,
                "reason": reason
            }
        
        # Escalate if emotional distress + panic
        # Combination of emotional and panic keywords indicates severe distress
        if emotional_count >= 1 and panic_count >= 1:
            human_required = True
            reason = (
                "Emotional distress and panic indicators detected - "
                "human empathy and assistance required"
            )
            logger.warning(f"Escalation triggered: {reason}")
            return {
                "human_required": True,
                "reason": reason
            }
    
    # Check 4: Explicit Human Help Requests
    # If user directly asks for human operator, honor the request
    # This shows user preference for human interaction
    if user_input:
        user_lower = user_input.lower()
        for request in HUMAN_HELP_REQUESTS:
            if request.lower() in user_lower:
                human_required = True
                reason = "User explicitly requested human assistance"
                logger.warning(f"Escalation triggered: {reason}")
                return {
                    "human_required": True,
                    "reason": reason
                }
    
    # Check 5: Low Progress After Multiple Attempts
    # Very low completeness after many questions indicates communication difficulty
    # This could be due to:
    # - Language barriers
    # - Technical issues
    # - User confusion
    # - Need for more natural conversation flow
    if completeness < 0.3 and question_count >= 5:
        human_required = True
        reason = (
            f"Low conversation progress (completeness: {completeness:.2f}) "
            f"after {question_count} questions - human assistance recommended"
        )
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason
        }
    
    # No escalation needed
    # All checks passed - AI can continue handling the conversation
    return {
        "human_required": False,
        "reason": None
    }


def check_panic_indicators(user_input: str) -> Dict:
    """
    Check for panic indicators in user input.
    
    Helper function to detect panic/emotional keywords separately.
    Useful for logging and analysis.
    
    Args:
        user_input: User input text to analyze
    
    Returns:
        dict: Panic analysis with keys:
            - "has_panic": bool - True if panic keywords found
            - "panic_count": int - Number of panic keywords
            - "emotional_count": int - Number of emotional keywords
            - "keywords_found": List[str] - List of found keywords
    """
    if not user_input:
        return {
            "has_panic": False,
            "panic_count": 0,
            "emotional_count": 0,
            "keywords_found": []
        }
    
    user_lower = user_input.lower()
    panic_found = []
    emotional_found = []
    
    # Find panic keywords
    for keyword in PANIC_KEYWORDS:
        if keyword.lower() in user_lower:
            panic_found.append(keyword)
    
    # Find emotional keywords
    for keyword in EMOTIONAL_KEYWORDS:
        if keyword.lower() in user_lower:
            emotional_found.append(keyword)
    
    return {
        "has_panic": len(panic_found) > 0 or len(emotional_found) > 0,
        "panic_count": len(panic_found),
        "emotional_count": len(emotional_found),
        "keywords_found": panic_found + emotional_found
    }
