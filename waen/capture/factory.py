"""Select a capture backend by probing for a non-black real frame."""

from __future__ import annotations

import logging

import numpy as np

from ..geometry import Box
from .base import CaptureBackend
from .dxgi_backend import DxgiCapture
from .mss_backend import MssCapture

logger = logging.getLogger(__name__)

VALID_PREFERENCES = ("auto", "dxgi", "mss")
PROBE_BOX = Box(0, 0, 64, 64)
PROBE_ATTEMPTS = 5
BLACK_THRESHOLD = 1.0


def is_usable(backend: CaptureBackend, probe: Box | None = None) -> bool:
    """Return whether a backend yields a non-black frame within five attempts."""
    region = probe or PROBE_BOX
    try:
        for _ in range(PROBE_ATTEMPTS):
            frame = backend.grab(region)
            if frame is None:
                continue
            if float(np.mean(frame)) > BLACK_THRESHOLD:
                return True
        return False
    except Exception as exc:
        logger.info("backend %s is unusable: %s", getattr(backend, "name", "?"), exc)
        return False


def create_backend(preference: str = "auto") -> CaptureBackend:
    """Construct the requested backend, or select a verified automatic choice."""
    if preference not in VALID_PREFERENCES:
        raise ValueError(
            f"Unknown capture_backend {preference!r}; expected one of {VALID_PREFERENCES}"
        )

    if preference == "mss":
        return MssCapture()
    if preference == "dxgi":
        return DxgiCapture()

    if DxgiCapture.is_available():
        candidate = DxgiCapture()
        if is_usable(candidate):
            logger.info("capture backend: dxgi")
            return candidate
        candidate.close()
        logger.info("DXGI returned black or unavailable frames; falling back to mss")

    logger.info("capture backend: mss")
    return MssCapture()
