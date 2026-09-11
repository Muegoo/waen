from waen.corpus.adapters.base import split_pages
from waen.corpus.adapters.persona5r import Persona5RoyalAdapter
from waen.corpus.formats.atlus_msg import AtlusMsgFormat


SAMPLE = """\
[dlg DLG_000_01 [Someone]]
[f 4 10][f 2 1]First page here.[n]Still first page.[w]Second page.[f 1 3 65535 0 0][e]

[msg MSG_000_02]
[f 2 1]No speaker on this one.[e]

[sel SEL_000_03]
[f 2 1]Choice A[e]
[f 2 1]Choice B[e]
"""


def test_msg_format_yields_dialogue_and_each_choice_separately():
    messages = list(AtlusMsgFormat().decode(SAMPLE.encode("utf-8"), "e500.msg"))

    assert [m.name for m in messages] == ["DLG_000_01", "MSG_000_02", "SEL_000_03#0", "SEL_000_03#1"]
    assert messages[0].speaker == "Someone"
    assert messages[1].speaker is None
    assert messages[0].text.startswith("[f 4 10]")
    assert [m.text for m in messages[2:]] == ["[f 2 1]Choice A[e]", "[f 2 1]Choice B[e]"]
    assert all(m.source == "e500.msg" for m in messages)


def test_p5r_rules_split_on_w_and_join_on_n():
    messages = list(AtlusMsgFormat().decode(SAMPLE.encode("utf-8"), "e500.msg"))
    pages = split_pages(messages[0].text, Persona5RoyalAdapter.tag_rules, {})

    assert pages == ["First page here. Still first page.", "Second page."]


def test_adapter_detects_a_folder_with_msg_files(tmp_path):
    adapter = Persona5RoyalAdapter()
    assert not adapter.detect(tmp_path)

    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "x.msg").write_text(SAMPLE, encoding="utf-8")
    assert adapter.detect(tmp_path)

    (reader, fmt, pattern), = list(adapter.sources(tmp_path))
    assert reader.list(pattern) == ["deep/x.msg"]
    assert isinstance(fmt, AtlusMsgFormat)


def test_adapter_is_registered():
    from waen.corpus.__main__ import ADAPTERS

    assert ADAPTERS["persona5r"] is Persona5RoyalAdapter
