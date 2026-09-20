import json

import numpy as np

from waen.debug import DebugDumper
from waen.geometry import Box
from waen.models import TextBlock, TextLine, TranslatedBlock


def sample():
    frame = np.zeros((60, 120, 3), dtype=np.uint8)
    line = TextLine(text="Hello there", box=Box(10, 10, 80, 20), confidence=0.9)
    block = TextBlock.from_lines([line], "Hello there", "standalone")
    translated = TranslatedBlock(
        block=block, translated="สวัสดี", glossary_applied=True
    )
    return frame, [line], [block], [translated]


def test_dump_writes_three_files(tmp_path, qt_app):
    frame, lines, blocks, translated = sample()
    DebugDumper(tmp_path).dump(frame, lines, blocks, translated, {"ocr_ms": 12.0})
    assert (tmp_path / "0000_frame.png").exists()
    assert (tmp_path / "0000_boxes.png").exists()
    assert (tmp_path / "0000.json").exists()


def test_the_json_records_text_boxes_and_timings(tmp_path, qt_app):
    frame, lines, blocks, translated = sample()
    DebugDumper(tmp_path).dump(frame, lines, blocks, translated, {"ocr_ms": 12.0})
    data = json.loads((tmp_path / "0000.json").read_text(encoding="utf-8"))
    assert data["lines"][0]["text"] == "Hello there"
    assert data["lines"][0]["box"] == {"x": 10, "y": 10, "w": 80, "h": 20}
    assert data["blocks"][0]["kind"] == "standalone"
    assert data["translated"][0]["translated"] == "สวัสดี"
    assert data["timings"]["ocr_ms"] == 12.0


def test_cycle_numbers_increase(tmp_path, qt_app):
    frame, lines, blocks, translated = sample()
    dumper = DebugDumper(tmp_path)
    assert dumper.dump(frame, lines, blocks, translated, {}) == 0
    assert dumper.dump(frame, lines, blocks, translated, {}) == 1


def test_it_wraps_around_instead_of_filling_the_disk(tmp_path, qt_app):
    frame, lines, blocks, translated = sample()
    dumper = DebugDumper(tmp_path, max_cycles=3)
    for _ in range(5):
        dumper.dump(frame, lines, blocks, translated, {})
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_it_creates_the_directory_if_missing(tmp_path, qt_app):
    target = tmp_path / "deep" / "dump"
    frame, lines, blocks, translated = sample()
    DebugDumper(target).dump(frame, lines, blocks, translated, {})
    assert (target / "0000.json").exists()


def test_a_dump_with_nothing_detected_still_writes(tmp_path, qt_app):
    frame = np.zeros((60, 120, 3), dtype=np.uint8)
    DebugDumper(tmp_path).dump(frame, [], [], [], {})
    data = json.loads((tmp_path / "0000.json").read_text(encoding="utf-8"))
    assert data["lines"] == []
