"""Kontroler - "mózg" programu: zdarzenie z urządzenia -> profil -> akcja.

ZA CO ODPOWIADA
    * uruchomienie i zatrzymanie wszystkich części (silnik, most, obserwator
      programów, skrót awaryjny),
    * wybór aktywnego profilu według programu na pierwszym planie,
    * decyzja, co zrobić z każdym zdarzeniem:
        - przycisk boczny -> akcja z profilu (skrót, przytrzymanie, nawigacja 3D,
          widok przez dodatek 3D), z obsługą przełącznika,
        - ruch gałki -> dodatek 3D programu z profilu (Fusion albo SolidCraft,
          sterowanie wprost) albo gest przez Navigator,
        - obrót pierścienia -> zoom/scroll ze skokiem z czułości zoomu,
    * czułości osi (ruch gałki / orbita / przesuwanie) w obu ścieżkach,
    * skrót awaryjny (domyślnie Ctrl+Alt+F12) - puszcza wszystko i wyłącza program.

NAJWAŻNIEJSZE ELEMENTY
    Controller ............ główna klasa; sygnały Qt informują okno o zdarzeniach
    Controller._on_axis ... ruch gałki (wołany wprost z wątku silnika)
    Controller._press / _release / _activate / _deactivate  przyciski boczne
    Controller._do_wheel .. pierścień (zoom)
    Controller._push_engine_config  przelicza ustawienia silnika po każdej zmianie
    AxisGesture ........... gest gałki prowadzony przez Navigator, kończony po
                            chwili bezczynności (gałka nie ma "puszczenia")
    GestureHold ........... modyfikator trzymany w trakcie scrolla

POWIĄZANIA
    używa: engine.py, navigator.py, output.py, bridge.py, appwatch.py,
    devices.py, profiles.py, keys.py
    używany przez: run.py (tworzy go), ui/main_window.py (sygnały, apply())

SZCZEGÓŁY
Kontroler żyje w wątku GUI, ale zdarzenia dostaje z wątku silnika. Akcje są
wykonywane w osobnym wątku roboczym, żeby callback hooka niskopoziomowego
wracał natychmiast (Windows odpina hooki, które odpowiadają zbyt długo).
"""
from __future__ import annotations

import queue
import threading
import time

from PySide6.QtCore import QObject, Signal

from . import appwatch
from . import devices as dv
from . import keys as K
from . import output as out
from .bridge import Bridge
from .engine import EngineConfig, InputEngine, InputEvent
from .i18n import tr
from .navigator import HoldPreset, NavPreset, Navigator
from .profiles import BUTTON_SLOTS, Binding, Config, Profile

MONITOR_MIN_INTERVAL = 0.05  # s - throttling podglądu zdarzeń w GUI
AXIS_NAV_MODE = "move"  # tryb Navigatora zarezerwowany dla gestu gałki
AXIS_IDLE = 0.25  # s - po tylu bez zdarzeń osi gest gałki uznajemy za skończony


class GestureHold:
    """Trzyma modyfikatory gestu ciągłego i zwalnia je po chwili bezczynności.

    Ruch gałki i obrót pierścienia nie mają "puszczenia" - jedynym sygnałem końca
    gestu jest to, że przestały przychodzić zdarzenia.
    """

    def __init__(self, idle: float = 0.25) -> None:
        self._idle = idle
        self._lock = threading.Lock()
        self._keys = ""
        self._button = ""
        self._last = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="MakmouseGesture", daemon=True)

    @property
    def active(self) -> bool:
        return bool(self._keys or self._button)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.release()

    def poke(self, preset: HoldPreset) -> None:
        """Zgłasza aktywność gestu; przy zmianie presetu przepina modyfikatory."""
        with self._lock:
            self._last = time.perf_counter()
            if preset.keys == self._keys and preset.button == self._button:
                return
            self._release_locked()
            if preset.keys:
                out.hold_hotkey(preset.keys, True)
                self._keys = preset.keys
            if preset.button:
                out.mouse_button(preset.button, True)
                self._button = preset.button

    def release(self) -> None:
        with self._lock:
            self._release_locked()

    def _release_locked(self) -> None:
        if self._button:
            out.mouse_button(self._button, False)
            self._button = ""
        if self._keys:
            out.hold_hotkey(self._keys, False)
            self._keys = ""

    def _loop(self) -> None:
        while not self._stop.wait(0.04):
            with self._lock:
                if (self._keys or self._button) and time.perf_counter() - self._last > self._idle:
                    self._release_locked()


