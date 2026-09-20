import json

from scripts.corpus_hitrate import summarize


def _dump(tmp_path, cycle, translated, kind="paragraph"):
    payload = {
        "translated": [
            {"source_text": text, "kind": kind, "corpus_hit": hit, "corpus_score": score}
            for text, hit, score in translated
        ]
    }
    (tmp_path / f"{cycle:04d}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_summarize_counts_hits_and_ranks_misses(tmp_path):
    _dump(tmp_path, 0, [("A", True, 95), ("B", False, 40)])
    _dump(tmp_path, 1, [("B", False, 42), ("C", True, 88)])
    _dump(tmp_path, 2, [("Menu", False, 10)], kind="standalone")

    report = summarize(tmp_path, kind="paragraph")

    assert report["total"] == 4
    assert report["hits"] == 2
    assert report["rate"] == 0.5
    assert report["top_misses"][0] == ("B", 2)
