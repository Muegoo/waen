import sys

import pytest

from waen.ocr.windows_ocr import WindowsOcrEngine
from tests.render import render_text

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows.Media.Ocr is Windows-only"
)


def test_is_available_never_raises():
    assert isinstance(WindowsOcrEngine.is_available(), bool)


def test_declares_it_does_not_report_confidence():
    engine = WindowsOcrEngine()
    assert engine.name == "windows"
    assert engine.reports_confidence is False


def test_reads_plain_rendered_text(qt_app):
    image = render_text("HELLO WORLD")
    lines = WindowsOcrEngine().recognize(image)
    assert "HELLO WORLD" in " ".join(line.text for line in lines).upper()


def test_returns_box_inside_the_image(qt_app):
    image = render_text("ANCHOR")
    lines = WindowsOcrEngine().recognize(image)
    assert lines, "OCR must read at least one line"
    box = lines[0].box
    assert 0 <= box.x and 0 <= box.y
    assert box.right <= image.shape[1]
    assert box.bottom <= image.shape[0]
    assert box.w > 0 and box.h > 0


def test_blank_image_returns_no_lines(qt_app):
    import numpy as np

    blank = np.zeros((120, 400, 3), dtype=np.uint8)
    assert WindowsOcrEngine().recognize(blank) == []


def test_engine_is_reusable_across_calls(qt_app):
    engine = WindowsOcrEngine()
    first = engine.recognize(render_text("FIRST"))
    second = engine.recognize(render_text("SECOND"))
    assert "FIRST" in " ".join(line.text for line in first).upper()
    assert "SECOND" in " ".join(line.text for line in second).upper()