class AxisGesture:
    """Gest gałki prowadzony przez Navigatora.

    Przeciąganie jest tylko środkiem: żeby Fusion (i każdy inny program 3D)
    zorbitował, trzeba mu podać wciśnięty przycisk i ruch kursora. Navigator
    zapamiętuje pozycję wskaźnika przed gestem; co się z nią stanie po geście,
    decyduje ustawienie profilu `keep_cursor` ("Zostaw kursor w nowym miejscu"):
    kursor zostaje tam, dokąd dojechał, albo wraca na pozycję sprzed gestu.
    Pusty preset (bez modyfikatora) to zwykły ruch kursora.

    Gałka nie ma "puszczenia": gest kończy brak zdarzeń przez `AXIS_IDLE`.
    Dopóki trzymany jest przycisk boczny, gest zostaje otwarty - odtworzenie
    kursora przy wciśniętym klawiszu myszy cofnęłoby właśnie zrobiony ruch.
    """

    def __init__(self, navigator: Navigator, idle: float = AXIS_IDLE) -> None:
        self._nav = navigator
        self._idle = idle
        self._lock = threading.Lock()
        self._preset: HoldPreset | None = None
        self._hold_open = False
        self._last = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="MakmouseAxisGesture", daemon=True)

    @property
    def active(self) -> bool:
        return self._preset is not None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.release()

    def poke(self, preset: HoldPreset, hold_open: bool = False) -> None:
        """Zgłasza aktywność gałki; przy zmianie presetu przepina cały gest."""
        with self._lock:
            self._last = time.perf_counter()
            self._hold_open = hold_open
            if self._preset is not None and (
                (preset.keys, preset.button) == (self._preset.keys, self._preset.button)
            ):
                return
            if self._preset is not None:
                self._nav.stop(AXIS_NAV_MODE)
            # Gdy przycisk boczny trzyma już klawisz myszy, nie centrujemy -
            # przeskok kursora byłby doklejony do jego gestu.
            self._nav.start(
                AXIS_NAV_MODE,
                NavPreset(keys=preset.keys, button=preset.button, style="drag"),
                center=False if hold_open else None,
            )
            self._preset = preset

    def release(self) -> None:
        with self._lock:
            self._release_locked()

    def _release_locked(self) -> None:
        if self._preset is not None:
            self._nav.stop(AXIS_NAV_MODE)
            self._preset = None
        self._hold_open = False

    def _loop(self) -> None:
        while not self._stop.wait(0.04):
            with self._lock:
                idle = time.perf_counter() - self._last > self._idle
                if self._preset is not None and idle and not self._hold_open:
                    self._release_locked()


