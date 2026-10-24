"""Własne kontrolki interfejsu - klocki, z których zbudowane jest okno główne.

ZA CO ODPOWIADA
    * wygląd i zachowanie powtarzalnych elementów okna (karty, przełączniki,
      suwaki, kropki stanu, lampki przycisków, paski osi),
    * pole "kliknij i naciśnij skrót" (nagrywanie skrótów klawiszowych),
    * edytor akcji przycisku bocznego i edytor gestu ciągłego.
    Kontrolki zmieniają obiekty konfiguracji (Binding, HoldPreset) bezpośrednio
    i sygnałem `changed` informują okno, że trzeba zapisać.

NAJWAŻNIEJSZE ELEMENTY
    Card .............. panel z tytułem (każda sekcja w oknie)
    ButtonCard ........ kafel jednego przycisku bocznego + kwadracik wł./wył. w rogu
    BindingEditor ..... wybór typu akcji i jej parametrów (wnętrze ButtonCard)
    GestureEditor ..... co trzymać podczas ruchu myszy / scrolla (Gesty ciągłe)
    HotkeyEdit ........ pole nagrywające skrót, np. "Ctrl+Shift+E"
    SliderRow ......... etykieta + suwak + wartość (czułości)
    ToggleSwitch, ThemeSwitch  przełącznik "Aktywny" i przełącznik motywu
    StatusPill ........ kolorowa kropka stanu (urządzenie, legenda przycisków)
    ButtonLamp, AxisBar  lampka przycisku i pasek osi w zakładce Monitor
    combo(), hint(), row()  małe pomocnicze do budowy formularzy

POWIĄZANIA
    używa: theme.py (kolory), profiles.py (Binding i listy akcji), keys.py
    używany przez: main_window.py
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import keys as K
from ..i18n import tr
from ..profiles import (
    ACTION_LABELS,
    ACTION_TYPES,
    DIRECT_ONLY_TYPES,
    NAV_LABELS,
    NAV_MODES,
    VIEW_ACTIONS,
    VIEW_LABELS,
    Binding,
)
from . import theme as T


# --------------------------------------------------------------------------- #
class Card(QFrame):
    """Panel z tytułem i pionową zawartością."""

    def __init__(self, title: str = "", parent: QWidget | None = None, flat: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("CardFlat" if flat else "Card")
        self._outer = QVBoxLayout(self)
        # Ciasne marginesy: cała zawartość zakładek ma się mieścić także na
        # mniejszym ekranie, bez przewijania i bez zmiany skali Windows.
        self._outer.setContentsMargins(11, 8, 11, 9)
        self._outer.setSpacing(6)
        if title:
            lbl = QLabel(title.upper())
            lbl.setObjectName("CardTitle")
            self._outer.addWidget(lbl)
        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        self._outer.addLayout(self.body)

    def add(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def combo(chars: int = 9) -> QComboBox:
    """Lista rozwijana, która nie rozpycha okna do najdłuższej pozycji.

    Domyślna podpowiedź rozmiaru QComboBox to szerokość najdłuższego wpisu -
    przy kilku listach w rzędzie wymusza poziomy pasek przewijania na mniejszym
    ekranie. Pełny tekst i tak widać po rozwinięciu.
    """
    box = QComboBox()
    box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(chars)
    return box


def row(*widgets: QWidget, spacing: int = 8, stretch_last: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for i, wdg in enumerate(widgets):
        lay.addWidget(wdg, 1 if (stretch_last and i == len(widgets) - 1) else 0)
    return lay


# --------------------------------------------------------------------------- #
class ToggleSwitch(QWidget):
    """Przełącznik wł/wył rysowany ręcznie."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(46, 24)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        value = bool(value)
        if value != self._checked:
            self._checked = value
            self.update()

    def mousePressEvent(self, event) -> None:
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor(T.ACCENT) if self._checked else QColor(T.TOGGLE_OFF)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 2, 46, 20), 10, 10)
        p.setBrush(QColor("#FFFFFF"))
        x = 26.0 if self._checked else 4.0
        p.drawEllipse(QRectF(x, 4, 16, 16))


