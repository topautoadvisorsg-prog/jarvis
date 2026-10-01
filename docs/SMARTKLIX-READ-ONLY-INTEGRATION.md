# SmartKlix read-only operations integration

`jarvis-main` remains the Hermes Operations Manager role. This integration adds
the `get_smartklix_operations` snapshot and `get_smartklix_attention`
deterministic preview tools, with no additional agent or manager.

The tool reads three existing sources:

- SmartKlix CRM: authoritative leads, proposal/review state, sends, replies,
  intake, execution state, outcomes, and controls.
- Smart Klix Claude Agents: local workers, research activity, executions,
  analytics, and estimated model usage.
- Jarvis HUD: local cumulative LLM/TTS usage counters.

The operations and attention tools cannot start or pause work, deliver alerts,
approve, execute, send, spend, retry, or mutate anything. The attention policy
is documented in `JARVIS-SMARTKLIX-ATTENTION-ENGINE.md`. A separate bounded
console-lifecycle adapter is documented in
`JARVIS-SMARTKLIX-BOUNDED-CONTROL.md`. The CRM uses a dedicated
`JARVIS_SMARTKLIX_READ_TOKEN`; the MCP side
receives the same secret as `SMARTKLIX_JARVIS_READ_TOKEN`. URLs must use HTTPS,
except loopback HTTP for the local Claude Agents service.

## Current activation state

Activation passed on September 30, 2026. The production CRM route rejects an
unauthenticated request with HTTP 401 and returns HTTP 200 with the protected
read token. The supervised Windows Claude Agents console and the Vercel CRM both
return `available` through the live `jarvis-main` MCP tool. Sending, execution,
approval and spending remain disabled.

Hermes runs in WSL while the approved Claude Agents console binds only to Windows
loopback. The MCP adapter therefore uses a Windows PowerShell bridge for those
GET-only loopback reads. The URL is still restricted to loopback HTTP; no LAN or
public listener is opened. The MCP server loads only allowlisted SmartKlix
settings from the protected Hermes dotenv, so unrelated provider credentials do
not enter that subprocess. See `SMARTKLIX-LIVE-ACCEPTANCE-20260930.md`.

## Activation

1. Confirm the deployed CRM route with the safe preflight below.
2. Generate one random token of at least 32 characters.
3. Set `JARVIS_SMARTKLIX_READ_TOKEN` in the CRM deployment.
4. Set `SMARTKLIX_JARVIS_READ_TOKEN` in the private Hermes environment.
5. Keep `SMARTKLIX_CRM_BASE_URL=https://smartklixcrm.vercel.app` and
   `SMARTKLIX_OUTREACH_BASE_URL=http://127.0.0.1:3001` unless the authoritative
   services move.
6. Restart the Jarvis/Hermes service and verify the MCP server with
   `hermes mcp test smartklix-operations`.

The reusable preflight never changes production or prints the token:

```bash
python integrations/smartklix_crm_activation.py --env-file ~/.hermes/.env
```

It fails closed if the route is public, the tokens differ, the response grants
write authority, or the snapshot is unavailable. Exit code `0` means the CRM
connection is authenticated and read-only; exit code `2` means activation is
still pending.

If the shared read token is missing, the tool returns that source as unavailable
rather than guessing or fabricating business data. The local outreach source
likewise reports unavailable when its approved local research server is stopped.
