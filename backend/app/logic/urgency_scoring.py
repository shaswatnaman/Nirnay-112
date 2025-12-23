"""
Decision Engine: Urgency Scoring Layer

This module implements urgency scoring using explicit, deterministic rules.
OpenAI is NOT used for scoring - all logic is local and explainable.

Naming Philosophy:
- We use "decision_engine" instead of "ai_agent" to emphasize that this is
  a deterministic decision-making system, not an autonomous AI agent.
- Decision engine clearly describes our role: making decisions based on
  explicit rules and formulas, not autonomous agent behavior.
- This naming makes it clear that decisions are deterministic and explainable,
  not black-box AI agent decisions.

Urgency Score Formula:
urgency_score = 
  w1 * intent_weight +
  w2 * stress_score +
  w3 * repetition_score +
  w4 * (1 - clarity_avg) +
  w5 * time_pressure +
  w6 * urgency_signals

Where:
- intent_weight: Based on incident type (fire=0.95, medical=0.9, etc.)
- stress_score: Deterministic stress score (0.0-1.0) from stress_estimator
  * Calculated from panic keywords, speaking rate, exclamations, repetition
  * NO LLM emotion labels - completely rule-based
- repetition_score: Normalized repetition count (0.0-1.0)
- clarity_avg: Speech clarity (inverted: low clarity = high urgency)
- time_pressure: Time elapsed (longer = more urgent)
- urgency_signals: Urgency keywords detected (jaldi, abhi, emergency, etc.)

All weights are configurable and documented.

Why Deterministic Stress Instead of LLM Emotion Labels:
1. Consistency: Rule-based stress scoring is deterministic and reproducible
   - Same input always produces same output
   - No LLM variability or hallucinations
2. Explainability: Every stress score can be traced to specific signals
   - Panic keywords found: ["मदद", "जल्दी"]
   - Speaking rate: 4.2 words/second
   - Exclamation count: 3
   - Repetition count: 2
3. Safety: LLM emotion labels can hallucinate or misclassify
   - LLM might label "calm" when user is actually panicking
   - LLM might hallucinate "panic" when user is actually calm
   - Deterministic stress uses observable signals (keywords, rate, etc.)
4. Performance: Rule-based scoring is faster and cheaper
   - No API calls needed
   - No rate limits or costs
5. Reliability: Works even if LLM is unavailable or returns errors
   - Stress estimator is completely local
   - No dependency on external services
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from app.nlp.india_keywords import detect_urgency_signals

logger = logging.getLogger(__name__)

# Configurable weights for urgency scoring
# These can be tuned based on real-world performance
# Note: Weights are multiplied by normalized values (0.0-1.0), so total can exceed 1.0
# This allows for proper urgency scaling (fire + high stress should be critical)
WEIGHTS = {
    "intent": 0.5,      # Weight for intent-based urgency (incident type is most important)
    "stress": 0.25,     # Weight for deterministic stress score (replaces LLM emotion)
    "repetition": 0.15, # Weight for repetition (indicates panic/confusion)
    "clarity": 0.05,    # Weight for clarity (low clarity = higher urgency)
    "time_pressure": 0.05,  # Weight for time-based urgency
    "urgency_signals": 0.1  # Weight for urgency keyword signals (e.g., "jaldi", "abhi", "emergency")
}

# Intent urgency mapping (deterministic, not from OpenAI)
# Maps all possible intent values from signal extraction to urgency weights
INTENT_URGENCY_MAP = {
    "medical_emergency": 0.9,  # Medical emergencies are highly urgent
    "fire": 0.95,              # Fire is extremely urgent
    "road_accident": 0.85,     # Road accidents are very urgent
    "crime": 0.8,              # Crime incidents are urgent
    "domestic_emergency": 0.75, # Domestic violence is urgent
    "natural_disaster": 0.9,   # Natural disasters are highly urgent
    "industrial_accident": 0.85, # Industrial accidents are very urgent
    "public_transport": 0.85,  # Public transport incidents are very urgent
    "mental_health": 0.8,      # Mental health crises are urgent
    "police": 0.8,             # Police incidents are urgent (legacy mapping)
    "non_emergency": 0.2,      # Non-emergencies are low urgency
    "unclear": 0.5             # Unclear intent = medium urgency
}

# NOTE: Emotion urgency mapping removed - replaced with deterministic stress_score
# Stress score (0.0-1.0) is calculated by stress_estimator using:
# - Panic keyword frequency (Hindi + English)
# - Speaking rate (words per second)
# - Exclamation usage
# - Repetition count
# This is safer and more reliable than LLM emotion labels


def calculate_urgency_score(
    intent: str,
    stress_score: float,
    repetition_count: int,
    clarity_avg: float,
    time_elapsed_seconds: float,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Calculate urgency score using deterministic ML formula.
    
    This is a deterministic, explainable scoring system.
    OpenAI is NOT used for scoring - all logic is local.
    
    Formula:
        urgency_score = 
            w_intent * intent_weight +
            w_stress * stress_score +
            w_repetition * repetition_weight +
            w_clarity * (1 - clarity_avg) +
            w_time * time_weight +
            w_urgency_signals * urgency_signal_weight
    
    Where:
        - intent_weight: Based on incident type (0.0-1.0)
        - stress_score: Deterministic stress score from stress_estimator (0.0-1.0)
        - repetition_weight: Normalized repetition count (0.0-1.0)
        - clarity_weight: Inverted clarity (low clarity = high urgency)
        - time_weight: Normalized time elapsed (0.0-1.0)
        - urgency_signal_weight: Urgency keywords detected (0.0 or 1.0)
    
    Args:
        intent: Intent classification ("medical_emergency", "fire", "crime", etc.)
        stress_score: Deterministic stress score (0.0 to 1.0) from stress_estimator
                     Replaces LLM emotion labels for safety and consistency
        repetition_count: Number of times user repeated themselves
        clarity_avg: Average clarity score (0.0 to 1.0)
        time_elapsed_seconds: Time elapsed since call started
        context: Optional context object for additional signals (transcript, etc.)
    
    Returns:
        dict: Urgency score breakdown with keys:
            - "urgency_score": float - Overall urgency score (0.0 to 1.0)
            - "urgency_level": str - "critical" | "high" | "medium" | "low"
            - "breakdown": dict - Component scores for explainability
    """
    # Component 1: Intent-based urgency
    # Normalize intent to handle variations (e.g., "fire" vs "fire_emergency")
    normalized_intent = intent.lower().replace("_emergency", "").replace("_", "_")
    intent_weight = INTENT_URGENCY_MAP.get(normalized_intent, INTENT_URGENCY_MAP.get(intent, 0.5))  # Try normalized first, then original, then default
    
    # Special case: Dog bites are medical emergencies but should NOT be critical
    # They need medical attention but are not life-threatening like heart attacks or severe bleeding
    is_dog_bite = False
    if context:
        transcript = context.get("transcript", "") or context.get("user_input_buffer", "")
        if transcript:
            dog_bite_keywords = ["dog bite", "dog_bite", "dogbite", "कुत्ते ने काट", "कुत्ता काट", "कुत्ते काट", 
                                 "कुत्ता ने काट", "कुत्ते", "कुत्ता", "bite", "काट लिया", "काटा", "काट गया"]
            transcript_lower = transcript.lower()
            is_dog_bite = any(keyword in transcript_lower for keyword in dog_bite_keywords)
    
    # If it's a dog bite, reduce urgency weight (dog bites are urgent but not critical)
    # Dog bites need medical attention but are not life-threatening like heart attacks
    if is_dog_bite and intent_weight >= 0.8:  # Only reduce if it's a high-urgency medical emergency
        intent_weight = 0.7  # Reduce from 0.9 to 0.7 (high urgency, but not critical - stays below 0.75 threshold)
        logger.info(f"Dog bite detected - reducing urgency weight from {INTENT_URGENCY_MAP.get(normalized_intent, 0.9)} to 0.7")
    
    intent_score = WEIGHTS["intent"] * intent_weight
    
    # Component 2: Stress-based urgency (replaces LLM emotion labels)
    # Use deterministic stress_score directly (0.0-1.0)
    # This is safer than LLM emotion labels because:
    # - Deterministic: same input always produces same output
    # - Explainable: can trace to specific signals (keywords, rate, etc.)
    # - No hallucinations: based on observable patterns, not LLM interpretation
    # - Reliable: works even if LLM is unavailable
    stress_score_normalized = max(0.0, min(1.0, stress_score))  # Clamp to [0.0, 1.0]
    stress_score_component = WEIGHTS["stress"] * stress_score_normalized
    
    # Component 3: Repetition-based urgency
    # More repetition = higher urgency (indicates panic/confusion)
    repetition_weight = min(repetition_count / 5.0, 1.0)  # Cap at 1.0
    repetition_score = WEIGHTS["repetition"] * repetition_weight
    
    # Component 4: Clarity-based urgency
    # Lower clarity = higher urgency (harder to understand = more urgent)
    clarity_weight = 1.0 - clarity_avg  # Invert: low clarity = high urgency
    clarity_score = WEIGHTS["clarity"] * clarity_weight
    
    # Component 5: Urgency signals from keywords (India-specific)
    # Check if user used urgency/panic keywords like "jaldi", "abhi", "emergency", "bachao"
    urgency_signals_detected = False
    if context:
        # Get transcript from context if available
        transcript = context.get("transcript", "") or context.get("user_input_buffer", "")
        if transcript:
            urgency_signals_detected = detect_urgency_signals(transcript)
    
    # If urgency signals detected, boost urgency score
    # Apply as weighted component (0.0-1.0 scale) for proper normalization
    urgency_signal_weight = 1.0 if urgency_signals_detected else 0.0
    urgency_signal_score = WEIGHTS.get("urgency_signals", 0.1) * urgency_signal_weight
    
    # Component 6: Time-based urgency
    # Longer calls = higher urgency (indicates complexity/severity)
    time_weight = min(time_elapsed_seconds / 300.0, 1.0)  # Cap at 5 minutes
    time_score = WEIGHTS["time_pressure"] * time_weight
    
    # Calculate total urgency score (including urgency signal boost)
    # Formula: urgency_score = Σ(weight_i * component_i)
    total_score = (
        intent_score +
        stress_score_component +
        repetition_score +
        clarity_score +
        time_score +
        urgency_signal_score
    )
    
    # Normalize to [0.0, 1.0]
    total_score = min(max(total_score, 0.0), 1.0)
    
    # Map to urgency level
    # Adjusted thresholds: fire/medical emergencies with panic should be critical
    # Fire (0.95 intent) + Panic (0.75 emotion) + Urgency signals = ~0.77 -> critical
    if total_score >= 0.75:  # Lowered from 0.8 to catch fire emergencies better
        urgency_level = "critical"
    elif total_score >= 0.55:  # Lowered from 0.6
        urgency_level = "high"
    elif total_score >= 0.35:  # Lowered from 0.4
        urgency_level = "medium"
    else:
        urgency_level = "low"
    
    breakdown = {
        "intent_score": intent_score,
        "stress_score": stress_score_component,
        "stress_score_raw": stress_score_normalized,  # Raw stress score before weighting
        "repetition_score": repetition_score,
        "clarity_score": clarity_score,
        "time_score": time_score,
        "urgency_signal_boost": urgency_signal_score,
        "urgency_signals_detected": urgency_signals_detected,
        "total": total_score
    }
    
    logger.info(
        f"Urgency score calculated: {total_score:.2f} ({urgency_level}) - "
        f"Intent: {intent} (weight: {intent_weight:.2f}), Stress: {stress_score_normalized:.2f} (component: {stress_score_component:.2f}), "
        f"Breakdown: {breakdown}"
    )
    
    return {
        "urgency_score": total_score,
        "urgency_level": urgency_level,
        "breakdown": breakdown
    }


def get_urgency_threshold(urgency_level: str) -> float:
    """
    Get escalation threshold for a given urgency level.
    
    These thresholds are deterministic and configurable.
    
    Args:
        urgency_level: Urgency level ("critical", "high", "medium", "low")
    
    Returns:
        float: Escalation threshold (0.0 to 1.0)
    """
    thresholds = {
        "critical": 0.7,  # Critical: escalate if score > 0.7
        "high": 0.6,      # High: escalate if score > 0.6
        "medium": 0.5,    # Medium: escalate if score > 0.5
        "low": 0.4        # Low: escalate if score > 0.4
    }
    return thresholds.get(urgency_level, 0.5)

