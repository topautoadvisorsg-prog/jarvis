# Jarvis + SmartKlix checkpoint — September 30, 2026

Status: **ACCEPTED LOCAL OPERATOR BASELINE**

This is the durable restore point for the first working connection between the
existing `jarvis-main` Hermes session, the Smart Klix Claude Agents supervised
local console, and the deployed SmartKlix CRM read route.

## Restore markers

| System | Accepted source | Git marker | Runtime state |
| --- | --- | --- | --- |
| Jarvis / Hermes integration | `codex/jarvis-live-openviking` | `jarvis-smartklix-live-accepted-2026-09-30` | Live `jarvis-main` read accepted |
| Smart Klix Claude Agents | `9086d88583cf73995ea0f1aa1d10ba796920af19` | `smartklix-agents-local-supervised-accepted-2026-09-30` | Windows loopback console; research only |
| SmartKlix CRM production source | `3025454c9c7ca3279ad28591a56ff4e693ec3ccd` | `smartklix-crm-jarvis-read-accepted-2026-09-30` | Vercel route authenticated and read only |

The tags are annotated and pushed to their corresponding GitHub repositories.
They preserve source state; private environment variables, Redis data, Neon data
and provider credentials remain outside Git and require the existing protected
backups and account access.

## Accepted behavior

- Buddy speaks or types to the existing `jarvis-main` session.
- Jarvis reads current CRM operational state from Vercel with the dedicated
  read-only token.
- Jarvis reads the Windows-local Claude Agents console through a private
  GET-only WSL/Windows loopback bridge.
- Jarvis can start or stop only the supervised research console with bounded,
  signed and idempotent lifecycle receipts.
- The local console forces research-only mode and disables sending and proposal
  execution.
- The existing CRM, Reviewer, Buddy approval and deterministic executor remain
  authoritative for consequential work.
- The dormant autonomous worker fleet and historical Vercel executor remain off.

No public Claude Agents domain, cloud worker deployment, Railway service, tunnel,
hosted Redis or duplicate manager/reviewer is required for this installation.

## Verification at checkpoint

### Jarvis

- Full regression suite: 195 passed.
- SmartKlix MCP: five tools discovered.
- Live `jarvis-main` natural-language report: CRM, outreach and Jarvis usage all
  available with no partial source failures.
- STOP made the outreach source unavailable; bounded restart restored it.
- Unauthenticated CRM request: HTTP 401.
- Authenticated CRM request: HTTP 200.

### Smart Klix Claude Agents

- `npx tsc --noEmit`: passed.
- `npm run ui:build`: passed; 1,942 modules transformed.
- Focused supervised-flow Vitest run: five files, 39 tests passed.
- Supervised UI: three saved companies, two pending operator review, one
  rejected.
- Sending and execution: disabled.

### SmartKlix CRM

- `npm run check`: passed.
- `npm run build:vercel`: passed.
- Jarvis operations route: seven tests passed.
- Production deployment: Ready.
- The build retains existing bundle and PostCSS warnings; neither failed the
  build. Address them only when working in those affected areas.

## Buddy actions

Nothing else is required to keep the accepted local connection working.

The next business decisions owned by Buddy are:

1. Review Rock Solid Hardwoods and Remodel Edge, the two saved pending research
   records. Approval to prepare a governed handoff is separate from permission to
   contact either business.
2. Add or select working model/provider credits before authorizing one new
   bounded research candidate. Existing saved research remains readable without
   credits.
3. Complete the room-level wake, sleep, STOP and barge-in voice test when the
   microphone/speaker environment is available.
4. Finish WhatsApp QR pairing and personal Google read-only OAuth only when those
   optional channels are wanted. Neither blocks SmartKlix operations.

No Claude Agents hosting purchase, domain, deployment account or public endpoint
is needed from Buddy.

## Engineering actions

The smallest next engineering package is a governed selected-result handoff:

1. Reuse the existing local `Export selected handoff` result.
2. Let Jarvis present the exact selected prospect, evidence and unsent draft.
3. Route the result into the existing CRM Proposal Agent and Independent Reviewer.
4. Keep Buddy's exact-version approval authoritative.
5. Let only the existing deterministic executor apply an approved change and
   record its receipt.

This package must not add direct CRM writes, send authority, a second reviewer,
another Kanban system or another manager agent. A first-class HUD business panel
can follow the accepted handoff contract; it should display live data rather than
decorative metrics.

The budget ledger remains a later accounting milestone, as directed. Until real
provider billing is reconciled, Jarvis must report known usage facts and label
cost or remaining budget as unknown.

## Current saved business state

- Rock Solid Hardwoods: pending review; source-backed email; unsent draft.
- Remodel Edge: pending review; targeting fit unresolved; unsent.
- Renovar Construction: rejected.
- `80204 / hardwood flooring contractors`: bounded source plan complete.
- `80205 / hardwood flooring contractors`: next queued territory, not started.
- Sends performed during activation and checkpoint: zero.
- CRM mutations performed during activation and checkpoint: zero.
- New paid/model research performed during activation and checkpoint: zero.

See `SMARTKLIX-LIVE-ACCEPTANCE-20260930.md` for the detailed live evidence and
`BUDDY-ACTION-CHECKLIST.md` for optional account-dependent tasks.
