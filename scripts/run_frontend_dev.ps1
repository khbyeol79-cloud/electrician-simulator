$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Start the backend in another terminal with run_web.bat."
Write-Host "The Vite development server proxies /api to http://127.0.0.1:8000."
Push-Location "frontend"
try {
    & npm run dev
}
finally {
    Pop-Location
}

