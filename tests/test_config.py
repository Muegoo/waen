import json

import pytest

from waen.config import AppConfig, load_config, save_config
from waen.geometry import Box


def test_defaults_are_sane():
    config = AppConfig()
    assert config.source_lang == "en"
    assert config.target_lang == "th"
    assert config.region is None
    assert config.overlay.font_family == "Leelawadee UI"
    assert config.overlay.min_font_size < config.overlay.font_size
    assert 0.0 < config.overlay.background_opacity <= 1.0


def test_region_box_is_none_until_a_region_is_chosen():
    assert AppConfig().region_box() is None


def test_set_region_then_region_box_round_trips_physical_pixels():
    config = AppConfig()
    config.set_region(Box(100, 200, 800, 150), scale=1.5)
    assert config.region_box() == Box(100, 200, 800, 150)
    assert config.region_scale == 1.5


def test_save_then_load_preserves_everything(tmp_path):
    path = tmp_path / "config.json"
    config = AppConfig()
    config.set_region(Box(10, 20, 300, 40), scale=1.25)
    config.overlay.font_size = 22
    config.grouping.vertical_gap_ratio = 0.6
    config.hotkeys["toggle"] = "ctrl+alt+y"
    save_config(config, path)

    loaded = load_config(path)
    assert loaded.region_box() == Box(10, 20, 300, 40)
    assert loaded.region_scale == 1.25
    assert loaded.overlay.font_size == 22
    assert loaded.grouping.vertical_gap_ratio == pytest.approx(0.6)
    assert loaded.hotkeys["toggle"] == "ctrl+alt+y"


def test_missing_file_returns_defaults(tmp_path):
    assert load_config(tmp_path / "nope.json") == AppConfig()


def test_corrupt_json_returns_defaults_instead_of_crashing(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ this is not json", encoding="utf-8")
    assert load_config(path) == AppConfig()


def test_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "from_the_future": 42}), encoding="utf-8")
    assert load_config(path) == AppConfig()


def test_wrong_type_falls_back_to_the_default_for_that_field(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"version": 1, "poll_interval_ms": "fast", "target_lang": "th"}),
        encoding="utf-8",
    )
    loaded = load_config(path)
    assert loaded.poll_interval_ms == AppConfig().poll_interval_ms
    assert loaded.target_lang == "th"


def test_partial_nested_section_keeps_the_other_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"version": 1, "overlay": {"font_size": 30}}), encoding="utf-8"
    )
    loaded = load_config(path)
    assert loaded.overlay.font_size == 30
    assert loaded.overlay.font_family == AppConfig().overlay.font_family


def test_save_creates_missing_directories(tmp_path):
    path = tmp_path / "deep" / "nested" / "config.json"
    save_config(AppConfig(), path)
    assert path.exists()
