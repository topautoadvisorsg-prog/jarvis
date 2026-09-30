from datetime import datetime, timedelta, timezone
from pathlib import Path

from integrations.smartklix_alerts import AlertLedger, build_attention_events


NOW = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)


def _snapshot() -> dict:
    return {
        "generatedAt": NOW.isoformat().replace("+00:00", "Z"),
        "sources": {
            "crm": {
                "status": "available",
                "data": {
                    "controls": {"aiKillSwitchActive": False},
                    "proposals": {
                        "attention": [
                            {"id": "p1", "status": "pending", "summary": "Review roofers"},
                            {"id": "p2", "status": "dispatch_failed", "reason": "provider rejected"},
                            {"id": "p3", "status": "processing"},
                        ]
                    },
                    "communication": {"replies": 2},
                    "execution": {"outboxByStatus": {"failed": 1, "sent": 3}},
                    "intake": {"byStatus": {"needs_review": 1}},
                },
            },
            "outreach": {
                "status": "available",
                "partialFailures": {"usage": "HTTP 500"},
                "data": {
                    "research": {"byStatus": {"failed": 1, "complete": 4}},
                    "activity": {
                        "events": [
                            {"id": "a1", "timestamp": NOW.isoformat(), "level": "error", "category": "system", "message": "worker stopped"},
                            {"id": "a2", "timestamp": NOW.isoformat(), "level": "info", "category": "prospect", "message": "lead found"},
                        ]
                    },
                },
            },
        },
    }


def test_normalizes_only_deterministic_attention_facts():
    events = build_attention_events(_snapshot())
    types = [event["type"] for event in events]

    assert "approval.pending" in types
    assert "workflow.blocked" in types
    assert "reply.received" in types
    assert "execution.failed" in types
    assert "intake.needs_review" in types
    assert "source.partial_failure" in types
    assert "research.failed" in types
    assert "worker.exception" in types
    assert len([event for event in events if event["type"] == "worker.exception"]) == 1
    assert all(len(event["eventId"]) == 24 for event in events)


def test_event_identity_does_not_change_when_snapshot_time_changes():
    first = _snapshot()
    second = _snapshot()
    second["generatedAt"] = (NOW + timedelta(minutes=5)).isoformat()

    first_ids = {event["dedupeKey"]: event["eventId"] for event in build_attention_events(first)}
    second_ids = {event["dedupeKey"]: event["eventId"] for event in build_attention_events(second)}

    assert first_ids == second_ids


def test_stopped_research_console_is_informational_not_an_interruption():
    snapshot = {
        "generatedAt": NOW.isoformat(),
        "sources": {
            "crm": {"status": "available", "data": {}},
            "outreach": {"status": "unavailable", "reason": "connection refused"},
        },
    }
    event = build_attention_events(snapshot)[0]
    assert event["type"] == "source.inactive"
    assert event["severity"] == "info"
    assert event["requiresBuddy"] is False


def test_missing_crm_is_attention_but_never_fabricates_business_counts():
    snapshot = {
        "generatedAt": NOW.isoformat(),
        "sources": {
            "crm": {"status": "unavailable", "reason": "token missing"},
            "outreach": {"status": "unavailable"},
        },
    }
    events = build_attention_events(snapshot)
    crm = next(event for event in events if event["source"] == "smartklix-crm")
    assert crm["type"] == "source.unavailable"
    assert crm["requiresBuddy"] is True
    assert "count" not in crm["facts"]


def test_ledger_deduplicates_with_cooldown(tmp_path: Path):
    event = next(event for event in build_attention_events(_snapshot()) if event["requiresBuddy"])
    ledger = AlertLedger(
        tmp_path / "ledger.json",
        timezone_info=timezone.utc,
        quiet_start_hour=0,
        quiet_end_hour=0,
        cooldown=timedelta(hours=6),
    )

    first = ledger.evaluate([event], now=NOW, record=True)
    replay = ledger.evaluate([event], now=NOW + timedelta(minutes=1), record=False)
    after = ledger.evaluate([event], now=NOW + timedelta(hours=7), record=False)

    assert first["deliverable"] == [event]
    assert replay["deliverable"] == []
    assert replay["suppressed"][0]["suppressedReason"] == "cooldown"
    assert after["deliverable"] == [event]


def test_quiet_hours_hold_attention_but_not_urgent(tmp_path: Path):
    base = next(event for event in build_attention_events(_snapshot()) if event["requiresBuddy"])
    urgent = {**base, "eventId": "urgent", "dedupeKey": "urgent", "severity": "urgent"}
    ledger = AlertLedger(
        tmp_path / "ledger.json",
        timezone_name="UTC",
        timezone_info=timezone.utc,
        quiet_start_hour=21,
        quiet_end_hour=8,
    )
    result = ledger.evaluate([base, urgent], now=datetime(2026, 9, 30, 23, tzinfo=timezone.utc))

    assert result["deliverable"] == [urgent]
    assert result["suppressed"][0]["suppressedReason"] == "quiet_hours"


def test_observation_builds_persistent_handoff_without_storing_facts(tmp_path: Path):
    event = next(event for event in build_attention_events(_snapshot()) if event["requiresBuddy"])
    path = tmp_path / "ledger.json"
    ledger = AlertLedger(path, timezone_info=timezone.utc)

    ledger.observe([event], now=NOW)
    handoffs = ledger.build_handoffs([event], now=NOW + timedelta(hours=3))
    stored = path.read_text(encoding="utf-8")

    assert len(handoffs) == 1
    assert handoffs[0]["priority"] == "urgent"
    assert handoffs[0]["overdue"] is True
    assert handoffs[0]["recommendedAction"]
    assert handoffs[0]["firstSeenAt"] == NOW.isoformat().replace("+00:00", "Z")
    assert "facts" not in stored
    assert "summary" not in stored


def test_acknowledged_handoff_leaves_history_but_suppresses_delivery(tmp_path: Path):
    event = next(event for event in build_attention_events(_snapshot()) if event["requiresBuddy"])
    ledger = AlertLedger(
        tmp_path / "ledger.json",
        timezone_info=timezone.utc,
        quiet_start_hour=0,
        quiet_end_hour=0,
    )
    ledger.observe([event], now=NOW)
    receipt = ledger.acknowledge(
        event["dedupeKey"], acknowledged_by="Buddy", now=NOW,
    )

    assert receipt["acknowledgedBy"] == "Buddy"
    assert ledger.build_handoffs([event], now=NOW) == []
    result = ledger.evaluate([event], now=NOW, record=False)
    assert result["deliverable"] == []
    assert result["suppressed"][0]["suppressedReason"] == "acknowledged"


def test_resolved_event_reopens_as_a_new_incident(tmp_path: Path):
    event = next(event for event in build_attention_events(_snapshot()) if event["requiresBuddy"])
    ledger = AlertLedger(tmp_path / "ledger.json", timezone_info=timezone.utc)
    ledger.observe([event], now=NOW)
    ledger.acknowledge(event["dedupeKey"], acknowledged_by="Buddy", now=NOW)
    ledger.observe([], now=NOW + timedelta(minutes=5))
    ledger.observe([event], now=NOW + timedelta(hours=1))

    handoff = ledger.build_handoffs([event], now=NOW + timedelta(hours=1))[0]
    assert handoff["firstSeenAt"] == (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert handoff["overdue"] is False
