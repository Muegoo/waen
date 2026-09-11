"""Google Translate backend with caching, throttling, retries, and batching."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Callable

logger = logging.getLogger(__name__)

MIN_TRANSLATABLE_CHARS = 2
BACKOFF_BASE_SECONDS = 1.5


def _default_backend_factory(source: str, target: str):
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source=source, target=target)


class GoogleTranslateBackend:
    def __init__(
        self,
        source: str = "en",
        target: str = "th",
        cache_size: int = 1000,
        max_per_second: float = 5.0,
        max_attempts: int = 3,
        backend_factory: Callable = _default_backend_factory,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.target = target
        self.cache_size = cache_size
        self.max_attempts = max_attempts
        self._min_interval = 1.0 / max_per_second if max_per_second > 0 else 0.0
        self._backend_factory = backend_factory
        self._clock = clock
        self._sleeper = sleeper
        self._backend = None
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._last_request_at = float("-inf")
        self._stats = {"requests": 0, "cache_hits": 0, "failures": 0}

    def set_languages(self, source: str, target: str) -> None:
        if (source, target) != (self.source, self.target):
            self.source, self.target = source, target
            self._backend = None

    def stats(self) -> dict:
        return dict(self._stats)

    def cache_size_now(self) -> int:
        return len(self._cache)

    def _key(self, text: str) -> tuple[str, str, str]:
        return (self.source, self.target, text)

    def _remember(self, text: str, translated: str) -> None:
        self._cache[self._key(text)] = translated
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        waited = self._clock() - self._last_request_at
        if waited < self._min_interval:
            self._sleeper(self._min_interval - waited)

    def _call(self, text: str) -> str | None:
        """Translate once, retrying transient failures with exponential backoff."""
        for attempt in range(self.max_attempts):
            self._throttle()
            try:
                if self._backend is None:
                    self._backend = self._backend_factory(self.source, self.target)
                result = self._backend.translate(text)
                self._last_request_at = self._clock()
                self._stats["requests"] += 1
                if result:
                    return result
                return None
            except Exception as exc:
                self._last_request_at = self._clock()
                self._backend = None
                logger.info("Translation failed (attempt %d): %s", attempt + 1, exc)
                if attempt < self.max_attempts - 1:
                    self._sleeper(BACKOFF_BASE_SECONDS * (2**attempt))
        self._stats["failures"] += 1
        return None

    def translate_many(self, texts: list[str]) -> list[str | None]:
        results: list[str | None] = [None] * len(texts)
        pending: list[int] = []

        for index, text in enumerate(texts):
            stripped = text.strip()
            if len(stripped.replace(" ", "")) < MIN_TRANSLATABLE_CHARS:
                continue
            cached = self._cache.get(self._key(stripped))
            if cached is not None:
                self._cache.move_to_end(self._key(stripped))
                self._stats["cache_hits"] += 1
                results[index] = cached
            else:
                pending.append(index)

        if not pending:
            return results

        if len(pending) == 1:
            index = pending[0]
            stripped = texts[index].strip()
            translated = self._call(stripped)
            if translated is not None:
                self._remember(stripped, translated)
            results[index] = translated
            return results

        stripped_texts = [texts[index].strip() for index in pending]
        joined = self._call("\n".join(stripped_texts))
        if joined is not None:
            parts = joined.split("\n")
            if len(parts) == len(pending):
                for index, part in zip(pending, parts):
                    cleaned = part.strip()
                    self._remember(texts[index].strip(), cleaned)
                    results[index] = cleaned
                return results
            logger.info(
                "Sent %d lines but received %d; falling back to individual requests",
                len(pending),
                len(parts),
            )

        for index in pending:
            stripped = texts[index].strip()
            translated = self._call(stripped)
            if translated is not None:
                self._remember(stripped, translated)
            results[index] = translated
        return results
