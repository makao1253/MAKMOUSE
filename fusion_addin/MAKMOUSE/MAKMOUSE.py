"""Dodatek do Fusion 360 - sterowanie kamerą wprost, bez udziału kursora.

Ten plik NIE jest częścią programu MAKMOUSE. Działa wewnątrz Fusiona (Fusion
sam go ładuje z folderu AddIns) i łączy się z programem MAKMOUSE przez TCP.

ZA CO ODPOWIADA
    * połączenie z MAKMOUSE (127.0.0.1:8765) i ponawianie go co sekundę,
    * odbiór paczek JSON: osie gałki, zoom, widok standardowy, tryb nawigacji,
    * obrót / przesunięcie / przybliżenie kamery Fusiona przez jego API,
    * dziennik zdarzeń w %TEMP%\\makmouse_addin.log (jedyny sposób diagnozy).

NAJWAŻNIEJSZE ELEMENTY
    run() / stop() ............. start i koniec dodatku (woła je Fusion)
    _reader() .................. wątek sieciowy: odbiór danych z MAKMOUSE
    _consume() ................. rozbiór jednej paczki JSON do bufora
    _AxisHandler.notify() ...... obsługa na wątku głównym Fusiona
    _apply() ................... ruch kamery: orbita / przesuwanie / zoom
    _apply_view() .............. widok standardowy (przód, góra, izometria, ...)
    ORBIT_RAD_PER_UNIT, PAN_PER_UNIT, ZOOM_PER_TICK  bazowe tempo kamery

POWIĄZANIA
    Druga strona połączenia: makmouse/bridge.py (serwer) i controller.py (co
    i z jaką czułością jest wysyłane). Opis dodatku: MAKMOUSE.manifest.

SZCZEGÓŁY

Po co
-----
Emulacja myszy (przeciąganie z wciśniętym przyciskiem) to jedyny kanał do
programu, który nic nie wie o urządzeniu - i z definicji rusza kursorem. Ten
dodatek działa WEWNĄTRZ Fusiona, więc przestawia kamerę bezpośrednio przez API.
Kursor nie drga ani o piksel i można jednocześnie pracować zwykłą myszą.
Tak samo działa SpaceMouse: jego sterownik nie udaje myszy, tylko podaje osie
aplikacji, która sama przelicza widok.

Jak
---
Wątek w tle łączy się z MAKMOUSE (gniazdo TCP na localhost) i zbiera przyrosty
osi. API Fusiona nie jest wielowątkowe, więc wątek nie dotyka kamery sam -
odpala zdarzenie własne, które Fusion obsługuje na swoim wątku głównym.
To jest wymagany wzorzec dla urządzeń zewnętrznych.

Komunikaty dziennika i okien są po angielsku, bo interfejs Fusiona też jest
angielski - a dziennik czyta się razem z jego własnymi błędami.

Instalacja: katalog z tym plikiem i manifestem wrzuć do
%APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\AddIns\\
"""
import json
import math
import os
import socket
import tempfile
import threading
import time
import traceback

import adsk.core

HOST = "127.0.0.1"
PORT = 8765
EVENT_ID = "MakmouseAxisEvent"
RECONNECT_S = 1.0

# Dziennik jest jedynym oknem na to, co dzieje się w dodatku: Fusion nie pokazuje
# wyjątków z wątków roboczych, a bez tego "nie działa" jest nie do zdiagnozowania.
LOG_PATH = os.path.join(tempfile.gettempdir(), "makmouse_addin.log")


def _log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write("{}  {}\n".format(time.strftime("%H:%M:%S"), message))
    except OSError:
        pass

# Czułość. Osie przychodzą jako przyrosty w jednostkach urządzenia (-127..127).
ORBIT_RAD_PER_UNIT = 0.006   # radiany obrotu na jednostkę osi
PAN_PER_UNIT = 0.0025        # ułamek odległości kamery na jednostkę osi
ZOOM_PER_TICK = 0.08         # 1 klik enkodera = ok. 8% odległości

_app = None
_ui = None
_event = None
_thread = None
_handlers = []  # Fusion zwalnia obiekty bez referencji - trzymamy je tutaj

