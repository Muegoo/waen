"""Safe no-op platform integration for non-Windows systems."""

from __future__ import annotations

from typing import Callable


class NoopPlatform:
    def make_dpi_aware(self) -> None:
        return None

    def exclude_from_capture(self, win_id: int) -> bool:
        return False

    def apply_overlay_styles(self, win_id: int) -> bool:
        return False

    def register_global_hotkeys(
        self, qapp, hotkeys: dict[str, str], callback: Callable[[str], None]
    ) -> bool:
        return False

    def unregister_global_hotkeys(self) -> None:
        return None
