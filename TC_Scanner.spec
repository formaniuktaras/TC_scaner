# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

project_dir = Path(__file__).resolve().parent
icon_path = project_dir / "assets" / "tc_scanner.ico"
default_config_path = project_dir / "scanner_config.default.json"

exe_icon = str(icon_path) if icon_path.exists() else None
datas = []
if default_config_path.exists():
    datas.append((str(default_config_path), "."))

a = Analysis(
    ['launch_tc_scanner.pyw'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=['tkinter', 'tkinter.scrolledtext'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TC_Scanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TC_Scanner',
)
