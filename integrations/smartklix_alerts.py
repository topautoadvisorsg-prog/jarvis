"""Deterministic SmartKlix attention events and local delivery policy.

This module observes the existing read-only operations snapshot. It does not
call an LLM, start work, approve, execute, send, or mutate either SmartKlix
system. Delivery remains a separate future boundary.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


SEVERITY_ORDER = {"urgent": 0, "attention": 1, "info": 2}
BLOCKED_PROPOSAL_STATES = {
    "review_rejected",
    "approval_stale",
    "dispatch_failed",
    "failed",
    "expired",
}
PENDING_PROPOSAL_STATES = {"pending", "review_complete", "needs_review"}
ACTIVE_PROPOSAL_STATES = {"approved", "queued", "processing"}
FAILURE_STATES = {"failed", "error", "dispatch_failed", "undelivered", "bounced"}
HANDOFF_ACTIONS = {
    "approval.pending": "review_approval",
    "workflow.blocked": "inspect_blocked_work",
    "control.kill_switch_active": "review_kill_switch",
    "reply.received": "review_reply",
    "execution.failed": "inspect_execution_failure",
    "intake.needs_review": "review_intake",
    "source.unavailable": "restore_visibility",
    "source.partial_failure": "inspect_read_failure",
    "research.failed": "inspect_research_failure",
    "worker.exception": "inspect_worker_failure",
}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _count(mapping: Any, names: set[str]) -> int:
    total = 0
    for key, value in _mapping(mapping).items():
        if str(key).casefold() not in names:
            continue
        try:
            total += int(value or 0)
        except (TypeError, ValueError):
            continue
    return total


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _event(
    *,
    occurred_at: str,
    source: str,
    event_type: str,
    subject: dict[str, Any],
    facts: dict[str, Any],
    severity: str,
    requires_buddy: bool,
    dedupe_key: str,
) -> dict[str, Any]:
    identity = json.dumps(
        {
            "source": source,
            "type": event_type,
            "subject": subject,
            "facts": facts,
            "dedupeKey": dedupe_key,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return {
        "eventId": hashlib.sha256(identity.encode()).hexdigest()[:24],
        "occurredAt": occurred_at,
        "source": source,
        "type": event_type,
        "subject": subject,
        "facts": facts,
        "severity": severity,
        "requiresBuddy": requires_buddy,
        "dedupeKey": dedupe_key,
        "evidenceUrl": None,
    }


def build_attention_events(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize authoritative snapshot facts into deterministic events."""
    occurred_at = str(snapshot.get("generatedAt") or datetime.now(timezone.utc).isoformat())
    sources = _mapping(snapshot.get("sources"))
    events: list[dict[str, Any]] = []

    crm_source = _mapping(sources.get("crm"))
    if crm_source.get("status") != "available":
        reason = str(crm_source.get("reason") or "CRM snapshot unavailable")[:240]
        events.append(_event(
            occurred_at=occurred_at,
            source="smartklix-crm",
            event_type="source.unavailable",
            subject={"type": "system", "id": "smartklix-crm"},
            facts={"reason": reason},
            severity="attention",
            requires_buddy=True,
            dedupe_key="source:smartklix-crm:unavailable",
        ))
    else:
        crm = _mapping(crm_source.get("data"))
        controls = _mapping(crm.get("controls"))
        if controls.get("aiKillSwitchActive") is True:
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-crm",
                event_type="control.kill_switch_active",
                subject={"type": "control", "id": "ai-kill-switch"},
                facts={"active": True},
                severity="attention",
                requires_buddy=True,
                dedupe_key="control:ai-kill-switch:active",
            ))

        proposals = _mapping(crm.get("proposals"))
        attention_rows = proposals.get("attention")
        if isinstance(attention_rows, list):
            for proposal in attention_rows[:25]:
                if not isinstance(proposal, dict):
                    continue
                proposal_id = str(proposal.get("id") or "unknown")
                status = str(proposal.get("status") or "unknown").casefold()
                facts = {
                    "status": status,
                    "summary": proposal.get("summary"),
                    "reason": proposal.get("reason"),
                    "createdAt": proposal.get("createdAt"),
                }
                if status in BLOCKED_PROPOSAL_STATES:
                    event_type, severity, requires_buddy = "workflow.blocked", "attention", True
                elif status in PENDING_PROPOSAL_STATES:
                    event_type, severity, requires_buddy = "approval.pending", "attention", True
                elif status in ACTIVE_PROPOSAL_STATES:
                    event_type, severity, requires_buddy = "workflow.in_progress", "info", False
                else:
                    continue
                events.append(_event(
                    occurred_at=occurred_at,
                    source="smartklix-crm",
                    event_type=event_type,
                    subject={"type": "proposal", "id": proposal_id},
                    facts=facts,
                    severity=severity,
                    requires_buddy=requires_buddy,
                    dedupe_key=f"proposal:{proposal_id}:{status}",
                ))

        communication = _mapping(crm.get("communication"))
        replies = _safe_int(communication.get("replies"))
        if replies:
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-crm",
                event_type="reply.received",
                subject={"type": "reporting-window", "id": "current"},
                facts={"count": replies},
                severity="attention",
                requires_buddy=True,
                dedupe_key=f"reply:window:{replies}",
            ))

        failed_outbox = _count(_mapping(crm.get("execution")).get("outboxByStatus"), FAILURE_STATES)
        if failed_outbox:
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-crm",
                event_type="execution.failed",
                subject={"type": "outbox", "id": "current-window"},
                facts={"count": failed_outbox},
                severity="attention",
                requires_buddy=True,
                dedupe_key=f"execution:failed:{failed_outbox}",
            ))

        needs_review = _count(_mapping(crm.get("intake")).get("byStatus"), {"needs_review"})
        if needs_review:
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-crm",
                event_type="intake.needs_review",
                subject={"type": "intake", "id": "current-window"},
                facts={"count": needs_review},
                severity="attention",
                requires_buddy=True,
                dedupe_key=f"intake:needs-review:{needs_review}",
            ))

    outreach_source = _mapping(sources.get("outreach"))
    if outreach_source.get("status") != "available":
        events.append(_event(
            occurred_at=occurred_at,
            source="smartklix-claude-agents",
            event_type="source.inactive",
            subject={"type": "system", "id": "research-console"},
            facts={"reason": str(outreach_source.get("reason") or "Research console is stopped")[:240]},
            severity="info",
            requires_buddy=False,
            dedupe_key="source:research-console:inactive",
        ))
    else:
        outreach = _mapping(outreach_source.get("data"))
        partial_failures = _mapping(outreach_source.get("partialFailures"))
        for name, reason in sorted(partial_failures.items()):
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-claude-agents",
                event_type="source.partial_failure",
                subject={"type": "read-surface", "id": str(name)},
                facts={"reason": str(reason)[:240]},
                severity="attention",
                requires_buddy=True,
                dedupe_key=f"source:outreach:{name}:failure",
            ))

        research_failed = _count(_mapping(outreach.get("research")).get("byStatus"), FAILURE_STATES)
        if research_failed:
            events.append(_event(
                occurred_at=occurred_at,
                source="smartklix-claude-agents",
                event_type="research.failed",
                subject={"type": "research", "id": "current-window"},
                facts={"count": research_failed},
                severity="attention",
                requires_buddy=True,
                dedupe_key=f"research:failed:{research_failed}",
            ))

        activity = _mapping(outreach.get("activity")).get("events")
        if isinstance(activity, list):
            for row in activity[:25]:
                if not isinstance(row, dict) or str(row.get("level", "")).casefold() not in {"warn", "error"}:
                    continue
                row_id = str(row.get("id") or hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:16])
                events.append(_event(
                    occurred_at=str(row.get("timestamp") or occurred_at),
                    source="smartklix-claude-agents",
                    event_type="worker.exception",
                    subject={"type": "activity", "id": row_id},
                    facts={
                        "level": row.get("level"),
                        "category": row.get("category"),
                        "message": str(row.get("message") or "")[:240],
                    },
                    severity="attention",
                    requires_buddy=True,
                    dedupe_key=f"activity:{row_id}",
                ))

    return sorted(
        events,
        key=lambda item: (SEVERITY_ORDER.get(item["severity"], 99), item["dedupeKey"]),
    )


