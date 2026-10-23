@echo off
rem ===========================================================================
rem  MAKMOUSE - generowanie pliku INSTALACYJNEGO (MAKMOUSE-<wersja>-setup.exe)
rem
rem  Za co odpowiada: buduje wersje folderowa programu (build_exe.bat folder),
rem  odnajduje Inno Setup i kompiluje "Program instalacyjny (exe)\MAKMOUSE.iss".
rem  Numer wersji w nazwie instalatora pochodzi z makmouse\__init__.py.
rem
rem  Uzycie: kliknij ten plik dwukrotnie.
rem  Wynik:  "Program instalacyjny (exe)\Output\MAKMOUSE-<wersja>-setup.exe"
rem
rem  Wymaga Inno Setup 6 (darmowy): https://jrsoftware.org/isdl.php
rem ===========================================================================
setlocal
cd /d "%~dp0"
set "KOD=1"
set "ISS=Program instalacyjny (exe)\MAKMOUSE.iss"
set "WYNIK=Program instalacyjny (exe)\Output"

echo.
echo === MAKMOUSE: budowanie instalatora ===
echo.

rem --- 1. Inno Setup - sprawdzany najpierw, zeby nie budowac programu na darmo
set "ISCC="
for %%D in ("%ProgramFiles(x86)%" "%ProgramFiles%" "%LocalAppData%\Programs") do (
    if exist "%%~D\Inno Setup 6\ISCC.exe" set "ISCC=%%~D\Inno Setup 6\ISCC.exe"
)
if not defined ISCC for /f "delims=" %%F in ('where ISCC.exe 2^>nul') do set "ISCC=%%F"
if not defined ISCC (
    echo [BLAD] Nie znaleziono Inno Setup 6 - pobierz go z https://jrsoftware.org/isdl.php
    goto :koniec
)

rem --- 2. Program w wersji folderowej (dist\MAKMOUSE) ------------------------
rem  build_exe.bat pilnuje Pythona, bibliotek i dzialajacego MAKMOUSE.
call "%~dp0build_exe.bat" folder bezpauzy
if errorlevel 1 goto :blad

rem --- 3. Kompilacja instalatora ---------------------------------------------
echo.
echo === Kompilacja: %ISS% ===
"%ISCC%" /Qp "%ISS%"
if errorlevel 1 goto :blad

rem --- 4. Najnowszy plik w Output to ten, ktory wlasnie powstal --------------
set "PLIK="
for /f "delims=" %%F in ('dir /b /o-d "%WYNIK%\*-setup.exe" 2^>nul') do if not defined PLIK set "PLIK=%%F"

echo.
echo === GOTOWE ===
echo Instalator: %~dp0%WYNIK%\%PLIK%
echo.
set "KOD=0"
goto :koniec

:blad
echo.
echo [BLAD] Budowanie instalatora nie powiodlo sie - komunikat powyzej.
echo.

:koniec
pause
endlocal & exit /b %KOD%
