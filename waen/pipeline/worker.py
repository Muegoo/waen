"""Capture loop that runs separately from the UI thread."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal

from ..capture.factory import create_backend
from ..geometry import Box
from .core import PipelineCore, apply_masks

logger = logging.getLogger(__name__)


class PipelineWorker(QThread):
    blocks_translated = pyqtSignal(object)  # list[TranslatedBlock]
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        core: PipelineCore,
        region: Box,
        capture_preference: str = "auto",
        poll_interval_ms: int = 250,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._core = core
        self._region = region
        self._capture_preference = capture_preference
        self._poll_ms = max(50, int(poll_interval_ms))
        self._paused = False
        self._region_dirty = False
        self._masks: list[Box] = []

    def set_region(self, region: Box) -> None:
        self._region = region
        self._region_dirty = True

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def set_masks(self, masks: list[Box]) -> None:
        """Store overlay masks for the Task 26 UI integration."""
        self._masks = list(masks)

    def stop(self) -> None:
        self.requestInterruption()
        self.wait(3000)

    def run(self) -> None:
        backend = create_backend(self._capture_preference)
        executor = ThreadPoolExecutor(max_workers=2)
        consecutive_failures = 0
        try:
            self.status.emit(f"watching ({backend.name})")
            while not self.isInterruptionRequested():
                if self._paused:
                    self.msleep(100)
                    continue
                if self._region_dirty:
                    self._core.reset()
                    self._region_dirty = False

                try:
                    frame = backend.grab(self._region)
                    consecutive_failures = 0
                except Exception as exc:
                    consecutive_failures += 1
                    logger.warning("Capture failed: %s", exc)
                    self.failed.emit(f"Capture failed: {exc}")
                    if consecutive_failures >= 10:
                        self.failed.emit("Capture failed 10 times consecutively; stopping")
                        return
                    self.msleep(self._poll_ms)
                    continue

                if frame is None:
                    self.msleep(self._poll_ms)
                    continue

                now_ms = int(time.monotonic() * 1000)
                try:
                    masked = apply_masks(frame, self._region, self._masks)
                    blocks = self._core.detect(
                        masked, origin=(self._region.x, self._region.y), now_ms=now_ms
                    )
                except Exception as exc:
                    logger.exception("OCR failed")
                    self.failed.emit(f"OCR failed: {exc}")
                    self.msleep(self._poll_ms)
                    continue

                if blocks:
                    self.status.emit(f"translating {len(blocks)}")
                    executor.submit(self._translate_and_emit, blocks)
                self.msleep(self._poll_ms)
        finally:
            executor.shutdown(wait=False)
            backend.close()
            self.status.emit("stopped")

    def _translate_and_emit(self, blocks) -> None:
        translated = []
        for block in blocks:
            try:
                result = self._core.translate(block)
            except Exception as exc:
                logger.warning("Translation failed: %s", exc)
                result = None
            if result is not None:
                translated.append(result)
        if translated:
            self.blocks_translated.emit(translated)
        else:
            self.failed.emit("Translation failed; check the internet connection")
        self.status.emit("watching")
