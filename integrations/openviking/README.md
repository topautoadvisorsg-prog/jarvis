# Controlled OpenViking integration

This directory makes the second-brain corpus explicit and reusable. It does
not crawl repositories. Only files listed in `sources.smartklix.json` can be
packaged or sent to the loopback OpenViking server.

The reviewed pilot pins OpenViking `0.4.22` in a separate Python 3.12 virtual
environment. A new deployment can reproduce that boundary with `uv`:

```bash
uv python install 3.12
uv venv "$HOME/.local/share/openviking/venv" --python 3.12
uv pip install --python "$HOME/.local/share/openviking/venv/bin/python" \
  'openviking==0.4.22'
mkdir -p "$HOME/.openviking"
cp integrations/openviking/ov.conf.example "$HOME/.openviking/ov.conf"
chmod 600 "$HOME/.openviking/ov.conf"
```

Replace only the workspace owner segment in the copied config. The example
expects `DEEPSEEK_API_KEY` in the protected environment and never embeds it.
Run `~/.local/share/openviking/venv/bin/openviking doctor --config
~/.openviking/ov.conf` before starting the service. Customer packaging still
requires an AGPL-3.0 distribution review.

Customer-specific fields live in the manifest's `deployment` object:

- `customerId`
- `account`
- `user`
- `agent`
- `namespace`

Repository locations are supplied at runtime. They are never committed as
machine-specific absolute paths:

```powershell
$env:SMARTKLIX_AGENTS_ROOT = 'C:\path\to\specialized-agents'
$env:SMARTKLIX_CRM_ROOT = 'C:\path\to\crm'
python -m integrations.openviking.second_brain `
  --manifest integrations/openviking/sources.smartklix.json plan
```

The `plan` command validates paths, extensions, file sizes, duplicate targets,
UTF-8 content, and high-confidence secret patterns. `bundle` creates a ZIP with
an ingestion record. `sync` uploads that reviewed bundle to local OpenViking.
When `--record` points to the prior successful record, `sync` verifies that the
namespace still exists and skips ingestion/model calls if the deployment
metadata and every source hash are unchanged. `verify` lists the resulting
tree, and `find` performs a scoped semantic query.

Changing or removing indexed material is deliberately not automatic. Review
the new plan, remove the old namespace through the OpenViking administration
surface, verify deletion, and then sync the replacement. This avoids silently
destroying the only indexed copy or retaining stale material by accident.

OpenViking remains a document context service. SmartKlix CRM remains the source
of truth for leads, approvals, sends, replies, and live business state.

The local visual explorer is available at `http://127.0.0.1:1933/studio/` while
the service is running. Use the dedicated `server/scripts/openviking-*.sh`
scripts for lifecycle control. The first SmartKlix evaluation did not beat the
repository-search baseline, so the normal Hermes memory provider intentionally
remains disabled; see `docs/JARVIS-SECOND-BRAIN-IMPLEMENTATION.md`.
