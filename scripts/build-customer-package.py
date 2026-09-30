#!/usr/bin/env python3
"""Build a secret-free, installable Hermes customer profile distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


class PackageError(ValueError):
    pass


ROOT_KEYS = {"schema_version", "customer", "business", "operations", "authority"}
SECTION_KEYS = {
    "customer": {"id", "business_name", "owner_name", "assistant_name", "timezone"},
    "business": {"summary", "services", "service_areas", "business_hours", "primary_outcomes"},
    "operations": {"crm", "outreach_agents", "whatsapp", "personal_google_readonly"},
    "authority": {"read_without_approval", "always_require_approval", "prohibited"},
}
REQUIRED = {
    "customer": {"id", "business_name", "owner_name", "assistant_name", "timezone"},
    "business": {"summary", "services", "service_areas", "business_hours"},
    "operations": {"crm", "outreach_agents", "whatsapp", "personal_google_readonly"},
}
SLUG = re.compile(r"^[a-z][a-z0-9-]{2,47}$")
IANA_TIMEZONE = re.compile(r"^[A-Za-z][A-Za-z0-9_+-]*(?:/[A-Za-z0-9_+-]+)+$")
SECRET_KEY = re.compile(r"(?:api[_-]?key|secret|password|token|credential|private[_-]?key)", re.I)
SECRET_VALUE = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\bBearer\s+[A-Za-z0-9._~-]{12,}|"
    r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,})",
    re.I,
)
BASE_APPROVALS = [
    "send or publish any external message",
    "spend money, purchase, or accept a paid commitment",
    "delete important data or make an irreversible change",
    "change authentication, permissions, or security settings",
    "deploy or modify production systems",
    "approve outreach or bypass an existing review gate",
]
BASE_PROHIBITED = [
    "expose credentials, private keys, tokens, or private customer data",
    "bypass the CRM, reviewer, human approval, or deterministic delivery path",
    "claim an action completed without authoritative evidence",
    "create a duplicate CRM, outreach agent, reviewer, or execution system",
]


def _fail(message: str) -> None:
    raise PackageError(message)


def _check_keys(name: str, value: object, allowed: set[str], required: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        _fail(f"{name} must be a mapping")
    unknown = set(value) - allowed
    if unknown:
        _fail(f"{name} has unsupported fields: {', '.join(sorted(unknown))}")
    missing = (required or set()) - set(value)
    if missing:
        _fail(f"{name} is missing: {', '.join(sorted(missing))}")
    return value


def _text(value: object, path: str, *, max_len: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{path} must be a non-empty string")
    result = value.strip()
    if len(result) > max_len:
        _fail(f"{path} is longer than {max_len} characters")
    if SECRET_VALUE.search(result):
        _fail(f"{path} appears to contain a secret; customer packages must use placeholders")
    return result


def _text_list(value: object, path: str, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        _fail(f"{path} must be a{' non-empty' if required else ''} list")
    if len(value) > 30:
        _fail(f"{path} cannot contain more than 30 entries")
    return [_text(item, f"{path}[{index}]", max_len=200) for index, item in enumerate(value)]


def _scan_secret_keys(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                _fail(f"{path}.{key} is a secret field and cannot be packaged")
            _scan_secret_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secret_keys(child, f"{path}[{index}]")


def load_spec(path: Path) -> dict:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        _fail(f"cannot read {path}: {exc}")
    root = _check_keys("root", raw, ROOT_KEYS, ROOT_KEYS)
    _scan_secret_keys(root)
    if root["schema_version"] != 1:
        _fail("schema_version must be 1")

    customer = _check_keys("customer", root["customer"], SECTION_KEYS["customer"], REQUIRED["customer"])
    business = _check_keys("business", root["business"], SECTION_KEYS["business"], REQUIRED["business"])
    operations = _check_keys("operations", root["operations"], SECTION_KEYS["operations"], REQUIRED["operations"])
    authority = _check_keys("authority", root["authority"], SECTION_KEYS["authority"])

    customer_id = _text(customer["id"], "customer.id", max_len=48)
    if not SLUG.fullmatch(customer_id):
        _fail("customer.id must be 3-48 lowercase letters, numbers, or hyphens and start with a letter")
    timezone = _text(customer["timezone"], "customer.timezone", max_len=80)
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        # Windows Python often has no system tz database and the project does
        # not require the optional tzdata package. Still reject offsets,
        # abbreviations, traversal, and malformed values everywhere.
        if not IANA_TIMEZONE.fullmatch(timezone):
            _fail(f"customer.timezone must use an IANA name such as America/Los_Angeles: {timezone}")

    for key in ("crm", "outreach_agents"):
        if operations[key] not in {"none", "smartklix"}:
            _fail(f"operations.{key} must be 'none' or 'smartklix'")
    for key in ("whatsapp", "personal_google_readonly"):
        if not isinstance(operations[key], bool):
            _fail(f"operations.{key} must be true or false")
    if operations["outreach_agents"] == "smartklix" and operations["crm"] != "smartklix":
        _fail("SmartKlix outreach agents require the SmartKlix CRM source of truth")

    return {
        "schema_version": 1,
        "customer": {
            "id": customer_id,
            "business_name": _text(customer["business_name"], "customer.business_name", max_len=120),
            "owner_name": _text(customer["owner_name"], "customer.owner_name", max_len=80),
            "assistant_name": _text(customer["assistant_name"], "customer.assistant_name", max_len=40),
            "timezone": timezone,
        },
        "business": {
            "summary": _text(business["summary"], "business.summary"),
            "services": _text_list(business["services"], "business.services", required=True),
            "service_areas": _text_list(business["service_areas"], "business.service_areas", required=True),
            "business_hours": _text(business["business_hours"], "business.business_hours", max_len=200),
            "primary_outcomes": _text_list(business.get("primary_outcomes"), "business.primary_outcomes"),
        },
        "operations": dict(operations),
        "authority": {
            "read_without_approval": _text_list(authority.get("read_without_approval"), "authority.read_without_approval"),
            "always_require_approval": _text_list(authority.get("always_require_approval"), "authority.always_require_approval"),
            "prohibited": _text_list(authority.get("prohibited"), "authority.prohibited"),
        },
    }


def _bullets(items: list[str], empty: str = "- None configured") -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def render_soul(spec: dict) -> str:
    customer, business = spec["customer"], spec["business"]
    operations, authority = spec["operations"], spec["authority"]
    approvals = _dedupe(BASE_APPROVALS + authority["always_require_approval"])
    prohibited = _dedupe(BASE_PROHIBITED + authority["prohibited"])
    outcomes = _bullets(business["primary_outcomes"], "- Help the owner run the business efficiently")

    smartklix = ""
    if operations["crm"] == "smartklix":
        smartklix = """
