"""Immutable data objects that move through the processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Literal, Sequence

from .geometry import Box

BlockKind = Literal["paragraph", "standalone"]


@dataclass(frozen=True)
class TextLine:
    text: str
    box: Box
    confidence: float


@dataclass(frozen=True)
class TextBlock:
    lines: tuple[TextLine, ...]
    source_text: str
    box: Box
    kind: BlockKind

    @classmethod
    def from_lines(
        cls, lines: Sequence[TextLine], source_text: str, kind: BlockKind
    ) -> "TextBlock":
        if not lines:
            raise ValueError("TextBlock needs at least one line")
        box = reduce(lambda a, b: a.union(b), (line.box for line in lines))
        return cls(lines=tuple(lines), source_text=source_text, box=box, kind=kind)


@dataclass(frozen=True)
class OverlayItem:
    source_text: str
    translated: str
    anchor: Box
    draw: Box
    font_size: int


@dataclass(frozen=True)
class TranslatedBlock:
    block: TextBlock
    translated: str
    glossary_applied: bool
