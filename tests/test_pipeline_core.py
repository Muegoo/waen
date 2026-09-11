import numpy as np

from waen.config import AppConfig
from waen.geometry import Box
from waen.models import TextLine
from waen.pipeline.core import PipelineCore, thai_ratio
from waen.translate.glossary import Glossary


class FakeOcr:
    name = "fake"
    reports_confidence = True

    def __init__(self, lines_per_call):
        self.lines_per_call = list(lines_per_call)
        self.images = []

    def recognize(self, image):
        self.images.append(image)
        return self.lines_per_call.pop(0) if self.lines_per_call else []


class FakeTranslator:
    def __init__(self, rule=None):
        self.rule = rule or (lambda text: f"TH<{text}>")

    def translate_many(self, texts):
        return [self.rule(text) for text in texts]


def line(text, x, y, w=200, h=20):
    return TextLine(text=text, box=Box(x, y, w, h), confidence=1.0)


def frame(h=100, w=200):
    return np.zeros((h, w, 3), dtype=np.uint8)


def make_core(lines_per_call, preprocess_name="raw", translator=None):
    config = AppConfig()
    config.stable_frames = 2
    config.min_stable_ms = 250
    return PipelineCore(
        ocr=FakeOcr(lines_per_call),
        config=config,
        glossary=Glossary.empty(),
        translator=translator or FakeTranslator(),
        preprocess_name=preprocess_name,
    )


def test_thai_ratio_of_pure_english_is_zero():
    assert thai_ratio("Welcome to this village") == 0.0


def test_thai_ratio_of_pure_thai_is_one():
    assert thai_ratio("ยินดีต้อนรับ") == 1.0


def test_thai_ratio_ignores_spaces_and_punctuation():
    assert thai_ratio("!!! ???") == 0.0


def test_thai_ratio_of_empty_text_is_zero():
    assert thai_ratio("") == 0.0


def test_detect_returns_nothing_on_the_first_frame():
    core = make_core([[line("Hello there.", 10, 10)]])
    assert core.detect(frame(), origin=(0, 0), now_ms=0) == []


def test_detect_emits_after_the_text_settles():
    lines = [line("Hello there.", 10, 10)]
    core = make_core([lines, lines, lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    blocks = core.detect(frame(), origin=(0, 0), now_ms=300)
    assert [b.source_text for b in blocks] == ["Hello there."]


def test_boxes_are_shifted_into_screen_coordinates_by_the_region_origin():
    lines = [line("Hello there.", 10, 10)]
    core = make_core([lines, lines, lines])
    core.detect(frame(), origin=(1000, 500), now_ms=0)
    core.detect(frame(), origin=(1000, 500), now_ms=100)
    blocks = core.detect(frame(), origin=(1000, 500), now_ms=300)
    assert blocks[0].box.x == 1010
    assert blocks[0].box.y == 510


def test_boxes_are_divided_back_when_the_image_was_upscaled():
    lines = [line("Hello there.", 20, 20, w=400, h=40)]
    core = make_core([lines, lines, lines], preprocess_name="x2")
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    blocks = core.detect(frame(), origin=(0, 0), now_ms=300)
    assert blocks[0].box == Box(10, 10, 200, 20)


def test_thai_lines_are_dropped_because_they_can_only_be_our_own_overlay():
    lines = [line("ยินดีต้อนรับสู่หมู่บ้าน", 10, 10), line("Welcome home.", 10, 60)]
    core = make_core([lines, lines, lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    blocks = core.detect(frame(), origin=(0, 0), now_ms=300)
    assert [b.source_text for b in blocks] == ["Welcome home."]


def test_two_close_lines_arrive_as_one_paragraph():
    lines = [line("Welcome to this village,", 10, 10), line("brave warrior.", 10, 34)]
    core = make_core([lines, lines, lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    blocks = core.detect(frame(), origin=(0, 0), now_ms=300)
    assert [b.source_text for b in blocks] == ["Welcome to this village, brave warrior."]


def test_detect_skips_ocr_when_nothing_changed_and_nothing_is_pending():
    core = make_core([[], []])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    assert len(core.ocr.images) == 1


def test_detect_keeps_ocring_while_a_block_is_still_settling():
    lines = [line("Hello there.", 10, 10)]
    core = make_core([lines, lines, lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    assert len(core.ocr.images) == 2


def test_last_lines_exposes_the_raw_ocr_output_for_debugging():
    lines = [line("Hello there.", 10, 10)]
    core = make_core([lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    assert [ln.text for ln in core.last_lines] == ["Hello there."]


def test_translate_returns_a_translated_block():
    core = make_core([])
    from waen.models import TextBlock

    block = TextBlock.from_lines([line("Hello there.", 0, 0)], "Hello there.", "standalone")
    result = core.translate(block)
    assert result is not None
    assert result.translated == "TH<Hello there.>"
    assert result.block is block


def test_translate_returns_none_when_the_translator_fails():
    core = make_core([], translator=FakeTranslator(lambda text: None))
    from waen.models import TextBlock

    block = TextBlock.from_lines([line("Hello there.", 0, 0)], "Hello there.", "standalone")
    assert core.translate(block) is None


def test_reset_clears_the_stabilizer_state():
    lines = [line("Hello there.", 10, 10)]
    core = make_core([lines, lines, lines, lines, lines, lines])
    core.detect(frame(), origin=(0, 0), now_ms=0)
    core.detect(frame(), origin=(0, 0), now_ms=100)
    core.detect(frame(), origin=(0, 0), now_ms=300)
    core.reset()
    assert core.detect(frame(), origin=(0, 0), now_ms=400) == []
