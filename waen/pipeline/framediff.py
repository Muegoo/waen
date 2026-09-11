"""Cheap frame-difference gate for avoiding redundant OCR work.

Frames are stride-downsampled rather than averaged, then compared by their
mean absolute grayscale pixel difference.  This is deliberately a coarse,
fast signal rather than a visual similarity metric.
"""

from __future__ import annotations

import numpy as np


class FrameDiffer:
    def __init__(self, threshold: float = 4.0, downsample: int = 4) -> None:
        self.threshold = float(threshold)
        self.downsample = max(1, int(downsample))
        self._previous: np.ndarray | None = None

    def reset(self) -> None:
        self._previous = None

    def changed(self, frame: np.ndarray) -> bool:
        step = self.downsample
        small = frame[::step, ::step].astype(np.float32)
        if small.ndim == 3:
            small = small.mean(axis=2)

        previous, self._previous = self._previous, small
        if previous is None or previous.shape != small.shape:
            return True
        return float(np.mean(np.abs(small - previous))) > self.threshold
