"""Podgląd na żywo - rysowana grafika urządzenia reagująca na jego ruchy.

ZA CO ODPOWIADA
    * narysowanie urządzenia w rzucie 3/4 (podstawa, opaska, 3 lub 6 przycisków,
      świecący pierścień, gałka) - wszystko kodem, bez plików graficznych,
    * animacja: wciśnięty przycisk świeci, gałka się odchyla i pokazuje strzałkę
      kierunku, pierścień rozbłyska w stronę obrotu; efekty same gasną (~0,25 s).
    Legenda z opisem funkcji pod grafiką NIE jest tu - buduje ją main_window.py.

NAJWAŻNIEJSZE ELEMENTY
    DeviceView ........... widget grafiki
      set_button() ....... wciśnięcie / puszczenie przycisku
      set_axis() ......... wychylenie gałki
      pulse_wheel() ...... impuls pierścienia
      set_count() ........ 3 albo 6 przycisków na opasce
      _geometry() ........ proporcje wszystkich elementów (liczone raz na rozmiar)
      _draw_*() .......... rysowanie kolejnych warstw grafiki

POWIĄZANIA
    używa: theme.py (kolor wiodący)
    używany przez: main_window.py (karta "Podgląd na żywo")

SZCZEGÓŁY
Widok 3/4 urządzenia: metalowa stożkowa podstawa, czarna opaska z przyciskami
bocznymi (trzema albo sześcioma), świecący pierścień i gałka o profilu klepsydry.

Elementy reagują na wejście z urządzenia:
  * przycisk boczny  -> podświetlenie wciśniętego przycisku,
  * ruch myszy (X/Y) -> gałka odchyla się i zapala się strzałka kierunku,
  * scroll           -> zapala się łuk w stronę obrotu.

Przypisania poszczególnych elementów wypisuje legenda pod grafiką (okno główne).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor, QLinearGradient, QPainter, QPainterPath, QPainterPathStroker, QPen, QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import theme as T

MAX_BUTTONS = 6
AXIS_DECAY = 0.80  # zanik wskaźnika osi na klatkę (~0.25 s do wygaszenia)
WHEEL_DECAY = 0.82
FRAME_MS = 16
RING_WIDTH = 6.8  # grubość świecącego pierścienia (x skala)
ARROW_WIDTH = 4.0  # grubość strzałki kierunku (x skala)

# Kąty przycisków na opasce (przód urządzenia = 270 stopni).
BUTTON_ANGLES = {
    3: (215.0, 270.0, 325.0),
    6: (203.0, 230.0, 257.0, 283.0, 310.0, 337.0),
}


def _ellipse_rect(cx: float, cy: float, rx: float, ry: float) -> QRectF:
    return QRectF(cx - rx, cy - ry, rx * 2, ry * 2)


class DeviceView(QWidget):
    """Grafika urządzenia sterowana zdarzeniami z MAKMOUSE."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._count = 3
        self._buttons = {i: False for i in range(1, MAX_BUTTONS + 1)}
        self._labels = {i: "" for i in range(1, MAX_BUTTONS + 1)}
        self._ax = 0.0
        self._ay = 0.0
        self._wheel = 0.0
        self._enabled_look = True

        self._shapes: dict[str, object] = {}
        self._geom_for = (0, 0)

        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._on_frame)
        self._timer.start()

    # ------------------------------------------------------------- stan ---
    def set_active(self, on: bool) -> None:
        self._enabled_look = on
        self.update()

    def set_button(self, index: int, pressed: bool) -> None:
        if index in self._buttons and self._buttons[index] != pressed:
            self._buttons[index] = pressed
            self.update()

    def set_count(self, count: int) -> None:
        """Ile przycisków bocznych ma rysować grafika (3 albo 6)."""
        count = 6 if count >= 6 else 3
        if count != self._count:
            self._count = count
            self._shapes = {}  # geometria zależy od liczby przycisków
            self.update()

    def set_labels(self, labels: dict[int, str]) -> None:
        self._labels = {i: labels.get(i, "") for i in range(1, MAX_BUTTONS + 1)}
        self.setToolTip("\n".join(f"{i}: {self._labels[i] or '-'}"
                                  for i in range(1, self._count + 1)))
        self.update()

    def set_axis(self, dx: float, dy: float) -> None:
        self._ax = max(-1.0, min(1.0, dx))
        self._ay = max(-1.0, min(1.0, dy))
        self.update()

    def pulse_wheel(self, notches: float) -> None:
        self._wheel = max(-1.0, min(1.0, self._wheel + notches * 0.6))
        self.update()

    def _on_frame(self) -> None:
        changed = False
        if abs(self._ax) > 0.004 or abs(self._ay) > 0.004:
            self._ax *= AXIS_DECAY
            self._ay *= AXIS_DECAY
            changed = True
        else:
            changed = self._ax != 0.0 or self._ay != 0.0
            self._ax = self._ay = 0.0
        if abs(self._wheel) > 0.004:
            self._wheel *= WHEEL_DECAY
            changed = True
        elif self._wheel:
            self._wheel = 0.0
            changed = True
        if changed:
            self.update()

    # --------------------------------------------------------- geometria ---
    def _geometry(self) -> dict:
        """Proporcje odwzorowane ze zdjęć: szeroka stożkowa podstawa, czarna
        opaska z przyciskami, świecący pierścień i przysadzista klepsydra."""
        key = (self.width(), self.height())
        if self._shapes and self._geom_for == key:
            return self._shapes
        self._geom_for = key

        w, h = self.width(), self.height()
        cx = w / 2
        r = min(w * 0.43, h * 0.38)  # promień podstawy - miara wszystkiego
        flat = 0.30  # spłaszczenie elips w rzucie 3/4

        r_band = r * 0.86
        r_ring = r * 0.82
        r_knob_bottom = r * 0.76
        r_knob_top = r * 0.68
        r_knob_waist = r * 0.56

        base_bottom_y = h * 0.50 + r * 0.62
        band_y = base_bottom_y - r * 0.34  # górna krawędź metalu = dół czarnej opaski
        ring_y = band_y - r * 0.17  # świecący pierścień nad opaską
        # Przednia krawędź gałki ma leżeć dokładnie na przedniej krawędzi pierścienia.
        knob_bottom_y = ring_y + (r_ring - r_knob_bottom) * flat
        knob_top_y = knob_bottom_y - r * 0.78

        g = {
            "s": r / 128.0, "cx": cx, "r": r,
            "base_bottom": (cx, base_bottom_y, r, r * flat),
            "base_top": (cx, band_y, r_band, r_band * flat),
            "band_top": (cx, ring_y, r_ring, r_ring * flat),
            "ring": (cx, ring_y, r_ring, r_ring * flat),
            "knob_bottom": (cx, knob_bottom_y, r_knob_bottom, r_knob_bottom * flat),
            "knob_top": (cx, knob_top_y, r_knob_top, r_knob_top * flat),
            "knob_waist": r_knob_waist,
        }
        g["buttons"] = self._button_shapes(g, self._count)
        self._shapes = g
        return g

    @staticmethod
    def _cone(top: tuple, bottom: tuple) -> QPainterPath:
        """Bryła ściętego stożka między dwiema elipsami."""
        tcx, tcy, trx, tryy = top
        bcx, bcy, brx, bry = bottom
        # Kąty Qt: 0 = godzina 3, dodatnie = przeciwnie do ruchu wskazówek.
        p = QPainterPath()
        p.moveTo(tcx - trx, tcy)
        p.lineTo(bcx - brx, bcy)
        p.arcTo(_ellipse_rect(bcx, bcy, brx, bry), 180, 180)  # lewo -> dół -> prawo
        p.lineTo(tcx + trx, tcy)
        p.arcTo(_ellipse_rect(tcx, tcy, trx, tryy), 0, 180)  # prawo -> góra -> lewo
        p.closeSubpath()
        return p

    @staticmethod
    def _knob_path(g: dict, off_x: float = 0.0, off_y: float = 0.0) -> QPainterPath:
        """Sylwetka gałki - klepsydra z wciętą talią."""
        bcx, bcy, brx, bry = g["knob_bottom"]
        tcx, tcy, trx, tryy = g["knob_top"]
        bcx += off_x
        tcx += off_x
        tcy += off_y
        rw = g["knob_waist"]
        span = bcy - tcy
        p = QPainterPath()
        p.moveTo(bcx - brx, bcy)
        p.cubicTo(bcx - rw, bcy - span * 0.42, tcx - rw, tcy + span * 0.42, tcx - trx, tcy)
        p.arcTo(_ellipse_rect(tcx, tcy, trx, tryy), 180, -180)
        p.cubicTo(tcx + rw, tcy + span * 0.42, bcx + rw, bcy - span * 0.42, bcx + brx, bcy)
        p.arcTo(_ellipse_rect(bcx, bcy, brx, bry), 0, -180)
        p.closeSubpath()
        return p

    @staticmethod
    def _button_shapes(g: dict, count: int) -> dict[int, QPainterPath]:
        """Przyciski rozłożone na czarnej opasce, od lewej do prawej."""
        _cx, band_y, r_band, _ = g["base_top"]
        cx, ring_y, r_ring, _ = g["band_top"]
        mid_y = (band_y + ring_y) / 2
        rx = (r_band + r_ring) / 2
        ry = rx * 0.30
        r = g["r"]
        angles = BUTTON_ANGLES.get(count, BUTTON_ANGLES[3])
        # Przy sześciu przyciskach na tej samej opasce każdy musi być węższy.
        bw = r * (0.26 if count <= 3 else 0.17)
        bh = r * 0.115
        out: dict[int, QPainterPath] = {}
        for i, ang in enumerate(angles, start=1):
            rad = math.radians(ang)
            px = cx + math.cos(rad) * rx * 0.80
            # Zsunięte niżej, żeby nie wchodziły pod świecący pierścień.
            py = mid_y - math.sin(rad) * ry * 0.95 + r * 0.05
            path = QPainterPath()
            path.addRoundedRect(QRectF(px - bw / 2, py - bh / 2, bw, bh), bh * 0.42, bh * 0.42)
            out[i] = path
        return out

    # ------------------------------------------------------------ rysunek --
    def paintEvent(self, _event) -> None:
        g = self._geometry()
        s = g["s"]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        dim = 1.0 if self._enabled_look else 0.45
        accent = QColor(T.ACCENT)
        accent.setAlphaF(dim)

        self._draw_shadow(p, g)
        self._draw_base(p, g, dim)
        self._draw_band(p, g, dim)
        self._draw_buttons(p, g, s, dim)
        self._draw_ring_back(p, g, s, dim)
        self._draw_knob(p, g, s, dim)
        # Przednia połowa pierścienia idzie na wierzch - tak jak na zdjęciach.
        self._draw_ring_front(p, g, s, dim)
        self._draw_direction(p, g, s)
        p.end()

    def _draw_shadow(self, p: QPainter, g: dict) -> None:
        cx, cy, rx, ry = g["base_bottom"]
        grad = QRadialGradient(QPointF(cx, cy + ry * 0.6), rx * 1.25)
        grad.setColorAt(0.0, QColor(0, 0, 0, 110))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(_ellipse_rect(cx, cy + ry * 0.55, rx * 1.2, ry * 0.85))

    def _draw_base(self, p: QPainter, g: dict, dim: float) -> None:
        cx, cy, rx, ry = g["base_bottom"]
        body = self._cone(g["base_top"], g["base_bottom"])
        grad = QLinearGradient(cx - rx, 0, cx + rx, 0)
        for pos, col in ((0.00, "#6E747E"), (0.16, "#C9CFD8"), (0.34, "#F0F3F7"),
                         (0.52, "#9AA1AB"), (0.72, "#DFE4EA"), (0.90, "#7B8189"),
                         (1.00, "#565B63")):
            c = QColor(col)
            c.setAlphaF(dim)
            grad.setColorAt(pos, c)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(body)

        edge = QColor("#3A4048")
        edge.setAlphaF(0.7 * dim)
        p.setPen(QPen(edge, max(1.0, g["s"])))
        p.setBrush(Qt.NoBrush)
        p.drawPath(body)

    def _draw_band(self, p: QPainter, g: dict, dim: float) -> None:
        band = self._cone(g["band_top"], g["base_top"])
        cx, _cy, rx, _ry = g["base_top"]
        grad = QLinearGradient(cx - rx, 0, cx + rx, 0)
        for pos, col in ((0.0, "#0C0E12"), (0.30, "#2B303A"), (0.55, "#14171C"),
                         (0.80, "#262B33"), (1.0, "#0B0D10")):
            c = QColor(col)
            c.setAlphaF(dim)
            grad.setColorAt(pos, c)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(band)

    def _draw_buttons(self, p: QPainter, g: dict, s: float, dim: float) -> None:
        for i, path in g["buttons"].items():
            pressed = self._buttons.get(i, False)
            if pressed:
                glow = QColor(T.ACCENT)
                glow.setAlpha(80)
                p.setPen(Qt.NoPen)
                p.setBrush(glow)
                p.drawPath(_grown(path, 5.5 * s))

            fill = QColor(T.ACCENT) if pressed else QColor("#1A1E25")
            if not pressed:
                fill.setAlphaF(dim)
            p.setBrush(fill)
            border = QColor(T.ACCENT_SOFT if pressed else "#454C57")
            border.setAlphaF(dim)
            p.setPen(QPen(border, max(1.0, 1.2 * s)))
            p.drawPath(path)

            rect = path.boundingRect()
            label = QColor("#FFFFFF" if pressed else "#8A93A3")
            label.setAlphaF(dim)
            p.setPen(QPen(label))
            font = p.font()
            font.setPointSizeF(max(6.5, 7.5 * s))
            font.setBold(pressed)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, str(i))

    def _draw_ring_back(self, p: QPainter, g: dict, s: float, dim: float) -> None:
        """Tylna połowa pierścienia - rysowana przed gałką, więc częściowo znika za nią."""
        cx, cy, rx, ry = g["ring"]
        color = QColor(T.ACCENT)
        color.setAlphaF(0.35 * dim)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(color, max(3.0, RING_WIDTH * s), Qt.SolidLine, Qt.RoundCap))
        p.drawArc(_ellipse_rect(cx, cy, rx, ry), 0, 180 * 16)

    def _draw_ring_front(self, p: QPainter, g: dict, s: float, dim: float) -> None:
        cx, cy, rx, ry = g["ring"]
        rect = _ellipse_rect(cx, cy, rx, ry)
        width = max(3.0, RING_WIDTH * s)
        front, sweep = 0, -180 * 16  # przednia połowa: od godziny 3 przez dół

        halo = QColor(T.ACCENT)
        halo.setAlphaF(0.13 * dim)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(halo, width * 1.9, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, front, sweep)

        base = QColor(T.ACCENT)
        base.setAlphaF(0.62 * dim)
        p.setPen(QPen(base, width, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, front, sweep)

        if abs(self._wheel) <= 0.01:
            return
        strength = min(1.0, abs(self._wheel))
        direction = 1 if self._wheel > 0 else -1

        glow = QColor(T.ACCENT)
        glow.setAlphaF(0.28 * strength)
        p.setPen(QPen(glow, width * 3.6, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, front, sweep)

        hot = QColor(T.ACCENT_SOFT)
        hot.setAlphaF(min(1.0, 0.5 + strength))
        p.setPen(QPen(hot, width * 1.4, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, front, sweep)
        # Grot na tym końcu przedniego łuku, w którą stronę kręci się pierścień.
        self._draw_rotation_arrow(p, g, s, direction, hot)

    def _draw_rotation_arrow(self, p: QPainter, g: dict, s: float, direction: int, color: QColor) -> None:
        cx, cy, rx, ry = g["ring"]
        end_deg = 356.0 if direction > 0 else 184.0
        ang = math.radians(end_deg)
        x = cx + math.cos(ang) * rx
        y = cy - math.sin(ang) * ry
        size = 12.5 * s
        # Styczna do elipsy w tym punkcie, skierowana zgodnie z obrotem.
        tangent = QPointF(-math.sin(ang) * rx, -math.cos(ang) * ry)
        length = math.hypot(tangent.x(), tangent.y()) or 1.0
        tx, ty = tangent.x() / length * direction, tangent.y() / length * direction
        tip = QPointF(x + tx * size, y + ty * size)
        nx, ny = -ty, tx
        head = QPainterPath(tip)
        head.lineTo(QPointF(x + nx * size * 0.45, y + ny * size * 0.45))
        head.lineTo(QPointF(x - nx * size * 0.45, y - ny * size * 0.45))
        head.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(head)

    def _draw_knob(self, p: QPainter, g: dict, s: float, dim: float) -> None:
        tilt = 9 * s
        off_x = self._ax * tilt
        off_y = self._ay * tilt * 0.55
        body = self._knob_path(g, off_x, off_y)

        cx = g["cx"]
        rx = g["knob_bottom"][2]
        grad = QLinearGradient(cx - rx, 0, cx + rx, 0)
        for pos, col in ((0.0, "#0A0C10"), (0.22, "#3A414C"), (0.45, "#22262E"),
                         (0.70, "#434A56"), (0.88, "#191D23"), (1.0, "#0A0C10")):
            c = QColor(col)
            c.setAlphaF(dim)
            grad.setColorAt(pos, c)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(body)

        outline = QColor("#0A0C10")
        outline.setAlphaF(dim)
        p.setPen(QPen(outline, max(1.0, s)))
        p.setBrush(Qt.NoBrush)
        p.drawPath(body)

        # Talerz na szczycie - ciemne wgłębienie z jasnym rantem.
        tcx, tcy, trx, tryy = g["knob_top"]
        tcx += off_x
        tcy += off_y
        rim = _ellipse_rect(tcx, tcy, trx, tryy)
        rim_grad = QLinearGradient(rim.left(), rim.top(), rim.right(), rim.bottom())
        rim_grad.setColorAt(0.0, QColor("#5A626E"))
        rim_grad.setColorAt(0.5, QColor("#20242B"))
        rim_grad.setColorAt(1.0, QColor("#6A727E"))
        p.setPen(Qt.NoPen)
        p.setBrush(rim_grad)
        p.drawEllipse(rim)

        dish = _ellipse_rect(tcx, tcy + tryy * 0.10, trx * 0.86, tryy * 0.84)
        dish_grad = QRadialGradient(dish.center(), dish.width() / 2)
        dish_grad.setColorAt(0.0, QColor("#0B0D11"))
        dish_grad.setColorAt(1.0, QColor("#1A1E25"))
        p.setBrush(dish_grad)
        p.drawEllipse(dish)

    def _draw_direction(self, p: QPainter, g: dict, s: float) -> None:
        mag = math.hypot(self._ax, self._ay)
        if mag < 0.06:
            return
        tcx, tcy, trx, tryy = g["knob_top"]
        tcx += self._ax * 9 * s
        tcy += self._ay * 9 * s * 0.55
        center = QPointF(tcx, tcy + tryy * 0.1)

        ang = math.atan2(self._ay, self._ax)
        reach = min(1.0, mag) * trx * 0.92
        tip = QPointF(center.x() + math.cos(ang) * reach,
                      center.y() + math.sin(ang) * reach * 0.55)

        color = QColor(T.ACCENT_SOFT)
        color.setAlphaF(min(1.0, 0.35 + mag))
        p.setPen(QPen(color, max(2.6, ARROW_WIDTH * s), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(center, tip)

        size = 10.5 * s
        head = QPainterPath(tip)
        for delta in (2.5, -2.5):
            head.lineTo(QPointF(tip.x() + math.cos(ang + delta) * size,
                                tip.y() + math.sin(ang + delta) * size * 0.55))
        head.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(head)


def _grown(path: QPainterPath, amount: float) -> QPainterPath:
    """Kontur powiększony o zadaną grubość - do rysowania poświaty."""
    stroker = QPainterPathStroker(QPen(Qt.black, amount * 2))
    return stroker.createStroke(path).united(path)
