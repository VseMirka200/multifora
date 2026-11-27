# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

engine_root = Path('engines')
engine_binaries = []
engine_notices = []  # Portable trees are copied verbatim after freezing.

excluded_qt_runtime_binaries = {
    'qpdf.dll',
    'qtvirtualkeyboardplugin.dll',
    'qt6pdf.dll',
    'qt6virtualkeyboard.dll',
    'qt6quick.dll',
    'qt6qml.dll',
    'qt6qmlmeta.dll',
    'qt6qmlmodels.dll',
    'qt6qmlworkerscript.dll',
}

a = Analysis(
    ['multifora_start.py'],
    pathex=[],
    binaries=engine_binaries,
    datas=([('assets', 'assets')] if __import__('os').path.isdir('assets') else []) + engine_notices,
    hiddenimports=['PySide6.support.deprecated'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5', 'PySide2', 'tkinter', '_tkinter'],
    noarchive=False,
    optimize=0,
)
a.binaries = [
    binary
    for binary in a.binaries
    if binary[0].replace('\\', '/').rsplit('/', 1)[-1].lower()
    not in excluded_qt_runtime_binaries
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Multifora',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=['assets/icon.ico'] if __import__('os').path.isfile('assets/icon.ico') else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=["multifora_*.dll"],
    name='Multifora',
)
