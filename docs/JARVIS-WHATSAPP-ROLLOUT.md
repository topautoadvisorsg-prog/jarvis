# Jarvis WhatsApp rollout

Date: 2026-09-30

Status: bridge prepared and tested; account pairing is intentionally pending.

## Decision

Use Hermes's existing WhatsApp platform. Do not add a WhatsApp agent, another
conversation service, or a second orchestration layer.

The internal proof uses Hermes's bundled Baileys bridge in `self-chat` mode so
Buddy can message his own WhatsApp account. A customer deployment should use a
dedicated business number. The official Meta Cloud API is the preferred durable
customer path when the business has the required Meta account and public signed
webhook.

WhatsApp is only a transport:

```text
Buddy on WhatsApp
  -> Hermes WhatsApp gateway
  -> the existing jarvis-main session
  -> existing Jarvis tools and approval policy
```

SmartKlix outreach email continues through the existing CRM, Reviewer, human
approval, and deterministic executor. WhatsApp does not become an alternate
outreach-delivery channel.

## Prepared locally

- Installed the bundled bridge's locked Node dependencies.
- Passed all 22 bundled bridge tests.
- Selected `self-chat` for the internal proof.
- Kept WhatsApp disabled until valid pairing credentials exist.
- Set DM policy to `allowlist` and group policy to `disabled`.
- Disabled global and WhatsApp allow-all switches.
- Disabled owner-message forwarding and read receipts for the first proof.
- Restarted the Hermes gateway and verified it remains healthy while WhatsApp
  is unpaired and disabled.

No contact is notified and no message is sent by this preparation.

## One pending interactive step

Run this inside the Hermes WSL environment:

```bash
hermes whatsapp
```

The native wizard will request Buddy's own phone number for the allowlist and
display a QR code. In WhatsApp, use **Settings -> Linked Devices -> Link a
Device** and scan it. Hermes writes `WHATSAPP_ENABLED=true` only after pairing
succeeds; cancelling the wizard leaves WhatsApp disabled.

After pairing:

1. Restart the Hermes gateway.
2. Send a message to the account's **Message Yourself** chat.
3. Send `/sethome` there so Hermes has a delivery destination.
4. Resume `jarvis-main` in the Hermes CLI and run `/handoff whatsapp` once.
5. Verify text, voice note transcription, voice response, `/stop`, approval
   responses, restart persistence, and handoff back to the HUD.

The handoff rebinds the WhatsApp home chat to the existing session and reuses
its transcript and tool history. It does not create a new Jarvis brain.

## Reusable customer fields

Each installation changes only these deployment fields:

| Field | Internal owner proof | Customer installation |
| --- | --- | --- |
| Transport | Bundled Baileys bridge | Meta Cloud API preferred |
| Account | Buddy's self-chat | Dedicated business number |
| Allowed users | Buddy's number only | Explicit owner/staff allowlist |
| DM policy | `allowlist` | `allowlist` |
| Group policy | `disabled` | `disabled` unless specifically designed |
| Session | Existing `jarvis-main` | Customer's existing primary Hermes session |
| Write authority | Existing approval policy | Customer-specific approved policy |

Never copy WhatsApp session credentials, access tokens, allowlists, customer
messages, or phone numbers into Git. Each customer gets a separate Hermes home,
credentials, session store, allowlist, and revocation procedure.

## Acceptance test

The phase is complete only when all of these pass:

- unauthorized numbers receive no agent access;
- a text message reaches `jarvis-main` and the response returns;
- a voice note is transcribed correctly;
- voice output returns when requested;
- `/stop` cancels a running turn;
- an approval request remains authoritative and usable;
- the same session context survives gateway restart;
- SmartKlix read tools remain available;
- no business outreach bypasses the CRM execution path.
