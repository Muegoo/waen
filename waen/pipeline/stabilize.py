"""Emit text for translation only after it has stopped changing.

The caller supplies time explicitly so the state machine stays deterministic
and testable.  Blocks are matched across frames by bounding-box IoU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..geometry import Box
from ..models import TextBlock


@dataclass
class StabilizeConfig:
    stable_frames: int = 2
    min_stable_ms: int = 250
    match_iou: float = 0.5
    min_chars: int = 2


@dataclass
class _Tracked:
    text: str
    box: Box
    first_seen_ms: int
    repeats: int
    emitted: str | None = None


class Stabilizer:
    def __init__(self, config: StabilizeConfig | None = None) -> None:
        self.config = config or StabilizeConfig()
        self._tracked: list[_Tracked] = []

    def reset(self) -> None:
        self._tracked = []

    @property
    def pending(self) -> bool:
        """Whether any currently visible text still needs another OCR pass."""
        return any(entry.emitted != entry.text for entry in self._tracked)

    def _match(self, box: Box, pool: list[_Tracked]) -> _Tracked | None:
        best: _Tracked | None = None
        best_iou = self.config.match_iou
        for entry in pool:
            score = entry.box.iou(box)
            if score >= best_iou:
                best, best_iou = entry, score
        return best

    def feed(self, blocks: Sequence[TextBlock], now_ms: int) -> list[TextBlock]:
        previous = self._tracked
        current: list[_Tracked] = []
        stable: list[TextBlock] = []

        for block in blocks:
            entry = self._match(block.box, previous)
            if entry is None:
                current.append(
                    _Tracked(
                        text=block.source_text,
                        box=block.box,
                        first_seen_ms=now_ms,
                        repeats=1,
                    )
                )
                continue

            previous.remove(entry)
            if block.source_text == entry.text:
                entry.repeats += 1
            else:
                entry.text = block.source_text
                entry.repeats = 1
                entry.first_seen_ms = now_ms
                entry.emitted = None
            entry.box = block.box
            current.append(entry)

            if self._is_stable(entry, now_ms):
                entry.emitted = entry.text
                stable.append(block)

        self._tracked = current
        return stable

    def _is_stable(self, entry: _Tracked, now_ms: int) -> bool:
        if entry.emitted == entry.text:
            return False
        # The initial sighting is not yet a stable frame.  ``stable_frames``
        # therefore counts matching confirmations after it, so the default of
        # two emits on the third identical observation.
        if entry.repeats <= self.config.stable_frames:
            return False
        if now_ms - entry.first_seen_ms < self.config.min_stable_ms:
            return False
        if len(entry.text.replace(" ", "")) < self.config.min_chars:
            return False
        return True
