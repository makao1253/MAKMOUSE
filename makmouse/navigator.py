"""Navigator - zamiana ruchu gałki na gest myszy w programie CAD (emulacja przeciągania).

ZA CO ODPOWIADA
    * syntezowanie gestu CAD: wciśnij modyfikatory i przycisk myszy, prowadź
      kursor za ruchem gałki, na końcu wszystko puść,
    * zachowanie kursora: centrowanie przed gestem, przepinanie przy krawędzi
      ekranu, zostawienie albo przywrócenie pozycji po geście,
    * tryb "kółko myszy": zamiana ruchu gałki na kliknięcia scrolla,
    * przechowywanie ustawień osi profilu (czułości, odwrócenia, opcje kursora).
    Używany wtedy, gdy NIE działa sterowanie wprost przez dodatek 3D.

NAJWAŻNIEJSZE ELEMENTY
    Navigator ........ jeden aktywny gest naraz; start() / feed() / stop();
                       osobny wątek odświeża kursor 120 razy na sekundę (_tick)
    AxisSettings ..... ustawienia osi profilu - zakładka "Nawigacja 3D -> Osie X/Y"
                       (sens_move, sens_orbit, sens_pan, sens_zoom, keep_cursor, ...)
    NavPreset ........ co trzymać dla trybu orbita / przesuwanie / zoom
                       (tabela "Gesty programu")
    HoldPreset ....... co trzymać w trakcie gestu ciągłego (ruch myszy / scroll)

POWIĄZANIA
    używa: output.py (ruch kursora, przyciski, scroll), winapi.py
    używany przez: controller.py (Controller, AxisGesture), profiles.py (dane)

SZCZEGÓŁY
Orbita w Fusion 360 to "Shift + środkowy przycisk + ruch myszy". Navigator trzyma
wciśnięte modyfikatory i przycisk, a następnie generuje ruch kursora pozycją
bezwzględną (omija przyspieszenie wskaźnika, więc reakcja jest liniowa).

Gdy wirtualny kursor dojdzie do krawędzi ekranu, gest jest "przepinany":
przycisk puszczony -> kursor na środek -> przycisk wciśnięty. Dzięki temu
przy trybie proporcjonalnym (wychylenie = prędkość) można obracać bez końca.
"""
from __future__ import annotations

import ctypes
import math
import threading
import time
from dataclasses import dataclass

from . import output as out
from . import winapi as w
from .i18n import tr

EDGE_MARGIN = 90  # px - odległość od krawędzi wymuszająca przepięcie gestu
TICK_HZ = 120.0


@dataclass
class NavPreset:
    """Co trzeba trzymać, żeby dany program wszedł w dany tryb nawigacji."""

    keys: str = ""  # np. "Shift"
    button: str = "middle"  # "" | left | middle | right | x1 | x2
    style: str = "drag"  # "drag" | "wheel"
    wheel_axis: str = "y"  # która oś steruje scrollem w trybie "wheel"

    def to_dict(self) -> dict:
        return {"keys": self.keys, "button": self.button, "style": self.style,
                "wheel_axis": self.wheel_axis}

    @classmethod
    def from_dict(cls, d: dict) -> "NavPreset":
        return cls(
            keys=str(d.get("keys", "")),
            button=str(d.get("button", "middle")),
            style=str(d.get("style", "drag")),
            wheel_axis=str(d.get("wheel_axis", "y")),
        )


@dataclass
class HoldPreset:
    """Co trzymać w trakcie gestu osi (ruch gałką / obrót pierścienia).

    Przykład: ruch gałką + trzymany Shift i środkowy przycisk = orbita w Fusion,
    obrót pierścienia + trzymany Ctrl = zoom krokowy w wielu programach.
    """

    keys: str = ""
    button: str = ""

    def active(self) -> bool:
        return bool(self.keys.strip() or self.button)

    def describe(self) -> str:
        parts = [p for p in (self.keys.strip(), tr(_MOUSE_LABELS.get(self.button, ""))) if p]
        return " + ".join(parts) if parts else tr("bez modyfikatora")

    def to_dict(self) -> dict:
        return {"keys": self.keys, "button": self.button}

    @classmethod
    def from_dict(cls, d: dict) -> "HoldPreset":
        return cls(keys=str((d or {}).get("keys", "")), button=str((d or {}).get("button", "")))


_MOUSE_LABELS = {"left": "LPM", "middle": "SPM", "right": "PPM", "x1": "Mysz 4", "x2": "Mysz 5"}


