"""Game-specific rules for locating and rendering extracted script messages."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Mapping, Protocol

from ..archives.base import ArchiveReader
from ..formats.base import TextFormat

logger = logging.getLogger(__name__)

_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class TagRules:
    """Rules for the tags a particular game's script format embeds in text."""

    pattern: str
    page_break: frozenset[str] = frozenset()
    newline: frozenset[str] = frozenset()
    variables: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def none(cls) -> "TagRules":
        return cls(pattern="")


def split_pages(text_raw: str, rules: TagRules, values: Mapping[str, str]) -> list[str]:
    """Remove/replace tags and split text into the separately visible pages."""
    if not rules.pattern:
        return [_clean(text_raw)] if _clean(text_raw) else []

    regex = re.compile(rules.pattern)
    pages: list[str] = []
    buffer: list[str] = []
    cursor = 0

    for match in regex.finditer(text_raw):
        buffer.append(text_raw[cursor : match.start()])
        cursor = match.end()
        name = match.group("name")

        if name in rules.page_break:
            pages.append("".join(buffer))
            buffer = []
        elif name in rules.newline:
            buffer.append(" ")
        elif name in rules.variables:
            key = rules.variables[name]
            if key in values:
                buffer.append(values[key])
            else:
                logger.warning("ไม่ได้ให้ค่า --var %s=... ปล่อย tag %s ไว้ตามเดิม", key, match.group(0))
                buffer.append(match.group(0))

    buffer.append(text_raw[cursor:])
    pages.append("".join(buffer))
    return [page for page in (_clean(page) for page in pages) if page]


def _clean(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


class GameAdapter(Protocol):
    id: str
    tag_rules: TagRules

    def detect(self, game_dir: Path) -> bool: ...
    def sources(self, game_dir: Path) -> Iterator[tuple[ArchiveReader, TextFormat, str]]: ...
