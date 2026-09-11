import numpy as np
import pytest

from waen.capture.base import CaptureBackend
from waen.capture.factory import create_backend, is_usable
from waen.geometry import Box


class FakeBackend:
    name = "fake"

    def __init__(self, frames):
        self._frames = list(frames)
        self.closed = False

    def grab(self, box: Box):
        return self._frames.pop(0) if self._frames else None

    def close(self):
        self.closed = True


def black(h=32, w=32):
    return np.zeros((h, w, 3), dtype=np.uint8)


def bright(h=32, w=32):
    return np.full((h, w, 3), 128, dtype=np.uint8)


def test_is_usable_accepts_a_backend_returning_a_normal_frame():
    assert is_usable(FakeBackend([bright()])) is True


def test_is_usable_rejects_a_backend_that_only_returns_black():
    assert is_usable(FakeBackend([black(), black(), black(), black(), black()])) is False


def test_is_usable_accepts_a_backend_that_returns_none_then_a_frame():
    assert is_usable(FakeBackend([None, None, bright()])) is True


def test_is_usable_rejects_a_backend_that_raises():
    class Exploding:
        name = "boom"

        def grab(self, box):
            raise RuntimeError("no device")

        def close(self):
            pass

    assert is_usable(Exploding()) is False


def test_explicit_mss_choice_is_honoured():
    assert create_backend("mss").name == "mss"


def test_auto_returns_something_that_satisfies_the_protocol():
    backend = create_backend("auto")
    try:
        assert isinstance(backend, CaptureBackend)
        assert backend.name in {"dxgi", "mss"}
    finally:
        backend.close()


def test_unknown_preference_raises_value_error():
    with pytest.raises(ValueError):
        create_backend("gdi")
