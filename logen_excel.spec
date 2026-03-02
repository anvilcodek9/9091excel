# PyInstaller spec - 단일 exe 생성
# 사용: pyinstaller logen_excel.spec
# 주의: Windows exe는 Windows 환경에서 빌드해야 합니다.

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'src.gui_main',
        'src.token_dialog',
        'openpyxl',
        'openpyxl.cell._writer',
        'openpyxl.utils.exceptions',
        'openpyxl.worksheet._writer',
        'openpyxl.styles.stylesheet',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LogenExcel',
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
)
