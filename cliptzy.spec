# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ('fonts', 'fonts'),
]

if os.path.isdir('images'):
    datas.append(('images', 'images'))

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'av',
    'yt_dlp',
    'core',
    'gui',
]

# Collect all binaries & datas for ctranslate2, faster_whisper, and av if available
for pkg in ['ctranslate2', 'faster_whisper', 'av', 'yt_dlp']:
    try:
        tmp_datas, tmp_binaries, tmp_hidden = collect_all(pkg)
        datas.extend(tmp_datas)
        hiddenimports.extend(tmp_hidden)
    except Exception:
        pass

a = Analysis(
    ['gui/app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['Flask', 'Jinja2', 'Werkzeug', 'blinker', 'itsdangerous', 'pytest', 'tkinter'],
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
    name='cliptzy',
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
    icon='images/icon.png' if os.path.exists('images/icon.png') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cliptzy',
)
