# Jarvis computer and screen control

Date: 2026-09-30

## Current capability

`jarvis-main` has an installed Cua Driver on the interactive Windows host and a
deny-by-default, read-only capability manifest. This first stage gives Jarvis
eyes only:

- list running/installed applications;
- list visible top-level windows;
- read the primary screen dimensions;
- capture the primary display;
- run driver health and permission diagnostics.

The manifest does not admit mouse, keyboard, focus, launch, clipboard, browser
mutation, file transfer, recording, replay, process control, or configuration
tools. Calls to omitted tools fail inside the native driver even if a model asks
for them. Full-display capture is intentionally allowed because Buddy asked
Jarvis to understand what is on screen; screenshots can contain sensitive
information and should stay in the active session unless Buddy asks to save or
share one.

## Runtime architecture

```text
jarvis-main in WSL
  -> Hermes computer_use tool
  -> scripts/cua-driver-wsl-wrapper.sh
       - maps Hermes's private Unix socket label to a Windows named pipe
       - maps the reviewed WSL manifest path to its Windows path
  -> Cua Driver private bounded runtime in the interactive Windows session
  -> config/cua-read-only.yaml
```

Hermes owns a private driver runtime for each active computer-use session. The
runtime expires after 24 hours and after 30 minutes idle. Telemetry is disabled.
The driver is not run in unrestricted mode.

## Operational configuration

The live Hermes configuration uses:

```yaml
toolsets:
  - hermes-cli
  - computer_use

computer_use:
  permission_mode: bounded
  capability_manifest: /home/jovan/.hermes/jarvis-hud/config/cua-read-only.yaml
  cua_telemetry: false
  max_image_dimension: 1456
  no_overlay: true
```

`HERMES_CUA_DRIVER_CMD` points to the checked-in WSL wrapper. The Windows
installer created an elevated logon task. An unelevated process cannot remove
that task, so user-level launch variables force the task into the same bounded
read-only manifest if Windows starts it after login. Removing the unused task is
a later administrator housekeeping action; it is not required for the private
Hermes runtime.

## Use and acceptance

For this stage, Jarvis should use `computer_use` only with `list_apps`,
`list_windows`, or `capture` with `app: screen`. A successful acceptance run
must prove:

1. Windows driver health is `ok`.
2. Hermes can list Windows applications/windows.
3. Hermes can capture the primary display.
4. A native action such as `click` is denied with `permission_denied`.
5. No cursor, focus, text, process, browser, or file state changes during the
   test.

## Next expansion

Do not broaden this manifest globally. When Buddy chooses a real workflow,
create a second capability manifest naming the exact non-browser application
executable and only the minimum required actions. Keep browser work in Hermes's
dedicated browser tool with explicit origin scope. Sending, submitting,
purchasing, deleting, publishing, security changes, and production actions keep
their Buddy approval boundary.
