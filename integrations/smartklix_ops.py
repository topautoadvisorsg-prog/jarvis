"""Read-only SmartKlix operations aggregation for Jarvis.

This module deliberately exposes observations only. It has no POST, PATCH,
PUT, DELETE, approval, execution, delivery, or retry code path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


JsonFetcher = Callable[[str, Mapping[str, str], float], Any]
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_CRM_BASE_URL = "https://smartklixcrm.vercel.app"
DEFAULT_OUTREACH_BASE_URL = "http://127.0.0.1:3001"
SMARTKLIX_RUNTIME_ENV_KEYS = {
    "SMARTKLIX_AGENTS_ROOT",
    "SMARTKLIX_ALERT_STATE_PATH",
    "SMARTKLIX_ALERT_TIMEZONE",
    "SMARTKLIX_CONTROL_STATE_DIR",
    "SMARTKLIX_CRM_BASE_URL",
    "SMARTKLIX_JARVIS_CONTROL_ENABLED",
    "SMARTKLIX_JARVIS_CONTROL_TOKEN",
    "SMARTKLIX_JARVIS_READ_TOKEN",
    "SMARTKLIX_OUTREACH_ADMIN_TOKEN",
    "SMARTKLIX_OUTREACH_BASE_URL",
    "SMARTKLIX_READ_TIMEOUT_SECONDS",
}


def load_smartklix_environment(
    path: Path,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load only SmartKlix MCP settings from the protected Hermes dotenv."""
    result = dict(os.environ if base is None else base)
    try:
        lines = path.expanduser().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return result
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in SMARTKLIX_RUNTIME_ENV_KEYS or key in result:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def _validate_base_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    if parsed.scheme == "https" and parsed.hostname:
        return value.rstrip("/")
    if parsed.scheme == "http" and parsed.hostname in LOOPBACK_HOSTS:
        return value.rstrip("/")
    raise ValueError(f"{label} must use HTTPS or loopback HTTP")


def _fetch_json(url: str, headers: Mapping[str, str], timeout: float) -> Any:
    request = Request(url, method="GET", headers={"Accept": "application/json", **dict(headers)})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _windows_loopback_bridge_available() -> bool:
    """Return whether this process can safely ask Windows for loopback data."""
    if os.name == "nt" or not shutil.which("powershell.exe"):
        return False
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
    except OSError:
        return False
    return "microsoft" in release.casefold()


def _fetch_windows_loopback_json(
    url: str, headers: Mapping[str, str], timeout: float
) -> Any:
    """Read a Windows-only loopback endpoint from a WSL-hosted MCP server.

    The supervised Claude Agents console deliberately binds to Windows
    127.0.0.1. On WSL installations without mirrored networking, Linux
    127.0.0.1 is a different interface. This bridge keeps the service private
    instead of opening it on the LAN.
    """
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError("Windows bridge accepts loopback HTTP only")
    if not _windows_loopback_bridge_available():
        raise OSError("Windows loopback bridge is unavailable")

    request_payload = json.dumps(
        {"url": url, "headers": dict(headers), "timeout": max(1, int(timeout))}
    )
    script = (
        "$utf8=New-Object System.Text.UTF8Encoding($false);"
        "[Console]::OutputEncoding=$utf8;$OutputEncoding=$utf8;"
        "$ErrorActionPreference='Stop';"
        "$request=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
        "$headers=@{};"
        "if($request.headers){"
        "$request.headers.PSObject.Properties|ForEach-Object{$headers[$_.Name]=[string]$_.Value}"
        "};"
        "$result=Invoke-RestMethod -Uri ([string]$request.url) -Method Get "
        "-Headers $headers -TimeoutSec ([int]$request.timeout);"
        "$result|ConvertTo-Json -Depth 64 -Compress"
    )
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            check=False,
            capture_output=True,
            text=True,
            input=request_payload,
            timeout=timeout + 5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OSError(f"Windows loopback request failed: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or "Windows loopback request failed").strip()[-240:]
        raise OSError(detail)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise OSError("Windows loopback response was not valid JSON") from error


def _source_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, URLError):
        return f"connection failed: {error.reason}"
    return str(error)[:240]


