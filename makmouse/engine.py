"""Silnik wejścia - odbiór i rozkodowanie raportów z urządzenia MAKMOUSE.

ZA CO ODPOWIADA
    * zapis do Windows Raw Input i odbiór surowych raportów HID z urządzenia,
    * rozkodowanie raportu (5 bajtów) na zdarzenia: przycisk boczny, ruch gałki
      (osie X/Y), obrót pierścienia (scroll) oraz surowy raport do Monitora,
    * tylko w trybie "Mysz" (stary firmware): blokowanie oryginalnych zdarzeń
      myszy hookiem WH_MOUSE_LL.
    Silnik nic nie naciska - tylko czyta i przekazuje dalej.

NAJWAŻNIEJSZE ELEMENTY
    InputEngine .............. wątek z własną pętlą komunikatów Windows; każde
                               zdarzenie oddaje callbackiem on_event(InputEvent)
    InputEngine._decode_hid_report  tu raport zamienia się w zdarzenia
    InputEvent ............... zdarzenie: kind = button / axis / wheel / report
    HidLayout, AxisSpec ...... gdzie w raporcie leżą osie, scroll i bity przycisków
    EngineConfig ............. ustawienia silnika wyliczane przez controller.py

POWIĄZANIA
    używa: winapi.py (Win32), devices.py (czy dany uchwyt to MAKMOUSE)
    używany przez: controller.py (tworzy silnik, odbiera zdarzenia)

SZCZEGÓŁY
Raw Input (rozpoznanie urządzenia) + hooki niskopoziomowe (blokowanie
oryginalnych zdarzeń). Działa we własnym wątku z własną pętlą komunikatów
i oknem message-only.

Jak działa odróżnianie urządzeń
---------------------------------
Raw Input mówi KTÓRE urządzenie wysłało zdarzenie, ale nie pozwala go zablokować.
Hook WH_MOUSE_LL pozwala zablokować, ale nie mówi z jakiego urządzenia pochodzi
zdarzenie. Łączymy oba: każde WM_INPUT z naszego urządzenia trafia do krótkiej
kolejki, a hook sprawdza czy pasuje do niej bieżące zdarzenie systemowe.

Surowy HID: pełna separacja od zwykłej myszy
-------------------------------------------
Firmware MAKMOUSE zgłasza się jako Multi-axis Controller (0x01/0x08), czyli
kolekcja, której Windows nie interpretuje: nie rusza kursorem, nie przewija,
nie wpisuje znaków. Wszystkie osie, scroll i przyciski przychodzą jednym
raportem HID, który czytamy sami. Dzięki temu nie trzeba niczego blokować -
a to ważne, bo zmierzone: zwrócenie 1 z hooka niskopoziomowego usuwa zdarzenie
z całego potoku RAZEM z raportem Raw Input, więc blokowanie i rozpoznawanie
urządzenia wzajemnie się wykluczają.

Źródła wejścia są więc zakładane pod tryb (patrz `_sync_sources`), a nie raz na
starcie. W trybie surowego HID nie ma ani hooka WH_MOUSE_LL, ani rejestracji
Raw Input na kolekcję Mouse - inaczej każdy ruch każdej myszy w systemie
przechodziłby przez callback w Pythonie i dopłacalibyśmy do zwykłej myszy
opóźnieniem, mimo że nie mamy z nią nic wspólnego.

Silnik nie rejestruje już żadnej klawiatury ani nie zakłada hooka klawiatury -
nie widzi więc ani jednego naciśnięcia klawisza w systemie.
"""
from __future__ import annotations

import ctypes
import threading
import time
from collections import deque
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Callable

from . import devices as dv
from . import winapi as w

BTN_COUNT_MOUSE = 5  # Windows wystawia w warstwie myszy maksymalnie 5 przycisków
BTN_WINDOW = 0.25  # s - okno korelacji dla przycisków
MOVE_WINDOW = 0.04  # s - okno korelacji dla ruchu
WHEEL_WINDOW = 0.15

