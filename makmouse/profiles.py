"""Konfiguracja programu - profile, przypisania przycisków, zapis i odczyt config.json.

ZA CO ODPOWIADA
    * model danych całej konfiguracji (co jest zapisywane w config.json),
    * profile: do jakich programów pasują, co robią przyciski, gesty i osie,
    * profile fabryczne (Fusion 360, SolidCraft, Inventor, Blender, SolidWorks,
      SketchUp, Rhino),
    * wybór dodatku przy sterowaniu wprost (Fusion 360 albo SolidCraft),
    * zapis / odczyt pliku i miejsce, w którym leży (domyślnie %APPDATA%\\MAKMOUSE),
    * przenoszenie starszych konfiguracji (np. osie globalne z 1.3.1 -> do profili).

NAJWAŻNIEJSZE ELEMENTY
    Config ............... cała konfiguracja; active_profile(exe) wybiera profil
    Profile .............. jeden profil (przyciski, gesty, nav, axes, direct, addon)
    Binding .............. akcja jednego przycisku bocznego (typ, skrót, tryb, ...)
    DeviceConfig ......... tryb odczytu i układ raportu HID
    ACTION_TYPES, NAV_MODES, GESTURES, VIEW_ACTIONS, ADDONS  listy możliwych wartości
    default_profiles() ... profile fabryczne
    load() / save() ...... odczyt i zapis pliku konfiguracji

POWIĄZANIA
    używa: navigator.py (AxisSettings, NavPreset, HoldPreset), engine.py (HidLayout)
    używany przez: run.py, controller.py, ui/main_window.py, ui/widgets.py

SZCZEGÓŁY
Etykiety (`NAV_LABELS`, `ACTION_LABELS`, ...) są trzymane po polsku i tłumaczone
dopiero w miejscu wyświetlenia przez `i18n.tr()`. Dzięki temu plik konfiguracji
nie zależy od wybranego języka - zapisywane są wyłącznie klucze techniczne.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import keys as K
from .bridge import ADDON_FUSION, ADDON_SOLIDCRAFT
from .engine import AxisSpec, HidLayout
from .i18n import DEFAULT_LANGUAGE, tr
from .navigator import AxisSettings, HoldPreset, NavPreset

# Firmware wystawia sześć bitów przycisków; ile z nich ma naprawdę urządzenie,
# mówi `Config.button_count` (do wyboru w Ustawieniach). Sloty ponad tę liczbę
# zostają w konfiguracji nietknięte - po powrocie do 6 przycisków wracają ich
# dotychczasowe przypisania.
BUTTON_SLOTS = 6
BUTTON_COUNT_CHOICES = (3, 6)
DEFAULT_BUTTON_COUNT = 3

# Kolor wiodący aplikacji - dziesięć podstawowych barw do wyboru w Ustawieniach.
DEFAULT_ACCENT = "#0080FF"

NAV_MODES = ["orbit", "pan", "zoom"]
NAV_LABELS = {"orbit": "Orbita", "pan": "Przesuwanie", "zoom": "Zoom"}

# Gesty ciągłe: gałka (ruch X/Y) i pierścień (obrót = scroll).
GESTURES = ["move", "scroll"]
GESTURE_LABELS = {"move": "Ruch myszy (X/Y)", "scroll": "Scroll"}

ACTION_TYPES = ["none", "nav", "hotkey", "hold", "view"]
ACTION_LABELS = {
    "none": "Nic (przepuść dalej)",
    "nav": "Nawigacja 3D (przytrzymanie)",
    "hotkey": "Skrót klawiszowy",
    "hold": "Przytrzymaj klawisze/przycisk",
    "view": "Widok (dodatek 3D)",
}

# Programy, z których dodatkiem profil rozmawia przy sterowaniu wprost (lista
# rozwijana przy "Sterowanie wprost"). Klucze są te same, którymi dodatki
# przedstawiają się mostowi - patrz bridge.py.
ADDONS = [ADDON_FUSION, ADDON_SOLIDCRAFT]
ADDON_LABELS = {ADDON_FUSION: "Fusion 360", ADDON_SOLIDCRAFT: "SolidCraft"}
DEFAULT_ADDON = ADDON_FUSION

# Akcja "view" idzie mostem do dodatku, więc działa wyłącznie w profilu
# obsługiwanym przez dodatek - UI pokazuje ją tylko tam.
DIRECT_ONLY_TYPES = {"view"}

VIEW_ACTIONS = ["front", "back", "left", "right", "top", "bottom", "iso", "fit"]
VIEW_LABELS = {
    "front": "Przód",
    "back": "Tył",
    "left": "Lewo",
    "right": "Prawo",
    "top": "Góra",
    "bottom": "Dół",
    "iso": "Izometria",
    "fit": "Dopasuj do okna",
}

DEFAULT_BUTTON_NAMES = {i: f"Przycisk boczny {i}" for i in range(1, BUTTON_SLOTS + 1)}


def default_hid_layout() -> HidLayout:
    """Układ raportu firmware'u MAKMOUSE (Multi-axis Controller, 5 bajtów).

    [0] Report ID = 1,  [1] X,  [2] Y,  [3] Rz (enkoder),  [4] przyciski.
    Osie i enkoder są 8-bitowe ze znakiem i przyrostowe.
    Bajt przycisków niesie sześć bitów: bit 0 = przycisk 1, ..., bit 5 = przycisk 6.
    """
    return HidLayout(
        report_id=1,
        buttons=[(4, bit) for bit in range(BUTTON_SLOTS)],
        axis_x=AxisSpec(offset=1, size=1, signed=True),
        axis_y=AxisSpec(offset=2, size=1, signed=True),
        wheel=AxisSpec(offset=3, size=1, signed=True),
    )


# Folder aplikacji w APPDATA służy tylko za punkt zaczepienia: leży w nim
# wskaźnik na właściwy plik konfiguracji. Sam config może być gdziekolwiek
# (dysk przenośny, folder projektu, chmura).
APP_DIR = Path(os.environ.get("APPDATA") or str(Path.home())) / "MAKMOUSE"
DEFAULT_CONFIG_PATH = APP_DIR / "config.json"
POINTER_PATH = APP_DIR / "location.json"


def default_config_path() -> Path:
    return DEFAULT_CONFIG_PATH


def config_path() -> Path:
    """Ścieżka, w której naprawdę trzymana jest konfiguracja."""
    try:
        if POINTER_PATH.exists():
            raw = str(json.loads(POINTER_PATH.read_text(encoding="utf-8")).get("config_path", ""))
            if raw.strip():
                return Path(raw.strip())
    except Exception:
        pass  # uszkodzony wskaźnik - wracamy do lokalizacji domyślnej
    return DEFAULT_CONFIG_PATH


def set_config_path(path: Path | None) -> str:
    """Zapamiętuje lokalizację configu. None = powrót do domyślnej.

    Zwraca pusty string przy powodzeniu, inaczej komunikat błędu.
    """
    try:
        if path is None or Path(path) == DEFAULT_CONFIG_PATH:
            POINTER_PATH.unlink(missing_ok=True)
            return ""
        POINTER_PATH.parent.mkdir(parents=True, exist_ok=True)
        POINTER_PATH.write_text(
            json.dumps({"config_path": str(Path(path))}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return ""
    except Exception as exc:
        return tr("Nie udało się zapamiętać lokalizacji: {error}").format(error=exc)


@dataclass
class Binding:
    type: str = "none"
    hotkey: str = ""
    button: str = ""  # przycisk myszy dla typu "hold"
    nav: str = "orbit"
    view: str = "front"  # widok standardowy dla typu "view"
    note: str = ""
    # Przełącznik: pierwsze wciśnięcie włącza akcję, drugie ją wyłącza. Bez tego
    # akcje typu "nav"/"hold" trzeba trzymać przez cały czas gestu.
    toggle: bool = False
    # Wyłącznik całego przycisku (kwadracik w rogu kafla). Ustawienia akcji
    # zostają zapisane - przycisk po prostu przestaje być przechwytywany.
    enabled: bool = True

    def describe(self) -> str:
        # Wyłączony przycisk pokazuje swoją akcję dalej - że jest wyłączony, mówi
        # zielona/czerwona kropka w legendzie podglądu.
        if self.type == "nav":
            label = tr(NAV_LABELS.get(self.nav, self.nav))
            return tr("{label} (przełącznik)").format(label=label) if self.toggle else label
        if self.type == "hotkey":
            return self.hotkey or tr("(pusty skrót)")
        if self.type == "view":
            return tr("Widok: {name}").format(name=tr(VIEW_LABELS.get(self.view, self.view)))
        if self.type == "hold":
            button_label = K.mouse_label(self.button) if self.button else ""
            parts = [p for p in (self.hotkey, button_label) if p]
            if not parts:
                return tr("(nic nie trzyma)")
            what = " + ".join(parts)
            pattern = "Przełącz {what}" if self.toggle else "Trzymaj {what}"
            return tr(pattern).format(what=what)
        return "-"

    def is_active(self) -> bool:
        if not self.enabled:
            return False
        if self.type == "nav":
            return True
        if self.type == "hotkey":
            return bool(self.hotkey.strip())
        if self.type == "view":
            return bool(self.view)
        if self.type == "hold":
            return bool(self.hotkey.strip() or self.button)
        return False

    def is_toggle(self) -> bool:
        """Przełącznik ma sens tylko dla akcji, które coś utrzymują."""
        return self.toggle and self.type in ("nav", "hold")

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "Binding":
        b = cls()
        for k in ("type", "hotkey", "button", "nav", "view", "note"):
            if k in d:
                setattr(b, k, str(d[k]))
        b.toggle = bool(d.get("toggle", False))
        b.enabled = bool(d.get("enabled", True))
        if b.type not in ACTION_TYPES:
            b.type = "none"
        if b.view not in VIEW_ACTIONS:
            b.view = "front"
        return b


@dataclass
class Profile:
    name: str = "Nowy profil"
    match: list[str] = field(default_factory=list)
    is_default: bool = False
    enabled: bool = True
    buttons: dict[int, Binding] = field(default_factory=dict)
    nav: dict[str, NavPreset] = field(default_factory=dict)
    gestures: dict[str, HoldPreset] = field(default_factory=dict)
    # Cała zakładka "Nawigacja 3D" należy do profilu: każdy program ma własną
    # czułość osi, własne odwrócenia i własne zachowanie kursora.
    axes: AxisSettings = field(default_factory=AxisSettings)
    # Osie idą wprost do dodatku działającego w programie 3D, z pominięciem
    # emulacji myszy. Działa tylko wtedy, gdy dodatek jest podłączony do mostu -
    # inaczej profil sam wraca do przeciągania kursorem.
    direct: bool = False
    # Dodatek którego programu dostaje osie przy sterowaniu wprost (ADDONS).
    addon: str = DEFAULT_ADDON

    def __post_init__(self) -> None:
        for i in range(1, BUTTON_SLOTS + 1):
            self.buttons.setdefault(i, Binding())
        self.nav.setdefault("orbit", NavPreset(keys="Shift", button="middle"))
        self.nav.setdefault("pan", NavPreset(keys="", button="middle"))
        self.nav.setdefault("zoom", NavPreset(keys="", button="", style="wheel"))
        for name in GESTURES:
            self.gestures.setdefault(name, HoldPreset())

    def matches(self, exe: str) -> bool:
        if not exe:
            return False
        low = exe.lower()
        return any(low == m.strip().lower() for m in self.match if m.strip())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "match": list(self.match),
            "is_default": self.is_default,
            "enabled": self.enabled,
            "buttons": {str(k): v.to_dict() for k, v in sorted(self.buttons.items())},
            "nav": {k: v.to_dict() for k, v in self.nav.items()},
            "gestures": {k: v.to_dict() for k, v in self.gestures.items()},
            "axes": self.axes.to_dict(),
            "direct": self.direct,
            "addon": self.addon,
        }

    @classmethod
    def from_dict(cls, d: dict, legacy_axes: AxisSettings | None = None) -> "Profile":
        """`legacy_axes` to ustawienia osi z konfiguracji sprzed 1.3.2, kiedy były
        wspólne dla całej aplikacji - profil bez własnej sekcji dziedziczy je."""
        buttons = {int(k): Binding.from_dict(v) for k, v in (d.get("buttons") or {}).items()}
        raw_axes = d.get("axes")
        if raw_axes:
            axes = AxisSettings.from_dict(raw_axes)
        elif legacy_axes is not None:
            axes = AxisSettings.from_dict(legacy_axes.to_dict())
        else:
            axes = AxisSettings()
        # Konfiguracja sprzed 1.4.0 nie zna wyboru dodatku - sterowanie wprost
        # było wtedy wyłącznie dla Fusiona.
        addon = str(d.get("addon", DEFAULT_ADDON))
        return cls(
            name=str(d.get("name", "Profil")),
            match=[str(m) for m in d.get("match", [])],
            is_default=bool(d.get("is_default", False)),
            enabled=bool(d.get("enabled", True)),
            buttons={k: v for k, v in buttons.items() if 1 <= k <= BUTTON_SLOTS},
            nav={k: NavPreset.from_dict(v) for k, v in (d.get("nav") or {}).items()},
            gestures={k: HoldPreset.from_dict(v) for k, v in (d.get("gestures") or {}).items()},
            axes=axes,
            direct=bool(d.get("direct", False)),
            addon=addon if addon in ADDONS else DEFAULT_ADDON,
        )


@dataclass
class DeviceConfig:
    """Urządzenie jest rozpoznawane po nazwie MAKMOUSE - nie ma tu żadnego wyboru,
    zostaje tylko sposób czytania jego raportów."""

    mode: str = "hid"  # "mouse" | "hid" - firmware zgłasza się jako multi-axis
    hid_layout: HidLayout = field(default_factory=default_hid_layout)

    def to_dict(self) -> dict:
        return {"mode": self.mode, "hid_layout": self.hid_layout.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceConfig":
        raw = d.get("hid_layout")
        layout = HidLayout.from_dict(raw) if raw else default_hid_layout()
        _extend_button_bits(layout)
        return cls(mode=str(d.get("mode", "hid")), hid_layout=layout)


def _extend_button_bits(layout: HidLayout) -> None:
    """Konfiguracja sprzed 1.3.2 opisywała tylko trzy bity przycisków.

    Dokładamy kolejne bity tego samego bajtu, żeby wybór sześciu przycisków
    działał bez ręcznego poprawiania pliku konfiguracyjnego.
    """
    if not layout.buttons or len(layout.buttons) >= BUTTON_SLOTS:
        return
    byte_idx, bit_idx = layout.buttons[-1]
    while len(layout.buttons) < BUTTON_SLOTS:
        bit_idx += 1
        if bit_idx > 7:
            byte_idx, bit_idx = byte_idx + 1, 0
        layout.buttons.append((byte_idx, bit_idx))


def _add_solidcraft_profile(cfg: "Config", version: int) -> None:
    """Konfiguracja sprzed 1.4.0 nie ma profilu SolidCrafta - dokładamy go raz.

    Tylko przy pierwszym wczytaniu starszego pliku (wersja < 3) i tylko wtedy,
    gdy żaden profil nie pasuje już do solidcraft.exe: profil usunięty później
    ręcznie nie wraca.
    """
    if version >= 3 or any(p.matches("solidcraft.exe") for p in cfg.profiles):
        return
    cfg.profiles.append(_solidcraft_profile())


# 3 = profile mają wybór dodatku ("addon"), doszedł profil SolidCrafta.
CONFIG_VERSION = 3


@dataclass
class Config:
    enabled: bool = True
    device: DeviceConfig = field(default_factory=DeviceConfig)
    suppress_movement: bool = False  # gałka MAKMOUSE ma ruszać kursorem
    # Ile przycisków bocznych ma urządzenie (3 albo 6). Steruje UI, podglądem
    # na żywo i tym, które bity raportu w ogóle trafiają do akcji.
    button_count: int = DEFAULT_BUTTON_COUNT
    panic_hotkey: str = "Ctrl+Alt+F12"
    start_minimized: bool = False
    theme: str = "dark"  # "dark" | "light"
    accent: str = DEFAULT_ACCENT  # kolor wiodący interfejsu
    language: str = DEFAULT_LANGUAGE  # "pl" | "en"
    # Most do dodatków programów 3D (sterowanie kamerą z pominięciem kursora).
    bridge_enabled: bool = True
    bridge_port: int = 8765
    profiles: list[Profile] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def active_profile(self, exe: str) -> Profile:
        for p in self.profiles:
            if p.enabled and not p.is_default and p.matches(exe):
                return p
        for p in self.profiles:
            if p.is_default:
                return p
        if not self.profiles:
            self.profiles.append(Profile(name="MAKMOUSE", is_default=True))
        return self.profiles[-1]

    def to_dict(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "enabled": self.enabled,
            "device": self.device.to_dict(),
            "suppress_movement": self.suppress_movement,
            "button_count": self.button_count,
            "panic_hotkey": self.panic_hotkey,
            "start_minimized": self.start_minimized,
            "theme": self.theme,
            "accent": self.accent,
            "language": self.language,
            "bridge_enabled": self.bridge_enabled,
            "bridge_port": self.bridge_port,
            "profiles": [p.to_dict() for p in self.profiles],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        # Do 1.3.1 osie były jedną sekcją dla całej aplikacji. Wczytujemy ją jako
        # punkt wyjścia dla profili, które nie mają jeszcze własnej.
        raw_axes = d.get("axes")
        legacy_axes = AxisSettings.from_dict(raw_axes) if raw_axes else None
        count = int(d.get("button_count", DEFAULT_BUTTON_COUNT))
        cfg = cls(
            enabled=bool(d.get("enabled", True)),
            device=DeviceConfig.from_dict(d.get("device", {})),
            suppress_movement=bool(d.get("suppress_movement", False)),
            button_count=count if count in BUTTON_COUNT_CHOICES else DEFAULT_BUTTON_COUNT,
            panic_hotkey=str(d.get("panic_hotkey", "Ctrl+Alt+F12")),
            start_minimized=bool(d.get("start_minimized", False)),
            theme=str(d.get("theme", "dark")),
            accent=str(d.get("accent", DEFAULT_ACCENT)),
            language=str(d.get("language", DEFAULT_LANGUAGE)),
            bridge_enabled=bool(d.get("bridge_enabled", True)),
            bridge_port=int(d.get("bridge_port", 8765)),
            profiles=[Profile.from_dict(p, legacy_axes) for p in d.get("profiles", [])],
        )
        if not cfg.profiles:
            cfg.profiles = default_profiles()
        if not any(p.is_default for p in cfg.profiles):
            cfg.profiles[-1].is_default = True
        _add_solidcraft_profile(cfg, int(d.get("version", 1) or 1))
        return cfg

    def clone(self) -> "Config":
        return copy.deepcopy(self)


# --------------------------------------------------------------------------- #
# Profile domyślne
# --------------------------------------------------------------------------- #
# Akord orbity różni się między pakietami 3D - to jedyne, co naprawdę trzeba
# przestawiać między programami. Przesuwanie ma własny preset, bo np. SolidWorks
# panuje na Ctrl+SPM, a Blender na Shift+SPM.
_ZOOM_WHEEL = NavPreset(button="", style="wheel", wheel_axis="y")


def _cad_profile(name: str, match: list[str], undo: str, extra: str, extra_note: str,
                 orbit: NavPreset, pan: NavPreset, is_default: bool = False,
                 direct: bool = False, addon: str = DEFAULT_ADDON) -> Profile:
    """Układ domyślny: gałka orbituje, przycisk 1 przełącza ją na przesuwanie.

    Gest gałki dostaje akord orbity danego programu. Sam ruch kursora prowadzi
    Navigator; co z kursorem po geście, decyduje `AxisSettings.keep_cursor`.
    """
    return Profile(
        name=name,
        match=match,
        is_default=is_default,
        buttons={
            1: Binding(type="nav", nav="pan", note="Przesuwanie widoku"),
            2: Binding(type="hotkey", hotkey=undo, note="Cofnij"),
            3: Binding(type="hotkey", hotkey=extra, note=extra_note),
        },
        nav={
            "orbit": NavPreset.from_dict(orbit.to_dict()),
            "pan": NavPreset.from_dict(pan.to_dict()),
            "zoom": NavPreset.from_dict(_ZOOM_WHEEL.to_dict()),
        },
        gestures={
            # Sama gałka = orbita w danym programie.
            "move": HoldPreset(keys=orbit.keys, button=orbit.button),
            # Pierścień zostawiamy jako czysty scroll - to natywny zoom.
            "scroll": HoldPreset(),
        },
        direct=direct,
        addon=addon,
    )


def _solidcraft_profile() -> Profile:
    """SolidCraft czyta most sam (Preferencje -> Nawigacja -> mysz 3D), więc
    profil od razu ma sterowanie wprost. Bez połączenia wraca do przeciągania
    akordem Fusiona - to domyślna nawigacja myszą w SolidCrafcie."""
    profile = _cad_profile("SolidCraft", ["solidcraft.exe"],
                           "Ctrl+Z", "", "",
                           orbit=NavPreset(keys="Shift", button="middle"),
                           pan=NavPreset(keys="", button="middle"),
                           direct=True, addon=ADDON_SOLIDCRAFT)
    # Przycisk 3: dopasowanie widoku przez most - SolidCraft obsługuje widoki
    # standardowe tak jak dodatek Fusiona.
    profile.buttons[3] = Binding(type="view", view="fit", note="Dopasuj widok")
    return profile


def default_profiles() -> list[Profile]:
    """Profile dla popularnych pakietów 3D.

    Fusion jest profilem domyślnym: wchodzi też tam, gdzie nie pasuje żaden inny,
    bo akord Shift + SPM jest najczęstszy. Wszystko jest edytowalne w UI.
    """
    shift_mmb = NavPreset(keys="Shift", button="middle")
    mmb = NavPreset(keys="", button="middle")
    return [
        # Fusion ma dodatek sterujący kamerą wprost - gdy jest podłączony,
        # osie omijają emulację myszy i kursor w ogóle się nie rusza.
        _cad_profile("Fusion 360", ["Fusion360.exe", "Fusion.exe"],
                     "Ctrl+Z", "S", "Paleta skrótów",
                     orbit=shift_mmb, pan=mmb, is_default=True, direct=True,
                     addon=ADDON_FUSION),
        # SolidCraft czyta most sam - kamera bez udziału kursora, jak w Fusionie.
        _solidcraft_profile(),
        _cad_profile("Inventor", ["Inventor.exe"],
                     "Ctrl+Z", "F6", "Widok domowy",
                     orbit=shift_mmb, pan=mmb),
        # Blender: SPM = obrót widoku, Shift + SPM = przesuwanie.
        _cad_profile("Blender", ["blender.exe"],
                     "Ctrl+Z", "Home", "Dopasuj widok",
                     orbit=mmb, pan=NavPreset(keys="Shift", button="middle")),
        # SolidWorks: SPM = obrót, Ctrl + SPM = przesuwanie.
        _cad_profile("SolidWorks", ["SLDWORKS.exe"],
                     "Ctrl+Z", "F", "Dopasuj widok",
                     orbit=mmb, pan=NavPreset(keys="Ctrl", button="middle")),
        # SketchUp: SPM = orbita, Shift + SPM = przesuwanie.
        _cad_profile("SketchUp", ["SketchUp.exe"],
                     "Ctrl+Z", "Shift+Z", "Dopasuj widok",
                     orbit=mmb, pan=NavPreset(keys="Shift", button="middle")),
        # Rhino: PPM w widoku perspektywicznym obraca, Shift + PPM przesuwa.
        _cad_profile("Rhino", ["Rhino.exe", "Rhino7.exe", "Rhino8.exe"],
                     "Ctrl+Z", "Ctrl+Shift+E", "Dopasuj widok",
                     orbit=NavPreset(keys="", button="right"),
                     pan=NavPreset(keys="Shift", button="right")),
    ]


def default_config() -> Config:
    return Config(profiles=default_profiles())


# --------------------------------------------------------------------------- #
# Zapis / odczyt
# --------------------------------------------------------------------------- #
def load(path: Path | None = None) -> tuple[Config, str]:
    """Zwraca (konfiguracja, komunikat_błędu)."""
    explicit = path is not None
    path = path or config_path()
    if not path.exists():
        if not explicit and path != DEFAULT_CONFIG_PATH:
            # Wskaźnik pokazuje na plik, którego nie ma - np. odłączony pendrive.
            return default_config(), tr(
                "Nie znaleziono {path} - użyto ustawień domyślnych. "
                "Sprawdź lokalizację w zakładce Ustawienia."
            ).format(path=path)
        return default_config(), ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Config.from_dict(data), ""
    except Exception as exc:
        return default_config(), tr("Nie udało się wczytać {path}: {error}").format(
            path=path, error=exc
        )


def save(cfg: Config, path: Path | None = None) -> str:
    """Zwraca pusty string przy powodzeniu, inaczej komunikat błędu."""
    path = path or config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / (path.name + ".tmp")  # działa też dla nazw bez .json
        tmp.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return ""
    except Exception as exc:
        return tr("Nie udało się zapisać {path}: {error}").format(path=path, error=exc)
