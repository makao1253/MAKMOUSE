# -*- mode: python ; coding: utf-8 -*-
"""Przepis PyInstallera dla MAKMOUSE - wersja FOLDEROWA (exe + _internal).

Za co odpowiada: mowi PyInstallerowi, od czego zaczac (run.py), czego nie
pakowac (nieuzywane moduly Qt), jaka ikone dac i ze program nie ma konsoli.
Z tego wyniku korzysta instalator (.iss) i `build_exe.bat folder`.
Wersja jednoplikowa: MAKMOUSE-onefile.spec.

Budowanie / build:

    python -m PyInstaller --noconfirm MAKMOUSE.spec

Wynik / result:  dist\\MAKMOUSE\\MAKMOUSE.exe
"""

# Qt ciagnie za soba komplet modulow - bierzemy tylko te trzy, ktorych uzywa
# aplikacja. Reszta (QtWebEngine, QtQuick, Qt3D, tlumaczenia Qt) to setki MB,
# ktore nigdy nie zostana wczytane.
EXCLUDES = [
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtUiTools",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSerialPort",
    "PySide6.QtSensors", "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtHelp",
    "PySide6.QtPrintSupport", "PySide6.QtXml", "PySide6.QtConcurrent",
    "tkinter", "unittest", "pydoc", "doctest", "email", "http", "xmlrpc",
    "pdb", "distutils", "setuptools", "pip",
]

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["makmouse.i18n"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MAKMOUSE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Aplikacja mieszka w zasobniku i nie wypisuje nic na stdout - konsola
    # tylko migalaby przy starcie.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="makmouse.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MAKMOUSE",
)
