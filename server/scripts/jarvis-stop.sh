#!/bin/bash
if command -v launchctl >/dev/null 2>&1; then
  U=gui/$(id -u)
  for s in com.jarvis.voice com.jarvis.dashboard; do launchctl bootout "$U/$s" 2>/dev/null; done
else
  tmux kill-session -t jarvis-hud 2>/dev/null || true
fi
sleep 1
# kill anything still holding our ports (catches orphaned STT children whose
# cmdline doesn't contain "server.py")
for port in 443 8765 8766 9443; do
  lsof -ti tcp:$port -sTCP:LISTEN 2>/dev/null | xargs -r kill -9 2>/dev/null
done
pkill -9 -if "server\.py" 2>/dev/null
echo "HUD stopped (Hermes gateway left running)"
