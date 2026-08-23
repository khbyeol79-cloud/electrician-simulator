param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$OutputZip = ""
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path $ProjectRoot).Path

if ([string]::IsNullOrWhiteSpace($OutputZip)) {
    $parent = Split-Path $root -Parent
    $OutputZip = Join-Path $parent "electrician-simulator-current-full-source.zip"
}

$required = @(
    "backend",
    "frontend",
    "problems",
    "catalog"
)

Write-Host ""
Write-Host "전기기능사 시퀀스 회로 시뮬레이터 전체 소스 수집" -ForegroundColor Cyan
Write-Host "프로젝트: $root"
Write-Host "출력 ZIP : $OutputZip"
Write-Host ""

foreach ($item in $required) {
    $path = Join-Path $root $item
    if (-not (Test-Path $path)) {
        throw "필수 경로가 없습니다: $path"
    }
}

$important = @(
    "backend\app\main.py",
    "frontend\src",
    "problems",
    "catalog"
)

Write-Host "[핵심 원본 확인]"
foreach ($rel in $important) {
    $path = Join-Path $root $rel
    if (Test-Path $path) {
        Write-Host "  PASS  $rel" -ForegroundColor Green
    } else {
        Write-Host "  WARN  $rel 없음" -ForegroundColor Yellow
    }
}

# 원본 프로젝트를 건드리지 않기 위해 임시 폴더에 필요한 파일만 복사한다.
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("electrician-full-source-" + [guid]::NewGuid().ToString("N"))
$stage = Join-Path $tempRoot (Split-Path $root -Leaf)

New-Item -ItemType Directory -Force -Path $stage | Out-Null

$excludedDirs = @(
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode"
)

$excludedExtensions = @(
    ".pyc",
    ".pyo",
    ".log",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip",
    ".7z",
    ".rar"
)

$excludedNames = @(
    "Thumbs.db",
    ".DS_Store"
)

Write-Host ""
Write-Host "[파일 수집 중]" -ForegroundColor Cyan

$files = Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object {
    $full = $_.FullName
    $relative = $full.Substring($root.Length).TrimStart('\','/')

    $parts = $relative -split '[\\/]'

    $dirExcluded = $false
    foreach ($part in $parts) {
        if ($excludedDirs -contains $part) {
            $dirExcluded = $true
            break
        }
    }

    if ($dirExcluded) { return $false }
    if ($excludedExtensions -contains $_.Extension.ToLowerInvariant()) { return $false }
    if ($excludedNames -contains $_.Name) { return $false }

    return $true
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($root.Length).TrimStart('\','/')
    $dest = Join-Path $stage $relative
    $destDir = Split-Path $dest -Parent
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
}

# 어떤 핵심 파일이 들어갔는지 간단한 수집 보고서를 같이 넣는다.
$report = @()
$report += "# Electrician Simulator Full Source Collection"
$report += ""
$report += "Project root: $root"
$report += "Collected at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
$report += "File count: $($files.Count)"
$report += ""
$report += "## Important paths"
$checkPaths = @(
    "backend\app\main.py",
    "backend\app\services",
    "backend\app\repositories",
    "frontend\src",
    "frontend\src\features\wiring",
    "frontend\src\features\wiring\components\WiringBoard.tsx",
    "frontend\dist",
    "problems",
    "catalog",
    "schemas",
    "scripts",
    "tests"
)
foreach ($rel in $checkPaths) {
    $p = Join-Path $stage $rel
    $status = if (Test-Path $p) { "PRESENT" } else { "MISSING" }
    $report += "- $status : $rel"
}

$reportPath = Join-Path $stage "SOURCE_COLLECTION_REPORT.md"
[System.IO.File]::WriteAllLines($reportPath, $report, [System.Text.UTF8Encoding]::new($false))

if (Test-Path $OutputZip) {
    Remove-Item -LiteralPath $OutputZip -Force
}

Write-Host ""
Write-Host "[ZIP 생성 중]" -ForegroundColor Cyan
Compress-Archive -LiteralPath $stage -DestinationPath $OutputZip -CompressionLevel Optimal

# ZIP SHA-256
$hash = (Get-FileHash -LiteralPath $OutputZip -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item -LiteralPath $OutputZip).Length

Write-Host ""
Write-Host "완료" -ForegroundColor Green
Write-Host "ZIP : $OutputZip"
Write-Host "크기: $size bytes"
Write-Host "SHA-256: $hash"
Write-Host ""
Write-Host "이 ZIP을 ChatGPT에 그대로 업로드하면 됩니다." -ForegroundColor Cyan

Remove-Item -LiteralPath $tempRoot -Recurse -Force
