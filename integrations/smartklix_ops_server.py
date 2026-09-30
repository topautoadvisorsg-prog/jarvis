"""MCP entry point for SmartKlix visibility and bounded console lifecycle tools."""

from __future__ import annotations

import json

from mcp.server import MCPServer

from smartklix_control import ControlError, SmartKlixResearchControl
from smartklix_ops import build_operations_snapshot


mcp = MCPServer(
    "smartklix-operations",
    instructions=(
        "Visibility into the existing SmartKlix CRM and Claude Agents plus bounded "
        "lifecycle control of the approved local research console. Lifecycle control "
        "cannot create objectives, approve, execute, send, spend, or mutate CRM data."
    ),
)


@mcp.tool()
def get_smartklix_operations(hours: int = 24, lead: str | None = None) -> str:
    """Get current SmartKlix outreach status from authoritative existing systems.

    Args:
        hours: Reporting window from 1 to 168 hours. Defaults to 24.
        lead: Optional lead ID, name, company, email, or phone fragment.
    """
    return json.dumps(build_operations_snapshot(hours=hours, lead=lead), indent=2)


def _control() -> SmartKlixResearchControl:
    return SmartKlixResearchControl()


@mcp.tool()
def get_smartklix_research_console_status() -> str:
    """Check the bounded local SmartKlix research console lifecycle state."""
    try:
        return json.dumps(_control().status(), indent=2)
    except ControlError as error:
        return json.dumps({"status": "unavailable", "error": str(error)}, indent=2)


@mcp.tool()
def start_smartklix_research_console(
    idempotency_key: str,
    objective: str,
    max_runtime_minutes: int = 60,
) -> str:
    """Start only the supervised research console, bounded to 5-240 minutes.

    This never starts legacy workers, delivery, CRM execution, or email sending.
    Use a unique idempotency key for the requested action.
    """
    try:
        result = _control().start(
            idempotency_key=idempotency_key,
            objective=objective,
            max_runtime_minutes=max_runtime_minutes,
        )
        return json.dumps(result, indent=2)
    except ControlError as error:
        return json.dumps({"status": "rejected", "error": str(error)}, indent=2)


@mcp.tool()
def stop_smartklix_research_console(idempotency_key: str, reason: str) -> str:
    """Stop only the supervised local SmartKlix research console.

    Use a unique idempotency key and state the operator reason. This does not
    approve, execute, send, or change CRM data.
    """
    try:
        return json.dumps(
            _control().stop(idempotency_key=idempotency_key, reason=reason),
            indent=2,
        )
    except ControlError as error:
        return json.dumps({"status": "rejected", "error": str(error)}, indent=2)


if __name__ == "__main__":
    mcp.run()
