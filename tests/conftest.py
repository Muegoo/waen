import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    from pathlib import Path

    from PyQt6.QtGui import QFontDatabase
    from PyQt6.QtWidgets import QApplication

    # QGuiApplication is sufficient for OCR rendering, but QWidget-based UI
    # tests require QApplication.  Construct the broader application once.
    app = QApplication.instance() or QApplication([])
    font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))
    yield app