_RAW_BTN_MAP = {
    w.RI_MOUSE_LEFT_BUTTON_DOWN: (1, True), w.RI_MOUSE_LEFT_BUTTON_UP: (1, False),
    w.RI_MOUSE_RIGHT_BUTTON_DOWN: (2, True), w.RI_MOUSE_RIGHT_BUTTON_UP: (2, False),
    w.RI_MOUSE_MIDDLE_BUTTON_DOWN: (3, True), w.RI_MOUSE_MIDDLE_BUTTON_UP: (3, False),
    w.RI_MOUSE_BUTTON_4_DOWN: (4, True), w.RI_MOUSE_BUTTON_4_UP: (4, False),
    w.RI_MOUSE_BUTTON_5_DOWN: (5, True), w.RI_MOUSE_BUTTON_5_UP: (5, False),
}

_HOOK_BTN_MAP = {
    w.WM_LBUTTONDOWN: (1, True), w.WM_LBUTTONUP: (1, False),
    w.WM_RBUTTONDOWN: (2, True), w.WM_RBUTTONUP: (2, False),
    w.WM_MBUTTONDOWN: (3, True), w.WM_MBUTTONUP: (3, False),
}


# --------------------------------------------------------------------------- #
# Model danych
# --------------------------------------------------------------------------- #
@dataclass
class AxisSpec:
    offset: int = 0
    size: int = 2  # 1 lub 2 bajty
    signed: bool = True
    full_scale: int = 0  # 0 = automatycznie z rozmiaru


@dataclass
class HidLayout:
    """Opis położenia przycisków, osi i scrolla w surowym raporcie HID."""

    report_id: int = -1  # -1 = nie filtruj po ID raportu
    buttons: list[tuple[int, int]] = field(default_factory=list)  # (bajt, bit)
    axis_x: AxisSpec | None = None
    axis_y: AxisSpec | None = None
    wheel: AxisSpec | None = None  # enkoder / scroll - zawsze przyrostowy

    def to_dict(self) -> dict:
        def ax(a):
            return None if a is None else {"offset": a.offset, "size": a.size,
                                           "signed": a.signed, "full_scale": a.full_scale}

        return {"report_id": self.report_id, "buttons": [list(b) for b in self.buttons],
                "axis_x": ax(self.axis_x), "axis_y": ax(self.axis_y), "wheel": ax(self.wheel)}

    @classmethod
    def from_dict(cls, d: dict) -> "HidLayout":
        def ax(v):
            if not v:
                return None
            return AxisSpec(int(v.get("offset", 0)), int(v.get("size", 2)),
                            bool(v.get("signed", True)), int(v.get("full_scale", 0)))

        return cls(
            report_id=int(d.get("report_id", -1)),
            buttons=[(int(b[0]), int(b[1])) for b in d.get("buttons", []) if len(b) >= 2],
            axis_x=ax(d.get("axis_x")),
            axis_y=ax(d.get("axis_y")),
            wheel=ax(d.get("wheel")),
        )


@dataclass
class EngineConfig:
    enabled: bool = True
    mode: str = "mouse"  # "mouse" | "hid"
    # Ścieżki kolekcji HID należących do MAKMOUSE (małe litery). Wyznaczane poza
    # ścieżką krytyczną, żeby hook nigdy nie musiał otwierać pliku urządzenia.
    target_paths: frozenset[str] = frozenset()
    suppress_buttons: frozenset[int] = frozenset()
    suppress_movement: bool = False
    suppress_wheel: bool = False
    hid_layout: HidLayout = field(default_factory=HidLayout)
    # Czy osie w raporcie HID niosą przyrost (Rel), czy bieżące wychylenie (Abs).
    # Od tego zależy, czy wartość normalizujemy do <-1, 1>, czy oddajemy surową.
    axes_relative: bool = True


@dataclass
class InputEvent:
    kind: str  # "button" | "axis" | "key" | "wheel" | "report"
    index: int = 0
    pressed: bool = False
    dx: float = 0.0
    dy: float = 0.0
    raw: bytes = b""
    device: str = ""
    suppressed: bool = False


