"""GDI/BitBlt screen capture using mss, the portable fallback backend."""

from __future__ import annotations

import numpy as np

from ..geometry import Box

MIN_SIZE = 8


class MssCapture:
    name = "mss"

    def __init__(self) -> None:
        self._sct = None

    def _ensure(self):
        if self._sct is None:
            import mss

            self._sct = mss.MSS()
        return self._sct

    def grab(self, box: Box) -> np.ndarray | None:
        if not box.is_valid(MIN_SIZE):
            raise ValueError(f"Capture box is too small: {box}")
        shot = self._ensure().grab(
            {"left": box.x, "top": box.y, "width": box.w, "height": box.h}
        )
        frame = np.asarray(shot, dtype=np.uint8)
        return np.ascontiguousarray(frame[:, :, :3])  # BGRA -> BGR

    def close(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None
