"""Build and sync a strictly allowlisted OpenViking document bundle.

The manifest is the authority boundary. This module never crawls a repository,
reads a directory recursively, or follows a source path outside its declared
root. Secrets are rejected before a bundle can be created or uploaded.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
ENV_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:sk|rk|pk)_[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(
        r"(?im)^\s*[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*"
        r"(?!\$\{|<|example|placeholder|redacted|changeme)[^\s#]{12,}\s*$"
    ),
)


class ManifestError(ValueError):
    """Raised when a manifest or selected source violates the pilot boundary."""


@dataclass(frozen=True)
class PlannedSource:
    id: str
    source: Path
    repository_root: Path
    target: str
    sha256: str
    size: int
    git_commit: str | None
    status: str
    owner_system: str
    sensitivity: str
    replacement_path: str | None

    def record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "originalAbsolutePath": str(self.source),
            "repositoryRoot": str(self.repository_root),
            "target": self.target,
            "repositoryCommit": self.git_commit,
            "sha256": self.sha256,
            "bytes": self.size,
            "status": self.status,
            "ownerSystem": self.owner_system,
            "sensitivity": self.sensitivity,
            "replacementPath": self.replacement_path,
        }


def _expand(value: str, environ: Mapping[str, str]) -> str:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        resolved = environ.get(name)
        if not resolved:
            missing.add(name)
            return match.group(0)
        return resolved

    result = ENV_PATTERN.sub(replace, value)
    if missing:
        raise ManifestError(f"Missing required environment variables: {', '.join(sorted(missing))}")
    return result


def load_manifest(path: Path, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1:
        raise ManifestError("Unsupported manifest schemaVersion")
    if not isinstance(data.get("sources"), list) or not data["sources"]:
        raise ManifestError("Manifest requires at least one source")
    deployment = data.get("deployment") or {}
    for key in ("customerId", "account", "user", "agent", "namespace"):
        if not str(deployment.get(key) or "").strip():
            raise ManifestError(f"deployment.{key} is required")
    endpoint = str((data.get("server") or {}).get("endpoint") or "")
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise ManifestError("OpenViking endpoint must use loopback HTTP for this local pilot")
    return data


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _contains_blocked_part(path: Path, blocked_parts: set[str]) -> str | None:
    for part in path.parts:
        if part.casefold() in blocked_parts:
            return part
    return None


def plan_sources(
    manifest_path: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], list[PlannedSource]]:
    env = os.environ if environ is None else environ
    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path, env)
    policy = manifest.get("policy") or {}
    allowed_extensions = {str(item).casefold() for item in policy.get("allowedExtensions", [])}
    max_bytes = int(policy.get("maxFileBytes", 0))
    blocked_parts = {str(item).casefold() for item in policy.get("blockedPathParts", [])}
    if not allowed_extensions or max_bytes <= 0:
        raise ManifestError("policy.allowedExtensions and positive maxFileBytes are required")

    repo_root = manifest_path.parents[2]
    planned: list[PlannedSource] = []
    ids: set[str] = set()
    targets: set[str] = set()

    for raw in manifest["sources"]:
        source_id = str(raw.get("id") or "").strip()
        if not source_id or source_id in ids:
            raise ManifestError(f"Source id is missing or duplicated: {source_id!r}")
        ids.add(source_id)

        root_text = _expand(str(raw.get("root") or ""), env)
        root = (repo_root / root_text).resolve() if not Path(root_text).is_absolute() else Path(root_text).resolve()
        relative = Path(str(raw.get("path") or ""))
        source = (root / relative).resolve()
        if source != root and root not in source.parents:
            raise ManifestError(f"Source {source_id} escapes its declared root")
        if not source.is_file():
            raise ManifestError(f"Source {source_id} does not exist: {source}")
        if source.suffix.casefold() not in allowed_extensions:
            raise ManifestError(f"Source {source_id} has a disallowed extension")
        blocked = _contains_blocked_part(relative, blocked_parts)
        if blocked:
            raise ManifestError(f"Source {source_id} contains blocked path part: {blocked}")

        content = source.read_bytes()
        if len(content) > max_bytes:
            raise ManifestError(f"Source {source_id} exceeds maxFileBytes")
        text = content.decode("utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ManifestError(f"Source {source_id} matched a secret-safety pattern")

        target = str(raw.get("target") or "").strip().replace("\\", "/").lstrip("/")
        target_path = Path(target)
        if not target or ".." in target_path.parts or target in targets:
            raise ManifestError(f"Source {source_id} has an invalid or duplicated target")
        targets.add(target)

        status = str(raw.get("status") or "")
        if status not in {"current", "historical", "superseded"}:
            raise ManifestError(f"Source {source_id} has invalid status: {status}")

        planned.append(
            PlannedSource(
                id=source_id,
                source=source,
                repository_root=root,
                target=target,
                sha256=hashlib.sha256(content).hexdigest(),
                size=len(content),
                git_commit=_git_commit(root),
                status=status,
                owner_system=str(raw.get("ownerSystem") or ""),
                sensitivity=str(raw.get("sensitivity") or ""),
                replacement_path=raw.get("replacementPath"),
            )
        )
    return manifest, planned


def build_bundle(manifest: dict[str, Any], planned: list[PlannedSource]) -> tuple[bytes, dict[str, Any]]:
    indexed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "schemaVersion": 1,
        "deployment": manifest["deployment"],
        "indexedAt": indexed_at,
        "sources": [item.record() for item in planned],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("_ingestion-record.json", json.dumps(record, indent=2) + "\n")
        for item in planned:
            archive.writestr(item.target, item.source.read_bytes())
    payload = buffer.getvalue()
    record["bundleSha256"] = hashlib.sha256(payload).hexdigest()
    record["bundleBytes"] = len(payload)
    return payload, record


def source_set_sha256(manifest: dict[str, Any], planned: list[PlannedSource]) -> str:
    """Return a stable digest for the deployment and indexed source contents.

    Machine-specific roots and repository commits are audit metadata, so moving
    a checkout or committing an unrelated file does not trigger re-ingestion.
    """
    stable = {
        "deployment": manifest["deployment"],
        "sources": [{
            "id": item.id,
            "target": item.target,
            "sha256": item.sha256,
            "status": item.status,
            "ownerSystem": item.owner_system,
            "sensitivity": item.sensitivity,
            "replacementPath": item.replacement_path,
        } for item in planned],
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def unchanged_sync(record_path: Path | None, source_set_hash: str) -> dict[str, Any] | None:
    """Return the previous record when the reviewed source set has not changed."""
    if record_path is None or not record_path.is_file():
        return None
    try:
        previous = json.loads(record_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if previous.get("sourceSetSha256") == source_set_hash:
        return previous
    return None


def tree_has_content(response: dict[str, Any]) -> bool:
    """Accept both list and wrapped-list shapes returned by OpenViking releases."""
    result = response.get("result")
    if isinstance(result, list):
        return bool(result)
    if isinstance(result, dict):
        for key in ("items", "entries", "nodes"):
            if isinstance(result.get(key), list) and result[key]:
                return True
    return False


def _headers(manifest: dict[str, Any]) -> dict[str, str]:
    deployment = manifest["deployment"]
    return {
        "Accept": "application/json",
        "X-OpenViking-Account": deployment["account"],
        "X-OpenViking-User": deployment["user"],
    }


def _request_json(
    url: str,
    *,
    headers: Mapping[str, str],
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    body: bytes | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    request_headers = dict(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"OpenViking HTTP {error.code}: {detail}") from error


def upload_bundle(manifest: dict[str, Any], bundle: bytes, *, timeout: float = 900) -> dict[str, Any]:
    endpoint = manifest["server"]["endpoint"].rstrip("/")
    headers = _headers(manifest)
    boundary = f"----jarvis-openviking-{uuid.uuid4().hex}"
    filename = f"{manifest['deployment']['namespace']}.zip"
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: application/zip\r\n\r\n",
        bundle,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    upload_headers = {**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    uploaded = _request_json(
        f"{endpoint}/api/v1/resources/temp_upload",
        headers=upload_headers,
        method="POST",
        body=b"".join(parts),
        timeout=60,
    )
    temp_id = str((uploaded.get("result") or {}).get("temp_file_id") or "")
    if not temp_id:
        raise RuntimeError("OpenViking upload did not return temp_file_id")

    namespace = manifest["deployment"]["namespace"]
    return _request_json(
        f"{endpoint}/api/v1/resources",
        headers=headers,
        method="POST",
        payload={
            "temp_file_id": temp_id,
            "source_name": namespace,
            "to": f"viking://resources/{namespace}",
            "reason": "Reviewed Jarvis/SmartKlix architecture and operating knowledge",
            "instruction": "Preserve source paths, distinguish current from historical status, and summarize ownership and authority boundaries.",
            "wait": True,
            "timeout": timeout,
            "strict": True,
            "preserve_structure": True,
            "tags": ["corpus=smartklix", "status=reviewed", "scope=internal-architecture"],
        },
        timeout=timeout + 30,
    )


def verify_tree(manifest: dict[str, Any]) -> dict[str, Any]:
    endpoint = manifest["server"]["endpoint"].rstrip("/")
    namespace = manifest["deployment"]["namespace"]
    query = urllib.parse.urlencode(
        {"uri": f"viking://resources/{namespace}", "recursive": "true", "node_limit": "1000"}
    )
    return _request_json(
        f"{endpoint}/api/v1/fs/ls?{query}", headers=_headers(manifest), timeout=30
    )


def semantic_find(manifest: dict[str, Any], query: str, *, limit: int = 8) -> dict[str, Any]:
    endpoint = manifest["server"]["endpoint"].rstrip("/")
    namespace = manifest["deployment"]["namespace"]
    return _request_json(
        f"{endpoint}/api/v1/search/find",
        headers=_headers(manifest),
        method="POST",
        payload={
            "query": query,
            "target_uri": f"viking://resources/{namespace}",
            "limit": limit,
            "include_provenance": True,
            "read_content": False,
        },
        timeout=60,
    )


def _print_plan(manifest: dict[str, Any], planned: list[PlannedSource]) -> None:
    print(f"namespace: viking://resources/{manifest['deployment']['namespace']}")
    print(f"sources: {len(planned)}")
    print(f"bytes: {sum(item.size for item in planned)}")
    for item in planned:
        print(f"- {item.id}: {item.target} sha256={item.sha256}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    bundle_parser = subparsers.add_parser("bundle")
    bundle_parser.add_argument("--output", type=Path, required=True)
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--record", type=Path)
    subparsers.add_parser("verify")
    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("query")
    args = parser.parse_args(argv)

    manifest, planned = plan_sources(args.manifest)
    if args.command == "plan":
        _print_plan(manifest, planned)
        return 0
    if args.command == "verify":
        print(json.dumps(verify_tree(manifest), indent=2))
        return 0
    if args.command == "find":
        print(json.dumps(semantic_find(manifest, args.query), indent=2))
        return 0

    source_set_hash = source_set_sha256(manifest, planned)
    if args.command == "sync":
        previous = unchanged_sync(args.record, source_set_hash)
        if previous is not None:
            try:
                tree = verify_tree(manifest)
                namespace_exists = tree_has_content(tree)
            except Exception:
                namespace_exists = False
            if namespace_exists:
                print(json.dumps({
                    "status": "unchanged",
                    "sourceSetSha256": source_set_hash,
                    "indexedAt": previous.get("indexedAt"),
                    "message": "No source hash changed; ingestion and model calls were skipped.",
                }, indent=2))
                return 0

    bundle, record = build_bundle(manifest, planned)
    record["sourceSetSha256"] = source_set_hash
    if args.command == "bundle":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(bundle)
        print(json.dumps(record, indent=2))
        return 0

    result = upload_bundle(manifest, bundle)
    record["openVikingResult"] = result.get("result")
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": record, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
