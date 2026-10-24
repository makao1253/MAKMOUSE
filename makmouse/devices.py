"""Wyszukiwanie urządzenia MAKMOUSE wśród wszystkich urządzeń wejściowych.

ZA CO ODPOWIADA
    * lista wszystkich urządzeń widocznych dla Raw Input (myszy, klawiatury, HID),
    * odczyt nazwy producenta/produktu z deskryptora USB (hid.dll),
    * rozpoznanie, które kolekcje należą do MAKMOUSE (napis "MAKMOUSE" w nazwie),
    * lista kolekcji HID (usage page/usage), na które silnik ma się zapisać.

NAJWAŻNIEJSZE ELEMENTY
    TARGET_NAME ............ napis, po którym rozpoznawane jest urządzenie
    DeviceInfo ............. opis jednego urządzenia; is_makmouse mówi, czy to nasze
    enumerate_devices() .... wszystkie urządzenia wejściowe w systemie
    describe() ............. DeviceInfo dla jednego uchwytu Raw Input
    HID_USAGES, MOUSE_USAGES  kolekcje rejestrowane przez silnik

POWIĄZANIA
    używa: winapi.py
    używany przez: controller.py (refresh_devices), engine.py (_is_target),
    ui/main_window.py (tabela w zakładce Urządzenie)

SZCZEGÓŁY
Aplikacja celowo nie ma wyboru urządzenia - reaguje wyłącznie na sprzęt, który
przedstawia się systemowi jako MAKMOUSE (łańcuch produktu lub producenta w
deskryptorze USB). Każdy inny sprzęt jest ignorowany.
"""
from __future__ import annotations

import ctypes
import re
from ctypes import wintypes
from dataclasses import dataclass

from . import winapi as w
from .i18n import tr

TARGET_NAME = "MAKMOUSE"

_VIDPID_RE = re.compile(r"VID_([0-9A-Fa-f]{4}).*?PID_([0-9A-Fa-f]{4})")
_COL_RE = re.compile(r"&Col([0-9A-Fa-f]{2})", re.IGNORECASE)
_MI_RE = re.compile(r"&MI_([0-9A-Fa-f]{2})", re.IGNORECASE)

# Nazwy są po polsku i tłumaczone dopiero przez `kind_name`.
TYPE_NAMES = {w.RIM_TYPEMOUSE: "mysz", w.RIM_TYPEKEYBOARD: "klawiatura", w.RIM_TYPEHID: "HID"}

# Usage page/usage rejestrowane jako źródła wejścia - rozdzielone wg trybu.
#   (1,4)/(1,5) joystick/gamepad,
#   (1,8) multi-axis controller  <- tego używa MAKMOUSE i profesjonalne manipulatory 3D,
#   (0xFF00,1) strona producenta.
# Klawiatury celowo nie ma na liście: MAKMOUSE nie zgłasza takiej kolekcji,
# a bez rejestracji aplikacja nie widzi ani jednego naciśnięcia klawisza.
HID_USAGES = [(0x01, 0x04), (0x01, 0x05), (0x01, 0x08), (0xFF00, 0x01)]

# Kolekcja Mouse - rejestrowana WYŁĄCZNIE w trybie "Mysz". Rejestracja oznacza,
# że każdy ruch każdej myszy w systemie trafia do naszej pętli komunikatów, więc
# w trybie surowego HID (gdzie i tak jest ignorowana) to czysty koszt dołożony
# do ścieżki zwykłej myszy.
MOUSE_USAGES = [(0x01, 0x02)]

# --------------------------------------------------------------------------- #
# Odczyt łańcuchów tekstowych z deskryptora USB (hid.dll)
# --------------------------------------------------------------------------- #
hid = ctypes.WinDLL("hid", use_last_error=True)
hid.HidD_GetProductString.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.ULONG]
hid.HidD_GetProductString.restype = wintypes.BOOLEAN
hid.HidD_GetManufacturerString.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.ULONG]
hid.HidD_GetManufacturerString.restype = wintypes.BOOLEAN

GENERIC_NONE = 0
FILE_SHARE_RW = 0x00000001 | 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE = wintypes.HANDLE(-1).value

w.kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
]
w.kernel32.CreateFileW.restype = wintypes.HANDLE

_strings_cache: dict[str, tuple[str, str]] = {}


def device_strings(path: str) -> tuple[str, str]:
    """(producent, produkt) z deskryptora USB. Puste, gdy nie da się odczytać."""
    if not path:
        return "", ""
    cached = _strings_cache.get(path)
    if cached is not None:
        return cached

    result = ("", "")
    # Dostęp 0 wystarcza do zapytań HidD_* i działa też dla myszy/klawiatur,
    # które system trzyma otwarte na wyłączność.
    handle = w.kernel32.CreateFileW(path, GENERIC_NONE, FILE_SHARE_RW, None, OPEN_EXISTING, 0, None)
    if handle and handle != INVALID_HANDLE:
        try:
            buf = ctypes.create_unicode_buffer(256)
            maker = buf.value if hid.HidD_GetManufacturerString(handle, buf, ctypes.sizeof(buf)) else ""
            buf2 = ctypes.create_unicode_buffer(256)
            product = buf2.value if hid.HidD_GetProductString(handle, buf2, ctypes.sizeof(buf2)) else ""
            result = (maker.strip(), product.strip())
        finally:
            w.kernel32.CloseHandle(handle)

    _strings_cache[path] = result
    return result


