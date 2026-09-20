from waen.config import AppConfig
from waen.ui.main_window import SettingsWindow, format_status


def test_status_shows_the_state():
    text = format_status("watching", {"requests": 0, "cache_hits": 0, "failures": 0}, True)
    assert "watching" in text


def test_status_shows_per_stage_latency_when_metrics_are_available():
    text = format_status(
        "watching",
        {"requests": 1, "cache_hits": 0, "failures": 0},
        True,
        {"detect_ms": 42.0, "translate_ms": 310.0, "pending": 2},
    )
    assert "42" in text and "310" in text


def test_status_shows_how_many_requests_are_still_in_flight():
    text = format_status(
        "watching",
        {"requests": 1, "cache_hits": 0, "failures": 0},
        True,
        {"detect_ms": 10.0, "translate_ms": 20.0, "pending": 3},
    )
    assert "3" in text


def test_status_works_without_metrics_yet():
    assert "watching" in format_status(
        "watching", {"requests": 0, "cache_hits": 0, "failures": 0}, True, None
    )


def test_status_shows_a_dash_when_the_engine_reports_no_confidence():
    text = format_status("watching", {"requests": 1, "cache_hits": 0, "failures": 0}, False)
    assert "—" in text


def test_status_includes_translation_counters():
    text = format_status(
        "watching", {"requests": 12, "cache_hits": 5, "failures": 1}, True
    )
    assert "12" in text and "5" in text and "1" in text


def test_editing_the_font_size_emits_the_updated_config(qt_app):
    window = SettingsWindow(AppConfig())
    seen = []
    window.config_changed.connect(seen.append)
    window.font_size_input.setValue(24)
    assert seen and seen[-1].overlay.font_size == 24


def test_editing_preprocess_emits_the_updated_config(qt_app):
    window = SettingsWindow(AppConfig())
    seen = []
    window.config_changed.connect(seen.append)
    window.preprocess_input.setCurrentText("raw")
    assert seen and seen[-1].preprocess == "raw"


def test_buttons_emit_their_signals(qt_app):
    window = SettingsWindow(AppConfig())
    events = []
    window.start_requested.connect(lambda: events.append("start"))
    window.stop_requested.connect(lambda: events.append("stop"))
    window.select_region_requested.connect(lambda: events.append("region"))
    window.start_button.click()
    window.stop_button.click()
    window.select_region_button.click()
    assert events == ["start", "stop", "region"]


def test_set_status_updates_the_visible_label(qt_app):
    window = SettingsWindow(AppConfig())
    window.set_status("watching (dxgi)")
    assert "watching (dxgi)" in window.status_label.text()
