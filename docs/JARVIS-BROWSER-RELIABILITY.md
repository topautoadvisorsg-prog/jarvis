# Jarvis browser reliability acceptance

Date: 2026-09-30

## Scope

The browser acceptance uses the real HUD document in Chromium with a
deterministic in-page WebSocket and avatar adapter. It exercises the same DOM,
event handlers, STOP button, audio-generation state, reconnect timer, and visual
state transitions used by the live interface without calling a model, speech
provider, or business system.

Covered behavior:

- STOP during model thinking;
- STOP during visible tool execution;
- STOP during streamed speech;
- duplicate `speaking` events do not start duplicate playback;
- audio arriving after STOP is dropped;
- a dropped WebSocket returns the HUD to standby and hides STOP;
- a closed socket cannot mutate the reconnected HUD;
- repeated close callbacks cannot schedule duplicate reconnects;
- the active replacement socket continues receiving events;
- no browser console or page errors occur in the deterministic run.

## Defect found and corrected

The first real-browser reconnect test proved that a closed socket retained a
live `onmessage` callback. After the replacement socket connected, a delayed
event from the closed socket could still move the HUD back to `PROCESSING` and a
repeated close callback could schedule another connection.

Each connection now receives an epoch and captures its own socket. Open, close,
and message callbacks return immediately unless both values still identify the
active connection. A real disconnect also clears the active run and recording
state, interrupts audio, hides STOP, and schedules exactly one reconnect.

## Repeatable command

From the repository root on Windows with Node/npm available:

```powershell
npx --yes @playwright/cli -s=jarvis-reliability open about:blank
npx --yes @playwright/cli -s=jarvis-reliability run-code --filename server/scripts/hud-browser-reliability.js
npx --yes @playwright/cli -s=jarvis-reliability close
```

Passing output includes `"passed":true`, all four tested phases, one audio
stream start, two accepted PCM chunks, one playback interruption, one dropped
late chunk, two total socket instances, and an empty `consoleErrors` array.

This deterministic test complements the Python WebSocket protocol suite. A
room-level microphone/speaker acceptance run is still required for acoustic
echo, device permissions, and real autoplay behavior.