class StatusPill(QLabel):
    """Kropka + tekst, np. 'Urządzenie podłączone'."""

    def __init__(self, text: str = "", color: str = T.TEXT_DIM, parent: QWidget | None = None,
                 dot: float = 8.0) -> None:
        super().__init__(parent)
        self._color = color
        self._dot = dot
        self.setText(text)
        self.setContentsMargins(int(dot + 10), 0, 0, 0)

    def set_state(self, text: str, color: str) -> None:
        self._color = color
        self.setText(text)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        d = self._dot
        if d >= 12:  # większa kropka dostaje delikatną poświatę
            halo = QColor(self._color)
            halo.setAlpha(60)
            p.setBrush(halo)
            p.drawEllipse(QRectF(-1, self.height() / 2 - d / 2 - 3, d + 6, d + 6))
        p.setBrush(QColor(self._color))
        p.drawEllipse(QRectF(2, self.height() / 2 - d / 2, d, d))
        p.end()
        super().paintEvent(event)


class ThemeSwitch(QWidget):
    """Dwupozycyjny przełącznik motywu: słońce = jasny, księżyc = ciemny."""

    modeChanged = Signal(str)

    def __init__(self, mode: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "light" if mode == "light" else "dark"
        self.setFixedSize(74, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Motyw jasny / ciemny"))

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        mode = "light" if mode == "light" else "dark"
        if mode != self._mode:
            self._mode = mode
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._mode = "light" if self._mode == "dark" else "dark"
        self.update()
        self.modeChanged.emit(self._mode)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        light = self._mode == "light"

        p.setPen(QPen(QColor(T.BORDER), 1))
        p.setBrush(QColor(T.FIELD))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # Suwak stoi po stronie wybranego motywu.
        cx = r if light else w - r
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.ACCENT))
        p.drawEllipse(QPointF(cx, h / 2), r - 3, r - 3)

        on, off = QColor("#FFFFFF"), QColor(T.TEXT_DIM)
        self._sun(p, QPointF(r, h / 2), r * 0.52, on if light else off)
        self._moon(p, QPointF(w - r, h / 2), r * 0.52, off if light else on)

    @staticmethod
    def _sun(p: QPainter, c: QPointF, r: float, color: QColor) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(c, r * 0.52, r * 0.52)
        p.setPen(QPen(color, max(1.2, r * 0.24), Qt.SolidLine, Qt.RoundCap))
        for i in range(8):
            a = math.pi * i / 4
            p.drawLine(
                QPointF(c.x() + math.cos(a) * r * 0.82, c.y() + math.sin(a) * r * 0.82),
                QPointF(c.x() + math.cos(a) * r * 1.15, c.y() + math.sin(a) * r * 1.15),
            )

    @staticmethod
    def _moon(p: QPainter, c: QPointF, r: float, color: QColor) -> None:
        full = QPainterPath()
        full.addEllipse(c, r, r)
        bite = QPainterPath()
        bite.addEllipse(QPointF(c.x() + r * 0.58, c.y() - r * 0.30), r * 0.92, r * 0.92)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(full.subtracted(bite))


class AxisBar(QWidget):
    """Dwukierunkowy pasek wychylenia osi (-1 .. 1)."""

    def __init__(self, label: str = "X", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._label = label
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: float) -> None:
        value = max(-1.0, min(1.0, value))
        if abs(value - self._value) > 0.002:
            self._value = value
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        track = QRectF(24, h / 2 - 5.5, w - 28, 11)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.AXIS_TRACK))
        p.drawRoundedRect(track, 5.5, 5.5)

        p.setPen(QPen(QColor(T.TEXT_DIM)))
        p.drawText(QRectF(0, 0, 20, h), Qt.AlignVCenter | Qt.AlignLeft, self._label)

        mid = track.center().x()
        p.setPen(QPen(QColor(T.AXIS_MID), 1))
        p.drawLine(QPointF(mid, track.top() - 3), QPointF(mid, track.bottom() + 3))

        span = (track.width() / 2) * self._value
        if abs(span) >= 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.ACCENT))
            rect = QRectF(min(mid, mid + span), track.top(), abs(span), track.height())
            p.drawRoundedRect(rect, 5.5, 5.5)


