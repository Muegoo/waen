import pytest

from waen.corpus.build import build_corpus_db, fts5_trigram_available
from waen.translate.lookup import CorpusLookup, load_corpus


pytestmark = pytest.mark.skipif(not fts5_trigram_available(), reason="SQLite has no FTS5 trigram")

ROWS = [
    {"id": "d:1", "scene": "d", "order": 0, "speaker": "A",
     "text": "The masked thieves strike again tonight.", "translated": "โจรสวมหน้ากากลงมืออีกครั้งคืนนี้"},
    {"id": "d:2", "scene": "d", "order": 1, "speaker": None,
     "text": "Welcome to the blue room.", "translated": "ยินดีต้อนรับสู่ห้องสีน้ำเงิน"},
    {"id": "d:3", "scene": "d", "order": 2, "speaker": None, "text": "Yes", "translated": "ใช่"},
    {"id": "d:4", "scene": "d", "order": 3, "speaker": None, "text": "No translation", "translated": ""},
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "demo.sqlite"
    assert build_corpus_db(ROWS, path) == 3
    return path


def test_exact_text_hits_with_full_score(db):
    hit = CorpusLookup(db).lookup("The masked thieves strike again tonight.")
    assert hit is not None
    assert (hit.entry_id, hit.translated, hit.score) == ("d:1", "โจรสวมหน้ากากลงมืออีกครั้งคืนนี้", 100)


def test_ocr_noise_still_hits_and_reports_canonical_source(db):
    hit = CorpusLookup(db).lookup("The rnasked thleves strike again tonight")
    assert hit is not None
    assert hit.entry_id == "d:1"
    assert hit.source == "The masked thieves strike again tonight."
    assert 85 <= hit.score < 100


def test_unrelated_text_misses(db):
    lookup = CorpusLookup(db)
    assert lookup.lookup("Completely different words about cats and rain") is None
    assert lookup.stats() == {"hits": 0, "misses": 1}


def test_threshold_is_respected(db):
    assert CorpusLookup(db, threshold=100).lookup("The rnasked thleves strike again tonight") is None


def test_too_short_text_never_queries(db):
    assert CorpusLookup(db).lookup("Hi") is None
    assert CorpusLookup(db).lookup("Yes").translated == "ใช่"


def test_lookup_is_safe_to_call_from_another_thread(db):
    import threading

    lookup = CorpusLookup(db)
    results = []
    worker = threading.Thread(target=lambda: results.append(lookup.lookup("Welcome to the blue room.")))
    worker.start()
    worker.join()
    assert results[0].entry_id == "d:2"


def test_load_corpus_degrades_to_none(tmp_path, db):
    assert load_corpus(None, 85) is None
    assert load_corpus(str(tmp_path / "missing.sqlite"), 85) is None
    assert isinstance(load_corpus(str(db), 85), CorpusLookup)


def test_cli_build_from_translated_jsonl(tmp_path):
    import json

    from waen.corpus.__main__ import main

    src = tmp_path / "x.th.jsonl"
    src.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in ROWS), encoding="utf-8")
    out = tmp_path / "x.sqlite"

    assert main(["build", "--in", str(src), "--out", str(out)]) == 0
    assert CorpusLookup(out).lookup("Welcome to the blue room.").entry_id == "d:2"