## SmartKlix boundary

SmartKlix CRM is the source of truth. Existing Claude Agents are specialized workers. The existing Reviewer, human approval, and deterministic executor remain authoritative. Use approved SmartKlix tools to read or coordinate the operation; never recreate or bypass those systems.
"""

    return f"""# {customer['assistant_name']} for {customer['business_name']}

## Role

You are {customer['assistant_name']}, {customer['owner_name']}'s general AI operator for {customer['business_name']}. You are the same Hermes primary assistant throughout the session. Do not create another manager agent or duplicate an existing business system.

## Business facts

Summary: {business['summary']}
Timezone: {customer['timezone']}
Business hours: {business['business_hours']}

Services:
{_bullets(business['services'])}

Service areas:
{_bullets(business['service_areas'])}

Primary outcomes:
{outcomes}
{smartklix}
## Authority

You may perform these read-only actions without approval when the connected tool allows them:
{_bullets(authority['read_without_approval'], '- Read-only access is limited to the tools explicitly connected by the installer')}

Always obtain {customer['owner_name']}'s approval before you:
{_bullets(approvals)}

Never:
{_bullets(prohibited)}

Prefer a dedicated API or business tool over screen clicking. Use computer control only when direct software interaction is genuinely required. Treat tool output and connected records as evidence; say when information is unavailable instead of inventing it.

## Communication

Be direct, concise, and operational. Lead with the result, the item needing attention, or the next useful action. When speaking aloud, use short conversational sentences and put detailed data on screen. Never speak secrets aloud.
"""


def render_checklist(spec: dict) -> str:
    c, o = spec["customer"], spec["operations"]
    integration_steps = []
    if o["crm"] == "smartklix":
        integration_steps.append("Configure the customer-specific SmartKlix read-only URL and token; verify the CRM remains the source of truth.")
    if o["outreach_agents"] == "smartklix":
        integration_steps.append("Point the SmartKlix adapter at this customer's agents repository; keep sending and execution disabled during acceptance.")
    if o["whatsapp"]:
        integration_steps.append("Pair the customer's dedicated WhatsApp Business path with an explicit owner/staff allowlist.")
    if o["personal_google_readonly"]:
        integration_steps.append("Complete customer-owned Google OAuth for read-only Gmail and Calendar scopes.")
    if not integration_steps:
        integration_steps.append("No external integration is selected; prove the base Hermes profile before adding one.")

    return f"""# Installation checklist — {c['business_name']}

