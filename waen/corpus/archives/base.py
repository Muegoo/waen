"""Interfaces for sources of files, independent of game archive type."""

from __future__ import annotations

from typing import Protocol


class ArchiveReader(Protocol):
    """A directory, CPK, zip, or other source of named files."""

    def list(self, pattern: str) -> list[str]: ...
    def read(self, name: str) -> bytes: ...
