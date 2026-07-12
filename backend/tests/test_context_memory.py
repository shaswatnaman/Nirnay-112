"""Unit tests for the context-memory safety layer (app/logic/context_memory.py).

This is the module that keeps LLM misperceptions from "locking in": confidence
gating, contradiction detection, low-clarity guarding, and snapshot/rollback.
"""
from app.logic.context_memory import ContextMemory


def test_new_context_is_missing_critical_fields():
    c = ContextMemory(session_id="s")
    assert set(c.get_missing_fields()) == {"location", "incident_type"}


def test_high_confidence_signal_updates_field():
    c = ContextMemory(session_id="s")
    c.update_from_signals({"entities": {"location": "Mumbai", "location_confidence": 0.8},
                           "clarity": 0.9})
    assert c.location == "Mumbai"
    assert "location" not in c.get_missing_fields()


def test_contradicting_entity_is_rolled_back():
    c = ContextMemory(session_id="s")
    c.update_from_signals({"entities": {"location": "Mumbai", "location_confidence": 0.8},
                           "clarity": 0.9})
    # A contradictory, higher-confidence location must NOT overwrite the established one.
    c.update_from_signals({"entities": {"location": "Delhi", "location_confidence": 0.95},
                           "clarity": 0.9})
    assert c.location == "Mumbai"
    assert c.hallucination_detected is True


def test_low_clarity_update_is_rejected():
    c = ContextMemory(session_id="s")
    c.update_from_signals({"entities": {"location": "Pune", "location_confidence": 0.9},
                           "clarity": 0.2})  # clarity < 0.3 -> rollback
    assert c.location is None


def test_hallucination_flag_blocks_subsequent_updates():
    c = ContextMemory(session_id="s")
    c.hallucination_detected = True
    c.update_from_signals({"entities": {"incident": "fire", "incident_confidence": 0.9},
                           "clarity": 0.9})
    assert c.incident_type is None


def test_snapshot_restore_roundtrip():
    c = ContextMemory(session_id="s")
    c.update_from_signals({"entities": {"location": "Chennai", "location_confidence": 0.8},
                           "clarity": 0.9})
    snap = c.create_snapshot()
    c.location = "Kolkata"          # simulate a bad in-place mutation
    snap.restore_to(c)
    assert c.location == "Chennai"


def test_intent_is_mapped_to_incident_type():
    c = ContextMemory(session_id="s")
    c.update_from_signals({"intent": "fire", "intent_confidence": 0.8, "clarity": 0.9})
    assert c.incident_type == "fire"
    assert "incident_type" not in c.get_missing_fields()