def _read_usage(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "unavailable", "reason": "Jarvis usage file does not exist yet"}
    except (OSError, ValueError) as error:
        return {"status": "unavailable", "reason": f"Jarvis usage file is unreadable: {error}"}

    totals = raw.get("totals") or raw.get("total") or raw
    return {
        "status": "available",
        "data": {
            "llmInputTokens": int(totals.get("llm_in", 0) or 0),
            "llmOutputTokens": int(totals.get("llm_out", 0) or 0),
            "turns": int(totals.get("turns", 0) or 0),
            "ttsCharacters": int(totals.get("tts_chars", 0) or 0),
            "actualCost": None,
            "costReason": "Jarvis model token prices are not configured in the HUD",
            "daily": raw.get("days", {}),
        },
    }


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        result[value] = result.get(value, 0) + 1
    return result


def _compact_outreach_source(name: str, payload: Any) -> Any:
    """Keep operational evidence while excluding large draft/source bodies."""
    if name == "research" and isinstance(payload, dict):
        rows = payload.get("records") if isinstance(payload.get("records"), list) else []
        return {
            "count": len(rows),
            "byStatus": _counts(rows, "status"),
            "sendingEnabled": bool(payload.get("sendingEnabled", False)),
            "recent": [
                {
                    "id": row.get("id"),
                    "prospectId": row.get("prospectId"),
                    "businessName": (row.get("package") or {}).get("businessName")
                    if isinstance(row.get("package"), dict) else None,
                    "status": row.get("status"),
                    "version": row.get("version"),
                    "delivery": row.get("delivery"),
                    "updatedAt": row.get("updatedAt"),
                }
                for row in rows[:25] if isinstance(row, dict)
            ],
        }
    if name == "territoryWork" and isinstance(payload, dict):
        rows = payload.get("work") if isinstance(payload.get("work"), list) else []
        return {
            "count": len(rows),
            "byResearchStatus": _counts(rows, "researchStatus"),
            "current": payload.get("current"),
            "next": payload.get("next"),
            "sendingEnabled": bool(payload.get("sendingEnabled", False)),
            "work": [
                {
                    "id": row.get("id"),
                    "zip": row.get("zip"),
                    "niche": row.get("niche"),
                    "researchStatus": row.get("researchStatus"),
                    "outreachStatus": row.get("outreachStatus"),
                    "metrics": row.get("metrics"),
                    "updatedAt": row.get("updatedAt"),
                }
                for row in rows[:25] if isinstance(row, dict)
            ],
        }
    return payload


