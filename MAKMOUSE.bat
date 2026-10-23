@echo off
rem ===========================================================================
rem  MAKMOUSE - uruchomienie z kodu zrodlowego, bez okna konsoli
rem
rem  Za co odpowiada: startuje run.py przez pythonw (Python bez konsoli), wiec
rem  program od razu laduje w zasobniku. Wymaga zainstalowanego Pythona i PySide6.
rem  Gotowy .exe (bez Pythona) buduje build_exe.bat.
rem ===========================================================================
start "" pythonw "%~dp0run.py"
