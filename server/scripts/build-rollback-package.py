#!/usr/bin/env python3
"""Build and verify a secret-free Jarvis rollback archive from a clean Git commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


FORBIDDEN_EXACT = {
    ".env",
    "server/config/server.yaml",
}
FORBIDDEN_PARTS = {
    "backups",
    "certs",
    "logs",
    "models",
    "run",
}


def _git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_forbidden(path: str) -> bool:
    normalized = PurePosixPath(path)
    lowered = path.lower()
    name = normalized.name.lower()
    if path in FORBIDDEN_EXACT or name == ".env" or name.startswith(".env.") or lowered.endswith(".env"):
        return True
    if path.startswith("server/config/") and path != "server/config/server.example.yaml":
        return True
    if path.startswith("server/") and any(part in FORBIDDEN_PARTS for part in normalized.parts):
        return True
    if path.startswith("server/hud/") and normalized.parts[-2:-1] in (("audio",), ("demo",)):
        return True
    return False


def _tracked_files(repo: Path) -> list[dict]:
    raw = _git(repo, "ls-tree", "-r", "-z", "--full-tree", "HEAD", text=False)
    files = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, encoded_path = entry.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split()
        if object_type != "blob":
            continue
        path = encoded_path.decode("utf-8", errors="strict")
        if _is_forbidden(path):
            raise RuntimeError(f"refusing to package forbidden tracked path: {path}")
        content = _git(repo, "cat-file", "blob", object_id, text=False)
        files.append(
            {
                "path": path,
                "mode": mode,
                "size": len(content),
                "sha256": _sha256(content),
                "content": content,
            }
        )
    return sorted(files, key=lambda item: item["path"])


def _restore_instructions(commit: str, tree: str, archive_name: str) -> bytes:
    return f"""# Restore this Jarvis checkpoint

This internal rollback package contains Git-tracked source from commit
`{commit}` (tree `{tree}`). It deliberately excludes live secrets, private
configuration, certificates, logs, sessions, models, audio, and runtime state.

## Verify before restoring

1. Keep the ZIP and its adjacent `.sha256` file together.
2. Verify the outer archive checksum with `sha256sum -c {archive_name}.sha256`
   or the platform equivalent.
3. From a trusted Jarvis checkout, run:
   `python server/scripts/build-rollback-package.py --verify {archive_name}`.

## Restore

1. Stop only the HUD with `server/scripts/jarvis-stop.sh`. This leaves the
   Hermes gateway running.
2. Copy the current private `server/config/server.yaml`, `~/.hermes/.env`, and
   any required local certificates to a protected location outside the source
   tree. Do not place them in this archive or Git.
3. Extract this ZIP into a new directory. Do not overlay a running checkout.
4. Review `server/config/server.example.yaml`, then either create a fresh
   `server/config/server.yaml` or restore the separately protected configuration.
   Re-enter or rotate secrets through the normal secret store; never copy them
   from logs or chat history.
5. Recreate the Python environment using `docs/SETUP.md`. Local speech models,
   certificates, OpenViking data, and Hermes state are external dependencies and
   are not restored by this source package.
6. Start with `server/scripts/jarvis-start.sh`, run
   `server/scripts/jarvis-health.sh`, then run the automated test suite and the
   applicable text/voice/STOP/approval acceptance checks before replacing the
   previous checkout.

