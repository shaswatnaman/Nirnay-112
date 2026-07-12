"""Unit tests for the append-only audit event log (app/logic/event_log.py).

The audit trail is what makes the pipeline reviewable after the fact, so its
append-only ordering and per-session isolation are contract-level guarantees.
"""
from app.logic import event_log


def test_events_are_appended_and_retrievable():
    event_log.clear_session_events("s1")
    event_log.log_event("s1", "transcription_received", {"x": 1})
    event_log.log_event("s1", "context_updated", {"y": 2})

    events = event_log.get_session_events("s1")
    assert len(events) == 2
    assert events[0]["event_type"] == "transcription_received"
    assert events[1]["event_type"] == "context_updated"
    assert events[0]["session_id"] == "s1"
    assert "timestamp" in events[0]


def test_append_only_preserves_order():
    event_log.clear_session_events("s2")
    for i in range(5):
        event_log.log_event("s2", "context_updated", {"i": i})
    events = event_log.get_session_events("s2")
    assert [e["payload"]["i"] for e in events] == [0, 1, 2, 3, 4]


def test_count_and_clear():
    event_log.clear_session_events("s3")
    event_log.log_event("s3", "e", {})
    assert event_log.get_event_count("s3") == 1
    event_log.clear_session_events("s3")
    assert event_log.get_event_count("s3") == 0


def test_empty_session_id_is_ignored():
    event_log.log_event("", "e", {})
    assert event_log.get_event_count("") == 0


def test_sessions_are_isolated():
    event_log.clear_session_events("a")
    event_log.clear_session_events("b")
    event_log.log_event("a", "e", {})
    assert event_log.get_event_count("a") == 1
    assert event_log.get_event_count("b") == 0


def test_convenience_loggers_record_structured_payloads():
    event_log.clear_session_events("s4")
    event_log.log_escalation_triggered("s4", "high urgency", "critical", 0.9)
    event_log.log_rollback_occurred("s4", "entity contradiction", ["location"])
    events = event_log.get_session_events("s4")
    assert [e["event_type"] for e in events] == ["escalation_triggered", "rollback_occurred"]
    assert events[0]["payload"]["priority"] == "critical"
    assert events[1]["payload"]["rolled_back_fields"] == ["location"]
