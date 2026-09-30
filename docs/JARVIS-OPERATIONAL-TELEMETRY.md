# Jarvis operational telemetry and model evidence

Date: 2026-09-30

## Implemented boundary

The HUD now reads the configured Hermes provider and model from the protected
local Hermes configuration and displays their names without returning keys or
other configuration. The usage API also summarizes the most recent 200 Jarvis
turn records into:

- successful, interrupted, and failed counts;
- raw successful-turn rate and completion reliability excluding intentional
  STOP/barge-in turns;
- median and 95th-percentile LLM time to first token;
- median and 95th-percentile total turn time;
- the latest recorded provider/model labels.

Only aggregate numbers and provider/model labels leave the server. Transcripts,
responses, error text, run IDs, and tool inputs/outputs remain absent from this
telemetry response. Existing local token and TTS-character counters remain in
place. Cash cost stays unknown unless a verified price source is configured.

## Local performance health

`/api/usage` now evaluates the aggregate measurements and returns a separate
`performance_health` object. The HUD displays one of three states:

- `WARMING UP` until every check has enough measured samples;
- `HEALTHY` when all measured checks are inside their guardrails;
- `DEGRADED` when at least one sufficiently sampled check crosses a guardrail.

The initial defaults are five samples, at least 80% completion reliability, no
more than 15 seconds for p95 LLM time to first token, and no more than 60 seconds
for p95 total turn time. They are configurable under
`usage.performance_health` in `server.yaml`. These deliberately broad values are
early local regression detectors, not a customer SLA. They should be tightened
only after enough representative turns exist for the actual hardware, network,
tools, and providers.

An intentional STOP or barge-in remains visible in the raw turn counts but is
excluded from completion reliability. This prevents a normal safety control
from being reported as a backend failure. Missing timing fields stay `unknown`;
the system does not manufacture a passing result from incomplete evidence.

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

The current health signal covers end-to-end turn time and Hermes response time.
Separate provider-specific STT, tool, and TTS guardrails still require enough
real measurements and remain open production work.
