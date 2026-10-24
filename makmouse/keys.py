"""Słownik klawiszy i przycisków myszy - tekst skrótu <-> kody Windows.

ZA CO ODPOWIADA
    * zamiana nazw klawiszy ("Ctrl", "F5", "Num+") na kody wirtualne VK i z powrotem,
    * rozbiór zapisu skrótu "Ctrl+Shift+E" na listę modyfikatorów i klawisz główny,
    * lista przycisków myszy dostępnych w akcjach (LPM, SPM, PPM, Mysz 4/5)
      i ich wyświetlane nazwy.

NAJWAŻNIEJSZE ELEMENTY
    VK, MODIFIERS, ALIASES ... tabele nazw -> kody
    parse_hotkey() ........... "Ctrl+Shift+E" -> ([VK_CTRL, VK_SHIFT], VK_E)
    format_hotkey() .......... odwrotność parse_hotkey()
    MOUSE_BUTTONS, mouse_label() ... przyciski myszy i ich przetłumaczone nazwy

POWIĄZANIA
    używany przez: output.py (wysyłanie skrótów), controller.py (skrót awaryjny),
    ui/widgets.py i ui/main_window.py (listy przycisków myszy w UI)
"""
from __future__ import annotations

from .i18n import tr

VK: dict[str, int] = {
    "BACKSPACE": 0x08, "TAB": 0x09, "CLEAR": 0x0C, "ENTER": 0x0D, "PAUSE": 0x13,
    "CAPSLOCK": 0x14, "ESC": 0x1B, "SPACE": 0x20, "PGUP": 0x21, "PGDN": 0x22,
    "END": 0x23, "HOME": 0x24, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "PRINTSCREEN": 0x2C, "INSERT": 0x2D, "DELETE": 0x2E, "APPS": 0x5D,
    "NUM0": 0x60, "NUM1": 0x61, "NUM2": 0x62, "NUM3": 0x63, "NUM4": 0x64,
    "NUM5": 0x65, "NUM6": 0x66, "NUM7": 0x67, "NUM8": 0x68, "NUM9": 0x69,
    "NUM*": 0x6A, "NUM+": 0x6B, "NUM-": 0x6D, "NUM.": 0x6E, "NUM/": 0x6F,
    "NUMLOCK": 0x90, "SCROLLLOCK": 0x91,
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF, "`": 0xC0,
    "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
for _i in range(1, 25):
    VK[f"F{_i}"] = 0x6F + _i
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    VK[_c] = ord(_c)

# Aliasy przyjazne użytkownikowi
ALIASES = {
    "ESCAPE": "ESC", "RETURN": "ENTER", "SPACEBAR": "SPACE", "DEL": "DELETE",
    "INS": "INSERT", "PAGEUP": "PGUP", "PAGEDOWN": "PGDN", "BKSP": "BACKSPACE",
    "PRTSC": "PRINTSCREEN", "PLUS": "=", "MINUS": "-",
}

MODIFIERS = {"CTRL": 0x11, "SHIFT": 0x10, "ALT": 0x12, "WIN": 0x5B}
MOD_ORDER = ["CTRL", "SHIFT", "ALT", "WIN"]
MOD_VK_TO_NAME = {
    0x11: "CTRL", 0xA2: "CTRL", 0xA3: "CTRL",
    0x10: "SHIFT", 0xA0: "SHIFT", 0xA1: "SHIFT",
    0x12: "ALT", 0xA4: "ALT", 0xA5: "ALT",
    0x5B: "WIN", 0x5C: "WIN",
}

VK_TO_NAME = {v: k for k, v in VK.items()}
VK_TO_NAME.update({v: k.capitalize() for k, v in MODIFIERS.items()})

# Przyciski myszy dostępne jako cel akcji. Etykiety są po polsku - tłumaczy je
# `mouse_label()` w momencie wyświetlenia.
MOUSE_BUTTONS = ["left", "middle", "right", "x1", "x2"]
MOUSE_LABELS = {
    "": "brak", "left": "LPM", "middle": "SPM", "right": "PPM", "x1": "Mysz 4", "x2": "Mysz 5",
}


def mouse_label(button: str) -> str:
    """Przetłumaczona nazwa przycisku myszy ("" = brak)."""
    return tr(MOUSE_LABELS.get(button, ""))


def normalize_name(name: str) -> str:
    n = name.strip().upper()
    return ALIASES.get(n, n)


def parse_hotkey(text: str) -> tuple[list[int], int | None]:
    """"Ctrl+Shift+E" -> ([VK_CTRL, VK_SHIFT], VK_E). Zwraca ([], None) dla pustego."""
    if not text or not text.strip():
        return [], None
    mods: list[int] = []
    main: int | None = None
    for part in text.split("+"):
        name = normalize_name(part)
        if not name:
            continue
        if name in MODIFIERS:
            vk = MODIFIERS[name]
            if vk not in mods:
                mods.append(vk)
        elif name in VK:
            main = VK[name]
    return mods, main


def format_hotkey(mods: list[int], main: int | None) -> str:
    names = [MOD_VK_TO_NAME.get(m, "").capitalize() for m in mods]
    names = [n for n in dict.fromkeys(names) if n]
    order = {m.capitalize(): i for i, m in enumerate(MOD_ORDER)}
    names.sort(key=lambda n: order.get(n, 99))
    if main is not None:
        names.append(VK_TO_NAME.get(main, f"VK{main:02X}"))
    return "+".join(names)


def hotkey_is_valid(text: str) -> bool:
    mods, main = parse_hotkey(text)
    return main is not None or bool(mods)
