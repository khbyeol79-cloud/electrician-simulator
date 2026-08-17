$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run setup_windows.bat first."
}

Write-Host "Running Python tests..."
& ".venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { throw "Python tests failed." }

Write-Host "Validating problem packages..."
& ".venv\Scripts\python.exe" "scripts\validate_problems.py"
if ($LASTEXITCODE -ne 0) { throw "Problem validation failed." }

Write-Host "Running frontend tests..."
Push-Location "frontend"
try {
    & npm test
    if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
}
finally {
    Pop-Location
}

Write-Host "All tests and builds passed."
