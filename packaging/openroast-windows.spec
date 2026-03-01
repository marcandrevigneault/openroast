# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for OpenRoast Windows .exe build."""

import re
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

ROOT = Path(SPECPATH).parent
BACKEND_SRC = ROOT / "backend" / "src"
FRONTEND_BUILD = ROOT / "frontend" / "build"
ICON_ICO = ROOT / "packaging" / "icon.ico"
ICON_PNG = ROOT / "packaging" / "icon.png"

# Read version from pyproject.toml (single source of truth)
_pyproject = ROOT / "backend" / "pyproject.toml"
_version_match = re.search(
    r'^version\s*=\s*"([^"]+)"',
    _pyproject.read_text(),
    re.MULTILINE,
)
VERSION = _version_match.group(1) if _version_match else "0.0.0"

if not FRONTEND_BUILD.exists():
    raise FileNotFoundError(
        "Frontend build not found. Run 'npm run build' in frontend/ first."
    )

a = Analysis(
    [str(BACKEND_SRC / "openroast" / "desktop" / "__main__.py")],
    pathex=[str(BACKEND_SRC)],
    binaries=[],
    datas=[
        (str(FRONTEND_BUILD), "static"),
        (
            str(BACKEND_SRC / "openroast" / "catalog" / "machines.json"),
            "openroast/catalog",
        ),
        (str(ICON_PNG), "."),
    ] + copy_metadata("openroast"),
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "pydantic",
        "pydantic_core",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
        "pymodbus",
        "pymodbus.client",
        "pymodbus.client.tcp",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "openroast.catalog.loader",
        "openroast.simulator",
        "openroast.simulator.engine",
        "openroast.simulator.server",
        "openroast.simulator.manager",
        "openroast.simulator.register_map",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest", "pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="OpenRoast",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=str(ICON_ICO) if ICON_ICO.exists() else None,
)
