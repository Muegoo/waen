import pytest

from scripts.ocr_bakeoff import CaseResult, Summary, summarize


def result(engine="windows", pipeline="raw", group="dialogue", acc=1.0, cer=0.0, ms=10.0):
    return CaseResult(
        engine=engine,
        pipeline=pipeline,
        name=f"{group}_01",
        group=group,
        word_accuracy=acc,
        cer=cer,
        elapsed_ms=ms,
        text="whatever",
    )


def test_summarize_averages_accuracy_within_a_group():
    out = summarize([result(acc=1.0), result(acc=0.8)])
    assert len(out) == 1
    assert out[0].mean_word_accuracy == pytest.approx(0.9)
    assert out[0].count == 2


def test_summarize_keeps_engine_pipeline_and_group_separate():
    out = summarize(
        [
            result(engine="windows", pipeline="raw", group="dialogue"),
            result(engine="rapid", pipeline="raw", group="dialogue"),
            result(engine="windows", pipeline="x2", group="dialogue"),
            result(engine="windows", pipeline="raw", group="menu"),
        ]
    )
    assert len(out) == 4


def test_p95_latency_uses_the_slow_end_not_the_average():
    results = [result(ms=float(x)) for x in range(1, 101)]
    out = summarize(results)
    assert out[0].p95_ms >= 95.0


def test_p95_of_single_sample_is_that_sample():
    assert summarize([result(ms=42.0)])[0].p95_ms == pytest.approx(42.0)


def test_summarize_of_empty_input_returns_empty_list():
    assert summarize([]) == []


def test_summary_rows_are_sorted_for_stable_reports():
    out = summarize([result(engine="windows"), result(engine="rapid")])
    assert [s.engine for s in out] == ["rapid", "windows"]
