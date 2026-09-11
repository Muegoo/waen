import pytest

from waen.corpus.normalize import normalize


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Hello World", "hello world"),
        ("It’s “fine”, isn’t it?", "it s fine isn t it"),
        ("Wait—what… really?", "wait what really"),
        ("Line one\nline two\r\nline three", "line one line two line three"),
        ("   too    many   spaces   ", "too many spaces"),
        ("Hey,you.There!", "hey you there"),
        ("Room 302 — 3rd floor", "room 302 3rd floor"),
        ("", ""),
    ],
)
def test_normalize_examples(raw, expected):
    assert normalize(raw) == expected


def test_normalize_is_idempotent():
    once = normalize("It’s “fine”, isn’t it?\nReally.")
    assert normalize(once) == once


def test_ocr_noise_and_file_text_land_on_the_same_string():
    from_file = "Well… you're “late,” aren't you?"
    from_ocr = "Well... you're \"late,\" aren't you?"
    assert normalize(from_file) == normalize(from_ocr)


def test_script_entry_round_trips_through_dict():
    from waen.corpus.models import ScriptEntry

    entry = ScriptEntry(
        id="demo:a.msg:MSG_1:0",
        game="demo",
        scene="a.msg",
        order=3,
        speaker="Someone",
        text_raw="[f 1]Hi[w]",
        text="Hi",
    )
    assert ScriptEntry.from_dict(entry.to_dict()) == entry
