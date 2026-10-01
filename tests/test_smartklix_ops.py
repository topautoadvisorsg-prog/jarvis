from datetime import datetime, timezone
from pathlib import Path

import pytest

from integrations.smartklix_ops import (
    _fetch_windows_loopback_json,
    _validate_base_url,
    build_operations_snapshot,
    load_smartklix_environment,
)


NOW = datetime(2026, 9, 25, 16, 0, tzinfo=timezone.utc)
TOKEN = "r" * 40


def test_rejects_plain_http_to_non_loopback_host():
    with pytest.raises(ValueError, match="HTTPS or loopback"):
        _validate_base_url("http://smartklix.example", "test")


def test_missing_crm_token_and_offline_outreach_are_explicit(tmp_path: Path):
    def offline(url, headers, timeout):
        raise OSError("offline")

    snapshot = build_operations_snapshot(
        environ={}, fetch_json=offline, now=NOW, usage_path=tmp_path / "missing.json"
    )

    assert snapshot["authority"] == {
        "readOnly": True,
        "canStart": False,
        "canPause": False,
        "canApprove": False,
        "canExecute": False,
        "canSend": False,
        "canSpend": False,
    }
    assert snapshot["sources"]["crm"]["status"] == "unavailable"
    assert "TOKEN" in snapshot["sources"]["crm"]["reason"]
    assert snapshot["sources"]["outreach"]["status"] == "unavailable"
    assert snapshot["sources"]["jarvisUsage"]["status"] == "unavailable"


def test_collects_only_get_snapshots_and_forwards_bounded_lead_query(tmp_path: Path):
    calls = []

    def fake_fetch(url, headers, timeout):
        calls.append((url, dict(headers), timeout))
        if "/api/jarvis/operations" in url:
            return {"authority": {"readOnly": True}, "leadLookup": {"matches": []}}
        return {"ok": True}

    usage = tmp_path / "usage.json"
    usage.write_text('{"totals":{"llm_in":100,"llm_out":20,"turns":3,"tts_chars":50}}')
    snapshot = build_operations_snapshot(
        hours=12,
        lead="Acme Roofing",
        environ={
            "SMARTKLIX_JARVIS_READ_TOKEN": TOKEN,
            "SMARTKLIX_CRM_BASE_URL": "https://smartklixcrm.vercel.app",
            "SMARTKLIX_OUTREACH_BASE_URL": "http://127.0.0.1:3001",
        },
        fetch_json=fake_fetch,
        now=NOW,
        usage_path=usage,
    )

    assert snapshot["sources"]["crm"]["status"] == "available"
    assert snapshot["sources"]["outreach"]["status"] == "available"
    assert snapshot["sources"]["jarvisUsage"]["data"]["llmInputTokens"] == 100
    assert all(url.startswith(("https://", "http://127.0.0.1")) for url, _, _ in calls)
    crm_url, crm_headers, _ = calls[0]
    assert "lead=Acme+Roofing" in crm_url
    assert crm_headers == {"x-jarvis-read-token": TOKEN}
    assert len(calls) == 9


def test_can_use_separate_private_windows_loopback_fetcher(tmp_path: Path):
    remote_calls = []
    local_calls = []

    def remote_fetch(url, headers, timeout):
        remote_calls.append(url)
        return {"authority": {"readOnly": True}}

    def local_fetch(url, headers, timeout):
        local_calls.append(url)
        return {"ok": True}

    snapshot = build_operations_snapshot(
        environ={"SMARTKLIX_JARVIS_READ_TOKEN": TOKEN},
        fetch_json=remote_fetch,
        local_fetch_json=local_fetch,
        now=NOW,
        usage_path=tmp_path / "none.json",
    )

    assert snapshot["sources"]["crm"]["status"] == "available"
    assert snapshot["sources"]["outreach"]["status"] == "available"
    assert len(remote_calls) == 1
    assert len(local_calls) == 8
    assert all(url.startswith("http://127.0.0.1:3001/") for url in local_calls)


def test_windows_bridge_rejects_non_loopback_before_launching():
    with pytest.raises(ValueError, match="loopback HTTP only"):
        _fetch_windows_loopback_json("https://smartklix.example/api", {}, 1)


def test_runtime_environment_loads_only_allowlisted_missing_values(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "SMARTKLIX_JARVIS_READ_TOKEN=from-file\n"
        "SMARTKLIX_AGENTS_ROOT='/approved/agents'\n"
        "OPENAI_API_KEY=must-not-load\n"
        "SMARTKLIX_CRM_BASE_URL=https://wrong.example\n",
        encoding="utf-8",
    )

    result = load_smartklix_environment(
        dotenv,
        base={"SMARTKLIX_CRM_BASE_URL": "https://configured.example"},
    )

    assert result["SMARTKLIX_JARVIS_READ_TOKEN"] == "from-file"
    assert result["SMARTKLIX_AGENTS_ROOT"] == "/approved/agents"
    assert result["SMARTKLIX_CRM_BASE_URL"] == "https://configured.example"
    assert "OPENAI_API_KEY" not in result


def test_compacts_research_and_territory_payloads(tmp_path: Path):
    def fake_fetch(url, headers, timeout):
        if "/api/jarvis/operations" in url:
            return {"authority": {"readOnly": True}}
        if url.endswith("/api/cold-research"):
            return {"sendingEnabled": False, "records": [{
                "id": "r1", "prospectId": "p1", "status": "pending", "version": 2,
                "package": {"businessName": "Acme", "draft": {"body": "do not expose"}},
                "updatedAt": "2026-09-25T15:00:00Z",
            }]}
        if url.endswith("/api/territory/work"):
            return {"current": "t1", "next": None, "sendingEnabled": False, "work": [{
                "id": "t1", "zip": "92101", "niche": "roofing", "researchStatus": "in_progress",
                "outreachStatus": "not_started", "businesses": {"huge": {"secret": "omit"}},
                "metrics": {"researched": 4}, "updatedAt": "2026-09-25T15:00:00Z",
            }]}
        if url.endswith("/api/metrics"):
            return {"researchOnly": True, "health": "offline"}
        if url.endswith("/api/workers"):
            return {"workers": [], "count": 0, "healthy": False}
        return {"ok": True}

    snapshot = build_operations_snapshot(
        environ={"SMARTKLIX_JARVIS_READ_TOKEN": TOKEN}, fetch_json=fake_fetch,
        now=NOW, usage_path=tmp_path / "none.json",
    )
    outreach = snapshot["sources"]["outreach"]["data"]
    assert outreach["research"]["recent"][0]["businessName"] == "Acme"
    assert "package" not in outreach["research"]["recent"][0]
    assert outreach["territoryWork"]["work"][0]["metrics"] == {"researched": 4}
    assert "businesses" not in outreach["territoryWork"]["work"][0]
    assert outreach["operatingMode"]["name"] == "supervised_research"
    assert outreach["workers"]["operationalStatus"] == "expected_idle"
    assert outreach["workers"]["expectedInSupervisedResearch"] is True


@pytest.mark.parametrize("hours", [0, 169])
def test_rejects_unbounded_reporting_window(hours: int):
    with pytest.raises(ValueError, match="between 1 and 168"):
        build_operations_snapshot(hours=hours, environ={})
