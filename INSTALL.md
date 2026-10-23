# MAKMOUSE — instalacja na innym komputerze

*[English version below](#makmouse--installing-on-another-computer)*

Są trzy drogi. Wybierz jedną — nie trzeba robić wszystkich.

| Droga | Dla kogo | Czy potrzebny Python |
|---|---|---|
| **A. Gotowy `.exe`** | użytkownik, który ma tylko używać | nie |
| **B. Kod źródłowy + Python** | ktoś, kto będzie zmieniał kod | tak |
| **C. Instalator MSI/EXE** | dystrybucja dla wielu osób | nie (u odbiorcy) |

Wymagania w każdym wariancie: **Windows 10 lub 11, 64-bit**. Aplikacja opiera
się na Raw Input, hookach niskopoziomowych i `SendInput`, więc na Linuksie ani
macOS nie ruszy.

---

## A. Gotowy `.exe` (najprostsze)

### 1. Zbuduj plik na swoim komputerze

**Kliknij dwukrotnie `build_exe.bat`** w folderze projektu. Skrypt sprawdzi
Pythona, doinstaluje `PySide6` i `pyinstaller`, jeśli ich brakuje, i zbuduje
program. To samo z wiersza poleceń:

```powershell
cd d:\MAKMOUSE
.\build_exe.bat
```

Powstaje **jeden plik**:

```
d:\MAKMOUSE\Program gotowy (bez instalatora)\MAKMOUSE.exe     (~36 MB)
```

Kolejne budowania nadpisują ten sam plik.

Jeśli wolisz wariant folderowy (startuje natychmiast, bo nic się nie rozpakowuje):

```powershell
.\build_exe.bat folder
```

Powstaje wtedy `Program gotowy (bez instalatora)\MAKMOUSE\` — około **90 MB**,
w środku `MAKMOUSE.exe` i folder `_internal` z bibliotekami Qt.

### 2. Przenieś na docelowy komputer

* **wariant jednoplikowy** — skopiuj sam `MAKMOUSE.exe`, gdziekolwiek,
* **wariant folderowy** — skopiuj **cały folder** `MAKMOUSE` (sam `.exe` bez
  `_internal` nie wstanie).

Na docelowym komputerze umieść go gdziekolwiek, np.:

```
C:\Program Files\MAKMOUSE\
C:\Users\<nazwa>\MAKMOUSE\
```

> Jeśli wybierzesz `C:\Program Files`, kopiowanie będzie wymagało zgody
> administratora. Sama aplikacja **nie potrzebuje** uprawnień administratora —
> chyba że ma działać nad oknem programu uruchomionego jako administrator.

### 3. Uruchom

Dwuklik w `MAKMOUSE.exe`. Okno wstaje, w zasobniku pojawia się ikona.

Windows SmartScreen może przy pierwszym uruchomieniu pokazać *„System Windows
ochronił Twój komputer"* — to normalne dla niepodpisanego pliku. *Więcej
informacji → Uruchom mimo to*. Żeby ostrzeżenie zniknęło na stałe, plik musiałby
być podpisany certyfikatem code signing (płatny, wystawiany na firmę lub osobę).

### 4. (opcjonalnie) Skrót i autostart

Skrót na pulpicie: prawy przycisk na `MAKMOUSE.exe` → *Pokaż więcej opcji* →
*Wyślij do* → *Pulpit (utwórz skrót)*.

Autostart przy logowaniu — wciśnij `Win`+`R`, wpisz `shell:startup`, wklej do
otwartego folderu **skrót** do `MAKMOUSE.exe`.

### 5. Przenieś swoje ustawienia (opcjonalnie)

Konfiguracja **nie jest** częścią paczki — na nowym komputerze aplikacja wstaje
z ustawieniami fabrycznymi. Żeby przenieść swoje:

1. na starym komputerze: *Ustawienia → Eksportuj…* → zapisz `makmouse-config.json`,
2. na nowym: *Ustawienia → Importuj…* → wskaż ten plik.

Alternatywnie skopiuj wprost plik `%APPDATA%\MAKMOUSE\config.json`.

Wyeksportowany plik niesie też wybrany **język**, motyw i wszystkie profile.

---

## B. Kod źródłowy + Python (dla rozwijania)

### 1. Zainstaluj Pythona

Pobierz z [python.org](https://www.python.org/downloads/windows/) wersję **3.10
lub nowszą** (projekt był budowany na 3.14). Przy instalacji zaznacz
**„Add python.exe to PATH"**.

### 2. Skopiuj projekt

Przenieś folder `MAKKEY` (albo sklonuj repozytorium). Wystarczą:

```
run.py  MAKMOUSE.bat  build_exe.bat  MAKMOUSE.spec  MAKMOUSE-onefile.spec
makmouse.ico  makmouse\  fusion_addin\
```

Foldery `build\`, `dist\`, `__pycache__\` i `.mypy_cache\` są generowane —
nie ma potrzeby ich kopiować.

### 3. Zainstaluj zależność

```powershell
python -m pip install PySide6-Essentials
```

To jedyna zależność zewnętrzna. Cała warstwa systemowa (Raw Input, hooki,
`SendInput`, odczyt deskryptorów USB) idzie przez wbudowany `ctypes` — bez
pywin32 i bez bibliotek HID.

Zalecane, choć nieobowiązkowe — środowisko wirtualne:

```powershell
cd d:\MAKKEY
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install PySide6-Essentials
```

### 4. Uruchom

```powershell
python run.py
```

Bez okna konsoli: dwuklik w [MAKMOUSE.bat](MAKMOUSE.bat) albo `pythonw run.py`.

---

## C. Instalator (dystrybucja dla wielu osób)

PyInstaller robi folder, nie instalator. Jeśli potrzebny jest klasyczny
kreator „Dalej → Dalej → Zakończ", zbuduj paczkę z wariantu A i opakuj ją.

Gotowy skrypt leży w repozytorium:
**[Program instalacyjny (exe)/MAKMOUSE.iss](<Program instalacyjny (exe)/MAKMOUSE.iss>)**.
Nie trzeba go pisać od zera — wystarczy zbudować.

### Najprościej: jedno kliknięcie

**1. Zainstaluj Inno Setup** — [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
(darmowy). Skrypt był sprawdzony na **6.7.3**.

**2. Kliknij dwukrotnie [build_installer.bat](build_installer.bat)** w folderze
projektu. Skrypt odnajduje Inno Setup, buduje wersję folderową programu
(`build_exe.bat folder` — sprawdza Pythona i biblioteki, pyta o zamknięcie
działającego MAKMOUSE) i kompiluje instalator. Całość trwa 1–2 minuty.

Wynik: `Program instalacyjny (exe)\Output\MAKMOUSE-1.3.3-setup.exe`, około
**26 MB** (instalator kompresuje 91 MB paczki do jednego pliku).

### Ręcznie, krok po kroku

**1. Zbuduj wersję folderową programu** — instalator tylko ją opakowuje:

```powershell
cd d:\MAKMOUSE
.\build_exe.bat folder
# albo samym PyInstallerem:
python -m PyInstaller --noconfirm --clean MAKMOUSE.spec
```

**2. Skompiluj instalator** — z wiersza polecenia:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "d:\MAKMOUSE\Program instalacyjny (exe)\MAKMOUSE.iss"
```

albo otwórz `MAKMOUSE.iss` w *Inno Setup Compiler* i wciśnij **F9**.

### ⚠ Najczęstszy błąd kompilacji

```
Brak dist\MAKMOUSE\MAKMOUSE.exe - najpierw zbuduj wersje FOLDEROWA programu ...
```

Instalator pakuje **wersję folderową** (`dist\MAKMOUSE\`). Zwykłe `build_exe.bat`
(bez `folder`) robi jeden plik `dist\MAKMOUSE.exe` — tego skrypt nie użyje.
Wykonaj krok 1 albo użyj `build_installer.bat`.

Skrypt liczy ścieżki od **katalogu nadrzędnego wobec siebie**, więc plik `.iss`
musi leżeć w podfolderze projektu (tak jak teraz: `Program instalacyjny (exe)\`);
skąd uruchomisz kompilator, nie ma znaczenia. Kopia zapisana gdzie indziej,
np. w *Dokumentach*, zgłosi, że nie może otworzyć `makmouse\__init__.py`.

### Co ten instalator robi

| Element | Zachowanie |
|---|---|
| Katalog docelowy | `C:\Program Files\MAKMOUSE` (do zmiany w kreatorze) |
| Instalacja bez admina | tak — kreator pyta „dla wszystkich / tylko dla mnie" |
| Język kreatora | polski i angielski, do wyboru na starcie |
| Skrót na pulpicie | opcjonalny (zaznaczany) |
| Autostart z Windows | opcjonalny (zaznaczany) |
| Dodatek do Fusion 360 | opcjonalny — kopiuje pliki wprost do `%APPDATA%` |
| Działający MAKMOUSE | wykrywany przez `AppMutex` — kreator poprosi o zamknięcie zamiast wywalić się na zajętych plikach |
| Aktualizacja | nowa wersja zastępuje starą; stary folder `_internal` jest usuwany przed kopiowaniem |
| System | Windows 10/11, 64-bit — na starszym kreator odmówi instalacji |
| Deinstalacja | pełna, przez *Aplikacje i funkcje* |
| Konfiguracja | **nie jest kasowana** przy deinstalacji — to Twoje dane |

Dodatek Fusiona ląduje też **zawsze** w `{app}\fusion_addin\MAKMOUSE`, więc da się
go skopiować ręcznie także później.

### Wersja i AppId

Numer wersji instalator bierze sam z `makmouse/__init__.py`:

```python
__version__ = "1.3.3"
```

Przy wydaniu nowej wersji zmieniasz go **tylko tam** — nazwa pliku
`MAKMOUSE-<wersja>-setup.exe` i wersja w *Aplikacjach i funkcjach* zmienią się same.

**Nie zmieniaj `AppId`.** To on identyfikuje program przy aktualizacji — po jego
podmianie nowa wersja zainstaluje się *obok* starej zamiast ją zastąpić.

### Instalacja cicha (wdrożenia masowe)

```powershell
MAKMOUSE-1.3.3-setup.exe /VERYSILENT /NORESTART /MERGETASKS="desktopicon,startupicon"
```

Przydatne przełączniki: `/DIR="C:\ścieżka"`, `/CURRENTUSER` (bez admina),
`/LOG="plik.log"`, `/MERGETASKS="!desktopicon"` (wyłącza zadanie).

### Alternatywa: MSI

Jeśli wymagany jest format **MSI** (wdrożenia przez GPO albo Intune), Inno Setup
go nie robi — potrzebny jest **[WiX Toolset](https://wixtoolset.org/)**. Jest
istotnie trudniejszy; sensowny tylko wtedy, gdy MSI jest twardym wymogiem
działu IT.

---

## Dodatek do Fusion 360

Dodatek jest osobny od aplikacji i instaluje się go po stronie Fusiona.

1. Skopiuj **cały folder** `fusion_addin\MAKMOUSE` (plik `.py` **i** `.manifest`)
   do:

   ```
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
   ```

   Docelowo ma powstać `...\AddIns\MAKMOUSE\MAKMOUSE.py`.

2. W Fusionie: *Utilities → Scripts and Add-Ins* (`Shift`+`S`) → zakładka
   **Add-Ins** → `MAKMOUSE` → **Run**. Zaznacz **Run on Startup**.

3. Sprawdzenie: w MAKMOUSE, w panelu profilu, powinno pojawić się
   *Dodatek podłączony (1)*.

Gdy coś nie gra, dodatek pisze dziennik do `%TEMP%\makmouse_addin.log` — wpisz
`%TEMP%` w pasku Eksploratora.

---

## Czego trzeba pilnować

**Zapora / antywirus.** MAKMOUSE otwiera gniazdo TCP na `127.0.0.1:8765` dla
dodatku. To ruch wyłącznie lokalny — Zapora Windows zwykle o nic nie pyta, ale
gdyby zapytała, wystarczy sieć **prywatna**. Port zmienisz w konfiguracji
(`"bridge_port"`).

**Jedna instancja.** Aplikacja pilnuje się muteksem — drugie uruchomienie tylko
pokaże komunikat i zamknie się. Jeśli okno „zniknęło", szukaj ikony w zasobniku.

**Urządzenie.** Na nowym komputerze sterownik nie jest potrzebny (klasa HID jest
wbudowana w Windows), ale deskryptor USB nadal musi zawierać napis `MAKMOUSE`
w `iProduct` albo `iManufacturer` — inaczej aplikacja go nie rozpozna.

**Bez uruchomionego MAKMOUSE urządzenie nie robi nic.** To nie usterka, tylko
cena pełnej separacji od zwykłej myszy.

---
---

# MAKMOUSE — installing on another computer

There are three routes. Pick one — you do not need all of them.

| Route | For whom | Python needed |
|---|---|---|
| **A. Ready-made folder with the `.exe`** | someone who only wants to use it | no |
| **B. Source code + Python** | someone who will change the code | yes |
| **C. MSI/EXE installer** | distribution to many people | no (on their side) |

Requirements in every variant: **Windows 10 or 11, 64-bit**. The application is
built on Raw Input, low-level hooks and `SendInput`, so it will not run on Linux
or macOS.

---

## A. Ready-made `.exe` (simplest)

### 1. Build the file on your machine

**Double-click `build_exe.bat`** in the project folder. The script checks for
Python, installs `PySide6` and `pyinstaller` if they are missing, and builds the
program. The same from a command line:

```powershell
cd d:\MAKMOUSE
.\build_exe.bat
```

This produces **a single file**:

```
d:\MAKMOUSE\Program gotowy (bez instalatora)\MAKMOUSE.exe     (~36 MB)
```

Later builds overwrite the same file.

If you prefer the folder variant (starts instantly, because nothing is unpacked):

```powershell
.\build_exe.bat folder
```

That produces `Program gotowy (bez instalatora)\MAKMOUSE\` — about **90 MB**,
containing `MAKMOUSE.exe` and an `_internal` folder with the Qt libraries.

### 2. Move it to the target computer

* **single-file variant** — copy `MAKMOUSE.exe` alone, anywhere,
* **folder variant** — copy the **whole folder** `MAKMOUSE` (the `.exe` without
  `_internal` will not start).

On the target computer put it anywhere, e.g.:

```
C:\Program Files\MAKMOUSE\
C:\Users\<name>\MAKMOUSE\
```

> If you pick `C:\Program Files`, copying will ask for administrator consent. The
> application itself **does not need** administrator rights — unless it has to
> work over a window of a program running as administrator.

### 3. Run it

Double-click `MAKMOUSE.exe`. The window comes up and an icon appears in the tray.

Windows SmartScreen may show *"Windows protected your PC"* on first run — that is
normal for an unsigned file. *More info → Run anyway*. To make the warning go
away for good, the file would have to be signed with a code-signing certificate
(paid, issued to a company or a person).

### 4. (optional) Shortcut and autostart

Desktop shortcut: right-click `MAKMOUSE.exe` → *Show more options* → *Send to* →
*Desktop (create shortcut)*.

Autostart at logon — press `Win`+`R`, type `shell:startup`, and paste a
**shortcut** to `MAKMOUSE.exe` into the folder that opens.

### 5. Move your settings (optional)

The configuration is **not** part of the package — on a new computer the
application starts with factory settings. To move yours:

1. on the old computer: *Settings → Export…* → save `makmouse-config.json`,
2. on the new one: *Settings → Import…* → point at that file.

Alternatively, copy the `%APPDATA%\MAKMOUSE\config.json` file directly.

The exported file also carries the chosen **language**, the theme and every
profile.

---

## B. Source code + Python (for development)

### 1. Install Python

Get **3.10 or newer** from [python.org](https://www.python.org/downloads/windows/)
(the project was built on 3.14). During installation tick **"Add python.exe to
PATH"**.

### 2. Copy the project

Move the `MAKKEY` folder (or clone the repository). These are enough:

```
run.py  MAKMOUSE.bat  build_exe.bat  MAKMOUSE.spec  MAKMOUSE-onefile.spec
makmouse.ico  makmouse\  fusion_addin\
```

The `build\`, `dist\`, `__pycache__\` and `.mypy_cache\` folders are generated —
there is no need to copy them.

### 3. Install the dependency

```powershell
python -m pip install PySide6-Essentials
```

That is the only external dependency. The whole system layer (Raw Input, hooks,
`SendInput`, reading USB descriptors) goes through the built-in `ctypes` — no
pywin32 and no HID libraries.

Recommended, though optional — a virtual environment:

```powershell
cd d:\MAKKEY
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install PySide6-Essentials
```

### 4. Run it

```powershell
python run.py
```

Without a console window: double-click [MAKMOUSE.bat](MAKMOUSE.bat) or run
`pythonw run.py`.

---

## C. Installer (distribution to many people)

PyInstaller produces a folder, not an installer. If you need a classic
"Next → Next → Finish" wizard, build the package from route A and wrap it.

A ready-made script is in the repository:
**[Program instalacyjny (exe)/MAKMOUSE.iss](<Program instalacyjny (exe)/MAKMOUSE.iss>)**.
You do not need to write one from scratch — just build it.

### The easy way: one click

**1. Install Inno Setup** — [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
(free). The script was verified on **6.7.3**.

**2. Double-click [build_installer.bat](build_installer.bat)** in the project
folder. The script finds Inno Setup, builds the folder variant of the program
(`build_exe.bat folder` — checks Python and the libraries, asks before closing a
running MAKMOUSE) and compiles the installer. It takes 1–2 minutes.

Result: `Program instalacyjny (exe)\Output\MAKMOUSE-1.3.3-setup.exe`, about
**26 MB** (the installer compresses the 91 MB package into a single file).

### By hand, step by step

**1. Build the folder variant of the program** — the installer only wraps it:

```powershell
cd d:\MAKMOUSE
.\build_exe.bat folder
# or with PyInstaller alone:
python -m PyInstaller --noconfirm --clean MAKMOUSE.spec
```

**2. Compile the installer** — from the command line:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "d:\MAKMOUSE\Program instalacyjny (exe)\MAKMOUSE.iss"
```

or open `MAKMOUSE.iss` in *Inno Setup Compiler* and press **F9**.

### ⚠ The most common compile error

```
Brak dist\MAKMOUSE\MAKMOUSE.exe - najpierw zbuduj wersje FOLDEROWA programu ...
```

("dist\MAKMOUSE\MAKMOUSE.exe is missing — build the FOLDER variant first".) The
installer packages the **folder variant** (`dist\MAKMOUSE\`). Plain
`build_exe.bat` (without `folder`) produces a single file `dist\MAKMOUSE.exe`,
which the script does not use. Do step 1 or use `build_installer.bat`.

The script resolves paths from **its parent directory**, so the `.iss` file has
to live in a subfolder of the project (as it does now: `Program instalacyjny (exe)\`);
where you run the compiler from does not matter. A copy saved elsewhere, e.g. in
*Documents*, reports that it cannot open `makmouse\__init__.py`.

### What this installer does

| Item | Behaviour |
|---|---|
| Target directory | `C:\Program Files\MAKMOUSE` (changeable in the wizard) |
| Install without admin | yes — the wizard asks "for everyone / just for me" |
| Wizard language | Polish and English, chosen at the start |
| Desktop shortcut | optional (a tick box) |
| Start with Windows | optional (a tick box) |
| Fusion 360 add-in | optional — copies the files straight into `%APPDATA%` |
| Running MAKMOUSE | detected via `AppMutex` — the wizard asks you to close it instead of failing on locked files |
| Upgrade | the new version replaces the old one; the old `_internal` folder is removed before copying |
| System | Windows 10/11, 64-bit — on anything older the wizard refuses to install |
| Uninstall | complete, through *Apps & features* |
| Configuration | **not deleted** on uninstall — it is your data |

The Fusion add-in also **always** lands in `{app}\fusion_addin\MAKMOUSE`, so it can
be copied by hand later too.

### Version and AppId

The installer takes the version number from `makmouse/__init__.py` by itself:

```python
__version__ = "1.3.3"
```

When releasing a new version you change it **only there** — the file name
`MAKMOUSE-<version>-setup.exe` and the version in *Apps & features* follow.

**Do not change `AppId`.** It identifies the program on upgrade — replace it and
the new version installs *next to* the old one instead of replacing it.

### Silent install (mass deployment)

```powershell
MAKMOUSE-1.3.3-setup.exe /VERYSILENT /NORESTART /MERGETASKS="desktopicon,startupicon"
```

Useful switches: `/DIR="C:\path"`, `/CURRENTUSER` (no admin), `/LOG="file.log"`,
`/MERGETASKS="!desktopicon"` (turns a task off).

### Alternative: MSI

If the **MSI** format is required (GPO or Intune deployments), Inno Setup does not
produce one — you need the **[WiX Toolset](https://wixtoolset.org/)**. It is
considerably harder; worth it only when MSI is a hard requirement from an IT
department.

---

## The Fusion 360 add-in

The add-in is separate from the application and is installed on the Fusion side.

1. Copy the **whole folder** `fusion_addin\MAKMOUSE` (both the `.py` **and** the
   `.manifest`) into:

   ```
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
   ```

   The end result should be `...\AddIns\MAKMOUSE\MAKMOUSE.py`.

2. In Fusion: *Utilities → Scripts and Add-Ins* (`Shift`+`S`) → the **Add-Ins**
   tab → `MAKMOUSE` → **Run**. Tick **Run on Startup**.

3. Check: in MAKMOUSE, in the profile panel, *Add-in connected (1)* should appear.

If something is off, the add-in writes a log to `%TEMP%\makmouse_addin.log` —
type `%TEMP%` into the Explorer address bar.

---

## Things to watch out for

**Firewall / antivirus.** MAKMOUSE opens a TCP socket on `127.0.0.1:8765` for the
add-in. That is purely local traffic — Windows Firewall usually does not ask, but
if it does, the **private** network is enough. You can change the port in the
configuration (`"bridge_port"`).

**Single instance.** The application guards itself with a mutex — a second launch
only shows a message and exits. If the window "disappeared", look for the icon in
the tray.

**The device.** No driver is needed on the new computer (the HID class is built
into Windows), but the USB descriptor still has to contain the text `MAKMOUSE` in
`iProduct` or `iManufacturer` — otherwise the application will not recognise it.

**Without MAKMOUSE running, the device does nothing.** That is not a fault, it is
the price of full separation from your ordinary mouse.
