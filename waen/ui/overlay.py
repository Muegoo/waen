"""Transparent window that draws translations over the virtual desktop.

All public coordinates are physical pixels.  Qt uses logical coordinates, so
the conversion happens here through :func:`waen.geometry.to_logical`.
"""

from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QWidget

from ..config import OverlayConfig
from ..geometry import Box, to_logical
from ..models import OverlayItem

TEXT_PADDING_X = 8
TEXT_PADDING_Y = 4
CORNER_RADIUS = 6
TEXT_FLAGS = int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft)


def make_qt_measure(font_family: str):
    """Return a Qt text measurer suitable for ``layout_blocks``.

    This must be called on a thread with a QGuiApplication because it uses
    QFontMetrics; layout is therefore performed by the UI, not the worker.
    """

    def measure(text: str, font_size: int, max_width: int) -> tuple[int, int]:
        font = QFont(font_family, font_size)
        metrics = QFontMetrics(font)
        inner_width = max(1, max_width - 2 * TEXT_PADDING_X)
        bounds = metrics.boundingRect(
            QRect(0, 0, inner_width, 10_000), TEXT_FLAGS, text
        )
        return (
            min(max_width, bounds.width() + 2 * TEXT_PADDING_X),
            bounds.height() + 2 * TEXT_PADDING_Y,
        )

    return measure


class OverlayWindow(QWidget):
    """Click-through, always-on-top surface for translated text panels."""

    def __init__(
        self, virtual_box: Box, device_pixel_ratio: float, config: OverlayConfig
    ) -> None:
        super().__init__()
        self._config = config
        self._dpr = device_pixel_ratio
        self._items: list[OverlayItem] = []
        self._hidden = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        logical = to_logical(virtual_box, device_pixel_ratio)
        self.setGeometry(logical.x, logical.y, logical.w, logical.h)

    def set_items(self, items: Sequence[OverlayItem]) -> None:
        self._items = list(items)
        self.update()

    def set_hidden(self, hidden: bool) -> None:
        self._hidden = hidden
        self.update()

    def clear(self) -> None:
        self._items = []
        self.update()

    def occupied_boxes(self) -> list[Box]:
        """Return physical boxes currently painted, for capture masking."""
        if self._hidden:
            return []
        return [item.draw for item in self._items]

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # A translucent QWidget has no guaranteed background.  Explicitly
        # clear it on every paint, including hidden/empty states, so a stale
        # panel cannot survive a clear and offscreen rendering stays alpha-0.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        if self._hidden or not self._items:
            painter.end()
            return

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        alpha = int(255 * self._config.background_opacity)
        origin = self.geometry()

        for item in self._items:
            logical = to_logical(item.draw, self._dpr)
            rect = QRect(
                logical.x - origin.x(), logical.y - origin.y(), logical.w, logical.h
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)

            painter.setFont(QFont(self._config.font_family, item.font_size))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                rect.adjusted(
                    TEXT_PADDING_X, TEXT_PADDING_Y, -TEXT_PADDING_X, -TEXT_PADDING_Y
                ),
                TEXT_FLAGS,
                item.translated,
            )
        painter.end()
