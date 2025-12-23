"""
Decision Engine: Escalation Logic

This module implements deterministic rules for human-in-the-loop escalation.
OpenAI MUST NOT trigger escalation - all logic is local and explainable.

Naming Philosophy:
- We use "decision_engine" instead of "ai_agent" to emphasize that this is
  a deterministic decision-making system, not an autonomous AI agent.
- Decision engine clearly describes our role: making escalation decisions
  based on explicit rules, not autonomous agent behavior.
- This naming makes it clear that escalation decisions are deterministic and
  explainable, not black-box AI agent decisions.

Escalation Rules (all deterministic):
1. If urgency_score > threshold → escalate
2. If clarity drops too low → escalate
3. If panic persists → escalate
4. If critical fields missing after N questions → escalate
5. If explicit human help request → escalate
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Escalation thresholds (deterministic, configurable)
URGENCY_ESCALATION_THRESHOLD = 0.7  # Escalate if urgency score > 0.7
CLARITY_ESCALATION_THRESHOLD = 0.3  # Escalate if clarity < 0.3
PANIC_PERSISTENCE_THRESHOLD = 3     # Escalate if panic detected 3+ times
CRITICAL_FIELDS_MISSING_THRESHOLD = 5  # Escalate if critical fields missing after 5 questions

# Critical fields that must be collected
CRITICAL_FIELDS = ["location", "incident_type"]


def check_escalation_required(
    urgency_score: float,
    urgency_level: str,
    clarity_avg: float,
    emotion_history: list,
    missing_fields: list,
    question_count: int,
    explicit_human_request: bool = False,
    immediate_danger: bool = False
) -> Dict[str, any]:
    """
    Determine if human intervention is required using deterministic rules.
    
    This function implements explicit, explainable escalation logic.
    OpenAI is NOT used for escalation decisions.
    
    Escalation Rules (any one can trigger escalation):
    1. Urgency threshold: urgency_score > URGENCY_ESCALATION_THRESHOLD
    2. Clarity threshold: clarity_avg < CLARITY_ESCALATION_THRESHOLD
    3. Panic persistence: panic detected PANIC_PERSISTENCE_THRESHOLD+ times
    4. Missing critical fields: critical fields missing after N questions
    5. Explicit request: user directly asks for human operator
    
    Args:
        urgency_score: Calculated urgency score (0.0 to 1.0)
        urgency_level: Urgency level ("critical", "high", "medium", "low")
        clarity_avg: Average clarity score (0.0 to 1.0)
        emotion_history: List of recent emotions
        missing_fields: List of missing critical fields
        question_count: Number of questions asked so far
        explicit_human_request: Whether user explicitly requested human help
    
    Returns:
        dict: Escalation decision with keys:
            - "human_required": bool - True if escalation needed
            - "reason": str - Reason for escalation (None if no escalation)
            - "priority": str - "critical" | "high" | "medium" | "low"
    """
    human_required = False
    reason = None
    priority = "medium"
    
    # Rule 1: Urgency threshold
    if urgency_score > URGENCY_ESCALATION_THRESHOLD:
        human_required = True
        reason = f"High urgency score ({urgency_score:.2f}) exceeds threshold ({URGENCY_ESCALATION_THRESHOLD})"
        priority = urgency_level
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # Rule 2: Clarity threshold
    if clarity_avg < CLARITY_ESCALATION_THRESHOLD:
        human_required = True
        reason = f"Low clarity ({clarity_avg:.2f}) below threshold ({CLARITY_ESCALATION_THRESHOLD})"
        priority = "high"  # Low clarity = high priority for human help
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # Rule 3: Panic persistence (only escalate if panic persists across multiple interactions)
    # Don't escalate on first panic - allow conversation to continue
    panic_count = emotion_history.count("panic") if emotion_history else 0
    # Only escalate if panic detected in last 3+ consecutive interactions
    recent_panic = sum(1 for e in emotion_history[-3:] if e == "panic") if len(emotion_history) >= 3 else panic_count
    if recent_panic >= PANIC_PERSISTENCE_THRESHOLD:
        human_required = True
        reason = f"Panic detected {recent_panic} times in recent interactions (threshold: {PANIC_PERSISTENCE_THRESHOLD})"
        priority = "critical"
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # Rule 4: Missing critical fields
    critical_missing = [f for f in missing_fields if f in CRITICAL_FIELDS]
    if critical_missing and question_count >= CRITICAL_FIELDS_MISSING_THRESHOLD:
        human_required = True
        reason = f"Critical fields missing ({', '.join(critical_missing)}) after {question_count} questions"
        priority = "high"
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # Rule 5: Immediate danger indicator (Layer 2 field)
    # If fire spreading, weapon, bleeding, or trapped - escalate immediately
    if immediate_danger:
        human_required = True
        reason = "Immediate danger detected (fire spreading, weapon, bleeding, or trapped)"
        priority = "critical"
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # Rule 6: Explicit human request
    if explicit_human_request:
        human_required = True
        reason = "User explicitly requested human assistance"
        priority = "high"
        logger.warning(f"Escalation triggered: {reason}")
        return {
            "human_required": True,
            "reason": reason,
            "priority": priority
        }
    
    # No escalation needed
    return {
        "human_required": False,
        "reason": None,
        "priority": None
    }


def detect_explicit_human_request(text: str) -> bool:
    """
    Detect if user explicitly requests human help.
    
    This is a deterministic keyword-based check.
    
    Args:
        text: User's transcribed speech
    
    Returns:
        bool: True if explicit human request detected
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Keywords indicating explicit human request
    human_request_keywords = [
        "human", "person", "operator", "dispatcher",
        "मानव", "व्यक्ति", "ऑपरेटर",
        "talk to human", "speak to person", "human help",
        "मानव से बात", "व्यक्ति से बात"
    ]
    
    for keyword in human_request_keywords:
        if keyword in text_lower:
            logger.debug(f"Explicit human request detected: '{keyword}' in text")
            return True
    
    return False
