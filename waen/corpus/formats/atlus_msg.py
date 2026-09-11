"""Read ``.msg`` files decompiled from Atlus ``.bmd`` scripts.

The header syntax is based on synthetic AtlusScriptTools output and still needs
confirmation against decompiled game files during Phase 6a.
"""

from __future__ import annotations

import re
from typing import Iterator

from .base import RawMessage

_HEADER = re.compile(
    r"^\[(?P<kind>dlg|msg|sel)\s+(?P<name>\S+?)(?:\s+\[(?P<speaker>[^\]]*)\])?\]\s*$"
)
_END = "[e]"


class AtlusMsgFormat:
    """Decode dialogue and selection blocks from a decompiled ``.msg`` file."""

    extensions = (".msg",)

    def decode(self, data: bytes, name: str) -> Iterator[RawMessage]:
        text = data.decode("utf-8-sig", errors="replace")
        kind = msg_name = speaker = None
        body: list[str] = []

        def flush() -> Iterator[RawMessage]:
            if msg_name is None:
                return
            joined = "\n".join(body).strip()
            if not joined:
                return
            if kind == "sel":
                for index, part in enumerate(p.strip() for p in joined.split(_END) if p.strip()):
                    yield RawMessage(f"{msg_name}#{index}", None, part + _END, name)
            else:
                yield RawMessage(msg_name, speaker, joined, name)

        for line in text.splitlines():
            header = _HEADER.match(line)
            if header:
                yield from flush()
                kind = header.group("kind")
                msg_name = header.group("name")
                speaker = header.group("speaker") or None
                body = []
            elif msg_name is not None:
                body.append(line)
        yield from flush()
