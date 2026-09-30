#!/bin/bash
# Bounded WSL/Linux supervisor for the Jarvis HUD server.
# Keeps status and rotated logs local; it never reads or writes credentials.
set -u

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${JARVIS_SUPERVISOR_STATE_DIR:-$SERVER_DIR/run}"
STATUS_FILE="$STATE_DIR/jarvis-supervisor.json"
LOG_FILE="${JARVIS_SUPERVISOR_LOG_FILE:-$SERVER_DIR/logs/server.log}"
SERVER_EXECUTABLE="${JARVIS_SUPERVISOR_EXECUTABLE:-$SERVER_DIR/.venv/bin/python}"
SERVER_ARGUMENT="${JARVIS_SUPERVISOR_ARGUMENT-$SERVER_DIR/server.py}"
MAX_RESTARTS="${JARVIS_SUPERVISOR_MAX_RESTARTS:-5}"
WINDOW_SECONDS="${JARVIS_SUPERVISOR_WINDOW_SECONDS:-600}"
BACKOFF_SECONDS="${JARVIS_SUPERVISOR_BACKOFF_SECONDS:-2}"
MAX_LOG_BYTES="${JARVIS_SUPERVISOR_MAX_LOG_BYTES:-5242880}"
LOG_KEEP="${JARVIS_SUPERVISOR_LOG_KEEP:-3}"
LOG_CHECK_SECONDS="${JARVIS_SUPERVISOR_LOG_CHECK_SECONDS:-30}"

require_uint() {
  case "$2" in
    ''|*[!0-9]*) echo "invalid $1: expected a non-negative integer" >&2; exit 2 ;;
  esac
}

require_uint JARVIS_SUPERVISOR_MAX_RESTARTS "$MAX_RESTARTS"
require_uint JARVIS_SUPERVISOR_WINDOW_SECONDS "$WINDOW_SECONDS"
require_uint JARVIS_SUPERVISOR_BACKOFF_SECONDS "$BACKOFF_SECONDS"
require_uint JARVIS_SUPERVISOR_MAX_LOG_BYTES "$MAX_LOG_BYTES"
require_uint JARVIS_SUPERVISOR_LOG_KEEP "$LOG_KEEP"
require_uint JARVIS_SUPERVISOR_LOG_CHECK_SECONDS "$LOG_CHECK_SECONDS"
if [ "$MAX_RESTARTS" -lt 1 ] || [ "$WINDOW_SECONDS" -lt 1 ] || \
   [ "$LOG_KEEP" -lt 1 ] || [ "$LOG_CHECK_SECONDS" -lt 1 ]; then
  echo "restart count, window, log count, and log interval must be at least 1" >&2
  exit 2
fi
if [ ! -x "$SERVER_EXECUTABLE" ]; then
  echo "Jarvis server executable is unavailable: $SERVER_EXECUTABLE" >&2
  exit 2
fi

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

write_status() {
  local state="$1" reason="$2" restarts="$3" pid="${4:-}"
  local tmp="$STATUS_FILE.tmp.$$"
  python3 - "$tmp" "$state" "$reason" "$restarts" "$pid" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

path, state, reason, restarts, pid = sys.argv[1:]
payload = {
    "state": state,
    "reason": reason,
    "restartCount": int(restarts),
    "pid": int(pid) if pid else None,
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, separators=(",", ":"))
    handle.write("\n")
os.replace(path, path.rsplit(".tmp.", 1)[0])
PY
}

rotate_log() {
  [ -f "$LOG_FILE" ] || return 0
  local size i previous
  size="$(wc -c < "$LOG_FILE" 2>/dev/null || printf 0)"
  [ "$size" -lt "$MAX_LOG_BYTES" ] && return 0
  i="$LOG_KEEP"
  while [ "$i" -gt 1 ]; do
    previous=$((i - 1))
    [ ! -f "$LOG_FILE.$previous" ] || mv -f "$LOG_FILE.$previous" "$LOG_FILE.$i"
    i="$previous"
  done
  # Copy/truncate keeps the server's open file descriptor on the active log.
  cp -f "$LOG_FILE" "$LOG_FILE.1"
  : > "$LOG_FILE"
}

monitor_log() {
  local monitored_pid="$1"
  while kill -0 "$monitored_pid" 2>/dev/null; do
    sleep "$LOG_CHECK_SECONDS"
    rotate_log
  done
}

stop_requested=0
child_pid=""
request_stop() {
  stop_requested=1
  if [ -n "$child_pid" ]; then
    kill -TERM "$child_pid" 2>/dev/null || true
  fi
}
trap request_stop INT TERM HUP

restart_count=0
window_started="$(date +%s)"
write_status starting "supervisor initialized" "$restart_count"

while :; do
  rotate_log
  if [ -n "$SERVER_ARGUMENT" ]; then
    "$SERVER_EXECUTABLE" "$SERVER_ARGUMENT" >> "$LOG_FILE" 2>&1 &
  else
    "$SERVER_EXECUTABLE" >> "$LOG_FILE" 2>&1 &
  fi
  child_pid=$!
  write_status running "server process active" "$restart_count" "$child_pid"

  monitor_log "$child_pid" &
  monitor_pid=$!
  wait "$child_pid"
  exit_code=$?
  kill "$monitor_pid" 2>/dev/null || true
  wait "$monitor_pid" 2>/dev/null || true
  child_pid=""
  if [ "$stop_requested" -eq 1 ]; then
    write_status stopped "operator stop" "$restart_count"
    exit 0
  fi

  now="$(date +%s)"
  if [ $((now - window_started)) -ge "$WINDOW_SECONDS" ]; then
    restart_count=0
    window_started="$now"
  fi
  restart_count=$((restart_count + 1))
  if [ "$restart_count" -gt "$MAX_RESTARTS" ]; then
    write_status failed "restart limit reached after exit $exit_code" "$restart_count"
    [ "$exit_code" -ne 0 ] || exit_code=1
    exit "$exit_code"
  fi

  delay=$((BACKOFF_SECONDS * restart_count))
  [ "$delay" -le 30 ] || delay=30
  write_status restarting "server exited $exit_code; retrying in ${delay}s" "$restart_count"
  sleep "$delay" &
  backoff_pid=$!
  wait "$backoff_pid"
  kill "$backoff_pid" 2>/dev/null || true
  if [ "$stop_requested" -eq 1 ]; then
    write_status stopped "operator stop" "$restart_count"
    exit 0
  fi
done
