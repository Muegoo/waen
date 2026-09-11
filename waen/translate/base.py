"""Translator interface.

Translation failures are represented by ``None`` rather than exceptions so the
pipeline can continue when connectivity or rate limits fail.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Translator(Protocol):
    def translate_many(self, texts: list[str]) -> list[str | None]:
        """Translate texts, preserving their order and count."""
        ...
