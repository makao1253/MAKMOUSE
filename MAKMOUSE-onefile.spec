# -*- mode: python ; coding: utf-8 -*-
"""Przepis PyInstallera: MAKMOUSE jako JEDEN plik .exe.

Za co odpowiada: to samo co MAKMOUSE.spec (punkt startu, wykluczenia Qt, ikona,
brak konsoli), ale wszystko laduje w jednym pliku. Uzywa go build_exe.bat.

Roznica wzgledem MAKMOUSE.spec:
    MAKMOUSE.spec          -> folder dist\\MAKMOUSE\\ (exe + _internal) - dla instalatora
    MAKMOUSE-onefile.spec  -> jeden plik dist\\MAKMOUSE.exe - do przenoszenia i uruchamiania

Budowanie / build:

    build_exe.bat              (najprosciej - klikniecie dwukrotne)
    python -m PyInstaller --noconfirm MAKMOUSE-onefile.spec

Wynik / result:  dist\\MAKMOUSE.exe
"""

# Qt ciagnie za soba komplet modulow - bierzemy tylko te, ktorych uzywa
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

# Brak COLLECT i exclude_binaries=False: wszystko laduje w jednym pliku .exe.
# Przy starcie PyInstaller rozpakowuje zawartosc do folderu tymczasowego, wiec
# pierwsze uruchomienie trwa kilka sekund dluzej niz wersja folderowa.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MAKMOUSE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
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
