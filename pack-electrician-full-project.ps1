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

$excludedPrivatePaths = @(
    "docs\private",
    "docs\qnet-010-verification-0.14.0-dev4.md",
    "scripts\audit_qnet_010_user_candidate.py",
    "scripts\build_qnet_010_private_definition.py",
    "scripts\check_qnet_010_readiness.py",
    "backend\tests\test_qnet_010_user_candidate_audit.py",
    "backend\tests\test_qnet_010_private_validation.py",
    "backend\tests\test_qnet_008_018_private_candidates.py"
)

Write-Host ""
Write-Host "[파일 수집 중]" -ForegroundColor Cyan

function Test-PrivatePath([string]$relative) {
    $normalizedRelative = $relative.Replace('/', '\')
    foreach ($privatePath in $excludedPrivatePaths) {
        if ($normalizedRelative.Equals($privatePath, [System.StringComparison]::OrdinalIgnoreCase) -or
            $normalizedRelative.StartsWith($privatePath + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-IncludedFiles([string]$directory, [string]$relativePrefix = "") {
    foreach ($item in Get-ChildItem -LiteralPath $directory -Force) {
        $relative = if ($relativePrefix) { Join-Path $relativePrefix $item.Name } else { $item.Name }
        if ($item.PSIsContainer) {
            if ($excludedDirs -contains $item.Name) { continue }
            if (Test-PrivatePath $relative) { continue }
            Get-IncludedFiles $item.FullName $relative
            continue
        }
        if ($excludedExtensions -contains $item.Extension.ToLowerInvariant()) { continue }
        if ($excludedNames -contains $item.Name) { continue }
        if (Test-PrivatePath $relative) { continue }
        $item
    }
}

$files = @(Get-IncludedFiles $root)

foreach ($file in $files) {
    $relative = $file.FullName.Substring($root.Length).TrimStart('\','/')
    $dest = Join-Path $stage $relative
    $destDir = Split-Path $dest -Parent
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
}

# 실행 가능한 공개 연습본에는 어느 Q-Net 문제의 내부 정답 Net이나 동작 채점
# 시나리오도 싣지 않는다. 원본 저장소의 answer.json은 건드리지 않고 임시
# 수집본만 비식별화하므로 이후 다른 문제에 비공개 답안이 추가되어도 안전하다.
$qnetAnswers = @(Get-ChildItem -LiteralPath (Join-Path $stage "problems") -Directory -Filter "qnet_electrician_practical_*" | ForEach-Object {
    Get-Item -LiteralPath (Join-Path $_.FullName "answer.json") -ErrorAction SilentlyContinue
})
foreach ($qnetAnswer in $qnetAnswers) {
    $answerText = [System.IO.File]::ReadAllText($qnetAnswer.FullName, [System.Text.Encoding]::UTF8)
    $answer = $answerText | ConvertFrom-Json
    $answer.expected_nets = @()
    $answer.allowed_alternatives = @()
    $answer.wiring_connections = @()
    $answer.wiring_forbidden_connections = @()
    $answer.operation_tests = @()
    $answer.verification.status = "unverified"
    $answer.verification.verified_by = $null
    $answer.verification.verified_at = $null
    $answer.verification.notes = "공개 실행 ZIP용 무채점 정의. 비공개 후보와 정답 Net은 포함하지 않습니다."
    $serializedAnswer = $answer | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText($qnetAnswer.FullName, $serializedAnswer + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

# 어떤 핵심 파일이 들어갔는지 간단한 수집 보고서를 같이 넣는다.
$report = @()
$report += "# Electrician Simulator Full Source Collection"
$report += ""
$report += "Project root: $root"
$report += "Collected at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
$report += "File count: $($files.Count)"
$report += "Private Q-Net 010 candidate/audit files: EXCLUDED"
$report += "Q-Net 001-018 answer Nets and operation tests: REMOVED FROM DISTRIBUTION COPY"
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
