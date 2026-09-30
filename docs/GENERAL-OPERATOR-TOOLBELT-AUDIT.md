# `jarvis-main` general operator toolbelt audit

Date: 2026-09-25

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

The new `smartklix-operations` MCP server is enabled globally and exposes one
tool: `get_smartklix_operations`. Therefore the same default Hermes session used
by `jarvis-main` can discover it without a new profile or agent.

Some configured toolsets are not currently operational:

- Computer use: the official Windows `cua-driver` is installed and its health
  checks pass. `jarvis-main` is connected through a private bounded runtime and
  a deny-by-default manifest. App/window inventory and full-screen inspection
  are enabled. Mouse, keyboard, focus, launch, clipboard, recording, process,
  browser mutation, and file authority remain denied. See
  `JARVIS-COMPUTER-CONTROL.md`.
- Browser interaction: Hermes selects its Browser Use CLI backend and the CLI
  resolves, but a live read-only navigation smoke test failed because no
  supported Chromium-family browser was running. The web search/extract tools
  do work.
- Cron: enabled in configuration but absent from the current runtime tool list;
  its gateway requirements are not active in this process.
- Image generation: enabled in configuration but absent from the current
  runtime tool list because its provider requirements are not satisfied.
- Native Hermes STT is disabled. Jarvis already has its own working voice/STT
  pipeline, so enabling a duplicate STT tool is unnecessary.

Video analysis/generation, X search, Context Engine, Home Assistant, Spotify,
Yuanbao, and A2A are disabled and have no current business requirement.

## Personal email and calendar

Hermes already ships two possible email integrations, but neither is configured:

- `google-workspace`: Gmail, Calendar, Drive, Docs, Sheets, and Contacts through
  Google OAuth.
- `himalaya`: email through IMAP/SMTP, including Gmail App Password support.

No Google OAuth credential files and no relevant email/calendar environment
configuration were found. The current Google Workspace setup asks for Gmail
read, send, and modify scopes plus broad Calendar access when those services are
selected. It should not be connected as-is for an eyes-only phase. The safest
next email step is a read-only Gmail/Calendar connector or a narrowed version of
the existing Google skill. Sending and calendar mutations must remain separate,
approval-gated tools.

Personal email must never use the SmartKlix outreach rail. Business outreach
must continue through CRM review, human approval, and deterministic delivery.

## Approval policy

Hermes is currently in manual approval mode, with cron denied. Keep these
operations read-only without per-call approval: SmartKlix status reads, web
research, user-requested file reads, screen capture, window/app listing, and
future Gmail/Calendar reads.

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

Deploy the new read-only CRM route, provision the dedicated shared read token on
both sides, restart Jarvis/Hermes, and run a live query from `jarvis-main`. This
is the smallest step that changes the CRM source from `unavailable` to live.
Production deployment remains a Buddy-approved action.

After live SmartKlix read acceptance, validate the existing dedicated browser
mode, then connect a read-only personal email/calendar surface. Expand computer
control only for a named workflow and exact application; do not add global write
authority during those steps.
