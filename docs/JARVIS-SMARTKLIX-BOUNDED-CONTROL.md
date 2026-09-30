# Jarvis bounded SmartKlix control

This is the first narrow "hands" capability for the existing `jarvis-main`
Hermes Operations Manager role. It does not add an agent or workflow engine.

## Authority

The `smartklix-operations` MCP server exposes three lifecycle tools in addition
to the read-only operations snapshot:

- `get_smartklix_research_console_status`
- `start_smartklix_research_console`
- `stop_smartklix_research_console`

They can control only the existing Smart Klix Claude Agents
`scripts/local-research.ts` launcher. That launcher forces local research mode,
disables outreach delivery, disables the proposal executor, clears webhook and
admin secrets, and serves the supervised console on loopback port 3001.

These tools cannot create objectives, select prospects, approve work, write CRM
records, send email, spend money, or start the retained legacy worker bootstrap.
The existing Reviewer, Buddy approval, CRM, and deterministic executor remain
authoritative.

## Safety and operation

- Write control is disabled unless `SMARTKLIX_JARVIS_CONTROL_ENABLED=true` and
  a private `SMARTKLIX_JARVIS_CONTROL_TOKEN` of at least 32 characters exists.
- Every start and stop requires a unique idempotency key and a short reason.
- Starts are bounded to 5-240 minutes and get an independent watchdog.
- The adapter validates the recorded process before stopping its process tree.
- HMAC-signed local receipts and an idempotency ledger are stored outside the
  repository, under `SMARTKLIX_CONTROL_STATE_DIR`.
- Status remains available when write control is disabled.

Required per-installation configuration:

```text
SMARTKLIX_AGENTS_ROOT=<absolute path to that customer's agents repository>
SMARTKLIX_CONTROL_STATE_DIR=<private local state directory>
SMARTKLIX_JARVIS_CONTROL_ENABLED=true
SMARTKLIX_JARVIS_CONTROL_TOKEN=<random private value, 32+ characters>
```

The only platform-specific component is
`scripts/jarvis-research-control.ps1` in the existing agents repository. It uses
Windows process APIs because the installed Node dependencies are Windows-native.
The MCP policy and audit adapter remains portable Python and calls the Windows
adapter from the current WSL-hosted Hermes installation.

## Verified scope

The end-to-end smoke test exercised this exact path:

`jarvis-main MCP adapter -> WSL/Windows bridge -> supervised launcher -> health`

It verified stopped status, bounded start, idempotent replay, running status,
stop, and final stopped status. Both returned authority flags remained
`sendingEnabled=false` and `executionEnabled=false`.

The next SmartKlix control must be a separate, reviewed tool. Do not expand
these lifecycle methods into generic shell, HTTP, database, approval, or send
access.
