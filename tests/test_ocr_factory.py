import pytest

from waen.ocr.factory import create_engine


def test_explicit_windows_choice_returns_windows_engine():
    pytest.importorskip("winrt.windows.media.ocr")
    assert create_engine("windows").name == "windows"


def test_explicit_rapid_choice_returns_rapid_engine():
    pytest.importorskip("rapidocr_onnxruntime")
    assert create_engine("rapid").name == "rapid"


def test_auto_returns_an_engine_that_satisfies_the_protocol():
    from waen.ocr.base import OcrEngine

    engine = create_engine("auto")
    assert isinstance(engine, OcrEngine)
    assert engine.name in {"windows", "rapid"}


def test_unknown_preference_raises_value_error():
    with pytest.raises(ValueError):
        create_engine("tesseract")
