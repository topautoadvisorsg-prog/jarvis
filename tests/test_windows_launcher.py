from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (REPO_ROOT / "windows" / "Start-Jarvis-HUD.ps1").read_text(encoding="utf-8")


def test_windows_launcher_uses_the_supervised_repository_start_path():
    assert "scripts/jarvis-start.sh" in LAUNCHER
    assert ".venv/bin/python server.py" not in LAUNCHER
    assert "server/scripts/jarvis-health.sh" in LAUNCHER


def test_windows_launcher_restores_the_loopback_dashboard():
    assert "http://127.0.0.1:9119/" in LAUNCHER
    assert "tmux new-session -d -s hermes-dashboard" in LAUNCHER
    assert "--host 127.0.0.1" in LAUNCHER


def test_windows_launcher_contains_no_credentials():
    lowered = LAUNCHER.lower()
    assert "api_server_key=" not in lowered
    assert "openai_api_key=" not in lowered
    assert "deepseek_api_key=" not in lowered
