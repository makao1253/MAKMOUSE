@echo off
rem ===========================================================================
rem  MAKMOUSE - generowanie pliku .exe (zwyklego, nie instalacyjnego)
rem
rem  Za co odpowiada: sprawdza Pythona, doinstalowuje PySide6 i PyInstaller,
rem  zamyka dzialajacy MAKMOUSE (blokuje plik), buduje program wg przepisu
rem  MAKMOUSE-onefile.spec albo MAKMOUSE.spec i kopiuje wynik do folderu
rem  "Program gotowy (bez instalatora)". Robocze foldery build\ i dist\ mozna kasowac.
rem
rem  Uzycie: kliknij ten plik dwukrotnie albo uruchom w wierszu polecen:
rem      build_exe.bat            -> jeden plik  "Program gotowy (bez instalatora)\MAKMOUSE.exe"
rem      build_exe.bat folder     -> wersja folderowa "...\MAKMOUSE\MAKMOUSE.exe" (szybszy start)
rem
rem  Kolejne wersje nadpisuja poprzedni plik - nic nie trzeba sprzatac recznie.
rem
rem  Drugi parametr - dla innych skryptow (np. build_installer.bat):
rem      cicho     -> bez pytan i bez pauzy (dzialajacy MAKMOUSE zamyka od razu)
rem      bezpauzy  -> pyta jak zwykle, ale nie czeka na klawisz na koncu
rem  Kod wyjscia: 0 = zbudowano, 1 = blad albo przerwano.
rem ===========================================================================
setlocal
cd /d "%~dp0"
set "KOD=1"

set "TRYB=%~1"
if /i "%TRYB%"=="folder" (
    set "SPEC=MAKMOUSE.spec"
    set "ZRODLO=dist\MAKMOUSE"
    set "CEL=Program gotowy (bez instalatora)\MAKMOUSE"
) else (
    set "SPEC=MAKMOUSE-onefile.spec"
    set "ZRODLO=dist\MAKMOUSE.exe"
    set "CEL=Program gotowy (bez instalatora)\MAKMOUSE.exe"
)

echo.
echo === MAKMOUSE: budowanie %SPEC% ===
echo.

rem --- 1. Python ------------------------------------------------------------
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Nie znaleziono Pythona. Zainstaluj go z https://www.python.org/downloads/
    echo        i zaznacz "Add python.exe to PATH".
    goto :koniec
)

rem --- 2. Biblioteki --------------------------------------------------------
%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Instaluje PySide6...
    %PY% -m pip install --disable-pip-version-check PySide6 || goto :blad
)
%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Instaluje PyInstaller...
    %PY% -m pip install --disable-pip-version-check pyinstaller || goto :blad
)

rem --- 3. Dzialajacy MAKMOUSE trzyma plik docelowy --------------------------
tasklist /fi "imagename eq MAKMOUSE.exe" 2>nul | find /i "MAKMOUSE.exe" >nul
if not errorlevel 1 (
    echo MAKMOUSE jest uruchomiony i blokuje plik, ktory mam nadpisac.
    if /i "%~2"=="cicho" (
        taskkill /im MAKMOUSE.exe /f >nul 2>&1
    ) else (
        choice /c TN /n /m "Zamknac go teraz? [T/N] "
        if errorlevel 2 (
            echo Przerwane. Zamknij MAKMOUSE z zasobnika i uruchom skrypt ponownie.
            goto :koniec
        )
        taskkill /im MAKMOUSE.exe /f >nul 2>&1
    )
    rem Bootloader wersji jednoplikowej konczy sie z lekkim opoznieniem.
    ping -n 3 127.0.0.1 >nul
)

rem --- 4. Budowanie ---------------------------------------------------------
%PY% -m PyInstaller --noconfirm --clean "%SPEC%" || goto :blad

if not exist "%ZRODLO%" (
    echo [BLAD] PyInstaller nie zostawil pliku %ZRODLO%.
    goto :blad
)

rem --- 5. Kopia do folderu z gotowym programem ------------------------------
if /i "%TRYB%"=="folder" (
    if exist "%CEL%" rmdir /s /q "%CEL%"
    xcopy "%ZRODLO%" "%CEL%\" /e /i /q /y >nul || goto :blad
) else (
    if not exist "Program gotowy (bez instalatora)" mkdir "Program gotowy (bez instalatora)"
    copy /y "%ZRODLO%" "%CEL%" >nul || goto :blad
)

echo.
echo === GOTOWE ===
echo Plik: %~dp0%CEL%
echo.
set "KOD=0"
goto :koniec

:blad
echo.
echo [BLAD] Budowanie nie powiodlo sie - komunikat powyzej.
echo.

:koniec
if /i not "%~2"=="cicho" if /i not "%~2"=="bezpauzy" pause
endlocal & exit /b %KOD%
