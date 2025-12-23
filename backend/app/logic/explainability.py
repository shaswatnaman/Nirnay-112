"""
Decision Explainability Module

This module provides human-readable explanations for AI decisions without changing
the decision logic itself. All explanations are deterministic and based on existing signals.

Key Principles:
- No ML, no OpenAI calls
- Deterministic logic only
- Uses existing signals (emotion, intent, clarity, repetition)
- JSON-serializable output
- Does NOT change escalation thresholds or decision logic
"""

import logging
from typing import Dict, Optional, List, Tuple, Any
from app.logic.context_memory import ContextMemory

logger = logging.getLogger(__name__)


def explain_decision(
    context: ContextMemory,
    urgency_score: float,
    escalation_decision: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate human-readable explanation for AI decision.
    
    This function explains WHY a decision was made without changing the decision logic.
    All explanations are deterministic and based on existing signals.
    
    Args:
        context: ContextMemory object containing conversation state
        urgency_score: Calculated urgency score (0.0 to 1.0)
        escalation_decision: Escalation decision dict with keys:
            - "human_required": bool
            - "reason": str or None
            - "priority": str or None
    
    Returns:
        dict: Explanation with keys:
            - "urgency_score": float
            - "urgency_level": str ("critical" | "high" | "medium" | "low")
            - "top_3_contributing_factors": List[str] - Human-readable factors
            - "why_escalated": str or None - Reason for escalation
            - "confidence_warnings": List[str] - Warnings about low confidence signals
    """
    # Determine urgency level from score
    if urgency_score >= 0.75:
        urgency_level = "critical"
    elif urgency_score >= 0.55:
        urgency_level = "high"
    elif urgency_score >= 0.35:
        urgency_level = "medium"
    else:
        urgency_level = "low"
    
    # Collect contributing factors (deterministic, based on existing signals)
    contributing_factors = []
    
    # Factor 1: Intent/Incident Type
    if context.incident_type:
        intent_factor = _explain_intent_factor(context.incident_type, context.incident_confidence)
        if intent_factor:
            contributing_factors.append(intent_factor)
    
    # Factor 2: Stress/Emotion indicators
    stress_factor = _explain_stress_factor(context)
    if stress_factor:
        contributing_factors.append(stress_factor)
    
    # Factor 3: Repetition
    if context.repetition_count > 0:
        repetition_factor = _explain_repetition_factor(context.repetition_count)
        if repetition_factor:
            contributing_factors.append(repetition_factor)
    
    # Factor 4: Clarity
    clarity_factor = _explain_clarity_factor(context.clarity_avg)
    if clarity_factor:
        contributing_factors.append(clarity_factor)
    
    # Factor 5: Urgency signals (if available in context)
    urgency_signals_factor = _explain_urgency_signals_factor(context)
    if urgency_signals_factor:
        contributing_factors.append(urgency_signals_factor)
    
    # Factor 6: Missing critical information
    missing_fields = context.get_missing_fields()
    if missing_fields:
        missing_factor = _explain_missing_fields_factor(missing_fields)
        if missing_factor:
            contributing_factors.append(missing_factor)
    
    # Get top 3 contributing factors (sorted by impact)
    top_3_factors = _rank_contributing_factors(contributing_factors, urgency_score)[:3]
    
    # Determine escalation reason
    why_escalated = None
    if escalation_decision.get("human_required", False):
        why_escalated = escalation_decision.get("reason", "Human intervention required")
    
    # Collect confidence warnings
    confidence_warnings = []
    
    # Warning: Low clarity
    if context.clarity_avg < 0.4:
        confidence_warnings.append(f"Low speech clarity ({context.clarity_avg:.2f}) - may affect understanding")
    
    # Warning: High repetition
    if context.repetition_count >= 3:
        confidence_warnings.append(f"High repetition detected ({context.repetition_count} times) - user may be distressed")
    
    # Warning: Low intent confidence
    if context.incident_confidence < 0.5 and context.incident_type:
        confidence_warnings.append(f"Low confidence in incident type ({context.incident_confidence:.2f})")
    
    # Warning: Missing critical fields
    critical_missing = [f for f in missing_fields if f in ["location", "incident_type"]]
    if critical_missing:
        confidence_warnings.append(f"Missing critical information: {', '.join(critical_missing)}")
    
    # Warning: Unclear intent
    if not context.incident_type or context.incident_type == "unclear":
        confidence_warnings.append("Incident type unclear - may need human clarification")
    
    explanation = {
        "urgency_score": round(urgency_score, 3),
        "urgency_level": urgency_level,
        "top_3_contributing_factors": top_3_factors,
        "why_escalated": why_escalated,
        "confidence_warnings": confidence_warnings
    }
    
    logger.debug(f"Decision explanation generated: {explanation}")
    
    return explanation


def _explain_intent_factor(incident_type: str, confidence: float) -> Optional[str]:
    """Explain intent/incident type contribution."""
    if not incident_type or incident_type == "unclear":
        return None
    
    # Map incident types to human-readable descriptions
    intent_descriptions = {
        "fire": "Fire emergency detected",
        "medical_emergency": "Medical emergency detected",
        "road_accident": "Road accident reported",
        "crime": "Crime incident reported",
        "domestic_emergency": "Domestic emergency reported",
        "natural_disaster": "Natural disaster reported",
        "other": "Other emergency type"
    }
    
    description = intent_descriptions.get(incident_type, f"{incident_type} incident")
    
    if confidence < 0.6:
        return f"{description} (low confidence: {confidence:.2f})"
    else:
        return description


def _explain_stress_factor(context: ContextMemory) -> Optional[str]:
    """Explain stress/emotion indicators."""
    if not context.emotion_history:
        return None
    
    # Count recent emotions
    recent_emotions = context.emotion_history[-5:] if len(context.emotion_history) >= 5 else context.emotion_history
    panic_count = sum(1 for e in recent_emotions if e == "panic")
    stressed_count = sum(1 for e in recent_emotions if e == "stressed" or e == "distress")
    
    if panic_count >= 2:
        return f"Panic detected ({panic_count} times in recent speech)"
    elif stressed_count >= 2:
        return f"Stress/distress indicators detected ({stressed_count} times)"
    elif panic_count == 1:
        return "Panic indicators present"
    elif stressed_count == 1:
        return "Stress indicators present"
    
    return None


def _explain_repetition_factor(repetition_count: int) -> Optional[str]:
    """Explain repetition contribution."""
    if repetition_count == 0:
        return None
    
    if repetition_count >= 5:
        return f"Very high repetition ({repetition_count} times) - strong distress indicator"
    elif repetition_count >= 3:
        return f"High repetition ({repetition_count} times) - user may be panicking"
    elif repetition_count >= 2:
        return f"Moderate repetition ({repetition_count} times) - user may be stressed"
    else:
        return f"Some repetition detected ({repetition_count} time)"


def _explain_clarity_factor(clarity_avg: float) -> Optional[str]:
    """Explain clarity contribution."""
    if clarity_avg >= 0.7:
        return None  # Good clarity, not a contributing factor
    
    if clarity_avg < 0.3:
        return f"Very low speech clarity ({clarity_avg:.2f}) - difficult to understand"
    elif clarity_avg < 0.5:
        return f"Low speech clarity ({clarity_avg:.2f}) - may affect information gathering"
    else:
        return f"Moderate speech clarity ({clarity_avg:.2f})"


def _explain_urgency_signals_factor(context: ContextMemory) -> Optional[str]:
    """Explain urgency keyword signals."""
    # Check if urgency keywords were detected (this would be in the context if available)
    # For now, we can infer from emotion history or other signals
    if context.emotion_history:
        recent_panic = sum(1 for e in context.emotion_history[-3:] if e == "panic")
        if recent_panic >= 2:
            return "Urgent keywords detected (e.g., 'jaldi', 'abhi', 'emergency')"
    
    return None


def _explain_missing_fields_factor(missing_fields: List[str]) -> Optional[str]:
    """Explain missing critical information."""
    if not missing_fields:
        return None
    
    critical_fields = [f for f in missing_fields if f in ["location", "incident_type"]]
    if critical_fields:
        return f"Missing critical information: {', '.join(critical_fields)}"
    
    return f"Missing information: {', '.join(missing_fields[:2])}"  # Limit to first 2


def _rank_contributing_factors(factors: List[str], urgency_score: float) -> List[str]:
    """
    Rank contributing factors by impact.
    
    Factors are ranked based on:
    1. Urgency score (higher = more impactful)
    2. Factor type (intent > stress > repetition > clarity)
    3. Severity indicators in the factor description
    """
    if not factors:
        return []
    
    # Simple ranking: prioritize factors that indicate higher urgency
    # Factors mentioning "panic", "critical", "very high", "very low" get priority
    def factor_priority(factor: str) -> int:
        priority = 0
        factor_lower = factor.lower()
        
        # High priority keywords
        if any(word in factor_lower for word in ["panic", "critical", "very high", "very low", "emergency"]):
            priority += 3
        elif any(word in factor_lower for word in ["high", "low", "distress", "stressed"]):
            priority += 2
        elif any(word in factor_lower for word in ["moderate", "some", "detected"]):
            priority += 1
        
        # Intent factors are generally more important
        if "emergency" in factor_lower or "incident" in factor_lower or "accident" in factor_lower:
            priority += 2
        
        return priority
    
    # Sort by priority (descending)
    ranked = sorted(factors, key=factor_priority, reverse=True)
    
    return ranked