The prototype avatar notice still applies. This package is an internal rollback
artifact and is not a commercially licensed distribution bundle.
""".encode("utf-8")


def _zip_info(name: str, timestamp: tuple[int, int, int, int, int, int], mode: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    return info


def build_package(repo: Path, output_dir: Path) -> tuple[Path, Path]:
    repo = repo.resolve()
    if (_git(repo, "status", "--porcelain") or "").strip():
        raise RuntimeError("working tree must be clean before building a rollback package")

    commit = str(_git(repo, "rev-parse", "HEAD")).strip()
    short_commit = str(_git(repo, "rev-parse", "--short=12", "HEAD")).strip()
    tree = str(_git(repo, "rev-parse", "HEAD^{tree}")).strip()
    branch = str(_git(repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
    tags = sorted(filter(None, str(_git(repo, "tag", "--points-at", "HEAD")).splitlines()))
    commit_epoch = int(str(_git(repo, "show", "-s", "--format=%ct", "HEAD")).strip())
    commit_time = datetime.fromtimestamp(commit_epoch, timezone.utc)
    zip_timestamp = max(commit_time, datetime(1980, 1, 1, tzinfo=timezone.utc)).timetuple()[:6]
    created_at = commit_time.isoformat().replace("+00:00", "Z")

    files = _tracked_files(repo)
    root = f"jarvis-rollback-{short_commit}"
    archive_name = f"{root}.zip"
    restore = _restore_instructions(commit, tree, archive_name)
    public_files = [{key: item[key] for key in ("path", "mode", "size", "sha256")} for item in files]
    manifest = {
        "schema_version": 1,
        "commit": commit,
        "tree": tree,
        "branch": branch,
        "tags": tags,
        "commit_time": created_at,
        "root": root,
        "tracked_file_count": len(public_files),
        "config_templates": [item["path"] for item in public_files if item["path"].startswith("server/config/")],
        "assets": [item for item in public_files if item["path"].startswith("server/hud/assets/")],
        "restore_sha256": _sha256(restore),
        "files": public_files,
        "exclusions": [
            "live configuration and .env files",
            "certificates and secrets",
            "logs, sessions, runtime state, and backups",
            "downloaded models, generated audio, and local service data",
        ],
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for item in files:
            mode = int(item["mode"], 8)
            bundle.writestr(_zip_info(f"{root}/{item['path']}", zip_timestamp, mode), item["content"])
        bundle.writestr(_zip_info(f"{root}/ROLLBACK-MANIFEST.json", zip_timestamp, 0o100644), manifest_bytes)
        bundle.writestr(_zip_info(f"{root}/RESTORE.md", zip_timestamp, 0o100644), restore)

    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{_sha256(archive_path.read_bytes())}  {archive_path.name}\n", encoding="utf-8")
    return archive_path, checksum_path


def verify_package(archive_path: Path) -> dict:
    archive_path = archive_path.resolve()
    with zipfile.ZipFile(archive_path, "r") as bundle:
        manifests = [name for name in bundle.namelist() if name.endswith("/ROLLBACK-MANIFEST.json")]
        if len(manifests) != 1:
            raise RuntimeError("archive must contain exactly one rollback manifest")
        manifest = json.loads(bundle.read(manifests[0]))
        root = manifest["root"]
        expected = {f"{root}/{item['path']}" for item in manifest["files"]}
        expected.update({f"{root}/ROLLBACK-MANIFEST.json", f"{root}/RESTORE.md"})
        actual = {name for name in bundle.namelist() if not name.endswith("/")}
        if actual != expected:
            raise RuntimeError("archive contents do not match the manifest")
        for item in manifest["files"]:
            content = bundle.read(f"{root}/{item['path']}")
            if len(content) != item["size"] or _sha256(content) != item["sha256"]:
                raise RuntimeError(f"file verification failed: {item['path']}")
        if _sha256(bundle.read(f"{root}/RESTORE.md")) != manifest["restore_sha256"]:
            raise RuntimeError("restore instructions failed verification")

    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    if checksum_path.exists():
        expected_checksum = checksum_path.read_text(encoding="utf-8").split()[0]
        if _sha256(archive_path.read_bytes()) != expected_checksum:
            raise RuntimeError("outer archive checksum failed verification")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify", type=Path, metavar="ZIP")
    args = parser.parse_args()
    if args.verify:
        manifest = verify_package(args.verify)
        print(f"verified {args.verify}: {manifest['tracked_file_count']} files at {manifest['commit']}")
        return 0
    output_dir = args.output_dir or args.repo / "server" / "backups"
    archive, checksum = build_package(args.repo, output_dir)
    manifest = verify_package(archive)
    print(f"created {archive}")
    print(f"created {checksum}")
    print(f"verified {manifest['tracked_file_count']} files at {manifest['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
