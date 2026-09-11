import numpy as np

from waen.geometry import Box
from waen.pipeline.core import apply_masks

REGION = Box(100, 200, 400, 300)


def frame(value: int = 255) -> np.ndarray:
    return np.full((REGION.h, REGION.w, 3), value, dtype=np.uint8)


def test_no_masks_returns_an_identical_frame():
    original = frame()
    assert (apply_masks(original, REGION, []) == original).all()


def test_a_mask_inside_the_region_is_blacked_out():
    masked = apply_masks(frame(), REGION, [Box(150, 250, 100, 50)])
    assert (masked[50:100, 50:150] == 0).all()


def test_pixels_outside_the_mask_are_untouched():
    masked = apply_masks(frame(), REGION, [Box(150, 250, 100, 50)])
    assert (masked[0:40, 0:40] == 255).all()


def test_a_mask_outside_the_region_changes_nothing():
    original = frame()
    assert (apply_masks(original, REGION, [Box(1000, 1000, 50, 50)]) == original).all()


def test_a_mask_that_straddles_the_edge_is_clipped_not_crashed():
    masked = apply_masks(frame(), REGION, [Box(50, 150, 100, 100)])
    assert (masked[0:50, 0:50] == 0).all()
    assert (masked[100:, 100:] == 255).all()


def test_the_input_frame_is_not_modified_in_place():
    original = frame()
    copy = original.copy()
    apply_masks(original, REGION, [Box(150, 250, 100, 50)])
    assert (original == copy).all()


def test_several_masks_are_all_applied():
    masked = apply_masks(
        frame(), REGION, [Box(100, 200, 50, 50), Box(400, 400, 50, 50)]
    )
    assert (masked[0:50, 0:50] == 0).all()
    assert (masked[200:250, 300:350] == 0).all()