def build_operations_snapshot(
    hours: int = 24,
    lead: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    fetch_json: JsonFetcher = _fetch_json,
    local_fetch_json: JsonFetcher | None = None,
    now: datetime | None = None,
    usage_path: Path | None = None,
) -> dict[str, Any]:
    """Collect one bounded, read-only view from existing SmartKlix systems."""
    if not 1 <= hours <= 168:
        raise ValueError("hours must be between 1 and 168")
    if lead is not None:
        lead = lead.strip()
        if not 2 <= len(lead) <= 200:
            raise ValueError("lead must be between 2 and 200 characters")

    env = os.environ if environ is None else environ
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    since = current.astimezone(timezone.utc) - timedelta(hours=hours)
    since_text = since.isoformat().replace("+00:00", "Z")
    timeout = min(max(float(env.get("SMARTKLIX_READ_TIMEOUT_SECONDS", "8")), 1), 30)

    crm: dict[str, Any]
    crm_token = env.get("SMARTKLIX_JARVIS_READ_TOKEN", "")
    try:
        crm_base = _validate_base_url(
            env.get("SMARTKLIX_CRM_BASE_URL", DEFAULT_CRM_BASE_URL), "SMARTKLIX_CRM_BASE_URL"
        )
        if len(crm_token) < 32:
            crm = {"status": "unavailable", "reason": "SMARTKLIX_JARVIS_READ_TOKEN is not configured"}
        else:
            params = {"since": since_text}
            if lead:
                params["lead"] = lead
            payload = fetch_json(
                f"{crm_base}/api/jarvis/operations?{urlencode(params)}",
                {"x-jarvis-read-token": crm_token},
                timeout,
            )
            crm = {"status": "available", "data": payload}
    except Exception as error:
        crm = {"status": "unavailable", "reason": _source_error(error)}

    outreach: dict[str, Any]
    try:
        outreach_base = _validate_base_url(
            env.get("SMARTKLIX_OUTREACH_BASE_URL", DEFAULT_OUTREACH_BASE_URL),
            "SMARTKLIX_OUTREACH_BASE_URL",
        )
        admin_token = env.get("SMARTKLIX_OUTREACH_ADMIN_TOKEN", "")
        headers = {"x-admin-token": admin_token} if admin_token else {}
        paths = {
            "metrics": "/api/metrics",
            "workers": "/api/workers",
            "activity": "/api/activity?limit=25",
            "usage": "/api/usage",
            "analytics": "/api/analytics",
            "executions": "/api/executions?limit=25",
            "research": "/api/cold-research",
            "territoryWork": "/api/territory/work",
        }
        outreach_fetch = local_fetch_json or fetch_json
        if (
            local_fetch_json is None
            and fetch_json is _fetch_json
            and _windows_loopback_bridge_available()
        ):
            outreach_fetch = _fetch_windows_loopback_json
        collected: dict[str, Any] = {}
        failures: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="smartklix-read") as pool:
            requests = {
                pool.submit(outreach_fetch, f"{outreach_base}{path}", headers, timeout): name
                for name, path in paths.items()
            }
            for future in as_completed(requests):
                name = requests[future]
                try:
                    collected[name] = _compact_outreach_source(name, future.result())
                except Exception as error:
                    failures[name] = _source_error(error)
        metrics = collected.get("metrics")
        if isinstance(metrics, dict) and metrics.get("researchOnly") is True:
            collected["operatingMode"] = {
                "name": "supervised_research",
                "researchOnly": True,
                "legacyWorkersExpected": False,
                "sendingEnabled": False,
                "executionEnabled": False,
                "interpretation": (
                    "The supervised console intentionally runs without the legacy "
                    "autonomous worker fleet. Zero workers or legacy worker health "
                    "offline is expected in this mode. Activity and execution failures "
                    "from the dormant pipeline are preserved audit history unless a "
                    "current supervised action explicitly owns them."
                ),
            }
            workers = collected.get("workers")
            if isinstance(workers, dict) and int(workers.get("count", 0) or 0) == 0:
                workers["operationalStatus"] = "expected_idle"
                workers["expectedInSupervisedResearch"] = True
        outreach = {
            "status": "available" if collected else "unavailable",
            "data": collected,
            "partialFailures": failures,
        }
        if not collected:
            outreach["reason"] = "Local outreach read API is not running or reachable"
    except Exception as error:
        outreach = {"status": "unavailable", "reason": _source_error(error)}

    if usage_path is None:
        usage_path = Path(__file__).resolve().parents[1] / "server" / "logs" / "usage_stats.json"

    missing_telemetry = [
        "one daily budget ledger joining Jarvis, model, research, STT, TTS, and delivery costs",
        "budget allocated, reserved, spent, and remaining by Buddy objective",
        "durable runtime by objective across Hermes and every SmartKlix worker",
        "provider-billed cost reconciliation rather than local estimates",
    ]

    return {
        "schemaVersion": 1,
        "generatedAt": current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window": {"hours": hours, "since": since_text},
        "leadQuery": lead,
        "authority": {
            "readOnly": True,
            "canStart": False,
            "canPause": False,
            "canApprove": False,
            "canExecute": False,
            "canSend": False,
            "canSpend": False,
        },
        "sources": {
            "crm": crm,
            "outreach": outreach,
            "jarvisUsage": _read_usage(usage_path),
        },
        "missingTelemetry": missing_telemetry,
    }
