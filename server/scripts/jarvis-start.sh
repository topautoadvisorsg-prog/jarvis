#!/bin/bash
set -u

if command -v launchctl >/dev/null 2>&1; then
  U=gui/$(id -u)
  for s in com.jarvis.voice com.jarvis.dashboard; do
    launchctl bootstrap "$U" "$HOME/Library/LaunchAgents/$s.plist" 2>/dev/null || launchctl kickstart "$U/$s"
  done
else
  # Linux / WSL: keep services in named tmux sessions. The HUD session runs a
  # bounded supervisor so a crash cannot create an endless restart loop.
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required for supervised Jarvis startup on Linux/WSL." >&2
    exit 1
  fi
  SERVER_DIR=$(cd "$(dirname "$0")/.." && pwd)
  if [ -x "$HOME/.local/share/openviking/venv/bin/openviking-server" ] && \
     [ -r "$HOME/.openviking/ov.conf" ]; then
    "$SERVER_DIR/scripts/openviking-start.sh" --background || \
      echo "warning: OpenViking did not start; Jarvis will continue without it" >&2
  fi
  # A healthy gateway may require time to finish loading after its port opens.
  # Do not kill an existing/warming gateway merely because one HTTP probe was
  # early; only create the tmux service when nothing is listening on 8642.
  if ! ss -ltn 2>/dev/null | grep -q ':8642 '; then
    tmux kill-session -t hermes-gateway 2>/dev/null || true
    tmux new-session -d -s hermes-gateway "exec hermes gateway run"
  fi
  gateway_healthy=0
  for _ in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8642/health 2>/dev/null | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
      gateway_healthy=1
      break
    fi
    sleep 1
  done
  if [ "$gateway_healthy" -ne 1 ]; then
    echo "Hermes API did not become healthy within 60 seconds." >&2
    echo "Inspect $HOME/.hermes/logs/jarvis-gateway.log locally for details." >&2
    exit 1
  fi
  if ! curl -fsS http://127.0.0.1:8765/api/config-summary >/dev/null 2>&1; then
    tmux kill-session -t jarvis-hud 2>/dev/null || true
    tmux new-session -d -s jarvis-hud "exec '$SERVER_DIR/scripts/jarvis-supervise.sh'"
    healthy=0
    for _ in $(seq 1 30); do
      if curl -fsS http://127.0.0.1:8765/api/config-summary >/dev/null 2>&1; then
        healthy=1
        break
      fi
      sleep 1
    done
    if [ "$healthy" -ne 1 ]; then
      echo "Jarvis HUD did not become healthy within 30 seconds." >&2
      if [ -r "$SERVER_DIR/run/jarvis-supervisor.json" ]; then
        echo "Supervisor status:" >&2
        cat "$SERVER_DIR/run/jarvis-supervisor.json" >&2
      fi
      echo "Inspect $SERVER_DIR/logs/server.log locally for details." >&2
      exit 1
    fi
  fi
fi
echo "started (voice server may warm its STT model on first use)"
