import numpy as np
import pytest
from PyQt6.QtGui import QImage

from waen.config import OverlayConfig
from waen.geometry import Box
from waen.models import OverlayItem
from waen.ui.overlay import OverlayWindow, make_qt_measure

CONFIG = OverlayConfig(font_size=16, min_font_size=11, gap_px=4)


def item(draw: Box, anchor: Box | None = None) -> OverlayItem:
    return OverlayItem(
        source_text="Hello there",
        translated="สวัสดีชาวโลก",
        anchor=anchor or Box(draw.x, draw.bottom + 4, draw.w, 24),
        draw=draw,
        font_size=16,
    )


def painted_alpha(window: OverlayWindow, width: int, height: int) -> np.ndarray:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    window.render(image)
    pointer = image.constBits()
    pointer.setsize(image.sizeInBytes())
    stride = image.bytesPerLine() // 4
    buffer = np.frombuffer(pointer, dtype=np.uint8).reshape(height, stride, 4)
    # The QImage owns ``pointer`` and is destroyed when this helper returns.
    return buffer[:, :width, 3].copy()


def test_measure_grows_with_font_size(qt_app):
    measure = make_qt_measure("Tahoma")
    small_w, small_h = measure("ทดสอบข้อความ", 12, 1000)
    large_w, large_h = measure("ทดสอบข้อความ", 24, 1000)
    assert large_w > small_w
    assert large_h > small_h


def test_measure_wraps_when_the_width_is_tight(qt_app):
    measure = make_qt_measure("Tahoma")
    text = "ยินดีต้อนรับสู่หมู่บ้านแห่งนี้ นักรบผู้กล้าหาญ"
    _, wide_h = measure(text, 16, 2000)
    _, narrow_h = measure(text, 16, 120)
    assert narrow_h > wide_h


def test_measure_never_exceeds_the_max_width(qt_app):
    measure = make_qt_measure("Tahoma")
    width, _ = measure("ข้อความยาวมากมากมากมากมากมาก", 16, 150)
    assert width <= 150


def test_window_is_click_through_and_always_on_top(qt_app):
    from PyQt6.QtCore import Qt

    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    flags = window.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowTransparentForInput
    assert window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_nothing_is_painted_before_any_item_is_set(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    assert painted_alpha(window, 400, 200).max() == 0


def test_an_item_paints_pixels_inside_its_draw_box(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    window.set_items([item(Box(50, 50, 200, 30))])
    alpha = painted_alpha(window, 400, 200)
    assert alpha[50:80, 50:250].max() > 0


def test_nothing_is_painted_outside_the_draw_box(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    window.set_items([item(Box(50, 50, 100, 30))])
    alpha = painted_alpha(window, 400, 200)
    assert alpha[150:200, :].max() == 0


def test_set_hidden_stops_all_painting(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    window.set_items([item(Box(50, 50, 200, 30))])
    window.set_hidden(True)
    assert painted_alpha(window, 400, 200).max() == 0


def test_unhiding_paints_again(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    window.set_items([item(Box(50, 50, 200, 30))])
    window.set_hidden(True)
    window.set_hidden(False)
    assert painted_alpha(window, 400, 200).max() > 0


def test_clear_removes_everything(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    window.set_items([item(Box(50, 50, 200, 30))])
    window.clear()
    assert painted_alpha(window, 400, 200).max() == 0
    assert window.occupied_boxes() == []


def test_occupied_boxes_reports_physical_coordinates(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 1.0, CONFIG)
    draw = Box(50, 50, 200, 30)
    window.set_items([item(draw)])
    assert window.occupied_boxes() == [draw]


def test_positions_are_converted_to_logical_coordinates_when_dpi_is_scaled(qt_app):
    window = OverlayWindow(Box(0, 0, 400, 200), 2.0, CONFIG)
    window.set_items([item(Box(200, 100, 200, 40))])
    alpha = painted_alpha(window, 400, 200)
    assert alpha[50:70, 100:200].max() > 0
    assert alpha[150:200, :].max() == 0
