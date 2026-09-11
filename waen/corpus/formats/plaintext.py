"""Common reader for existing plaintext script dumps."""

from __future__ import annotations

import csv
import io
import json
from pathlib import PurePosixPath
from typing import Iterator

from .base import RawMessage


def _row(obj: dict, index: int, source: str) -> RawMessage | None:
    text = obj.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    speaker = obj.get("speaker")
    return RawMessage(
        name=str(obj.get("id") or index),
        speaker=str(speaker) if speaker else None,
        text=text,
        source=source,
    )


class PlaintextFormat:
    extensions = (".txt", ".jsonl", ".json", ".csv")

    def decode(self, data: bytes, name: str) -> Iterator[RawMessage]:
        ext = PurePosixPath(name).suffix.lower()
        text = data.decode("utf-8-sig", errors="replace")

        if ext == ".txt":
            for index, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    yield RawMessage(name=f"L{index}", speaker=None, text=line.strip(), source=name)

        elif ext == ".jsonl":
            for index, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and (message := _row(obj, index, name)):
                    yield message

        elif ext == ".json":
            try:
                rows = json.loads(text)
            except json.JSONDecodeError:
                return
            if isinstance(rows, list):
                for index, obj in enumerate(rows, start=1):
                    if isinstance(obj, dict) and (message := _row(obj, index, name)):
                        yield message

        elif ext == ".csv":
            for index, obj in enumerate(csv.DictReader(io.StringIO(text)), start=1):
                if message := _row(obj, index, name):
                    yield message


FORMATS_BY_EXT: dict[str, PlaintextFormat] = {
    ext: PlaintextFormat() for ext in PlaintextFormat.extensions
}
