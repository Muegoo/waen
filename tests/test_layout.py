from waen.config import OverlayConfig
from waen.geometry import Box
from waen.models import TextBlock, TextLine, TranslatedBlock
from waen.pipeline.layout import clamp_horizontally, collides, layout_blocks

SCREEN = Box(0, 0, 1920, 1080)
CONFIG = OverlayConfig(font_size=16, min_font_size=11, gap_px=4)


def measure(text: str, font_size: int, max_width: int) -> tuple[int, int]:
    """Predictable fake measurement: width is character count times half font size."""
    return (len(text) * font_size // 2, font_size + 8)


def translated(text: str, anchor: Box, thai: str = "แปลแล้ว") -> TranslatedBlock:
    block = TextBlock.from_lines(
        [TextLine(text=text, box=anchor, confidence=1.0)], text, "standalone"
    )
    return TranslatedBlock(block=block, translated=thai, glossary_applied=True)


def run(items, screen=SCREEN, config=CONFIG):
    return layout_blocks(items, screen, config, measure)


def test_clamp_pulls_a_box_back_inside_the_right_edge():
    assert clamp_horizontally(Box(1900, 10, 80, 20), SCREEN) == Box(1840, 10, 80, 20)


def test_clamp_pushes_a_box_back_inside_the_left_edge():
    assert clamp_horizontally(Box(-30, 10, 80, 20), SCREEN) == Box(0, 10, 80, 20)


def test_clamp_leaves_a_box_that_already_fits():
    assert clamp_horizontally(Box(100, 10, 80, 20), SCREEN) == Box(100, 10, 80, 20)


def test_collides_detects_overlap():
    assert collides(Box(0, 0, 50, 50), [Box(25, 25, 50, 50)]) is True


def test_collides_ignores_boxes_that_only_touch():
    assert collides(Box(0, 0, 50, 50), [Box(50, 0, 50, 50)]) is False


def test_translation_is_placed_above_the_original():
    anchor = Box(100, 500, 400, 24)
    items = run([translated("Hello", anchor)])
    assert len(items) == 1
    assert items[0].draw.bottom <= anchor.y
    assert items[0].anchor == anchor


def test_translation_never_covers_the_original():
    anchor = Box(100, 500, 400, 24)
    item = run([translated("Hello", anchor)])[0]
    assert item.draw.intersection(anchor) is None


def test_it_falls_below_when_there_is_no_room_above():
    anchor = Box(100, 0, 400, 24)
    item = run([translated("Hello", anchor)])[0]
    assert item.draw.y >= anchor.bottom


def test_it_shrinks_the_font_when_neither_side_fits_at_full_size():
    screen = Box(0, 0, 400, 70)
    item = run([translated("Hi", Box(0, 25, 200, 20))], screen=screen)[0]
    assert item.font_size < CONFIG.font_size
    assert item.font_size >= CONFIG.min_font_size
    assert item.draw.y >= 0 and item.draw.bottom <= screen.h


def test_last_resort_overlaps_the_original_at_the_smallest_font():
    screen = Box(0, 0, 400, 60)
    anchor = Box(0, 20, 200, 20)
    item = run([translated("Hi", anchor)], screen=screen)[0]
    assert item.font_size == CONFIG.min_font_size
    assert item.draw.intersection(anchor) is not None


def test_a_translation_never_covers_another_blocks_original_text():
    upper = Box(100, 500, 400, 24)
    lower = Box(100, 540, 400, 24)
    items = run([translated("Upper", upper), translated("Lower", lower)])
    for item in items:
        for other in (upper, lower):
            if other == item.anchor:
                continue
            assert item.draw.intersection(other) is None


def test_two_translations_do_not_overlap_each_other():
    items = run(
        [
            translated("First", Box(100, 500, 400, 24)),
            translated("Second", Box(100, 540, 400, 24)),
        ]
    )
    assert items[0].draw.intersection(items[1].draw) is None


def test_a_wide_panel_is_pulled_inside_the_right_edge():
    anchor = Box(1900, 500, 20, 24)
    item = run([translated("x", anchor, thai="กขคงจฉชญฎฏ")])[0]
    assert item.draw.right <= SCREEN.w
    assert item.draw.x >= 0


def test_output_is_ordered_top_to_bottom_regardless_of_input_order():
    lower = translated("Lower", Box(100, 800, 400, 24))
    upper = translated("Upper", Box(100, 200, 400, 24))
    items = run([lower, upper])
    assert [item.source_text for item in items] == ["Upper", "Lower"]


def test_empty_input_gives_empty_output():
    assert run([]) == []


def test_the_original_text_is_carried_through_for_debugging():
    item = run([translated("Hello there", Box(0, 500, 100, 20))])[0]
    assert item.source_text == "Hello there"
    assert item.translated == "แปลแล้ว"
