"""The contract implemented by every OCR engine."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from ..models import TextLine


@runtime_checkable
class OcrEngine(Protocol):
    name: str
    reports_confidence: bool

    def recognize(self, image: np.ndarray) -> list[TextLine]:
        """Recognize BGR uint8 image data and return image-relative text lines."""
        ...
