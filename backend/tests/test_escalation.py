"""Unit tests for the deterministic human-in-the-loop escalation rules
(app/logic/escalation.py). Any single rule can trigger escalation; each is
explicit and independently testable.
"""
from app.logic.escalation import check_escalation_required, detect_explicit_human_request


def _call(**overrides):
    base = dict(
        urgency_score=0.1,
        urgency_level="low",
        clarity_avg=0.9,
        emotion_history=[],
        missing_fields=[],
        question_count=0,
    )
    base.update(overrides)
    return check_escalation_required(**base)


def test_high_urgency_escalates():
    r = _call(urgency_score=0.8, urgency_level="critical")
    assert r["human_required"] is True
    assert "urgency" in r["reason"].lower()


def test_low_clarity_escalates():
    r = _call(clarity_avg=0.2)
    assert r["human_required"] is True


def test_persistent_panic_escalates_as_critical():
    r = _call(emotion_history=["panic", "panic", "panic"])
    assert r["human_required"] is True
    assert r["priority"] == "critical"


def test_missing_critical_fields_after_enough_questions_escalates():
    r = _call(missing_fields=["location"], question_count=5)
    assert r["human_required"] is True


def test_missing_fields_early_does_not_escalate():
    r = _call(missing_fields=["location"], question_count=2)
    assert r["human_required"] is False


def test_immediate_danger_escalates_as_critical():
    r = _call(immediate_danger=True)
    assert r["human_required"] is True
    assert r["priority"] == "critical"


def test_explicit_human_request_escalates():
    r = _call(explicit_human_request=True)
    assert r["human_required"] is True


def test_calm_complete_call_does_not_escalate():
    r = _call()
    assert r["human_required"] is False
    assert r["reason"] is None


def test_detect_explicit_human_request():
    assert detect_explicit_human_request("I want to talk to a human") is True
    assert detect_explicit_human_request("operator please") is True
    assert detect_explicit_human_request("there is a fire in the kitchen") is False
    assert detect_explicit_human_request("") is False
