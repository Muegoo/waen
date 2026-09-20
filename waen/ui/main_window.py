"""Small settings window for waen."""

from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig


def format_status(
    state: str,
    stats: dict,
    reports_confidence: bool,
    metrics: dict | None = None,
) -> str:
    """Build the status-bar text, including metrics when a worker has emitted them."""
    parts = [
        state,
        f"translations {stats.get('requests', 0)}",
        f"cache {stats.get('cache_hits', 0)}",
        f"failures {stats.get('failures', 0)}",
        "confidence available" if reports_confidence else "confidence n/a —",
    ]
    if metrics:
        parts.insert(
            1,
            f"detect {metrics.get('detect_ms', 0):.0f} ms · "
            f"translate {metrics.get('translate_ms', 0):.0f} ms · "
            f"pending {metrics.get('pending', 0)}",
        )
    return " · ".join(parts)


class SettingsWindow(QWidget):
    config_changed = pyqtSignal(object)
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    select_region_requested = pyqtSignal()

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self.setWindowTitle("waen — screen translation glasses")

        form = QFormLayout()

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(8, 48)
        self.font_size_input.setValue(config.overlay.font_size)
        self.font_size_input.valueChanged.connect(self._on_changed)
        form.addRow("Font size", self.font_size_input)

        self.opacity_input = QDoubleSpinBox()
        self.opacity_input.setRange(0.1, 1.0)
        self.opacity_input.setSingleStep(0.05)
        self.opacity_input.setValue(config.overlay.background_opacity)
        self.opacity_input.valueChanged.connect(self._on_changed)
        form.addRow("Background opacity", self.opacity_input)

        self.poll_input = QSpinBox()
        self.poll_input.setRange(50, 2000)
        self.poll_input.setSingleStep(50)
        self.poll_input.setValue(config.poll_interval_ms)
        self.poll_input.valueChanged.connect(self._on_changed)
        form.addRow("Polling interval (ms)", self.poll_input)

        self.ocr_input = QComboBox()
        self.ocr_input.addItems(["auto", "windows", "rapid"])
        self.ocr_input.setCurrentText(config.ocr_engine)
        self.ocr_input.currentTextChanged.connect(self._on_changed)
        form.addRow("OCR engine", self.ocr_input)

        self.preprocess_input = QComboBox()
        self.preprocess_input.addItems(["raw", "x2", "x3_binary", "invert_x2"])
        self.preprocess_input.setCurrentText(config.preprocess)
        self.preprocess_input.currentTextChanged.connect(self._on_changed)
        form.addRow("Preprocessing", self.preprocess_input)

        self.capture_input = QComboBox()
        self.capture_input.addItems(["auto", "dxgi", "mss"])
        self.capture_input.setCurrentText(config.capture_backend)
        self.capture_input.currentTextChanged.connect(self._on_changed)
        form.addRow("Capture method", self.capture_input)

        self.select_region_button = QPushButton("Select region…")
        self.select_region_button.clicked.connect(self.select_region_requested)
        self.start_button = QPushButton("▶ Start")
        self.start_button.clicked.connect(self.start_requested)
        self.stop_button = QPushButton("■ Stop")
        self.stop_button.clicked.connect(self.stop_requested)

        buttons = QHBoxLayout()
        buttons.addWidget(self.select_region_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_changed(self, *_args) -> None:
        config = self._config
        config.overlay = replace(
            config.overlay,
            font_size=self.font_size_input.value(),
            background_opacity=self.opacity_input.value(),
        )
        config.poll_interval_ms = self.poll_input.value()
        config.ocr_engine = self.ocr_input.currentText()
        config.preprocess = self.preprocess_input.currentText()
        config.capture_backend = self.capture_input.currentText()
        self.config_changed.emit(config)
