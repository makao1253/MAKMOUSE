"""Tłumaczenia interfejsu - polski (źródłowy) i angielski.

ZA CO ODPOWIADA
    * wybór języka interfejsu i zapamiętanie bieżącego,
    * zamiana polskiego tekstu z kodu na tekst w wybranym języku (funkcja tr).
    Dodając w kodzie nowy napis tr("..."), trzeba dopisać jego tłumaczenie do
    słownika _EN poniżej - inaczej w wersji angielskiej zostanie po polsku.

NAJWAŻNIEJSZE ELEMENTY
    tr(text) ........... tłumaczenie tekstu na bieżący język
    set_language() ..... zmiana języka ("pl" / "en")
    LANGUAGES .......... języki na liście w zakładce Ustawienia
    _EN ................ słownik: polski tekst -> angielski

POWIĄZANIA
    Nie importuje nic z projektu. Używany przez prawie każdy moduł, który
    pokazuje jakiś napis.

SZCZEGÓŁY
Kluczem jest polski tekst źródłowy - dzięki temu kod czyta się tak samo jak
przed wprowadzeniem tłumaczeń, a brak wpisu w słowniku nie wywraca interfejsu,
tylko pokazuje polski oryginał.

Użycie:

    from .i18n import tr
    label = QLabel(tr("Zapisano konfigurację"))

Teksty z parametrami wstawiamy przez `.format()` **po** tłumaczeniu, żeby
kluczem pozostawał stały wzorzec:

    tr("Wyeksportowano do {path}").format(path=name)

Zmiana języka nie odświeża istniejących widgetów - okno główne jest po prostu
budowane od nowa (patrz `run.py`), bo to jedyny sposób, który nie zostawia
połowy interfejsu w poprzednim języku.
"""
from __future__ import annotations

# Kod języka -> nazwa pokazywana na rozwijanej liście (zawsze w tym języku).
LANGUAGES: list[tuple[str, str]] = [
    ("pl", "Polski"),
    ("en", "English"),
]

DEFAULT_LANGUAGE = "pl"

_language = DEFAULT_LANGUAGE


