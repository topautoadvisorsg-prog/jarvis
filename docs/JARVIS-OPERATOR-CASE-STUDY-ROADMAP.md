# Jarvis general operator roadmap

Date: 2026-09-30

Status: architecture plus implementation tracking. This document does not grant
new send, spend, call, approval, deployment, or computer-control authority.

## Decision

The case studies should extend the existing `jarvis-main` Hermes session. They
do not justify another agent framework, another operations-manager agent, or a
second CRM/workflow system.

The target remains:

```mermaid
flowchart LR
    B[Buddy] --> J[Jarvis HUD / Hermes jarvis-main]
    W[WhatsApp] --> J
    P[Approved phone escalation] --> J

    J --> PB[Policy and approval broker]
    PB --> S[SmartKlix read and bounded-control tools]
    PB --> G[Personal Google tools]
    PB --> C[Computer and browser tools]

    S --> A[Existing Claude Agents]
    S --> R[SmartKlix CRM source of truth]
    R --> V[Existing review and human approval]
    V --> E[Existing deterministic executor]

    R --> EV[Normalized operations events]
    A --> EV
    EV --> IR[Deterministic importance rules]
    IR --> J
```

Jarvis/Hermes holds the Operations Manager role. Existing agents remain the
workers. SmartKlix CRM remains the business source of truth. Existing review,
human approval, and deterministic execution remain authoritative.

## What exists today

### Jarvis/Hermes

- The HUD and voice bridge use the persistent `jarvis-main` session.
- The `smartklix-operations` MCP server exposes the read-only operations
  snapshot, a deterministic attention preview, and bounded supervised research
  console start/stop/status controls. Those controls cannot approve, send,
  execute CRM work, or start the legacy autonomous scheduler.
- Hermes v0.21.0 is installed locally. The upstream main branch has moved far
  beyond that release, so upgrading must be a separate compatibility project;
  this roadmap does not upgrade it.
- The installed Hermes version already includes WhatsApp, incoming WhatsApp
  voice transcription, WhatsApp TTS delivery, `/stop`, scheduled jobs, webhook
  inputs, HMAC verification, cross-platform session handoff, session search,
  memory, toolsets, and per-session model selection.
- The supported `/handoff whatsapp` flow can transfer the current session ID,
  transcript, and tool history to WhatsApp. The remote experience must bind to
  `jarvis-main` through that flow instead of silently creating a second Jarvis
  conversation.
- Approval mode is `manual`; cron authority is denied.
- The Hermes gateway is running and healthy. The WhatsApp pairing wizard is in
  progress; WhatsApp remains disabled until valid credentials are written. No
  cron jobs exist.
- The official Windows `cua-driver` is installed and passes Hermes doctor.
  `jarvis-main` can inspect the screen and list apps/windows through a
  deny-by-default bounded manifest. Clicks, typing, focus, launch, clipboard,
  recording, process control, browser mutation, and file authority are denied.
- A separate personal Google MCP server is installed and discovers four
  read-only Gmail/Calendar tools. OAuth remains pending, so it currently has no
  Google account access and reports `setup_required`.
- Local memory and FTS5 `session_search` already cover conversational recall.
  They should be used before adding a vector-memory product.

### SmartKlix CRM

- `GET /api/jarvis/operations` is implemented as a dedicated authenticated,
  read-only snapshot route.
- The route includes leads, research-relevant CRM state, drafts/proposals,
  approvals, sends, replies, failures, calls/intake, meetings, revenue, and
  safety-control status where the underlying records exist.
- The production route is deployed and fails closed with
  `JARVIS_READ_NOT_CONFIGURED`. Matching private read-token configuration in
  Vercel is the remaining activation step; the protected local Hermes token is
  prepared. The currently cached Vercel CLI identity cannot access the linked
  team project, so that production setting requires an authorized Vercel
  login/team member.
- Retell inbound receptionist intake already exists with signed webhook
  verification, idempotent receipts, bounded recovery, retained failures, and
  manual review boundaries.
- Retell currently has no general CRM lookup or booking authority. Appointment
  requests remain intake for a human-controlled Calendar action.
- SmartKlix contains outbox/audit/event evidence that can feed Jarvis. We should
  add an adapter over these records, not replace them with a new event store.

### Existing outreach workers

The authoritative repository is
`C:\Users\jovan\Downloads\smart klix claude agents`, branch
`fix/vercel-first-runtime`, current commit `5cddf1e`. It contains the existing
bounded Hermes researcher, source-backed qualification, unsent drafting, Redis
identity/territory records, operator review UI, execution receipts, and the
trusted handoff boundary toward CRM.

