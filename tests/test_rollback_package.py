import hashlib
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "server" / "scripts" / "build-rollback-package.py"
SPEC = importlib.util.spec_from_file_location("rollback_package", SCRIPT)
rollback_package = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(rollback_package)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "server/config").mkdir(parents=True)
    (repo / "server/hud/assets").mkdir(parents=True)
    (repo / "server/scripts").mkdir(parents=True)
    (repo / "server/config/server.example.yaml").write_text("server:\n  port: 8765\n", encoding="utf-8")
    (repo / "server/hud/assets/face.png").write_bytes(b"synthetic-face")
    (repo / "server/scripts/start.sh").write_text("#!/bin/sh\necho ready\n", encoding="utf-8")
    (repo / "README.md").write_text("Jarvis\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Rollback Test")
    _git(repo, "config", "user.email", "rollback@example.test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")
    return repo


def test_build_is_reproducible_and_excludes_local_secrets(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / ".env").write_text("API_KEY=never-package-this\n", encoding="utf-8")
    (repo / "server/config/server.yaml").write_text("secret: never-package-this\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".env\nserver/config/server.yaml\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "ignore local state")

    output = tmp_path / "out"
    archive, checksum = rollback_package.build_package(repo, output)
    first_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive_again, _ = rollback_package.build_package(repo, output)
    assert hashlib.sha256(archive_again.read_bytes()).hexdigest() == first_hash
    assert checksum.read_text(encoding="utf-8").startswith(first_hash)

    manifest = rollback_package.verify_package(archive)
    assert manifest["tracked_file_count"] == 5
    assert manifest["assets"][0]["sha256"] == hashlib.sha256(b"synthetic-face").hexdigest()
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert not any(name.endswith("/.env") for name in names)
        assert not any(name.endswith("/server/config/server.yaml") for name in names)
        assert any(name.endswith("/server/config/server.example.yaml") for name in names)
        assert any(name.endswith("/ROLLBACK-MANIFEST.json") for name in names)
        restore = bundle.read(next(name for name in names if name.endswith("/RESTORE.md"))).decode()
        assert "Do not overlay a running checkout" in restore
        assert "prototype avatar notice" in restore
        assert "never-package-this" not in json.dumps(manifest)


def test_build_refuses_a_dirty_tree(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    try:
        rollback_package.build_package(repo, tmp_path / "out")
    except RuntimeError as error:
        assert "working tree must be clean" in str(error)
    else:
        raise AssertionError("dirty working tree was packaged")


def test_forbidden_tracked_runtime_paths_fail_closed(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / "server/logs").mkdir()
    (repo / "server/logs/session.json").write_text("private", encoding="utf-8")
    _git(repo, "add", "-f", "server/logs/session.json")
    _git(repo, "commit", "-q", "-m", "bad tracked state")
    try:
        rollback_package.build_package(repo, tmp_path / "out")
    except RuntimeError as error:
        assert "forbidden tracked path" in str(error)
    else:
        raise AssertionError("tracked runtime state was packaged")


def test_environment_and_live_config_variants_are_forbidden():
    assert rollback_package._is_forbidden(".env.production")
    assert rollback_package._is_forbidden("service.env")
    assert rollback_package._is_forbidden("server/config/server.prod.yaml")
    assert not rollback_package._is_forbidden("server/config/server.example.yaml")