# --------------------------------------------------------------------------- #
# Słownik: polski tekst źródłowy -> tłumaczenie angielskie
# --------------------------------------------------------------------------- #
_EN: dict[str, str] = {
    # ----------------------------------------------------------- pasek górny --
    "Gotowe": "Ready",
    "Instrukcja obsługi": "User manual",
    "Aktywny": "Active",
    "Nieaktywny": "Inactive",
    "Motyw jasny / ciemny": "Light / dark theme",

    # -------------------------------------------------------------- profile --
    "Profile": "Profiles",
    "Dodaj": "Add",
    "Duplikuj": "Duplicate",
    "Usuń": "Delete",
    "Nazwa": "Name",
    "Pliki .exe (po przecinku)": ".exe files (comma separated)",
    "Profil domyślny": "Default profile",
    "Kwadracik przy nazwie włącza i wyłącza profil":
        "The box next to the name switches the profile on and off",
    "Sterowanie wprost (dodatek 3D)": "Direct control (3D add-in)",
    "Osie idą prosto do dodatku działającego w programie 3D, który sam\n"
    "przestawia kamerę. Kursor w ogóle się nie rusza.\n"
    "Gdy dodatek nie jest podłączony, profil sam wraca do\n"
    "emulacji przeciągania.":
        "Axes go straight to the add-in running inside the 3D application,\n"
        "which moves the camera itself. The cursor does not move at all.\n"
        "When no add-in is connected, the profile falls back to\n"
        "drag emulation on its own.",
    "Dodatek:": "Add-in:",
    "Odwróć zoom": "Invert zoom",
    "Odwraca kierunek obrotu pierścienia: przybliżanie zamienia się\n"
    "z oddalaniem - w zwykłym scrollu i w zoomie przez dodatek 3D.":
        "Reverses the ring's direction: zooming in becomes zooming out -\n"
        "in ordinary scrolling and in zoom through the 3D add-in.",
    "Program, którego dodatek dostaje osie przy sterowaniu wprost.\n"
    "Fusion 360: dodatek MAKMOUSE uruchomiony w Fusionie.\n"
    "SolidCraft: Preferencje -> Nawigacja -> Mysz 3D ->\n"
    "\"Nawiguj programem urządzenia na tym komputerze\".":
        "The application whose add-in receives the axes in direct control.\n"
        "Fusion 360: the MAKMOUSE add-in running in Fusion.\n"
        "SolidCraft: Preferences -> Navigation -> 3D mouse ->\n"
        "\"Navigate with a device app on this computer\".",
    "Nowy profil": "New profile",
    "{name} (kopia)": "{name} (copy)",
    "{name}  (domyślny)": "{name}  (default)",
    "Musi zostać przynajmniej jeden profil.": "At least one profile must remain.",

    # ---------------------------------------------------------------- most --
    "Dodatek 3D: sprawdzanie...": "3D add-in: checking...",
    "Most wyłączony w konfiguracji.": "Bridge disabled in the configuration.",
    "Ten profil używa emulacji przeciągania. Dodatków podłączonych: {count}.":
        "This profile uses drag emulation. Add-ins connected: {count}.",
    "Dodatek podłączony: {name}": "Add-in connected: {name}",
    "Brak dodatku: {name}": "No add-in: {name}",
    "Brak połączenia z SolidCraft. W SolidCrafcie włącz: Preferencje -> "
    "Nawigacja -> Mysz 3D -> \"Nawiguj programem urządzenia na tym komputerze\" "
    "(port {port}).":
        "Not connected to SolidCraft. In SolidCraft turn on: Preferences -> "
        "Navigation -> 3D mouse -> \"Navigate with a device app on this computer\" "
        "(port {port}).",

    # ------------------------------------------------------- panel urządzenia --
    "Podgląd na żywo": "Live preview",
    "Przycisk {index}": "Button {index}",
    "Ruch myszy": "Mouse move",
    "Scroll": "Scroll",
    "ruch myszy": "mouse move",
    "scroll": "scroll",
    "dodatek 3D: kamera": "3D add-in: camera",
    "dodatek 3D: zoom": "3D add-in: zoom",

    # -------------------------------------------------------------- zakładki --
    "Przyciski i gesty": "Buttons and gestures",
    "Nawigacja 3D": "3D navigation",
    "Urządzenie": "Device",
    "Monitor": "Monitor",
    "Ustawienia": "Settings",

    # ------------------------------------------------ zakładka: przyciski --
    "Przyciski boczne": "Side buttons",
    "Gesty ciągłe": "Continuous gestures",
    "Włącz / wyłącz ten przycisk": "Switch this button on / off",
    "Funkcja przycisku włączona / wyłączona": "Button function on / off",
    "Funkcja przycisku włączona": "Button function is on",
    "Funkcja przycisku wyłączona": "Button function is off",

    # ----------------------------------------------- zakładka: nawigacja --
    "Gesty programu (akcje 'Nawigacja 3D')":
        "Application gestures ('3D navigation' actions)",
    "np. Shift": "e.g. Shift",
    "Oś": "Axis",
    "Przeciąganie kursorem": "Cursor drag",
    "Kółko myszy (scroll)": "Mouse wheel (scroll)",
    "Oś Y": "Y axis",
    "Oś X": "X axis",
    "Trzymaj klawisze": "Hold keys",
    "Trzymaj przycisk": "Hold button",
    "Sposób": "Style",
    "Oś sterująca": "Control axis",
    "Osie X/Y": "X/Y axes",
    "Czułość - ruch gałki": "Sensitivity - knob",
    "Czułość - zoom (pierścień)": "Sensitivity - zoom (ring)",
    "Czułość - orbita": "Sensitivity - orbit",
    "Czułość - przesuwanie": "Sensitivity - pan",
    "Skok jednego kliknięcia zoomu: 1.00 = zwykły klik kółka, "
    "mniej = drobniejsze przybliżanie i mniej wierszy przy przewijaniu, "
    "więcej = większy skok. Liczba kliknięć na obrót pierścienia (20) "
    "zostaje bez zmian.":
        "The step of one zoom click: 1.00 = an ordinary wheel click, less = finer "
        "zooming and fewer lines when scrolling, more = a bigger step. The number "
        "of clicks per ring turn (20) stays the same.",
    "Zostaw kursor w nowym miejscu": "Leave the cursor where the gesture ended",
    "Włączone: po ruchu gałką kursor zostaje tam, dokąd dojechał -\n"
    "gałka zachowuje się wtedy jak zwykła mysz.\n"
    "Wyłączone: po geście kursor wraca na pozycję sprzed gestu.":
        "On: after moving the knob the cursor stays where it arrived -\n"
        "the knob then behaves like an ordinary mouse.\n"
        "Off: after the gesture the cursor returns to where it was.",
    "Osie X/Y (ustawienia tego profilu)": "X/Y axes (settings of this profile)",
    "Poniższe dotyczą akcji 'Nawigacja 3D' przypisanych do przycisków bocznych.":
        "The settings below apply to '3D navigation' actions bound to the side buttons.",
    "Odwróć X": "Invert X",
    "Odwróć Y": "Invert Y",
    "Zamień X/Y": "Swap X/Y",
    "Przepinaj gest przy krawędzi": "Re-anchor the gesture at the screen edge",
    "Kursor na środek okna przed gestem":
        "Center the cursor in the window before the gesture",
    "Działa przez dodatek 3D: mnożnik przyrostów osi wysyłanych do programu.":
        "Works through the 3D add-in: multiplier of the axis deltas sent to the application.",
    "Działa przez emulację przeciągania: mnożnik ruchu kursora w trakcie gestu.":
        "Works through drag emulation: multiplier of the cursor movement during the gesture.",

    # ------------------------------------------------ zakładka: urządzenie --
    "Urządzenie {name}": "Device {name}",
    "Typ urządzenia": "Device type",
    "Szukaj ponownie": "Scan again",
    "mysz": "mouse",
    "klawiatura": "keyboard",
    ", {count} przycisków": ", {count} buttons",

    # --------------------------------------------------- zakładka: monitor --
    "Wciśnięte przyciski": "Pressed buttons",
    "Ostatni raport HID / stan osi": "Last HID report / axis state",
    "Strumień zdarzeń": "Event stream",
    "Wyczyść": "Clear",
    "Pokazuj osie i raporty": "Show axes and reports",
    "zmienione bajty: ": "changed bytes: ",
    "raport ": "report ",
    "przycisk boczny {index} DÓŁ": "side button {index} DOWN",
    "przycisk boczny {index} GÓRA": "side button {index} UP",
    "  [zablokowany]": "  [blocked]",
    "ruch myszy  X={dx:+.3f}  Y={dy:+.3f}": "mouse move  X={dx:+.3f}  Y={dy:+.3f}",
    "scroll {value:+.2f}": "scroll {value:+.2f}",
    "klawisz VK 0x{vk:02X} DÓŁ": "key VK 0x{vk:02X} DOWN",
    "klawisz VK 0x{vk:02X} GÓRA": "key VK 0x{vk:02X} UP",
    "profil: {name}": "profile: {name}",
    "Błąd silnika: {message}": "Engine error: {message}",
    "[BŁĄD] {message}": "[ERROR] {message}",

    # ------------------------------------------------- zakładka: ustawienia --
    "Aplikacja": "Application",
    "Język": "Language",
    "Liczba przycisków bocznych": "Number of side buttons",
    "{count} przyciski": "{count} buttons",
    "Wersja urządzenia. Przestawia podgląd na żywo i zakładkę\n"
    "'Przyciski i gesty'. Ustawienia ukrytych przycisków zostają zapisane.":
        "Device variant. Switches the live preview and the 'Buttons and gestures'\n"
        "tab. Settings of the hidden buttons are kept.",
    "Kolor wiodący": "Accent colour",
    "Niebieski": "Blue",
    "Granatowy": "Indigo",
    "Fioletowy": "Violet",
    "Różowy": "Pink",
    "Czerwony": "Red",
    "Pomarańczowy": "Orange",
    "Żółty": "Amber",
    "Zielony": "Green",
    "Turkusowy": "Teal",
    "Grafitowy": "Graphite",
    "Skrót awaryjny (włącz/wyłącz MAKMOUSE)": "Panic hotkey (enable/disable MAKMOUSE)",
    "Autostart": "Start with Windows",
    "Eksportuj...": "Export...",
    "Importuj...": "Import...",
    "Przywróć domyślne": "Restore defaults",
    "Plik konfiguracji": "Configuration file",
    "Ścieżka pliku konfiguracyjnego": "Path of the configuration file",
    "Zmień lokalizację...": "Change location...",
    "Wróć do domyślnej": "Back to default",
    "Otwórz folder": "Open folder",
    "To jest lokalizacja domyślna.": "This is the default location.",
    "Lokalizacja domyślna: {path}": "Default location: {path}",
    "Wybierz plik konfiguracji": "Choose the configuration file",
    "Konfiguracja zapisywana w {path}": "Configuration is now saved in {path}",
    "Wrócono do lokalizacji domyślnej": "Back to the default location",
    "Eksportuj konfigurację": "Export configuration",
    "Wyeksportowano do {path}": "Exported to {path}",
    "Importuj konfigurację": "Import configuration",
    "Zaimportowano z {path}": "Imported from {path}",
    "Przywrócić ustawienia domyślne? Bieżąca konfiguracja zostanie nadpisana.":
        "Restore the default settings? The current configuration will be overwritten.",
    "Przywrócono ustawienia domyślne": "Default settings restored",
    "Zapisano konfigurację": "Configuration saved",

    # ------------------------------------------------------------ zasobnik --
    "Pokaż okno": "Show window",
    "Zakończ": "Quit",
    "Działa w tle. Kliknij ikonę, żeby wrócić.":
        "Running in the background. Click the icon to come back.",

    # ------------------------------------------------------------- widgety --
    "Przycisk działa normalnie - MAKMOUSE go nie przechwytuje.":
        "The button works normally - MAKMOUSE does not intercept it.",
    "Tryb aktywny tak długo, jak przycisk jest wciśnięty.":
        "The mode stays on as long as the button is held.",
    "Wysyłane raz przy naciśnięciu.": "Sent once on press.",
    "Trzymane aż do puszczenia przycisku.": "Held until the button is released.",
    "Ustawia widok w programie z profilu (Fusion 360 albo SolidCraft). "
    "Wymaga podłączonego dodatku.":
        "Sets the view in the profile's application (Fusion 360 or SolidCraft). "
        "Requires a connected add-in.",
    "Przełącznik": "Toggle",
    "Bez przełącznika akcja trwa tylko dopóki przycisk jest wciśnięty.\n"
    "Z przełącznikiem zostaje włączona aż do kolejnego wciśnięcia - tak\n"
    "można np. przestawić gałkę z orbity na przesuwanie i zostawić ją tak.":
        "Without the toggle the action lasts only while the button is held.\n"
        "With the toggle it stays on until the next press - that is how you\n"
        "switch the knob from orbit to pan and leave it there.",
    "Trzymaj": "Hold",
    "bez modyfikatora": "no modifier",
    "kliknij i naciśnij klawisze": "click and press keys",
    "kliknij i naciśnij skrót": "click and press a shortcut",
    "naciśnij  (Esc = wyczyść)": "press  (Esc = clear)",

    # ------------------------------------------------------------- akcje --
    "Orbita": "Orbit",
    "Przesuwanie": "Pan",
    "Zoom": "Zoom",
    "Ruch myszy (X/Y)": "Mouse move (X/Y)",
    "Nic (przepuść dalej)": "Nothing (pass through)",
    "Nawigacja 3D (przytrzymanie)": "3D navigation (hold)",
    "Skrót klawiszowy": "Keyboard shortcut",
    "Przytrzymaj klawisze/przycisk": "Hold keys/button",
    "Widok (dodatek 3D)": "View (3D add-in)",
    "Przód": "Front",
    "Tył": "Back",
    "Lewo": "Left",
    "Prawo": "Right",
    "Góra": "Top",
    "Dół": "Bottom",
    "Izometria": "Isometric",
    "Dopasuj do okna": "Fit to window",
    "Przycisk boczny 1": "Side button 1",
    "Przycisk boczny 2": "Side button 2",
    "Przycisk boczny 3": "Side button 3",
    "Przycisk boczny 4": "Side button 4",
    "Przycisk boczny 5": "Side button 5",
    "Przycisk boczny 6": "Side button 6",
    "{label} (przełącznik)": "{label} (toggle)",
    "(pusty skrót)": "(empty shortcut)",
    "Widok: {name}": "View: {name}",
    "(nic nie trzyma)": "(holds nothing)",
    "Przełącz {what}": "Toggle {what}",
    "Trzymaj {what}": "Hold {what}",

    # ---------------------------------------------------- przyciski myszy --
    "brak": "none",
    "LPM": "LMB",
    "SPM": "MMB",
    "PPM": "RMB",
    "Mysz 4": "Mouse 4",
    "Mysz 5": "Mouse 5",

    # ---------------------------------------------------------- komunikaty --
    "Przycisk boczny {index} -> wyłączono: {action}":
        "Side button {index} -> switched off: {action}",
    "Przycisk boczny {index} -> {action}": "Side button {index} -> {action}",
    "Widok wymaga podłączonego dodatku 3D":
        "The view action requires a connected 3D add-in",
    "Scroll {delta:+.2f} -> {action}": "Scroll {delta:+.2f} -> {action}",
    "akcja: {error}": "action: {error}",
    "wyliczanie urządzeń: {error}": "device enumeration: {error}",
    "most 3D: nie udało się otworzyć portu {port}: {error}":
        "3D bridge: could not open port {port}: {error}",
    "Nie udało się zapamiętać lokalizacji: {error}":
        "Could not remember the location: {error}",
    "Nie znaleziono {path} - użyto ustawień domyślnych. "
    "Sprawdź lokalizację w zakładce Ustawienia.":
        "{path} not found - default settings were used. "
        "Check the location in the Settings tab.",
    "Nie udało się wczytać {path}: {error}": "Could not load {path}: {error}",
    "Nie udało się zapisać {path}: {error}": "Could not save {path}: {error}",
    "MAKMOUSE działa tylko na Windows.": "MAKMOUSE runs on Windows only.",
    "MAKMOUSE już działa (sprawdź zasobnik systemowy).":
        "MAKMOUSE is already running (check the system tray).",

    # ---------------------------------------------------------- pomoc/okno --
    "{app} - instrukcja obsługi": "{app} - user manual",
    "Zamknij": "Close",
}

_TABLES: dict[str, dict[str, str]] = {"en": _EN}


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def available() -> list[tuple[str, str]]:
    """Lista (kod, nazwa) języków do rozwijanej listy w Ustawieniach."""
    return list(LANGUAGES)


def set_language(code: str) -> str:
    """Ustawia język i zwraca faktycznie użyty kod (nieznany = domyślny)."""
    global _language
    _language = code if code in {c for c, _ in LANGUAGES} else DEFAULT_LANGUAGE
    return _language


def language() -> str:
    return _language


def tr(text: str) -> str:
    """Tłumaczy polski tekst źródłowy na bieżący język."""
    table = _TABLES.get(_language)
    if table is None:
        return text
    return table.get(text, text)
