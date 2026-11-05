# Load .env into the current PowerShell session without printing any value.
# Usage (note the leading dot):   . .\scripts\load-env.ps1
$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) { Write-Error ".env not found: copy .env.example to .env first"; return }
$count = 0
foreach ($line in Get-Content $envFile -Encoding UTF8) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $name, $value = $line -split '=', 2
    Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
    $count++
}
Write-Host "Loaded $count variables from .env (values not shown)."
