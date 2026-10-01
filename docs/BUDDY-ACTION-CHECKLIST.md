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
- [ ] **Run one full Windows reboot acceptance after the room voice test.** Use
  the desktop `JARVIS HUD` shortcut after sign-in and confirm the supervised HUD,
  Hermes API, dashboard, and second brain return without terminal repair. The
  equivalent complete WSL shutdown/recovery test already passes.
- [ ] **Finish WhatsApp QR pairing.** Resume the existing pairing wizard, scan
  the QR code with the intended account, and confirm the allowlisted owner
  number. Keep groups and customer messaging disabled during acceptance.
- [ ] **Authorize personal Google read-only access.** Complete OAuth with only
  `gmail.readonly` and `calendar.readonly`, then run the acceptance checks in
  `JARVIS-PERSONAL-GOOGLE-READONLY.md`.
- [x] **Authorize the SmartKlix Vercel project.** Completed September 30, 2026.
  The protected production token was saved, the CRM redeployed, unauthenticated
  access returned HTTP 401, authenticated access returned HTTP 200, and the
  temporary local token file/page were removed.

## Deferred decisions

- [ ] Choose a dedicated WhatsApp Business number and Cloud API path before any
  customer-facing deployment.
- [ ] Select the first customer pilot workflow after the local operator loop is
  accepted.
- [ ] Fill in a copy of `customer-deployment/example-handyman.yaml` for the
  first customer pilot and review the generated approval boundaries before
  installation.
- [ ] Select and license the commercial voice and final avatar assets before
  commercial distribution.
