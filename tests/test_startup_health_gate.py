from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STARTER = (REPO_ROOT / "server" / "scripts" / "jarvis-start.sh").read_text(encoding="utf-8")


def test_existing_gateway_is_not_restarted_on_one_early_http_probe():
    assert "ss -ltn" in STARTER
    assert "grep -q ':8642 '" in STARTER
    gateway_block = STARTER.split("tmux new-session -d -s hermes-gateway", 1)[0]
    assert "curl -fsS http://127.0.0.1:8642/health" not in gateway_block


def test_startup_waits_for_hermes_health_before_starting_the_hud():
    assert "gateway_healthy=0" in STARTER
    assert "Hermes API did not become healthy within 60 seconds" in STARTER
    health_gate = STARTER.index('grep -q \'"status"[[:space:]]*:[[:space:]]*"ok"\'')
    hud_start = STARTER.index("tmux new-session -d -s jarvis-hud")
    assert health_gate < hud_start
