# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for DnD World Builder.

Builds a single-directory distribution bundling:
- Python 3.11 interpreter
- All application source code
- SRD rulebook JSON data (core/data_/rulebook_json/)
- SQLite database (dnd_database.db)
- Default config template (config/)
- qt-material theme XML files
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Locate qt-material theme files
try:
    import qt_material
    qt_material_dir = Path(qt_material.__file__).parent
    qt_material_datas = [
        (str(qt_material_dir / 'themes'), 'qt_material/themes'),
        (str(qt_material_dir / 'fonts'), 'qt_material/fonts'),
    ]
    # Include XML theme files at package root too
    for xml in qt_material_dir.glob('*.xml'):
        qt_material_datas.append((str(xml), 'qt_material'))
except ImportError:
    qt_material_datas = []

a = Analysis(
    ['entry_point.py'],
    pathex=[],
    binaries=[],
    datas=[
        # SRD rulebook JSON files
        ('core/data_/rulebook_json', 'core/data_/rulebook_json'),
        # SQLite database
        ('dnd_database.db', '.'),
        # Default config
        ('config', 'config'),
        # Demo scenario
        ('scenarios', 'scenarios'),
        # User documentation
        ('docs/user', 'docs'),
    ] + qt_material_datas,
    hiddenimports=[
        'aiohttp',
        'PyQt5.sip',
        'PyQt5.QtWebEngineWidgets',
        'sqlite3',
        'json',
        'asyncio',
        'logging',
        'uuid',
        'threading',
        # Registries and domain modules
        'registries',
        'registries.condition_registry',
        'registries.reaction_registry',
        'registries.trigger_registry',
        'domain',
        'domain.specs',
        'network',
        'network.protocol',
        'network.transport',
        'network.websocket_transport',
        'network.session_host',
        'network.session_client',
        'network.session_manager',
        'network.event_bridge',
        'network.sync',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
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
    [],
    exclude_binaries=True,
    name='DnD World Builder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed application (no console)
    icon='assets/icons/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DnD World Builder',
)
