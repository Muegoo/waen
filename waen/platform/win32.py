"""Win32 integration through ctypes.

Task 10 supplies DPI awareness and hotkey parsing. Capture exclusion and global
hotkey registration are intentionally deferred to their dedicated tasks.
"""

from __future__ import annotations

import ctypes
import logging
from typing import Callable

logger = logging.getLogger(__name__)

PROCESS_PER_MONITOR_DPI_AWARE = 2

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
}


def parse_hotkey(combo: str) -> tuple[int, int] | None:
    """Return ``(modifiers, virtual_key)`` for a hotkey combo, or ``None``."""
    modifiers = 0
    virtual_key = None
    for part in combo.lower().replace(" ", "").split("+"):
        if not part:
            continue
        if part in _MODIFIERS:
            modifiers |= _MODIFIERS[part]
        elif len(part) == 1 and part.isalnum():
            virtual_key = ord(part.upper())
        elif part.startswith("f") and part[1:].isdigit():
            number = int(part[1:])
            if 1 <= number <= 24:
                virtual_key = 0x70 + number - 1
    if virtual_key is None:
        return None
    return modifiers | MOD_NOREPEAT, virtual_key


class Win32Platform:
    def __init__(self) -> None:
        self._hotkey_filter = None

    def make_dpi_aware(self) -> None:
        """Set per-monitor DPI awareness before constructing QApplication."""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
            return
        except (AttributeError, OSError) as exc:
            logger.debug("SetProcessDpiAwareness failed: %s", exc)
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError) as exc:
            logger.warning("Could not set DPI awareness; coordinates may be scaled: %s", exc)

    def exclude_from_capture(self, win_id: int) -> bool:
        return False  # Task 25

    def register_global_hotkeys(
        self, qapp, hotkeys: dict[str, str], callback: Callable[[str], None]
    ) -> bool:
        return False  # Task 28