class ButtonLamp(QWidget):
    """Kafelek jednego przycisku bocznego - zapala się na czas wciśnięcia."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._action = ""
        self._pressed = False
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def is_pressed(self) -> bool:
        return self._pressed

    def set_action(self, text: str) -> None:
        if text != self._action:
            self._action = text
            self.update()

    def set_pressed(self, pressed: bool) -> None:
        if pressed != self._pressed:
            self._pressed = pressed
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(1, 1, self.width() - 2, self.height() - 2)

        fill = QColor(T.ACCENT) if self._pressed else QColor(T.FIELD)
        border = QColor(T.ACCENT_SOFT if self._pressed else T.BORDER)
        p.setBrush(fill)
        p.setPen(QPen(border, 1.4))
        p.drawRoundedRect(box, 8, 8)

        font = p.font()
        font.setBold(self._pressed)
        p.setFont(font)
        p.setPen(QPen(QColor("#FFFFFF" if self._pressed else T.TEXT)))
        p.drawText(box.adjusted(10, 5, -10, -box.height() / 2), Qt.AlignVCenter | Qt.AlignLeft, self._name)

        font.setBold(False)
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1))
        p.setFont(font)
        p.setPen(QPen(QColor("#E8F2FF" if self._pressed else T.TEXT_DIM)))
        p.drawText(box.adjusted(10, box.height() / 2 - 5, -10, -5),
                   Qt.AlignVCenter | Qt.AlignLeft, self._action or "-")


class SliderRow(QWidget):
    """Etykieta + suwak + wartość liczbowa.

    `step` mówi, o ile skacze suwak. Krok 1 daje suwak całkowitoliczbowy (bez
    miejsc po przecinku) - tego wymaga np. dzielnik impulsów pierścienia.
    """

    valueChanged = Signal(float)

    def __init__(self, label: str, value: float, lo: float, hi: float,
                 suffix: str = "", parent: QWidget | None = None,
                 step: float = 0.05) -> None:
        super().__init__(parent)
        self._lo, self._hi, self._suffix = lo, hi, suffix
        self._integer = step >= 1.0
        self._scale = 1 if self._integer else 100
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._name = QLabel(label)
        self._name.setMinimumWidth(120)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(int(lo * self._scale), int(hi * self._scale))
        self._slider.setValue(int(round(value * self._scale)))
        self._slider.setSingleStep(max(1, int(round(step * self._scale))))
        self._slider.setPageStep(max(1, int(round(step * self._scale))))
        self._value = QLabel()
        self._value.setMinimumWidth(44)
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(self._name)
        lay.addWidget(self._slider, 1)
        lay.addWidget(self._value)

        self._slider.valueChanged.connect(self._on_change)
        self._refresh()

    def _on_change(self, _raw: int) -> None:
        self._refresh()
        self.valueChanged.emit(self.value())

    def _refresh(self) -> None:
        digits = 0 if self._integer else 2
        self._value.setText(f"{self.value():.{digits}f}{self._suffix}")

    def value(self) -> float:
        return self._slider.value() / self._scale

    def setValue(self, value: float) -> None:
        clamped = max(self._lo, min(self._hi, value))
        self._slider.blockSignals(True)
        self._slider.setValue(int(round(clamped * self._scale)))
        self._slider.blockSignals(False)
        self._refresh()


# --------------------------------------------------------------------------- #
_QT_KEYS = {
    Qt.Key_Escape: "Esc", Qt.Key_Tab: "Tab", Qt.Key_Backspace: "Backspace",
    Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter", Qt.Key_Insert: "Insert",
    Qt.Key_Delete: "Delete", Qt.Key_Home: "Home", Qt.Key_End: "End",
    Qt.Key_PageUp: "PgUp", Qt.Key_PageDown: "PgDn", Qt.Key_Left: "Left",
    Qt.Key_Up: "Up", Qt.Key_Right: "Right", Qt.Key_Down: "Down",
    Qt.Key_Space: "Space", Qt.Key_Print: "PrintScreen", Qt.Key_Pause: "Pause",
    Qt.Key_CapsLock: "CapsLock", Qt.Key_NumLock: "NumLock",
    Qt.Key_ScrollLock: "ScrollLock", Qt.Key_Menu: "Apps",
    Qt.Key_Semicolon: ";", Qt.Key_Equal: "=", Qt.Key_Comma: ",", Qt.Key_Minus: "-",
    Qt.Key_Period: ".", Qt.Key_Slash: "/", Qt.Key_QuoteLeft: "`",
    Qt.Key_BracketLeft: "[", Qt.Key_Backslash: "\\", Qt.Key_BracketRight: "]",
    Qt.Key_Apostrophe: "'",
}
for _i in range(1, 25):
    _QT_KEYS[Qt.Key(int(Qt.Key_F1) + _i - 1)] = f"F{_i}"

_NUMPAD = {Qt.Key_Plus: "Num+", Qt.Key_Minus: "Num-", Qt.Key_Asterisk: "Num*",
           Qt.Key_Slash: "Num/", Qt.Key_Period: "Num."}

_MOD_KEYS = {Qt.Key_Control: "Ctrl", Qt.Key_Shift: "Shift", Qt.Key_Alt: "Alt",
             Qt.Key_AltGr: "Alt", Qt.Key_Meta: "Win"}
_MOD_ORDER = ["Ctrl", "Shift", "Alt", "Win"]


def _mod_names(modifiers) -> list[str]:
    names = []
    if modifiers & Qt.ControlModifier:
        names.append("Ctrl")
    if modifiers & Qt.ShiftModifier:
        names.append("Shift")
    if modifiers & Qt.AltModifier:
        names.append("Alt")
    if modifiers & Qt.MetaModifier:
        names.append("Win")
    return names


class HotkeyEdit(QLineEdit):
    """Pole 'kliknij i naciśnij skrót'. Zwraca zapis typu 'Ctrl+Shift+E'.

    `mods_only=True` pozwala zapisać sam modyfikator ("Shift", "Ctrl+Alt") - tego
    wymagają pola typu "co trzymać", gdzie klawisz główny byłby wręcz szkodliwy.
    """

    hotkeyChanged = Signal(str)
    captureChanged = Signal(bool)

    def __init__(self, value: str = "", parent: QWidget | None = None,
                 mods_only: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Capture")
        self.setReadOnly(True)
        self._mods_only = mods_only
        self._idle_text = (
            tr("kliknij i naciśnij klawisze") if mods_only
            else tr("kliknij i naciśnij skrót")
        )
        self.setPlaceholderText(self._idle_text)
        self.setText(value)
        self.setCursor(Qt.PointingHandCursor)
        self._recording = False

    def _set_recording(self, value: bool) -> None:
        if value == self._recording:
            return
        self._recording = value
        self.setProperty("recording", "true" if value else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if value:
            self.setPlaceholderText(tr("naciśnij  (Esc = wyczyść)"))
        else:
            self.setPlaceholderText(self._idle_text)
        self.captureChanged.emit(value)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._set_recording(True)

    def focusOutEvent(self, event) -> None:
        self._set_recording(False)
        super().focusOutEvent(event)

    def event(self, event) -> bool:
        # Tab i Backtab muszą trafić do keyPressEvent, a nie do nawigacji fokusem.
        if event.type() == QEvent.KeyPress and self._recording:
            if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
                self.keyPressEvent(event)
                return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in _MOD_KEYS:
            # Sam modyfikator jest pełnoprawnym zapisem tylko w polach "co trzymać";
            # gdzie indziej czekamy na klawisz główny.
            if not self._mods_only:
                return
            parts = _mod_names(event.modifiers())
            if _MOD_KEYS[key] not in parts:
                parts.append(_MOD_KEYS[key])
            parts.sort(key=_MOD_ORDER.index)
            self.set_hotkey("+".join(parts))
            return
        if key == Qt.Key_Escape:
            self.set_hotkey("")
            return

        mods = event.modifiers()
        parts = _mod_names(mods)

        name = ""
        keypad = bool(mods & Qt.KeypadModifier)
        if keypad and Qt.Key_0 <= key <= Qt.Key_9:
            name = f"Num{key - Qt.Key_0}"
        elif keypad and key in _NUMPAD:
            name = _NUMPAD[key]
        elif key in _QT_KEYS:
            name = _QT_KEYS[key]
        elif Qt.Key_A <= key <= Qt.Key_Z:
            name = chr(key)
        elif Qt.Key_0 <= key <= Qt.Key_9:
            name = chr(key)
        elif key == Qt.Key_Backtab:
            name = "Tab"

        if not name:
            return
        parts.append(name)
        self.set_hotkey("+".join(parts))

    def set_hotkey(self, value: str) -> None:
        if value != self.text():
            self.setText(value)
            self.hotkeyChanged.emit(value)
        elif not value:
            self.hotkeyChanged.emit(value)


# --------------------------------------------------------------------------- #
class BindingEditor(QWidget):
    """Wybór typu akcji + jej parametry."""

    changed = Signal()
    captureChanged = Signal(bool)

    def __init__(self, binding: Binding, allow_direct: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.binding = binding
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Akcje wysyłane mostem mają sens tylko w profilu obsługiwanym przez
        # dodatek - w pozostałych nie pokazujemy ich wcale, żeby nie dało się
        # ustawić czegoś, co i tak nie zadziała.
        self._types = [t for t in ACTION_TYPES
                       if allow_direct or t not in DIRECT_ONLY_TYPES]
        self.type_box = combo(14)
        for t in self._types:
            self.type_box.addItem(tr(ACTION_LABELS[t]), t)
        start = binding.type if binding.type in self._types else "none"
        self.type_box.setCurrentIndex(self._types.index(start))
        lay.addWidget(self.type_box)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack)
        self._pages: dict[str, int] = {}

        # none
        self._pages["none"] = self.stack.addWidget(
            hint(tr("Przycisk działa normalnie - MAKMOUSE go nie przechwytuje."))
        )

        # nav
        nav_page = QWidget()
        nav_lay = QVBoxLayout(nav_page)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        self.nav_box = combo(10)
        for m in NAV_MODES:
            self.nav_box.addItem(tr(NAV_LABELS[m]), m)
        idx = NAV_MODES.index(binding.nav) if binding.nav in NAV_MODES else 0
        self.nav_box.setCurrentIndex(idx)
        nav_lay.addWidget(self.nav_box)
        nav_lay.addWidget(hint(tr("Tryb aktywny tak długo, jak przycisk jest wciśnięty.")))
        self._pages["nav"] = self.stack.addWidget(nav_page)

        # hotkey
        hk_page = QWidget()
        hk_lay = QVBoxLayout(hk_page)
        hk_lay.setContentsMargins(0, 0, 0, 0)
        self.hotkey_edit = HotkeyEdit(binding.hotkey)
        hk_lay.addWidget(self.hotkey_edit)
        hk_lay.addWidget(hint(tr("Wysyłane raz przy naciśnięciu.")))
        self._pages["hotkey"] = self.stack.addWidget(hk_page)

        # hold
        hold_page = QWidget()
        hold_lay = QVBoxLayout(hold_page)
        hold_lay.setContentsMargins(0, 0, 0, 0)
        self.hold_edit = HotkeyEdit(binding.hotkey, mods_only=True)
        self.mouse_box = combo(6)
        self.mouse_box.addItem(K.mouse_label(""), "")
        for b in K.MOUSE_BUTTONS:
            self.mouse_box.addItem(K.mouse_label(b), b)
        pos = self.mouse_box.findData(binding.button)
        self.mouse_box.setCurrentIndex(pos if pos >= 0 else 0)
        hold_lay.addWidget(self.hold_edit)
        hold_lay.addWidget(self.mouse_box)
        hold_lay.addWidget(hint(tr("Trzymane aż do puszczenia przycisku.")))
        self._pages["hold"] = self.stack.addWidget(hold_page)

        # view
        view_page = QWidget()
        view_lay = QVBoxLayout(view_page)
        view_lay.setContentsMargins(0, 0, 0, 0)
        self.view_box = combo(10)
        for v in VIEW_ACTIONS:
            self.view_box.addItem(tr(VIEW_LABELS[v]), v)
        vpos = self.view_box.findData(binding.view)
        self.view_box.setCurrentIndex(vpos if vpos >= 0 else 0)
        view_lay.addWidget(self.view_box)
        view_lay.addWidget(hint(tr(
            "Ustawia widok w programie z profilu (Fusion 360 albo SolidCraft). "
            "Wymaga podłączonego dodatku."
        )))
        self._pages["view"] = self.stack.addWidget(view_page)

        self.chk_toggle = QCheckBox(tr("Przełącznik"))
        self.chk_toggle.setChecked(binding.toggle)
        self.chk_toggle.setToolTip(tr(
            "Bez przełącznika akcja trwa tylko dopóki przycisk jest wciśnięty.\n"
            "Z przełącznikiem zostaje włączona aż do kolejnego wciśnięcia - tak\n"
            "można np. przestawić gałkę z orbity na przesuwanie i zostawić ją tak."
        ))
        lay.addWidget(self.chk_toggle)

        self._sync_stack()
        self.type_box.currentIndexChanged.connect(self._on_type)
        self.nav_box.currentIndexChanged.connect(self._on_nav)
        self.view_box.currentIndexChanged.connect(self._on_view)
        self.chk_toggle.toggled.connect(self._on_toggle)
        self.hotkey_edit.hotkeyChanged.connect(self._on_hotkey)
        self.hold_edit.hotkeyChanged.connect(self._on_hotkey)
        self.mouse_box.currentIndexChanged.connect(self._on_mouse)
        self.hotkey_edit.captureChanged.connect(self.captureChanged)
        self.hold_edit.captureChanged.connect(self.captureChanged)

    def _sync_stack(self) -> None:
        self.stack.setCurrentIndex(self._pages.get(self.binding.type, self._pages["none"]))
        # Przełącznik ma sens tylko tam, gdzie akcja coś utrzymuje.
        self.chk_toggle.setVisible(self.binding.type in ("nav", "hold"))

    def _on_type(self, _index: int) -> None:
        self.binding.type = self.type_box.currentData() or "none"
        if self.binding.type == "hotkey":
            self.hotkey_edit.setText(self.binding.hotkey)
        elif self.binding.type == "hold":
            self.hold_edit.setText(self.binding.hotkey)
        self._sync_stack()
        self.changed.emit()

    def _on_nav(self, index: int) -> None:
        self.binding.nav = NAV_MODES[index]
        self.changed.emit()

    def _on_view(self, _index: int) -> None:
        self.binding.view = self.view_box.currentData() or "front"
        self.changed.emit()

    def _on_toggle(self, value: bool) -> None:
        self.binding.toggle = bool(value)
        self.changed.emit()

    def _on_hotkey(self, value: str) -> None:
        self.binding.hotkey = value
        self.changed.emit()

    def _on_mouse(self, _index: int) -> None:
        self.binding.button = self.mouse_box.currentData() or ""
        self.changed.emit()


class GestureEditor(Card):
    """Modyfikator trzymany w trakcie gestu ciągłego (ruch myszy / scroll)."""

    changed = Signal()
    captureChanged = Signal(bool)

    def __init__(self, title: str, preset, parent: QWidget | None = None) -> None:
        super().__init__(title, parent=parent, flat=True)
        self.preset = preset

        self.keys_edit = HotkeyEdit(preset.keys, mods_only=True)
        self.keys_edit.setPlaceholderText(tr("bez modyfikatora"))
        self.mouse_box = combo(6)
        self.mouse_box.addItem(K.mouse_label(""), "")
        for b in K.MOUSE_BUTTONS:
            self.mouse_box.addItem(K.mouse_label(b), b)
        pos = self.mouse_box.findData(preset.button)
        self.mouse_box.setCurrentIndex(pos if pos >= 0 else 0)

        grid = QHBoxLayout()
        grid.setSpacing(8)
        lbl = QLabel(tr("Trzymaj"))
        lbl.setMinimumWidth(58)
        grid.addWidget(lbl)
        grid.addWidget(self.keys_edit, 3)
        grid.addWidget(self.mouse_box, 2)
        self.add_layout(grid)

        self.keys_edit.hotkeyChanged.connect(self._on_change)
        self.keys_edit.captureChanged.connect(self.captureChanged)
        self.mouse_box.currentIndexChanged.connect(self._on_change)

    def _on_change(self, *_args) -> None:
        self.preset.keys = self.keys_edit.text()
        self.preset.button = self.mouse_box.currentData() or ""
        self.changed.emit()

    def load(self, preset) -> None:
        self.preset = preset
        self.keys_edit.blockSignals(True)
        self.mouse_box.blockSignals(True)
        self.keys_edit.setText(preset.keys)
        self.mouse_box.setCurrentIndex(max(0, self.mouse_box.findData(preset.button)))
        self.keys_edit.blockSignals(False)
        self.mouse_box.blockSignals(False)


class ButtonCard(Card):
    """Kafel jednego fizycznego przycisku urządzenia."""

    changed = Signal()
    captureChanged = Signal(bool)

    def __init__(self, index: int, name: str, binding: Binding, allow_direct: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.index = index
        self._live = False

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.dot = StatusPill("", T.BORDER)
        self.dot.setFixedWidth(14)
        self.title = QLabel(name)
        self.title.setObjectName("Big")
        header.addWidget(self.dot)
        header.addWidget(self.title)
        header.addStretch(1)
        self.badge = QLabel("")
        self.badge.setObjectName("Hint")
        header.addWidget(self.badge)

        # Kwadracik w prawym górnym rogu kafla: wyłącza funkcję tego jednego
        # przycisku, zostawiając jego ustawienia nietknięte.
        self.binding = binding
        self.chk_on = QCheckBox()
        self.chk_on.setChecked(binding.enabled)
        self.chk_on.setToolTip(tr("Włącz / wyłącz ten przycisk"))
        self.chk_on.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.chk_on, 0, Qt.AlignRight | Qt.AlignTop)
        self.body.addLayout(header)

        self.editor = BindingEditor(binding, allow_direct=allow_direct)
        self.editor.changed.connect(self._on_changed)
        self.editor.captureChanged.connect(self.captureChanged)
        self.body.addWidget(self.editor)
        self.body.addStretch(1)

        self.chk_on.toggled.connect(self._on_enabled)
        self._sync_enabled()

    def _on_enabled(self, value: bool) -> None:
        self.binding.enabled = bool(value)
        self._sync_enabled()
        self.changed.emit()

    def _sync_enabled(self) -> None:
        self.editor.setEnabled(self.binding.enabled)
        self.title.setEnabled(self.binding.enabled)

    def _on_changed(self) -> None:
        self.changed.emit()

    def set_live(self, pressed: bool) -> None:
        if pressed == self._live:
            return
        self._live = pressed
        self.repaint_dot()

    def repaint_dot(self) -> None:
        """Kropka trzyma swój kolor, więc po zmianie motywu trzeba go nadać ponownie."""
        self.dot.set_state("", T.ACCENT if self._live else T.BORDER)

    def set_unavailable(self, reason: str) -> None:
        self.badge.setText(reason)
        self.editor.setEnabled(not reason and self.binding.enabled)
        self.setToolTip(reason)
