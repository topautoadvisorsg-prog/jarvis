# SmartKlix live Jarvis acceptance — September 30, 2026

Status: **PASS — CRM AND SUPERVISED CLAUDE AGENTS VISIBLE TO `jarvis-main`.**

Durable cross-system restore markers and the final Buddy/engineering handoff are
recorded in `JARVIS-SMARTKLIX-CHECKPOINT-20260930.md`.

## Accepted architecture

```text
Buddy
  -> Jarvis / Hermes (`jarvis-main`)
     -> authenticated read-only SmartKlix CRM route on Vercel
     -> bounded lifecycle + read-only data from the Windows-local
        Smart Klix Claude Agents supervised console
```

The Claude Agents application does not need a public domain or cloud runtime for
this installation. It runs on the owner's Windows computer and binds to
`127.0.0.1:3001`. Hermes runs in WSL and reaches that Windows-only loopback
service through a GET-only PowerShell bridge. The bridge rejects non-loopback
HTTP targets and does not expose the service to the LAN or internet.

The historical Vercel proposal executor remains disabled and is not the current
Claude Agents runtime. The legacy autonomous worker bootstrap also remains
dormant.

## Live proof

- CRM deployment: Ready on Vercel.
- CRM authorization: unauthenticated HTTP 401; authenticated HTTP 200.
- MCP discovery: five `smartklix-operations` tools available.
- CRM source through `jarvis-main`: `available`.
- Claude Agents source through `jarvis-main`: `available`, no partial failures.
- Supervised console: running in `researchOnly` mode.
- Sending: disabled.
- Execution: disabled.
- Approval and spending authority: absent.
- STOP: console changed from running to stopped and the outreach source became
  unavailable.
- Restart: console returned to running and the outreach source returned to
  available.

The live natural-language `jarvis-main` check reported all three read sources
available and correctly distinguished the intentionally idle legacy workers from
the current supervised research console.

## Current saved work

- Saved research: 3 records.
- Pending operator review: 2.
- Rejected: 1.
- `80204 / hardwood flooring contractors`: research complete, one qualified
  saved prospect and one unsent draft.
- `80205 / hardwood flooring contractors`: next queued territory, not started.
- Sends performed by this acceptance: 0.
- CRM writes performed by this acceptance: 0.
- New prospect/model research performed by this acceptance: 0.

The retained Anthropic 401 activity belongs to a September 30 regression startup
of the dormant legacy pipeline. It is preserved audit history and is not a fault
in the running supervised path. The MCP payload now marks zero legacy workers as
`expected_idle` while `researchOnly` mode is active.

## Verification

- SmartKlix focused integration tests: 30 passed.
- Jarvis full regression suite: 195 passed.
- Python compile and Git whitespace checks: passed.
- Live `jarvis-main` read: passed after the WSL/Windows loopback and allowlisted
  MCP environment fixes.

## Remaining boundary

Jarvis can see the operation and can start or stop only the supervised local
console. It does not directly write research into the CRM. A selected result must
continue through the existing SmartKlix proposal, independent review, Buddy
approval and deterministic execution path. No send, execution or production
mutation authority was added in this milestone.

The smallest next business step is operator review of the two pending saved
research records. New model research should begin with one bounded candidate only
after provider credits are available and its cost and quality can be inspected.
