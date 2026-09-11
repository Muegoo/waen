from waen.config import GroupingConfig
from waen.geometry import Box
from waen.models import TextLine
from waen.pipeline.grouping import group_lines, join_lines, same_paragraph

CONFIG = GroupingConfig()


def line(text: str, x: int, y: int, w: int = 200, h: int = 20) -> TextLine:
    return TextLine(text=text, box=Box(x, y, w, h), confidence=1.0)


def test_two_close_left_aligned_lines_become_one_paragraph():
    blocks = group_lines(
        [line("Welcome to this village,", 100, 500), line("brave warrior.", 100, 524)],
        CONFIG,
    )
    assert len(blocks) == 1
    assert blocks[0].kind == "paragraph"
    assert blocks[0].source_text == "Welcome to this village, brave warrior."


def test_paragraph_box_covers_every_line():
    blocks = group_lines(
        [line("first", 100, 500, w=300), line("second", 100, 524, w=180)], CONFIG
    )
    assert blocks[0].box == Box(100, 500, 300, 44)


def test_menu_items_on_the_same_row_stay_separate():
    blocks = group_lines(
        [line("Iron Sword", 100, 400, w=120), line("Wooden Shield", 300, 400, w=140)],
        CONFIG,
    )
    assert len(blocks) == 2
    assert all(block.kind == "standalone" for block in blocks)


def test_hyphenated_break_joins_without_a_space():
    blocks = group_lines(
        [line("The Phantom Thieves are ex-", 100, 500), line("tremely careful.", 100, 524)],
        CONFIG,
    )
    assert blocks[0].source_text == "The Phantom Thieves are extremely careful."


def test_lines_far_apart_vertically_split():
    blocks = group_lines(
        [line("Chapter One", 100, 100), line("It was a dark night.", 100, 300)], CONFIG
    )
    assert len(blocks) == 2


def test_indentation_beyond_tolerance_splits():
    blocks = group_lines(
        [line("First paragraph.", 100, 500, w=200), line("Indented line.", 140, 524, w=200)],
        CONFIG,
    )
    assert len(blocks) == 2


def test_indentation_within_tolerance_still_joins():
    blocks = group_lines(
        [line("First line.", 100, 500, w=200), line("Second line.", 120, 524, w=200)],
        CONFIG,
    )
    assert len(blocks) == 1


def test_slightly_overlapping_boxes_from_ocr_noise_still_join():
    blocks = group_lines(
        [line("first line", 100, 500), line("second line", 100, 518)], CONFIG
    )
    assert len(blocks) == 1


def test_a_single_line_becomes_a_standalone_block():
    blocks = group_lines([line("Save", 900, 80, w=60)], CONFIG)
    assert len(blocks) == 1
    assert blocks[0].kind == "standalone"
    assert blocks[0].source_text == "Save"


def test_no_horizontal_overlap_splits_even_when_close_vertically():
    blocks = group_lines(
        [line("left", 0, 500, w=100), line("right", 800, 524, w=100)], CONFIG
    )
    assert len(blocks) == 2


def test_input_is_sorted_by_position_not_by_arrival_order():
    blocks = group_lines(
        [line("brave warrior.", 100, 524), line("Welcome to this village,", 100, 500)],
        CONFIG,
    )
    assert blocks[0].source_text == "Welcome to this village, brave warrior."


def test_empty_input_gives_empty_output():
    assert group_lines([], CONFIG) == []


def test_three_line_paragraph_joins_in_order():
    blocks = group_lines(
        [line("one", 100, 500), line("two", 100, 524), line("three", 100, 548)], CONFIG
    )
    assert blocks[0].source_text == "one two three"
    assert len(blocks[0].lines) == 3


def test_join_lines_strips_stray_whitespace():
    assert join_lines([line("  hello ", 0, 0), line(" world  ", 0, 24)]) == "hello world"


def test_same_paragraph_is_false_for_identical_rows():
    a = line("a", 0, 400)
    b = line("b", 0, 400)
    assert same_paragraph(a, b, CONFIG) is False
