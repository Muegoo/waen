"""Persona 5 Royal adapter for a directory of decompiled ``.msg`` files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..archives.base import ArchiveReader
from ..archives.plain_dir import PlainDirReader
from ..formats.atlus_msg import AtlusMsgFormat
from ..formats.base import TextFormat
from .base import TagRules


class Persona5RoyalAdapter:
    id = "persona5r"
    tag_rules = TagRules(
        pattern=r"\[(?P<name>[a-zA-Z_]+)(?P<args>[^\]]*)\]",
        page_break=frozenset({"w"}),
        newline=frozenset({"n"}),
        # Populate once the real-game player-name tag is identified in Phase 6a.
        variables={},
    )

    def detect(self, game_dir: Path) -> bool:
        return any(Path(game_dir).rglob("*.msg"))

    def sources(self, game_dir: Path) -> Iterator[tuple[ArchiveReader, TextFormat, str]]:
        yield PlainDirReader(game_dir), AtlusMsgFormat(), "**/*.msg"