@dataclass
class AxisSettings:
    # Firmware zgłasza osie jako przyrostowe (deskryptor Rel), więc każdy raport
    # niesie zmianę, a nie wychylenie. Wariant "wychylenie = prędkość" (jak
    # w profesjonalnych manipulatorach 3D) został usunięty - przy tym deskryptorze nie miał
    # jak zadziałać i tylko mnożył martwe suwaki.
    sens_move: float = 1.0  # zwykły ruch gałki (bez trybu nawigacji)
    sens_orbit: float = 1.0
    sens_pan: float = 1.0
    # Zoom to skok, a nie liczba kliknięć: wartość skaluje *wielkość* jednego
    # kliknięcia. 1.00 = zwykły klik kółka na impuls pierścienia, 0.30 = skok
    # trzykrotnie mniejszy (mniej wierszy na stronie, bliższe podejście do bryły),
    # 2.00 = dwa razy większy. Liczba zdarzeń zostaje ta sama, zmienia się ich waga.
    sens_zoom: float = 1.0
    invert_x: bool = False
    invert_y: bool = False
    swap_xy: bool = False
    # Odwrócony kierunek obrotu pierścienia: przybliżanie zamienia się
    # z oddalaniem - i w zwykłym scrollu, i w zoomie przez dodatek 3D.
    invert_zoom: bool = False
    recenter: bool = True  # przepinaj gest przy krawędzi ekranu
    center_on_start: bool = True  # ustaw kursor na środku okna przed gestem
    # Czy po zakończeniu gestu kursor zostaje tam, gdzie go zaprowadziła gałka.
    # Bez tego gałka bez modyfikatora byłaby bezużyteczna: kursor jechałby przez
    # ekran i wracał na start.
    keep_cursor: bool = True

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "AxisSettings":
        base = cls()
        for k, v in (d or {}).items():
            if hasattr(base, k):
                setattr(base, k, type(getattr(base, k))(v))
        return base

    def sens_for(self, mode: str) -> float:
        return {"move": self.sens_move, "orbit": self.sens_orbit,
                "pan": self.sens_pan, "zoom": self.sens_zoom}.get(mode, 1.0)


def _foreground_center() -> tuple[int, int] | None:
    hwnd = w.user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = w.wintypes.RECT()
    if not w.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if rect.right - rect.left < 200 or rect.bottom - rect.top < 200:
        return None
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


