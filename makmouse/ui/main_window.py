"""Okno główne MAKMOUSE - wszystko, co użytkownik widzi i klika.

ZA CO ODPOWIADA
    * układ okna: pasek górny (stan urządzenia, "i", motyw, Aktywny), lista
      profili, podgląd na żywo z legendą, zakładki, pasek stanu, ikona w zasobniku,
    * zakładki: Przyciski i gesty, Nawigacja 3D, Urządzenie, Monitor, Ustawienia,
    * przenoszenie ustawień z kontrolek do konfiguracji (i z powrotem przy zmianie
      profilu) - każda zmiana od razu trafia do kontrolera i jest zapisywana,
    * pokazywanie zdarzeń z urządzenia (podgląd, lampki, log w Monitorze),
    * import / eksport / reset konfiguracji i zmiana miejsca pliku config.json.

NAJWAŻNIEJSZE ELEMENTY (klasa MainWindow)
    _build_*() / _tab_*() ..... budowa kolejnych części okna i zakładek
    _load_profile_into_ui() ... wpisuje wybrany profil do wszystkich kontrolek
    _on_*_changed() ........... zapis zmian z kontrolek do konfiguracji
    _refresh_legend() ......... legenda pod podglądem (funkcje + kropki wł./wył.)
    _on_input_event() ......... zdarzenie z urządzenia -> podgląd i Monitor
    _touch() .................. "coś się zmieniło": kontroler + zapis po 0,6 s
    _restyle() ................ ponowne nadanie kolorów po zmianie motywu/koloru

POWIĄZANIA
    używa: controller.py (sygnały, apply), profiles.py (konfiguracja), widgets.py,
    device_view.py, theme.py, help_dialog.py, i18n.py
    tworzony przez: run.py (WindowHost - odbudowa okna po zmianie języka)
"""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QRectF, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSystemTrayIcon, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__, devices as dv, i18n, keys as K, profiles as P
from ..controller import Controller
from ..engine import InputEvent
from ..i18n import tr
from ..navigator import HoldPreset, NavPreset
from ..profiles import Binding, Config, Profile
from . import theme as T
from .device_view import DeviceView
from .help_dialog import HelpDialog
from .widgets import (
    AxisBar, ButtonCard, ButtonLamp, Card, GestureEditor, HotkeyEdit, SliderRow,
    StatusPill, ThemeSwitch, ToggleSwitch, combo, hint, row,
)

LOG_LIMIT = 400
TAB_DEVICE = 2


