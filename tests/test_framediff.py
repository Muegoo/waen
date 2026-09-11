import numpy as np

from waen.pipeline.framediff import FrameDiffer


def frame(value: int, h: int = 64, w: int = 64) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def test_first_frame_always_counts_as_changed():
    assert FrameDiffer().changed(frame(0)) is True


def test_identical_frames_are_not_changed():
    differ = FrameDiffer()
    differ.changed(frame(50))
    assert differ.changed(frame(50)) is False


def test_a_big_difference_is_detected():
    differ = FrameDiffer(threshold=4.0)
    differ.changed(frame(0))
    assert differ.changed(frame(200)) is True


def test_a_difference_below_the_threshold_is_ignored():
    differ = FrameDiffer(threshold=4.0)
    differ.changed(frame(100))
    assert differ.changed(frame(102)) is False


def test_a_resized_frame_counts_as_changed():
    differ = FrameDiffer()
    differ.changed(frame(100, h=64, w=64))
    assert differ.changed(frame(100, h=32, w=32)) is True


def test_reset_makes_the_next_frame_count_as_changed():
    differ = FrameDiffer()
    differ.changed(frame(50))
    assert differ.changed(frame(50)) is False
    differ.reset()
    assert differ.changed(frame(50)) is True
