# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for SmartScan.

Produces a one-folder build (fast startup, no unpacking to %TEMP%) which
``packaging/inno/smartscan.iss`` then wraps into a single installer.

    pyinstaller packaging/smartscan.spec --noconfirm
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "SmartScan"

block_cipher = None

# The app paints its own icon at runtime, so no image assets are needed here;
# only the guide, which the in-app Help window can point at.
datas = [
    (str(ROOT / "HOW-TO-USE.md"), "."),
    (str(ROOT / "docs" / "install-notes.txt"), "docs"),
]

# OpenCV and Pillow pull plugins dynamically; collect them explicitly so the
# frozen build does not fail with "cannot load module" at runtime.
hiddenimports = (
    collect_submodules("PIL")
    + collect_submodules("cv2")
    + ["numpy", "PySide6.QtSvg", "PySide6.QtPrintSupport"]
)

excludes = [
    # Never bundle a second copy of Qt or a launcher we do not use.
    "tkinter",
    "matplotlib",
    "pandas",
    "scipy",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtNetworkAuth",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "cv2.gapi",
    "pytest",
    "pypdf",
]

a = Analysis(
    [str(ROOT / "run_smartscan.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # no console window: this is a GUI app
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "smartscan.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),  # ignored on non-Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
