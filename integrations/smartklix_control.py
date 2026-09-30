"""Bounded lifecycle control for the existing SmartKlix research console.

This adapter can only start, inspect, or stop scripts/local-research.ts. That
upstream launcher forces research-only mode and disables sending and execution.
It cannot create objectives, research prospects, approve work, or deliver mail.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")
Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


class ControlError(RuntimeError):
    """Raised when the local control policy or platform adapter rejects work."""


def _default_runner(command: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ControlError("SmartKlix control returned no JSON result")


class SmartKlixResearchControl:
    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        runner: Runner = _default_runner,
    ) -> None:
        self.environ = dict(os.environ if environ is None else environ)
        self.runner = runner
        root_text = self.environ.get("SMARTKLIX_AGENTS_ROOT", "").strip()
        if not root_text:
            raise ControlError("SMARTKLIX_AGENTS_ROOT is not configured")
        self.root = Path(root_text).expanduser().resolve()
        self.script = self.root / "scripts" / "jarvis-research-control.ps1"
        self.launcher = self.root / "scripts" / "local-research.ts"
        if not self.script.is_file() or not self.launcher.is_file():
            raise ControlError("Configured root is missing the reviewed SmartKlix control scripts")

        state_text = self.environ.get("SMARTKLIX_CONTROL_STATE_DIR", "").strip()
        self.state_dir = (
            Path(state_text).expanduser().resolve()
            if state_text
            else Path.home() / ".hermes" / "smartklix-control"
        )
        self.receipts_path = self.state_dir / "receipts.jsonl"
        self.idempotency_path = self.state_dir / "idempotency.json"

    def _powershell_paths(self) -> tuple[str, str]:
        if os.name == "nt":
            return str(self.script), str(self.root)
        if not shutil.which("powershell.exe"):
            raise ControlError("Windows PowerShell bridge is unavailable")
        converted: list[str] = []
        for path in (self.script, self.root):
            try:
                result = subprocess.run(
                    ["wslpath", "-w", str(path)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ControlError(f"Could not convert WSL path: {path}") from exc
            if result.returncode != 0 or not result.stdout.strip():
                raise ControlError(f"Could not convert WSL path: {path}")
            converted.append(result.stdout.strip())
        return converted[0], converted[1]

    def _command(self, action: str, max_runtime_minutes: int = 60) -> list[str]:
        script, root = self._powershell_paths()
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
            "-Action",
            action,
            "-Root",
            root,
            "-MaxRuntimeMinutes",
            str(max_runtime_minutes),
        ]

    def _invoke(self, action: str, max_runtime_minutes: int = 60) -> dict[str, Any]:
        try:
            result = self.runner(self._command(action, max_runtime_minutes), 45)
        except subprocess.TimeoutExpired as exc:
            raise ControlError(f"SmartKlix {action.casefold()} timed out") from exc
        except OSError as exc:
            raise ControlError(f"SmartKlix control could not start: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "control failed").strip()[-1000:]
            raise ControlError(detail)
        return _last_json(result.stdout)

    def _authorize(self) -> str:
        if not _is_true(self.environ.get("SMARTKLIX_JARVIS_CONTROL_ENABLED")):
            raise ControlError("SmartKlix lifecycle control is disabled by server policy")
        token = self.environ.get("SMARTKLIX_JARVIS_CONTROL_TOKEN", "")
        if len(token) < 32:
            raise ControlError("SmartKlix lifecycle policy token is missing or too short")
        return token

    def _load_idempotency(self) -> dict[str, Any]:
        if not self.idempotency_path.is_file():
            return {}
        try:
            value = json.loads(self.idempotency_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_json_private(self, path: Path, value: Any) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        temporary.replace(path)

    def _receipt(
        self,
        *,
        token: str,
        action: str,
        idempotency_key: str,
        reason: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        receipt = {
            "schemaVersion": 1,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "actor": "jarvis-main",
            "system": "smartklix-claude-agents",
            "action": action,
            "idempotencyKey": idempotency_key,
            "reason": reason,
            "result": result,
            "authority": {
                "researchConsoleOnly": True,
                "sendingEnabled": False,
                "executionEnabled": False,
            },
        }
        canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
        receipt["signature"] = hmac.new(token.encode(), canonical, hashlib.sha256).hexdigest()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, separators=(",", ":")) + "\n")
        try:
            self.receipts_path.chmod(0o600)
        except OSError:
            pass
        return receipt

    def status(self) -> dict[str, Any]:
        return self._invoke("Status")

    def _change(
        self,
        *,
        action: str,
        idempotency_key: str,
        reason: str,
        max_runtime_minutes: int = 60,
    ) -> dict[str, Any]:
        token = self._authorize()
        if not IDEMPOTENCY_KEY.fullmatch(idempotency_key):
            raise ControlError("idempotency_key must be 8-128 safe characters")
        reason = reason.strip()
        if not reason or len(reason) > 240 or "\n" in reason:
            raise ControlError("reason must be a single line between 1 and 240 characters")
        if not 5 <= max_runtime_minutes <= 240:
            raise ControlError("max_runtime_minutes must be between 5 and 240")

        ledger = self._load_idempotency()
        previous = ledger.get(idempotency_key)
        if previous:
            if previous.get("action") != action:
                raise ControlError("idempotency_key was already used for a different action")
            return {**previous["result"], "idempotentReplay": True}

        result = self._invoke(action, max_runtime_minutes)
        receipt = self._receipt(
            token=token,
            action=action.casefold(),
            idempotency_key=idempotency_key,
            reason=reason,
            result=result,
        )
        ledger[idempotency_key] = {"action": action, "result": result, "receipt": receipt["signature"]}
        self._write_json_private(self.idempotency_path, ledger)
        return {**result, "receipt": receipt["signature"], "idempotentReplay": False}

    def start(
        self,
        *,
        idempotency_key: str,
        objective: str,
        max_runtime_minutes: int = 60,
    ) -> dict[str, Any]:
        return self._change(
            action="Start",
            idempotency_key=idempotency_key,
            reason=objective,
            max_runtime_minutes=max_runtime_minutes,
        )

    def stop(self, *, idempotency_key: str, reason: str) -> dict[str, Any]:
        return self._change(
            action="Stop",
            idempotency_key=idempotency_key,
            reason=reason,
        )
