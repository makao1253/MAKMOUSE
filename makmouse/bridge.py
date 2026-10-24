"""Most do dodatków programów 3D - serwer TCP na localhost (port 8765).

ZA CO ODPOWIADA
    * przyjmowanie połączeń od dodatków programów 3D: Fusion 360 (dodatek
      w fusion_addin/) i SolidCraft (obsługa wbudowana w sam program),
    * rozpoznanie, który program się podłączył (komunikat "hello"),
    * wysyłanie osi gałki, kliknięć zoomu, widoków standardowych i trybu
      nawigacji TYLKO do programu wybranego w profilu - w trybie "Sterowanie
      wprost" kursor się nie rusza,
    * wysyłka w tle: wątek silnika wrzuca dane do kolejki i od razu wraca.

NAJWAŻNIEJSZE ELEMENTY
    Bridge.start()/stop() ...... otwarcie i zamknięcie portu
    Bridge.send(payload, addon)  wrzucenie paczki JSON do kolejki wysyłki
    Bridge.client_count ........ ilu dodatków jest podłączonych w ogóle
    Bridge.clients_for(addon) .. ilu dodatków danego programu jest podłączonych
    ADDON_FUSION, ADDON_SOLIDCRAFT  identyfikatory programów (jak w profilach)

POWIĄZANIA
    używany przez: controller.py (wysyłka), ui/main_window.py (napis o stanie
    dodatku). Druga strona połączenia: fusion_addin/MAKMOUSE/MAKMOUSE.py
    i SolidCraft (Preferencje -> Nawigacja -> mysz 3D, "Nawiguj programem
    urządzenia na tym komputerze").

SZCZEGÓŁY

Po co to istnieje
-----------------
Emulacja myszy (przeciąganie z wciśniętym przyciskiem) to jedyny kanał do
programu, który nic nie wie o naszym urządzeniu - i z definicji rusza kursorem.
Dodatek działający WEWNĄTRZ programu 3D może przestawić kamerę bezpośrednio,
więc kursor zostaje nietknięty. Tak działają profesjonalne manipulatory 3D: ich
sterownik nie udaje myszy, tylko podaje osie aplikacji, która sama przelicza widok.

MAKMOUSE jest serwerem, bo to on trzyma urządzenie i stoi w tle cały czas.
Dodatek łączy się jako klient i ponawia próby, gdy MAKMOUSE jeszcze nie ruszył.

Protokół: jeden obiekt JSON na linię, UTF-8.
    MAKMOUSE -> dodatek
    {"t":"hello","server":"MAKMOUSE","device":"MAKMOUSE"}  zaraz po połączeniu
    {"t":"axis","x":<float>,"y":<float>}   przyrost osi gałki
    {"t":"zoom","d":<float>}               kliki enkodera
    {"t":"view","name":"front"}            widok standardowy
    {"t":"mode","mode":"pan","on":true}    chwilowa zmiana trybu nawigacji
    dodatek -> MAKMOUSE (opcjonalnie)
    {"t":"hello","app":"solidcraft"}       który program się podłączył

"device" w powitaniu to nazwa z deskryptora USB: SolidCraft sam czyta myszy 3D
przez HID, więc po tym napisie wie, że to urządzenie obsługuje MAKMOUSE, i nie
czyta go drugi raz (inaczej widok ruszałby się podwójnie).

Dodatek, który się nie przedstawi (dodatek Fusiona - nie wysyła nic), jest
traktowany jak Fusion. Dzięki temu stary dodatek działa bez zmian.

Paczki idą tylko do dodatku programu wybranego w aktywnym profilu. Gdy Fusion
i SolidCraft są uruchomione jednocześnie, gałka rusza kamerą tylko w tym,
który jest na pierwszym planie.

Wysyłka nigdy nie blokuje wątku silnika: `send` tylko wrzuca dane do kolejki,
a gniazda obsługuje osobny wątek. Gdy klient nie nadąża, gubimy najstarsze
paczki - w strumieniu przyrostów świeższe dane są ważniejsze niż komplet.
"""
from __future__ import annotations

import json
import queue
import socket
import threading
from typing import Callable

from . import __version__
from .i18n import tr

QUEUE_LIMIT = 256
ACCEPT_TIMEOUT = 0.5  # s - żeby wątek akceptujący dało się zatrzymać
MAX_CLIENTS = 8  # więcej dodatków naraz to już nie dodatki, tylko zator
MAX_LINE = 4096  # bajtów - dłuższa linia od klienta jest odrzucana

ADDON_FUSION = "fusion"
ADDON_SOLIDCRAFT = "solidcraft"
# Dodatek, który się nie przedstawił, to dodatek Fusiona (nie wysyła "hello").
LEGACY_ADDON = ADDON_FUSION

HELLO = {"t": "hello", "server": "MAKMOUSE", "device": "MAKMOUSE", "version": __version__}


