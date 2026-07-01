param(
    [switch]$Build,
    [string]$BuildTarget = "StandaloneWindows64"
)

$ErrorActionPreference = "Stop"
$ProjectPath = Join-Path $PSScriptRoot "..\src\unity" -Resolve
$UnityVersion = "6000.0.23f1"

Write-Host "=== AI Companion - Unity Auto Setup ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectPath" -ForegroundColor Gray
Write-Host ""

# Tìm Unity Hub
$UnityHubPath = ""
$possiblePaths = @(
    "$env:LOCALAPPDATA\Unity\Hub\editor\Unity.exe",
    "$env:PROGRAMFILES\Unity\Hub\Editor\Unity.exe",
    "${env:PROGRAMFILES(x86)}\Unity\Hub\Editor\Unity.exe"
)
foreach ($p in $possiblePaths) {
    if (Test-Path $p) { $UnityHubPath = $p; break }
}

if (-not $UnityHubPath) {
    Write-Host "[WARN] Không tìm thấy Unity Editor." -ForegroundColor Yellow
    Write-Host "       Cài Unity Hub tại: https://unity.com/download" -ForegroundColor Yellow
    Write-Host "       Sau đó cài Unity $UnityVersion qua Unity Hub." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[INFO] Các .cs files đã sẵn sàng tại: src/unity/Assets/Scripts/" -ForegroundColor Green
    Write-Host "[INFO] Packages đã cấu hình trong: src/unity/Packages/manifest.json" -ForegroundColor Green
    Write-Host ""
    Write-Host "Các bước thủ công:" -ForegroundColor Cyan
    Write-Host "  1. Mở Unity Hub -> Install Editor -> $UnityVersion" -ForegroundColor White
    Write-Host "  2. Open -> Add project from disk -> chọn src/unity/" -ForegroundColor White
    Write-Host "  3. Unity sẽ tự động download các packages trong manifest.json" -ForegroundColor White
    Write-Host "  4. Sau khi load xong, File -> Build Settings -> Build" -ForegroundColor White
    exit 1
}

Write-Host "[OK] Tìm thấy Unity: $UnityHubPath" -ForegroundColor Green

# Mở project trong Unity Editor
Write-Host "[...] Đang mở project trong Unity Editor..." -ForegroundColor Yellow
Start-Process -FilePath $UnityHubPath -ArgumentList "-projectPath", "`"$ProjectPath`""

if ($Build) {
    Write-Host "[...] Đang build cho $BuildTarget ..." -ForegroundColor Yellow
    & $UnityHubPath -quit -batchmode -projectPath "$ProjectPath" -buildTarget $BuildTarget -executeMethod "BuildScript.PerformBuild"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Build thành công!" -ForegroundColor Green
    } else {
        Write-Host "[ERR] Build thất bại (code: $LASTEXITCODE)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
