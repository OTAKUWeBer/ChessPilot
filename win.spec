# -*- mode: python ; coding: utf-8 -*-
import os

datas = [
    ('assets/logo.png', 'assets'),
    ('src/chess_detection.onnx', '.'),
]
if os.path.exists('assets/logo.ico'):
    datas.append(('assets/logo.ico', 'assets'))

a = Analysis(
    ['src/main.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'onnxruntime',
        'PIL',
        'cpuinfo',
        'mss',
        'pyautogui',
        'win32api',
        'win32con',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChessPilot-v2.3.0-windows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo.ico' if os.path.exists('assets\\logo.ico') else 'assets\\logo.png'],
)
