"""Protect game-specific terms while sending text to a translation service."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Mapping, Sequence

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES: tuple[str, ...] = ("[[{i}]]", "@@{i}@@", "#{i}#", "{{{i}}}")


def _pattern_for(template: str) -> re.Pattern[str]:
    """Return a pattern that also accepts spaces inserted into a placeholder."""
    prefix, suffix = template.split("{i}")
    return re.compile(
        r"\s*".join(re.escape(ch) for ch in prefix)
        + r"\s*(\d+)\s*"
        + r"\s*".join(re.escape(ch) for ch in suffix)
    )


class Glossary:
    def __init__(self, keep: Sequence[str], mapping: Mapping[str, str]) -> None:
        # Stable tie ordering avoids nondeterministic placeholder indices from a set.
        self._terms = sorted(dict.fromkeys([*keep, *mapping]), key=len, reverse=True)
        self._replacement = {term: mapping.get(term, term) for term in self._terms}

    @classmethod
    def empty(cls) -> "Glossary":
        return cls(keep=[], mapping={})

    @classmethod
    def from_file(cls, path: str | Path) -> "Glossary":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read glossary (%s); continuing without one", exc)
            return cls.empty()
        keep = raw.get("keep", []) if isinstance(raw, dict) else []
        mapping = raw.get("map", {}) if isinstance(raw, dict) else {}
        if not isinstance(keep, list) or not isinstance(mapping, dict):
            logger.warning("Invalid glossary format; continuing without one")
            return cls.empty()
        return cls(keep=keep, mapping=mapping)

    def protect(self, text: str, template: str) -> tuple[str, list[str]]:
        replacements: list[str] = []
        if not self._terms:
            return text, replacements

        pattern = re.compile(
            rf"\b(?:{'|'.join(re.escape(term) for term in self._terms)})\b"
        )

        def substitute(match: re.Match[str]) -> str:
            index = len(replacements)
            replacements.append(self._replacement[match.group(0)])
            return template.format(i=index)

        return pattern.sub(substitute, text), replacements

    def missing(
        self, text: str, replacements: list[str], template: str
    ) -> list[int]:
        pattern = _pattern_for(template)
        found = {int(match.group(1)) for match in pattern.finditer(text)}
        return [index for index in range(len(replacements)) if index not in found]

    def restore(self, text: str, replacements: list[str], template: str) -> str:
        pattern = _pattern_for(template)

        def substitute(match: re.Match[str]) -> str:
            index = int(match.group(1))
            if 0 <= index < len(replacements):
                return replacements[index]
            return match.group(0)

        return pattern.sub(substitute, text)


def translate_with_glossary(
    text: str,
    translator,
    glossary: Glossary,
    templates: Sequence[str] = DEFAULT_TEMPLATES,
) -> tuple[str | None, bool]:
    """Translate text and restore protected terms when a template survives."""
    for template in templates:
        protected, replacements = glossary.protect(text, template)
        if not replacements:
            return translator.translate_many([text])[0], True

        translated = translator.translate_many([protected])[0]
        if translated is None:
            return None, False
        if not glossary.missing(translated, replacements, template):
            return glossary.restore(translated, replacements, template), True

        logger.debug("Placeholder %r did not survive; trying the next template", template)

    logger.info("No placeholder template survived; translating without glossary")
    return translator.translate_many([text])[0], False
