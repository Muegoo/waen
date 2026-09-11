import pytest

from waen.geometry import Box, to_logical, to_physical


def test_right_and_bottom_are_exclusive_edges():
    b = Box(10, 20, 30, 40)
    assert b.right == 40
    assert b.bottom == 60


def test_union_covers_both_boxes():
    a = Box(10, 10, 20, 5)
    b = Box(15, 20, 30, 5)
    assert a.union(b) == Box(10, 10, 35, 15)


def test_intersection_returns_overlap():
    a = Box(0, 0, 100, 100)
    b = Box(50, 50, 100, 100)
    assert a.intersection(b) == Box(50, 50, 50, 50)


def test_intersection_returns_none_when_disjoint():
    assert Box(0, 0, 10, 10).intersection(Box(100, 100, 10, 10)) is None


def test_iou_of_identical_boxes_is_one():
    b = Box(5, 5, 20, 20)
    assert b.iou(b) == pytest.approx(1.0)


def test_iou_of_disjoint_boxes_is_zero():
    assert Box(0, 0, 10, 10).iou(Box(50, 50, 10, 10)) == 0.0


def test_iou_of_half_overlap():
    a = Box(0, 0, 10, 10)
    b = Box(5, 0, 10, 10)
    assert a.iou(b) == pytest.approx(50 / 150)


def test_offset_by_moves_origin_only():
    assert Box(10, 10, 5, 5).offset_by(100, 200) == Box(110, 210, 5, 5)


def test_is_valid_rejects_tiny_boxes():
    assert Box(0, 0, 20, 20).is_valid()
    assert not Box(0, 0, 4, 20).is_valid()
    assert not Box(0, 0, 20, 4).is_valid()


def test_to_physical_scales_and_rounds():
    assert to_physical(Box(10, 20, 30, 40), 1.5) == Box(15, 30, 45, 60)


def test_to_physical_at_scale_one_is_identity():
    b = Box(3, 7, 11, 13)
    assert to_physical(b, 1.0) == b


def test_to_physical_keeps_negative_origin_of_left_hand_monitor():
    assert to_physical(Box(-1920, 0, 1920, 1080), 1.0) == Box(-1920, 0, 1920, 1080)


def test_negative_origin_scales_correctly():
    assert to_physical(Box(-800, -600, 400, 300), 2.0) == Box(-1600, -1200, 800, 600)


def test_round_trip_is_stable_at_125_percent():
    b = Box(0, 0, 1600, 900)
    assert to_logical(to_physical(b, 1.25), 1.25) == b


def test_round_trip_is_stable_at_150_percent():
    b = Box(100, 200, 1200, 600)
    assert to_logical(to_physical(b, 1.5), 1.5) == b


def test_width_never_collapses_to_zero():
    assert to_physical(Box(0, 0, 1, 1), 0.4).w >= 1
    assert to_physical(Box(0, 0, 1, 1), 0.4).h >= 1
