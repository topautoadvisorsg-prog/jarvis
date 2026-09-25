"""MCP entry point for the single read-only SmartKlix operations tool."""

from __future__ import annotations

import json

from mcp.server import MCPServer

from smartklix_ops import build_operations_snapshot


mcp = MCPServer(
    "smartklix-operations",
    instructions=(
        "Read-only visibility into the existing SmartKlix CRM and Claude Agents. "
        "This server cannot start, pause, approve, execute, send, spend, or mutate anything."
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


if __name__ == "__main__":
    mcp.run()