# --------------------------------------------------------------------------- #
# Silnik
# --------------------------------------------------------------------------- #
class InputEngine(threading.Thread):
    def __init__(
        self,
        on_event: Callable[[InputEvent], None],
        on_devices_changed: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(name="MakmouseInputEngine", daemon=True)
        self._on_event = on_event
        self._on_devices_changed = on_devices_changed
        self._on_error = on_error or (lambda msg: None)

        self.cfg = EngineConfig()
        self.ready = threading.Event()
        self.last_error = ""

        self._hwnd: int = 0
        self._thread_id: int = 0
        self._mouse_hook = None
        self._wndproc_ref = None
        self._mouse_proc_ref = None
        self._stopping = False
        self._draining = False

        self._registered: set[tuple[int, int]] = set()

        # cache: uchwyt urządzenia -> czy to nasze urządzenie
        self._handle_cache: dict[int, bool] = {}
        self._handle_name: dict[int, str] = {}

        self._pending_btn: deque[tuple[int, bool, float]] = deque(maxlen=64)
        self._pending_move: deque[float] = deque(maxlen=128)
        self._pending_wheel: deque[float] = deque(maxlen=32)
        # Stan przycisków z raportu HID. Celowo NIE czyszczony przy zmianie
        # konfiguracji: gdyby wyzerować go w trakcie trzymania przycisku,
        # zwolnienie uznano by za powtórkę i akcja zawisłaby wciśnięta.
        self._hid_btn_state: dict[tuple[int, int, int], bool] = {}
        self._hid_axis_active = False

        self._raw_buf = ctypes.create_string_buffer(1024)

    # ---------------------------------------------------------------- API ---
    def apply_config(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self._handle_cache.clear()
        self._pending_btn.clear()
        self._pending_move.clear()
        self._pending_wheel.clear()
        # Źródła wejścia zakłada się i zdejmuje w wątku silnika: hook
        # niskopoziomowy woła tylko ten wątek, który go założył.
        if self._thread_id:
            w.user32.PostThreadMessageW(self._thread_id, w.WM_APP_SYNC, 0, 0)

    def stop(self) -> None:
        self._stopping = True
        if self._thread_id:
            w.user32.PostThreadMessageW(self._thread_id, w.WM_QUIT, 0, 0)

    # ------------------------------------------------------------- wątek ---
    def run(self) -> None:
        try:
            self._setup()
        except Exception as exc:  # pragma: no cover - zależne od środowiska
            self.last_error = str(exc)
            self._on_error(str(exc))
            self.ready.set()
            return
        self.ready.set()

        msg = wintypes.MSG()
        while not self._stopping:
            res = w.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res in (0, -1):
                break
            if not msg.hWnd and msg.message == w.WM_APP_SYNC:
                try:
                    self._sync_sources()
                except Exception as exc:  # pragma: no cover - zależne od środowiska
                    self._on_error(str(exc))
                continue
            w.user32.TranslateMessage(ctypes.byref(msg))
            w.user32.DispatchMessageW(ctypes.byref(msg))
        self._teardown()

    def _setup(self) -> None:
        self._thread_id = w.kernel32.GetCurrentThreadId()
        hinst = w.kernel32.GetModuleHandleW(None)

        self._wndproc_ref = w.WNDPROC(self._wndproc)
        cls = w.WNDCLASSW()
        cls.lpfnWndProc = self._wndproc_ref
        cls.hInstance = hinst
        cls.lpszClassName = f"MakmouseRawInput_{self._thread_id}"
        if not w.user32.RegisterClassW(ctypes.byref(cls)):
            raise OSError(f"RegisterClassW: {ctypes.get_last_error()}")

        self._hwnd = w.user32.CreateWindowExW(
            0, cls.lpszClassName, "MAKMOUSE", 0, 0, 0, 0, 0, w.HWND_MESSAGE, None, hinst, None
        )
        if not self._hwnd:
            raise OSError(f"CreateWindowExW: {ctypes.get_last_error()}")

        # Trzymany przez cały czas życia silnika: Windows może wołać procedurę
        # hooka jeszcze chwilę po odpięciu, więc obiekt nie może zniknąć.
        self._mouse_proc_ref = w.HOOKPROC(self._mouse_proc)
        self._sync_sources()

    # ------------------------------------------------------ źródła wejścia ---
    def _sync_sources(self) -> None:
        """Zakłada dokładnie te źródła wejścia, których wymaga bieżący tryb.

        Wołane wyłącznie z wątku silnika. W trybie surowego HID zwykła mysz nie
        przechodzi przez ani jedną linijkę naszego kodu: nie ma ani hooka, ani
        rejestracji Raw Input na kolekcję Mouse.
        """
        if not self._hwnd:
            return
        mouse_mode = self.cfg.mode == "mouse"
        wanted = set(dv.HID_USAGES)
        if mouse_mode:
            wanted |= set(dv.MOUSE_USAGES)
        self._register_usages(wanted)
        self._set_mouse_hook(mouse_mode)

    def _register_usages(self, wanted: set[tuple[int, int]]) -> None:
        add = sorted(wanted - self._registered)
        drop = sorted(self._registered - wanted)
        if not add and not drop:
            return

        # RIDEV_REMOVE wymaga hwndTarget = NULL, inaczej całe wywołanie odpada.
        items = [(page, usage, w.RIDEV_INPUTSINK | w.RIDEV_DEVNOTIFY, self._hwnd)
                 for page, usage in add]
        items += [(page, usage, w.RIDEV_REMOVE, 0) for page, usage in drop]

        rid = (w.RAWINPUTDEVICE * len(items))()
        for i, (page, usage, flags, hwnd) in enumerate(items):
            rid[i].usUsagePage = page
            rid[i].usUsage = usage
            rid[i].dwFlags = flags
            rid[i].hwndTarget = hwnd
        if not w.user32.RegisterRawInputDevices(rid, len(rid), ctypes.sizeof(w.RAWINPUTDEVICE)):
            raise OSError(f"RegisterRawInputDevices: {ctypes.get_last_error()}")
        self._registered = set(wanted)

    def _set_mouse_hook(self, active: bool) -> None:
        """Hook myszy służy tylko trybowi "Mysz" (blokowanie oryginalnych zdarzeń).

        Hooka klawiatury nie zakładamy nigdy - MAKMOUSE nie zgłasza już żadnej
        kolekcji klawiatury.
        """
        if active == bool(self._mouse_hook):
            return
        if not active:
            w.user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
            self._pending_btn.clear()
            self._pending_move.clear()
            self._pending_wheel.clear()
            return
        hinst = w.kernel32.GetModuleHandleW(None)
        hook = w.user32.SetWindowsHookExW(w.WH_MOUSE_LL, self._mouse_proc_ref, hinst, 0)
        if not hook:
            raise OSError(f"SetWindowsHookExW(mouse): {ctypes.get_last_error()}")
        self._mouse_hook = hook

    def _teardown(self) -> None:
        if self._mouse_hook:
            w.user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        if self._hwnd:
            w.user32.DestroyWindow(self._hwnd)
            self._hwnd = 0

    # -------------------------------------------------------- okno / raw ---
    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == w.WM_INPUT:
                self._process_raw(lparam)
                return 0
            if msg == w.WM_INPUT_DEVICE_CHANGE:
                self._handle_cache.clear()
                if self._on_devices_changed:
                    self._on_devices_changed()
                return 0
        except Exception as exc:  # pragma: no cover
            self._on_error(f"wndproc: {exc}")
        return w.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _is_target(self, handle: int) -> bool:
        cached = self._handle_cache.get(handle)
        if cached is not None:
            return cached
        info = dv.describe(handle, with_strings=False)
        ok = bool(info and info.path.lower() in self.cfg.target_paths)
        self._handle_cache[handle] = ok
        if info:
            self._handle_name[handle] = info.vidpid
        return ok

    def _process_raw(self, hrawinput: int) -> None:
        size = wintypes.UINT(0)
        hdr = ctypes.sizeof(w.RAWINPUTHEADER)
        if w.user32.GetRawInputData(hrawinput, w.RID_INPUT, None, ctypes.byref(size), hdr) == 0xFFFFFFFF:
            return
        if size.value > len(self._raw_buf):
            self._raw_buf = ctypes.create_string_buffer(size.value + 64)
        got = w.user32.GetRawInputData(
            hrawinput, w.RID_INPUT, self._raw_buf, ctypes.byref(size), hdr
        )
        if got == 0xFFFFFFFF or got == 0:
            return

        ri = ctypes.cast(self._raw_buf, ctypes.POINTER(w.RAWINPUT)).contents
        handle = ri.header.hDevice
        if not self._is_target(handle):
            return
        dev_id = self._handle_name.get(handle, "")

        if ri.header.dwType == w.RIM_TYPEMOUSE and self.cfg.mode == "mouse":
            self._handle_raw_mouse(ri.mouse, dev_id)
        elif ri.header.dwType == w.RIM_TYPEHID and self.cfg.mode == "hid":
            self._handle_raw_hid(ri, dev_id)

    def _handle_raw_mouse(self, rm: w.RAWMOUSE, dev_id: str) -> None:
        now = time.perf_counter()
        flags = rm.usButtonFlags

        for bit, (index, down) in _RAW_BTN_MAP.items():
            if flags & bit:
                if index in self.cfg.suppress_buttons:
                    self._pending_btn.append((index, down, now))
                self._emit(InputEvent("button", index=index, pressed=down, device=dev_id,
                                      suppressed=index in self.cfg.suppress_buttons))

        if flags & (w.RI_MOUSE_WHEEL | w.RI_MOUSE_HWHEEL):
            data = ctypes.c_short(rm.usButtonData).value
            horizontal = bool(flags & w.RI_MOUSE_HWHEEL)
            block = self.cfg.suppress_wheel and not horizontal
            if block:
                self._pending_wheel.append(now)
            self._emit(InputEvent("wheel", index=1 if horizontal else 0,
                                  dx=data / 120.0, device=dev_id, suppressed=block))

        if (rm.lLastX or rm.lLastY) and not (rm.usFlags & w.MOUSE_MOVE_ABSOLUTE):
            if self.cfg.suppress_movement:
                self._pending_move.append(now)
            self._emit(InputEvent("axis", dx=float(rm.lLastX), dy=float(rm.lLastY),
                                  device=dev_id, suppressed=self.cfg.suppress_movement))

    def _handle_raw_hid(self, ri: w.RAWINPUT, dev_id: str) -> None:
        size_hid = ri.hid.dwSizeHid
        count = ri.hid.dwCount
        if size_hid == 0 or count == 0:
            return
        base = ctypes.addressof(ri) + w.RAWHID_DATA_OFFSET
        total = size_hid * count
        blob = ctypes.string_at(base, total)
        for i in range(count):
            self._decode_hid_report(blob[i * size_hid:(i + 1) * size_hid], dev_id)

    def _decode_hid_report(self, report: bytes, dev_id: str) -> None:
        layout = self.cfg.hid_layout
        if layout.report_id >= 0 and (not report or report[0] != layout.report_id):
            self._emit(InputEvent("report", raw=report, device=dev_id))
            return

        self._emit(InputEvent("report", raw=report, device=dev_id))

        for i, (byte_idx, bit_idx) in enumerate(layout.buttons, start=1):
            if byte_idx >= len(report):
                continue
            pressed = bool(report[byte_idx] & (1 << bit_idx))
            key = (i, byte_idx, bit_idx)
            prev = self._hid_btn_state.get(key, False)
            if pressed != prev:
                self._hid_btn_state[key] = pressed
                self._emit(InputEvent("button", index=i, pressed=pressed, device=dev_id))

        ticks = _read_int(report, layout.wheel)
        if ticks:
            self._emit(InputEvent("wheel", index=0, dx=float(ticks), device=dev_id))

        rel = self.cfg.axes_relative
        dx = _read_axis(report, layout.axis_x, rel)
        dy = _read_axis(report, layout.axis_y, rel)
        if dx or dy or self._hid_axis_active:
            self._hid_axis_active = bool(dx or dy)
            self._emit(InputEvent("axis", dx=dx, dy=dy, device=dev_id))

    def _emit(self, ev: InputEvent) -> None:
        try:
            self._on_event(ev)
        except Exception as exc:  # pragma: no cover
            self._on_error(f"handler: {exc}")

    # ------------------------------------------------------------- hooki ---
    def _drain_raw_input(self) -> None:
        """Przetwarza zaległe WM_INPUT, żeby hook widział aktualny stan kolejki."""
        if self._draining or not self._hwnd:
            return
        self._draining = True
        try:
            msg = wintypes.MSG()
            guard = 0
            while guard < 64 and w.user32.PeekMessageW(
                ctypes.byref(msg), self._hwnd, w.WM_INPUT, w.WM_INPUT, w.PM_REMOVE
            ):
                guard += 1
                self._process_raw(msg.lParam)
        except Exception as exc:  # pragma: no cover
            self._on_error(f"drain: {exc}")
        finally:
            self._draining = False

    @staticmethod
    def _prune(dq: deque, now: float, window: float, indexed: bool) -> None:
        while dq:
            t = dq[0][2] if indexed else dq[0]
            if now - t > window:
                dq.popleft()
            else:
                break

    def _mouse_proc(self, ncode, wparam, lparam):
        try:
            if ncode == w.HC_ACTION and self.cfg.enabled and self.cfg.mode == "mouse":
                ms = ctypes.cast(lparam, ctypes.POINTER(w.MSLLHOOKSTRUCT)).contents
                if ms.dwExtraInfo != w.MAKMOUSE_SIGNATURE and not (ms.flags & w.LLMHF_INJECTED):
                    if self._should_block_mouse(int(wparam), ms):
                        return 1
        except Exception as exc:  # pragma: no cover
            self._on_error(f"mouse hook: {exc}")
        return w.user32.CallNextHookEx(None, ncode, wparam, lparam)

    def _should_block_mouse(self, msg: int, ms: w.MSLLHOOKSTRUCT) -> bool:
        if not (self.cfg.suppress_buttons or self.cfg.suppress_movement or self.cfg.suppress_wheel):
            return False
        self._drain_raw_input()
        now = time.perf_counter()

        if msg == w.WM_MOUSEMOVE:
            if not self.cfg.suppress_movement:
                return False
            self._prune(self._pending_move, now, MOVE_WINDOW, indexed=False)
            if self._pending_move:
                self._pending_move.popleft()
                return True
            return False

        if msg == w.WM_MOUSEWHEEL:
            if not self.cfg.suppress_wheel:
                return False
            self._prune(self._pending_wheel, now, WHEEL_WINDOW, indexed=False)
            if self._pending_wheel:
                self._pending_wheel.popleft()
                return True
            return False

        hit = _HOOK_BTN_MAP.get(msg)
        if hit is None:
            if msg in (w.WM_XBUTTONDOWN, w.WM_XBUTTONUP):
                xb = (ms.mouseData >> 16) & 0xFFFF
                index = 4 if xb == w.XBUTTON1 else 5
                hit = (index, msg == w.WM_XBUTTONDOWN)
            else:
                return False

        index, down = hit
        if index not in self.cfg.suppress_buttons:
            return False
        self._prune(self._pending_btn, now, BTN_WINDOW, indexed=True)
        for i, (p_index, p_down, _t) in enumerate(self._pending_btn):
            if p_index == index and p_down == down:
                del self._pending_btn[i]
                return True
        return False


def _read_int(report: bytes, spec: AxisSpec | None) -> int:
    """Surowa liczba spod wskazanego offsetu (0, gdy pole nie istnieje)."""
    if spec is None:
        return 0
    end = spec.offset + spec.size
    if spec.offset < 0 or end > len(report):
        return 0
    return int.from_bytes(report[spec.offset:end], "little", signed=spec.signed)


def _read_axis(report: bytes, spec: AxisSpec | None, relative: bool) -> float:
    """Odczyt osi z surowego raportu.

    Oś przyrostową (Rel) oddajemy surową - to gotowy przyrost w jednostkach
    urządzenia. Oś bezwzględną (Abs) normalizujemy do okolic <-1, 1>, bo dalsza
    warstwa traktuje ją jako wychylenie, czyli prędkość.
    """
    if spec is None:
        return 0.0
    raw = _read_int(report, spec)
    if relative:
        return float(raw)
    scale = spec.full_scale or ((1 << (8 * spec.size - 1)) - 1 if spec.signed else (1 << (8 * spec.size)) - 1)
    if scale <= 0:
        return 0.0
    return max(-1.5, min(1.5, raw / scale))
