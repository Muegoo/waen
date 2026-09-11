from waen.geometry import Box
from waen.models import TextBlock, TextLine
from waen.pipeline.stabilize import Stabilizer, StabilizeConfig

CONFIG = StabilizeConfig(stable_frames=2, min_stable_ms=250)
BOX = Box(100, 500, 400, 24)


def block(text: str, box: Box = BOX) -> TextBlock:
    return TextBlock.from_lines(
        [TextLine(text=text, box=box, confidence=1.0)], text, "standalone"
    )


def texts(blocks) -> list[str]:
    return [item.source_text for item in blocks]


def test_first_sighting_is_never_emitted():
    assert Stabilizer(CONFIG).feed([block("Hello there.")], now_ms=0) == []


def test_text_repeated_long_enough_is_emitted_once():
    stabilizer = Stabilizer(CONFIG)
    assert stabilizer.feed([block("Hello there.")], now_ms=0) == []
    assert stabilizer.feed([block("Hello there.")], now_ms=100) == []
    assert texts(stabilizer.feed([block("Hello there.")], now_ms=300)) == ["Hello there."]


def test_the_same_text_is_not_emitted_twice():
    stabilizer = Stabilizer(CONFIG)
    for now in (0, 100, 300):
        stabilizer.feed([block("Hello there.")], now_ms=now)
    assert stabilizer.feed([block("Hello there.")], now_ms=400) == []


def test_growing_prefix_is_never_emitted_midway():
    stabilizer = Stabilizer(CONFIG)
    for index, partial in enumerate(
        ["Welco", "Welcome to", "Welcome to this", "Welcome to this vill"]
    ):
        assert stabilizer.feed([block(partial)], now_ms=index * 60) == []


def test_text_that_finished_growing_is_emitted():
    stabilizer = Stabilizer(CONFIG)
    stabilizer.feed([block("Welco")], now_ms=0)
    stabilizer.feed([block("Welcome to this village.")], now_ms=60)
    stabilizer.feed([block("Welcome to this village.")], now_ms=160)
    assert texts(stabilizer.feed([block("Welcome to this village.")], now_ms=400)) == [
        "Welcome to this village."
    ]


def test_completely_new_text_resets_the_counter():
    stabilizer = Stabilizer(CONFIG)
    stabilizer.feed([block("First line.")], now_ms=0)
    stabilizer.feed([block("First line.")], now_ms=300)
    assert stabilizer.feed([block("Second line.")], now_ms=400) == []


def test_a_block_that_shifts_slightly_is_still_the_same_block():
    stabilizer = Stabilizer(CONFIG)
    stabilizer.feed([block("Hello there.", Box(100, 500, 400, 24))], now_ms=0)
    stabilizer.feed([block("Hello there.", Box(102, 501, 400, 24))], now_ms=100)
    assert texts(
        stabilizer.feed([block("Hello there.", Box(101, 502, 400, 24))], now_ms=300)
    ) == ["Hello there."]


def test_a_block_far_away_is_tracked_separately():
    stabilizer = Stabilizer(CONFIG)
    near = Box(100, 500, 400, 24)
    far = Box(100, 100, 400, 24)
    stabilizer.feed([block("Hello.", near), block("Menu.", far)], now_ms=0)
    stabilizer.feed([block("Hello.", near), block("Menu.", far)], now_ms=100)
    assert sorted(
        texts(stabilizer.feed([block("Hello.", near), block("Menu.", far)], now_ms=300))
    ) == ["Hello.", "Menu."]


def test_text_shorter_than_min_chars_is_ignored():
    stabilizer = Stabilizer(CONFIG)
    for now in (0, 100, 300, 400):
        assert stabilizer.feed([block("a")], now_ms=now) == []


def test_reset_forgets_everything():
    stabilizer = Stabilizer(CONFIG)
    for now in (0, 100, 300):
        stabilizer.feed([block("Hello there.")], now_ms=now)
    stabilizer.reset()
    assert stabilizer.feed([block("Hello there.")], now_ms=400) == []


def test_blocks_that_disappear_are_forgotten_so_they_re_emit_on_return():
    stabilizer = Stabilizer(CONFIG)
    for now in (0, 100, 300):
        stabilizer.feed([block("Hello there.")], now_ms=now)
    stabilizer.feed([], now_ms=400)
    stabilizer.feed([block("Hello there.")], now_ms=500)
    stabilizer.feed([block("Hello there.")], now_ms=600)
    assert texts(stabilizer.feed([block("Hello there.")], now_ms=800)) == ["Hello there."]


def test_pending_is_true_while_text_has_not_settled():
    stabilizer = Stabilizer(CONFIG)
    assert stabilizer.pending is False
    stabilizer.feed([block("Hello there.")], now_ms=0)
    assert stabilizer.pending is True


def test_pending_is_false_once_everything_has_been_emitted():
    stabilizer = Stabilizer(CONFIG)
    for now in (0, 100, 300):
        stabilizer.feed([block("Hello there.")], now_ms=now)
    assert stabilizer.pending is False


def test_a_long_pause_mid_typing_does_emit_partial_text():
    stabilizer = Stabilizer(CONFIG)
    stabilizer.feed([block("Welcome to")], now_ms=0)
    stabilizer.feed([block("Welcome to")], now_ms=400)
    assert texts(stabilizer.feed([block("Welcome to")], now_ms=800)) == ["Welcome to"]
