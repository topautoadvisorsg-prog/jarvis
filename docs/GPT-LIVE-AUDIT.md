# GPT-Live integration audit

Date: 23 September 2026

## Reported failure

The user started GPT Live, said “Hi, how's it going?”, and heard no response.

## Evidence and root cause

The OpenAI session exchange succeeded (`POST /api/live/session` returned 201),
and the browser received an output transcript: “Hey! I'm doing fine, just
hanging out. What about you?” The GPT-Live model and data channel therefore
worked. The failure was in local playback.

The first implementation routed the remote WebRTC stream directly into a Web
Audio graph. OpenAI's supported browser example attaches the received remote
track to an autoplay `HTMLAudioElement` and explicitly calls `play()`, with a
visible recovery when autoplay is blocked. The HUD omitted that playback path,
so it could receive transcripts while remaining silent.

The first implementation also assumed input/output transcript `.done` events.
The official GPT-Live session guide states that transcript deltas have no item
ID and no event marking a completed conversational turn. That assumption made
caption grouping unreliable and could send an incomplete utterance to Hermes.

A second independent fault was found during the audit: Hermes was not listening
on port 8642. A macOS-only HUD restart script had been run under WSL; it stopped
the local processes but its `launchctl` start commands could not restore them.
Direct GPT-Live conversation still worked, but delegated memory, tools, and
actions could not reach Hermes.

## Corrections

- Remote speech now uses the documented autoplay media-element path.
- A cloned remote track feeds a muted analyser graph for avatar lip movement;
  the original track remains the single audible output.
- Playback rejection is shown in the HUD and the GPT LIVE control becomes an
  explicit ENABLE AUDIO recovery action.
- Transcript fragments are grouped by speaker and timing gaps. Client
  delegation waits briefly for trailing transcript fragments before submitting
  the task to Hermes.
- The browser keeps a bounded `window.__jarvisLiveEvents` event trace for local
  diagnosis without recording transcript content or audio.
- `session.close` is sent before local GPT-Live cleanup.
- Normal Starlette WebSocket disconnects no longer produce noisy ASGI traces.
- The Hermes gateway was restored in a persistent WSL tmux session and its
  `/health` endpoint was verified before retesting the HUD.
- The start/stop/restart scripts now select launchd on macOS and persistent
  tmux services on Linux/WSL. Restarting the HUD leaves a healthy Hermes
  gateway running and restores it automatically if it is absent.

## Voice controls

- **ENGAGE VOICE** is the established push-to-talk path: microphone recording,
  OpenAI transcription, Hermes, then OpenAI TTS.
- **GPT LIVE** starts the new continuous full-duplex voice session. GPT-Live
  handles casual speech directly and delegates memory, reasoning, tools, files,
  and actions to the same persistent Hermes session.
- **STOP** ends speech and stops an active delegated Hermes run.

## Acceptance checks

1. GPT-Live session creation returns 201.
2. `session.started` arrives on the `oai-events` data channel.
3. A remote audio track reaches the autoplay media element.
4. `session.output_transcript.delta` and audible speech occur together; the HUD
   displays `GPT LIVE · AUDIO` after playback begins.
5. A delegated request creates a Hermes run and displays tool/approval events.
6. STOP cancels the Hermes run and closes the GPT-Live session.
7. ENGAGE VOICE remains usable after GPT-Live ends.
