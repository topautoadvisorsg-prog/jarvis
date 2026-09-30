# `jarvis-main` general operator toolbelt audit

Date: 2026-09-30

## Architecture source of truth

`jarvis-main` is both Buddy's general AI operator and the Hermes Operations
Manager role for SmartKlix. There is no separate manager agent.

```text
Buddy
  -> Jarvis HUD / jarvis-main Hermes session
       -> existing Smart Klix Claude Agents (specialized research workers)
       -> existing SmartKlix CRM (business source of truth)
       -> other explicitly connected personal tools
```

The CRM reviewer, human approvals, and deterministic execution/delivery paths
remain authoritative. The read integration added in this checkpoint cannot
mutate any of them.

## Tools available now

The default Hermes configuration enables the core web, terminal, file, code,
vision, TTS, skills, memory, session-search, planning, delegation, browser,
computer-use, cron, and HUD toolsets. Runtime discovery confirmed the following
usable core surfaces: web search/extraction, terminal/processes, file read/write/
patch/search, code execution, vision, TTS, skills, memory, session search,
planning/clarification/delegation, and HUD display tools. A live `web_search`
smoke test passed.

The `smartklix-operations` MCP server is enabled globally and exposes five
tools: read-only operations status, deterministic attention previews, supervised
research-console status, and bounded start/stop controls for that console. The
same default Hermes session used by `jarvis-main` discovers them without a new
profile or manager agent. The controls cannot approve, send, execute CRM work,
or start the legacy autonomous scheduler.

Some configured toolsets are not currently operational:

- Computer use: the official Windows `cua-driver` is installed and its health
  checks pass. `jarvis-main` is connected through a private bounded runtime and
  a deny-by-default manifest. App/window inventory and full-screen inspection
  are enabled. Mouse, keyboard, focus, launch, clipboard, recording, process,
  browser mutation, and file authority remain denied. See
  `JARVIS-COMPUTER-CONTROL.md`.
- Browser interaction: the full browser bundle is configured, but its
  `agent-browser` runtime is not installed. It was deliberately left that way:
  the bundle exposes navigation, clicks, typing, keypresses, and JavaScript as
  one surface, and the current Hermes approval policy does not provide the
  workflow-specific boundary required before enabling those actions. Web
  search/extraction and bounded read-only screen inspection do work.
- Cron: enabled in configuration but absent from the current runtime tool list;
  its gateway requirements are not active in this process.
- Image generation: enabled in configuration but absent from the current
  runtime tool list because its provider requirements are not satisfied.
- Native Hermes STT is disabled. Jarvis already has its own working voice/STT
  pipeline, so enabling a duplicate STT tool is unnecessary.

Video analysis/generation, X search, Context Engine, Home Assistant, Spotify,
Yuanbao, and A2A are disabled and have no current business requirement.

## Personal email and calendar

Hermes ships two broad email integrations, but neither is configured:

- `google-workspace`: Gmail, Calendar, Drive, Docs, Sheets, and Contacts through
  Google OAuth.
- `himalaya`: email through IMAP/SMTP, including Gmail App Password support.

The broad Google Workspace setup asks for Gmail read, send, and modify scopes
plus broad Calendar access when those services are selected, so it was not used
for the eyes-only phase. A dedicated `personal-google-readonly` MCP server is now
installed and verified in the live Hermes runtime. It exposes exactly four
tools: connection status, Gmail search, one-message read, and primary-calendar
event listing. It accepts only the exact `gmail.readonly` and
`calendar.readonly` scope set and keeps its credentials separate. OAuth remains
pending Buddy setup; until then it reports `setup_required` and has no Google
data access. See `JARVIS-PERSONAL-GOOGLE-READONLY.md`.

Personal email must never use the SmartKlix outreach rail. Business outreach
must continue through CRM review, human approval, and deterministic delivery.

## Approval policy

Hermes is currently in manual approval mode, with cron denied. Keep these
operations read-only without per-call approval: SmartKlix status reads, web
research, user-requested file reads, screen capture, window/app listing, and
personal Gmail/Calendar reads.

Require Buddy approval for email/message sending, form submission, purchases or
spending, important deletion, public publishing, authentication/security
changes, production deployment, CRM approval/execution, outreach sends, and
calendar invitations. Computer-use clicks and typing should keep Hermes' native
manual approval boundary until narrower standing rules are explicitly created.

## Tools deliberately not added

- Direct CRM database write access.
- A broad SmartKlix admin token exposed as a general MCP/API tool.
- Direct SMTP or generic email sending for business outreach.
- Legacy scheduler, retry, executor, or delivery controls.
- Another reviewer, CRM, Kanban, outreach worker, or manager agent.
- Payment or purchasing tools.

## Next activation step

Finish the in-progress WhatsApp pairing and prove an allowlisted self-message
plus `jarvis-main` session continuity. Separately, Buddy can authorize the
prepared personal Google connector with a Desktop OAuth client when convenient.
Neither pending action blocks the other.

Do not install the broad browser runtime until a named workflow and explicit
action boundary are implemented. Expand computer control only for an exact
application and exact actions; do not add global write authority.
