import json

import pytest

from waen.corpus.adapters.base import TagRules, split_pages
from waen.corpus.adapters.plaintext import PlaintextAdapter
from waen.corpus.extract import corpus_stats, extract_entries, read_jsonl, write_jsonl

DEMO_RULES = TagRules(
    pattern=r"\[(?P<name>[a-z]+)(?P<args>[^\]]*)\]",
    page_break=frozenset({"w"}),
    newline=frozenset({"n"}),
    variables={"hero": "player_name"},
)


def test_page_break_splits_into_one_entry_per_screen():
    pages = split_pages("[f 4 10]First page.[w]Second page.[w][e]", DEMO_RULES, {})
    assert pages == ["First page.", "Second page."]


def test_newline_tag_becomes_a_space_and_other_tags_are_stripped():
    pages = split_pages("[f 2 1]Line one[n]line two.[f 1 3 0][e]", DEMO_RULES, {})
    assert pages == ["Line one line two."]


def test_variable_tag_is_substituted_from_values():
    pages = split_pages("Hey, [hero]. Ready?", DEMO_RULES, {"player_name": "Ren Amamiya"})
    assert pages == ["Hey, Ren Amamiya. Ready?"]


def test_missing_variable_value_keeps_the_tag_visible():
    pages = split_pages("Hey, [hero].", DEMO_RULES, {})
    assert pages == ["Hey, [hero]."]


def test_empty_pages_are_dropped():
    assert split_pages("[w][w]Only this.[w]   [w]", DEMO_RULES, {}) == ["Only this."]


def test_no_rules_means_one_page():
    assert split_pages("Just text, [not a tag].", TagRules.none(), {}) == ["Just text, [not a tag]."]


@pytest.fixture
def demo_game(tmp_path):
    (tmp_path / "ch1").mkdir()
    (tmp_path / "ch1" / "intro.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"id": "m1", "speaker": "Alice", "text": "Welcome."},
                {"id": "m2", "speaker": "Bob", "text": "Thanks."},
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "notes.txt").write_text("Loose line\n", encoding="utf-8")
    (tmp_path / "ignored.bin").write_bytes(b"\x00")
    return tmp_path


def test_plaintext_adapter_walks_every_supported_file(demo_game):
    adapter = PlaintextAdapter()
    assert adapter.detect(demo_game)

    entries = list(extract_entries(adapter, demo_game, {}))

    assert [entry.id for entry in entries] == [
        "plaintext:ch1/intro.jsonl:m1:0",
        "plaintext:ch1/intro.jsonl:m2:0",
        "plaintext:notes.txt:L1:0",
    ]
    assert [entry.scene for entry in entries] == ["ch1/intro.jsonl", "ch1/intro.jsonl", "notes.txt"]
    assert [entry.order for entry in entries] == [0, 1, 0]
    assert entries[0].speaker == "Alice" and entries[2].speaker is None


def test_ids_are_stable_across_runs(demo_game):
    first = [entry.id for entry in extract_entries(PlaintextAdapter(), demo_game, {})]
    second = [entry.id for entry in extract_entries(PlaintextAdapter(), demo_game, {})]
    assert first == second


def test_jsonl_round_trip_and_stats(demo_game, tmp_path):
    entries = list(extract_entries(PlaintextAdapter(), demo_game, {}))
    out = tmp_path / "out.src.jsonl"

    assert write_jsonl(entries, out) == 3
    assert read_jsonl(out) == entries

    stats = corpus_stats(entries)
    assert stats["entries"] == 3
    assert stats["scenes"] == 2
    assert stats["chars"] == len("Welcome.") + len("Thanks.") + len("Loose line")
    assert stats["unique_texts"] == 3


def test_cli_extract_then_stats(demo_game, tmp_path, capsys):
    from waen.corpus.__main__ import main

    out = tmp_path / "x.src.jsonl"
    assert main(["extract", "--game", "plaintext", "--game-dir", str(demo_game), "--out", str(out)]) == 0
    assert out.exists()

    assert main(["stats", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "entries: 3" in printed and "chars: 25" in printed


def test_cli_rejects_unknown_game(tmp_path):
    from waen.corpus.__main__ import main

    assert main(["extract", "--game", "nope", "--game-dir", str(tmp_path), "--out", "x"]) == 2