The approved supervised startup is `npx tsx scripts/local-research.ts`, which
serves the loopback application on port 3001. `npm start` invokes the retained
legacy autonomous bootstrap and is not an approved startup path. Outbound
delivery remains off.

The Jarvis read adapter targets the existing GET surfaces for metrics, workers,
activity, usage, executions, research, and territory work. The loopback service
is not running or reachable at the time of this audit. Jarvis must continue
reporting that source as unavailable rather than estimating activity.

### Telemetry gaps

No authoritative ledger currently joins all of the following by Buddy objective:

- budget allocated, reserved, spent, and remaining;
- provider-billed model cost;
- research/enrichment cost per prospect;
- STT, TTS, phone, and delivery cost;
- durable worker and end-to-end runtime;
- cost adjustments or late provider reconciliation.

Local token counts and provider-specific records are evidence inputs, but they
are not yet one reconciled business budget.

## Repository and package decisions

| Capability | Decision | Reason |
| --- | --- | --- |
| Core agent, WhatsApp, cron, webhooks, memory | Keep `NousResearch/hermes-agent` already installed | These are native features. A new orchestration repo would duplicate the runtime and split `jarvis-main`. |
| Jarvis HUD | Keep this repository | It already owns the approved HUD, voice, STOP/barge-in, approvals, tool visualization, and SmartKlix read bridge. |
| SmartKlix operations | Keep the CRM and existing Claude Agents repositories | They own business state, worker execution, review, and delivery. |
| Windows computer control | Use Hermes's built-in adapter with official `trycua/cua` `cua-driver` | It supports Windows screenshots, accessibility trees, background actions, bounded capability manifests, and explicit failures. Install the released driver; do not fork or embed the whole Cua repo. |
| Phone calls | Reuse the existing Retell/Twilio boundary | SmartKlix already receives Retell calls safely. For future owner calls, use Retell's official SDK/API through a narrow server tool. Do not enable the broad Retell MCP or direct model access to arbitrary phone calls. |
| Gmail and Calendar | Use Google's official APIs behind narrow local tools | Hermes has a Google Workspace skill, but the current generic setup asks for broader scopes than this rollout needs. Begin with Calendar free/busy/events-read and Gmail metadata/read-only as separately authorized tools. |
| Alerts | Use SmartKlix events/outbox plus Hermes signed webhooks and WhatsApp delivery | This is already sufficient. A general event-orchestration platform would add another control plane. |
| Model routing | Use Hermes provider/model overrides and a small policy table | Easy scheduled/background work can pin a cheap model. Keep the live operator model replaceable. Do not add another visible agent. |
| Second brain | Pilot Hermes's native OpenViking provider against curated SmartKlix/Jarvis documents | OpenViking matches the desired file-hierarchy, tiered-loading, semantic-retrieval experience without replacing Hermes. Keep FTS5 session search and built-in memory alongside it. |

No additional orchestration repository is needed. OpenViking and `cua-driver`
were installed only for their bounded evaluation stages described below; neither
creates another agent layer or changes SmartKlix's authority boundaries.

## Event and interruption design

Every event entering Jarvis should use one small normalized envelope:

```json
{
  "eventId": "source-stable-id",
  "occurredAt": "2026-09-28T12:00:00Z",
  "source": "smartklix-crm",
  "type": "approval.blocking",
  "subject": { "type": "proposal", "id": "..." },
  "facts": {},
  "severity": "attention",
  "requiresBuddy": true,
  "dedupeKey": "approval:proposal-id",
  "evidenceUrl": null
}
```

Classification should be deterministic first:

| Severity | Examples | Delivery |
| --- | --- | --- |
| `info` | research completed, routine send receipt | store for status summaries; no interruption |
| `attention` | approval waiting, qualified reply, recoverable worker failure | WhatsApp/HUD during allowed hours, deduped |
| `urgent` | repeated system failure, signed deal, payment, explicit urgent customer issue | immediate WhatsApp; phone escalation only under a later standing rule |

The rule engine must support deduplication, cooldowns, quiet hours, acknowledgement,
and escalation timeout. It should not ask an LLM to classify every routine event.
An inexpensive classifier may resolve ambiguous text only after deterministic
rules fail, and its output cannot grant execution authority.

## How real the second brain is

Three memory layers already exist, but they solve different problems:

| Layer | What is real today | Limit |
| --- | --- | --- |
| Built-in memory | Compact stable facts in `MEMORY.md` and `USER.md`, injected into each turn | Intentionally small; not a document library |
| Session search | FTS5 search over actual Hermes messages and tool history | Keyword/full-text retrieval, not broad semantic document search |
| Project context | Progressive loading of `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, and related project instructions | Loads selected context files; it does not index every project document automatically |

OpenViking is the closest match to the demonstrated file-distribution idea. The
Hermes integration is already bundled as a memory provider. OpenViking adds:

- a `viking://` hierarchy for resources, memories, and skills;
- semantic search plus visible file/tree navigation;
- L0 abstracts, L1 overviews, and L2 full content loaded on demand;
- URL and document ingestion;
- automatic memory extraction when a session is committed;
- retrieval traces that can be inspected when the wrong file is selected.

That capability is real, but it is not magic. It requires a separate OpenViking
server, embedding/model configuration, an ingestion manifest, refresh rules,
access boundaries, backups, and measured retrieval tests. It must not crawl the
whole computer. Credentials, `.env` files, raw customer exports, private mailbox
content, database dumps, generated dependencies, and archived evidence stay out
of the index unless a later policy explicitly admits a narrow source.

The completed pilot ingested only reviewed architecture, product, operating,
and project documents from Jarvis, Smart Klix Claude Agents, and SmartKlix CRM.
It compared OpenViking with ordinary repository search on a fixed 20-question
set. OpenViking did not beat the baseline, so its local service and Studio remain
available for inspection while the Hermes provider stays disabled. See
`JARVIS-SECOND-BRAIN-IMPLEMENTATION.md`.

OpenViking is AGPL-3.0. Internal evaluation can proceed in isolation; any future
customer packaging or hosted offering needs an explicit licensing and source-
distribution review before it becomes part of the commercial product.

## Permission boundary

| Action | Initial policy |
| --- | --- |
| Read operations, search history, calculate summaries | autonomous |
| Read Gmail/Calendar after account authorization | autonomous within the explicit read scope |
| Draft a personal email or calendar change | prepare and show Buddy |
| Send personal email, create/update calendar event | explicit approval until a narrower standing rule exists |
| Start/pause bounded existing outreach workflow | disabled until the read-only milestone is accepted, then policy-token controlled |
| Business outreach send | only through existing CRM review/approval/executor |
| Outbound phone call | disabled; later explicit recipient/purpose/budget authorization |
| Computer click/type | bounded manifest; sensitive or consequential actions require approval |
| Purchase, payment, production deploy, deletion, auth/security change | explicit approval |

## Implementation order

### Milestone 0 - activate and verify the existing eyes

**Partially complete.** The adapters, source labels, failure reporting, tests,
and production route deployment are complete. The remaining blocker is matching
private-token configuration followed by live authenticated acceptance. The safe
preflight reports the current state without changing production or printing the
secret.

1. Confirm the deployed SmartKlix read-only route with the safe preflight.
2. Configure matching 32+ character CRM/Jarvis read tokens without exposing them
   to the browser or source control.
3. Build the existing outreach UI, start Redis and the approved supervised
   `scripts/local-research.ts` server, then verify every expected read endpoint.
4. Run live read-only questions through `jarvis-main` and confirm that CRM,
   worker, and Jarvis usage data are labeled by source and time window.
5. Add no write tool.

Acceptance: Buddy can ask the agreed operations questions and each answer either
cites current authoritative data or explicitly names the unavailable source.

### Milestone 1 - controlled second-brain pilot

**Completed but not adopted (2026-09-29).** The isolated OpenViking service,
allowlisted manifest, indexed corpus, deletion/no-op checks, and fixed retrieval
evaluation are complete. The provider remains disabled because OpenViking found
the expected source in the top three for 7/20 questions versus 17/20 for the
repository-search baseline.

Run OpenViking as a separate local service and connect it through Hermes's
bundled provider. Create a reviewed ingestion manifest for a small set of Jarvis,
Smart Klix Claude Agents, and SmartKlix CRM documents. Exclude secrets, customer
records, generated files, dependencies, and archives. Evaluate a fixed set of
cross-project questions against file search, session search, and OpenViking.

Acceptance: the provider returns source-identifiable answers, the filesystem
hierarchy is inspectable, stale/deleted documents are handled correctly, and it
beats existing retrieval enough to justify another local service.

### Milestone 2 - bounded SmartKlix hands

**First bounded control complete (2026-09-30).** Jarvis can inspect, start, and
stop only the supervised local research console with enable flags, a private
control token, idempotency, time bounds, a watchdog, and signed local receipts.
End-to-end start/replay/status/stop acceptance passed with sending and execution
disabled. See `JARVIS-SMARTKLIX-BOUNDED-CONTROL.md`.

Create separate narrow tools for specific existing controls such as pause an
objective, resume an already-approved objective, or start a bounded existing
workflow. Use idempotency keys, objective limits, audit receipts, and
server-side authorization. Do not expose generic HTTP, SQL, approval, or send.