class Navigator:
    """Jeden aktywny tryb nawigacji naraz."""

    def __init__(self, settings: AxisSettings | None = None) -> None:
        self.settings = settings or AxisSettings()
        self._lock = threading.RLock()
        self._active_mode = ""
        self._preset = NavPreset()
        self._held_keys = ""
        self._held_button = ""
        self._saved_cursor: tuple[int, int] | None = None
        self._vx = 0.0
        self._vy = 0.0
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._wheel_acc = 0.0
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    @property
    def active_mode(self) -> str:
        return self._active_mode

    def update_settings(self, settings: AxisSettings) -> None:
        self.settings = settings

    def start(self, mode: str, preset: NavPreset, center: bool | None = None) -> None:
        """`center=None` bierze ustawienie z konfiguracji; False wymusza start
        w bieżącym punkcie - tak trzeba, gdy przycisk boczny wcisnął już klawisz
        myszy i przeskok kursora na środek okna byłby doklejonym szarpnięciem."""
        with self._lock:
            if self._active_mode == mode:
                return
            if self._active_mode:
                self._stop_locked()

            self._active_mode = mode
            self._preset = preset
            self._acc_x = self._acc_y = 0.0
            self._wheel_acc = 0.0

            if preset.style == "drag":
                self._saved_cursor = w.cursor_pos()
                start_pos = self._saved_cursor
                do_center = self.settings.center_on_start if center is None else center
                # Gest, który nic nie trzyma, to zwykły ruch kursora - przeskok na
                # środek okna byłby wtedy tylko szarpnięciem bez powodu.
                if not (preset.keys or preset.button):
                    do_center = False
                if do_center:
                    middle = _foreground_center()
                    if middle:
                        start_pos = middle
                        w.user32.SetCursorPos(middle[0], middle[1])
                self._vx, self._vy = float(start_pos[0]), float(start_pos[1])
                if preset.keys:
                    out.hold_hotkey(preset.keys, True)
                    self._held_keys = preset.keys
                if preset.button:
                    out.mouse_button(preset.button, True)
                    self._held_button = preset.button
            else:
                self._saved_cursor = None

            self._stop_evt.clear()
            self._thread = threading.Thread(target=self._loop, name="MakmouseNav", daemon=True)
            self._thread.start()

    def feed(self, dx: float, dy: float) -> None:
        with self._lock:
            if not self._active_mode:
                return
            s = self.settings
            if s.swap_xy:
                dx, dy = dy, dx
            if s.invert_x:
                dx = -dx
            if s.invert_y:
                dy = -dy
            self._acc_x += dx
            self._acc_y += dy

    def stop(self, mode: str = "") -> None:
        with self._lock:
            if not self._active_mode:
                return
            if mode and mode != self._active_mode:
                return
            self._stop_locked()

    def release_all(self) -> None:
        """Awaryjne zwolnienie wszystkiego (panic / wyjście z aplikacji)."""
        with self._lock:
            self._stop_locked()

    # ------------------------------------------------------------------ #
    def _stop_locked(self) -> None:
        # Nie dołączamy wątku tików: on sam czeka na ten sam zamek, więc join()
        # trzymałby zwolnienie gestu przez cały timeout. Wyczyszczony _active_mode
        # wystarczy - _tick sprawdza go na wejściu i natychmiast wraca.
        self._stop_evt.set()
        self._thread = None
        self._active_mode = ""

        if self._held_button:
            out.mouse_button(self._held_button, False)
            self._held_button = ""
        if self._held_keys:
            out.hold_hotkey(self._held_keys, False)
            self._held_keys = ""
        if self._saved_cursor:
            # "Zostaw kursor" (ustawienie profilu) sprawia, że wskaźnik kończy tam,
            # gdzie zaprowadziła go gałka - inaczej wraca na pozycję sprzed gestu.
            if not self.settings.keep_cursor:
                w.user32.SetCursorPos(int(self._saved_cursor[0]), int(self._saved_cursor[1]))
            self._saved_cursor = None

    def _loop(self) -> None:
        period = 1.0 / TICK_HZ
        last = time.perf_counter()
        while not self._stop_evt.wait(period):
            now = time.perf_counter()
            dt = min(0.1, now - last)
            last = now
            try:
                self._tick(dt)
            except Exception:  # pragma: no cover - nie przerywaj gestu
                pass

    def _tick(self, _dt: float) -> None:
        with self._lock:
            if not self._active_mode:
                return
            s = self.settings
            sens = s.sens_for(self._active_mode)
            preset = self._preset

            raw_x, raw_y = self._acc_x, self._acc_y
            mx, my = raw_x * sens, raw_y * sens
            self._acc_x = self._acc_y = 0.0

            if preset.style == "wheel":
                # Czułość zoomu jest skokiem kliknięcia, nie tempem ich zliczania:
                # próg liczymy na surowym ruchu, a mnożnik idzie w wysyłany klik.
                val = raw_y if preset.wheel_axis == "y" else raw_x
                self._wheel_acc += val / 90.0
                notches = int(self._wheel_acc)
                if notches:
                    self._wheel_acc -= notches
                    out.wheel(notches * sens)
                return

            if abs(mx) < 1e-4 and abs(my) < 1e-4:
                return

            self._vx += mx
            self._vy += my
            left, top, width, height = w.virtual_screen_rect()
            right, bottom = left + width - 1, top + height - 1

            # Przepinanie ma sens tylko dla gestu, który coś trzyma (orbita, pan).
            # Przy zwykłym ruchu kursora byłoby teleportacją na środek ekranu.
            holds = bool(self._held_button or self._held_keys)
            if s.recenter and holds and (
                self._vx < left + EDGE_MARGIN or self._vx > right - EDGE_MARGIN
                or self._vy < top + EDGE_MARGIN or self._vy > bottom - EDGE_MARGIN
            ):
                self._reanchor()
                return

            self._vx = max(left, min(right, self._vx))
            self._vy = max(top, min(bottom, self._vy))
            out.move_absolute(int(round(self._vx)), int(round(self._vy)))

    def _reanchor(self) -> None:
        """Przepina trwający gest na środek ekranu bez gubienia modyfikatorów."""
        center = _foreground_center()
        if center is None:
            left, top, width, height = w.virtual_screen_rect()
            center = (left + width // 2, top + height // 2)
        if self._held_button:
            out.mouse_button(self._held_button, False)
        w.user32.SetCursorPos(int(center[0]), int(center[1]))
        time.sleep(0.004)
        if self._held_button:
            out.mouse_button(self._held_button, True)
        self._vx, self._vy = float(center[0]), float(center[1])
