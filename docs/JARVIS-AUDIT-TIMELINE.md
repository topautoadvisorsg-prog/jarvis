# Jarvis local audit timeline

Date: 2026-09-30

## Decision

Jarvis now keeps a small append-only operational audit for its existing Hermes
turn path. This is observability for the same `jarvis-main` manager; it is not a
second agent, workflow engine, CRM, or source of business truth.

The existing HUD activity panel is the read surface. It reloads the newest
records from `GET /api/audit` every five seconds, so recent history survives a
browser refresh or reconnect.

## Recorded lifecycle

- accepted typed, voice, delegated, or HTTP request;
- Hermes run start with provider/model labels;
- tool start and the bounded input preview supplied by Hermes;
- tool completion and bounded output preview when Hermes emits a completion
  event;
- approval requested and Buddy's allow/deny decision;
- cancellation requested and turn cancelled;
- final result or failure.

Records carry correlation fields such as turn, run, conversation, tool, and
approval request identifiers when available.

## Storage and privacy boundary

Records are written locally to `server/logs/audit.jsonl`. The active file
rotates at 5 MiB to one local predecessor. Audit failure is fail-soft and never
blocks or changes an agent turn.

All values are bounded before writing. Credential-shaped field names such as
API keys, passwords, tokens, authorization headers, cookies, and credentials
are replaced with `[REDACTED]`. Secret-shaped values inside request, tool,
result, and error previews are also removed. Previews are capped at 500
characters and nested structures are depth/item limited.

The `/api/audit` route is read-only, returns at most 100 newest-first records,
and inherits the existing `/api/*` HUD authentication middleware. The browser
renders every row through `textContent`; audit text is never inserted as HTML.

## Deliberate limits

- This is a local operator record, not a compliance archive or billing ledger.
- It does not copy SmartKlix CRM history. CRM approvals, sends, replies, and
  business outcomes remain authoritative in SmartKlix.
- Tool output is recorded only when the installed Hermes build emits
  `tool.completed`, `tool.finished`, or `tool.result`; absence is not invented.
- Full prompts, complete tool payloads, and complete responses are intentionally
  excluded. The timeline is for attribution and diagnosis, not conversation
  reconstruction.

## Verification

Automated coverage proves credential redaction before disk write, malformed-row
recovery, newest-first bounded reads, inherited API authentication, Hermes tool
completion parsing, and the HUD's durable timeline wiring.