def _app_name(value: object) -> str:
    """Nazwa programu z powitania - krótka, małymi literami, bez dziwnych znaków."""
    if not isinstance(value, str):
        return ""
    name = "".join(c for c in value.strip().lower() if c.isalnum() or c in "-_")
    return name[:32]


class _Client:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.app = ""  # pusty do czasu powitania

    def serves(self, addon: str) -> bool:
        return (self.app or LEGACY_ADDON) == addon


class Bridge:
    def __init__(self, on_error: Callable[[str], None] | None = None) -> None:
        self._on_error = on_error or (lambda msg: None)
        self._srv: socket.socket | None = None
        self._clients: list[_Client] = []
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue(maxsize=QUEUE_LIMIT)
        self._running = False
        self._threads: list[threading.Thread] = []
        self.port = 0

    # ---------------------------------------------------------------- API ---
    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def clients_for(self, addon: str) -> int:
        """Ilu podłączonych dodatków obsługuje dany program ("fusion", "solidcraft")."""
        with self._lock:
            return sum(1 for c in self._clients if c.serves(addon))

    def start(self, port: int) -> str:
        """Zwraca pusty string przy powodzeniu, inaczej komunikat błędu."""
        if self._running:
            return ""
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", port))
            srv.listen(4)
            srv.settimeout(ACCEPT_TIMEOUT)
        except OSError as exc:
            return tr("most 3D: nie udało się otworzyć portu {port}: {error}").format(
                port=port, error=exc
            )

        self._srv = srv
        self.port = port
        self._running = True
        self._threads = [
            threading.Thread(target=self._accept_loop, name="MakmouseBridgeAccept", daemon=True),
            threading.Thread(target=self._writer_loop, name="MakmouseBridgeWriter", daemon=True),
        ]
        for t in self._threads:
            t.start()
        return ""

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        try:
            self._queue.put_nowait(None)  # budzi wątek zapisu
        except queue.Full:
            pass
        srv, self._srv = self._srv, None
        if srv:
            try:
                srv.close()
            except OSError:
                pass
        with self._lock:
            for client in self._clients:
                self._close(client.sock)
            self._clients.clear()

    def send(self, payload: dict, addon: str = LEGACY_ADDON) -> None:
        """Wołane z wątku silnika - musi wrócić natychmiast.

        `addon` to program, do którego dodatku paczka ma trafić (z profilu).
        """
        if not self._running:
            return
        with self._lock:
            if not any(c.serves(addon) for c in self._clients):
                return  # nikt tego programu nie słucha, nie ma po co pakować JSON-a
        item = (payload, addon)
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            # Zrzucamy najstarszą paczkę, żeby przepuścić świeższą.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(item)
            except (queue.Empty, queue.Full):
                pass

    # ------------------------------------------------------------- wątki ---
    def _accept_loop(self) -> None:
        while self._running:
            srv = self._srv
            if srv is None:
                break
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self._lock:
                full = len(self._clients) >= MAX_CLIENTS
            if full:
                self._close(conn)
                continue
            try:
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(None)  # gniazdo z accept() dziedziczy timeout serwera
                # Powitanie: kto nadaje i jakie urządzenie czyta. Dodatek Fusiona
                # nieznany typ komunikatu po prostu pomija.
                conn.sendall((json.dumps(HELLO, separators=(",", ":")) + "\n").encode("utf-8"))
            except OSError:
                self._close(conn)
                continue
            client = _Client(conn)
            with self._lock:
                self._clients.append(client)
            threading.Thread(target=self._reader_loop, args=(client,),
                             name="MakmouseBridgeReader", daemon=True).start()

    def _reader_loop(self, client: _Client) -> None:
        """Czyta, co dodatek mówi (powitanie), i zauważa jego rozłączenie.

        Bez tego zamknięty program liczyłby się jako podłączony aż do pierwszej
        nieudanej wysyłki - a profil nie wróciłby do emulacji przeciągania.
        """
        buf = b""
        while self._running:
            try:
                chunk = client.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._consume(client, line)
            if len(buf) > MAX_LINE:
                break  # linia bez końca - to nie jest dodatek
        self._drop(client)

    def _consume(self, client: _Client, line: bytes) -> None:
        try:
            msg = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        if isinstance(msg, dict) and msg.get("t") == "hello":
            name = _app_name(msg.get("app"))
            if name:
                with self._lock:
                    client.app = name

    def _writer_loop(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            payload, addon = item
            line = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
            with self._lock:
                targets = [c for c in self._clients if c.serves(addon)]
            for client in targets:
                try:
                    client.sock.sendall(line)
                except OSError:
                    self._drop(client)

    def _drop(self, client: _Client) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)
        self._close(client.sock)

    @staticmethod
    def _close(sock: socket.socket) -> None:
        try:
            sock.close()
        except OSError:
            pass
