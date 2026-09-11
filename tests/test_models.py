import dataclasses

import pytest

from waen.geometry import Box
from waen.models import OverlayItem, TextBlock, TextLine


def line(text: str, x: int, y: int, w: int = 100, h: int = 20) -> TextLine:
    return TextLine(text=text, box=Box(x, y, w, h), confidence=1.0)


def test_text_line_is_frozen():
    ln = line("hello", 0, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ln.text = "changed"


def test_text_block_is_frozen():
    blk = TextBlock.from_lines([line("a", 0, 0)], "a", "standalone")
    with pytest.raises(dataclasses.FrozenInstanceError):
        blk.source_text = "changed"


def test_from_lines_computes_union_box():
    blk = TextBlock.from_lines(
        [line("first", 10, 10, w=200), line("second", 10, 40, w=150)],
        "first second",
        "paragraph",
    )
    assert blk.box == Box(10, 10, 200, 50)


def test_from_lines_stores_lines_as_tuple_so_it_stays_hashable_across_threads():
    blk = TextBlock.from_lines([line("a", 0, 0)], "a", "standalone")
    assert isinstance(blk.lines, tuple)


def test_from_lines_rejects_empty_input():
    with pytest.raises(ValueError):
        TextBlock.from_lines([], "", "standalone")


def test_overlay_item_is_frozen():
    item = OverlayItem(
        source_text="Hello",
        translated="สวัสดี",
        anchor=Box(0, 100, 200, 20),
        draw=Box(0, 74, 200, 22),
        font_size=16,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.font_size = 12
