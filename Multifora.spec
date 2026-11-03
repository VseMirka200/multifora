# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files

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
    binaries=[],
    datas=[('assets', 'assets')]
    + collect_data_files('docxcompose')
    + collect_data_files('pymupdf', excludes=['mupdf-devel/**']),
    hiddenimports=['docxcompose.composer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5', 'PySide2', 'pdf2docx.gui', 'tkinter', '_tkinter'],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Multifora',
)
