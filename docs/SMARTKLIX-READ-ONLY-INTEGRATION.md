# SmartKlix read-only operations integration

`jarvis-main` remains the Hermes Operations Manager role. This integration adds
one MCP tool, `get_smartklix_operations`, and no additional agent or manager.

The tool reads three existing sources:

- SmartKlix CRM: authoritative leads, proposal/review state, sends, replies,
  intake, execution state, outcomes, and controls.
- Smart Klix Claude Agents: local workers, research activity, executions,
  analytics, and estimated model usage.
- Jarvis HUD: local cumulative LLM/TTS usage counters.

It cannot start or pause work, approve, execute, send, spend, retry, or mutate
anything. The CRM uses a dedicated `JARVIS_SMARTKLIX_READ_TOKEN`; the MCP side
receives the same secret as `SMARTKLIX_JARVIS_READ_TOKEN`. URLs must use HTTPS,
except loopback HTTP for the local Claude Agents service.

## Activation

1. Deploy the CRM route from the matching SmartKlix CRM change.
2. Generate one random token of at least 32 characters.
3. Set `JARVIS_SMARTKLIX_READ_TOKEN` in the CRM deployment.
4. Set `SMARTKLIX_JARVIS_READ_TOKEN` in the private Hermes environment.
5. Keep `SMARTKLIX_CRM_BASE_URL=https://smartklixcrm.vercel.app` and
   `SMARTKLIX_OUTREACH_BASE_URL=http://127.0.0.1:3001` unless the authoritative
   services move.
6. Restart the Jarvis/Hermes service and verify the MCP server with
   `hermes mcp test smartklix-operations`.

Until the CRM route is deployed and the shared read token is configured, the
tool returns that source as unavailable rather than guessing or fabricating
business data. The local outreach source likewise reports unavailable when its
approved local research server is stopped.