_stop = threading.Event()
_lock = threading.Lock()
_pending = {"x": 0.0, "y": 0.0, "zoom": 0.0}
_views = []  # kolejka żądań widoku standardowego (front, góra, ...)
_mode = "orbit"

# Kierunki patrzenia dla widoków standardowych, w układzie Fusiona (Z do góry).
# Wektor wskazuje OD celu DO oka, czyli z której strony patrzymy na model.
_VIEW_DIRS = {
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "back": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "left": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "iso": ((1.0, -1.0, 1.0), (0.0, 0.0, 1.0)),
}


# --------------------------------------------------------------------------- #
# Wątek sieciowy
# --------------------------------------------------------------------------- #
def _consume(line):
    """Dokłada jedną paczkę JSON do bufora i budzi wątek główny."""
    global _mode
    try:
        msg = json.loads(line.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    kind = msg.get("t")
    with _lock:
        if kind == "axis":
            _pending["x"] += float(msg.get("x", 0.0))
            _pending["y"] += float(msg.get("y", 0.0))
        elif kind == "zoom":
            _pending["zoom"] += float(msg.get("d", 0.0))
        elif kind == "view":
            _views.append(str(msg.get("name", "")))
        elif kind == "mode":
            _mode = str(msg.get("mode", "orbit")) if msg.get("on") else "orbit"
            _log("axis mode: " + _mode)
            return False
        else:
            return False
    return True


def _reader():
    """Pętla połączenia. Łapie KAŻDY wyjątek: wątek roboczy, który umrze po cichu,
    wygląda dokładnie tak samo jak dodatek, którego nikt nie uruchomił."""
    announced = False
    while not _stop.is_set():
        sock = None
        try:
            sock = socket.create_connection((HOST, PORT), timeout=2.0)
            sock.settimeout(0.4)
            _log("connected to MAKMOUSE {}:{}".format(HOST, PORT))
            announced = False
            buf = b""
            while not _stop.is_set():
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    _log("MAKMOUSE closed the connection")
                    break
                buf += chunk
                fire = False
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if _consume(line):
                        fire = True
                if fire and _app is not None:
                    _app.fireCustomEvent(EVENT_ID, "")
        except OSError as exc:
            if not announced:  # nie zaśmiecamy dziennika co sekundę
                _log("MAKMOUSE not running ({}), retrying every {:.0f}s".format(
                    exc, RECONNECT_S))
                announced = True
        except Exception:
            _log("network thread error:\n" + traceback.format_exc())
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        _stop.wait(RECONNECT_S)
    _log("network thread finished")


# --------------------------------------------------------------------------- #
# Kamera (tylko wątek główny Fusiona)
# --------------------------------------------------------------------------- #
def _apply(dx, dy, dzoom, mode):
    viewport = _app.activeViewport
    if viewport is None:
        return
    cam = viewport.camera
    eye, target, up = cam.eye, cam.target, cam.upVector

    forward = adsk.core.Vector3D.create(target.x - eye.x, target.y - eye.y, target.z - eye.z)
    dist = forward.length
    if dist < 1e-9:
        return
    right = forward.crossProduct(up)
    if right.length < 1e-9:
        return  # patrzymy dokładnie wzdłuż osi "góry" - obrót byłby nieokreślony
    right.normalize()

    if dx or dy:
        if mode == "pan":
            upn = up.copy()
            upn.normalize()
            step = dist * PAN_PER_UNIT
            shift = right.copy()
            shift.scaleBy(-dx * step)
            vertical = upn.copy()
            vertical.scaleBy(dy * step)
            shift.add(vertical)
            eye.translateBy(shift)
            target.translateBy(shift)
        else:
            # Obrót "obrotowego stołu": odchylenie wokół pionu świata, żeby model
            # się nie przechylał, pochylenie wokół osi poziomej kamery.
            world_up = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
            origin = adsk.core.Point3D.create(0.0, 0.0, 0.0)
            for angle, axis in ((-dx * ORBIT_RAD_PER_UNIT, world_up),
                                (-dy * ORBIT_RAD_PER_UNIT, right)):
                if not angle:
                    continue
                # Punkt obracamy wokół celu, wektor wokół początku układu -
                # inaczej doliczyłaby się do niego translacja.
                rot_point = adsk.core.Matrix3D.create()
                rot_point.setToRotation(angle, axis, target)
                rot_vector = adsk.core.Matrix3D.create()
                rot_vector.setToRotation(angle, axis, origin)
                eye.transformBy(rot_point)
                up.transformBy(rot_vector)

    if dzoom:
        # Skala wykładnicza: każdy klik zmienia skalę o stały procent, więc
        # zbliżanie i oddalanie są symetryczne i nigdy nie przechodzą przez cel.
        factor = math.exp(-dzoom * ZOOM_PER_TICK)
        if cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType:
            # W rzucie ortograficznym - a taki Fusion ma domyślnie - przesuwanie
            # oka NIC nie zmienia w obrazie. Skala widoku to viewExtents i tylko
            # to trzeba ruszyć. To była przyczyna "scroll nie przybliżał".
            cam.viewExtents = max(1e-6, cam.viewExtents * factor)
        else:
            back = adsk.core.Vector3D.create(eye.x - target.x, eye.y - target.y, eye.z - target.z)
            back.normalize()
            back.scaleBy(dist * factor)
            eye = adsk.core.Point3D.create(target.x + back.x, target.y + back.y, target.z + back.z)

    cam.eye = eye
    cam.target = target
    cam.upVector = up
    cam.isSmoothTransition = False  # reakcja 1:1, bez animacji dojazdu
    viewport.camera = cam
    viewport.refresh()


def _apply_view(name):
    """Ustawia widok standardowy, zachowując cel i skalę bieżącego widoku."""
    viewport = _app.activeViewport
    if viewport is None:
        return
    if name == "fit":
        viewport.fit()
        return
    spec = _VIEW_DIRS.get(name)
    if spec is None:
        _log("unknown view: " + str(name))
        return
    (dx, dy, dz), (ux, uy, uz) = spec

    cam = viewport.camera
    target = cam.target
    eye = cam.eye
    dist = adsk.core.Vector3D.create(eye.x - target.x, eye.y - target.y, eye.z - target.z).length
    if dist < 1e-9:
        dist = 10.0

    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    cam.eye = adsk.core.Point3D.create(
        target.x + dx / length * dist,
        target.y + dy / length * dist,
        target.z + dz / length * dist,
    )
    cam.upVector = adsk.core.Vector3D.create(ux, uy, uz)
    cam.isSmoothTransition = False
    viewport.camera = cam
    viewport.refresh()


class _AxisHandler(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            with _lock:
                dx, dy, dzoom = _pending["x"], _pending["y"], _pending["zoom"]
                _pending["x"] = _pending["y"] = _pending["zoom"] = 0.0
                views, _views[:] = list(_views), []
                mode = _mode
            for name in views:
                _apply_view(name)
            if dx or dy or dzoom:
                _apply(dx, dy, dzoom, mode)
        except Exception:
            _log("camera error:\n" + traceback.format_exc())
            if _ui:
                _ui.messageBox("MAKMOUSE - camera error:\n" + traceback.format_exc())


# --------------------------------------------------------------------------- #
# Cykl życia dodatku
# --------------------------------------------------------------------------- #
def run(context):
    global _app, _ui, _event, _thread
    _log("--- run() : MAKMOUSE add-in starting ---")
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        try:
            _app.unregisterCustomEvent(EVENT_ID)  # po przeładowaniu dodatku
        except Exception:
            pass
        _event = _app.registerCustomEvent(EVENT_ID)
        handler = _AxisHandler()
        _event.add(handler)
        _handlers.append(handler)

        _stop.clear()
        _thread = threading.Thread(target=_reader, name="MakmouseBridge")
        _thread.daemon = True
        _thread.start()
        _log("add-in ready, log file: " + LOG_PATH)
    except Exception:
        _log("startup error:\n" + traceback.format_exc())
        if _ui:
            _ui.messageBox("MAKMOUSE - startup error:\n" + traceback.format_exc())


def stop(context):
    global _event, _thread
    try:
        _stop.set()
        if _thread is not None:
            _thread.join(timeout=2.0)
            _thread = None
        if _event is not None:
            for handler in _handlers:
                _event.remove(handler)
            _handlers[:] = []
            _app.unregisterCustomEvent(EVENT_ID)
            _event = None
    except Exception:
        if _ui:
            _ui.messageBox("MAKMOUSE - shutdown error:\n" + traceback.format_exc())
