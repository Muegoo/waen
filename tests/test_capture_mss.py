import numpy as np
import pytest
from mss.exception import ScreenShotError

from waen.capture.base import CaptureBackend
from waen.capture.mss_backend import MssCapture
from waen.geometry import Box


@pytest.fixture
def backend():
    capture = MssCapture()
    yield capture
    capture.close()


@pytest.fixture
def screen_backend(backend):
    try:
        backend.grab(Box(0, 0, 8, 8))
    except ScreenShotError as exc:
        pytest.skip(f"Desktop GDI capture is unavailable in this session: {exc}")
    return backend


def test_satisfies_the_protocol(backend):
    assert isinstance(backend, CaptureBackend)
    assert backend.name == "mss"


def test_grab_returns_bgr_uint8_of_the_requested_size(screen_backend):
    frame = screen_backend.grab(Box(0, 0, 64, 48))
    assert frame is not None
    assert frame.shape == (48, 64, 3)
    assert frame.dtype == np.uint8


def test_grab_is_repeatable_on_one_instance(screen_backend):
    first = screen_backend.grab(Box(0, 0, 32, 32))
    second = screen_backend.grab(Box(0, 0, 32, 32))
    assert first is not None and second is not None
    assert first.shape == second.shape


def test_grab_of_a_different_size_works_without_recreating(screen_backend):
    assert screen_backend.grab(Box(0, 0, 32, 32)).shape == (32, 32, 3)
    assert screen_backend.grab(Box(0, 0, 100, 20)).shape == (20, 100, 3)


def test_tiny_box_is_rejected_loudly(backend):
    with pytest.raises(ValueError):
        backend.grab(Box(0, 0, 2, 2))


def test_close_can_be_called_twice(backend):
    backend.close()
    backend.close()
