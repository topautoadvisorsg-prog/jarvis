import json
import subprocess
from pathlib import Path

import pytest

from integrations.smartklix_control import ControlError, SmartKlixResearchControl


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "agents"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "local-research.ts").write_text("// reviewed launcher\n")
    (root / "scripts" / "jarvis-research-control.ps1").write_text("# adapter\n")
    return root


def _runner(status: str = "started"):
    calls = []

    def run(command, timeout):
        calls.append((list(command), timeout))
        return subprocess.CompletedProcess(command, 0, json.dumps({"status": status}) + "\n", "")

    return run, calls


def test_control_is_disabled_without_server_policy(tmp_path: Path):
    root = _repo(tmp_path)
    run, _ = _runner()
    control = SmartKlixResearchControl(
        environ={"SMARTKLIX_AGENTS_ROOT": str(root)}, runner=run
    )
    with pytest.raises(ControlError, match="disabled"):
        control.start(idempotency_key="start-0001", objective="Open console")


def test_start_is_bounded_audited_and_idempotent(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path)
    state = tmp_path / "state"
    run, calls = _runner()
    monkeypatch.setattr(SmartKlixResearchControl, "_powershell_paths", lambda self: (str(self.script), str(self.root)))
    control = SmartKlixResearchControl(
        environ={
            "SMARTKLIX_AGENTS_ROOT": str(root),
            "SMARTKLIX_CONTROL_STATE_DIR": str(state),
            "SMARTKLIX_JARVIS_CONTROL_ENABLED": "true",
            "SMARTKLIX_JARVIS_CONTROL_TOKEN": "t" * 40,
        },
        runner=run,
    )

    first = control.start(
        idempotency_key="start-0001",
        objective="Open supervised research console",
        max_runtime_minutes=15,
    )
    replay = control.start(
        idempotency_key="start-0001",
        objective="Open supervised research console",
        max_runtime_minutes=15,
    )

    assert first["status"] == "started"
    assert first["idempotentReplay"] is False
    assert replay["idempotentReplay"] is True
    assert len(calls) == 1
    assert "15" in calls[0][0]
    receipt = json.loads((state / "receipts.jsonl").read_text())
    assert receipt["authority"] == {
        "researchConsoleOnly": True,
        "sendingEnabled": False,
        "executionEnabled": False,
    }
    assert len(receipt["signature"]) == 64
    assert "t" * 40 not in (state / "receipts.jsonl").read_text()


def test_idempotency_key_cannot_change_action(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path)
    run, _ = _runner()
    monkeypatch.setattr(SmartKlixResearchControl, "_powershell_paths", lambda self: (str(self.script), str(self.root)))
    control = SmartKlixResearchControl(
        environ={
            "SMARTKLIX_AGENTS_ROOT": str(root),
            "SMARTKLIX_CONTROL_STATE_DIR": str(tmp_path / "state"),
            "SMARTKLIX_JARVIS_CONTROL_ENABLED": "true",
            "SMARTKLIX_JARVIS_CONTROL_TOKEN": "t" * 40,
        },
        runner=run,
    )
    control.start(idempotency_key="same-key", objective="Open console")
    with pytest.raises(ControlError, match="different action"):
        control.stop(idempotency_key="same-key", reason="Done")


@pytest.mark.parametrize("minutes", [4, 241])
def test_runtime_limit_is_enforced(tmp_path: Path, minutes: int):
    root = _repo(tmp_path)
    run, _ = _runner()
    control = SmartKlixResearchControl(
        environ={
            "SMARTKLIX_AGENTS_ROOT": str(root),
            "SMARTKLIX_JARVIS_CONTROL_ENABLED": "true",
            "SMARTKLIX_JARVIS_CONTROL_TOKEN": "t" * 40,
        },
        runner=run,
    )
    with pytest.raises(ControlError, match="between 5 and 240"):
        control.start(
            idempotency_key="start-limit",
            objective="Open console",
            max_runtime_minutes=minutes,
        )


def test_subprocess_timeout_becomes_policy_error(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path)

    def timeout_runner(command, timeout):
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(
        SmartKlixResearchControl,
        "_powershell_paths",
        lambda self: (str(self.script), str(self.root)),
    )
    control = SmartKlixResearchControl(
        environ={"SMARTKLIX_AGENTS_ROOT": str(root)},
        runner=timeout_runner,
    )

    with pytest.raises(ControlError, match="status timed out"):
        control.status()
