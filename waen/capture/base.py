"""Screen-capture backend contract.

Every backend returns a BGR uint8 frame with shape ``(height, width, 3)``.
``None`` is reserved exclusively for a backend that has no new frame; errors
must be surfaced to callers instead.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from ..geometry import Box


@runtime_checkable
class CaptureBackend(Protocol):
    name: str

    def grab(self, box: Box) -> np.ndarray | None: ...

    def close(self) -> None: ...
