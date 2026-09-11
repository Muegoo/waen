"""Render BGR text images for OCR and overlay tests."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter


def render_text(
    text: str,
    width: int = 640,
    height: int = 160,
    point_size: int = 28,
    font_family: str = "Arial",
) -> np.ndarray:
    """Render white text on black and return an ``(H, W, 3)`` BGR array."""
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(0, 0, 0))

    painter = QPainter(image)
    painter.setFont(QFont(font_family, point_size))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(
        image.rect(),
        int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
        text,
    )
    painter.end()

    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    stride = image.bytesPerLine() // 4
    buffer = np.frombuffer(ptr, dtype=np.uint8).reshape(height, stride, 4)
    return np.ascontiguousarray(buffer[:, :width, :3])
