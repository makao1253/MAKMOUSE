; MAKMOUSE CAD Software - skrypt instalatora / installer script (Inno Setup 6)
;
; Za co odpowiada: pakuje wersje folderowa programu (dist\MAKMOUSE) w klasyczny
; instalator "Dalej -> Dalej -> Zakoncz": katalog programu, skroty, autostart,
; opcjonalna kopia dodatku do Fusion 360, deinstalacja. Konfiguracji uzytkownika
; nie rusza. Numer wersji bierze sam z makmouse\__init__.py (__version__) -
; przy nowej wersji nic tu nie trzeba zmieniac.
;
; Budowanie / build - najprosciej dwuklik w build_installer.bat w katalogu
; projektu (buduje program i instalator za jednym razem). Recznie:
;     1. build_exe.bat folder
;        (albo: python -m PyInstaller --noconfirm --clean MAKMOUSE.spec)
;     2. "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "Program instalacyjny (exe)\MAKMOUSE.iss"
;        albo otworz ten plik w Inno Setup Compiler i wcisnij F9.
; Wynik / result:  Program instalacyjny (exe)\Output\MAKMOUSE-<wersja>-setup.exe
;
; Ten plik MUSI lezec w podfolderze projektu (jednym poziomie ponizej run.py) -
; ProjectDir ponizej to katalog nadrzedny i od niego liczone sa wszystkie
; sciezki zrodlowe. Skopiowany gdzie indziej zglosi brak makmouse\__init__.py.

#define ScriptDir     AddBackslash(SourcePath)
#define ProjectDir    ExtractFilePath(RemoveBackslashUnlessRoot(SourcePath))

#define AppName       "MAKMOUSE CAD Software"
#define AppShortName  "MAKMOUSE"
#define AppPublisher  "MAKMOUSE"
#define AppExe        "MAKMOUSE.exe"

; --- Numer wersji z makmouse\__init__.py ------------------------------------
; Jedno zrodlo wersji dla programu i instalatora: szukamy linii ZACZYNAJACEJ
; sie od  __version__ = "1.3.3"  (wzmianki w komentarzach sa wciete, wiec ich
; nie zlapiemy) i bierzemy tekst miedzy cudzyslowami. Wewnatrz #sub
; przypisujemy przez #expr, bo #define utworzylby tam zmienna lokalna
; i wynik znikalby po petli.
#define AppVersion    ""
#define VerLine       ""
#define VerPos        0
#define VerHandle     FileOpen(ProjectDir + "makmouse\__init__.py")
#if !VerHandle
  #error Nie moge otworzyc makmouse\__init__.py - plik .iss musi lezec w podfolderze projektu MAKMOUSE.
#endif
#sub ReadVersionLine
  #expr VerLine = FileRead(VerHandle)
  #expr VerPos = Pos('__version__ = "', VerLine)
  #if VerPos == 1
    #expr AppVersion = Copy(VerLine, 16, Len(VerLine))
    #expr AppVersion = Copy(AppVersion, 1, Pos('"', AppVersion) - 1)
  #endif
#endsub
#for {0; AppVersion == "" && !FileEof(VerHandle); 0} ReadVersionLine
#expr FileClose(VerHandle)
#if AppVersion == ""
  #error Nie znalazlem linii __version__ = "..." w makmouse\__init__.py.
#endif

; --- Czy jest co pakowac ------------------------------------------------------
; Bez tej kontroli kompilator zglosi tylko suche "No files found matching".
#if !FileExists(ProjectDir + "dist\MAKMOUSE\" + AppExe)
  #error Brak dist\MAKMOUSE\MAKMOUSE.exe - najpierw zbuduj wersje FOLDEROWA programu: build_exe.bat folder (albo uzyj build_installer.bat, ktory robi oba kroki).
#endif

[Setup]
; AppId identyfikuje program przy aktualizacji i odinstalowaniu - raz nadany
; NIE MOZE sie zmieniac, inaczej kolejna wersja zainstaluje sie obok starej.
AppId={{4B1E7A96-2C08-4D3F-9A75-6E0C8B21D4F5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}

DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppShortName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}

