# Jarvis local runtime supervision

Date: 2026-09-30

## Purpose

The WSL/Linux HUD process runs inside the existing `jarvis-hud` tmux session
through `server/scripts/jarvis-supervise.sh`. This is a local reliability layer,
not another agent or orchestration service.

The supervisor provides:

- at most five crash restarts in a ten-minute window;
- incremental restart delays capped at 30 seconds;
- atomic, machine-readable status in
  `server/run/jarvis-supervisor.json`;
- rotation of `server/logs/server.log` at 5 MiB with three old files retained,
  checked every 30 seconds while the process runs;
- forwarding of stop signals to the HUD process;
- a final `failed` state when the restart limit is reached.

The status file contains only state, reason, restart count, process ID, and UTC
update time. Runtime state and logs stay ignored by Git.

## Normal operation

From the `server` directory:

```bash
scripts/jarvis-start.sh
scripts/jarvis-health.sh
scripts/jarvis-restart.sh
scripts/jarvis-stop.sh
```

On WSL/Linux, `jarvis-start.sh` waits up to 30 seconds for the HUD API. If the
service never becomes healthy, it exits unsuccessfully and prints the safe
supervisor status plus the local log path. It does not print log contents or
credentials.

macOS continues to use the existing launchd services. Windows-native service
packaging remains a later commercial-distribution task.

The Windows desktop `JARVIS HUD` shortcut now invokes the tracked
`windows/Start-Jarvis-HUD.ps1` launcher. That launcher calls the same
`server/scripts/jarvis-start.sh` path instead of starting `server.py` directly,
then restores the loopback Hermes dashboard if needed. This keeps shortcut and
terminal startup on the same supervised runtime path.

## Acceptance evidence

The supervisor was checked with an isolated process that exited immediately:

- one allowed restart produced exactly two attempts;
- the final state was `failed`;
- the exit reason and count were recorded;
- an oversized log rotated to `server.log.1`;
- no partial temporary status file remained.

Live acceptance must also prove that killing only the HUD child produces a new
child process, restores `/api/config-summary`, and increments `restartCount`
without restarting the Hermes gateway.

That acceptance passed on 2026-09-30. The HUD child changed from PID 13944 to
14007, the supervisor returned to `running` with `restartCount: 1`, the API
became healthy again, and the Hermes gateway remained on PID 10783. The normal
launcher was then restarted to clear the intentional test restart count.
