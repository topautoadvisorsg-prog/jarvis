# Buddy action checklist

Updated: 2026-09-30

These items require Buddy's account access or an interactive decision. They do
not block local Jarvis engineering.

## Pending activations

- [ ] **Run the room-level voice lifecycle test when available.** On the actual
  microphone and speakers, verify wake/voice activation, continuous listening,
  the voice shutoff or sleep command, STOP during a response, barge-in while
  Jarvis is speaking, and the return to standby. Record any missed activation,
  failure to stop listening, echo, duplicate playback, or delayed interruption.
- [ ] **Finish WhatsApp QR pairing.** Resume the existing pairing wizard, scan
  the QR code with the intended account, and confirm the allowlisted owner
  number. Keep groups and customer messaging disabled during acceptance.
- [ ] **Authorize personal Google read-only access.** Complete OAuth with only
  `gmail.readonly` and `calendar.readonly`, then run the acceptance checks in
  `JARVIS-PERSONAL-GOOGLE-READONLY.md`.
- [ ] **Authorize the SmartKlix Vercel project.** Use an account with access to
  the linked project, configure the production read token to match the protected
  local value, redeploy, and run the safe CRM activation preflight. Do not paste
  the token into chat, source control, or browser-visible configuration.

## Deferred decisions

- [ ] Choose a dedicated WhatsApp Business number and Cloud API path before any
  customer-facing deployment.
- [ ] Select the first customer pilot workflow after the local operator loop is
  accepted.
- [ ] Select and license the commercial voice and final avatar assets before
  commercial distribution.