; Sciezki zrodlowe licza sie od korzenia projektu, a gotowy instalator laduje
; w Output obok tego pliku - niezaleznie od tego, skad uruchomiono kompilator.
SourceDir={#ProjectDir}
OutputDir={#ScriptDir}Output
OutputBaseFilename={#AppShortName}-{#AppVersion}-setup
SetupIconFile=makmouse.ico

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Paczka PySide6 jest 64-bitowa - na 32 bitach nie ma czego instalowac.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Qt 6 nie dziala na Windows 7/8 - lepiej odmowic na starcie niz zainstalowac
; program, ktory sie nie uruchomi.
MinVersion=10.0

; Domyslnie instalacja dla wszystkich, ale uzytkownik bez praw administratora
; moze wybrac instalacje do wlasnego profilu - okienkiem albo przelacznikiem
; /CURRENTUSER z wiersza polecen.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline

; Ten sam muteks, ktorym aplikacja pilnuje pojedynczej instancji (run.py).
; Dzieki temu instalator sam poprosi o zamkniecie dzialajacego MAKMOUSE
; zamiast wywalic sie na zajetych plikach.
AppMutex=MakmouseRemapperSingleton,Global\MakmouseRemapperSingleton

; Zadanie "fusionaddin" celowo pisze do {userappdata}: Fusion czyta dodatki
; wylacznie z profilu uzytkownika i nie ma dla nich lokalizacji wspolnej.
; Przy zwyklym podniesieniu uprawnien przez UAC profil sie zgadza; rozjedzie
; sie tylko wtedy, gdy ktos poda dane LOGOWANIA innego administratora.
UsedUserAreasWarning=no

[Languages]
Name: "polski"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
polski.StartupIcon=Uruchamiaj MAKMOUSE przy starcie systemu
polski.AddonGroup=Dodatek do Fusion 360:
polski.AddonCopy=Zainstaluj dodatek do Fusion 360 (kopiuje pliki do %APPDATA%)
english.StartupIcon=Start MAKMOUSE when Windows starts
english.AddonGroup=Fusion 360 add-in:
english.AddonCopy=Install the Fusion 360 add-in (copies files into %APPDATA%)

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "{cm:StartupIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"
Name: "fusionaddin"; Description: "{cm:AddonCopy}"; \
    GroupDescription: "{cm:AddonGroup}"; Flags: unchecked

[InstallDelete]
; Przy aktualizacji usuwamy stary _internal: nowa wersja PySide6/PyInstallera
; moze miec inny zestaw bibliotek, a resztki poprzedniej tylko by zalegaly.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
; Cala paczka PyInstallera - MAKMOUSE.exe plus folder _internal.
Source: "dist\MAKMOUSE\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; Zrodlo dodatku do Fusiona - zawsze obok programu, zeby dalo sie je
; skopiowac recznie takze pozniej. Pamiec podreczna Pythona nie jest potrzebna.
Source: "fusion_addin\MAKMOUSE\*"; DestDir: "{app}\fusion_addin\MAKMOUSE"; \
    Excludes: "__pycache__,*.pyc"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; Ta sama kopia ladowana wprost do Fusiona, gdy zaznaczono zadanie.
; Fusion czyta dodatki wylacznie z profilu uzytkownika, wiec instalowanie
; ich w trybie administratora trafiloby do profilu administratora - stad
; ostrzezenie w INSTALL.md.
Source: "fusion_addin\MAKMOUSE\*"; \
    DestDir: "{userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns\MAKMOUSE"; \
    Excludes: "__pycache__,*.pyc"; \
    Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall; \
    Tasks: fusionaddin

Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.en.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "ADDONS.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppShortName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppShortName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppShortName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{autostartup}\{#AppShortName}"; Filename: "{app}\{#AppExe}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppShortName}}"; \
    Flags: nowait postinstall skipifsilent

; Konfiguracja (%APPDATA%\MAKMOUSE) celowo NIE jest kasowana przy
; odinstalowaniu - to dane uzytkownika, nie czesc programu.
