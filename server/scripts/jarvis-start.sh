#!/bin/bash
set -u

if command -v launchctl >/dev/null 2>&1; then
  U=gui/$(id -u)
  for s in com.jarvis.voice com.jarvis.dashboard; do
    launchctl bootstrap "$U" "$HOME/Library/LaunchAgents/$s.plist" 2>/dev/null || launchctl kickstart "$U/$s"
  done
else
  # Linux / WSL: keep both services alive in named tmux sessions. Hermes must
  # be restored as well as the HUD or GPT-Live client delegation has no agent.
  if ! curl -fsS http://127.0.0.1:8642/health >/dev/null 2>&1; then
    tmux kill-session -t hermes-gateway 2>/dev/null || true
    tmux new-session -d -s hermes-gateway "exec hermes gateway run"
  fi
  if ! curl -fsS http://127.0.0.1:8765/api/config-summary >/dev/null 2>&1; then
    tmux kill-session -t jarvis-hud 2>/dev/null || true
    SERVER_DIR=$(cd "$(dirname "$0")/.." && pwd)
    tmux new-session -d -s jarvis-hud "cd '$SERVER_DIR' && exec .venv/bin/python server.py >> logs/server.log 2>&1"
  fi
fi
echo "started (voice server may warm its STT model on first use)"
