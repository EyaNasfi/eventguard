# Start the whole lab with the current git commit recorded in the gateway's tool-call log (S2-05).
# Usage, from the repo root:   .\scripts\lab-up.ps1            (add -Dev to publish EventSim on 127.0.0.1:8000)
param([switch]$Dev)
$env:EVENTGUARD_GIT_COMMIT = (git rev-parse --short HEAD)
$files = @("-f", "docker-compose.yml")
if ($Dev) { $files += @("-f", "docker-compose.dev.yml") }
docker compose @files up -d --build --wait
Write-Host "Lab up at commit $env:EVENTGUARD_GIT_COMMIT. n8n: http://localhost:5678"
