"""Contracts for integrations with the operating system."""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class PlatformIntegration(Protocol):
    def make_dpi_aware(self) -> None:
        """Must be called before QApplication is constructed."""
        ...

    def exclude_from_capture(self, win_id: int) -> bool:
        """Exclude a window from screen capture, if supported."""
        ...

    def apply_overlay_styles(self, win_id: int) -> bool:
        """Apply styles that make an overlay click-through and non-activating."""
        ...

    def register_global_hotkeys(
        self, qapp, hotkeys: dict[str, str], callback: Callable[[str], None]
    ) -> bool:
        """Register system-wide hotkeys, if supported."""
        ...