Acceptance: every command is attributable, repeat-safe, within limits, visible
in CRM/audit history, and rejected when authority or an objective limit is absent.

### Milestone 3 - WhatsApp remote access to the same Jarvis

Current status (2026-09-30): the bundled bridge dependencies are installed and
its 22 tests pass. A locked-down local configuration is prepared with WhatsApp
disabled until pairing, DM allowlisting, groups disabled, and allow-all off.
The remaining first-proof step is Buddy's interactive QR pairing, followed by
the `jarvis-main` handoff and acceptance checks documented in
`JARVIS-WHATSAPP-ROLLOUT.md`.

Use Hermes's existing WhatsApp integration; do not add a separate messaging
agent. For a quick internal proof, the Baileys bridge can link an existing
WhatsApp account without a Meta developer application, but it is unofficial,
holds powerful linked-device credentials, and carries account-restriction risk.
The durable business path is WhatsApp Cloud API on a dedicated business number,
which requires Meta setup and a public signed webhook.

Whichever path is chosen, allowlist only Buddy, silently ignore unauthorized
DMs, resume the actual `jarvis-main` session, and use `/handoff whatsapp`. Start
with read-only SmartKlix tools. Verify voice-note transcription, text replies,
TTS voice reply, `/stop`, restart persistence, and handoff back to the HUD/CLI.

Acceptance: the session ID and remembered context survive the handoff; an
unauthorized WhatsApp account cannot interact with the bot; no bulk or customer
messaging authority is enabled.

### Milestone 4 - proactive alerts

Current status (2026-09-30): deterministic event normalization plus local
dedupe, cooldown, quiet-hour policy, persistent first/last-seen observation,
two-hour escalation, resolution/reopen behavior, and a deterministic Buddy
handoff queue are implemented behind the read-only `get_smartklix_attention`
MCP tool. External delivery and agent-accessible acknowledgement remain disabled
until their separate acceptance steps. See `JARVIS-SMARTKLIX-ATTENTION-ENGINE.md`.

Expose a signed SmartKlix event adapter to Hermes webhooks. Implement the
deterministic severity policy, dedupe/cooldown ledger, quiet hours, and WhatsApp
delivery. Begin with synthetic events, then supervised real read-only events.

Acceptance: routine events remain quiet; duplicate events do not cause duplicate
alerts; urgent synthetic events reach Buddy once with evidence and a clear next
decision; no event can bypass CRM approval/execution.

### Milestone 5 - Calendar and personal Gmail

**Prepared, pending Buddy OAuth (2026-09-30).** A separate MCP connector now
exposes only personal Gmail search/read and primary-calendar event reads. It uses
its own credential directory and requires exactly `gmail.readonly` plus
`calendar.readonly`; broader or mismatched tokens fail closed. The live server
can be enabled before authorization and reports setup required without starting
OAuth. See `JARVIS-PERSONAL-GOOGLE-READONLY.md`.

Sending, labeling, deletion, event creation/modification, Drive, Contacts,
Sheets, and Docs remain absent. Business outreach email never uses this path.

### Milestone 6 - owner phone escalation and background continuation

Add a narrow Retell call tool for Buddy's verified number only, with a daily
cost cap, allowed reasons, quiet hours, explicit call receipts, STOP, and signed
post-call events. Convert the spoken decision into a pending audited action and
continue through the same policy broker after the call ends.

Do not reuse the public receptionist agent as the owner-operations agent. Reuse
the provider and signed webhook infrastructure, with a separately scoped Retell
agent/configuration.

### Milestone 7 - computer and screen control

**Implemented first stage (2026-09-30).** The official released `cua-driver` is
installed on Windows and its doctor passes. Hermes uses a private bounded runtime
through the WSL/Windows adapter with a version-3 deny-by-default manifest.
`jarvis-main` may list apps/windows and inspect the primary screen; mouse,
keyboard, focus, app launch, clipboard, browser mutation, recording, process,
and file actions are excluded. See `JARVIS-COMPUTER-CONTROL.md`.

The next expansion must be a separate workflow-specific manifest naming exact
approved non-browser applications and actions. Prefer APIs and dedicated tools
whenever available.

### Milestone 8 - reflex and model routing

**Observability first stage complete (2026-09-30).** The HUD now shows the
configured Hermes provider/model plus privacy-safe recent success and latency
aggregates. A minimal live turn proved the current DeepSeek route and recorded
the resolved model, tokens, estimated cost, and wall time. No automatic selector
or second agent was added. See `JARVIS-OPERATIONAL-TELEMETRY.md`.

