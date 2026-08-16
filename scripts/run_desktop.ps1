$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run setup_windows.bat first."
}
if (-not (Test-Path "frontend\dist\index.html")) {
    throw "Frontend build not found. Run setup_windows.bat first."
}

$env:APP_MODE = "desktop"
$env:APP_ENV = "production"
& ".venv\Scripts\python.exe" "desktop\launcher.py"

