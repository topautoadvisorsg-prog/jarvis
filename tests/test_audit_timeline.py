"""Privacy, persistence, API, and Hermes-event coverage for the audit timeline."""

from __future__ import annotations

import json


def test_record_audit_redacts_secrets_before_writing(server_mod, isolated_audit_path):
    record = server_mod.record_audit(
        "tool.completed",
        path=isolated_audit_path,
        run_id="run-123",
        tool="example",
        output_preview="password=hunter2 bearer=super-secret-value",
        input_preview=json.dumps({"api_key": "quoted-key-secret", "query": "safe"}),
        nested={"api_key": "sk-test-secret-value", "safe": "kept"},
    )

    raw = isolated_audit_path.read_text(encoding="utf-8")
    assert "hunter2" not in raw
    assert "super-secret-value" not in raw
    assert "quoted-key-secret" not in raw
    assert "sk-test-secret-value" not in raw
    assert record["nested"] == {"api_key": "[REDACTED]", "safe": "kept"}
    assert record["run_id"] == "run-123"


def test_read_audit_is_newest_first_and_ignores_malformed(server_mod, isolated_audit_path):
    server_mod.record_audit("first", path=isolated_audit_path)
    with isolated_audit_path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
        handle.write(json.dumps({"event": "injected", "api_key": "must-not-leak"}) + "\n")
    server_mod.record_audit("second", path=isolated_audit_path)

    rows = server_mod.read_audit(3, path=isolated_audit_path)
    assert [row["event"] for row in rows] == ["second", "injected", "first"]
    assert rows[1]["api_key"] == "[REDACTED]"


def test_audit_api_returns_only_bounded_local_events(
    no_token, server_mod, client, isolated_audit_path,
):
    server_mod.record_audit("request.accepted", request_preview="safe", path=isolated_audit_path)
    response = client.get("/api/audit?limit=500")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "jarvis_local_audit"
    assert body["limit"] == 100
    assert body["events"][0]["event"] == "request.accepted"


def test_audit_api_inherits_api_auth(with_token, client):
    response = client.get("/api/audit")
    assert response.status_code == 401


def test_hermes_tool_completion_is_available_to_the_audit_pipeline(server_mod):
    class Response:
        def iter_lines(self, decode_unicode=True):
            yield "event: tool.completed"
            yield "data: " + json.dumps({
                "tool_name": "lookup",
                "output": {"status": "ok", "count": 2},
            })

    events = list(server_mod.HermesAPI._parse_sse(Response()))
    kind, payload = events[0]
    assert kind == "tool_result"
    assert json.loads(payload) == {
        "name": "lookup",
        "preview": '{"status": "ok", "count": 2}',
    }
