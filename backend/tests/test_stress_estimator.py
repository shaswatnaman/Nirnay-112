"""Unit tests for the deterministic stress estimator (app/ml/stress_estimator.py).

The estimator uses observable, rule-based signals (panic keywords, speaking
rate, exclamations, repetition) instead of LLM emotion labels, so its output is
fully deterministic and testable.
"""
from app.ml.stress_estimator import estimate_stress, StressEstimator

CALM = "i would like to report a broken street lamp near the market"
PANIC = "help help emergency save us we are trapped and bleeding"


def test_empty_transcript_is_zero_stress():
    r = estimate_stress("")
    assert r["stress_score"] == 0.0
    assert r["details"]["word_count"] == 0
    assert r["details"]["panic_keyword_count"] == 0


def test_calm_text_is_low_stress():
    assert estimate_stress(CALM)["stress_score"] < 0.2


def test_panic_keywords_increase_stress():
    calm = estimate_stress(CALM)["stress_score"]
    panic = estimate_stress(PANIC)["stress_score"]
    assert panic > calm
    assert panic > 0.3


def test_panic_keywords_are_reported():
    r = estimate_stress("help emergency save")
    assert r["details"]["panic_keyword_count"] >= 3
    assert set(r["details"]["panic_keywords_found"]) & {"help", "emergency", "save"}


def test_fast_speech_scores_higher_than_slow():
    text = "one two three four five six seven eight nine ten eleven twelve"
    slow = estimate_stress(text, time_elapsed_seconds=12.0)["components"]["speaking_rate_score"]
    fast = estimate_stress(text, time_elapsed_seconds=2.0)["components"]["speaking_rate_score"]
    assert slow == 0.0   # ~1 word/sec is normal
    assert fast == 1.0   # ~6 words/sec is extreme
    assert fast > slow


def test_exclamations_increase_stress():
    r = estimate_stress("fire fire fire!!!")
    assert r["details"]["exclamation_count"] >= 3
    assert r["components"]["exclamation_score"] > 0.0


def test_repetition_component_saturates():
    r = estimate_stress("help", repetition_count=3)
    assert r["components"]["repetition_score"] == 1.0


def test_stress_score_is_bounded():
    r = estimate_stress("help! emergency! save! trapped! bleeding!",
                        repetition_count=99, time_elapsed_seconds=0.5)
    assert 0.0 <= r["stress_score"] <= 1.0


def test_class_and_convenience_function_agree():
    est = StressEstimator()
    assert est.calculate_stress_score(PANIC)["stress_score"] == estimate_stress(PANIC)["stress_score"]
