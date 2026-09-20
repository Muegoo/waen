"""DXGI Desktop Duplication capture through bettercam."""

from __future__ import annotations

import logging
import subprocess
import sys

import numpy as np

from ..geometry import Box

logger = logging.getLogger(__name__)

MIN_SIZE = 8


class DxgiCapture:
    name = "dxgi"

    def __init__(self, output_idx: int = 0, origin: tuple[int, int] = (0, 0)) -> None:
        self._output_idx = output_idx
        self._origin = origin
        self._camera = None

    @classmethod
    def is_available(cls) -> bool:
        """Whether bettercam can initialise DXGI Desktop Duplication here."""
        if getattr(sys, "frozen", False):
            # A PyInstaller executable cannot invoke itself with ``-c``. Probe
            # in-process instead; any bettercam cleanup noise is harmless here.
            try:
                import bettercam

                camera = bettercam.create(output_idx=0, output_color="BGR")
                if camera is None:
                    return False
                camera.release()
                return True
            except Exception as exc:
                logger.info("bettercam unavailable: %s", exc)
                return False

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import bettercam\n"
                        "camera = bettercam.create(output_idx=0, output_color='BGR')\n"
                        "if camera is None: raise RuntimeError('no DXGI camera')\n"
                        "camera.release()\n"
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.info("bettercam unavailable: %s", exc)
            return False

    def _ensure(self):
        if self._camera is None:
            import bettercam

            self._camera = bettercam.create(
                output_idx=self._output_idx, output_color="BGR"
            )
            if self._camera is None:
                raise RuntimeError(
                    f"Could not create DXGI camera for output {self._output_idx}"
                )
        return self._camera

    def grab(self, box: Box) -> np.ndarray | None:
        if not box.is_valid(MIN_SIZE):
            raise ValueError(f"Capture box is too small: {box}")

        camera = self._ensure()
        left = box.x - self._origin[0]
        top = box.y - self._origin[1]
        if left < 0 or top < 0:
            raise ValueError(
                f"Capture box {box} is outside DXGI output origin={self._origin}; use mss"
            )

        frame = camera.grab(region=(left, top, left + box.w, top + box.h))
        if frame is None:
            return None
        return np.ascontiguousarray(frame[:, :, :3])

    def close(self) -> None:
        if self._camera is not None:
            try:
                self._camera.release()
            except Exception as exc:
                logger.debug("release camera failed: %s", exc)
            self._camera = None
