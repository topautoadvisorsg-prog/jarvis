# JARVIS production readiness

Updated: 30 September 2026

This document is the handoff for any agent continuing the Windows/Hermes
deployment. Preserve the approved working checkpoint before changing the
avatar, voice path, or Hermes bridge.

## Approved current system

- **Interface:** dedicated browser HUD at `http://127.0.0.1:8765/hud/`.
- **Runtime:** Hermes Agent 0.21.0 remains the only agent, tool, memory, and
  session runtime. The HUD does not contain a second agent architecture.
- **Reasoning provider:** Hermes owns model routing. DeepSeek Flash with
  thinking disabled is active. A real minimal turn completed on 30 September;
  Hermes resolved it to `deepseek-v4-flash`. No fallback provider is configured.
- **Speech input:** OpenAI `gpt-4o-transcribe`, 16 kHz mono PCM, with partial
  captions and final transcription.
- **Speech output:** OpenAI `gpt-4o-mini-tts`, streamed as 16 kHz PCM.
- **Optional full-duplex voice:** GPT-Live-1 is integrated behind the HUD's
  `GPT LIVE` control using WebRTC and client delegation. Hermes remains the
  backend agent and the chained speech path remains available.
- **Visible avatar:** original `server/hud/assets/synthetic-face-v1.png`, shown
  as a stable frontal code-and-particle portrait.
- **Hidden compatibility rig:** CC0 MPFB/TalkingHead remains underneath the
  portrait for the established stream/analyser clock and fallback rendering.
- **Lip movement:** the exact audible playback analyser drives a restrained
  procedural mouth overlay. It uses one dominant spectral family per frame,
  smoothing, silence decay, and immediate reset on interruption.
- **Control path:** typed and spoken commands share conversation `jarvis-main`
  and memory scope `jarvis:user:main`.
- **Preserved administration UI:** Hermes Desktop remains available for
  configuration, history, debugging, and detailed administration.
- **Launch:** the Windows desktop shortcut `Start Jarvis HUD.lnk` starts the
  WSL service and opens the HUD.

Approved Git checkpoint before the final size increase: `c6bed57`.

## Verified behavior

- HUD launches and connects to the local voice server.
- Typed commands reach Hermes and streamed text returns.
- Live microphone capture and OpenAI transcription work.
- Audible streamed voice and restrained mouth motion run from one playback
  path without doubled audio.
- Listening, thinking, executing, speaking, and standby states are wired.
- Tool events render in Agent Activity.
- STOP remains visible during playback, interrupts TalkingHead once, clears
  queued PCM, resets the mouth, and returns to standby.
- Barge-in uses the same interrupt path before microphone capture.
- Generation ids reject stale audio chunks.
- Session identifiers persist in the local Hermes bridge.
- The original Hermes Desktop installation remains separate and usable.
- The HUD reports the real configured Hermes provider/model plus aggregate
  recent success and latency metrics without exposing transcript content.
- The current local automated suite passes, including HTTP/WebSocket
  authentication, security regression, integration, HUD static, telemetry,
  SmartKlix, second-brain, computer-use, and backdoor checks.
- GPT-Live server exchange and delegation contract are covered by the suite;
  a paid live browser session still requires an account-access acceptance run.

## Deliberate limitations of this prototype

- The approved portrait is a 2D generated layer. It has subtle hover and eye
  glow, but does not yet have true eyelid, gaze, or head-pose animation.
- Lip movement is audio-reactive rather than timestamped phoneme alignment.
- Wake-word reliability belongs to the Hermes Desktop/openWakeWord path and is
  not yet a proven hands-free loop inside this browser HUD.
- Provider billing is not yet reconciled across DeepSeek, transcription, TTS,
  GPT Live, research, and delivery. Local token counts and estimates must not be
  presented as an authoritative business budget.
- GPT Live needs idle disconnects, spend caps, and measured task-success/latency
  data before customer rollout.
- The current service is a local single-user installation. It is not a
  customer-facing multi-tenant service.
- Business dashboards show only configured live endpoints; business-specific
  data connectors and permissions have not been defined.

