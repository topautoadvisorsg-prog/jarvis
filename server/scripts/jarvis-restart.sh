#!/bin/bash
set -e
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
bash "$SCRIPT_DIR/jarvis-stop.sh"
sleep 2
bash "$SCRIPT_DIR/jarvis-start.sh"
