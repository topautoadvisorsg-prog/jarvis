import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from integrations.openviking.second_brain import (
    ManifestError,
    build_bundle,
    plan_sources,
    source_set_sha256,
    tree_has_content,
    unchanged_sync,
)


def _manifest(tmp_path: Path, source_path: str = "docs/architecture.md") -> Path:
    manifest = {
        "schemaVersion": 1,
        "deployment": {
            "customerId": "test",
            "account": "default",
            "user": "default",
            "agent": "jarvis-main",
            "namespace": "test-brain",
        },
        "server": {"endpoint": "http://127.0.0.1:1933"},
        "policy": {
            "allowedExtensions": [".md"],
            "maxFileBytes": 4096,
            "blockedPathParts": [".env", "credentials"],
        },
        "sources": [{
            "id": "architecture",
            "root": "${TEST_SOURCE_ROOT}",
            "path": source_path,
            "target": "system/architecture.md",
            "status": "current",
            "ownerSystem": "test-system",
            "sensitivity": "internal-architecture",
        }],
    }
    path = tmp_path / "repo" / "integrations" / "openviking" / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_plan_and_bundle_only_include_allowlisted_file(tmp_path: Path):
    source_root = tmp_path / "source"
    (source_root / "docs").mkdir(parents=True)
    (source_root / "docs" / "architecture.md").write_text("# Architecture\nSafe facts.\n")
    (source_root / ".env").write_text("SECRET=must-not-appear")
    manifest_path = _manifest(tmp_path)

    manifest, planned = plan_sources(
        manifest_path, environ={"TEST_SOURCE_ROOT": str(source_root)}
    )
    bundle, record = build_bundle(manifest, planned)

    assert len(planned) == 1
    assert record["sources"][0]["target"] == "system/architecture.md"
    with zipfile.ZipFile(BytesIO(bundle)) as archive:
        assert sorted(archive.namelist()) == ["_ingestion-record.json", "system/architecture.md"]
        assert "must-not-appear" not in archive.read("system/architecture.md").decode()


def test_missing_environment_variable_fails_closed(tmp_path: Path):
    manifest_path = _manifest(tmp_path)
    with pytest.raises(ManifestError, match="Missing required environment"):
        plan_sources(manifest_path, environ={})


def test_source_cannot_escape_declared_root(tmp_path: Path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (tmp_path / "outside.md").write_text("outside")
    manifest_path = _manifest(tmp_path, "../outside.md")
    with pytest.raises(ManifestError, match="escapes"):
        plan_sources(manifest_path, environ={"TEST_SOURCE_ROOT": str(source_root)})


@pytest.mark.parametrize(
    "content",
    [
        "-----BEGIN PRIVATE KEY-----\nsecret",
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456",
    ],
)
def test_high_confidence_secret_patterns_fail_closed(tmp_path: Path, content: str):
    source_root = tmp_path / "source"
    (source_root / "docs").mkdir(parents=True)
    (source_root / "docs" / "architecture.md").write_text(content)
    manifest_path = _manifest(tmp_path)
    with pytest.raises(ManifestError, match="secret-safety"):
        plan_sources(manifest_path, environ={"TEST_SOURCE_ROOT": str(source_root)})


def test_remote_or_credentialed_endpoint_is_rejected(tmp_path: Path):
    manifest_path = _manifest(tmp_path)
    data = json.loads(manifest_path.read_text())
    data["server"]["endpoint"] = "https://memory.example.com"
    manifest_path.write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="loopback"):
        plan_sources(manifest_path, environ={"TEST_SOURCE_ROOT": str(tmp_path)})


def test_unchanged_source_set_skips_reingestion(tmp_path: Path):
    source_root = tmp_path / "source"
    (source_root / "docs").mkdir(parents=True)
    source_file = source_root / "docs" / "architecture.md"
    source_file.write_text("# Architecture\nStable facts.\n")
    manifest_path = _manifest(tmp_path)
    manifest, planned = plan_sources(
        manifest_path, environ={"TEST_SOURCE_ROOT": str(source_root)}
    )
    digest = source_set_sha256(manifest, planned)
    record_path = tmp_path / "last-sync.json"
    record_path.write_text(json.dumps({"sourceSetSha256": digest, "indexedAt": "then"}))

    assert unchanged_sync(record_path, digest)["indexedAt"] == "then"

    source_file.write_text("# Architecture\nChanged facts.\n")
    _, changed = plan_sources(
        manifest_path, environ={"TEST_SOURCE_ROOT": str(source_root)}
    )
    assert unchanged_sync(record_path, source_set_sha256(manifest, changed)) is None


@pytest.mark.parametrize(
    "response",
    [
        {"result": [{"uri": "viking://resources/test"}]},
        {"result": {"items": [{"uri": "viking://resources/test"}]}},
    ],
)
def test_tree_content_accepts_supported_response_shapes(response):
    assert tree_has_content(response) is True


def test_tree_content_rejects_missing_or_empty_namespace():
    assert tree_has_content({"result": []}) is False
    assert tree_has_content({"status": "ok"}) is False
