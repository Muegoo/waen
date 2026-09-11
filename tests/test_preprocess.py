import numpy as np
import pytest

from waen.ocr.preprocess import (
    PIPELINES,
    binarize,
    invert,
    scale_factor_of,
    to_gray,
    upscale,
)


def sample() -> np.ndarray:
    img = np.zeros((10, 20, 3), dtype=np.uint8)
    img[3:7, 5:15] = 255
    return img


def test_upscale_multiplies_both_dimensions():
    out = upscale(sample(), 3)
    assert out.shape == (30, 60, 3)


def test_upscale_by_one_returns_same_shape():
    img = sample()
    assert upscale(img, 1).shape == img.shape


def test_upscale_rejects_factor_below_one():
    with pytest.raises(ValueError):
        upscale(sample(), 0)


def test_to_gray_collapses_channels():
    assert to_gray(sample()).shape == (10, 20)


def test_binarize_output_has_only_two_values():
    out = binarize(sample())
    assert out.shape == (10, 20, 3)
    assert set(np.unique(out)).issubset({0, 255})


def test_invert_flips_black_and_white():
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    out = invert(img)
    assert (out == 255).all()


def test_invert_is_its_own_inverse():
    img = sample()
    assert (invert(invert(img)) == img).all()


def test_every_pipeline_returns_three_channel_uint8():
    img = sample()
    for name, fn in PIPELINES.items():
        out = fn(img)
        assert out.ndim == 3 and out.shape[2] == 3, name
        assert out.dtype == np.uint8, name


def test_scale_factor_matches_actual_output_size():
    img = sample()
    for name, fn in PIPELINES.items():
        out = fn(img)
        assert out.shape[0] == img.shape[0] * scale_factor_of(name), name


def test_scale_factor_of_unknown_name_raises():
    with pytest.raises(KeyError):
        scale_factor_of("nope")