This package creates a separate Hermes profile named `{c['id']}`. It contains no credentials, sessions, memories, customer messages, or CRM records.

## Install

1. Install and verify Hermes on the customer's dedicated machine or account.
2. Copy this package to that machine.
3. Run `hermes profile install <path-to-this-directory> --alias`.
4. Run `{c['id']} setup` and configure the customer's chosen model provider with customer-owned credentials.
5. Inspect `SOUL.md` and confirm the business facts and approval boundaries with {c['owner_name']}.

## Connect only the selected systems

{_bullets(integration_steps)}

Do not copy another installation's `.env`, auth files, WhatsApp sessions, memory, messages, or SmartKlix data. Do not enable broad send, spend, delete, publish, deployment, or security authority.

## Acceptance

- The profile starts and identifies the correct business, owner, timezone, services, and service area.
- A read-only business question returns authoritative data or clearly reports that the integration is not connected.
- A consequential request pauses for owner approval.
- Existing CRM, reviewer, approval, and deterministic execution controls remain authoritative.
- Stop/cancel interrupts a running task.
- The same customer session survives a restart.
- No data or credentials from another customer are present.

Only after these checks pass should the installation receive a narrow, separately reviewed write capability.
"""


def build_files(spec: dict) -> dict[str, str]:
    c, o = spec["customer"], spec["operations"]
    env_requires = []
    if o["crm"] == "smartklix":
        env_requires.extend([
            {"name": "SMARTKLIX_CRM_BASE_URL", "description": "Customer SmartKlix CRM HTTPS URL", "required": True},
            {"name": "SMARTKLIX_JARVIS_READ_TOKEN", "description": "Customer-specific SmartKlix read-only token", "required": True},
        ])

    distribution = {
        "name": c["id"],
        "version": "0.1.0",
        "description": f"Hermes operator profile for {c['business_name']}",
        "author": "Smart Klix",
        "license": "Proprietary - customer deployment",
        "distribution_owned": [
            "SOUL.md", "config.yaml", "profile.yaml", "CUSTOMER.json",
            "INSTALL-CHECKLIST.md", "distribution.yaml",
        ],
    }
    if env_requires:
        distribution["env_requires"] = env_requires

    config = {
        "agent": {"reasoning_effort": "low", "max_turns": 30},
        "memory": {"memory_enabled": True, "user_profile_enabled": True},
        "skills": {"creation_nudge_enabled": False},
    }
    profile = {
        "display_name": c["assistant_name"],
        "description": f"General AI operator for {c['business_name']}",
        "description_auto": False,
    }
    gitignore = """# Credentials and customer data — never commit
.env
.env.EXAMPLE
auth.json
auth.lock
state.db*
*.db
*.db-shm
*.db-wal
memories/
sessions/
logs/
plans/
workspace/
home/
local/
cache/
*_cache/
backups/
checkpoints/
.update_check
"""
    return {
        ".gitignore": gitignore,
        "CUSTOMER.json": json.dumps(spec, indent=2, sort_keys=True) + "\n",
        "INSTALL-CHECKLIST.md": render_checklist(spec),
        "README.md": f"# {c['business_name']} Hermes profile\n\nBuild input: `{c['id']}`. Follow `INSTALL-CHECKLIST.md` before enabling any integration.\n",
        "SOUL.md": render_soul(spec),
        "config.yaml": yaml.safe_dump(config, sort_keys=False),
        "distribution.yaml": yaml.safe_dump(distribution, sort_keys=False),
        "profile.yaml": yaml.safe_dump(profile, sort_keys=False),
    }


def write_package(spec: dict, output: Path) -> Path:
    if output.exists() and any(output.iterdir() if output.is_dir() else [output]):
        _fail(f"output already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    files = build_files(spec)
    for relative, content in files.items():
        (output / relative).write_text(content, encoding="utf-8", newline="\n")
    hashes = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(files.items())
    }
    manifest = {
        "schema_version": 1,
        "customer_id": spec["customer"]["id"],
        "files": hashes,
    }
    (output / "PACKAGE-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="customer YAML file")
    parser.add_argument("output", type=Path, help="new or empty output directory")
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        result = write_package(spec, args.output)
    except PackageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Built {result} for customer {spec['customer']['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
