"""Connect archive, format, and adapter layers to write/read source JSONL."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Mapping

from .adapters.base import GameAdapter, split_pages
from .models import ScriptEntry

logger = logging.getLogger(__name__)


def extract_entries(
    adapter: GameAdapter, game_dir: Path, values: Mapping[str, str]
) -> Iterator[ScriptEntry]:
    order_in_scene: dict[str, int] = defaultdict(int)
    seen: set[str] = set()

    for reader, fmt, pattern in adapter.sources(Path(game_dir)):
        for name in reader.list(pattern):
            if name in seen:
                continue
            seen.add(name)
            try:
                data = reader.read(name)
            except OSError as exc:
                logger.warning("อ่าน %s ไม่ได้: %s", name, exc)
                continue
            for message in fmt.decode(data, name):
                for page_no, page in enumerate(split_pages(message.text, adapter.tag_rules, values)):
                    yield ScriptEntry(
                        id=f"{adapter.id}:{name}:{message.name}:{page_no}",
                        game=adapter.id,
                        scene=name,
                        order=order_in_scene[name],
                        speaker=message.speaker,
                        text_raw=message.text,
                        text=page,
                    )
                    order_in_scene[name] += 1


def write_jsonl(entries: Iterable[ScriptEntry], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[ScriptEntry]:
    entries = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                entries.append(ScriptEntry.from_dict(json.loads(line)))
    return entries


def corpus_stats(entries: Iterable[ScriptEntry]) -> dict:
    entries = list(entries)
    return {
        "entries": len(entries),
        "scenes": len({entry.scene for entry in entries}),
        "chars": sum(len(entry.text) for entry in entries),
        "unique_texts": len({entry.text for entry in entries}),
    }
