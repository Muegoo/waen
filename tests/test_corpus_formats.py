import json

from waen.corpus.archives.plain_dir import PlainDirReader
from waen.corpus.formats.plaintext import PlaintextFormat


def test_plain_dir_lists_relative_posix_names_and_reads_bytes(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "b.bin").write_bytes(b"\x00\x01")

    reader = PlainDirReader(tmp_path)

    assert reader.list("**/*.txt") == ["sub/a.txt"]
    assert reader.read("sub/a.txt") == b"hi"
    assert reader.read("b.bin") == b"\x00\x01"


def test_txt_yields_one_message_per_non_empty_line():
    fmt = PlaintextFormat()
    data = "First line\n\n  \nSecond line\n".encode("utf-8")

    messages = list(fmt.decode(data, "demo.txt"))

    assert [m.text for m in messages] == ["First line", "Second line"]
    assert [m.name for m in messages] == ["L1", "L4"]
    assert all(m.speaker is None and m.source == "demo.txt" for m in messages)


def test_jsonl_carries_speaker_and_id():
    fmt = PlaintextFormat()
    rows = [
        {"id": "m1", "speaker": "Alice", "text": "Hello"},
        {"text": "No speaker here"},
    ]
    data = "\n".join(json.dumps(r) for r in rows).encode("utf-8")

    messages = list(fmt.decode(data, "demo.jsonl"))

    assert (messages[0].name, messages[0].speaker, messages[0].text) == ("m1", "Alice", "Hello")
    assert (messages[1].name, messages[1].speaker) == ("2", None)


def test_json_list_and_csv_are_supported():
    fmt = PlaintextFormat()

    as_json = json.dumps([{"text": "A"}, {"speaker": "B", "text": "Bee"}]).encode("utf-8")
    assert [m.text for m in fmt.decode(as_json, "x.json")] == ["A", "Bee"]

    as_csv = "speaker,text\nCara,\"Hi, there\"\n,Alone\n".encode("utf-8")
    messages = list(fmt.decode(as_csv, "x.csv"))
    assert [(m.speaker, m.text) for m in messages] == [("Cara", "Hi, there"), (None, "Alone")]


def test_unknown_extension_yields_nothing():
    assert list(PlaintextFormat().decode(b"abc", "x.dat")) == []
