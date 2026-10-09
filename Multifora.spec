# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['multifora_start.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('app/ui/checkbox_checked.svg', 'app/ui')] + collect_data_files('docxcompose'),
    hiddenimports=collect_submodules('docxcompose'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
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
