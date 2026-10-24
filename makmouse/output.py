"""Wyjście programu - udawanie klawiatury i myszy (SendInput).

ZA CO ODPOWIADA
    * naciskanie i puszczanie klawiszy oraz całych skrótów ("Ctrl+Z"),
    * wciskanie przycisków myszy (LPM/SPM/PPM/4/5),
    * ruch kursora (względny i bezwzględny) oraz scroll z dowolną wielkością kroku.
    To jest JEDYNE miejsce, w którym MAKMOUSE coś "naciska" w systemie.

NAJWAŻNIEJSZE ELEMENTY
    tap_hotkey() ........ naciśnij i puść skrót (akcja "Skrót klawiszowy")
    hold_hotkey() ....... trzymaj / puść skrót (akcje przytrzymania, gesty)
    mouse_button() ...... wciśnij / puść przycisk myszy
    wheel() ............. scroll; ułamek kliknięcia = mniejszy skok (czułość zoomu)
    move_absolute() ..... ruch kursora do punktu (używa go Navigator)

POWIĄZANIA
    używa: winapi.py, keys.py
    używany przez: controller.py, navigator.py

SZCZEGÓŁY
Każde zdarzenie jest oznaczane sygnaturą MAKMOUSE_SIGNATURE w dwExtraInfo, żeby
własne hooki mogły je bezbłędnie odróżnić od wejścia sprzętowego.
"""
from __future__ import annotations

import ctypes
import threading

from . import keys as K
from . import winapi as w

_lock = threading.Lock()

_MOUSE_FLAGS = {
    "left": (w.MOUSEEVENTF_LEFTDOWN, w.MOUSEEVENTF_LEFTUP, 0),
    "right": (w.MOUSEEVENTF_RIGHTDOWN, w.MOUSEEVENTF_RIGHTUP, 0),
    "middle": (w.MOUSEEVENTF_MIDDLEDOWN, w.MOUSEEVENTF_MIDDLEUP, 0),
    "x1": (w.MOUSEEVENTF_XDOWN, w.MOUSEEVENTF_XUP, w.XBUTTON1),
    "x2": (w.MOUSEEVENTF_XDOWN, w.MOUSEEVENTF_XUP, w.XBUTTON2),
}


def _send(items: list[w.INPUT]) -> int:
    if not items:
        return 0
    arr = (w.INPUT * len(items))(*items)
    with _lock:
        return w.user32.SendInput(len(items), arr, ctypes.sizeof(w.INPUT))


def _kbd_input(vk: int, up: bool) -> w.INPUT:
    """Buduje zdarzenie klawiatury wysyłane scancode'em (najlepsza zgodność z CAD/3D)."""
    sc_ex = w.user32.MapVirtualKeyW(vk, w.MAPVK_VK_TO_VSC_EX)
    flags = w.KEYEVENTF_SCANCODE
    scan = sc_ex & 0xFF
    if (sc_ex >> 8) == 0xE0:
        flags |= w.KEYEVENTF_EXTENDEDKEY
    if up:
        flags |= w.KEYEVENTF_KEYUP
    if scan == 0:  # brak mapowania scancode - fallback na kod wirtualny
        flags = w.KEYEVENTF_KEYUP if up else 0
        scan = 0
    inp = w.INPUT(type=w.INPUT_KEYBOARD)
    inp.ki = w.KEYBDINPUT(
        wVk=0 if (flags & w.KEYEVENTF_SCANCODE) else vk,
        wScan=scan,
        dwFlags=flags,
        time=0,
        dwExtraInfo=w.MAKMOUSE_SIGNATURE,
    )
    return inp


def _mouse_input(flags: int, data: int = 0, dx: int = 0, dy: int = 0) -> w.INPUT:
    inp = w.INPUT(type=w.INPUT_MOUSE)
    inp.mi = w.MOUSEINPUT(
        dx=dx, dy=dy, mouseData=data & 0xFFFFFFFF, dwFlags=flags, time=0,
        dwExtraInfo=w.MAKMOUSE_SIGNATURE,
    )
    return inp