Measure latency and cost first. Use deterministic routing for domain/tool/approval
decisions. Pin cheap models for scheduled summaries and bounded classifications;
retain the selected main model for complex operator reasoning. Voice endpointing
belongs in the audio pipeline, not in a second agent.

### Milestone 9 - objective and budget ledger

Defer the combined ledger until provider choices and real prices are stable
enough to model. When that evidence exists, add a small append-only ledger tied
to a Buddy objective. Store allocations, reservations, provider usage evidence,
reconciled charges, runtime, and remaining budget. The ledger references existing
run/task/lead IDs and does not own leads, proposals, approvals, or execution.

Acceptance: `allocated = available + reserved + spent` can be reconciled, late
provider charges are adjustments rather than rewrites, and work stops before a
hard limit is exceeded. Until then, report available usage facts and label cost
or remaining budget as unknown.

### Later bucket

Focus/accountability mode, camera input, gesture control, and holographic display
work remain later features after the operator loop is reliable and measurable.

## Current activation package

The remaining Milestone 0 deliverable is a live, read-only operations acceptance
report covering:

- CRM authentication with the already-deployed route;
- local outreach endpoint health;
- Jarvis MCP discovery from `jarvis-main`;
- answers for current work, attention, leads, drafts, approvals, sends, replies,
  failures, worker status, and one lead lookup;
- existing usage facts labeled honestly, with cost/runtime gaps left for the
  final accounting milestone;
- regression tests for the HUD, voice, STOP, approvals, and SmartKlix snapshot.

The local second-brain evaluation, alert preview, bounded research-console
control, read-only computer vision, and personal Google connector preparation
are already complete. None of them replaces the remaining live CRM acceptance.
WhatsApp pairing and personal Google OAuth are independent pending activation
steps owned by Buddy's accounts. These and the SmartKlix Vercel authorization
are tracked in `BUDDY-ACTION-CHECKLIST.md` so engineering can continue without
losing the account-dependent work.

## Risks to carry forward

1. **Hermes upgrade delta.** The installed v0.21.0 checkout is materially behind
   upstream main. Do not mix an upgrade into an integration milestone. Audit and
   test a tagged release in isolation when an upgrade is approved.
2. **Session split.** A new WhatsApp conversation is not automatically
   `jarvis-main`. Use the supported handoff and verify the actual session ID.
3. **False budget confidence.** Token counts are not provider-billed cost. Do not
   report a remaining budget until the ledger reconciles real charges.
4. **Inbound versus outbound phone authority.** Existing Retell intake proves a
   safe inbound path. It does not authorize outbound calling.
5. **OAuth scope expansion.** Gmail read/compose scopes are sensitive or
   restricted. Separate internal-use setup from any future customer product and
   plan verification/security requirements before commercialization.
6. **Computer-use fallbacks.** Windows background control is best effort; some
   apps require foreground input. Every consequential action still needs
   independent policy checks and post-action verification.
7. **Dormant outreach bootstrap.** `npm start` in Smart Klix Claude Agents is a
   legacy autonomous path. Jarvis setup must use the documented supervised
   server and must not activate that scheduler as a shortcut.
8. **WhatsApp transport choice.** The personal-account bridge is convenient but
   unofficial and powerful. WhatsApp Cloud is official but needs a dedicated
   business number, Meta configuration, a public webhook, and template rules.
   Do not hide this tradeoff behind a generic "WhatsApp enabled" checkbox.
9. **Knowledge indexing boundary.** A second brain can leak secrets or stale
   business facts if ingestion is broad or deletion is incomplete. Use an
   allowlisted manifest and keep CRM live facts in CRM.

## Research references

- Hermes Agent repository and supported platforms:
  <https://github.com/NousResearch/hermes-agent>
- Hermes scheduled jobs and event-triggered runs:
  <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md>
- Hermes WhatsApp gateway and voice messages:
  <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/whatsapp.md>
- Hermes WhatsApp Business Cloud API adapter:
  <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/whatsapp-cloud.md>
- Hermes memory providers:
  <https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/>
- OpenViking repository:
  <https://github.com/volcengine/OpenViking>
- Cua Driver repository and Windows support:
  <https://github.com/trycua/cua>
- Retell official Python SDK:
  <https://github.com/RetellAI/retell-python-sdk>
- Retell phone-call API:
  <https://docs.retellai.com/api-references/create-phone-call>
- Google Calendar OAuth scopes:
  <https://developers.google.com/workspace/calendar/api/auth>
- Gmail OAuth scopes:
  <https://developers.google.com/workspace/gmail/api/auth/scopes>
