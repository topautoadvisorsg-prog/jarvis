import json
from datetime import datetime, timezone

from integrations.smartklix_crm_activation import (
    build_crm_activation_report,
    load_preflight_environment,
)


NOW = datetime(2026, 9, 30, 20, 0, tzinfo=timezone.utc)
TOKEN = "r" * 40


def test_env_loader_reads_only_preflight_keys_without_shell_evaluation(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SMARTKLIX_JARVIS_READ_TOKEN='" + TOKEN + "'\n"
        "UNRELATED=value with spaces\n"
        "SMARTKLIX_READ_TIMEOUT_SECONDS=12\n",
        encoding="utf-8",
    )
    result = load_preflight_environment(env_file, base={})
    assert result == {
        "SMARTKLIX_JARVIS_READ_TOKEN": TOKEN,
        "SMARTKLIX_READ_TIMEOUT_SECONDS": "12",
    }


def test_reports_deployed_route_waiting_for_production_token():
    def fetch(url, headers, timeout):
        assert not headers
        return 503, {"code": "JARVIS_READ_NOT_CONFIGURED"}

    report = build_crm_activation_report(fetch_status=fetch, now=NOW)
    assert report["status"] == "production_token_required"
    assert report["ready"] is False
    assert report["productionChanged"] is False


def test_rejects_a_publicly_exposed_snapshot():
    def fetch(url, headers, timeout):
        return 200, {"authority": {"readOnly": True}}

    report = build_crm_activation_report(fetch_status=fetch, now=NOW)
    assert report["status"] == "security_failure"
    assert report["ready"] is False


def test_reports_local_token_missing_after_protected_probe():
    def fetch(url, headers, timeout):
        return 401, {"code": "UNAUTHORIZED"}

    report = build_crm_activation_report(fetch_status=fetch, now=NOW)
    assert report["status"] == "local_token_required"
    assert report["tokenConfiguredLocally"] is False


def test_ready_requires_matching_token_and_read_only_authority():
    calls = []

    def fetch(url, headers, timeout):
        calls.append(dict(headers))
        if not headers:
            return 401, {"code": "UNAUTHORIZED"}
        return 200, {
            "authority": {
                "readOnly": True,
                "canStage": False,
                "canReview": False,
                "canApprove": False,
                "canExecute": False,
                "canSend": False,
            }
        }

    report = build_crm_activation_report(
        environ={"SMARTKLIX_JARVIS_READ_TOKEN": TOKEN},
        fetch_status=fetch,
        now=NOW,
    )
    assert report["status"] == "ready"
    assert report["ready"] is True
    assert calls == [{}, {"x-jarvis-read-token": TOKEN}]
    assert TOKEN not in json.dumps(report)


def test_rejects_an_authenticated_snapshot_with_broader_authority():
    def fetch(url, headers, timeout):
        if not headers:
            return 401, {"code": "UNAUTHORIZED"}
        return 200, {
            "authority": {
                "readOnly": True,
                "canStage": False,
                "canReview": False,
                "canApprove": False,
                "canExecute": False,
                "canSend": True,
            }
        }

    report = build_crm_activation_report(
        environ={"SMARTKLIX_JARVIS_READ_TOKEN": TOKEN},
        fetch_status=fetch,
        now=NOW,
    )
    assert report["status"] == "authority_mismatch"
    assert report["ready"] is False
