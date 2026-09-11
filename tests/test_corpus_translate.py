from waen.corpus.models import ScriptEntry
from waen.corpus.translate import (
    Checkpoint,
    group_by_scene,
    read_translated_jsonl,
    translate_corpus,
    write_translated_jsonl,
)


def entry(id_, scene, order, text, speaker=None):
    return ScriptEntry(id=id_, game="demo", scene=scene, order=order, speaker=speaker, text_raw=text, text=text)


ENTRIES = [
    entry("a:1", "a", 0, "Hello", "Alice"),
    entry("b:1", "b", 0, "Bye"),
    entry("a:2", "a", 1, "How are you?", "Bob"),
]


class FakeBackend:
    def __init__(self, fail_ids=(), miscount_scenes=()):
        self.calls: list[list[str]] = []
        self.fail_ids = set(fail_ids)
        self.miscount_scenes = set(miscount_scenes)

    def translate_scene(self, entries):
        self.calls.append([e.id for e in entries])
        if len(entries) > 1 and entries[0].scene in self.miscount_scenes:
            return ["wrong count"]
        return [None if e.id in self.fail_ids else f"TH({e.text})" for e in entries]


def test_group_by_scene_keeps_first_seen_order_and_sorts_within():
    groups = group_by_scene(ENTRIES)
    assert [[e.id for e in group] for group in groups] == [["a:1", "a:2"], ["b:1"]]


def test_translate_corpus_sends_whole_scenes_and_returns_mapping(tmp_path):
    backend = FakeBackend()
    result = translate_corpus(ENTRIES, backend, Checkpoint(tmp_path / "ck.json"))

    assert backend.calls == [["a:1", "a:2"], ["b:1"]]
    assert result == {"a:1": "TH(Hello)", "a:2": "TH(How are you?)", "b:1": "TH(Bye)"}


def test_second_run_skips_what_the_checkpoint_already_has(tmp_path):
    path = tmp_path / "ck.json"
    translate_corpus(ENTRIES, FakeBackend(), Checkpoint(path))

    backend = FakeBackend()
    result = translate_corpus(ENTRIES, backend, Checkpoint(path))

    assert backend.calls == []
    assert len(result) == 3


def test_failed_entries_are_not_checkpointed_so_they_retry(tmp_path):
    path = tmp_path / "ck.json"
    translate_corpus(ENTRIES, FakeBackend(fail_ids={"a:2"}), Checkpoint(path))
    assert "a:2" not in Checkpoint(path)

    backend = FakeBackend()
    translate_corpus(ENTRIES, backend, Checkpoint(path))
    assert backend.calls == [["a:2"]]


def test_line_count_mismatch_falls_back_to_one_entry_at_a_time(tmp_path):
    backend = FakeBackend(miscount_scenes={"a"})
    result = translate_corpus(ENTRIES, backend, Checkpoint(tmp_path / "ck.json"))

    assert backend.calls == [["a:1", "a:2"], ["a:1"], ["a:2"], ["b:1"]]
    assert result["a:1"] == "TH(Hello)"


def test_checkpoint_survives_reload_and_writes_atomically(tmp_path):
    path = tmp_path / "ck.json"
    ck = Checkpoint(path)
    ck.add({"x": "y"})

    assert Checkpoint(path).data == {"x": "y"}
    assert not list(tmp_path.glob("*.tmp"))


def test_translated_jsonl_round_trip(tmp_path):
    out = tmp_path / "x.th.jsonl"
    count = write_translated_jsonl(ENTRIES, {"a:1": "สวัสดี", "b:1": "ลาก่อน"}, out)

    assert count == 2
    rows = read_translated_jsonl(out)
    assert [(r["id"], r["translated"], r["speaker"]) for r in rows] == [
        ("a:1", "สวัสดี", "Alice"),
        ("b:1", "ลาก่อน", None),
    ]


def test_cli_dry_run_reports_size_without_calling_any_backend(tmp_path, capsys, monkeypatch):
    from waen.corpus import __main__ as cli
    from waen.corpus.extract import write_jsonl

    src = tmp_path / "x.src.jsonl"
    write_jsonl(ENTRIES, src)

    def boom(*args, **kwargs):
        raise AssertionError("dry-run must not create backend")

    monkeypatch.setattr(cli, "make_backend", boom, raising=False)
    assert cli.main(["translate", "--in", str(src), "--out", str(tmp_path / "x.th.jsonl"), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "entries: 3" in out and "chars: 20" in out
