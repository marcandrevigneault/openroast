# OpenRoast Windows build script
# Builds the frontend, installs backend, and creates the .exe with PyInstaller.

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Host "=== Building frontend ===" -ForegroundColor Cyan
Set-Location "$ROOT\frontend"
npm ci
npm run build
if (-not (Test-Path "build")) {
    Write-Error "Frontend build failed — build/ directory not found."
    exit 1
}

Write-Host "=== Installing backend ===" -ForegroundColor Cyan
Set-Location "$ROOT\backend"
python -m pip install --upgrade pip
pip install -e ".[hardware,desktop]"

Write-Host "=== Running PyInstaller ===" -ForegroundColor Cyan
Set-Location $ROOT
pyinstaller packaging/openroast-windows.spec --clean --noconfirm

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Output: dist\OpenRoast\OpenRoast.exe"
