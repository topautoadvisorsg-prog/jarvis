#!/bin/bash
set -euo pipefail

OPENVIKING_HOME="${OPENVIKING_HOME:-$HOME/.openviking}"
PID_FILE="$OPENVIKING_HOME/server.pid"

if [ ! -s "$PID_FILE" ]; then
  echo "OpenViking is not running"
  exit 0
fi

pid="$(cat "$PID_FILE")"
if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Removed stale OpenViking pid file"
  exit 0
fi

command_line="$(tr '\0' ' ' </proc/"$pid"/cmdline 2>/dev/null || true)"
case "$command_line" in
  *openviking-server*) ;;
  *) echo "Refusing to stop pid $pid because it is not OpenViking" >&2; exit 1 ;;
esac

kill "$pid"
for _ in {1..40}; do
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.25
done
if kill -0 "$pid" 2>/dev/null; then
  echo "OpenViking did not stop cleanly (pid $pid)" >&2
  exit 1
fi
rm -f "$PID_FILE"
echo "OpenViking stopped"
