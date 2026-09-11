"""Transparent full-screen widget used to drag out a capture region.

The coordinate calculations are deliberately kept in pure functions so they
can be tested without creating a Qt window.
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..geometry import Box, to_physical


def normalize_drag(start: tuple[int, int], end: tuple[int, int]) -> Box:
    """Return a non-negative box regardless of which direction was dragged."""
    x0, y0 = start
    x1, y1 = end
    return Box(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))


def selection_to_physical(rect_logical: Box, device_pixel_ratio: float) -> Box:
    """Convert a Qt logical-coordinate selection to physical screen pixels."""
    return to_physical(rect_logical, device_pixel_ratio)


class RegionSelector(QWidget):
    """A translucent virtual-desktop overlay that emits a selected region."""

    selected = pyqtSignal(object, float)  # Box physical, device pixel ratio
    cancelled = pyqtSignal()

    def __init__(self, virtual_geometry: QRect, device_pixel_ratio: float) -> None:
        super().__init__()
        self._dpr = device_pixel_ratio
        self._start: tuple[int, int] | None = None
        self._end: tuple[int, int] | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(virtual_geometry)

    def mousePressEvent(self, event) -> None:
        point = event.position().toPoint()
        self._start = (point.x(), point.y())
        self._end = self._start
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._start is None:
            return
        point = event.position().toPoint()
        self._end = (point.x(), point.y())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._start is None or self._end is None:
            return

        # Widget events are relative to the virtual-desktop overlay.
        origin = self.geometry()
        local = normalize_drag(self._start, self._end)
        logical = local.offset_by(origin.x(), origin.y())
        self.close()
        if logical.is_valid():
            self.selected.emit(selection_to_physical(logical, self._dpr), self._dpr)
        else:
            self.cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self._start is None or self._end is None:
            return

        box = normalize_drag(self._start, self._end)
        rect = QRect(box.x, box.y, box.w, box.h)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(rect, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor(80, 200, 255), 2))
        painter.drawRect(rect)