## Production path, in order

### P0 — Freeze and harden the working local system

**WSL supervision first stage complete (2026-09-30).** The HUD launcher now
runs through a bounded supervisor with atomic status, capped restart attempts,
incremental backoff, local log rotation, a 30-second startup health gate, and a
clear terminal failure message. A Windows-native installer/service remains part
of commercial packaging.

1. Tag the approved checkpoint and keep a rollback package containing source,
   sanitized config templates, asset hashes, and restore instructions.
2. Run the full acceptance matrix after a cold Windows/WSL restart: launch,
   text, microphone, transcription, tools, approvals, STOP, barge-in, voice,
   memory, dashboards, and Hermes Desktop coexistence.
3. Package the proven WSL supervisor as a Windows-native installed service with
   signed startup and update/rollback handling for customer deployment.
4. Add browser end-to-end tests for the WebSocket state machine, stale audio,
   double playback, STOP during LLM/tool/TTS phases, and reconnect recovery.
5. Record latency and cost budgets for STT, Hermes, tools, and TTS. Alert on
   regressions rather than relying on subjective testing.

### P1 — Security and customer boundary

1. Complete a deployment-specific threat model before exposing the HUD beyond
   localhost. Keep Hermes and its dashboard bound to loopback.
2. Replace the shared local token with per-user authentication, short-lived
   sessions, CSRF protection, rate limits, and auditable approval decisions.
3. Add tenant/workspace isolation before storing any customer conversation,
   files, credentials, memory, or business data.
4. Centralize secrets in an OS or managed secret store; rotate the current API
   credentials before any pilot distribution.
5. Define retention, export, deletion, backup, and incident-response policies
   for transcripts, audio, tool logs, and Hermes memory.

### P2 — Business capability

1. Choose the first concrete service workflow. Define its data sources,
   allowed tools, required approvals, response-time target, and success metric.
2. Add connectors through Hermes skills/tools so the HUD remains provider and
   business-system agnostic.
3. Build role-scoped business panels from live tool events and APIs; do not
   hard-code decorative fake metrics.
4. Add an audit timeline showing request, model, tool inputs/outputs, approval,
   cancellation, and final result with sensitive-field redaction.
5. Add escalation and human handoff for failures, ambiguous requests, and
   actions that cannot safely complete unattended.

### P3 — Voice and avatar refinement

1. Split the portrait into independently animated eye, mouth, contour, and
   particle layers. Add restrained blinks and gaze without reintroducing a
   rotating realistic head.
2. Upgrade to timestamped phonemes/visemes only if user testing shows the
   current mouth overlay is insufficient.
3. Test the complete hands-free wake → command → response → barge-in → sleep
   loop in the actual room, microphone, speakers, and noise conditions.
4. Select and license the final commercial voice, then test pronunciation,
   multilingual speech, interruption, and long-form stability.

### P4 — Pilot and commercial release

1. Package signed installers and automated updates with rollback.
2. Add opt-in diagnostics, uptime monitoring, error reporting, support export,
   and a privacy-safe customer troubleshooting bundle.
3. Run a limited internal pilot, then one controlled customer pilot with an
   explicit support and incident plan.
4. Complete legal review for generated artwork, third-party libraries, voice,
   data processing, privacy terms, and customer contracts.
5. Promote only after the cold-start acceptance suite, security review,
   recovery drill, and customer workflow metrics pass.

## Rules for future agents

- Do not replace Hermes with a second agent framework.
- Do not couple the HUD to DeepSeek, OpenAI, or another reasoning provider.
- Do not expose API keys to browser code or commit live secrets.
- Do not bring the rejected visible MPFB face back. It produced an uncanny
  rotating mask and circular mouth. The generated frontal portrait is the
  approved visual baseline.
- Do not add decorative dashboards before a real business workflow supplies
  the data.
- Preserve STOP, barge-in, approvals, generation guards, one audible playback
  path, and the shared Hermes session in every UI change.
- Run the focused tests and visually inspect standby, speaking, and STOP before
  committing avatar changes.


