#!/bin/bash
set -euo pipefail

OPENVIKING_HOME="${OPENVIKING_HOME:-$HOME/.openviking}"
OPENVIKING_BIN="${OPENVIKING_BIN:-$HOME/.local/share/openviking/venv/bin/openviking-server}"
OPENVIKING_CONFIG="${OPENVIKING_CONFIG:-$OPENVIKING_HOME/ov.conf}"
OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
PID_FILE="$OPENVIKING_HOME/server.pid"
LOG_FILE="$OPENVIKING_HOME/logs/server.log"
BACKGROUND_ONLY="${1:-}"

# OpenViking expands environment variables in ov.conf. Reuse the protected
# Hermes secret store rather than writing a provider key into that config.
if [ -z "${DEEPSEEK_API_KEY:-}" ] && [ -r "$HOME/.hermes/.env" ]; then
  key_line="$(grep -m1 '^DEEPSEEK_API_KEY=' "$HOME/.hermes/.env" || true)"
  if [ -n "$key_line" ]; then
    DEEPSEEK_API_KEY="${key_line#DEEPSEEK_API_KEY=}"
    DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY%\"}"; DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY#\"}"
    DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY%\'}"; DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY#\'}"
    export DEEPSEEK_API_KEY
  fi
fi

if curl -fsS --max-time 3 "$OPENVIKING_URL/health" >/dev/null 2>&1; then
  echo "OpenViking already healthy: $OPENVIKING_URL/studio/"
  exit 0
fi

if [ ! -x "$OPENVIKING_BIN" ]; then
  echo "OpenViking executable is missing: $OPENVIKING_BIN" >&2
  exit 1
fi
if [ ! -r "$OPENVIKING_CONFIG" ]; then
  echo "OpenViking configuration is missing: $OPENVIKING_CONFIG" >&2
  exit 1
fi

mkdir -p "$OPENVIKING_HOME/logs"
if [ -s "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE")"
  if kill -0 "$old_pid" 2>/dev/null; then
    echo "OpenViking process $old_pid is alive but not healthy" >&2
    exit 1
  fi
fi

nohup "$OPENVIKING_BIN" --config "$OPENVIKING_CONFIG" \
  >>"$LOG_FILE" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$PID_FILE"

if [ "$BACKGROUND_ONLY" = "--background" ]; then
  echo "OpenViking starting in background (pid $pid)"
  exit 0
fi

# A cold local-embedding start has taken roughly 72 seconds on this machine.
for _ in {1..120}; do
  if curl -fsS --max-time 3 "$OPENVIKING_URL/health" >/dev/null 2>&1; then
    echo "OpenViking healthy: $OPENVIKING_URL/studio/"
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "OpenViking exited during startup; see $LOG_FILE" >&2
    exit 1
  fi
  sleep 1
done

echo "OpenViking did not become healthy within 120 seconds; see $LOG_FILE" >&2
exit 1
