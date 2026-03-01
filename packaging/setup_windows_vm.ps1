# OpenRoast Windows VM — Dev Environment Setup
# Run this inside a fresh Windows 11 VM to install all build dependencies.
# Usage: Open PowerShell as Administrator, then:
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\setup_windows_vm.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== OpenRoast Windows Dev Environment Setup ===" -ForegroundColor Cyan
Write-Host "This script installs Git, Python 3.12, Node.js 20 LTS, and project dependencies.`n"

# --- 1. Install winget packages (Git, Python, Node) ---

function Install-WingetPackage {
    param([string]$Id, [string]$Name)
    Write-Host "[*] Installing $Name..." -ForegroundColor Yellow
    winget install --id $Id --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    winget install failed for $Name, trying alternative..." -ForegroundColor Red
        return $false
    }
    return $true
}

# Refresh PATH helper
function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Install-WingetPackage -Id "Git.Git" -Name "Git"
    Refresh-Path
} else {
    Write-Host "[OK] Git already installed: $(git --version)" -ForegroundColor Green
}

# Python 3.12
if (-not (Get-Command python -ErrorAction SilentlyContinue) -or
    -not ((python --version 2>&1) -match "3\.12")) {
    Install-WingetPackage -Id "Python.Python.3.12" -Name "Python 3.12"
    Refresh-Path
} else {
    Write-Host "[OK] Python already installed: $(python --version)" -ForegroundColor Green
}

# Node.js 20 LTS
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Install-WingetPackage -Id "OpenJS.NodeJS.LTS" -Name "Node.js LTS"
    Refresh-Path
} else {
    Write-Host "[OK] Node.js already installed: $(node --version)" -ForegroundColor Green
}

# Final PATH refresh
Refresh-Path

# --- 2. Verify installations ---
Write-Host "`n=== Verifying installations ===" -ForegroundColor Cyan
$tools = @(
    @{ Name = "git";    Cmd = "git --version" },
    @{ Name = "python"; Cmd = "python --version" },
    @{ Name = "node";   Cmd = "node --version" },
    @{ Name = "npm";    Cmd = "npm --version" }
)

$allOk = $true
foreach ($t in $tools) {
    try {
        $ver = Invoke-Expression $t.Cmd 2>&1
        Write-Host "  $($t.Name): $ver" -ForegroundColor Green
    } catch {
        Write-Host "  $($t.Name): NOT FOUND — restart terminal and re-run" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Host "`nSome tools not found. Close this terminal, open a new one, and re-run." -ForegroundColor Red
    exit 1
}

# --- 3. Clone repo (if not already present) ---
$REPO_URL = "https://github.com/marcandrevigneault/openroast.git"
$PROJECT_DIR = "$env:USERPROFILE\openroast"

if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "`n=== Cloning repository ===" -ForegroundColor Cyan
    git clone $REPO_URL $PROJECT_DIR
} else {
    Write-Host "`n=== Repository already cloned at $PROJECT_DIR ===" -ForegroundColor Green
    Set-Location $PROJECT_DIR
    git pull
}

Set-Location $PROJECT_DIR

# --- 4. Setup Python venv + backend deps ---
Write-Host "`n=== Setting up Python venv ===" -ForegroundColor Cyan
Set-Location "$PROJECT_DIR\backend"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Activate venv
& ".venv\Scripts\Activate.ps1"

Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -e ".[dev,hardware,desktop]"

# --- 5. Build frontend ---
Write-Host "`n=== Building frontend ===" -ForegroundColor Cyan
Set-Location "$PROJECT_DIR\frontend"
npm ci
npm run build

if (-not (Test-Path "build")) {
    Write-Host "ERROR: Frontend build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Frontend build OK" -ForegroundColor Green

# --- 6. Run PyInstaller build ---
Write-Host "`n=== Building Windows .exe with PyInstaller ===" -ForegroundColor Cyan
Set-Location $PROJECT_DIR

# Make sure venv is active
& "$PROJECT_DIR\backend\.venv\Scripts\Activate.ps1"

pyinstaller packaging/openroast-windows.spec --clean --noconfirm

$exePath = "$PROJECT_DIR\dist\OpenRoast.exe"
if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length / 1MB
    Write-Host "`n=== BUILD SUCCESSFUL ===" -ForegroundColor Green
    Write-Host "Executable: $exePath" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($size, 1)) MB" -ForegroundColor Green
    Write-Host "`nTo test: run the .exe from a terminal to see console output:" -ForegroundColor Yellow
    Write-Host "  $exePath" -ForegroundColor White
} else {
    Write-Host "`nERROR: Build failed — .exe not found!" -ForegroundColor Red
    exit 1
}
