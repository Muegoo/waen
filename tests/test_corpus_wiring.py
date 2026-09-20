import json

import pytest

from waen.config import AppConfig, load_config
from waen.geometry import Box
from waen.models import TextBlock, TextLine, TranslatedBlock


class FakeCorpus:
    def __init__(self, table):
        self.table = table
        self.asked = []

    def lookup(self, text):
        from waen.translate.lookup import LookupHit

        self.asked.append(text)
        if text in self.table:
            return LookupHit("id-1", text, self.table[text], 97)
        return None


class FakeTranslator:
    def __init__(self):
        self.calls = []

    def translate_many(self, texts):
        self.calls.append(list(texts))
        return [f"G({text})" for text in texts]


def block(text):
    line = TextLine(text=text, box=Box(0, 0, 100, 20), confidence=0.9)
    return TextBlock(lines=(line,), source_text=text, box=line.box, kind="paragraph")


def make_core(corpus):
    from waen.pipeline.core import PipelineCore
    from waen.translate.glossary import Glossary

    return PipelineCore(
        ocr=None,
        config=AppConfig(),
        glossary=Glossary.empty(),
        translator=FakeTranslator(),
        corpus=corpus,
    )


def test_translated_block_defaults_keep_old_call_sites_working():
    translated = TranslatedBlock(block=block("x"), translated="y", glossary_applied=True)
    assert (translated.corpus_hit, translated.corpus_score, translated.corpus_entry_id) == (False, 0, None)


def test_corpus_hit_bypasses_the_translator():
    core = make_core(FakeCorpus({"Hello there.": "สวัสดี"}))
    result = core.translate(block("Hello there."))

    assert result.translated == "สวัสดี"
    assert (result.corpus_hit, result.corpus_score, result.corpus_entry_id) == (True, 97, "id-1")
    assert core.translator.calls == []


def test_corpus_miss_falls_back_to_the_translator():
    core = make_core(FakeCorpus({}))
    result = core.translate(block("Unknown line"))

    assert result.translated == "G(Unknown line)"
    assert result.corpus_hit is False
    assert core.translator.calls == [["Unknown line"]]


def test_no_corpus_behaves_exactly_as_before():
    core = make_core(None)
    assert core.translate(block("Plain")).translated == "G(Plain)"


def test_config_reads_corpus_fields_and_tolerates_junk(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"corpus_path": "corpus/p5r.sqlite", "corpus_threshold": "90"}),
        encoding="utf-8",
    )
    config = load_config(path)
    assert (config.corpus_path, config.corpus_threshold) == ("corpus/p5r.sqlite", 90)

    path.write_text(
        json.dumps({"corpus_path": 123, "corpus_threshold": "high"}), encoding="utf-8"
    )
    config = load_config(path)
    assert (config.corpus_path, config.corpus_threshold) == (None, 85)


def test_debug_dump_records_corpus_fields(tmp_path):
    numpy = pytest.importorskip("numpy")
    from waen.debug import DebugDumper

    frame = numpy.zeros((10, 10, 3), dtype=numpy.uint8)
    hit = TranslatedBlock(
        block=block("A"),
        translated="ก",
        glossary_applied=True,
        corpus_hit=True,
        corpus_score=93,
        corpus_entry_id="p5:x:1:0",
    )
    DebugDumper(tmp_path).dump(frame, [], [], [hit], {})

    payload = json.loads((tmp_path / "0000.json").read_text(encoding="utf-8"))
    entry = payload["translated"][0]
    assert (entry["corpus_hit"], entry["corpus_score"], entry["corpus_entry_id"]) == (True, 93, "p5:x:1:0")
