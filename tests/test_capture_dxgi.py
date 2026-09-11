import numpy as np
import pytest

from waen.capture.base import CaptureBackend
from waen.capture.dxgi_backend import DxgiCapture
from waen.geometry import Box

pytestmark = pytest.mark.skipif(
    not DxgiCapture.is_available(), reason="bettercam is unavailable on this machine"
)


@pytest.fixture
def backend():
    capture = DxgiCapture()
    yield capture
    capture.close()


def test_satisfies_the_protocol(backend):
    assert isinstance(backend, CaptureBackend)
    assert backend.name == "dxgi"


def test_first_grab_returns_bgr_uint8_of_the_requested_size(backend):
    frame = backend.grab(Box(0, 0, 64, 48))
    assert frame is not None, "The first frame must always be available"
    assert frame.shape == (48, 64, 3)
    assert frame.dtype == np.uint8


def test_none_means_no_new_frame_not_an_error(backend):
    backend.grab(Box(0, 0, 64, 48))
    for _ in range(5):
        frame = backend.grab(Box(0, 0, 64, 48))
        assert frame is None or frame.shape == (48, 64, 3)


def test_tiny_box_is_rejected_loudly(backend):
    with pytest.raises(ValueError):
        backend.grab(Box(0, 0, 2, 2))


def test_box_outside_the_primary_monitor_is_rejected_so_the_factory_can_fall_back(backend):
    with pytest.raises(ValueError):
        backend.grab(Box(-5000, -5000, 100, 100))


def test_close_can_be_called_twice(backend):
    backend.close()
    backend.close()
