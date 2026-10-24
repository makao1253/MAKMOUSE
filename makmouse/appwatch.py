"""Wykrywanie aktywnego programu - podstawa automatycznego przełączania profili.

ZA CO ODPOWIADA
    * ustalenie, który program ma okno na pierwszym planie (nazwa pliku .exe
      i pełna ścieżka),
    * zgłaszanie zmiany aktywnego programu - co 0,35 s, w osobnym wątku.

NAJWAŻNIEJSZE ELEMENTY
    foreground_process() ... (nazwa_exe, ścieżka) okna na pierwszym planie
    AppWatcher ............. wątek odpytujący; woła on_change(exe, ścieżka)
                             tylko wtedy, gdy aktywny program się zmienił

POWIĄZANIA
    używa: winapi.py (GetForegroundWindow, QueryFullProcessImageNameW)
    używany przez: controller.py (Controller._on_app_changed wybiera profil)
"""
from __future__ import annotations

import ctypes
import ntpath
import threading
from ctypes import wintypes
from typing import Callable

from . import winapi as w


def foreground_process() -> tuple[str, str]:
    """Zwraca (nazwa_exe, pełna_ścieżka) okna na pierwszym planie."""
    hwnd = w.user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return "", ""
    handle = w.kernel32.OpenProcess(w.PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return "", ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not w.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return "", ""
        path = buf.value
        return ntpath.basename(path), path
    finally:
        w.kernel32.CloseHandle(handle)


class AppWatcher(threading.Thread):
    """Odpytuje aktywny proces i zgłasza zmiany."""

    def __init__(self, on_change: Callable[[str, str], None], interval: float = 0.35) -> None:
        super().__init__(name="MakmouseAppWatcher", daemon=True)
        self._on_change = on_change
        self._interval = interval
        self._stop = threading.Event()
        self.current = ("", "")

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                info = foreground_process()
            except Exception:  # pragma: no cover
                continue
            if info != self.current:
                self.current = info
                try:
                    self._on_change(*info)
                except Exception:  # pragma: no cover
                    pass
