"""Wire the UI and pipeline together for the desktop application.

This module deliberately contains orchestration rather than pipeline logic.
When Windows cannot exclude the overlay from capture, it publishes the active
draw boxes to the worker so the worker can apply the masking fallback.
"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from .config import AppConfig, load_config, save_config
from .geometry import Box
from .ocr.factory import create_engine
from .pipeline.core import PipelineCore
from .pipeline.layout import layout_blocks
from .pipeline.worker import PipelineWorker
from .platform import get_platform
from .translate.glossary import Glossary
from .translate.google import GoogleTranslateBackend
from .ui.overlay import OverlayWindow, make_qt_measure
from .ui.region_selector import RegionSelector

logger = logging.getLogger(__name__)


class WaenApp:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.platform = get_platform()
        self._worker: PipelineWorker | None = None
        self._hidden = False
        self._selector: RegionSelector | None = None

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No display is available for the overlay")
        self._dpr = screen.devicePixelRatio()
        virtual_logical = screen.virtualGeometry()
        self._screen = Box(
            round(virtual_logical.x() * self._dpr),
            round(virtual_logical.y() * self._dpr),
            round(virtual_logical.width() * self._dpr),
            round(virtual_logical.height() * self._dpr),
        )

        self.overlay = OverlayWindow(self._screen, self._dpr, config.overlay)
        self.overlay.show()
        self._measure = make_qt_measure(config.overlay.font_family)

        # The native window handle only exists after show().  Exclusion is the
        # preferred self-capture guard; masks are enabled if it is unavailable.
        win_id = int(self.overlay.winId())
        excluded = self.platform.exclude_from_capture(win_id)
        self.platform.apply_overlay_styles(win_id)
        self._needs_masking = not excluded
        if self._needs_masking:
            logger.warning(
                "Windows could not exclude the overlay from capture; using masks"
            )

    def start(self) -> None:
        region = self.config.region_box()
        if region is None:
            logger.error("No capture region has been selected")
            return
        if self._worker is not None:
            return

        core = PipelineCore(
            ocr=create_engine(self.config.ocr_engine),
            config=self.config,
            glossary=Glossary.from_file(self.config.glossary_path),
            preprocess_name=self.config.preprocess,
            translator=GoogleTranslateBackend(
                self.config.source_lang, self.config.target_lang
            ),
        )
        worker = PipelineWorker(
            core=core,
            region=region,
            capture_preference=self.config.capture_backend,
            poll_interval_ms=self.config.poll_interval_ms,
        )
        worker.blocks_translated.connect(self._on_blocks)
        worker.status.connect(lambda text: logger.info("status: %s", text))
        worker.failed.connect(lambda text: logger.warning("problem: %s", text))
        worker.start()
        self._worker = worker

    def stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
        self.overlay.clear()

    def toggle_hidden(self) -> None:
        self._hidden = not self._hidden
        self.overlay.set_hidden(self._hidden)
        self._publish_masks()

    def select_region(self) -> None:
        was_running = self._worker is not None
        self.stop()
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            logger.warning("Cannot select a region without a display")
            return
        selector = RegionSelector(screen.virtualGeometry(), self._dpr)

        def on_selected(box: Box, scale: float) -> None:
            self.config.set_region(box, scale)
            save_config(self.config)
            if was_running:
                self.start()

        selector.selected.connect(on_selected)
        selector.showFullScreen()
        self._selector = selector  # Keep it alive while the user is selecting.

    def _on_blocks(self, translated) -> None:
        items = layout_blocks(
            translated, self._screen, self.config.overlay, self._measure
        )
        self.overlay.set_items(items)
        self._publish_masks()

    def _publish_masks(self) -> None:
        if self._worker is not None and self._needs_masking:
            self._worker.set_masks(self.overlay.occupied_boxes())


def main(config: AppConfig | None = None, max_frames: int | None = None) -> int:
    """Run the overlay application.

    ``max_frames=0`` is a non-interactive construction smoke used by CI and
    support diagnostics.  Normal interactive launches leave it unset.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    platform = get_platform()
    platform.make_dpi_aware()  # Must precede QApplication construction.

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    waen = WaenApp(config or load_config())
    waen.start()
    if max_frames == 0:
        QTimer.singleShot(0, app.quit)
    try:
        return app.exec()
    finally:
        waen.stop()