# --------------------------------------------------------------------------- #
# Klawiatura
# --------------------------------------------------------------------------- #
def key_down(vk: int) -> None:
    _send([_kbd_input(vk, False)])


def key_up(vk: int) -> None:
    _send([_kbd_input(vk, True)])


def keys_down(vks: list[int]) -> None:
    _send([_kbd_input(vk, False) for vk in vks])


def keys_up(vks: list[int]) -> None:
    _send([_kbd_input(vk, True) for vk in reversed(vks)])


def tap_hotkey(text: str) -> None:
    """Naciśnij i puść cały skrót, np. "Ctrl+Shift+E"."""
    mods, main = K.parse_hotkey(text)
    if main is None and not mods:
        return
    seq: list[w.INPUT] = [_kbd_input(m, False) for m in mods]
    if main is not None:
        seq.append(_kbd_input(main, False))
        seq.append(_kbd_input(main, True))
    seq += [_kbd_input(m, True) for m in reversed(mods)]
    _send(seq)


def hold_hotkey(text: str, down: bool) -> None:
    """Wciśnij (down=True) lub zwolnij cały skrót - do akcji typu 'przytrzymaj'."""
    mods, main = K.parse_hotkey(text)
    vks = mods + ([main] if main is not None else [])
    if not vks:
        return
    if down:
        _send([_kbd_input(vk, False) for vk in vks])
    else:
        _send([_kbd_input(vk, True) for vk in reversed(vks)])


# --------------------------------------------------------------------------- #
# Mysz
# --------------------------------------------------------------------------- #
def mouse_button(button: str, down: bool) -> None:
    spec = _MOUSE_FLAGS.get(button)
    if not spec:
        return
    down_flag, up_flag, data = spec
    _send([_mouse_input(down_flag if down else up_flag, data)])


def mouse_click(button: str) -> None:
    spec = _MOUSE_FLAGS.get(button)
    if not spec:
        return
    down_flag, up_flag, data = spec
    _send([_mouse_input(down_flag, data), _mouse_input(up_flag, data)])


def wheel(clicks: float, horizontal: bool = False) -> None:
    delta = int(round(clicks * 120))
    if delta == 0:
        return
    flag = w.MOUSEEVENTF_HWHEEL if horizontal else w.MOUSEEVENTF_WHEEL
    _send([_mouse_input(flag, delta)])  # _mouse_input maskuje do DWORD


def move_relative(dx: int, dy: int) -> None:
    if dx == 0 and dy == 0:
        return
    _send([_mouse_input(w.MOUSEEVENTF_MOVE | w.MOUSEEVENTF_MOVE_NOCOALESCE, 0, dx, dy)])


def move_absolute(x: int, y: int) -> None:
    """Ruch bezwzględny - omija przyspieszenie kursora, więc jest przewidywalny."""
    left, top, width, height = w.virtual_screen_rect()
    nx = int(round((x - left) * 65535 / max(1, width - 1)))
    ny = int(round((y - top) * 65535 / max(1, height - 1)))
    nx = max(0, min(65535, nx))
    ny = max(0, min(65535, ny))
    flags = (
        w.MOUSEEVENTF_MOVE
        | w.MOUSEEVENTF_ABSOLUTE
        | w.MOUSEEVENTF_VIRTUALDESK
        | w.MOUSEEVENTF_MOVE_NOCOALESCE
    )
    _send([_mouse_input(flags, 0, nx, ny)])


def release_all(hotkey_text: str = "", button: str = "") -> None:
    """Awaryjne zwolnienie tego, co mogłoby zostać wciśnięte."""
    if hotkey_text:
        hold_hotkey(hotkey_text, False)
    if button:
        mouse_button(button, False)