class AlertLedger:
    """Local dedupe, cooldown, and quiet-hours policy for future delivery."""

    def __init__(
        self,
        path: Path,
        *,
        timezone_name: str = "America/Tijuana",
        timezone_info: tzinfo | None = None,
        quiet_start_hour: int = 21,
        quiet_end_hour: int = 8,
        cooldown: timedelta = timedelta(hours=6),
    ) -> None:
        if not 0 <= quiet_start_hour <= 23 or not 0 <= quiet_end_hour <= 23:
            raise ValueError("quiet hours must be between 0 and 23")
        self.path = path
        self.timezone = timezone_info or ZoneInfo(timezone_name)
        self.quiet_start_hour = quiet_start_hour
        self.quiet_end_hour = quiet_end_hour
        self.cooldown = cooldown

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    def _save(self, ledger: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        temporary.replace(self.path)

    @staticmethod
    def _utc(now: datetime | None = None) -> datetime:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_time(value: Any, fallback: datetime) -> datetime:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return fallback
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def observe(
        self,
        events: Iterable[dict[str, Any]],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Persist correlation/timing only; never store event facts or deliver."""
        current = self._utc(now)
        current_iso = self._iso(current)
        ledger = self._load()
        observed = 0
        changed = False
        active_keys: set[str] = set()
        for event in events:
            if not event.get("requiresBuddy"):
                continue
            key = str(event.get("dedupeKey") or event.get("eventId") or "")
            if not key:
                continue
            active_keys.add(key)
            previous = _mapping(ledger.get(key))
            if previous.get("resolvedAt"):
                previous = {}
            ledger[key] = {
                **previous,
                "eventId": event.get("eventId"),
                "eventType": event.get("type"),
                "severity": event.get("severity"),
                "firstSeenAt": previous.get("firstSeenAt") or current_iso,
                "lastSeenAt": current_iso,
            }
            observed += 1
            changed = True
        for key, value in list(ledger.items()):
            state = _mapping(value)
            if key not in active_keys and state.get("firstSeenAt") and not state.get("resolvedAt"):
                ledger[key] = {**state, "resolvedAt": current_iso}
                changed = True
        if changed:
            self._save(ledger)
        return {"observed": observed, "recordedAt": current_iso}

    def build_handoffs(
        self,
        events: Iterable[dict[str, Any]],
        *,
        now: datetime | None = None,
        escalation_after: timedelta = timedelta(hours=2),
    ) -> list[dict[str, Any]]:
        """Build a deterministic Buddy handoff queue from already-classified events."""
        current = self._utc(now)
        ledger = self._load()
        handoffs: list[dict[str, Any]] = []
        for event in events:
            if not event.get("requiresBuddy"):
                continue
            key = str(event.get("dedupeKey") or event.get("eventId") or "")
            state = _mapping(ledger.get(key))
            if state.get("acknowledgedAt"):
                continue
            first_seen = self._parse_time(
                state.get("firstSeenAt") or event.get("occurredAt"), current,
            )
            deadline = first_seen + escalation_after
            overdue = current >= deadline
            event_type = str(event.get("type") or "attention.required")
            handoffs.append({
                "handoffId": str(event.get("eventId") or key),
                "dedupeKey": key,
                "eventType": event_type,
                "subject": event.get("subject") or {},
                "source": event.get("source"),
                "priority": "urgent" if event.get("severity") == "urgent" or overdue else "attention",
                "requiresBuddy": True,
                "recommendedAction": HANDOFF_ACTIONS.get(event_type, "review_attention_item"),
                "firstSeenAt": self._iso(first_seen),
                "escalateAt": self._iso(deadline),
                "overdue": overdue,
                "facts": event.get("facts") or {},
            })
        return sorted(
            handoffs,
            key=lambda item: (0 if item["priority"] == "urgent" else 1, item["firstSeenAt"], item["dedupeKey"]),
        )

    def acknowledge(
        self,
        dedupe_key: str,
        *,
        acknowledged_by: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Record a local acknowledgement without changing SmartKlix state."""
        ledger = self._load()
        current = self._utc(now)
        state = _mapping(ledger.get(dedupe_key))
        if not state:
            raise KeyError("unknown handoff")
        state.update({
            "acknowledgedAt": self._iso(current),
            "acknowledgedBy": str(acknowledged_by)[:80],
        })
        ledger[dedupe_key] = state
        self._save(ledger)
        return {"dedupeKey": dedupe_key, **state}

    def _in_quiet_hours(self, now: datetime) -> bool:
        hour = now.astimezone(self.timezone).hour
        if self.quiet_start_hour == self.quiet_end_hour:
            return False
        if self.quiet_start_hour > self.quiet_end_hour:
            return hour >= self.quiet_start_hour or hour < self.quiet_end_hour
        return self.quiet_start_hour <= hour < self.quiet_end_hour

    def evaluate(
        self,
        events: Iterable[dict[str, Any]],
        *,
        now: datetime | None = None,
        record: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        current = self._utc(now)
        ledger = self._load()
        deliverable: list[dict[str, Any]] = []
        suppressed: list[dict[str, Any]] = []

        for event in events:
            if not event.get("requiresBuddy"):
                continue
            key = str(event.get("dedupeKey") or event.get("eventId"))
            reason = None
            state = _mapping(ledger.get(key))
            if state.get("acknowledgedAt"):
                suppressed.append({**event, "suppressedReason": "acknowledged"})
                continue
            previous = state.get("lastDeliveredAt")
            if previous:
                try:
                    last = datetime.fromisoformat(str(previous).replace("Z", "+00:00"))
                    if current.astimezone(timezone.utc) - last.astimezone(timezone.utc) < self.cooldown:
                        reason = "cooldown"
                except ValueError:
                    pass
            if reason is None and event.get("severity") != "urgent" and self._in_quiet_hours(current):
                reason = "quiet_hours"
            if reason:
                suppressed.append({**event, "suppressedReason": reason})
                continue
            deliverable.append(event)
            if record:
                ledger[key] = {
                    **state,
                    "eventId": event.get("eventId"),
                    "lastDeliveredAt": self._iso(current),
                }

        if record and deliverable:
            self._save(ledger)
        return {"deliverable": deliverable, "suppressed": suppressed}
