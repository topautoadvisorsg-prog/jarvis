# Jarvis rollback package

Date: 2026-09-30

## Purpose

The approved Jarvis source can now be packaged into a verifiable internal
rollback artifact. The builder accepts only a clean Git working tree and reads
the exact committed blobs rather than copying arbitrary files from the live
installation.

The ZIP contains:

- every permitted Git-tracked source file at the recorded commit;
- the sanitized `server/config/server.example.yaml` template;
- a manifest with the commit, Git tree, tag/branch information, file sizes,
  modes, and SHA-256 hashes;
- explicit SHA-256 entries for the HUD avatar assets;
- restore instructions generated for the exact checkpoint.

It deliberately excludes live `.env` and `server.yaml` files, certificates,
logs, sessions, runtime state, backups, downloaded models, generated audio, and
local service data. If any forbidden runtime or secret path becomes tracked,
the builder fails closed instead of packaging it.

## Build and verify

From a clean checkout:

```bash
python server/scripts/build-rollback-package.py
python server/scripts/build-rollback-package.py \
  --verify server/backups/jarvis-rollback-<commit>.zip
```

The default output is `server/backups/`, which is ignored by Git. The builder
creates a ZIP plus an adjacent `.sha256` file, verifies every tracked file and
the generated restore instructions, and produces identical archive bytes when
run again for the same commit.

The package remains an internal recovery artifact. It does not convert the
prototype avatar assets into commercially licensed assets and must not be used
as the customer distribution installer.

## Restore boundary

The package restores source. Private configuration, secrets, certificates,
Hermes state, OpenViking data, local speech models, and other runtime data must
be backed up and restored separately under their own access controls. Follow the
generated `RESTORE.md`, rebuild the environment, and pass health, automated, and
applicable acceptance checks before switching the active checkout.
