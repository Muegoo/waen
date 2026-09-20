import sys
import types

import numpy as np
import pytest

from waen.ocr.rapid_ocr import RapidOcrEngine
from tests.render import render_text


def test_declares_that_it_reports_confidence():
    engine = RapidOcrEngine()
    assert engine.name == "rapid"
    assert engine.reports_confidence is True


def test_is_available_never_raises():
    assert isinstance(RapidOcrEngine.is_available(), bool)


def test_providers_enable_directml_for_all_rapidocr_models(monkeypatch):
    calls = []

    class FakeRapidOCR:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(
        sys.modules, "rapidocr_onnxruntime", types.SimpleNamespace(RapidOCR=FakeRapidOCR)
    )

    RapidOcrEngine(providers=["DmlExecutionProvider", "CPUExecutionProvider"])._ensure_engine()

    assert calls == [
        {
            "det_use_dml": True,
            "cls_use_dml": True,
            "rec_use_dml": True,
            "det_use_cuda": False,
            "cls_use_cuda": False,
            "rec_use_cuda": False,
        }
    ]


def test_directml_initialisation_falls_back_to_cpu(monkeypatch):
    calls = []

    class FakeRapidOCR:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            if kwargs["det_use_dml"]:
                raise RuntimeError("DirectML adapter unavailable")

    monkeypatch.setitem(
        sys.modules, "rapidocr_onnxruntime", types.SimpleNamespace(RapidOCR=FakeRapidOCR)
    )

    engine = RapidOcrEngine(providers=["DmlExecutionProvider", "CPUExecutionProvider"])
    engine._ensure_engine()

    assert [call["det_use_dml"] for call in calls] == [True, False]
    assert engine.active_providers == ("CPUExecutionProvider",)


def test_reads_plain_rendered_text(qt_app):
    if not RapidOcrEngine.is_available():
        pytest.skip("rapidocr-onnxruntime ยังติดตั้งไม่สำเร็จ")
    lines = RapidOcrEngine().recognize(render_text("HELLO WORLD"))
    assert "HELLO WORLD" in " ".join(ln.text for ln in lines).upper()


def test_axis_aligned_box_covers_the_quad_returned_by_the_model(qt_app):
    if not RapidOcrEngine.is_available():
        pytest.skip("rapidocr-onnxruntime ยังติดตั้งไม่สำเร็จ")
    image = render_text("ANCHOR")
    lines = RapidOcrEngine().recognize(image)
    assert lines
    box = lines[0].box
    assert box.w > 0 and box.h > 0
    assert box.right <= image.shape[1] + 1
    assert box.bottom <= image.shape[0] + 1


def test_low_confidence_lines_are_dropped(qt_app):
    if not RapidOcrEngine.is_available():
        pytest.skip("rapidocr-onnxruntime ยังติดตั้งไม่สำเร็จ")
    # min_score 1.01 สูงกว่าคะแนนใด ๆ ที่เป็นไปได้ ทุกบรรทัดจึงต้องถูกตัดทิ้ง
    assert RapidOcrEngine(min_score=1.01).recognize(render_text("ANYTHING")) == []


def test_blank_image_returns_no_lines():
    if not RapidOcrEngine.is_available():
        pytest.skip("rapidocr-onnxruntime ยังติดตั้งไม่สำเร็จ")
    blank = np.zeros((120, 400, 3), dtype=np.uint8)
    assert RapidOcrEngine().recognize(blank) == []
