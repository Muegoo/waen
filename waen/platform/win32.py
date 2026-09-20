"""Win32 integration through ctypes.

Task 10 supplies DPI awareness and hotkey parsing. Capture exclusion and global
hotkey registration are intentionally deferred to their dedicated tasks.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
from typing import Callable

logger = logging.getLogger(__name__)

PROCESS_PER_MONITOR_DPI_AWARE = 2

WDA_EXCLUDEFROMCAPTURE = 0x00000011

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312

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
        self._hotkey_qapp = None
        self._registered_ids: list[int] = []

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
        """Exclude a window from both GDI and DXGI screen capture if supported."""
        if not win_id:
            return False
        try:
            return bool(
                ctypes.windll.user32.SetWindowDisplayAffinity(
                    ctypes.wintypes.HWND(win_id), WDA_EXCLUDEFROMCAPTURE
                )
            )
        except (AttributeError, OSError) as exc:
            logger.info("SetWindowDisplayAffinity is unavailable: %s", exc)
            return False

    def apply_overlay_styles(self, win_id: int) -> bool:
        """Make an overlay layered, click-through, and non-activating."""
        if not win_id:
            return False
        try:
            user32 = ctypes.windll.user32
            user32.GetWindowLongPtrW.restype = ctypes.c_longlong
            user32.SetWindowLongPtrW.restype = ctypes.c_longlong
            user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
            user32.SetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
            handle = ctypes.wintypes.HWND(win_id)
            current = user32.GetWindowLongPtrW(handle, GWL_EXSTYLE)
            wanted = current | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            user32.SetWindowLongPtrW(handle, GWL_EXSTYLE, wanted)
            return bool(user32.GetWindowLongPtrW(handle, GWL_EXSTYLE) & WS_EX_TRANSPARENT)
        except (AttributeError, OSError) as exc:
            logger.info("Could not set overlay window styles: %s", exc)
            return False

    def register_global_hotkeys(
        self, qapp, hotkeys: dict[str, str], callback: Callable[[str], None]
    ) -> bool:
        """Register hotkeys which work even while another app has focus.

        ``RegisterHotKey`` sends ``WM_HOTKEY`` to this thread's message queue,
        so a Qt native event filter is used instead of focus-bound shortcuts.
        """
        from PyQt6.QtCore import QAbstractNativeEventFilter

        if qapp is None:
            logger.warning("Cannot register global hotkeys without a QApplication")
            return False

        self.unregister_global_hotkeys()
        user32 = ctypes.windll.user32
        registered: dict[int, str] = {}
        next_id = 1
        for name, combo in hotkeys.items():
            parsed = parse_hotkey(combo)
            if parsed is None:
                logger.warning("Cannot parse hotkey; skipping %s = %r", name, combo)
                continue
            modifiers, virtual_key = parsed
            if user32.RegisterHotKey(None, next_id, modifiers, virtual_key):
                registered[next_id] = name
                next_id += 1
            else:
                logger.warning(
                    "Could not register %s (%s); it may be reserved by another program",
                    name,
                    combo,
                )

        if not registered:
            return False

        class _HotkeyFilter(QAbstractNativeEventFilter):
            def nativeEventFilter(self, event_type, message):
                if event_type == b"windows_generic_MSG":
                    msg = ctypes.wintypes.MSG.from_address(int(message))
                    if msg.message == WM_HOTKEY and msg.wParam in registered:
                        try:
                            callback(registered[msg.wParam])
                        except Exception:
                            logger.exception("Global hotkey callback failed")
                return False, 0

        self._hotkey_filter = _HotkeyFilter()
        self._hotkey_qapp = qapp
        self._registered_ids = list(registered)
        try:
            qapp.installNativeEventFilter(self._hotkey_filter)
        except Exception:
            logger.exception("Could not install the global-hotkey event filter")
            self.unregister_global_hotkeys()
            return False
        return True

    def unregister_global_hotkeys(self) -> None:
        """Release all hotkeys held by this platform instance."""
        event_filter = self._hotkey_filter
        qapp = self._hotkey_qapp
        if event_filter is not None and qapp is not None:
            try:
                qapp.removeNativeEventFilter(event_filter)
            except Exception:
                logger.debug("Could not remove global-hotkey event filter", exc_info=True)

        for hotkey_id in self._registered_ids:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
            except (AttributeError, OSError) as exc:
                logger.debug("UnregisterHotKey failed: %s", exc)
        self._registered_ids = []
        self._hotkey_filter = None
        self._hotkey_qapp = None
