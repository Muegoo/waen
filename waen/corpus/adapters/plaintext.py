"""Adapter for games that already have a plaintext script dump."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..archives.base import ArchiveReader
from ..archives.plain_dir import PlainDirReader
from ..formats.base import TextFormat
from ..formats.plaintext import PlaintextFormat
from .base import TagRules


class PlaintextAdapter:
    id = "plaintext"
    tag_rules = TagRules.none()

    def detect(self, game_dir: Path) -> bool:
        return any(
            path.suffix.lower() in PlaintextFormat.extensions
            for path in Path(game_dir).rglob("*")
            if path.is_file()
        )

    def sources(self, game_dir: Path) -> Iterator[tuple[ArchiveReader, TextFormat, str]]:
        yield PlainDirReader(game_dir), PlaintextFormat(), "**/*"
