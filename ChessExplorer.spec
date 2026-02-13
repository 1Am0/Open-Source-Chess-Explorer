# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launch_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('games', 'games'),
        ('chess_explorer', 'chess_explorer'),
    ],
    hiddenimports=['chess', 'tqdm', 'requests', 'orjson'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Testing frameworks
        'pytest', 'unittest', '_pytest', 'py', 'pluggy',
        # Data science and plotting
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'Pillow',
        # Jupyter and notebooks
        'IPython', 'jupyter', 'notebook', 'nbformat', 'ipykernel',
        'jedi', 'parso', 'jupyter_client', 'jupyter_core',
        # Build and dev tools
        'setuptools', 'pip', 'wheel', 'black', 'isort',
        # Documentation
        'sphinx', 'docutils',
        # GUI frameworks (not needed for web)
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        # Other unused
        'pygments', 'jinja2', 'wcwidth', 'jsonschema',
    ],
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
    name='ChessExplorer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols
    upx=True,    # Compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
