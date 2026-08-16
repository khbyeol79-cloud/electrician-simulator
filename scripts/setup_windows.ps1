param([switch]$RebuildFrontend)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogFile = Join-Path $ProjectRoot "setup.log"
$TranscriptStarted = $false
$ExitCode = 0
Set-Location $ProjectRoot

try {
    Start-Transcript -Path $LogFile -Force | Out-Null
    $TranscriptStarted = $true

    function Test-PythonCandidate {
        param(
            [string]$Executable,
            [string[]]$Prefix
        )

        $PreviousErrorActionPreference = $ErrorActionPreference
        try {
            # Windows PowerShell 5.1 converts py.exe probe errors into
            # terminating errors when ErrorActionPreference is Stop.
            # Candidate checks must therefore run with Continue temporarily.
            $ErrorActionPreference = "Continue"
            & $Executable @Prefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            return ($LASTEXITCODE -eq 0)
        }
        catch {
            return $false
        }
        finally {
            $ErrorActionPreference = $PreviousErrorActionPreference
        }
    }

    function Resolve-PythonCommand {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            if (Test-PythonCandidate -Executable "py" -Prefix @("-3")) {
                return @("py", "-3")
            }
        }

        if (Get-Command python -ErrorAction SilentlyContinue) {
            if (Test-PythonCandidate -Executable "python" -Prefix @()) {
                return @("python")
            }
        }

        throw "Python 3.11 or newer was not found. Install 64-bit Python 3.11+ and run setup_windows.bat again."
    }

    $PythonCommand = @(Resolve-PythonCommand)
    $PythonExecutable = $PythonCommand[0]
    $PythonPrefix = @()
    if ($PythonCommand.Count -gt 1) {
        $PythonPrefix = @($PythonCommand[1..($PythonCommand.Count - 1)])
    }

    function Invoke-SelectedPython {
        param([string[]]$Arguments)
        & $PythonExecutable @PythonPrefix @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Python command failed with exit code $LASTEXITCODE."
        }
    }

    Write-Host "[1/5] Checking Python..."
    Invoke-SelectedPython -Arguments @("-c", "import sys; print(sys.version)")

    Write-Host "[2/5] Creating Python virtual environment..."
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Invoke-SelectedPython -Arguments @("-m", "venv", ".venv")
    }

    Write-Host "[3/5] Updating pip..."
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip update failed. Check the internet connection or setup.log."
    }

    Write-Host "[4/5] Installing Python packages..."
    & ".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        throw "Python package installation failed. Check the internet connection or setup.log."
    }

    $FrontendReady = Test-Path "frontend\dist\index.html"
    if ($FrontendReady -and -not $RebuildFrontend) {
        Write-Host "[5/5] Prebuilt frontend found. Node.js installation is not required."
    }
    else {
        Write-Host "[5/5] Building React frontend..."
        if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
            throw "Node.js 20+ is required only when rebuilding the frontend. Run without -RebuildFrontend or install Node.js 20+."
        }
        & node -e "const major=Number(process.versions.node.split('.')[0]); if(major<20) process.exit(1); console.log(process.version)"
        if ($LASTEXITCODE -ne 0) {
            throw "Node.js 20 or newer is required to rebuild the frontend."
        }

        Push-Location "frontend"
        try {
            if (Test-Path "package-lock.json") {
                & npm ci
            }
            else {
                & npm install
            }
            if ($LASTEXITCODE -ne 0) {
                throw "npm package installation failed."
            }

            & npm run build
            if ($LASTEXITCODE -ne 0) {
                throw "React build failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    Write-Host ""
    Write-Host "Setup completed successfully." -ForegroundColor Green
    Write-Host "Desktop: run_desktop.bat"
    Write-Host "Web:     run_web.bat"
}
catch {
    $ExitCode = 1
    Write-Host ""
    Write-Host "SETUP FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Detailed log: $LogFile" -ForegroundColor Yellow
}
finally {
    if ($TranscriptStarted) {
        Stop-Transcript | Out-Null
    }
}

exit $ExitCode
