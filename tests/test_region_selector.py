import os
import subprocess
import sys

import pytest

from waen.config import AppConfig, save_config
from waen.geometry import Box
from waen.ui.region_selector import normalize_drag, selection_to_physical


@pytest.mark.parametrize(
    "start,end",
    [
        ((10, 20), (110, 70)),
        ((110, 70), (10, 20)),
        ((110, 20), (10, 70)),
        ((10, 70), (110, 20)),
    ],
)
def test_drag_in_any_direction_gives_the_same_box(start, end):
    assert normalize_drag(start, end) == Box(10, 20, 100, 50)


def test_zero_size_drag_produces_an_invalid_box_not_a_crash():
    box = normalize_drag((50, 50), (50, 50))
    assert not box.is_valid()


def test_selection_at_100_percent_is_unchanged():
    assert selection_to_physical(Box(100, 200, 800, 150), 1.0) == Box(100, 200, 800, 150)


def test_selection_at_150_percent_scales_up():
    assert selection_to_physical(Box(100, 200, 800, 150), 1.5) == Box(150, 300, 1200, 225)


def test_selection_at_125_percent_scales_up():
    assert selection_to_physical(Box(80, 40, 400, 200), 1.25) == Box(100, 50, 500, 250)


def test_selection_on_a_left_hand_second_monitor_keeps_negative_origin():
    assert selection_to_physical(Box(-1920, 0, 800, 100), 1.0) == Box(-1920, 0, 800, 100)


def _desktop_capture_is_available() -> bool:
    """Probe mss once so this integration test skips in headless sandboxes."""
    from waen.capture.mss_backend import MssCapture

    backend = MssCapture()
    try:
        return backend.grab(Box(0, 0, 8, 8)) is not None
    except Exception:
        return False
    finally:
        backend.close()


@pytest.mark.skipif(
    not _desktop_capture_is_available(),
    reason="requires a desktop that mss can capture",
)
def test_save_region_writes_a_png_matching_the_saved_region(tmp_path, monkeypatch):
    """Exercise the real CLI without requiring an interactive drag."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    config = AppConfig(capture_backend="mss")
    config.set_region(Box(0, 0, 16, 12), scale=1.0)
    save_config(config)

    output_path = tmp_path / "region.png"
    result = subprocess.run(
        [sys.executable, "-m", "waen", "--save-region", str(output_path)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )

    assert result.returncode == 0, result.stderr
    from PyQt6.QtGui import QImage

    image = QImage(str(output_path))
    assert not image.isNull()
    assert (image.width(), image.height()) == (16, 12)
