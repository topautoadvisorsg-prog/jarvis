# Jarvis cold-start acceptance

Date: 2026-09-30

## Scope

This acceptance shut down the complete Ubuntu WSL distribution twice and
restored Jarvis through the same supervised startup path used by the Windows
desktop shortcut. It tested process recovery, persistent Hermes continuity,
HTTP/UI availability, and deterministic browser safety behavior. It did not
claim a physical microphone, speaker, wake-word, sleep-word, or full Windows OS
reboot acceptance.

## Problems found and corrected

1. The existing Windows `JARVIS HUD` shortcut launched `server.py` directly,
   bypassing the bounded supervisor and optional dependency startup. The
   shortcut now points to the tracked `windows/Start-Jarvis-HUD.ps1`, which uses
   `server/scripts/jarvis-start.sh` and restores the loopback Hermes dashboard.
2. The repository launcher could report the HUD ready shortly before Hermes
   completed its cold initialization. It now creates the gateway only when port
   8642 is not already listening and waits up to 60 seconds for the Hermes
   health response before starting/reporting the HUD. Re-running startup kept
   the existing gateway PID unchanged.

Regression tests protect both corrections.

## Evidence after the final cold start

- HUD supervisor: healthy with zero crash restarts.
- HUD/voice WebSocket on port 8765: healthy.
- Hermes API on port 8642: healthy.
- Hermes dashboard on loopback port 9119: HTTP 200.
- OpenViking on port 1933: healthy.
- HUD page: HTTP 200 and visibly reconnected to `VOICE SERVER CONNECTED`.
- HUD performance health: `HEALTHY`.
- `jarvis-main` session: the hashed identifier was identical before and after
  both WSL shutdowns.
- Session memory: the pre-shutdown marker `COLD-NOVA-930` was recalled exactly
  after each restart.
- Repeated startup: the gateway PID remained unchanged, proving the launcher did
  not restart an already-running Hermes process.
- Deterministic browser acceptance: STOP passed during thinking, tool activity,
  and speaking; duplicate speaking events produced one playback stream; late
  audio after STOP was rejected; reconnect returned to standby; a stale socket
  could not mutate the active HUD; browser console errors were empty.
- Automated suites: 179 tests passed in the authoritative checkout and 163 tests
  passed in the active live checkout.

The local configuration intentionally serves plain loopback HTTP; unused TLS HUD
and dashboard-proxy ports remain down and are not failures for this deployment.

## Remaining hardware acceptance

Buddy still needs to run the room-level test already listed in
`BUDDY-ACTION-CHECKLIST.md`: microphone capture, real transcription, audible
voice, wake/activation, voice shutoff/sleep, physical STOP, barge-in with speaker
echo, and return to standby. One full Windows reboot should then confirm that
the desktop shortcut restores the same supervised stack from a powered-down OS.