def _color_icon(code: str, size: int = 14) -> QIcon:
    """Kwadracik koloru na rozwijanej liście kolorów wiodących."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(code))
    p.drawRoundedRect(QRectF(0, 0, size, size), 3, 3)
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    # Zmiana języka nie da się nanieść na gotowe widgety - okno jest budowane od
    # nowa przez `run.WindowHost`, a ten sygnał jest prośbą o przebudowę.
    languageChanged = Signal(str)

    def __init__(self, cfg: Config, controller: Controller) -> None:
        super().__init__()
        self.cfg = cfg
        self.ctl = controller
        self._loading = False
        self._captures = 0
        self._last_report: bytes = b""
        self._button_cards: dict[int, ButtonCard] = {}
        self._gesture_editors: dict[str, GestureEditor] = {}
        self._lamps: dict[int, ButtonLamp] = {}
        self._active_profile_name = ""
        self._detached = False  # okno oddane do skasowania po zmianie języka

        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(T.make_icon())
        self.resize(1380, 790)
        # Minimum dobrane pod ekran 1366x768 z paskiem zadań - przy mniejszym
        # oknie zawartość zakładek nadal mieści się bez przewijania.
        self.setMinimumSize(1060, 580)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._save_now)

        # Dodatek 3D łączy się sam, kiedy tylko wstanie program - stan trzeba
        # odświeżać, a nie odczytywać raz przy starcie okna.
        self._bridge_timer = QTimer(self)
        self._bridge_timer.setInterval(1000)
        self._bridge_timer.timeout.connect(self._update_bridge_label)

        self._build_ui()
        self._build_tray()
        self._connect_controller()
        self.load_profile_list()
        self._sync_globals()
        self._bridge_timer.start()

    # ================================================================= UI ==
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 6)
        outer.setSpacing(8)

        outer.addWidget(self._build_topbar())

        middle = QHBoxLayout()
        middle.setSpacing(10)
        middle.addWidget(self._build_sidebar(), 0)
        middle.addWidget(self._build_device_panel(), 0)
        middle.addWidget(self._build_tabs(), 1)
        outer.addLayout(middle, 1)

        self.setCentralWidget(root)

        self.status_action = QLabel(tr("Gotowe"))
        self.status_path = QLabel(str(P.config_path()))
        self.status_path.setObjectName("Hint")
        self.statusBar().addWidget(self.status_action, 1)
        self.statusBar().addPermanentWidget(self.status_path)

    def _build_topbar(self) -> QWidget:
        card = Card()
        bar = QHBoxLayout()
        bar.setSpacing(16)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel("MAKMOUSE")
        brand.setObjectName("Brand")
        sub = QLabel(f"CAD Software {__version__}")
        sub.setObjectName("BrandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(sub)
        bar.addLayout(brand_box)
        bar.addSpacing(10)

        self.pill_device = StatusPill(dv.TARGET_NAME, T.WARN, dot=15.0)
        font = self.pill_device.font()
        # pointSizeF() daje -1, gdy arkusz stylów ustawił rozmiar w pikselach -
        # dodawanie do tego wyprodukowałoby nieprawidłowy rozmiar.
        base = font.pointSizeF()
        font.setPointSizeF((base if base > 0 else 9.0) + 1.5)
        font.setBold(True)
        self.pill_device.setFont(font)
        bar.addWidget(self.pill_device)
        bar.addStretch(1)

        self.btn_help = QPushButton("i")
        self.btn_help.setObjectName("Info")
        self.btn_help.setFixedSize(30, 30)
        self.btn_help.setToolTip(tr("Instrukcja obsługi"))
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.clicked.connect(self._show_help)
        bar.addWidget(self.btn_help)
        bar.addSpacing(10)

        self.theme_switch = ThemeSwitch(self.cfg.theme)
        self.theme_switch.modeChanged.connect(self._on_theme_switch)
        bar.addWidget(self.theme_switch)
        bar.addSpacing(10)

        self.switch = ToggleSwitch(self.cfg.enabled)
        self.switch.toggled.connect(self.ctl.set_enabled)
        bar.addWidget(QLabel(tr("Aktywny")))
        bar.addWidget(self.switch)

        card.add_layout(bar)
        return card

    # ----------------------------------------------------------- instrukcja --
    def _show_help(self) -> None:
        HelpDialog(self).exec()

    # ---------------------------------------------------------------- motyw --
    @Slot(str)
    def _on_theme_switch(self, name: str) -> None:
        self._set_theme(name)
        self._touch()

    def _set_theme(self, name: str) -> None:
        self.cfg.theme = T.apply_mode(name)
        self.theme_switch.set_mode(self.cfg.theme)
        # Kolory zapamiętane przy tworzeniu widgetów trzeba nadać jeszcze raz.
        self._restyle()

    # ------------------------------------------------------------ sidebar --
    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(238)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card = Card(tr("Profile"))
        # Kwadracik przy nazwie włącza i wyłącza profil - bez wchodzenia w jego
        # ustawienia i bez osobnego pola pod listą.
        self.profile_list = QListWidget()
        self.profile_list.setToolTip(tr("Kwadracik przy nazwie włącza i wyłącza profil"))
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        self.profile_list.itemChanged.connect(self._on_profile_item_changed)
        card.add(self.profile_list)

        btn_add = QPushButton(tr("Dodaj"))
        btn_dup = QPushButton(tr("Duplikuj"))
        btn_del = QPushButton(tr("Usuń"))
        btn_del.setObjectName("Danger")
        btn_add.clicked.connect(self._add_profile)
        btn_dup.clicked.connect(self._duplicate_profile)
        btn_del.clicked.connect(self._delete_profile)
        card.add_layout(row(btn_add, btn_dup, btn_del))

        card.add(QLabel(tr("Nazwa")))
        self.edit_name = QLineEdit()
        self.edit_name.editingFinished.connect(self._on_profile_meta)
        card.add(self.edit_name)

        card.add(QLabel(tr("Pliki .exe (po przecinku)")))
        self.edit_match = QLineEdit()
        self.edit_match.setPlaceholderText("Fusion360.exe, Inventor.exe, Chrome.exe")
        self.edit_match.editingFinished.connect(self._on_profile_meta)
        card.add(self.edit_match)

        self.chk_default = QCheckBox(tr("Profil domyślny"))
        self.chk_default.toggled.connect(self._on_default_toggled)
        card.add(self.chk_default)

        lay.addWidget(card, 1)
        return panel

    # ----------------------------------------------------- panel urządzenia -
    def _build_device_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(344)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card = Card(tr("Podgląd na żywo"))
        self.view = DeviceView()
        self.view.set_count(self.cfg.button_count)
        card.add(self.view)

        # Legenda pod grafiką: nazwa elementu, jego funkcja i - dla przycisków -
        # zielona albo czerwona kropka mówiąca, czy funkcja jest włączona.
        self.legend: dict[str, QLabel] = {}
        self.legend_dots: dict[int, StatusPill] = {}
        self.legend_box = QGridLayout()
        self.legend_box.setContentsMargins(0, 4, 0, 0)
        self.legend_box.setHorizontalSpacing(10)
        self.legend_box.setVerticalSpacing(3)
        card.add_layout(self.legend_box)
        self._rebuild_legend_rows()

        lay.addWidget(card, 1)
        return panel

    def _rebuild_legend_rows(self) -> None:
        """Buduje wiersze legendy - tyle przycisków, ile ma urządzenie."""
        while self.legend_box.count():
            item = self.legend_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.legend.clear()
        self.legend_dots.clear()

        entries = [(f"btn{i}", tr("Przycisk {index}").format(index=i), i)
                   for i in range(1, self.cfg.button_count + 1)]
        entries += [("move", tr("Ruch myszy"), 0), ("scroll", tr("Scroll"), 0)]
        for r, (key, title, index) in enumerate(entries):
            name = QLabel(title)
            name.setObjectName("Hint")
            name.setMinimumWidth(78)
            value = QLabel("-")
            value.setWordWrap(True)
            self.legend_box.addWidget(name, r, 0)
            self.legend_box.addWidget(value, r, 1)
            self.legend[key] = value
            if index:
                # Ta sama kropka co przy stanie całego urządzenia w pasku górnym.
                dot = StatusPill("", T.OK, dot=9.0)
                dot.setFixedWidth(14)
                dot.setToolTip(tr("Funkcja przycisku włączona / wyłączona"))
                self.legend_box.addWidget(dot, r, 2)
                self.legend_dots[index] = dot
        self.legend_box.setColumnStretch(1, 1)

    # --------------------------------------------------------------- tabs --
    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_buttons(), tr("Przyciski i gesty"))
        self.tabs.addTab(self._tab_navigation(), tr("Nawigacja 3D"))
        self.tabs.addTab(self._tab_device(), tr("Urządzenie"))
        self.tabs.addTab(self._tab_monitor(), tr("Monitor"))
        self.tabs.addTab(self._tab_settings(), tr("Ustawienia"))
        return self.tabs

    def _scroll(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(inner)
        return area

    def _tab_buttons(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        self.card_buttons = Card(tr("Przyciski boczne"))
        grid_host = QWidget()
        self.buttons_grid = QGridLayout(grid_host)
        self.buttons_grid.setContentsMargins(0, 0, 0, 0)
        self.buttons_grid.setSpacing(8)
        self.card_buttons.add(grid_host)
        lay.addWidget(self.card_buttons)

        # Przy sterowaniu wprost z dodatku gesty ciągłe nie mają żadnego wpływu -
        # cała sekcja znika, zamiast stać wyszarzona i mylić.
        self.card_gestures = Card(tr("Gesty ciągłe"))
        for name in P.GESTURES:
            editor = GestureEditor(tr(P.GESTURE_LABELS[name]), HoldPreset())
            editor.changed.connect(self._on_gesture_changed)
            editor.captureChanged.connect(self._on_capture)
            self._gesture_editors[name] = editor
            self.card_gestures.add(editor)
        lay.addWidget(self.card_gestures)
        lay.addStretch(1)
        return self._scroll(host)

    def _tab_navigation(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        gestures = Card(tr("Gesty programu (akcje 'Nawigacja 3D')"))
        # Jedna tabela zamiast trzech osobnych kart: nagłówki kolumn stoją raz,
        # a każdy tryb zajmuje jeden wiersz. Zakładka mieści się przez to na
        # mniejszym ekranie i w pionie, i w poziomie.
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for col, title in enumerate(("", tr("Trzymaj klawisze"), tr("Trzymaj przycisk"),
                                     tr("Sposób"), tr("Oś"))):
            head = QLabel(title)
            head.setObjectName("Hint")
            grid.addWidget(head, 0, col)

        self.nav_rows: dict[str, dict] = {}
        for r, mode in enumerate(P.NAV_MODES, start=1):
            keys_edit = HotkeyEdit(mods_only=True)
            keys_edit.setPlaceholderText(tr("np. Shift"))
            keys_edit.setMinimumWidth(72)
            mouse_box = combo(4)
            mouse_box.addItem(K.mouse_label(""), "")
            for b in K.MOUSE_BUTTONS:
                mouse_box.addItem(K.mouse_label(b), b)
            style_box = combo(8)
            style_box.addItem(tr("Przeciąganie kursorem"), "drag")
            style_box.addItem(tr("Kółko myszy (scroll)"), "wheel")
            axis_box = combo(3)
            axis_box.addItem(tr("Oś Y"), "y")
            axis_box.addItem(tr("Oś X"), "x")

            name = QLabel(tr(P.NAV_LABELS[mode]))
            grid.addWidget(name, r, 0)
            grid.addWidget(keys_edit, r, 1)
            grid.addWidget(mouse_box, r, 2)
            grid.addWidget(style_box, r, 3)
            grid.addWidget(axis_box, r, 4)

            keys_edit.hotkeyChanged.connect(self._on_nav_changed)
            keys_edit.captureChanged.connect(self._on_capture)
            mouse_box.currentIndexChanged.connect(self._on_nav_changed)
            style_box.currentIndexChanged.connect(self._on_nav_changed)
            axis_box.currentIndexChanged.connect(self._on_nav_changed)
            self.nav_rows[mode] = {"keys": keys_edit, "mouse": mouse_box,
                                   "style": style_box, "axis": axis_box}
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 3)
        grid.setColumnStretch(4, 2)
        gestures.add_layout(grid)
        lay.addWidget(gestures)

        axes = Card(tr("Osie X/Y (ustawienia tego profilu)"))

        self.sl_move = SliderRow(tr("Czułość - ruch gałki"), 1.0, 0.05, 6.0)
        axes.add(self.sl_move)
        self.hint_move = hint("")
        axes.add(self.hint_move)

        # Zoom: wartość to wielkość jednego kliknięcia, nie liczba impulsów
        # potrzebnych na kliknięcie. Działa i na scroll, i na kamerę w dodatku.
        self.sl_zoom = SliderRow(tr("Czułość - zoom (pierścień)"), 1.0, 0.1, 5.0, step=0.1)
        axes.add(self.sl_zoom)
        self.hint_zoom = hint("")
        axes.add(self.hint_zoom)

        axes.add(hint(tr(
            "Poniższe dotyczą akcji 'Nawigacja 3D' przypisanych do przycisków bocznych."
        )))
        self.sl_orbit = SliderRow(tr("Czułość - orbita"), 1.0, 0.05, 6.0)
        self.sl_pan = SliderRow(tr("Czułość - przesuwanie"), 1.0, 0.05, 6.0)
        for s in (self.sl_orbit, self.sl_pan):
            axes.add(s)
        for s in (self.sl_move, self.sl_zoom, self.sl_orbit, self.sl_pan):
            s.valueChanged.connect(self._on_axes_changed)

        self.chk_inv_x = QCheckBox(tr("Odwróć X"))
        self.chk_inv_y = QCheckBox(tr("Odwróć Y"))
        self.chk_swap = QCheckBox(tr("Zamień X/Y"))
        self.chk_inv_zoom = QCheckBox(tr("Odwróć zoom"))
        self.chk_inv_zoom.setToolTip(tr(
            "Odwraca kierunek obrotu pierścienia: przybliżanie zamienia się\n"
            "z oddalaniem - w zwykłym scrollu i w zoomie przez dodatek 3D."
        ))
        self.chk_recenter = QCheckBox(tr("Przepinaj gest przy krawędzi"))
        self.chk_center = QCheckBox(tr("Kursor na środek okna przed gestem"))
        self.chk_keep_cursor = QCheckBox(tr("Zostaw kursor w nowym miejscu"))
        self.chk_keep_cursor.setToolTip(tr(
            "Włączone: po ruchu gałką kursor zostaje tam, dokąd dojechał -\n"
            "gałka zachowuje się wtedy jak zwykła mysz.\n"
            "Wyłączone: po geście kursor wraca na pozycję sprzed gestu."
        ))
        for c in (self.chk_inv_x, self.chk_inv_y, self.chk_swap, self.chk_inv_zoom,
                  self.chk_recenter, self.chk_center, self.chk_keep_cursor):
            c.toggled.connect(self._on_axes_changed)
        axes.add_layout(row(self.chk_inv_x, self.chk_inv_y, self.chk_swap, self.chk_inv_zoom))
        # Długie etykiety zostają w osobnych wierszach: dwie kolumny rozpychałyby
        # zakładkę w bok i wracałby poziomy pasek przewijania.
        axes.add(self.chk_recenter)
        axes.add(self.chk_center)
        axes.add(self.chk_keep_cursor)

        # Sterowanie wprost zamyka listę pól - decyduje o tym, czym w ogóle są
        # osie X/Y w tym profilu: kamerą w dodatku czy ruchem kursora.
        self.chk_direct = QCheckBox(tr("Sterowanie wprost (dodatek 3D)"))
        self.chk_direct.setToolTip(tr(
            "Osie idą prosto do dodatku działającego w programie 3D, który sam\n"
            "przestawia kamerę. Kursor w ogóle się nie rusza.\n"
            "Gdy dodatek nie jest podłączony, profil sam wraca do\n"
            "emulacji przeciągania."
        ))
        self.chk_direct.toggled.connect(self._on_profile_meta)

        # Do którego programu idą osie: każdy z nich ma własny dodatek, a most
        # wysyła paczki tylko do dodatku wybranego tutaj.
        self.lbl_addon = QLabel(tr("Dodatek:"))
        self.addon_box = combo(10)
        for key in P.ADDONS:
            self.addon_box.addItem(P.ADDON_LABELS[key], key)
        self.addon_box.setToolTip(tr(
            "Program, którego dodatek dostaje osie przy sterowaniu wprost.\n"
            "Fusion 360: dodatek MAKMOUSE uruchomiony w Fusionie.\n"
            "SolidCraft: Preferencje -> Nawigacja -> Mysz 3D ->\n"
            "\"Nawiguj programem urządzenia na tym komputerze\"."
        ))
        self.addon_box.currentIndexChanged.connect(self._on_profile_meta)
        addon_row = row(self.chk_direct, self.lbl_addon, self.addon_box, spacing=12)
        addon_row.addStretch(1)
        axes.add_layout(addon_row)

        self.lbl_bridge = QLabel(tr("Dodatek 3D: sprawdzanie..."))
        self.lbl_bridge.setWordWrap(True)
        self.lbl_bridge.setObjectName("Hint")
        axes.add(self.lbl_bridge)
        lay.addWidget(axes)
        lay.addStretch(1)
        return self._scroll(host)

    def _tab_device(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(12)

        status = Card(tr("Urządzenie {name}").format(name=dv.TARGET_NAME))
        self.lbl_found = QLabel("-")
        self.lbl_found.setObjectName("Big")
        status.add(self.lbl_found)

        self.device_table = QTableWidget(0, 2)
        self.device_table.setHorizontalHeaderLabels([tr("Nazwa"), tr("Typ urządzenia")])
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.setMinimumHeight(140)
        dh = self.device_table.horizontalHeader()
        dh.setSectionResizeMode(0, QHeaderView.Stretch)
        dh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        status.add(self.device_table)

        btn_refresh = QPushButton(tr("Szukaj ponownie"))
        btn_refresh.setObjectName("Primary")
        btn_refresh.clicked.connect(self.refresh_devices)
        status.add_layout(row(btn_refresh))
        lay.addWidget(status)

        # Tryb odczytu i układ raportu HID są ustalone przez firmware (Multi-axis
        # Controller, raport ID 1) i nie ma po co ich wystawiać - zostają w
        # konfiguracji jako stałe.
        lay.addStretch(1)
        return self._scroll(host)

    def _tab_monitor(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(10)

        pressed = Card(tr("Wciśnięte przyciski"))
        self.lbl_pressed = QLabel("-")
        self.lbl_pressed.setObjectName("Big")
        pressed.add(self.lbl_pressed)
        self.lamps_box = QHBoxLayout()
        self.lamps_box.setSpacing(8)
        pressed.add_layout(self.lamps_box)
        self._rebuild_lamps()
        lay.addWidget(pressed)

        top = Card(tr("Ostatni raport HID / stan osi"))
        self.lbl_hex = QLabel("-")
        self.lbl_hex.setObjectName("Mono")
        self.lbl_hex.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_hex.setWordWrap(True)
        top.add(self.lbl_hex)
        self.lbl_bits = QLabel("")
        self.lbl_bits.setObjectName("Mono")
        self.lbl_bits.setWordWrap(True)
        top.add(self.lbl_bits)
        self.bar_x = AxisBar("X")
        self.bar_y = AxisBar("Y")
        top.add(self.bar_x)
        top.add(self.bar_y)
        lay.addWidget(top)

        logc = Card(tr("Strumień zdarzeń"))
        self.log = QPlainTextEdit()
        self.log.setObjectName("Mono")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(LOG_LIMIT)
        logc.add(self.log)
        btn_clear = QPushButton(tr("Wyczyść"))
        btn_clear.clicked.connect(self.log.clear)
        self.chk_log_axes = QCheckBox(tr("Pokazuj osie i raporty"))
        self.chk_log_axes.setChecked(True)
        logc.add_layout(row(btn_clear, self.chk_log_axes))
        lay.addWidget(logc, 1)
        return page

    def _tab_settings(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        misc = Card(tr("Aplikacja"))

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(tr("Język")))
        self.combo_language = combo(10)
        for code, name in i18n.available():
            self.combo_language.addItem(name, code)
        current = self.combo_language.findData(i18n.language())
        self.combo_language.setCurrentIndex(max(0, current))
        self.combo_language.currentIndexChanged.connect(self._on_language)
        lang_row.addWidget(self.combo_language, 1)
        misc.add_layout(lang_row)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(QLabel(tr("Liczba przycisków bocznych")))
        self.combo_buttons = combo(10)
        for count in P.BUTTON_COUNT_CHOICES:
            self.combo_buttons.addItem(tr("{count} przyciski").format(count=count), count)
        self.combo_buttons.setToolTip(tr(
            "Wersja urządzenia. Przestawia podgląd na żywo i zakładkę\n"
            "'Przyciski i gesty'. Ustawienia ukrytych przycisków zostają zapisane."
        ))
        self.combo_buttons.currentIndexChanged.connect(self._on_button_count)
        buttons_row.addWidget(self.combo_buttons, 1)
        misc.add_layout(buttons_row)

        accent_row = QHBoxLayout()
        accent_row.addWidget(QLabel(tr("Kolor wiodący")))
        self.combo_accent = combo(10)
        for name, code in T.ACCENTS:
            self.combo_accent.addItem(_color_icon(code), tr(name), code)
        self.combo_accent.currentIndexChanged.connect(self._on_accent)
        accent_row.addWidget(self.combo_accent, 1)
        misc.add_layout(accent_row)

        panic_row = QHBoxLayout()
        panic_row.addWidget(QLabel(tr("Skrót awaryjny (włącz/wyłącz MAKMOUSE)")))
        self.edit_panic = HotkeyEdit(self.cfg.panic_hotkey)
        self.edit_panic.hotkeyChanged.connect(self._on_globals)
        self.edit_panic.captureChanged.connect(self._on_capture)
        panic_row.addWidget(self.edit_panic, 1)
        misc.add_layout(panic_row)
        self.chk_min = QCheckBox(tr("Autostart"))
        self.chk_min.toggled.connect(self._on_globals)
        misc.add(self.chk_min)

        btn_export = QPushButton(tr("Eksportuj..."))
        btn_import = QPushButton(tr("Importuj..."))
        btn_reset = QPushButton(tr("Przywróć domyślne"))
        btn_reset.setObjectName("Danger")
        btn_export.clicked.connect(self._export)
        btn_import.clicked.connect(self._import)
        btn_reset.clicked.connect(self._reset)
        misc.add_layout(row(btn_export, btn_import, btn_reset))
        lay.addWidget(misc)

        lay.addWidget(self._build_config_path_card())

        lay.addStretch(1)
        return self._scroll(host)

    def _build_config_path_card(self) -> QWidget:
        card = Card(tr("Plik konfiguracji"))
        card.add(QLabel(tr("Ścieżka pliku konfiguracyjnego")))
        self.edit_cfg_path = QLineEdit()
        self.edit_cfg_path.setReadOnly(True)
        self.edit_cfg_path.setObjectName("Mono")
        card.add(self.edit_cfg_path)

        btn_change = QPushButton(tr("Zmień lokalizację..."))
        btn_change.setObjectName("Primary")
        btn_default = QPushButton(tr("Wróć do domyślnej"))
        btn_open = QPushButton(tr("Otwórz folder"))
        btn_change.clicked.connect(self._change_config_path)
        btn_default.clicked.connect(self._reset_config_path)
        btn_open.clicked.connect(self._open_config_dir)
        card.add_layout(row(btn_change, btn_default, btn_open))

        self.lbl_cfg_default = hint("")
        card.add(self.lbl_cfg_default)
        return card

    # ---------------------------------------------------------------- tray --
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(T.make_icon(), self)
        self.tray.setToolTip(f"{APP_NAME} {__version__}")
        menu = QMenu()
        act_show = QAction(tr("Pokaż okno"), self)
        act_show.triggered.connect(self._restore)
        self.act_enabled = QAction(tr("Aktywny"), self, checkable=True, checked=self.cfg.enabled)
        self.act_enabled.toggled.connect(self.ctl.set_enabled)
        act_quit = QAction(tr("Zakończ"), self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_show)
        menu.addAction(self.act_enabled)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        # Menu kontekstowe żyje tylko tak długo, jak trzyma je Python - bez
        # referencji zostałoby zebrane zaraz po wyjściu z tej metody.
        self._tray_menu = menu
        self.tray.activated.connect(
            lambda reason: self._restore() if reason == QSystemTrayIcon.Trigger else None
        )
        self.tray.show()

    # ============================================================ sygnały ==
    def _connect_controller(self) -> None:
        self.ctl.sig_event.connect(self._on_input_event)
        self.ctl.sig_profile.connect(self._on_profile_active)
        self.ctl.sig_devices.connect(self.refresh_devices)
        self.ctl.sig_device_state.connect(self._on_device_state)
        self.ctl.sig_error.connect(self._on_error)
        self.ctl.sig_enabled.connect(self._on_enabled)
        self.ctl.sig_action.connect(self.status_action.setText)

    def _disconnect_controller(self) -> None:
        """Odpina okno od kontrolera - używane przy przebudowie po zmianie języka."""
        for signal, slot in (
            (self.ctl.sig_event, self._on_input_event),
            (self.ctl.sig_profile, self._on_profile_active),
            (self.ctl.sig_devices, self.refresh_devices),
            (self.ctl.sig_device_state, self._on_device_state),
            (self.ctl.sig_error, self._on_error),
            (self.ctl.sig_enabled, self._on_enabled),
            (self.ctl.sig_action, self.status_action.setText),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):  # pragma: no cover - już odpięte
                pass

    @Slot(bool)
    def _on_enabled(self, enabled: bool) -> None:
        self.switch.setChecked(enabled)
        self.act_enabled.blockSignals(True)
        self.act_enabled.setChecked(enabled)
        self.act_enabled.blockSignals(False)
        self.tray.setIcon(T.make_icon(active=enabled))
        self.view.set_active(enabled)
        self._refresh_device_status()
        self._save_timer.start()

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self.status_action.setText(tr("Błąd silnika: {message}").format(message=message))
        self._log(tr("[BŁĄD] {message}").format(message=message))

    @Slot(str, str)
    def _on_profile_active(self, name: str, exe: str) -> None:
        # Pasek górny nie pokazuje już profilu - zmianę widać w Monitorze.
        if name != self._active_profile_name:
            self._active_profile_name = name
            self._log(tr("profil: {name}").format(name=name) + (f"  ({exe})" if exe else ""))

    @Slot(bool)
    def _on_device_state(self, _present: bool) -> None:
        self._refresh_device_status()
        self._fill_device_table()

    def _refresh_device_status(self) -> None:
        """Sam kolor kropki mówi, czy MAKMOUSE działa."""
        live = self.ctl.device_present and self.cfg.enabled
        color = T.OK if live else T.BAD
        state = tr("Aktywny") if live else tr("Nieaktywny")
        self.pill_device.set_state(dv.TARGET_NAME, color)
        self.pill_device.setToolTip(state)
        self.lbl_found.setText(f"{dv.TARGET_NAME} - {state}")
        self.lbl_found.setStyleSheet(f"color: {color};")

    @Slot(object)
    def _on_input_event(self, ev: InputEvent) -> None:
        if ev.kind == "button":
            self.view.set_button(ev.index, ev.pressed)
            self._set_pressed(ev.index, ev.pressed)
            if ev.pressed:
                self._log(tr("przycisk boczny {index} DÓŁ").format(index=ev.index)
                          + (tr("  [zablokowany]") if ev.suppressed else ""))
            else:
                self._log(tr("przycisk boczny {index} GÓRA").format(index=ev.index))
        elif ev.kind == "axis":
            norm = self._axis_norm()
            self.bar_x.set_value(ev.dx / norm)
            self.bar_y.set_value(ev.dy / norm)
            self.view.set_axis(ev.dx / norm, ev.dy / norm)
            if self.chk_log_axes.isChecked():
                self._log(tr("ruch myszy  X={dx:+.3f}  Y={dy:+.3f}").format(dx=ev.dx, dy=ev.dy))
        elif ev.kind == "report":
            self._on_report(ev.raw)
        elif ev.kind == "wheel":
            self.view.pulse_wheel(ev.dx)
            self._log(tr("scroll {value:+.2f}").format(value=ev.dx))
        elif ev.kind == "key":
            pattern = "klawisz VK 0x{vk:02X} DÓŁ" if ev.pressed else "klawisz VK 0x{vk:02X} GÓRA"
            self._log(tr(pattern).format(vk=ev.index))

    def _axis_norm(self) -> float:
        """Skala podglądu osi - pełne wychylenie ma dawać pełny pasek."""
        spec = self.cfg.device.hid_layout.axis_x
        if spec is None:
            return 127.0
        auto = (1 << (8 * spec.size - 1)) - 1 if spec.signed else (1 << (8 * spec.size)) - 1
        return float(spec.full_scale or auto)

    def _on_report(self, data: bytes) -> None:
        if not data:
            return
        prev, self._last_report = self._last_report, data
        self.lbl_hex.setText(" ".join(f"{b:02X}" for b in data))
        if prev and len(prev) == len(data):
            diff = [i for i, (a, b) in enumerate(zip(prev, data)) if a != b]
            self.lbl_bits.setText(
                tr("zmienione bajty: ") + (", ".join(map(str, diff)) if diff else "-")
            )
        if self.chk_log_axes.isChecked():
            self._log(tr("raport ") + " ".join(f"{b:02X}" for b in data))

    def _log(self, text: str) -> None:
        self.log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def _set_pressed(self, index: int, pressed: bool) -> None:
        """Podgląd wciśniętych przycisków w zakładce Monitor."""
        lamp = self._lamps.get(index)
        if lamp is None:
            return
        lamp.set_pressed(pressed)
        names = [tr(P.DEFAULT_BUTTON_NAMES[i])
                 for i, wdg in sorted(self._lamps.items()) if wdg.is_pressed and i in P.DEFAULT_BUTTON_NAMES]
        self.lbl_pressed.setText(", ".join(names) if names else "-")

    @Slot(bool)
    def _on_capture(self, capturing: bool) -> None:
        """Licznik pól nagrywających skrót - trzymany dla porządku w UI.

        Silnik nie zakłada już hooka klawiatury, więc nie ma czego zwalniać.
        """
        self._captures = max(0, self._captures + (1 if capturing else -1))

    # =========================================================== profile ===
    @property
    def profile(self) -> Profile:
        idx = self.profile_list.currentRow()
        if 0 <= idx < len(self.cfg.profiles):
            return self.cfg.profiles[idx]
        return self.cfg.active_profile("")

    def load_profile_list(self, select: int = 0) -> None:
        self._loading = True
        self.profile_list.clear()
        for prof in self.cfg.profiles:
            label = (tr("{name}  (domyślny)").format(name=prof.name)
                     if prof.is_default else prof.name)
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if prof.enabled else Qt.Unchecked)
            self._paint_profile_item(item, prof.enabled)
            self.profile_list.addItem(item)
        self._loading = False
        self.profile_list.setCurrentRow(min(select, len(self.cfg.profiles) - 1))

    @staticmethod
    def _paint_profile_item(item: QListWidgetItem, enabled: bool) -> None:
        """Wyłączony profil jest wyszarzony - widać to bez czytania kwadracika."""
        item.setData(Qt.ForegroundRole, None if enabled else Qt.gray)

    @Slot(QListWidgetItem)
    def _on_profile_item_changed(self, item: QListWidgetItem) -> None:
        """Kwadracik przy nazwie profilu - włącznik całego profilu."""
        if self._loading:
            return
        index = self.profile_list.row(item)
        if not (0 <= index < len(self.cfg.profiles)):
            return
        prof = self.cfg.profiles[index]
        enabled = item.checkState() == Qt.Checked
        if enabled == prof.enabled:
            return
        prof.enabled = enabled
        self._loading = True  # zmiana koloru wywołałaby ten slot jeszcze raz
        try:
            self._paint_profile_item(item, enabled)
        finally:
            self._loading = False
        self._touch()

    @Slot(int)
    def _on_profile_selected(self, _index: int) -> None:
        if self._loading:
            return
        self._load_profile_into_ui()

    def _load_profile_into_ui(self) -> None:
        prof = self.profile
        self._loading = True
        try:
            self.edit_name.setText(prof.name)
            self.edit_match.setText(", ".join(prof.match))
            self.chk_default.setChecked(prof.is_default)
            self.chk_direct.setChecked(prof.direct)
            self.addon_box.setCurrentIndex(max(0, self.addon_box.findData(prof.addon)))
            self._load_axes_into_ui(prof)
            self._rebuild_button_cards(prof)
            for mode, widgets in self.nav_rows.items():
                preset = prof.nav.get(mode, NavPreset())
                widgets["keys"].setText(preset.keys)
                widgets["mouse"].setCurrentIndex(max(0, widgets["mouse"].findData(preset.button)))
                widgets["style"].setCurrentIndex(max(0, widgets["style"].findData(preset.style)))
                widgets["axis"].setCurrentIndex(max(0, widgets["axis"].findData(preset.wheel_axis)))
            for name, editor in self._gesture_editors.items():
                editor.load(prof.gestures.setdefault(name, HoldPreset()))
        finally:
            self._loading = False
        self._sync_nav_enabled()
        self._sync_direct_sections()
        self._update_bridge_label()
        self._refresh_legend()

    def _load_axes_into_ui(self, prof: Profile) -> None:
        """Osie należą do profilu - wczytujemy je razem z resztą jego ustawień."""
        a = prof.axes
        self.sl_move.setValue(a.sens_move)
        self.sl_zoom.setValue(a.sens_zoom)
        self.sl_orbit.setValue(a.sens_orbit)
        self.sl_pan.setValue(a.sens_pan)
        self.chk_inv_x.setChecked(a.invert_x)
        self.chk_inv_y.setChecked(a.invert_y)
        self.chk_swap.setChecked(a.swap_xy)
        self.chk_inv_zoom.setChecked(a.invert_zoom)
        self.chk_recenter.setChecked(a.recenter)
        self.chk_center.setChecked(a.center_on_start)
        self.chk_keep_cursor.setChecked(a.keep_cursor)

    def _sync_direct_sections(self) -> None:
        """Sterowanie wprost wyklucza gesty ciągłe - sekcja po prostu znika.
        Wybór dodatku ma sens tylko przy sterowaniu wprost."""
        direct = self.chk_direct.isChecked()
        self.card_gestures.setVisible(not direct)
        self.lbl_addon.setEnabled(direct)
        self.addon_box.setEnabled(direct)

    def _sync_nav_enabled(self) -> None:
        """W trybie 'kółko myszy' trzymane klawisze i przycisk nie mają zastosowania."""
        for widgets in self.nav_rows.values():
            wheel = (widgets["style"].currentData() or "drag") == "wheel"
            widgets["keys"].setEnabled(not wheel)
            widgets["mouse"].setEnabled(not wheel)
            widgets["axis"].setEnabled(wheel)

    def _refresh_legend(self) -> None:
        """Legenda pod grafiką: co robi każdy element i czy jest włączony."""
        prof = self.profile
        labels = {}
        for i in range(1, self.cfg.button_count + 1):
            binding = prof.buttons.get(i, Binding())
            text = binding.describe()
            labels[i] = text
            self.legend[f"btn{i}"].setText(text)
            # Stan funkcji pokazuje kropka - zielona jak działa, czerwona jak nie.
            dot = self.legend_dots.get(i)
            if dot is not None:
                dot.set_state("", T.OK if binding.enabled else T.BAD)
                dot.setToolTip(tr("Funkcja przycisku włączona") if binding.enabled
                               else tr("Funkcja przycisku wyłączona"))
            lamp = self._lamps.get(i)
            if lamp is not None:
                lamp.set_action(text)
        for name in P.GESTURES:
            preset = prof.gestures.get(name, HoldPreset())
            base = tr("ruch myszy") if name == "move" else tr("scroll")
            self.legend[name].setText(
                base if not preset.active() else f"{base} + {preset.describe()}"
            )
        if prof.direct:
            # Przy sterowaniu wprost gałka i pierścień idą do dodatku, a nie do
            # emulacji myszy - gesty ciągłe nie mają wtedy nic do rzeczy.
            self.legend["move"].setText(tr("dodatek 3D: kamera"))
            self.legend["scroll"].setText(tr("dodatek 3D: zoom"))
        self.view.set_labels(labels)

    def _rebuild_lamps(self) -> None:
        """Lampki w Monitorze - tyle, ile przycisków ma urządzenie."""
        while self.lamps_box.count():
            item = self.lamps_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._lamps.clear()
        for i in range(1, self.cfg.button_count + 1):
            # Krótka nazwa: przy sześciu lampkach w rzędzie "Przycisk boczny 6"
            # nie mieści się w kafelku.
            lamp = ButtonLamp(tr("Przycisk {index}").format(index=i))
            self._lamps[i] = lamp
            self.lamps_box.addWidget(lamp)

    def _rebuild_button_cards(self, prof: Profile) -> None:
        while self.buttons_grid.count():
            item = self.buttons_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._button_cards.clear()

        for i in range(1, self.cfg.button_count + 1):
            binding = prof.buttons.setdefault(i, Binding())
            # Akcje widoku idą mostem do dodatku, więc pokazujemy je tylko w
            # profilu, który rzeczywiście z niego korzysta.
            card = ButtonCard(i, tr(P.DEFAULT_BUTTON_NAMES[i]), binding, allow_direct=prof.direct)
            card.changed.connect(self._on_binding_changed)
            card.captureChanged.connect(self._on_capture)
            self._button_cards[i] = card
            self.buttons_grid.addWidget(card, (i - 1) // 2, (i - 1) % 2)
        self.buttons_grid.setColumnStretch(0, 1)
        self.buttons_grid.setColumnStretch(1, 1)

    def _on_binding_changed(self) -> None:
        if self._loading:
            return
        self._refresh_legend()
        self._touch()

    def _on_gesture_changed(self) -> None:
        if self._loading:
            return
        self._refresh_legend()
        self._touch()

    def _on_profile_meta(self) -> None:
        if self._loading:
            return
        prof = self.profile
        prof.name = self.edit_name.text().strip() or prof.name
        prof.match = [m.strip() for m in self.edit_match.text().split(",") if m.strip()]
        direct = self.chk_direct.isChecked()
        if direct != prof.direct:
            prof.direct = direct
            self._rebuild_button_cards(prof)  # zmienia się lista dostępnych akcji
            self._sync_direct_sections()
            self._refresh_legend()
        addon = self.addon_box.currentData() or P.DEFAULT_ADDON
        if addon != prof.addon:
            prof.addon = addon
            self._refresh_legend()
        current = self.profile_list.currentRow()
        self.load_profile_list(current)
        self._update_bridge_label()
        self._refresh_move_hint()
        self._touch()

    def _update_bridge_label(self) -> None:
        """Pokazuje, czy dodatek 3D naprawdę rozmawia z aplikacją.

        Bez tego nie da się odróżnić 'sterowanie wprost włączone' od 'sterowanie
        wprost działa' - a to właśnie ta różnica decyduje, czy kursor się rusza.
        """
        clients = self.ctl.bridge.client_count
        addon = self.addon_box.currentData() or P.DEFAULT_ADDON
        name = P.ADDON_LABELS.get(addon, addon)
        if not self.cfg.bridge_enabled:
            self.lbl_bridge.setText(tr("Most wyłączony w konfiguracji."))
        elif not self.chk_direct.isChecked():
            self.lbl_bridge.setText(
                tr("Ten profil używa emulacji przeciągania. Dodatków podłączonych: {count}.")
                .format(count=clients)
            )
        elif self.ctl.bridge.clients_for(addon):
            self.lbl_bridge.setText(
                tr("Dodatek podłączony: {name}").format(name=name)
            )
        elif addon == P.ADDON_SOLIDCRAFT:
            self.lbl_bridge.setText(tr(
                "Brak połączenia z SolidCraft. W SolidCrafcie włącz: Preferencje -> "
                "Nawigacja -> Mysz 3D -> \"Nawiguj programem urządzenia na tym komputerze\" "
                "(port {port})."
            ).format(port=self.cfg.bridge_port))
        else:
            self.lbl_bridge.setText(tr("Brak dodatku: {name}").format(name=name))

    @Slot(bool)
    def _on_default_toggled(self, value: bool) -> None:
        if self._loading:
            return
        prof = self.profile
        if value:
            for p in self.cfg.profiles:
                p.is_default = p is prof
        else:
            prof.is_default = False
            if not any(p.is_default for p in self.cfg.profiles):
                self.cfg.profiles[-1].is_default = True
        current = self.profile_list.currentRow()
        self.load_profile_list(current)
        self._load_profile_into_ui()
        self._touch()

    def _add_profile(self) -> None:
        self.cfg.profiles.insert(0, Profile(name=tr("Nowy profil")))
        self.load_profile_list(0)
        self._touch()

    def _duplicate_profile(self) -> None:
        src = self.profile
        clone = Profile.from_dict(src.to_dict())
        clone.name = tr("{name} (kopia)").format(name=src.name)
        clone.is_default = False
        self.cfg.profiles.insert(self.profile_list.currentRow() + 1, clone)
        self.load_profile_list(self.profile_list.currentRow() + 1)
        self._touch()

    def _delete_profile(self) -> None:
        if len(self.cfg.profiles) <= 1:
            QMessageBox.information(self, "MAKMOUSE", tr("Musi zostać przynajmniej jeden profil."))
            return
        idx = self.profile_list.currentRow()
        removed = self.cfg.profiles.pop(idx)
        if removed.is_default and self.cfg.profiles:
            self.cfg.profiles[-1].is_default = True
        self.load_profile_list(max(0, idx - 1))
        self._touch()

    # ========================================================= nawigacja ===
    def _on_nav_changed(self, *_args) -> None:
        if self._loading:
            return
        prof = self.profile
        for mode, widgets in self.nav_rows.items():
            preset = prof.nav.setdefault(mode, NavPreset())
            preset.keys = widgets["keys"].text()
            preset.button = widgets["mouse"].currentData() or ""
            preset.style = widgets["style"].currentData() or "drag"
            preset.wheel_axis = widgets["axis"].currentData() or "y"
        self._sync_nav_enabled()
        self._touch()

    def _on_axes_changed(self, *_args) -> None:
        if self._loading:
            return
        a = self.profile.axes
        a.sens_move = self.sl_move.value()
        a.sens_zoom = self.sl_zoom.value()
        a.sens_orbit = self.sl_orbit.value()
        a.sens_pan = self.sl_pan.value()
        a.invert_x = self.chk_inv_x.isChecked()
        a.invert_y = self.chk_inv_y.isChecked()
        a.swap_xy = self.chk_swap.isChecked()
        a.invert_zoom = self.chk_inv_zoom.isChecked()
        a.recenter = self.chk_recenter.isChecked()
        a.center_on_start = self.chk_center.isChecked()
        a.keep_cursor = self.chk_keep_cursor.isChecked()
        self._refresh_move_hint()
        self._touch()

    def _refresh_move_hint(self) -> None:
        prof = self.profile
        if prof.direct and self.ctl.bridge.clients_for(prof.addon):
            self.hint_move.setText(tr(
                "Działa przez dodatek 3D: mnożnik przyrostów osi wysyłanych do programu."
            ))
        else:
            self.hint_move.setText(tr(
                "Działa przez emulację przeciągania: mnożnik ruchu kursora w trakcie gestu."
            ))
        self.hint_zoom.setText(tr(
            "Skok jednego kliknięcia zoomu: 1.00 = zwykły klik kółka, "
            "mniej = drobniejsze przybliżanie i mniej wierszy przy przewijaniu, "
            "więcej = większy skok. Liczba kliknięć na obrót pierścienia (20) "
            "zostaje bez zmian."
        ))

    # ========================================================== urządzenie =
    @Slot()
    def refresh_devices(self) -> None:
        self.ctl.refresh_devices()

    def _fill_device_table(self) -> None:
        self.device_table.setRowCount(0)
        for i, dev in enumerate(self.ctl.found_devices):
            self.device_table.insertRow(i)
            for c, text in enumerate((dev.display_name() or dv.TARGET_NAME, dev.kind_name)):
                self.device_table.setItem(i, c, QTableWidgetItem(text))

    # ========================================================== ustawienia =
    @Slot(int)
    def _on_language(self, _index: int) -> None:
        """Zmiana języka: zapisz wybór i poproś o przebudowę okna.

        Tłumaczenia trafiają do widgetów w chwili ich tworzenia, więc jedynym
        sposobem na kompletną zmianę języka jest zbudowanie okna od zera.
        """
        if self._loading:
            return
        code = self.combo_language.currentData() or i18n.DEFAULT_LANGUAGE
        if code == self.cfg.language:
            return
        self.cfg.language = i18n.set_language(code)
        self._save_now()
        self.languageChanged.emit(self.cfg.language)

    def _on_globals(self, *_args) -> None:
        """Ustawienia globalne (nie związane z profilem)."""
        if self._loading:
            return
        self.cfg.panic_hotkey = self.edit_panic.text().strip() or self.cfg.panic_hotkey
        self.cfg.start_minimized = self.chk_min.isChecked()
        self._touch()

    def _sync_globals(self) -> None:
        """Wpisuje konfigurację do kontrolek globalnych (odwrotność _on_globals).

        Osie tu nie występują - od 1.3.2 należą do profilu (`_load_axes_into_ui`).
        """
        self._loading = True
        try:
            self.edit_panic.setText(self.cfg.panic_hotkey)
            self.chk_min.setChecked(self.cfg.start_minimized)
            self.combo_language.setCurrentIndex(
                max(0, self.combo_language.findData(self.cfg.language))
            )
            self.combo_buttons.setCurrentIndex(
                max(0, self.combo_buttons.findData(self.cfg.button_count))
            )
            self.combo_accent.setCurrentIndex(
                max(0, self.combo_accent.findData(self.cfg.accent))
            )
        finally:
            self._loading = False
        self._refresh_move_hint()
        self._sync_config_path()

    @Slot(int)
    def _on_button_count(self, _index: int) -> None:
        """Wersja urządzenia: 3 albo 6 przycisków bocznych."""
        if self._loading:
            return
        count = int(self.combo_buttons.currentData() or P.DEFAULT_BUTTON_COUNT)
        if count == self.cfg.button_count:
            return
        self.cfg.button_count = count
        self.view.set_count(count)
        self._rebuild_legend_rows()
        self._rebuild_lamps()
        self._rebuild_button_cards(self.profile)
        self._refresh_legend()
        self._touch()

    @Slot(int)
    def _on_accent(self, _index: int) -> None:
        """Kolor wiodący całej aplikacji."""
        if self._loading:
            return
        code = str(self.combo_accent.currentData() or P.DEFAULT_ACCENT)
        if code == self.cfg.accent:
            return
        self.cfg.accent = T.apply_accent(code)
        self._restyle()
        self._touch()

    def _restyle(self) -> None:
        """Nadaje aplikacji nowy arkusz stylów i odświeża to, co trzyma kolory."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(T.stylesheet())
            app.setWindowIcon(T.make_icon())
        self.setWindowIcon(T.make_icon())
        self.tray.setIcon(T.make_icon(active=self.cfg.enabled))
        self._refresh_device_status()
        self._refresh_legend()
        for card in self._button_cards.values():
            card.repaint_dot()
        self.view.update()
        self.update()

    def _sync_config_path(self) -> None:
        path = P.config_path()
        self.edit_cfg_path.setText(str(path))
        self.status_path.setText(str(path))
        self.lbl_cfg_default.setText(
            tr("To jest lokalizacja domyślna.")
            if path == P.default_config_path()
            else tr("Lokalizacja domyślna: {path}").format(path=P.default_config_path())
        )

    def _change_config_path(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, tr("Wybierz plik konfiguracji"), str(P.config_path()), "JSON (*.json)"
        )
        if not name:
            return
        err = P.set_config_path(Path(name)) or P.save(self.cfg, Path(name))
        self._sync_config_path()
        self.status_action.setText(
            err or tr("Konfiguracja zapisywana w {path}").format(path=name)
        )

    def _reset_config_path(self) -> None:
        err = P.set_config_path(None) or P.save(self.cfg)
        self._sync_config_path()
        self.status_action.setText(err or tr("Wrócono do lokalizacji domyślnej"))

    def _open_config_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(P.config_path().parent)))

    def _export(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, tr("Eksportuj konfigurację"), "makmouse-config.json", "JSON (*.json)"
        )
        if not name:
            return
        err = P.save(self.cfg, Path(name))
        self.status_action.setText(err or tr("Wyeksportowano do {path}").format(path=name))

    def _import(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, tr("Importuj konfigurację"), "", "JSON (*.json)"
        )
        if not name:
            return
        cfg, err = P.load(Path(name))
        if err:
            self.status_action.setText(err)
            return
        self._adopt(cfg, tr("Zaimportowano z {path}").format(path=name))

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self, "MAKMOUSE",
            tr("Przywrócić ustawienia domyślne? Bieżąca konfiguracja zostanie nadpisana.")
        )
        if answer != QMessageBox.Yes:
            return
        self._adopt(P.default_config(), tr("Przywrócono ustawienia domyślne"))

    def _adopt(self, cfg: P.Config, note: str) -> None:
        """Podmienia całą konfigurację i przebudowuje UI."""
        previous_language = self.cfg.language
        self.cfg = cfg
        T.apply_accent(cfg.accent)
        self.view.set_count(cfg.button_count)
        self._rebuild_legend_rows()
        self._rebuild_lamps()
        self._set_theme(cfg.theme)
        self.ctl.apply(cfg)
        self.load_profile_list()
        self._sync_globals()
        self._save_timer.start()
        self.status_action.setText(note)
        if cfg.language != previous_language:
            # Wczytana konfiguracja może nieść inny język - okno musi wstać od nowa.
            i18n.set_language(cfg.language)
            self.languageChanged.emit(cfg.language)

    # ============================================================== zapis ==
    def _touch(self) -> None:
        """Konfiguracja się zmieniła - przelicz silnik i zaplanuj zapis."""
        self.ctl.apply(self.cfg)
        self._save_timer.start()

    def _save_now(self) -> None:
        err = P.save(self.cfg)
        self.status_action.setText(err or tr("Zapisano konfigurację"))

    # ============================================================== okno ===
    def _restore(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._save_now()
        self.ctl.stop()
        self.tray.hide()
        QGuiApplication.quit()

    def detach(self) -> None:
        """Przygotowuje okno do skasowania (przebudowa po zmianie języka).

        Zdejmuje ikonę z zasobnika i odpina sygnały kontrolera, żeby stare okno
        nie rysowało zdarzeń w tle i nie zostawiało drugiej ikony w tacce.
        """
        self._detached = True
        self._save_timer.stop()
        self._bridge_timer.stop()
        self._disconnect_controller()
        self.tray.hide()

    def closeEvent(self, event) -> None:
        if self._detached:
            event.accept()
            return
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "MAKMOUSE", tr("Działa w tle. Kliknij ikonę, żeby wrócić."),
                QSystemTrayIcon.Information, 2500
            )
        else:  # pragma: no cover
            self._quit()
            event.accept()
