$ErrorActionPreference = 'Stop'

$distro = 'Ubuntu'
$hudUrl = 'http://127.0.0.1:8765/hud/'
$dashboardUrl = 'http://127.0.0.1:9119/'

function Invoke-Wsl([string]$command) {
    & wsl.exe -d $distro -- bash -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "WSL command failed: $command"
    }
}

# Use the repository launcher so the HUD always runs through the bounded
# supervisor and starts its optional local dependencies consistently.
Invoke-Wsl @'
cd ~/.hermes/jarvis-hud/server
scripts/jarvis-start.sh
if ! curl -fsS http://127.0.0.1:9119/ >/dev/null 2>&1; then
  tmux kill-session -t hermes-dashboard 2>/dev/null || true
  tmux new-session -d -s hermes-dashboard 'exec ~/.hermes/hermes-agent/venv/bin/hermes dashboard --host 127.0.0.1 --port 9119 --no-open --skip-build >> ~/.hermes/logs/jarvis-dashboard.log 2>&1'
fi
'@

function Wait-LocalHttp([string]$url, [string]$name) {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1
            if ($response.StatusCode -eq 200) { return }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "$name did not become ready. Run server/scripts/jarvis-health.sh and inspect local logs."
}

Wait-LocalHttp $hudUrl 'JARVIS HUD'
Wait-LocalHttp $dashboardUrl 'Hermes dashboard'

$edgeCandidates = @(
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$edge = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($edge) {
    Start-Process -FilePath $edge -ArgumentList "--app=$hudUrl", '--start-maximized'
} else {
    Start-Process $hudUrl
}
