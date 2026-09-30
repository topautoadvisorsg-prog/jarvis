"""Safe preflight for the SmartKlix CRM read-only Jarvis connection."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from .smartklix_ops import DEFAULT_CRM_BASE_URL, _validate_base_url
except ImportError:  # Support direct execution from the command line.
    from smartklix_ops import DEFAULT_CRM_BASE_URL, _validate_base_url


StatusFetcher = Callable[[str, Mapping[str, str], float], tuple[int, Any]]
PREFLIGHT_ENV_KEYS = {
    "SMARTKLIX_CRM_BASE_URL",
    "SMARTKLIX_JARVIS_READ_TOKEN",
    "SMARTKLIX_READ_TIMEOUT_SECONDS",
}


def _fetch_status(
    url: str,
    headers: Mapping[str, str],
    timeout: float,
) -> tuple[int, Any]:
    request = Request(
        url,
        method="GET",
        headers={"Accept": "application/json", **dict(headers)},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw)
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload: Any = json.loads(raw)
        except ValueError:
            payload = {"error": raw[:240]}
        return error.code, payload


def _read_only_authority(payload: Any) -> bool:
    if not isinstance(payload, Mapping):
        return False
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or authority.get("readOnly") is not True:
        return False
    forbidden = ("canStage", "canReview", "canApprove", "canExecute", "canSend")
    return all(authority.get(name) is False for name in forbidden)


def load_preflight_environment(
    path: Path,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load only preflight keys from a simple dotenv file without interpolation."""
    result = dict(os.environ if base is None else base)
    for raw_line in path.expanduser().read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in PREFLIGHT_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def build_crm_activation_report(
    *,
    environ: Mapping[str, str] | None = None,
    fetch_status: StatusFetcher = _fetch_status,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Probe deployment and authentication without exposing or changing secrets."""
    env = os.environ if environ is None else environ
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    generated_at = current.astimezone(timezone.utc)
    since = generated_at - timedelta(hours=24)
    timeout = min(max(float(env.get("SMARTKLIX_READ_TIMEOUT_SECONDS", "8")), 1), 30)
    token = env.get("SMARTKLIX_JARVIS_READ_TOKEN", "")

    try:
        base_url = _validate_base_url(
            env.get("SMARTKLIX_CRM_BASE_URL", DEFAULT_CRM_BASE_URL),
            "SMARTKLIX_CRM_BASE_URL",
        )
    except (TypeError, ValueError) as error:
        return {
            "schemaVersion": 1,
            "generatedAt": generated_at.isoformat().replace("+00:00", "Z"),
            "ready": False,
            "status": "invalid_configuration",
            "reason": str(error),
            "tokenConfiguredLocally": len(token) >= 32,
            "productionChanged": False,
        }

    url = f"{base_url}/api/jarvis/operations?{urlencode({'since': since.isoformat()})}"
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "generatedAt": generated_at.isoformat().replace("+00:00", "Z"),
        "endpoint": f"{base_url}/api/jarvis/operations",
        "ready": False,
        "tokenConfiguredLocally": len(token) >= 32,
        "productionChanged": False,
        "authorityExpected": {
            "readOnly": True,
            "canStage": False,
            "canReview": False,
            "canApprove": False,
            "canExecute": False,
            "canSend": False,
        },
    }

    try:
        public_status, public_payload = fetch_status(url, {}, timeout)
    except (OSError, URLError, ValueError) as error:
        report.update(status="unreachable", reason=str(error)[:240])
        return report

    report["unauthenticatedProbe"] = {
        "httpStatus": public_status,
        "code": public_payload.get("code") if isinstance(public_payload, Mapping) else None,
    }
    if public_status == 200:
        report.update(
            status="security_failure",
            reason="The operations route accepted an unauthenticated request.",
        )
        return report
    if public_status == 503 and isinstance(public_payload, Mapping):
        if public_payload.get("code") == "JARVIS_READ_NOT_CONFIGURED":
            report.update(
                status="production_token_required",
                reason=(
                    "The read-only route is deployed but its Vercel token is not configured."
                ),
            )
            return report
    if public_status != 401:
        report.update(
            status="unexpected_response",
            reason=f"Expected HTTP 401 or configuration HTTP 503, received {public_status}.",
        )
        return report
    if len(token) < 32:
        report.update(
            status="local_token_required",
            reason="Hermes does not have a 32+ character SmartKlix read token.",
        )
        return report

    try:
        authenticated_status, authenticated_payload = fetch_status(
            url,
            {"x-jarvis-read-token": token},
            timeout,
        )
    except (OSError, URLError, ValueError) as error:
        report.update(status="unreachable", reason=str(error)[:240])
        return report

    report["authenticatedProbe"] = {"httpStatus": authenticated_status}
    if authenticated_status == 401:
        report.update(
            status="token_mismatch",
            reason="Hermes and the CRM do not have the same read token.",
        )
        return report
    if authenticated_status != 200:
        report.update(
            status="snapshot_unavailable",
            reason=f"The authenticated snapshot returned HTTP {authenticated_status}.",
        )
        return report
    if not _read_only_authority(authenticated_payload):
        report.update(
            status="authority_mismatch",
            reason="The CRM snapshot did not prove the expected read-only authority.",
        )
        return report

    report.update(
        ready=True,
        status="ready",
        reason="The deployed CRM route is authenticated and read-only.",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    environ = load_preflight_environment(args.env_file) if args.env_file else None
    report = build_crm_activation_report(environ=environ)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ready"] else 2)


if __name__ == "__main__":
    main()
