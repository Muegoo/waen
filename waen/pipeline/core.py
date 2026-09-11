"""Pipeline logic independent of Qt and worker-thread management."""

from __future__ import annotations

import logging

import numpy as np

from ..config import AppConfig
from ..geometry import Box
from ..models import TextBlock, TextLine, TranslatedBlock
from ..ocr.preprocess import PIPELINES, scale_factor_of
from ..translate.glossary import DEFAULT_TEMPLATES, Glossary, translate_with_glossary
from .framediff import FrameDiffer
from .grouping import group_lines
from .stabilize import StabilizeConfig, Stabilizer

logger = logging.getLogger(__name__)

THAI_FIRST = 0x0E00
THAI_LAST = 0x0E7F
MAX_THAI_RATIO = 0.3


def thai_ratio(text: str) -> float:
    """Return the fraction of alphabetic characters in ``text`` that are Thai."""
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return 0.0
    thai = sum(THAI_FIRST <= ord(character) <= THAI_LAST for character in letters)
    return thai / len(letters)


class PipelineCore:
    def __init__(
        self,
        ocr,
        config: AppConfig,
        glossary: Glossary,
        translator,
        preprocess_name: str = "raw",
        max_thai_ratio: float = MAX_THAI_RATIO,
        templates=DEFAULT_TEMPLATES,
    ) -> None:
        self.ocr = ocr
        self.config = config
        self.glossary = glossary
        self.translator = translator
        self.preprocess_name = preprocess_name
        self.max_thai_ratio = max_thai_ratio
        self.templates = templates
        self.last_lines: list[TextLine] = []
        self._differ = FrameDiffer(threshold=config.diff_threshold)
        self._stabilizer = Stabilizer(
            StabilizeConfig(
                stable_frames=config.stable_frames,
                min_stable_ms=config.min_stable_ms,
            )
        )

    def reset(self) -> None:
        self._differ.reset()
        self._stabilizer.reset()
        self.last_lines = []

    def detect(
        self, frame: np.ndarray, origin: tuple[int, int], now_ms: int
    ) -> list[TextBlock]:
        changed = self._differ.changed(frame)
        if not changed and not self._stabilizer.pending:
            return []

        prepared = PIPELINES[self.preprocess_name](frame)
        factor = scale_factor_of(self.preprocess_name)
        lines: list[TextLine] = []
        for found in self.ocr.recognize(prepared):
            # Thai recognized from the captured scene can only be waen's own overlay.
            if thai_ratio(found.text) > self.max_thai_ratio:
                logger.debug("Dropping Thai OCR line: %r", found.text)
                continue
            box = Box(
                found.box.x // factor,
                found.box.y // factor,
                max(1, found.box.w // factor),
                max(1, found.box.h // factor),
            ).offset_by(origin[0], origin[1])
            lines.append(
                TextLine(text=found.text, box=box, confidence=found.confidence)
            )

        self.last_lines = lines
        return self._stabilizer.feed(group_lines(lines, self.config.grouping), now_ms)

    def translate(self, block: TextBlock) -> TranslatedBlock | None:
        """Translate one stable block; callers should run this off the capture thread."""
        translated, applied = translate_with_glossary(
            block.source_text, self.translator, self.glossary, self.templates
        )
        if translated is None:
            return None
        return TranslatedBlock(
            block=block, translated=translated, glossary_applied=applied
        )