def forget_strings() -> None:
    """Czyści cache nazw - wołane po zmianie listy urządzeń."""
    _strings_cache.clear()


# --------------------------------------------------------------------------- #
@dataclass
class DeviceInfo:
    handle: int
    kind: int  # RIM_TYPE*
    path: str
    vid: str = "0000"
    pid: str = "0000"
    usage_page: int = 0
    usage: int = 0
    buttons: int = 0
    collection: str = ""
    manufacturer: str = ""
    product: str = ""

    @property
    def vidpid(self) -> str:
        return f"{self.vid.upper()}:{self.pid.upper()}"

    @property
    def kind_name(self) -> str:
        return tr(TYPE_NAMES.get(self.kind, "?"))

    @property
    def is_makmouse(self) -> bool:
        """True gdy urządzenie przedstawia się jako MAKMOUSE."""
        haystack = f"{self.manufacturer} {self.product} {self.path}".upper()
        return TARGET_NAME in haystack

    def display_name(self) -> str:
        return self.product or self.manufacturer or self.vidpid

    def label(self) -> str:
        extra = ""
        if self.kind == w.RIM_TYPEMOUSE and self.buttons:
            extra = tr(", {count} przycisków").format(count=self.buttons)
        elif self.kind == w.RIM_TYPEHID:
            extra = f", usage {self.usage_page:02X}:{self.usage:02X}"
        col = f" {self.collection}" if self.collection else ""
        return f"{self.display_name()}{col}  [{self.kind_name}{extra}]"

    def is_virtual(self) -> bool:
        return "ROOT#RDP_" in self.path.upper()


def _device_path(handle: int) -> str:
    size = wintypes.UINT(0)
    w.user32.GetRawInputDeviceInfoW(handle, w.RIDI_DEVICENAME, None, ctypes.byref(size))
    if not size.value:
        return ""
    buf = ctypes.create_unicode_buffer(size.value + 1)
    if w.user32.GetRawInputDeviceInfoW(handle, w.RIDI_DEVICENAME, buf, ctypes.byref(size)) == 0xFFFFFFFF:
        return ""
    return buf.value


def _device_info(handle: int) -> w.RID_DEVICE_INFO | None:
    info = w.RID_DEVICE_INFO()
    info.cbSize = ctypes.sizeof(w.RID_DEVICE_INFO)
    size = wintypes.UINT(ctypes.sizeof(w.RID_DEVICE_INFO))
    res = w.user32.GetRawInputDeviceInfoW(handle, w.RIDI_DEVICEINFO, ctypes.byref(info), ctypes.byref(size))
    if res in (0, 0xFFFFFFFF):
        return None
    return info


def describe(handle: int, with_strings: bool = True) -> DeviceInfo | None:
    """Buduje DeviceInfo dla uchwytu Raw Input (albo None gdy urządzenie zniknęło).

    `with_strings=False` pomija odczyt nazw z deskryptora (wymaga otwarcia pliku
    urządzenia) - używane tam, gdzie liczy się czas reakcji.
    """
    path = _device_path(handle)
    if not path:
        return None
    info = _device_info(handle)
    if info is None:
        return None

    dev = DeviceInfo(handle=handle, kind=info.dwType, path=path)

    m = _VIDPID_RE.search(path)
    if m:
        dev.vid, dev.pid = m.group(1).upper(), m.group(2).upper()

    parts = []
    mi = _MI_RE.search(path)
    if mi:
        parts.append(f"MI_{mi.group(1).upper()}")
    col = _COL_RE.search(path)
    if col:
        parts.append(f"Col{col.group(1).upper()}")
    dev.collection = "/".join(parts)

    if info.dwType == w.RIM_TYPEMOUSE:
        dev.buttons = info.mouse.dwNumberOfButtons
        dev.usage_page, dev.usage = 0x01, 0x02
    elif info.dwType == w.RIM_TYPEKEYBOARD:
        dev.usage_page, dev.usage = 0x01, 0x06
    else:
        dev.usage_page = info.hid.usUsagePage
        dev.usage = info.hid.usUsage
        if dev.vid == "0000":
            dev.vid = f"{info.hid.dwVendorId & 0xFFFF:04X}"
            dev.pid = f"{info.hid.dwProductId & 0xFFFF:04X}"

    if with_strings:
        dev.manufacturer, dev.product = device_strings(path)
    return dev


def enumerate_devices(with_strings: bool = True) -> list[DeviceInfo]:
    """Lista wszystkich urządzeń wejściowych widocznych dla Raw Input."""
    count = wintypes.UINT(0)
    stride = ctypes.sizeof(w.RAWINPUTDEVICELIST)
    if w.user32.GetRawInputDeviceList(None, ctypes.byref(count), stride) == 0xFFFFFFFF:
        return []
    if count.value == 0:
        return []
    arr = (w.RAWINPUTDEVICELIST * count.value)()
    got = w.user32.GetRawInputDeviceList(arr, ctypes.byref(count), stride)
    if got == 0xFFFFFFFF:
        return []

    out: list[DeviceInfo] = []
    for i in range(got):
        dev = describe(arr[i].hDevice, with_strings)
        if dev and not dev.is_virtual():
            out.append(dev)
    out.sort(key=lambda d: (d.kind, d.display_name(), d.collection))
    return out


def find_makmouse() -> list[DeviceInfo]:
    """Wszystkie kolekcje HID należące do urządzenia MAKMOUSE."""
    forget_strings()
    return [d for d in enumerate_devices() if d.is_makmouse]
