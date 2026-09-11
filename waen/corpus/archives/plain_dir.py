"""Archive reader for an ordinary directory."""

from __future__ import annotations

from pathlib import Path


class PlainDirReader:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def list(self, pattern: str) -> list[str]:
        return sorted(
            path.relative_to(self.root).as_posix()
            for path in self.root.glob(pattern)
            if path.is_file()
        )

    def read(self, name: str) -> bytes:
        return (self.root / name).read_bytes()
