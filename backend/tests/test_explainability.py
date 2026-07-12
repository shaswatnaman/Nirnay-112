"""Unit tests for the decision explainability layer (app/logic/explainability.py).

Every escalation decision must come with a human-readable, deterministic
rationale. These tests pin the explanation's structure and key fields.
"""
from app.logic.context_memory import ContextMemory
from app.logic.explainability import explain_decision


def test_explanation_structure_and_level():
    c = ContextMemory(session_id="s")
    c.update_from_signals({
        "entities": {"incident": "fire", "incident_confidence": 0.9,
                     "location": "Mumbai", "location_confidence": 0.9},
        "clarity": 0.9,
    })
    escalation = {"human_required": True,
                  "reason": "High urgency score (0.82) exceeds threshold (0.7)",
                  "priority": "critical"}
    exp = explain_decision(c, urgency_score=0.82, escalation_decision=escalation)

    assert exp["urgency_level"] == "critical"
    assert isinstance(exp["top_3_contributing_factors"], list)
    assert len(exp["top_3_contributing_factors"]) <= 3
    assert exp["why_escalated"] == escalation["reason"]


def test_low_clarity_produces_confidence_warning():
    c = ContextMemory(session_id="s")
    c.clarity_avg = 0.2
    exp = explain_decision(c, urgency_score=0.3, escalation_decision={"human_required": False})
    assert any("clarity" in w.lower() for w in exp["confidence_warnings"])


def test_no_escalation_has_no_reason():
    c = ContextMemory(session_id="s")
    exp = explain_decision(c, urgency_score=0.2, escalation_decision={"human_required": False})
    assert exp["why_escalated"] is None
    assert exp["urgency_level"] == "low"
