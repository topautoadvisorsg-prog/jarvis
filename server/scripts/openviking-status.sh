#!/bin/bash
set -euo pipefail

OPENVIKING_HOME="${OPENVIKING_HOME:-$HOME/.openviking}"
OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
PID_FILE="$OPENVIKING_HOME/server.pid"

if health="$(curl -fsS --max-time 5 "$OPENVIKING_URL/health" 2>/dev/null)"; then
  printf 'OpenViking healthy: %s\n%s\n' "$OPENVIKING_URL/studio/" "$health"
  exit 0
fi

if [ -s "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "OpenViking process is starting or unhealthy (pid $(cat "$PID_FILE"))" >&2
else
  echo "OpenViking is stopped" >&2
fi
exit 1
