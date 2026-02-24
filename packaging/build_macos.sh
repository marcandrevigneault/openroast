#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== OpenRoast macOS Build ==="

# Step 1: Build frontend
echo "[1/3] Building frontend..."
cd "$ROOT_DIR/frontend"
npm ci
npm run build

if [ ! -d "build" ]; then
    echo "ERROR: Frontend build directory not found"
    exit 1
fi

FILE_COUNT=$(find build -type f | wc -l | tr -d ' ')
echo "       Frontend built ($FILE_COUNT files)"

# Step 2: Install backend dependencies
echo "[2/3] Installing backend dependencies..."
cd "$ROOT_DIR/backend"
pip install -e ".[hardware,desktop]"

# Step 3: Run PyInstaller
echo "[3/3] Building macOS .app bundle..."
cd "$ROOT_DIR"
pyinstaller packaging/openroast.spec --clean --noconfirm

APP_PATH="$ROOT_DIR/dist/OpenRoast.app"
if [ -d "$APP_PATH" ]; then
    echo ""
    echo "=== Build Complete ==="
    echo "App bundle: $APP_PATH"
    echo "Size: $(du -sh "$APP_PATH" | cut -f1)"
else
    echo "ERROR: Build failed — .app not found"
    exit 1
fi
