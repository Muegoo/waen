"""Normalize game-file and OCR text into a common lookup representation.

This is deliberately the single shared copy used while building and looking up a
corpus. Rebuild corpus data whenever its behavior changes.
"""

from __future__ import annotations

import re
import unicodedata

_QUOTES = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "–": "-", "—": "-", "―": "-",
        "…": "...",
    }
)
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Return an idempotent, punctuation-insensitive form of *text*."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    text = text.lower()
    text = _NON_WORD.sub(" ", text)
    return _SPACES.sub(" ", text).strip()
