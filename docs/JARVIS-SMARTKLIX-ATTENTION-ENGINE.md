# Jarvis SmartKlix attention engine

Date: 2026-09-30

Status: deterministic read-only preview implemented; external delivery is
disabled until WhatsApp is paired and live source data is verified.

## Purpose

Jarvis needs to distinguish routine operational activity from facts that need
Buddy's attention. This implementation derives normalized events from the
existing `get_smartklix_operations` snapshot. It does not add an agent, use an
LLM for classification, or create another event database.

The `get_smartklix_attention` MCP tool currently recognizes:

- CRM visibility failures;
- an active CRM kill switch;
- proposals waiting for review or approval;
- blocked, rejected, stale, expired, or failed proposals;
- replies received in the selected reporting window;
- failed execution/outbox records;
- intake records waiting for review;
- partial outreach read failures;
- failed research records;
- warning and error activity from existing workers.

A deliberately stopped research console is informational. It does not interrupt
Buddy or pretend that an expected stopped state is a failure.

## Event contract

Each result uses the reviewed envelope:

```json
{
  "eventId": "stable-content-hash",
  "occurredAt": "2026-09-30T18:00:00Z",
  "source": "smartklix-crm",
  "type": "approval.pending",
  "subject": { "type": "proposal", "id": "proposal-id" },
  "facts": {},
  "severity": "attention",
  "requiresBuddy": true,
  "dedupeKey": "proposal:proposal-id:pending",
  "evidenceUrl": null
}
```

Classification uses stored statuses and counts only. Missing sources produce an
explicit availability event; the engine never fabricates leads, replies,
failures, cost, or revenue.

## Delivery policy boundary

The local policy supports stable deduplication, a six-hour cooldown, and quiet
hours from 9:00 PM to 8:00 AM in `America/Tijuana`. Urgent events may bypass
quiet hours. Tests exercise recording and replay, but the MCP tool calls the
policy in preview mode and never records a notification as delivered.

Current authority is:

```text
read operations snapshot -> classify -> preview
```

It cannot send WhatsApp messages, start work, approve, execute, mutate CRM, or
spend. Enabling delivery later requires a separate reviewed dispatcher that
records a receipt only after the messaging adapter accepts the notification.

## Next acceptance step

After WhatsApp pairing:

1. Feed synthetic info, attention, urgent, duplicate, and quiet-hour events.
2. Confirm routine events stay local.
3. Confirm one attention event reaches only Buddy.
4. Confirm an immediate duplicate is suppressed.
5. Confirm quiet-hour attention is held and urgent delivery is allowed.
6. Confirm a failed delivery is retained and does not get marked delivered.
7. Repeat against supervised live read-only SmartKlix data.

No event may approve or execute the business action it reports.
