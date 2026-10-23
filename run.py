"""Punkt startowy MAKMOUSE - od tego pliku zaczyna się działanie programu.

ZA CO ODPOWIADA
    * pilnowanie, żeby działała tylko jedna kopia programu (muteks systemowy),
    * wczytanie konfiguracji, ustawienie języka, motywu i koloru wiodącego,
    * utworzenie kontrolera (logika) i okna, uruchomienie pętli Qt,
    * odbudowa okna od zera po zmianie języka - bez zatrzymywania urządzenia.

NAJWAŻNIEJSZE ELEMENTY
    main() ............... kolejność startu całej aplikacji
    WindowHost ........... trzyma okno główne i buduje je ponownie po zmianie języka
    _single_instance() ... blokada drugiego uruchomienia

POWIĄZANIA
    używa: makmouse/profiles.py (load), controller.py, ui/main_window.py,
    ui/theme.py, i18n.py
    uruchamiany przez: `python run.py`, MAKMOUSE.bat, `python -m makmouse`,
    a w wersji .exe - przez PyInstaller (MAKMOUSE.spec, MAKMOUSE-onefile.spec)

Uruchomienie:  python run.py
"""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from makmouse import APP_NAME, __version__
from makmouse import i18n
from makmouse import profiles as P
from makmouse.controller import Controller
from makmouse.i18n import tr
from makmouse.ui import theme as T
from makmouse.ui.main_window import MainWindow

ERROR_ALREADY_EXISTS = 183


def _single_instance() -> bool:
    """Zwraca False jeśli MAKMOUSE już działa."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Global\\MakmouseRemapperSingleton")
    if not handle:
        return True  # nie udało się sprawdzić - pozwól działać
    _single_instance.handle = handle  # utrzymaj uchwyt przy życiu
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


class WindowHost(QObject):
    """Trzyma okno główne i buduje je od nowa po zmianie języka.

    Tłumaczenia trafiają do widgetów w chwili tworzenia, więc nie da się ich
    podmienić w locie bez pisania `retranslate()` dla każdej kontrolki z osobna.
    Zamiast tego stawiamy okno jeszcze raz - kontroler, silnik i most żyją dalej,
    więc urządzenie nie przestaje działać nawet na moment.
    """

    def __init__(self, cfg: P.Config, controller: Controller) -> None:
        super().__init__()
        self.cfg = cfg
        self.controller = controller
        self.window: MainWindow | None = None

    def build(self, show: bool = True) -> MainWindow:
        previous, self.window = self.window, None
        if previous is not None:
            # Import konfiguracji podmienia cały obiekt Config w oknie - nowe
            # okno musi dostać ten, na którym pracuje kontroler, a nie ten,
            # z którym host wystartował.
            self.cfg = previous.cfg
            previous.detach()

        window = MainWindow(self.cfg, self.controller)
        window.languageChanged.connect(self._on_language_changed)
        self.window = window
        if show:
            window.show()

        if previous is not None:
            previous.close()
            previous.deleteLater()
        return window

    @Slot(str)
    def _on_language_changed(self, _code: str) -> None:
        # Nowe okno pokazujemy tylko wtedy, gdy stare było widoczne - zmiana
        # języka z zasobnika nie ma prawa wyciągnąć okna na wierzch.
        visible = bool(self.window and self.window.isVisible())
        self.build(show=visible)


def main() -> int:
    if sys.platform != "win32":
        print(tr("MAKMOUSE działa tylko na Windows."))
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MAKMOUSE")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(T.make_icon())

    if not _single_instance():
        QMessageBox.information(
            None, APP_NAME, tr("MAKMOUSE już działa (sprawdź zasobnik systemowy).")
        )
        return 0

    # Motyw i język znamy dopiero z konfiguracji - stylujemy po jej wczytaniu,
    # żeby okno nie mrugnęło ciemnym tłem przed przełączeniem na jasne.
    cfg, load_error = P.load()
    i18n.set_language(cfg.language)
    T.apply_mode(cfg.theme)
    T.apply_accent(cfg.accent)  # kolor wiodący wybrany w Ustawieniach
    app.setStyleSheet(T.stylesheet())
    app.setWindowIcon(T.make_icon())

    controller = Controller(cfg)
    host = WindowHost(cfg, controller)
    window = host.build(show=not cfg.start_minimized)
    controller.start()

    if load_error:
        window.status_action.setText(load_error)

    app.aboutToQuit.connect(controller.stop)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
