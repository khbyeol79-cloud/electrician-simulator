param([switch]$Lan)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run setup_windows.bat first."
}
if (-not (Test-Path "frontend\dist\index.html")) {
    throw "Frontend build not found. Run setup_windows.bat first."
}

$env:APP_MODE = "web"
$env:APP_ENV = "production"
$env:APP_PORT = "8000"
if ($Lan) {
    $env:ALLOW_LAN = "true"
    $env:APP_HOST = "0.0.0.0"
    Write-Host "LAN mode enabled. Review Windows Firewall settings before allowing access."
} else {
    $env:ALLOW_LAN = "false"
    $env:APP_HOST = "127.0.0.1"
}

Write-Host "Open http://127.0.0.1:8000 in your browser."
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host $env:APP_HOST --port 8000

