#!/usr/bin/env bash
set -euo pipefail

# Hermes runs in WSL while the supported Cua Driver runs in the interactive
# Windows session. Hermes creates a Unix-looking private socket name and passes
# Linux manifest paths; translate those two boundary values for the Windows
# process. All other arguments are forwarded byte-for-byte.
self="$(readlink -f "$0")"

if [[ -n "${HERMES_CUA_DRIVER_WINDOWS_EXE:-}" ]]; then
  driver="$HERMES_CUA_DRIVER_WINDOWS_EXE"
else
  # Keep stdin reserved for MCP JSON-RPC. Without /dev/null, cmd.exe can
  # consume the first request before the driver process starts.
  windows_local_app_data="$(cmd.exe /d /c 'echo %LOCALAPPDATA%' </dev/null 2>/dev/null | tr -d '\r')"
  driver="$(wslpath -u "$windows_local_app_data")/Programs/Cua/cua-driver/bin/cua-driver.exe"
fi

if [[ ! -x "$driver" ]]; then
  printf 'cua-driver Windows executable not found: %s\n' "$driver" >&2
  exit 127
fi

# Hermes asks the binary for its MCP launch command before starting the
# private runtime. The Windows driver reports its real .exe path, which would
# bypass this adapter on the next hop and lose the socket/path translations.
# Keep the driver's signed manifest intact except for pointing MCP back through
# this wrapper.
if [[ "${1:-}" == "manifest" ]]; then
  manifest_json="$("$driver" "$@")"
  WRAPPER_PATH="$self" python3 -c '
import json
import os
import sys

manifest = json.load(sys.stdin)
manifest["mcp_invocation"]["command"] = os.environ["WRAPPER_PATH"]
json.dump(manifest, sys.stdout, indent=2)
sys.stdout.write("\n")
' <<<"$manifest_json"
  exit 0
fi

args=()
while (($#)); do
  case "$1" in
    --socket)
      if (($# < 2)); then
        printf '%s\n' 'missing value for --socket' >&2
        exit 2
      fi
      socket="$2"
      if [[ "$socket" == /* ]]; then
        name="$(basename "$socket")"
        name="${name%.sock}"
        socket="\\\\.\\pipe\\${name}"
      fi
      args+=("--socket" "$socket")
      shift 2
      ;;
    --capability-manifest|--session-policy)
      flag="$1"
      if (($# < 2)); then
        printf 'missing value for %s\n' "$flag" >&2
        exit 2
      fi
      manifest="$2"
      if [[ "$manifest" == /* ]]; then
        manifest="$(wslpath -w "$manifest")"
      fi
      args+=("$flag" "$manifest")
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

exec "$driver" "${args[@]}"
