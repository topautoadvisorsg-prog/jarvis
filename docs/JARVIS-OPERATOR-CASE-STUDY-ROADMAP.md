# Jarvis general operator roadmap

Date: 2026-09-28

Status: architecture and implementation order only. This document does not grant
new send, spend, call, approval, deployment, or computer-control authority.

## Decision

The case studies should extend the existing `jarvis-main` Hermes session. They
do not justify another agent framework, another operations-manager agent, or a
second CRM/workflow system.

The target remains:

```mermaid
flowchart LR
    B[Buddy] --> J[Jarvis HUD / Hermes jarvis-main]
    T[Telegram] --> J
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
- The read-only `get_smartklix_operations` MCP tool is implemented and exposes
  no write, approval, send, execution, or spend method.
- Hermes v0.21.0 is installed locally. The upstream main branch has moved far
  beyond that release, so upgrading must be a separate compatibility project;
  this roadmap does not upgrade it.
- The installed Hermes version already includes Telegram, incoming Telegram
  voice transcription, Telegram TTS delivery, `/stop`, scheduled jobs, webhook
  inputs, HMAC verification, cross-platform session handoff, session search,
  memory, toolsets, and per-session model selection.
- The supported `/handoff telegram` flow can transfer the current session ID,
  transcript, and tool history to Telegram. The remote experience must bind to
  `jarvis-main` through that flow instead of silently creating a second Jarvis
  conversation.
- Approval mode is `manual`; cron authority is denied.
- The Hermes gateway is currently stopped. Telegram and webhook credentials are
  not configured. No cron jobs exist.
- Computer Use is present as a Hermes tool, but `cua-driver` is not installed on
  either Windows or WSL. It is therefore unavailable today.
- Local memory and FTS5 `session_search` already cover conversational recall.
  They should be used before adding a vector-memory product.

### SmartKlix CRM

- `GET /api/jarvis/operations` is implemented as a dedicated authenticated,
  read-only snapshot route.
- The route includes leads, research-relevant CRM state, drafts/proposals,
  approvals, sends, replies, failures, calls/intake, meetings, revenue, and
  safety-control status where the underlying records exist.
- The production route still needs deployment and matching read-token
  configuration before Jarvis has live CRM visibility.
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
| Core agent, Telegram, cron, webhooks, memory | Keep `NousResearch/hermes-agent` already installed | These are native features. A new orchestration repo would duplicate the runtime and split `jarvis-main`. |
| Jarvis HUD | Keep this repository | It already owns the approved HUD, voice, STOP/barge-in, approvals, tool visualization, and SmartKlix read bridge. |
| SmartKlix operations | Keep the CRM and existing Claude Agents repositories | They own business state, worker execution, review, and delivery. |
| Windows computer control | Use Hermes's built-in adapter with official `trycua/cua` `cua-driver` | It supports Windows screenshots, accessibility trees, background actions, bounded capability manifests, and explicit failures. Install the released driver; do not fork or embed the whole Cua repo. |
| Phone calls | Reuse the existing Retell/Twilio boundary | SmartKlix already receives Retell calls safely. For future owner calls, use Retell's official SDK/API through a narrow server tool. Do not enable the broad Retell MCP or direct model access to arbitrary phone calls. |
| Gmail and Calendar | Use Google's official APIs behind narrow local tools | Hermes has a Google Workspace skill, but the current generic setup asks for broader scopes than this rollout needs. Begin with Calendar free/busy/events-read and Gmail metadata/read-only as separately authorized tools. |
| Alerts | Use SmartKlix events/outbox plus Hermes signed webhooks and Telegram delivery | This is already sufficient. A general event-orchestration platform would add another control plane. |
| Model routing | Use Hermes provider/model overrides and a small policy table | Easy scheduled/background work can pin a cheap model. Keep the live operator model replaceable. Do not add another visible agent. |
| Second brain | Use Hermes memory, FTS5 session search, and project context first | Add semantic/vector retrieval only after a measured retrieval failure on actual SmartKlix/project documents. Do not pull Mem0, Zep, or LlamaIndex preemptively. |

No outside repository should be cloned for the first four milestones. The first
new binary worth installing is `cua-driver`, and only when the computer-control
milestone begins.

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
| `attention` | approval waiting, qualified reply, recoverable worker failure | Telegram/HUD during allowed hours, deduped |
| `urgent` | budget exhausted, repeated system failure, signed deal, payment, explicit urgent customer issue | immediate Telegram; phone escalation only under a later standing rule |

The rule engine must support deduplication, cooldowns, quiet hours, acknowledgement,
and escalation timeout. It should not ask an LLM to classify every routine event.
An inexpensive classifier may resolve ambiguous text only after deterministic
rules fail, and its output cannot grant execution authority.

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

1. Deploy the existing SmartKlix read-only route.
2. Configure matching 32+ character CRM/Jarvis read tokens without exposing them
   to the browser or source control.
3. Build the existing outreach UI, start Redis and the approved supervised
   `scripts/local-research.ts` server, then verify every expected read endpoint.
4. Run live read-only questions through `jarvis-main` and confirm that CRM,
   worker, and Jarvis usage data are labeled by source and time window.
5. Add no write tool.

Acceptance: Buddy can ask the agreed operations questions and each answer either
cites current authoritative data or explicitly names the unavailable source.

### Milestone 1 - objective and budget ledger

Add a small append-only ledger tied to a Buddy objective. Store allocations,
reservations, provider usage evidence, reconciled charges, runtime, and remaining
budget. The ledger references existing run/task/lead IDs and does not own leads,
proposals, approvals, or execution.

Acceptance: `allocated = available + reserved + spent` can be reconciled, late
provider charges are adjustments rather than rewrites, and work stops before a
hard limit is exceeded.

### Milestone 2 - Telegram remote access to the same Jarvis

Configure one allowlisted Buddy account, establish the home channel, resume the
actual `jarvis-main` session, and use `/handoff telegram`. Start with read-only
SmartKlix tools. Verify voice-note transcription, text replies, TTS voice reply,
`/stop`, restart persistence, and handoff back to the HUD/CLI.

Acceptance: the session ID and remembered context survive the handoff; an
unauthorized Telegram account cannot interact with the bot.

### Milestone 3 - proactive alerts

Expose a signed SmartKlix event adapter to Hermes webhooks. Implement the
deterministic severity policy, dedupe/cooldown ledger, quiet hours, and Telegram
delivery. Begin with synthetic events, then supervised real read-only events.

Acceptance: routine events remain quiet; duplicate events do not cause duplicate
alerts; urgent synthetic events reach Buddy once with evidence and a clear next
decision; no event can bypass CRM approval/execution.

### Milestone 4 - bounded SmartKlix hands

Create separate narrow tools for specific existing controls such as pause an
objective, resume an already-approved objective, or start a bounded existing
workflow. Use idempotency keys, objective/budget limits, audit receipts, and
server-side authorization. Do not expose generic HTTP, SQL, approval, or send.

Acceptance: every command is attributable, repeat-safe, within limits, visible
in CRM/audit history, and rejected when authority or budget is absent.

### Milestone 5 - Calendar and personal Gmail

Add separate OAuth clients/scopes and separate read/write tools. Calendar starts
with free/busy or event-read access. Gmail starts with the least access that
supports the accepted use case. Sending and event creation remain approval-gated.
Business outreach email never uses this path.

### Milestone 6 - owner phone escalation and background continuation

Add a narrow Retell call tool for Buddy's verified number only, with a daily
cost cap, allowed reasons, quiet hours, explicit call receipts, STOP, and signed
post-call events. Convert the spoken decision into a pending audited action and
continue through the same policy broker after the call ends.

Do not reuse the public receptionist agent as the owner-operations agent. Reuse
the provider and signed webhook infrastructure, with a separately scoped Retell
agent/configuration.

### Milestone 7 - computer and screen control

Install the official released `cua-driver` on Windows, run `doctor`, and connect
Hermes's existing `computer_use` tool. Start with read-only window inventory and
screen inspection, then a bounded capability manifest for approved apps/actions.
Prefer APIs and dedicated tools whenever available.

### Milestone 8 - reflex and model routing

Measure latency and cost first. Use deterministic routing for domain/tool/approval
decisions. Pin cheap models for scheduled summaries and bounded classifications;
retain the selected main model for complex operator reasoning. Voice endpointing
belongs in the audio pipeline, not in a second agent.

### Milestone 9 - retrieval expansion

Index project documents only after defining ownership, freshness, deletion, and
access rules. Evaluate semantic retrieval against real questions. Keep CRM facts
in CRM and conversation facts in Hermes rather than copying everything into a
new memory database.

### Later bucket

Focus/accountability mode, camera input, gesture control, and holographic display
work remain later features after the operator loop is reliable and measurable.

## First implementation package

The next code task should be only Milestone 0. Its deliverable is a live,
read-only operations acceptance report covering:

- CRM route deployment and authentication;
- local outreach endpoint health;
- Jarvis MCP discovery from `jarvis-main`;
- answers for current work, attention, leads, drafts, approvals, sends, replies,
  failures, spend telemetry, runtime telemetry, and one lead lookup;
- explicit gaps where cost/runtime cannot yet be proved;
- regression tests for the HUD, voice, STOP, approvals, and SmartKlix snapshot.

Only after that report passes should implementation move to the ledger and
Telegram handoff.

## Risks to carry forward

1. **Hermes upgrade delta.** The installed v0.21.0 checkout is materially behind
   upstream main. Do not mix an upgrade into an integration milestone. Audit and
   test a tagged release in isolation when an upgrade is approved.
2. **Session split.** A new Telegram conversation is not automatically
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

## Research references

- Hermes Agent repository and supported platforms:
  <https://github.com/NousResearch/hermes-agent>
- Hermes scheduled jobs and event-triggered runs:
  <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md>
- Hermes Telegram gateway and voice messages:
  <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/telegram.md>
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
