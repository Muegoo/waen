"""Interfaces for decoding script text formats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class RawMessage:
    """An undecorated message whose game-specific tags are still intact."""

    name: str
    speaker: str | None
    text: str
    source: str


class TextFormat(Protocol):
    extensions: tuple[str, ...]

    def decode(self, data: bytes, name: str) -> Iterator[RawMessage]: ...
