"""Select a platform integration for the current operating system."""

from __future__ import annotations

import sys

from .base import PlatformIntegration


def get_platform() -> PlatformIntegration:
    if sys.platform == "win32":
        from .win32 import Win32Platform

        return Win32Platform()
    from .noop import NoopPlatform

    return NoopPlatform()


__all__ = ["PlatformIntegration", "get_platform"]
