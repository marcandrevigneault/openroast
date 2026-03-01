#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# OpenRoast — Create Windows 11 ARM VM in UTM
#
# This script downloads the Windows 11 ARM evaluation ISO and opens UTM
# with instructions for creating the VM.
#
# Prerequisites: UTM installed (brew install --cask utm)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ISO_DIR="$HOME/Downloads"
VHDX_FILE="$ISO_DIR/Windows11_InsiderPreview_Client_ARM64_en-us.vhdx"

echo "=== OpenRoast — Windows 11 ARM VM Setup ==="
echo ""

# Check UTM is installed
if ! command -v utmctl &>/dev/null; then
    echo "ERROR: UTM is not installed. Run: brew install --cask utm"
    exit 1
fi

echo "UTM is installed."
echo ""

# --- Option A: Use CrystalFetch to download Windows ISO ---
echo "=== Step 1: Get Windows 11 ARM ==="
echo ""
echo "Choose one of these methods to get a Windows 11 ARM image:"
echo ""
echo "  OPTION A (Recommended): Use UTM's built-in Windows installer"
echo "    1. Open UTM app"
echo "    2. Click '+' to create a new VM"
echo "    3. Select 'Virtualize' (fast, native ARM)"
echo "    4. Select 'Windows'"
echo "    5. UTM will download and install Windows 11 ARM automatically"
echo "       (it uses CrystalFetch behind the scenes)"
echo ""
echo "  OPTION B: Download VHDX from Microsoft"
echo "    1. Go to: https://www.microsoft.com/en-us/software-download/windowsinsiderpreviewarm64"
echo "    2. Sign in with a Microsoft account"
echo "    3. Download the VHDX (Windows 11 ARM Insider Preview)"
echo "    4. Save to: $ISO_DIR"
echo ""

# --- Provide recommended VM settings ---
echo "=== Step 2: VM Configuration ==="
echo ""
echo "When creating the VM in UTM, use these settings:"
echo ""
echo "  Type:         Virtualize (NOT Emulate — we want native ARM speed)"
echo "  OS:           Windows"
echo "  RAM:          4096 MB (4 GB) minimum, 8192 MB recommended"
echo "  CPU Cores:    4 minimum"
echo "  Storage:      64 GB (the build artifacts need space)"
echo "  Network:      Shared Network (NAT — default)"
echo "  Display:      virtio-gpu"
echo ""
echo "  IMPORTANT: Enable 'Install Windows 10 or higher' checkbox"
echo "  IMPORTANT: Enable 'Install drivers and SPICE tools' checkbox"
echo ""

# --- Shared directory setup ---
echo "=== Step 3: Shared Folder (easiest way to transfer files) ==="
echo ""
echo "After VM is created, before starting it:"
echo "  1. In UTM, right-click the VM → Edit"
echo "  2. Go to 'Sharing' tab"
echo "  3. Enable 'Directory Sharing'"
echo "  4. Set shared directory to: $ROOT_DIR"
echo "  5. This makes the project files available inside Windows"
echo ""
echo "Inside Windows, the shared folder appears as a network drive."
echo "  Open File Explorer → This PC → look for a SPICE shared folder"
echo "  Or map it: \\\\localhost\\share"
echo ""

# --- Post-install instructions ---
echo "=== Step 4: After Windows is Installed ==="
echo ""
echo "Once Windows is running in the VM:"
echo "  1. Install SPICE Guest Tools (UTM downloads these automatically)"
echo "     → Enables clipboard sharing, shared folders, dynamic resolution"
echo "  2. Open PowerShell as Administrator"
echo "  3. Navigate to the shared folder or clone the repo:"
echo "     git clone <your-repo-url> C:\\openroast"
echo "  4. Run the setup script:"
echo "     cd C:\\openroast\\packaging"
echo "     Set-ExecutionPolicy Bypass -Scope Process -Force"
echo "     .\\setup_windows_vm.ps1"
echo ""
echo "  This will install Git, Python 3.12, Node.js, build the frontend,"
echo "  and create the Windows .exe with PyInstaller."
echo ""
echo "=== Step 5: Test the Build ==="
echo ""
echo "  The .exe is built with console=True, so just run it from a terminal:"
echo "    C:\\openroast\\dist\\OpenRoast.exe"
echo ""
echo "  You'll see all uvicorn/FastAPI output in the terminal window."
echo "  The tray icon should appear and the browser should open automatically."
echo ""

# --- Open UTM ---
read -rp "Open UTM now? [Y/n] " answer
if [[ "${answer:-Y}" =~ ^[Yy]$ ]]; then
    open -a UTM
    echo "UTM opened. Follow the steps above to create the VM."
fi
