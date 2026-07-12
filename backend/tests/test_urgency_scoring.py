"""Unit tests for the deterministic urgency scoring engine (app/logic/urgency_scoring.py).

Scoring is an explicit weighted formula over intent, stress, repetition, clarity,
time and urgency-keyword signals - no LLM is involved, so every score is
reproducible and every branch is testable.
"""
from app.logic.urgency_scoring import calculate_urgency_score, get_urgency_threshold


def test_fire_with_panic_is_critical():
    r = calculate_urgency_score("fire", stress_score=0.9, repetition_count=3,
                                clarity_avg=0.4, time_elapsed_seconds=60)
    assert r["urgency_level"] == "critical"
    assert r["urgency_score"] >= 0.75


def test_non_emergency_is_low():
    r = calculate_urgency_score("non_emergency", stress_score=0.0, repetition_count=0,
                                clarity_avg=1.0, time_elapsed_seconds=0)
    assert r["urgency_level"] == "low"


def test_score_is_monotonic_in_stress():
    lo = calculate_urgency_score("crime", 0.0, 0, 0.8, 30)["urgency_score"]
    hi = calculate_urgency_score("crime", 1.0, 0, 0.8, 30)["urgency_score"]
    assert hi > lo


def test_unknown_intent_defaults_to_medium_weight():
    r = calculate_urgency_score("nonsense_intent", 0.0, 0, 1.0, 0)
    # unknown intent -> default weight 0.5 -> intent_score 0.25 -> total 0.25 -> low
    assert r["urgency_level"] == "low"
    assert abs(r["breakdown"]["intent_score"] - 0.25) < 1e-9


def test_dog_bite_is_not_critical():
    # Documented special case: dog bites are medical but not life-threatening.
    ctx = {"transcript": "dog bite"}
    r = calculate_urgency_score("medical_emergency", stress_score=0.9, repetition_count=2,
                                clarity_avg=0.6, time_elapsed_seconds=60, context=ctx)
    assert r["urgency_level"] != "critical"


def test_urgency_keywords_boost_score():
    base = calculate_urgency_score("crime", 0.3, 0, 0.8, 30)
    boosted = calculate_urgency_score("crime", 0.3, 0, 0.8, 30,
                                      context={"transcript": "jaldi bhejo emergency"})
    assert boosted["urgency_score"] > base["urgency_score"]


def test_breakdown_exposes_all_components():
    r = calculate_urgency_score("medical_emergency", 0.5, 1, 0.7, 30)
    for key in ("intent_score", "stress_score", "repetition_score",
                "clarity_score", "time_score", "total"):
        assert key in r["breakdown"]


def test_score_is_bounded_under_extreme_inputs():
    r = calculate_urgency_score("fire", 1.0, 100, 0.0, 1_000_000)
    assert 0.0 <= r["urgency_score"] <= 1.0


def test_escalation_thresholds():
    assert get_urgency_threshold("critical") == 0.7
    assert get_urgency_threshold("low") == 0.4
    assert get_urgency_threshold("unknown_level") == 0.5  # safe default
