# MAKMOUSE — struktura kodu (wersja 1.3.3)

Mapa programu: co jest w którym pliku, za co odpowiada każda część i jak dane
płyną od urządzenia do programu CAD. Nie opisuje każdej linijki — ma pozwolić
szybko trafić we właściwe miejsce.

Każdy plik z kodem zaczyna się od nagłówka o tym samym układzie:

* **ZA CO ODPOWIADA** — jakie aspekty programu obsługuje,
* **NAJWAŻNIEJSZE ELEMENTY** — klasy i funkcje, od których warto zacząć czytanie,
* **POWIĄZANIA** — z czego plik korzysta i kto korzysta z niego,
* **SZCZEGÓŁY** (nie wszędzie) — techniczne wyjaśnienia, dlaczego coś działa tak, a nie inaczej.

Spis treści:

1. [Program w pigułce](#1-program-w-pigułce)
2. [Mapa plików](#2-mapa-plików)
3. [Warstwy programu](#3-warstwy-programu)
4. [Opis plików](#4-opis-plików)
5. [Jak płyną dane — scenariusze krok po kroku](#5-jak-płyną-dane--scenariusze-krok-po-kroku)
6. [Wątki](#6-wątki)
7. [Plik konfiguracji config.json](#7-plik-konfiguracji-configjson)
8. [Gdzie szukać, gdy chcesz zmienić…](#8-gdzie-szukać-gdy-chcesz-zmienić)
9. [Zasady obowiązujące w kodzie](#9-zasady-obowiązujące-w-kodzie)

---

## 1. Program w pigułce

MAKMOUSE czyta surowe raporty z urządzenia (gałka X/Y, pierścień, przyciski
boczne), sprawdza, który program jest na pierwszym planie, wybiera dla niego
profil i zamienia ruchy urządzenia na akcje: skróty klawiszowe, gesty myszy
albo polecenia dla dodatku w Fusion 360.

```
 urządzenie MAKMOUSE ── USB HID, raport 5 bajtów: [ID][X][Y][pierścień][przyciski]
        │
        ▼  Windows Raw Input (komunikat WM_INPUT)
 ┌─────────────────────┐
 │ engine.py           │  InputEngine: raport -> zdarzenia InputEvent
 │                     │  (button / axis / wheel / report)
 └─────────┬───────────┘
           ▼  callback on_event(...)
 ┌──────────────────────────────────────────────────────────────────────┐
 │ controller.py  Controller                                            │
 │                                                                      │
 │  profil = cfg.active_profile(exe)  ◄── appwatch.py (aktywny program) │
 │                                                                      │
 │  axis   ─► _on_axis ──┬─ sterowanie wprost ─► bridge.py ─────────────────► dodatek z profilu (Fusion 360 / SolidCraft)
 │                       └─ emulacja ─► navigator.py ─► output.py ──────────► Windows (kursor, przyciski)
 │  button ─► _press / _release ─► skrót / przytrzymanie / nawigacja / widok  │
 │  wheel  ─► _do_wheel ─► scroll albo zoom w dodatku (skok = czułość zoomu)  │
 │                                                                      │
 │  każde zdarzenie ─► sygnał sig_event ────────────────────────────────────► ui/main_window.py
 └──────────────────────────────────────────────────────────────────────┘      (podgląd, Monitor)
```

Konfigurację (profile, przyciski, czułości) trzyma `profiles.py`, a okno
(`ui/main_window.py`) zmienia ją na żywo i przekazuje kontrolerowi.

---

## 2. Mapa plików

```
MAKMOUSE/
├── run.py                      START programu: konfiguracja, kontroler, okno, pętla Qt
├── MAKMOUSE.bat                uruchomienie z kodu bez okna konsoli
├── build_exe.bat               budowa gotowego .exe (jeden plik albo folder)
├── build_installer.bat         budowa instalatora: build_exe.bat folder + Inno Setup
├── MAKMOUSE.spec               przepis PyInstallera - wersja folderowa (dla instalatora)
├── MAKMOUSE-onefile.spec       przepis PyInstallera - jeden plik .exe
├── makmouse.ico                ikona pliku .exe
├── config.json                 Twoja bieżąca konfiguracja - wskazana w Ustawieniach
│                               jako miejsce zapisu (patrz rozdz. 7)
│
├── makmouse/                   KOD PROGRAMU
│   ├── __init__.py             numer wersji i nazwa aplikacji
│   ├── __main__.py             pozwala uruchomić: python -m makmouse
│   │
│   ├── winapi.py               dostęp do Windows API (ctypes) - fundament
│   ├── devices.py              wyszukiwanie urządzenia MAKMOUSE
│   ├── engine.py               silnik wejścia: odbiór i rozkodowanie raportów
│   ├── output.py               wyjście: udawanie klawiatury i myszy (SendInput)
│   ├── appwatch.py             który program jest na pierwszym planie
│   │
│   ├── controller.py           "mózg": zdarzenie -> profil -> akcja
│   ├── navigator.py            gesty myszy dla CAD + ustawienia osi profilu
│   ├── bridge.py               serwer TCP dla dodatków (Fusion 360, SolidCraft)
│   ├── profiles.py             model konfiguracji, profile, zapis/odczyt pliku
│   ├── keys.py                 nazwy klawiszy <-> kody Windows
│   ├── i18n.py                 tłumaczenia PL / EN
│   │
│   └── ui/                     INTERFEJS (PySide6)
│       ├── __init__.py         spis zawartości folderu
│       ├── main_window.py      okno główne, zakładki, zasobnik
│       ├── widgets.py          własne kontrolki (karty, kafle przycisków, suwaki, ...)
│       ├── device_view.py      rysowana grafika urządzenia - podgląd na żywo
│       ├── theme.py            kolory, motyw, kolor wiodący, arkusz stylów, ikona
│       └── help_dialog.py      instrukcja pod przyciskiem "i"
│
├── fusion_addin/MAKMOUSE/      DODATEK DO FUSION 360 (działa wewnątrz Fusiona)
│   ├── MAKMOUSE.py             odbiór danych z MAKMOUSE i ruch kamery przez API Fusiona
│   └── MAKMOUSE.manifest       opis dodatku dla Fusiona (JSON)
│
├── Program instalacyjny (exe)/
│   ├── MAKMOUSE.iss            skrypt instalatora Inno Setup
│   └── Output/                 zbudowane instalatory
├── Program gotowy (bez instalatora)/
│   ├── MAKMOUSE.exe            wynik build_exe.bat (jeden plik)
│   └── MAKMOUSE/               wynik build_exe.bat folder
│
├── README.md / README.en.md    opis funkcji programu dla użytkownika
├── INSTALL.md                  instalacja, budowanie .exe i instalatora
├── ADDONS.md                   jak napisać dodatek do innego programu CAD (protokół mostu)
└── STRUKTURA.md                ten dokument
```

Pliki i foldery **niezwiązane z programem** (można je pominąć przy czytaniu):

| Co | Skąd się wzięło |
|---|---|
| `build/`, `dist/` | robocze wyjście PyInstallera — kasowane i tworzone od nowa przy każdym budowaniu |
| `__pycache__/`, `.mypy_cache/` | pamięć podręczna Pythona i sprawdzania typów |
| `main.c` (pusty), `main.obj`, `main.pdb`, `vc140.pdb`, `.vscode/tasks.json` | pozostałość po zadaniu kompilacji C w VS Code — nie mają nic wspólnego z MAKMOUSE |

---

## 3. Warstwy programu

Program jest ułożony warstwami. Niższa warstwa nie wie nic o wyższej —
np. silnik nie zna profili, a `output.py` nie wie, po co coś naciska.

| Warstwa | Pliki | Rola |
|---|---|---|
| **Start** | `run.py` | składa wszystko w całość i uruchamia |
| **Interfejs** | `ui/*` | pokazuje stan, zmienia konfigurację |
| **Logika** | `controller.py`, `navigator.py`, `bridge.py` | decyduje, co zrobić ze zdarzeniem |
| **Dane** | `profiles.py`, `keys.py`, `i18n.py` | konfiguracja, słowniki, tłumaczenia |
| **System** | `engine.py`, `output.py`, `devices.py`, `appwatch.py` | rozmowa z Windows: wejście i wyjście |
| **Fundament** | `winapi.py` | surowe wywołania Windows API |

---

## 4. Opis plików

### 4.1. Start

#### `run.py` — punkt startowy

Kolejność startu w `main()`:

1. `_single_instance()` — muteks `Global\MakmouseRemapperSingleton`; druga kopia
   programu pokazuje komunikat i kończy się (ten sam muteks sprawdza instalator),
2. `profiles.load()` — wczytanie konfiguracji,
3. ustawienie języka (`i18n`), motywu i koloru wiodącego (`theme`), nadanie arkusza stylów,
4. `Controller(cfg)` — logika programu,
5. `WindowHost.build()` — okno główne,
6. `controller.start()` — start silnika, mostu i wątków pomocniczych,
7. `app.exec()` — pętla zdarzeń Qt aż do zamknięcia.

`WindowHost` trzyma okno i **buduje je od nowa po zmianie języka** (tłumaczenia
trafiają do kontrolek w chwili tworzenia). Kontroler i urządzenie działają
w tym czasie bez przerwy.

#### `makmouse/__init__.py`, `makmouse/__main__.py`

`__version__` — jedyne miejsce z numerem wersji (skrypt instalatora `.iss`
odczytuje go stąd sam). `__main__.py` pozwala uruchomić program przez `python -m makmouse`.

---

### 4.2. Warstwa systemowa

#### `winapi.py` — Windows API przez ctypes

Stałe Windows (`WM_INPUT`, `RIDEV_*`, `MOUSEEVENTF_*`, …), struktury C
(`RAWINPUT`, `RAWHID`, `INPUT`, `MOUSEINPUT`, `KEYBDINPUT`, `MSLLHOOKSTRUCT`, …)
i deklaracje funkcji `user32` / `kernel32`. Dzięki temu program nie potrzebuje
pywin32. Dwie funkcje pomocnicze: `virtual_screen_rect()` (obszar wszystkich
monitorów) i `cursor_pos()`. `MAKMOUSE_SIGNATURE` oznacza zdarzenia wygenerowane
przez sam program.

#### `devices.py` — wyszukiwanie urządzenia

| Element | Co robi |
|---|---|
| `enumerate_devices()` | lista wszystkich urządzeń wejściowych z Raw Input |
| `describe(handle)` | `DeviceInfo` dla jednego urządzenia: typ, VID/PID, kolekcja, nazwy |
| `device_strings(path)` | nazwa producenta i produktu z deskryptora USB (`hid.dll`) |
| `DeviceInfo.is_makmouse` | czy w nazwie jest `TARGET_NAME = "MAKMOUSE"` — **tylko to decyduje, czy urządzenie jest nasze** |
| `HID_USAGES`, `MOUSE_USAGES` | kolekcje, na które zapisuje się silnik (MAKMOUSE to *Multi-axis Controller* 0x01/0x08) |

#### `engine.py` — silnik wejścia

`InputEngine` to osobny wątek z własną pętlą komunikatów Windows i niewidocznym
oknem (message-only), do którego Windows wysyła `WM_INPUT`.

| Element | Co robi |
|---|---|
| `run()` / `_setup()` / `_teardown()` | życie wątku: okno, pętla komunikatów, sprzątanie |
| `apply_config(EngineConfig)` | nowe ustawienia (np. po zmianie profilu); źródła wejścia przelicza `_sync_sources()` w wątku silnika |
| `_process_raw()` | odbiera jeden `WM_INPUT`, sprawdza (`_is_target`), czy pochodzi z MAKMOUSE |
| `_decode_hid_report()` | **serce silnika**: raport → zdarzenia `button` (zmiana bitu), `wheel` (bajt pierścienia), `axis` (bajty X/Y), `report` (surowe bajty do Monitora) |
| `_handle_raw_mouse()`, `_mouse_proc()`, `_should_block_mouse()` | tryb „Mysz” dla starego firmware'u: hook `WH_MOUSE_LL` blokujący oryginalne zdarzenia (w trybie HID nieużywane) |
| `HidLayout`, `AxisSpec` | gdzie w raporcie leżą osie, pierścień i bity przycisków |
| `InputEvent` | zdarzenie przekazywane dalej (`kind`, `index`, `pressed`, `dx`, `dy`, `raw`) |

W trybie surowego HID silnik nie zakłada hooka ani nie rejestruje kolekcji
Mouse — zwykła mysz nie przechodzi przez kod MAKMOUSE.

#### `output.py` — wyjście (SendInput)

Jedyne miejsce, w którym program coś „naciska”. Wszystko idzie przez
`_send()` → `SendInput`, ze znacznikiem `MAKMOUSE_SIGNATURE`.

| Funkcja | Używana do |
|---|---|
| `tap_hotkey("Ctrl+Z")` | akcja *Skrót klawiszowy* |
| `hold_hotkey(text, down)` | akcje przytrzymania, modyfikatory gestów |
| `mouse_button(button, down)` | wciskanie LPM/SPM/PPM/4/5 (gesty, przytrzymanie) |
| `wheel(clicks)` | scroll; `clicks` może być ułamkiem — tak działa skok zoomu (0,3 = 36 zamiast 120) |
| `move_absolute(x, y)` | ruch kursora prowadzony przez Navigator |
| `move_relative`, `mouse_click`, `key_down/up` | pomocnicze |

Klawisze są wysyłane kodami skanowania (scancode) — tak najpewniej reagują na
nie programy CAD.

#### `appwatch.py` — aktywny program

`AppWatcher` co 0,35 s sprawdza `foreground_process()` (nazwa `.exe` okna na
pierwszym planie) i przy zmianie woła `Controller._on_app_changed`.

---

### 4.3. Logika

#### `controller.py` — mózg programu

**`Controller`** (QObject) łączy wszystko. Sygnały do okna:
`sig_event` (zdarzenie do podglądu), `sig_profile` (aktywny profil),
`sig_device_state` (podłączony/nie), `sig_enabled`, `sig_error`, `sig_action`
(tekst na pasku stanu), `sig_devices`.

| Grupa | Metody | Co robią |
|---|---|---|
| Start/stop | `start()`, `stop()`, `release_everything()` | uruchamia silnik, most, obserwatora, skrót awaryjny; puszcza wszystko, co trzymane |
| Urządzenie | `refresh_devices()`, `device_present` | szuka MAKMOUSE i przekazuje jego ścieżki silnikowi |
| Konfiguracja | `apply(cfg)`, `set_enabled()`, `_push_engine_config()`, `axes` | przyjmuje nową konfigurację z okna; wylicza `EngineConfig` |
| Profil | `_on_app_changed(exe)` | wybór profilu dla aktywnego programu, ustawienia osi do Navigatora |
| Wejście | `_on_engine_event()` | rozdział: `axis` od razu do `_on_axis`, `button`/`wheel` do kolejki akcji |
| Gałka | `_on_axis()`, `_shape_axes()`, `_direct()` | patrz scenariusze B i C w rozdz. 5 |
| Przyciski | `_dispatch()`, `_press()`, `_release()`, `_activate()`, `_deactivate()` | akcje przycisków bocznych, przełącznik (toggle), widoki Fusiona |
| Pierścień | `_do_wheel()` | patrz scenariusz D |
| Monitor | `_emit_monitor()` | wysyła zdarzenia do okna, osie i raporty najwyżej co 50 ms |
| Awaryjny | `_panic_loop()` | skrót (domyślnie `Ctrl+Alt+F12`): puść wszystko i włącz/wyłącz MAKMOUSE |

Ważne pola: `_held` (przyciski, które teraz coś trzymają — także włączone
przełączniki), `_direct_mode` (tryb nawigacji włączony przyciskiem przy
sterowaniu wprost — decyduje o czułości orbity/przesuwania).

Dwie klasy pomocnicze:

* **`AxisGesture`** — gest gałki prowadzony przez Navigator. Gałka nie ma
  „puszczenia”, więc gest kończy się po 0,25 s bez ruchu (`AXIS_IDLE`), chyba
  że przycisk boczny trzyma go otwartym.
* **`GestureHold`** — modyfikator trzymany w trakcie scrolla (np. `Ctrl` przy
  obrocie pierścienia), zwalniany po 0,25 s ciszy.

#### `navigator.py` — gesty myszy dla CAD

Używany, gdy **nie** działa sterowanie wprost. Program CAD orbituje tylko
wtedy, gdy dostanie wciśnięty przycisk myszy i ruch kursora — Navigator to
syntezuje.

| Element | Co robi |
|---|---|
| `Navigator.start(mode, preset)` | zapamiętuje kursor, opcjonalnie centruje go w oknie, wciska klawisze i przycisk z presetu, startuje wątek 120 Hz |
| `Navigator.feed(dx, dy)` | dokłada ruch gałki (z odwróceniem i zamianą osi) |
| `Navigator._tick()` | co 1/120 s: ruch kursora × czułość trybu → `output.move_absolute`; w trybie „kółko myszy” zamienia ruch na kliknięcia scrolla ze skokiem `sens_zoom` |
| `Navigator._reanchor()` | przy krawędzi ekranu: puść przycisk → kursor na środek → wciśnij (obrót bez końca) |
| `Navigator.stop()` / `_stop_locked()` | puszcza wszystko; kursor zostaje albo wraca — wg `keep_cursor` |
| `AxisSettings` | **ustawienia osi profilu** (zakładka *Nawigacja 3D → Osie X/Y*): `sens_move`, `sens_orbit`, `sens_pan`, `sens_zoom`, `invert_x/y`, `swap_xy`, `recenter`, `center_on_start`, `keep_cursor`; `sens_for(tryb)` zwraca właściwą czułość |
| `NavPreset` | co trzymać dla trybu orbita/przesuwanie/zoom (tabela *Gesty programu*) |
| `HoldPreset` | co trzymać podczas gestu ciągłego (*Gesty ciągłe*) |

Gest, który nic nie trzyma (zwykły ruch kursora), pomija centrowanie
i przepinanie przy krawędzi.

#### `bridge.py` — most do dodatku 3D

Serwer TCP na `127.0.0.1:8765`. Dodatek w Fusionie i SolidCraft (obsługa
wbudowana w program) łączą się jako klienci. Jeden obiekt JSON na linię:

| Paczka | Znaczenie |
|---|---|
| `{"t":"hello","server":"MAKMOUSE","device":"MAKMOUSE"}` | powitanie od MAKMOUSE zaraz po połączeniu |
| `{"t":"hello","app":"solidcraft"}` | powitanie od dodatku: który to program (dodatek Fusiona go nie wysyła) |
| `{"t":"axis","x":…,"y":…}` | przyrost osi gałki (już z czułością) |
| `{"t":"zoom","d":…}` | kliknięcie zoomu (już ze skokiem `sens_zoom`) |
| `{"t":"view","name":"front"}` | widok standardowy |
| `{"t":"mode","mode":"pan","on":true}` | chwilowa zmiana trybu nawigacji |

`send(payload, addon)` tylko wrzuca paczkę do kolejki (max 256, najstarsze
wypadają) — wysyła ją osobny wątek, i to tylko do dodatków programu `addon`
z profilu (`"fusion"`, `"solidcraft"`; dodatek bez powitania to `"fusion"`).
Silnik nigdy nie czeka na sieć. Każdy klient ma też wątek czytający jego
powitanie, który od razu zauważa rozłączenie. `clients_for(addon)` mówi, czy
dodatek danego programu jest podłączony. Protokół dla innych programów:
`ADDONS.md`.

#### `profiles.py` — konfiguracja

| Klasa / funkcja | Co przechowuje / robi |
|---|---|
| `Config` | cała konfiguracja: `enabled`, `device`, `button_count` (3/6), `panic_hotkey`, `start_minimized`, `theme`, `accent`, `language`, `bridge_*`, `profiles`; `active_profile(exe)` wybiera profil |
| `Profile` | `name`, `match` (lista `.exe`), `is_default`, `enabled`, `buttons` (1–6 → `Binding`), `nav` (orbita/przesuwanie/zoom → `NavPreset`), `gestures` (move/scroll → `HoldPreset`), `axes` (`AxisSettings`), `direct` (sterowanie wprost) |
| `Binding` | akcja przycisku: `type` (`none`/`nav`/`hotkey`/`hold`/`view`), `hotkey`, `button`, `nav`, `view`, `toggle`, `enabled`; `describe()` — tekst do legendy, `is_active()` — czy przycisk ma coś robić |
| `DeviceConfig` | tryb odczytu (`hid`/`mouse`) i układ raportu `HidLayout` |
| `ACTION_TYPES`, `NAV_MODES`, `GESTURES`, `VIEW_ACTIONS` + `*_LABELS` | listy wartości i ich polskie nazwy (tłumaczone przy wyświetleniu) |
| `default_profiles()`, `_cad_profile()` | profile fabryczne: Fusion 360 (domyślny, sterowanie wprost), Inventor, Blender, SolidWorks, SketchUp, Rhino |
| `default_hid_layout()` | raport firmware'u: ID 1, X w bajcie 1, Y w 2, pierścień w 3, przyciski w bajcie 4 (bity 0–5) |
| `load()`, `save()` | odczyt i zapis JSON (zapis przez plik `.tmp`, żeby nie uszkodzić configu przy awarii) |
| `config_path()`, `set_config_path()` | gdzie leży config (wskaźnik w `%APPDATA%\MAKMOUSE\location.json`) |
| `_extend_button_bits()`, `legacy_axes` | przenoszenie starszych konfiguracji (3 bity → 6, osie globalne → w profilach) |

#### `keys.py` — klawisze

Tabele nazw klawiszy → kody VK (`VK`, `MODIFIERS`, `ALIASES`),
`parse_hotkey("Ctrl+Shift+E")` → `([VK_CTRL, VK_SHIFT], VK_E)`,
`format_hotkey()` (odwrotnie), przyciski myszy `MOUSE_BUTTONS` z nazwami
`mouse_label()`.

#### `i18n.py` — tłumaczenia

`tr("polski tekst")` zwraca tekst w bieżącym języku. Słownik `_EN` mapuje
polski tekst źródłowy na angielski. Brak wpisu = polski oryginał (nic się nie
psuje). `set_language("pl"|"en")`, `LANGUAGES` — lista w Ustawieniach.

---

### 4.4. Interfejs (`makmouse/ui/`)

#### `main_window.py` — okno główne

Klasa **`MainWindow`**. Układ okna:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MAKMOUSE  ● MAKMOUSE (stan)                      (i)  ☀/☾   Aktywny [══●]    │  _build_topbar
├────────────┬──────────────────────┬──────────────────────────────────────────┤
│ PROFILE    │ PODGLĄD NA ŻYWO      │ [Przyciski i gesty][Nawigacja 3D][...]   │
│ ☑ Fusion   │   (DeviceView)       │                                          │
│ ☑ Inventor │                      │   zawartość zakładki                     │  _tab_*
│ ...        │ Przycisk 1  ...   ●  │                                          │
│ Nazwa, exe │ Ruch myszy  ...      │                                          │
│ ☐ Domyślny │ Scroll      ...      │                                          │
├────────────┴──────────────────────┴──────────────────────────────────────────┤
│ pasek stanu: ostatnia akcja                         ścieżka config.json      │
└──────────────────────────────────────────────────────────────────────────────┘
   _build_sidebar      _build_device_panel                 _build_tabs
```

Metody pogrupowane według tego, czym się zajmują:

| Obszar | Metody | Opis |
|---|---|---|
| Budowa okna | `_build_ui`, `_build_topbar`, `_build_sidebar`, `_build_device_panel`, `_build_tabs`, `_build_tray`, `_build_config_path_card`, `_scroll` | tworzą kontrolki; wywoływane raz, w konstruktorze |
| Zakładki | `_tab_buttons`, `_tab_navigation`, `_tab_device`, `_tab_monitor`, `_tab_settings` | treść pięciu zakładek |
| Elementy zależne od liczby przycisków | `_rebuild_button_cards`, `_rebuild_legend_rows`, `_rebuild_lamps` | kafle, wiersze legendy i lampki Monitora — przebudowywane po zmianie 3↔6 |
| Profile | `load_profile_list`, `profile` (bieżący), `_on_profile_selected`, `_load_profile_into_ui`, `_load_axes_into_ui`, `_on_profile_item_changed` (kwadracik wł./wył.), `_on_profile_meta` (nazwa, `.exe`, sterowanie wprost), `_on_default_toggled`, `_add_profile`, `_duplicate_profile`, `_delete_profile` | lista profili i wpisywanie wybranego profilu do kontrolek |
| Przyciski i gesty | `_on_binding_changed`, `_on_gesture_changed`, `_sync_direct_sections` (chowa *Gesty ciągłe* przy sterowaniu wprost) | reakcje na zmiany w zakładce |
| Nawigacja 3D | `_on_nav_changed`, `_sync_nav_enabled`, `_on_axes_changed`, `_refresh_move_hint`, `_update_bridge_label` | tabela gestów programu, czułości, stan dodatku (odświeżany co 1 s) |
| Legenda i podgląd | `_refresh_legend` (opisy + zielone/czerwone kropki), `_on_input_event`, `_axis_norm`, `_on_report`, `_set_pressed`, `_log` | zdarzenia z urządzenia → grafika, legenda, Monitor |
| Stan urządzenia | `_on_device_state`, `_refresh_device_status`, `refresh_devices`, `_fill_device_table`, `_on_enabled`, `_on_error`, `_on_profile_active` | kropka w pasku górnym, zakładka Urządzenie |
| Ustawienia | `_on_language`, `_on_globals`, `_sync_globals`, `_on_button_count`, `_on_accent`, `_on_theme_switch`, `_set_theme`, `_restyle` | język, skrót awaryjny, autostart, liczba przycisków, kolor wiodący, motyw |
| Plik konfiguracji | `_sync_config_path`, `_change_config_path`, `_reset_config_path`, `_open_config_dir`, `_export`, `_import`, `_reset`, `_adopt` | miejsce zapisu, eksport/import, przywrócenie fabrycznych |
| Zapis | `_touch`, `_save_now` | każda zmiana → `_touch()`: kontroler dostaje konfigurację od razu, zapis na dysk po 0,6 s ciszy |
| Okno i zasobnik | `_restore`, `_quit`, `closeEvent`, `detach`, `_connect_controller`, `_disconnect_controller`, `_show_help` | zamknięcie okna chowa je do zasobnika; `detach` przy odbudowie po zmianie języka |

**Flaga `_loading`**: gdy okno wpisuje profil do kontrolek, każda z nich
wysyła sygnał „zmieniono”. `_loading = True` na ten czas sprawia, że handlery
`_on_*` nic nie robią — inaczej wczytanie profilu nadpisywałoby go samym sobą.

#### `widgets.py` — własne kontrolki

| Kontrolka | Gdzie jej używa okno |
|---|---|
| `Card` | każda sekcja z tytułem (np. „OSIE X/Y”) |
| `ButtonCard` | kafel przycisku bocznego w *Przyciski i gesty*; kwadracik w rogu → `Binding.enabled` |
| `BindingEditor` | wnętrze kafla: typ akcji + parametry (lista trybów, pole skrótu, przycisk myszy, widok, *Przełącznik*); strony w `QStackedWidget`, jedna na typ akcji |
| `GestureEditor` | *Gesty ciągłe*: co trzymać podczas ruchu myszy / scrolla |
| `HotkeyEdit` | pole „kliknij i naciśnij skrót”; `mods_only=True` przyjmuje sam modyfikator (np. „Shift”) |
| `SliderRow` | czułości; `step=1.0` daje suwak całkowity, domyślnie krok 0,05 |
| `ToggleSwitch` | przełącznik *Aktywny* |
| `ThemeSwitch` | słońce/księżyc |
| `StatusPill` | kolorowa kropka: stan urządzenia w pasku górnym, stan przycisków w legendzie |
| `ButtonLamp`, `AxisBar` | lampki wciśniętych przycisków i paski osi w *Monitorze* |
| `combo()`, `hint()`, `row()` | lista rozwijana, która nie rozpycha okna; szary opis; wiersz kontrolek |

Kontrolki zmieniają obiekty konfiguracji bezpośrednio (np. `BindingEditor`
zapisuje do `Binding`), a sygnałem `changed` każą oknu wywołać `_touch()`.

#### `device_view.py` — grafika podglądu

`DeviceView` rysuje urządzenie w całości kodem (`QPainter`). `_geometry()`
liczy proporcje raz na rozmiar okna; `paintEvent()` rysuje warstwami:
cień → podstawa → opaska → przyciski → tył pierścienia → gałka → przód
pierścienia → strzałka kierunku. Stan animacji (`_buttons`, `_ax`, `_ay`,
`_wheel`) wygasa co klatkę (`_on_frame`, co 16 ms). `set_count(3|6)` zmienia
liczbę i rozmieszczenie przycisków na opasce (`BUTTON_ANGLES`).

#### `theme.py` — wygląd

Kolory są zmiennymi modułu (`T.ACCENT`, `T.TEXT`, `T.PANEL`, …), czytanymi
w chwili rysowania. `apply_mode("dark"|"light")` podmienia paletę,
`apply_accent(kod)` ustawia kolor wiodący i wylicza odcienie `ACCENT_DIM`
(ciemniejszy) i `ACCENT_SOFT` (jaśniejszy). `_qss()` to arkusz stylów Qt —
tu są m.in. marginesy i odstępy przycisków, pól i zakładek. `make_icon()`
rysuje ikonę programu (szarą, gdy MAKMOUSE jest wyłączony).

#### `help_dialog.py` — instrukcja

`HelpDialog` z treścią w HTML: `_html_pl()` i `_html_en()` (wybór wg języka),
`_style()` — kolory z motywu.

---

### 4.5. Dodatek do Fusion 360 (`fusion_addin/MAKMOUSE/`)

To **osobny program** — Fusion ładuje go sam z folderu
`%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\MAKMOUSE`.

| Element | Co robi |
|---|---|
| `run()` / `stop()` | start i koniec dodatku (woła je Fusion); rejestracja zdarzenia własnego |
| `_reader()` | wątek sieciowy: łączy się z MAKMOUSE, co sekundę ponawia, gdy go nie ma |
| `_consume(line)` | jedna paczka JSON → bufor `_pending` (osie, zoom), kolejka widoków, `_mode` |
| `_AxisHandler.notify()` | na wątku głównym Fusiona (API nie jest wielowątkowe) zbiera bufor i woła `_apply` |
| `_apply(dx, dy, dzoom, mode)` | orbita (obrót „stołu obrotowego”), przesuwanie, zoom wykładniczy — z obsługą kamery ortograficznej |
| `_apply_view(name)` | widok standardowy z zachowaniem celu i skali |
| `ORBIT_RAD_PER_UNIT`, `PAN_PER_UNIT`, `ZOOM_PER_TICK` | bazowe tempo kamery (czułości z MAKMOUSE mnożą to tempo) |
| `_log()` | dziennik w `%TEMP%\makmouse_addin.log` |

`MAKMOUSE.manifest` to plik JSON z opisem dodatku dla Fusiona (JSON nie
pozwala na komentarze, więc nie ma w nim nagłówka).

---

### 4.6. Budowanie i instalator

| Plik | Rola |
|---|---|
| `build_exe.bat` | jedno kliknięcie: sprawdza Pythona, doinstalowuje PySide6 i PyInstaller, zamyka działający MAKMOUSE, buduje, kopiuje do `Program gotowy (bez instalatora)` |
| `MAKMOUSE-onefile.spec` | przepis PyInstallera — jeden plik `.exe` |
| `MAKMOUSE.spec` | przepis PyInstallera — folder `exe + _internal` (używa go instalator) |
| `build_installer.bat` | jedno kliknięcie: `build_exe.bat folder`, odnalezienie Inno Setup, kompilacja `.iss` do `Program instalacyjny (exe)\Output` |
| `Program instalacyjny (exe)/MAKMOUSE.iss` | instalator Inno Setup: pakuje `dist\MAKMOUSE`, skróty, autostart, opcjonalny dodatek do Fusiona; wersję czyta z `makmouse/__init__.py` |
| `MAKMOUSE.bat` | uruchomienie z kodu bez konsoli (`pythonw run.py`) |

---

## 5. Jak płyną dane — scenariusze krok po kroku

### A. Naciśnięcie przycisku bocznego (np. przycisk 2 = `Ctrl+Z`)

1. `engine._decode_hid_report` — bit 1 bajtu 4 zmienił się na 1 → `InputEvent("button", index=2, pressed=True)`.
2. `Controller._on_engine_event` — zdarzenie trafia do kolejki `_actions` (silnik od razu wraca do Windows).
3. Wątek `MakmouseActions`: `_dispatch` → `_press(2)`.
4. `_press` bierze `Binding` z aktywnego profilu; `is_active()` sprawdza, czy przycisk jest włączony i ma akcję.
5. `_activate` → `output.tap_hotkey("Ctrl+Z")` → `SendInput`.
6. Równolegle `_emit_monitor` → `sig_event` → `MainWindow._on_input_event`: przycisk świeci na grafice, lampka w Monitorze, wpis w logu.
7. Puszczenie: `_release(2)` → `_deactivate` (dla skrótu nic, dla przytrzymania puszcza klawisze). Przy **przełączniku** puszczenie nic nie robi — akcję gasi dopiero kolejne wciśnięcie.

### B. Ruch gałki w Fusionie z dodatkiem (sterowanie wprost)

1. `engine` → `InputEvent("axis", dx, dy)`, wywołany od razu (nie przez kolejkę — liczy się opóźnienie).
2. `Controller._on_axis` → `_direct()` = profil ma `direct` i `bridge.client_count > 0`.
3. `_shape_axes` — zamiana/odwrócenie osi, mnożnik: `sens_move`, a gdy przycisk trzyma tryb nawigacji (`_direct_mode`) — `sens_pan` albo `sens_orbit`.
4. `bridge.send({"t":"axis", ...})` → wątek wysyłki → TCP → dodatek.
5. Dodatek: `_consume` → `_AxisHandler.notify` → `_apply` obraca kamerę. **Kursor się nie rusza.**

### C. Ruch gałki w innym programie (emulacja przeciągania)

1. `_on_axis`: brak sterowania wprost.
2. Jeśli przycisk boczny trzyma tryb nawigacji (np. przesuwanie) → `navigator.feed` (Navigator już działa w tym trybie, z `sens_pan`).
3. W przeciwnym razie → `AxisGesture.poke(gest „Ruch myszy” z profilu)` → `Navigator.start("move", ...)`: wciska modyfikatory/przycisk z gestu (albo nic — wtedy to zwykły ruch kursora).
4. Wątek `MakmouseNav` co 1/120 s: `_tick` → `output.move_absolute`.
5. 0,25 s bez ruchu → `AxisGesture` kończy gest → `Navigator.stop` puszcza wszystko; kursor zostaje albo wraca (`keep_cursor`).

### D. Obrót pierścienia

1. `engine` → `InputEvent("wheel", dx=±1)` na każdy impuls (20 na obrót).
2. Kolejka akcji → `_do_wheel`: `krok = dx × sens_zoom`.
3. Sterowanie wprost: `bridge.send({"t":"zoom","d":krok})` → dodatek zoomuje o proporcjonalny kawałek.
4. Inaczej: ewentualny modyfikator z *Gesty ciągłe → Scroll* (`GestureHold`), potem `output.wheel(krok)` — `WHEEL_DELTA = 120 × krok`, więc strona przewija się o proporcjonalnie mniej/więcej wierszy.

### E. Zmiana ustawienia w oknie

1. Kontrolka (np. suwak czułości) → handler `MainWindow._on_axes_changed`.
2. Handler wpisuje wartość do `self.profile.axes` (obiekt konfiguracji).
3. `_touch()` → `controller.apply(cfg)` (działa od razu) + start zegara zapisu.
4. Po 0,6 s bez kolejnych zmian `_save_now()` → `profiles.save()` → `config.json`.

### F. Przełączenie na inny program

1. `AppWatcher` wykrywa nowe okno na pierwszym planie → `Controller._on_app_changed("blender.exe", ...)`.
2. `cfg.active_profile(exe)` — pierwszy włączony profil, którego lista `.exe` pasuje; jak żaden — profil domyślny.
3. Przy zmianie profilu: `release_everything()` (nic nie zostaje wciśnięte), nowe ustawienia osi do Navigatora, `_push_engine_config()`.
4. `sig_profile` → wpis w logu Monitora.

---

## 6. Wątki

| Wątek | Plik | Co robi | Jak często |
|---|---|---|---|
| główny (Qt) | `run.py`, `ui/*` | okno, rysowanie, zapis konfiguracji | zdarzenia Qt |
| `MakmouseInputEngine` | `engine.py` | pętla komunikatów Windows, odbiór raportów, wywołanie `_on_axis` | każdy raport |
| `MakmouseActions` | `controller.py` | przyciski boczne i pierścień (kolejka akcji) | każde zdarzenie |
| `MakmouseNav` | `navigator.py` | ruch kursora w trakcie gestu | 120 Hz, tylko w trakcie gestu |
| `MakmouseAxisGesture` | `controller.py` | koniec gestu gałki po 0,25 s ciszy | co 40 ms |
| `MakmouseGesture` | `controller.py` | puszczenie modyfikatora scrolla po 0,25 s | co 40 ms |
| `MakmouseAppWatcher` | `appwatch.py` | aktywny program | co 0,35 s |
| `MakmousePanic` | `controller.py` | skrót awaryjny | co 60 ms |
| `MakmouseBridgeAccept`, `MakmouseBridgeWriter` | `bridge.py` | przyjmowanie połączeń, wysyłka do dodatku | na żądanie |
| `MakmouseBridgeReader` (jeden na dodatek) | `bridge.py` | powitanie dodatku, wykrycie rozłączenia | na żądanie |

Wątki poza głównym **nie dotykają okna** — komunikują się z nim wyłącznie
sygnałami Qt (`sig_*`), które Qt dostarcza do wątku głównego.

---

## 7. Plik konfiguracji `config.json`

Domyślnie `%APPDATA%\MAKMOUSE\config.json`; inne miejsce ustawia się w
*Ustawienia → Plik konfiguracji*, a program zapamiętuje je we wskaźniku
`%APPDATA%\MAKMOUSE\location.json`. U Ciebie wskaźnik prowadzi do
`D:\MAKMOUSE\config.json`, więc to ten plik w katalogu projektu jest
konfiguracją, z której program faktycznie korzysta. Struktura (wersja 2, od 1.3.2):

```jsonc
{
  "version": 2,
  "enabled": true,                 // przełącznik "Aktywny"
  "device": { "mode": "hid", "hid_layout": { ... } },   // układ raportu - stały dla firmware'u
  "button_count": 3,               // 3 albo 6
  "panic_hotkey": "Ctrl+Alt+F12",
  "start_minimized": false,        // "Autostart" - start w zasobniku
  "theme": "dark",                 // "dark" | "light"
  "accent": "#0080FF",             // kolor wiodący
  "language": "pl",                // "pl" | "en"
  "bridge_enabled": true, "bridge_port": 8765,
  "profiles": [
    {
      "name": "Fusion 360", "match": ["Fusion360.exe"],
      "is_default": true, "enabled": true, "direct": true,
      "buttons":  { "1": { "type": "nav", "nav": "pan", "toggle": true, "enabled": true, ... }, ... },
      "nav":      { "orbit": { "keys": "Shift", "button": "middle", "style": "drag", ... }, ... },
      "gestures": { "move": { "keys": "", "button": "" }, "scroll": { ... } },
      "axes":     { "sens_move": 1.0, "sens_orbit": 1.0, "sens_pan": 1.0, "sens_zoom": 1.0,
                    "invert_x": false, "invert_y": false, "swap_xy": false,
                    "recenter": true, "center_on_start": true, "keep_cursor": true }
    }
  ]
}
```

Brakujące pola dostają wartości domyślne, a nieznane są ignorowane — dlatego
starsze pliki wczytują się bez błędów.

---

## 8. Gdzie szukać, gdy chcesz zmienić…

| Chcę zmienić… | Gdzie |
|---|---|
| układ raportu HID (inne bajty, więcej przycisków) | `profiles.default_hid_layout()`, `engine._decode_hid_report()` |
| po czym program rozpoznaje urządzenie | `devices.TARGET_NAME`, `DeviceInfo.is_makmouse` |
| co się dzieje po naciśnięciu przycisku bocznego | `controller._press()`, `_activate()`, `_deactivate()` |
| dodać nowy typ akcji przycisku | `profiles.ACTION_TYPES` + `ACTION_LABELS` + `Binding`, `widgets.BindingEditor` (nowa strona), `controller._activate()` / `_deactivate()`, tłumaczenia w `i18n.py` |
| zachowanie gałki / kursora | `controller._on_axis()`, `navigator.Navigator` |
| skok zoomu / scroll | `controller._do_wheel()`, `navigator._tick()` (tryb kółka), `output.wheel()` |
| czułości orbity/przesuwania | `controller._shape_axes()` (dodatek), `navigator._tick()` (emulacja), `AxisSettings.sens_for()` |
| tempo kamery w Fusionie | stałe na górze `fusion_addin/MAKMOUSE/MAKMOUSE.py` |
| profile fabryczne | `profiles.default_profiles()`, `_cad_profile()` |
| nowe pole w konfiguracji | pole w `Config`/`Profile`/`AxisSettings` + `to_dict()` + `from_dict()` z wartością domyślną |
| kolory, motyw, odstępy | `ui/theme.py` (`_PALETTES`, `ACCENTS`, `_qss()`) |
| wygląd grafiki urządzenia | `ui/device_view.py` (`_geometry()`, `_draw_*()`) |
| nową kontrolkę w zakładce | `ui/main_window.py`: `_tab_*()` (tworzenie), `_load_*_into_ui()` (wczytanie), handler `_on_*()` (zapis) |
| teksty i tłumaczenia | `tr("...")` w kodzie + wpis w `i18n._EN` |
| instrukcję w programie | `ui/help_dialog.py` (obie wersje językowe) |
| skrót awaryjny | `Config.panic_hotkey`, `controller._panic_loop()` |
| numer wersji | `makmouse/__init__.py` (instalator bierze go stamtąd) |
| sposób budowania .exe | `build_exe.bat`, `MAKMOUSE-onefile.spec`, `MAKMOUSE.spec` |
| sposób budowania instalatora | `build_installer.bat`, `Program instalacyjny (exe)/MAKMOUSE.iss` |

---

## 9. Zasady obowiązujące w kodzie

* **Wszystkie napisy przez `tr()`** — i nowy wpis w `i18n._EN`. Kluczem jest polski tekst.
* **Wyjście tylko przez `output.py`** — nic poza nim nie woła `SendInput`.
* **Nowe pole konfiguracji = wartość domyślna** w `from_dict()` — inaczej stare pliki przestaną się wczytywać.
* **Po zmianie konfiguracji w oknie — `_touch()`**, a przy wczytywaniu kontrolek — `_loading = True`.
* **Wątki poza głównym nie dotykają okna** — tylko sygnały Qt.
* **Silnik i `_on_axis` muszą być szybkie** — są wołane przy każdym raporcie; cięższa praca idzie do kolejki akcji.
* **Komentarze po polsku**, tłumaczą *dlaczego*, a nie *co* — co robi kod, widać z kodu.
