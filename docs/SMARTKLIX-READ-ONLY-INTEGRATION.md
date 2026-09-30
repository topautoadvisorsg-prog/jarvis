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

The production route is deployed and returns `503 JARVIS_READ_NOT_CONFIGURED`
without exposing data. A 64-character token has been generated in the protected
local Hermes environment; its value is not stored in Git or printed by the
preflight. The remaining action is to set that same value as
`JARVIS_SMARTKLIX_READ_TOKEN` in the linked Vercel project and redeploy/restart
the production function. The saved Vercel CLI identity on this computer is not
currently authorized for that team project.

## Activation

1. Confirm the deployed CRM route with the safe preflight below. The current
   production route is live and returns `JARVIS_READ_NOT_CONFIGURED`, proving
   deployment while refusing access until its secret exists.
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

Until the shared read token is configured, the tool returns that source as
unavailable rather than guessing or fabricating business data. The local
outreach source likewise reports unavailable when its approved local research
server is stopped.
