"""Determine where translations should be drawn.

The core user requirement is that a translation appears above the original
text while leaving the original visible.  Covering any original-text box is a
placement failure, including another block's box.

Text measurement is injected so this module has no Qt dependency and remains
fully testable.
"""

from __future__ import annotations

from typing import Callable, Sequence

from ..config import OverlayConfig
from ..geometry import Box
from ..models import OverlayItem, TranslatedBlock

Measure = Callable[[str, int, int], tuple[int, int]]

MIN_PANEL_WIDTH = 80


def clamp_horizontally(box: Box, screen: Box) -> Box:
    x = box.x
    if box.right > screen.right:
        x = screen.right - box.w
    if x < screen.x:
        x = screen.x
    return Box(x, box.y, box.w, box.h)


def collides(box: Box, others: Sequence[Box]) -> bool:
    return any(box.intersection(other) is not None for other in others)


def _fits_vertically(box: Box, screen: Box) -> bool:
    return box.y >= screen.y and box.bottom <= screen.bottom


def layout_blocks(
    translated: Sequence[TranslatedBlock],
    screen: Box,
    config: OverlayConfig,
    measure: Measure,
) -> list[OverlayItem]:
    ordered = sorted(translated, key=lambda t: (t.block.box.y, t.block.box.x))
    anchors = [item.block.box for item in ordered]
    reserved: list[Box] = []
    items: list[OverlayItem] = []

    for index, entry in enumerate(ordered):
        anchor = entry.block.box
        forbidden = reserved + [a for position, a in enumerate(anchors) if position != index]
        max_width = max(anchor.w, MIN_PANEL_WIDTH)

        placed: tuple[Box, int] | None = None
        for font_size in range(config.font_size, config.min_font_size - 1, -1):
            width, height = measure(entry.translated, font_size, max_width)
            above = Box(anchor.x, anchor.y - config.gap_px - height, width, height)
            below = Box(anchor.x, anchor.bottom + config.gap_px, width, height)
            for candidate in (above, below):
                fitted = clamp_horizontally(candidate, screen)
                if not _fits_vertically(fitted, screen):
                    continue
                if collides(fitted, forbidden):
                    continue
                placed = (fitted, font_size)
                break
            if placed is not None:
                break

        if placed is None:
            width, height = measure(entry.translated, config.min_font_size, max_width)
            fallback = clamp_horizontally(
                Box(anchor.x, anchor.y, width, height), screen
            )
            placed = (fallback, config.min_font_size)

        draw, font_size = placed
        reserved.append(draw)
        items.append(
            OverlayItem(
                source_text=entry.block.source_text,
                translated=entry.translated,
                anchor=anchor,
                draw=draw,
                font_size=font_size,
            )
        )
    return items
