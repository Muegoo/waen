"""OCR engine backed by Windows.Media.Ocr."""

from __future__ import annotations

import asyncio
import logging

import numpy as np

from ..geometry import Box
from ..models import TextLine

logger = logging.getLogger(__name__)


def _make_bitmap(image: np.ndarray):
    """Copy a BGR image into the BGRA WinRT bitmap format."""
    from winrt.windows.graphics.imaging import (
        BitmapAlphaMode,
        BitmapPixelFormat,
        SoftwareBitmap,
    )
    from winrt.windows.security.cryptography import CryptographicBuffer

    height, width = image.shape[:2]
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    bgra = np.concatenate([image[:, :, :3], alpha], axis=2)
    buffer = CryptographicBuffer.create_from_byte_array(bgra.tobytes())

    try:
        return SoftwareBitmap.create_copy_from_buffer(
            buffer, BitmapPixelFormat.BGRA8, width, height, BitmapAlphaMode.IGNORE
        )
    except TypeError:
        return SoftwareBitmap.create_copy_from_buffer(
            buffer, BitmapPixelFormat.BGRA8, width, height
        )


class WindowsOcrEngine:
    name = "windows"
    reports_confidence = False

    def __init__(self, language: str = "en-US") -> None:
        self._language = language
        self._engine = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    def is_available(cls) -> bool:
        try:
            cls()._ensure_engine()
            return True
        except Exception as exc:
            logger.info("Windows OCR unavailable: %s", exc)
            return False

    def _ensure_engine(self):
        if self._engine is not None:
            return self._engine

        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine as WinRtOcrEngine

        engine = WinRtOcrEngine.try_create_from_language(Language(self._language))
        if engine is None:
            engine = WinRtOcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            raise RuntimeError(
                f"No OCR language pack is available for {self._language}. "
                "Install it in Settings > Time & language > Language & region."
            )
        self._engine = engine
        return engine

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def recognize(self, image: np.ndarray) -> list[TextLine]:
        engine = self._ensure_engine()
        bitmap = _make_bitmap(image)
        result = self._ensure_loop().run_until_complete(engine.recognize_async(bitmap))

        lines: list[TextLine] = []
        for ocr_line in result.lines:
            words = list(ocr_line.words)
            if not words:
                continue
            box = None
            for word in words:
                rect = word.bounding_rect
                word_box = Box(
                    int(rect.x),
                    int(rect.y),
                    max(1, int(rect.width)),
                    max(1, int(rect.height)),
                )
                box = word_box if box is None else box.union(word_box)
            text = ocr_line.text.strip()
            if text and box is not None:
                lines.append(TextLine(text=text, box=box, confidence=1.0))
        return lines

    def close(self) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()
        self._loop = None
