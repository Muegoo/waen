"""Translate an extracted corpus scene by scene with an atomic checkpoint."""

from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Iterable, Mapping, Protocol, Sequence

from ..translate.glossary import DEFAULT_TEMPLATES, Glossary, translate_with_glossary
from .models import ScriptEntry

logger = logging.getLogger(__name__)


class CorpusTranslator(Protocol):
    """A corpus backend receives each complete scene, including speakers."""

    def translate_scene(self, entries: Sequence[ScriptEntry]) -> list[str | None]: ...


class LineByLineCorpusTranslator:
    """Translate each entry through the same glossary path used at runtime."""

    def __init__(self, translator, glossary: Glossary, templates=DEFAULT_TEMPLATES) -> None:
        self.translator = translator
        self.glossary = glossary
        self.templates = templates

    def translate_scene(self, entries: Sequence[ScriptEntry]) -> list[str | None]:
        return [
            translate_with_glossary(entry.text, self.translator, self.glossary, self.templates)[0]
            for entry in entries
        ]


def group_by_scene(entries: Iterable[ScriptEntry]) -> list[list[ScriptEntry]]:
    scenes: OrderedDict[str, list[ScriptEntry]] = OrderedDict()
    for entry in entries:
        scenes.setdefault(entry.scene, []).append(entry)
    return [sorted(scene, key=lambda entry: entry.order) for scene in scenes.values()]


class Checkpoint:
    """A durable entry-id to translated-text mapping."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.data: dict[str, str] = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data = {str(key): str(value) for key, value in raw.items()}
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read checkpoint %s (%s); starting fresh", self.path, exc)

    def __contains__(self, entry_id: str) -> bool:
        return entry_id in self.data

    def add(self, mapping: Mapping[str, str]) -> None:
        if not mapping:
            return
        self.data.update(mapping)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)


def translate_corpus(
    entries: Iterable[ScriptEntry],
    backend: CorpusTranslator,
    checkpoint: Checkpoint,
    progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    scenes = group_by_scene(entries)
    for index, scene in enumerate(scenes, start=1):
        pending = [entry for entry in scene if entry.id not in checkpoint]
        if not pending:
            continue

        results = backend.translate_scene(pending)
        if len(results) != len(pending):
            logger.warning(
                "Scene %s returned %d/%d lines; retrying one entry at a time",
                scene[0].scene,
                len(results),
                len(pending),
            )
            results = [backend.translate_scene([entry])[0] for entry in pending]

        completed = {entry.id: translated for entry, translated in zip(pending, results) if translated}
        checkpoint.add(completed)
        if progress:
            progress(f"[{index}/{len(scenes)}] {scene[0].scene}: {len(completed)}/{len(pending)}")
    return dict(checkpoint.data)


def write_translated_jsonl(
    entries: Iterable[ScriptEntry], translations: Mapping[str, str], path: Path
) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            if entry.id in translations:
                handle.write(
                    json.dumps({**entry.to_dict(), "translated": translations[entry.id]}, ensure_ascii=False)
                    + "\n"
                )
                count += 1
    return count


def read_translated_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
