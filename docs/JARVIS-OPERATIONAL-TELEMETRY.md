# Jarvis operational telemetry and model evidence

Date: 2026-09-30

## Implemented boundary

The HUD now reads the configured Hermes provider and model from the protected
local Hermes configuration and displays their names without returning keys or
other configuration. The usage API also summarizes the most recent 200 Jarvis
turn records into:

- successful, interrupted, and failed counts;
- success rate;
- median and 95th-percentile LLM time to first token;
- median and 95th-percentile total turn time;
- the latest recorded provider/model labels.

Only aggregate numbers and provider/model labels leave the server. Transcripts,
responses, error text, run IDs, and tool inputs/outputs remain absent from this
telemetry response. Existing local token and TTS-character counters remain in
place. Cash cost stays unknown unless a verified price source is configured.

## Live model proof

A real minimal Hermes turn completed on 2026-09-30 with the exact response
`ROUTING_OK`. Hermes reported:

- configured provider: `deepseek`;
- configured alias: `deepseek-flash`;
- resolved model: `deepseek-v4-flash`;
- one API call;
- 12,715 input, 5 output, and 5,504 cache-read tokens;
- zero reasoning tokens;
- estimated cost: $0.0017969112, labeled `estimated` by Hermes;
- wall-clock time: 16.579 seconds.

This proves the DeepSeek route currently works. One tiny turn is not a latency
or cost benchmark, and the estimate is not a provider invoice.

## Routing policy now

- Normal HUD and tool work remains in the existing `jarvis-main` Hermes session.
- DeepSeek Flash is the configured economical general model.
- GPT Live remains an explicit user-selected voice mode; it does not replace
  Hermes for memory, tools, files, business data, or actions.
- No scheduled jobs exist, so no background model override is active.
- No automatic model selector was added. Routing decisions remain deterministic
  and visible until enough real task evidence exists to justify another route.

## Deliberate exclusions

This is not the deferred business budget ledger. It does not claim provider
billing, allocate budgets, reconcile late charges, or combine SmartKlix,
transcription, speech, phone, and delivery expenses. Those require authoritative
provider records and remain a later milestone.