class Controller(QObject):
    sig_event = Signal(object)  # InputEvent -> grafika urządzenia i monitor
    sig_profile = Signal(str, str)  # nazwa profilu, exe
    sig_devices = Signal()  # zmiana listy urządzeń (sygnał z wątku silnika)
    sig_device_state = Signal(bool)  # czy MAKMOUSE jest podłączony
    sig_error = Signal(str)
    sig_enabled = Signal(bool)
    sig_action = Signal(str)

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.current_profile: Profile = cfg.active_profile("")
        # Ustawienia osi należą do profilu - Navigator dostaje je razem z każdą
        # zmianą aktywnego programu.
        self.navigator = Navigator(self.current_profile.axes)
        self.engine = InputEngine(
            on_event=self._on_engine_event,
            on_devices_changed=lambda: self.sig_devices.emit(),
            on_error=lambda m: self.sig_error.emit(m),
        )
        self.current_exe = ""
        self.found_devices: list[dv.DeviceInfo] = []

        self._target_paths: frozenset[str] = frozenset()
        self._actions: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._action_loop, name="MakmouseActions", daemon=True)
        self._held: dict[int, Binding] = {}
        self._last_monitor: dict[str, float] = {}
        self._running = False
        # Tryb nawigacji włączony przyciskiem przy sterowaniu wprost. Navigator
        # w tej ścieżce nie działa, więc czułość osi trzeba wybrać tutaj.
        self._direct_mode = ""

        self._axis_gesture = AxisGesture(self.navigator)
        self._hold_scroll = GestureHold()
        self.bridge = Bridge(on_error=lambda m: self.sig_error.emit(m))

        self._watcher = appwatch.AppWatcher(self._on_app_changed)
        self._panic_stop = threading.Event()
        self._panic_thread = threading.Thread(target=self._panic_loop, name="MakmousePanic", daemon=True)

    # ----------------------------------------------------------- start/stop --
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker.start()
        self._axis_gesture.start()
        self._hold_scroll.start()
        self._watcher.start()
        self._panic_thread.start()
        if self.cfg.bridge_enabled:
            err = self.bridge.start(self.cfg.bridge_port)
            if err:
                self.sig_error.emit(err)
        # Tryb musi być znany zanim silnik założy źródła wejścia - inaczej ruszyłby
        # z domyślnym trybem myszy i na moment zapiął hooka niskopoziomowego.
        self._push_engine_config()
        self.engine.start()
        self.engine.ready.wait(3.0)
        if self.engine.last_error:
            self.sig_error.emit(self.engine.last_error)
        self.refresh_devices()

    def stop(self) -> None:
        self._running = False
        self._panic_stop.set()
        self._watcher.stop()
        self.release_everything()
        self.bridge.stop()
        self._axis_gesture.stop()
        self._hold_scroll.stop()
        self.engine.stop()
        self._actions.put(None)

    def release_everything(self) -> None:
        self._direct_mode = ""
        self._axis_gesture.release()
        self.navigator.release_all()
        self._hold_scroll.release()
        for binding in list(self._held.values()):
            self._deactivate(binding)
        self._held.clear()

    # -------------------------------------------------------------- device --
    def refresh_devices(self) -> list[dv.DeviceInfo]:
        """Szuka kolekcji HID należących do MAKMOUSE i przekazuje je do silnika."""
        try:
            everything = dv.enumerate_devices()
        except Exception as exc:  # pragma: no cover
            self.sig_error.emit(tr("wyliczanie urządzeń: {error}").format(error=exc))
            everything = []
        self.found_devices = [d for d in everything if d.is_makmouse]
        self._target_paths = frozenset(d.path.lower() for d in self.found_devices)

        self._push_engine_config()
        self.sig_device_state.emit(bool(self.found_devices))
        return self.found_devices

    @property
    def device_present(self) -> bool:
        return bool(self.found_devices)

    # -------------------------------------------------------------- config --
    def apply(self, cfg: Config) -> None:
        self.cfg = cfg
        self.current_profile = cfg.active_profile(self.current_exe)
        self.navigator.update_settings(self.current_profile.axes)
        self._push_engine_config()
        self.sig_profile.emit(self.current_profile.name, self.current_exe)

    @property
    def axes(self):
        """Ustawienia osi aktywnego profilu."""
        return self.current_profile.axes

    def set_enabled(self, enabled: bool) -> None:
        self.cfg.enabled = enabled
        if not enabled:
            self.release_everything()
        self._push_engine_config()
        self.sig_enabled.emit(enabled)

    def _push_engine_config(self) -> None:
        cfg, prof = self.cfg, self.current_profile
        mouse_mode = cfg.device.mode == "mouse"
        live = cfg.enabled and self.device_present
        scroll_gesture = prof.gestures.get("scroll") or HoldPreset()

        suppress: set[int] = set()
        if live and mouse_mode:
            for idx, binding in prof.buttons.items():
                if 1 <= idx <= min(5, cfg.button_count) and binding.is_active():
                    suppress.add(idx)

        self.engine.apply_config(
            EngineConfig(
                enabled=cfg.enabled,
                mode=cfg.device.mode,
                target_paths=self._target_paths,
                suppress_buttons=frozenset(suppress),
                suppress_movement=bool(live and mouse_mode and cfg.suppress_movement),
                # Scroll przechwytujemy wtedy, gdy trzeba go wzbogacić o modyfikator,
                # przeliczyć impulsy enkodera na kliknięcia albo odwrócić jego
                # kierunek - inaczej dotarłby do programu takim, jakim wyszedł
                # z urządzenia.
                suppress_wheel=bool(live and mouse_mode and (
                    scroll_gesture.active() or abs(prof.axes.sens_zoom - 1.0) > 1e-3
                    or prof.axes.invert_zoom
                )),
                hid_layout=cfg.device.hid_layout,
            )
        )

    # -------------------------------------------------------------- profile --
    def _on_app_changed(self, exe: str, _path: str) -> None:
        self.current_exe = exe
        profile = self.cfg.active_profile(exe)
        if profile is not self.current_profile:
            self.release_everything()
            self.current_profile = profile
            self.navigator.update_settings(profile.axes)
            self._push_engine_config()
        self.sig_profile.emit(profile.name, exe)

    # -------------------------------------------------------------- events --
    def _on_engine_event(self, ev: InputEvent) -> None:
        """Wołane z wątku silnika (czasem z wnętrza hooka) - musi być szybkie."""
        if self.cfg.enabled:
            if ev.kind == "axis":
                self._on_axis(ev)
            elif ev.kind in ("button", "wheel"):
                self._actions.put(ev)
        self._emit_monitor(ev)

    def _on_axis(self, ev: InputEvent) -> None:
        """Gałka NIGDY nie przesuwa kursora na stałe.

        Każdy ruch osi trafia do Navigatora - albo do trybu włączonego przyciskiem
        bocznym, albo do gestu gałki. Navigator oddaje pozycję kursora po
        zakończeniu gestu, więc zwykła mysz zostaje tam, gdzie ją zostawiłeś.
        """
        # Sterowanie wprost: dodatek w programie 3D przestawia kamerę sam, więc
        # nie ma tu żadnej emulacji myszy - kursor nie drgnie ani o piksel.
        if self._direct():
            dx, dy = self._shape_axes(ev.dx, ev.dy)
            if dx or dy:
                self._send({"t": "axis", "x": dx, "y": dy})
            return
        # Tryb nawigacji włączony przyciskiem ma pierwszeństwo nad gestem gałki.
        if self.navigator.active_mode and self.navigator.active_mode != AXIS_NAV_MODE:
            self.navigator.feed(ev.dx, ev.dy)
            return
        if ev.dx == 0.0 and ev.dy == 0.0:
            return  # koniec paczki zdarzeń - gest zamknie licznik bezczynności

        # Pusty preset jest pełnoprawnym ustawieniem: gałka rusza wtedy kursorem
        # bez żadnego modyfikatora, czyli zachowuje się jak zwykła mysz. Wcześniej
        # brak modyfikatora blokował gest całkowicie i gałka była martwa wszędzie
        # poza profilami z wpisanym akordem orbity.
        preset = self.current_profile.gestures.get("move") or HoldPreset()

        # Przy trzymanym przycisku bocznym to on wnosi klawisze i przycisk myszy,
        # a gest gałki dokłada sam ruch (i zostaje otwarty aż do puszczenia).
        self._axis_gesture.poke(HoldPreset() if self._held else preset, hold_open=bool(self._held))
        self.navigator.feed(ev.dx, ev.dy)

    def _shape_axes(self, dx: float, dy: float) -> tuple[float, float]:
        """Ustawienia osi muszą działać tak samo w każdej ścieżce.

        Bez tego suwaki czułości i odwracanie osi zmieniają tylko zachowanie poza
        programem 3D, a w samym Fusionie nie robią nic.

        Gdy przycisk boczny trzyma tryb nawigacji (także jako przełącznik), osie
        dostają czułość tego trybu - orbity albo przesuwania - zamiast czułości
        zwykłego ruchu gałki. W emulacji przeciągania robi to Navigator; tutaj,
        przy sterowaniu wprost, nie ma go w torze, więc mnożnik wybieramy sami.
        """
        a = self.axes
        if a.swap_xy:
            dx, dy = dy, dx
        if a.invert_x:
            dx = -dx
        if a.invert_y:
            dy = -dy
        sens = a.sens_for(self._direct_mode) if self._direct_mode else a.sens_move
        return dx * sens, dy * sens

    def _direct(self) -> bool:
        """Czy osie mają iść wprost do dodatku programu 3D.

        Wymaga podłączonego dodatku programu wybranego w profilu (Fusion albo
        SolidCraft) - bez niego profil sam wraca do emulacji myszy, żeby
        zamknięcie programu nie unieruchamiało gałki.
        """
        prof = self.current_profile
        return prof.direct and self.bridge.clients_for(prof.addon) > 0

    def _send(self, payload: dict) -> None:
        """Paczka do dodatku programu z aktywnego profilu - i tylko do niego."""
        self.bridge.send(payload, self.current_profile.addon)

    def _emit_monitor(self, ev: InputEvent) -> None:
        if ev.kind in ("axis", "report"):
            now = time.perf_counter()
            if now - self._last_monitor.get(ev.kind, 0.0) < MONITOR_MIN_INTERVAL:
                return
            self._last_monitor[ev.kind] = now
        self.sig_event.emit(ev)

    # ------------------------------------------------------------- actions --
    def _action_loop(self) -> None:
        while True:
            item = self._actions.get()
            if item is None:
                break
            try:
                self._dispatch(item)
            except Exception as exc:  # pragma: no cover
                self.sig_error.emit(tr("akcja: {error}").format(error=exc))

    def _dispatch(self, ev: InputEvent) -> None:
        if ev.kind == "wheel":
            self._do_wheel(ev)
            return
        idx = ev.index
        # Ponad wybraną w Ustawieniach liczbę przycisków urządzenie ich po prostu
        # nie ma - bity z raportu ignorujemy, choćby firmware je wystawiał.
        if not (1 <= idx <= min(BUTTON_SLOTS, self.cfg.button_count)):
            return
        if ev.pressed:
            self._press(idx)
        else:
            self._release(idx)

    def _press(self, idx: int) -> None:
        latched = self._held.get(idx)
        if latched is not None and latched.is_toggle():
            # Drugie wciśnięcie tego samego przełącznika gasi akcję.
            del self._held[idx]
            self._deactivate(latched)
            self._close_axis_gesture()
            self.sig_action.emit(tr("Przycisk boczny {index} -> wyłączono: {action}")
                                 .format(index=idx, action=latched.describe()))
            return

        binding = self.current_profile.buttons.get(idx, Binding())
        if not binding.is_active():
            return
        if binding.type == "view":
            if not self._direct():
                self.sig_action.emit(tr("Widok wymaga podłączonego dodatku 3D"))
                return
            self._send({"t": "view", "name": binding.view})
            self.sig_action.emit(tr("Przycisk boczny {index} -> {action}")
                                 .format(index=idx, action=binding.describe()))
            return

        self._axis_gesture.release()  # przycisk przejmuje gest gałki
        self._held[idx] = binding
        self._activate(binding)
        self.sig_action.emit(tr("Przycisk boczny {index} -> {action}")
                             .format(index=idx, action=binding.describe()))

    def _release(self, idx: int) -> None:
        binding = self._held.get(idx)
        if binding is None:
            return
        if binding.is_toggle():
            return  # przełącznik gasi dopiero kolejne wciśnięcie, nie puszczenie
        del self._held[idx]
        self._deactivate(binding)
        self._close_axis_gesture()

    def _close_axis_gesture(self) -> None:
        """Gest gałki był trzymany otwarty przez przycisk - domykamy go, żeby
        Navigator oddał pozycję kursora."""
        if not self._held:
            self._axis_gesture.release()

    def _do_wheel(self, ev: InputEvent) -> None:
        """Każdy impuls pierścienia to jedno kliknięcie zoomu - czułość zmienia
        jego SKOK, a nie liczbę impulsów potrzebnych na kliknięcie.

        Dzięki temu ta sama wartość działa wszędzie tak samo: strona przewija się
        o mniej wierszy, a kamera w programie 3D podchodzi do bryły o mniejszy
        kawałek - zamiast zmuszać do kręcenia pierścieniem więcej razy.
        """
        step = float(ev.dx) * self.axes.sens_zoom
        if self.axes.invert_zoom:
            step = -step
        if self._direct():
            if step:
                self._send({"t": "zoom", "d": step})
            return
        preset = self.current_profile.gestures.get("scroll") or HoldPreset()
        if preset.active():
            self._hold_scroll.poke(preset)
        # W surowym HID Windows nie przewija sam - scroll wysyłamy my. W trybie
        # myszy tylko wtedy, gdy oryginalne zdarzenie zostało zablokowane.
        if ev.suppressed or self.cfg.device.mode == "hid":
            out.wheel(step)
        if preset.active():
            self.sig_action.emit(tr("Scroll {delta:+.2f} -> {action}")
                                 .format(delta=step, action=preset.describe()))

    def _activate(self, binding: Binding) -> None:
        if binding.type == "hotkey":
            out.tap_hotkey(binding.hotkey)
        elif binding.type == "hold":
            if binding.hotkey:
                out.hold_hotkey(binding.hotkey, True)
            if binding.button:
                out.mouse_button(binding.button, True)
        elif binding.type == "nav":
            # W sterowaniu wprost tryb nawigacji to tylko informacja dla dodatku -
            # żadnych przycisków myszy do wciskania tu nie ma.
            if self._direct():
                self._direct_mode = binding.nav
                self._send({"t": "mode", "mode": binding.nav, "on": True})
                return
            preset = self.current_profile.nav.get(binding.nav)
            if preset:
                self.navigator.start(binding.nav, preset)

    def _deactivate(self, binding: Binding) -> None:
        if binding.type == "hold":
            if binding.button:
                out.mouse_button(binding.button, False)
            if binding.hotkey:
                out.hold_hotkey(binding.hotkey, False)
        elif binding.type == "nav":
            if self._direct_mode == binding.nav:
                self._direct_mode = ""
            if self._direct():
                self._send({"t": "mode", "mode": binding.nav, "on": False})
                return
            self.navigator.stop(binding.nav)

    # --------------------------------------------------------------- panic --
    def _panic_loop(self) -> None:
        from .winapi import user32

        armed = False
        while not self._panic_stop.wait(0.06):
            mods, main = K.parse_hotkey(self.cfg.panic_hotkey)
            if main is None:
                continue
            need = mods + [main]
            hit = all(user32.GetAsyncKeyState(vk) & 0x8000 for vk in need)
            if hit and not armed:
                armed = True
                self.release_everything()
                self.set_enabled(not self.cfg.enabled)
            elif not hit:
                armed = False
