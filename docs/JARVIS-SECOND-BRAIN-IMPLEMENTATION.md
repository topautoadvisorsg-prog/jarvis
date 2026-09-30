# Jarvis second-brain implementation evidence

Date: 2026-09-29

Status: installed and indexed for internal evaluation; Hermes provider remains
disabled because the fixed retrieval evaluation did not beat repository search.

## Installed foundation

- OpenViking `0.4.22` in an isolated Python 3.12 virtual environment at
  `~/.local/share/openviking/venv`.
- Published Linux x86-64 wheel:
  `openviking-0.4.22-cp310-abi3-manylinux_2_31_x86_64.whl`.
- Published wheel SHA-256:
  `fa508fc9c84a32b3206d2f719c415bad5c50e88c1838fb19349881e087da72c8`.
- Upstream license: AGPL-3.0. Internal evaluation is permitted. Review the
  distribution and service boundary before packaging this for customers.
- Loopback-only service: `http://127.0.0.1:1933`.
- Studio: `http://127.0.0.1:1933/studio/`.
- Local embedding model: `bge-small-zh-v1.5-f16`, dimension 512.
- Document-structure model: the existing DeepSeek connection. Its key is read
  from the protected Hermes `.env`; `ov.conf` contains only an environment
  reference.
- OpenViking tracing and remote usage reporting are disabled. Local usage audit
  remains enabled.

`openviking doctor` passed configuration, Python, native engine, AGFS,
authentication, local embedding, VLM, VikingBot, and disk checks.

## Reusable deployment boundary

The committed manifest keeps these per-deployment values together:

- customer ID;
- OpenViking account and user;
- Hermes agent/session identity;
- resource namespace;
- two externally supplied repository roots.

The sync tool never crawls a repository. It accepts only explicitly allowlisted
UTF-8 Markdown/text files, rejects path escapes and blocked directories, applies
size limits, checks high-confidence secret patterns, records Git commits and
content hashes, and allows only a loopback OpenViking endpoint.

A successful sync record performs a cheap namespace check, then prevents
another ingestion/model call when the deployment metadata and all source hashes
are unchanged. This avoids unnecessary model spend without trusting a stale
local record. A changed reviewed package uses OpenViking's same-resource update
path; removals must still be reviewed and verified.

## Initial corpus

Twelve reviewed documents were indexed under
`viking://resources/smartklix`:

- four Jarvis architecture/readiness/roadmap documents at Git commit
  `7ab4fbe6e9d6faf7f087979c47558e63191ef580`;
- three Smart Klix Claude Agents architecture/readiness documents at commit
  `5cddf1ea1e40aac98d8c24b55c506be62f6353f4`;
- five SmartKlix CRM architecture, status, authority, and recovery documents at
  commit `9a4206a9e49ad9ffd33e5cadc117eca68050b09c`.

The package contained 96,199 source bytes and produced 100 indexed contexts.
OpenViking reported 13 processed files including the ingestion record, zero
failed files, zero unsupported files, and zero skipped files. Local storage was
8.7 MiB after indexing.

The initial semantic build reported 102,420 model tokens plus 8,213 tokens for
the resource-reason session commit. Provider billing was not queried, so a cash
cost is deliberately not claimed.

## Verification results

- Direct approval/execution retrieval returned SmartKlix readiness and outreach
  boundary material.
- Direct Jarvis production-gap retrieval ranked `PRODUCTION-READINESS.md` first.
- The service survived a real stop/start, reported healthy on version `0.4.22`,
  and retrieved the existing corpus without re-ingestion.
- A cold start took about 72 seconds while the local embedding model loaded.
  The launcher therefore allows 120 seconds before declaring startup failure.
- An isolated synthetic resource folder was created, verified, recursively
  deleted with semantic refresh enabled, and confirmed absent with HTTP 404.
- A second unchanged sync returned `unchanged` and made no OpenViking call.

## Fixed retrieval evaluation

Twenty questions were fixed before the run and cover Jarvis architecture,
production gaps, STOP/barge-in, SmartKlix authority, startup paths, reviewer and
approval boundaries, Retell limits, mailbox recovery, second-brain exclusions,
an ambiguous current-status question, and a dormant-startup trap.

The deterministic baseline is IDF-weighted text search over the same twelve
allowlisted files. OpenViking uses scoped semantic `find` retrieval.

| Metric | Repository baseline | OpenViking |
|---|---:|---:|
| Correct expected source at rank 1 | 6/20 | 5/20 |
| Correct expected source in top 3 | 17/20 | 7/20 |

OpenViking latency was 78.17 ms minimum, 104.09 ms median, and 491.94 ms
maximum. Hermes session search was not counted in this document-source score
because session history does not supply an authoritative repository path for
these fixed questions.

The pilot's adoption rule requires OpenViking to improve source selection over
the existing stack. It did not. The endpoint, account, user, agent, and resource
recall settings are prepared in Hermes, but `memory.provider` remains empty.
Built-in Hermes memory continues to operate normally, and normal Jarvis turns
are not automatically copied into OpenViking.

## Operations

The Jarvis launcher starts OpenViking in the background when the isolated
installation and local config exist. Dedicated scripts provide start, stop,
and status operations:

```bash
server/scripts/openviking-start.sh
server/scripts/openviking-status.sh
server/scripts/openviking-stop.sh
```

The normal Jarvis health report includes the second-brain health result when
OpenViking is installed.

## Rollback

Hermes is already in the rollback state: built-in memory only. To remove the
prepared connection, unset the `memory.openviking` mapping from
`~/.hermes/config.yaml`. To stop the separate service, run
`server/scripts/openviking-stop.sh`. The original documents remain in their
repositories and SmartKlix CRM remains authoritative for all live business
state.

## Pending before adoption or customer reuse

1. Improve or replace retrieval until it beats the existing source-selection
   baseline, then rerun the same fixed questions.
2. Add a source-citing answer reviewer if the provider reaches the retrieval
   threshold; this run evaluates source selection only.
3. Prove removal of an indexed document from vector retrieval during the next
   changed-manifest test. The current synthetic proof covers filesystem and
   semantic-refresh deletion without spending model tokens on a disposable
   document.
4. Review AGPL-3.0 obligations before any customer packaging or hosted service.
5. Parameterize the manifest for each customer and use only their explicitly
   reviewed documents. Never copy this SmartKlix corpus into another tenant.
