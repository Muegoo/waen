"""Persist the pipeline's inputs and decisions for troubleshooting.

Each dump cycle overwrites a fixed slot after ``max_cycles`` so a long-running
debug session cannot fill the user's disk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Sequence

import numpy as np

from .geometry import Box
from .models import TextBlock, TextLine, TranslatedBlock

logger = logging.getLogger(__name__)

BOX_COLOURS = {
    "paragraph": (80, 200, 255),
    "standalone": (120, 255, 120),
}


def _box_dict(box: Box) -> dict[str, int]:
    return {"x": box.x, "y": box.y, "w": box.w, "h": box.h}


def _save_png(frame: np.ndarray, path: Path) -> None:
    from PyQt6.QtGui import QImage

    height, width = frame.shape[:2]
    rgb = np.ascontiguousarray(frame[:, :, ::-1])
    image = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888)
    if not image.copy().save(str(path)):
        raise OSError(f"QImage could not save {path}")


def _draw_boxes(
    frame: np.ndarray, blocks: Sequence[TextBlock], origin: Box | None
) -> np.ndarray:
    """Draw block bounds on a copy using numpy, without an OpenCV dependency."""
    canvas = frame.copy()
    height, width = canvas.shape[:2]
    offset_x = origin.x if origin else 0
    offset_y = origin.y if origin else 0

    for block in blocks:
        colour = BOX_COLOURS.get(block.kind, (255, 255, 255))
        left = max(0, block.box.x - offset_x)
        top = max(0, block.box.y - offset_y)
        right = min(width - 1, block.box.right - offset_x)
        bottom = min(height - 1, block.box.bottom - offset_y)
        if right <= left or bottom <= top:
            continue
        canvas[top : top + 2, left:right] = colour
        canvas[bottom - 2 : bottom, left:right] = colour
        canvas[top:bottom, left : left + 2] = colour
        canvas[top:bottom, right - 2 : right] = colour
    return canvas


class DebugDumper:
    """Write a bounded ring of frame, annotation, and pipeline-data snapshots."""

    def __init__(self, directory: Path | str, max_cycles: int = 500) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_cycles = max(1, max_cycles)
        self._cycle = 0
        self._lock = Lock()

    def dump(
        self,
        frame: np.ndarray,
        lines: Sequence[TextLine],
        blocks: Sequence[TextBlock],
        translated: Sequence[TranslatedBlock],
        timings: dict,
        region: Box | None = None,
    ) -> int:
        """Write one snapshot and return its ring-slot number.

        Translation runs on two executor threads, so serialise a complete cycle
        to keep its three files consistent when the ring wraps around.
        """
        with self._lock:
            cycle = self._cycle % self.max_cycles
            self._cycle += 1
            stem = f"{cycle:04d}"

            try:
                _save_png(frame, self.directory / f"{stem}_frame.png")
                _save_png(
                    _draw_boxes(frame, blocks, region),
                    self.directory / f"{stem}_boxes.png",
                )
            except Exception as exc:
                logger.warning("Could not write debug images: %s", exc)

            payload = {
                "cycle": cycle,
                "region": _box_dict(region) if region else None,
                "lines": [
                    {
                        "text": line.text,
                        "box": _box_dict(line.box),
                        "confidence": line.confidence,
                    }
                    for line in lines
                ],
                "blocks": [
                    {
                        "kind": block.kind,
                        "source_text": block.source_text,
                        "box": _box_dict(block.box),
                        "line_count": len(block.lines),
                    }
                    for block in blocks
                ],
                "translated": [
                    {
                        "source_text": entry.block.source_text,
                        "translated": entry.translated,
                        "glossary_applied": entry.glossary_applied,
                        "kind": entry.block.kind,
                        "corpus_hit": entry.corpus_hit,
                        "corpus_score": entry.corpus_score,
                        "corpus_entry_id": entry.corpus_entry_id,
                    }
                    for entry in translated
                ],
                "timings": timings,
            }
            try:
                (self.directory / f"{stem}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except OSError as exc:
                logger.warning("Could not write debug metadata: %s", exc)
            return cycle
