# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SYBOT standalone executable
"""

import sys
from pathlib import Path

# Get the base directory
block_cipher = None

# Collect all data files and directories
added_files = [
    ('config', 'config'),
    ('core', 'core'),
    ('memory', 'memory'),
    ('actions', 'actions'),
    ('agent', 'agent'),
    ('ui.py', '.'),
]

# Collect hidden imports
hiddenimports = [
    'google.genai',
    'google.genai.types',
    'google.generativeai',
    'sounddevice',
    'numpy',
    'cv2',
    'PIL',
    'pyautogui',
    'pyperclip',
    'requests',
    'openai',
    'torch',
    'transformers',
    'speechbrain',
    'resemblyzer',
    'webrtcvad',
    'mss',
    'duckduckgo_search',
    'httpx',
    'watchdog',
    'psutil',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'scipy',
        'notebook',
        'jupyter',
        'ipython',
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
    name='SYBOT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging, can be set to False for silent mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path if available
)
