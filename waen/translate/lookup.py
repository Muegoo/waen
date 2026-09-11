"""Fuzzy lookup against an offline translated corpus."""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from ..corpus.normalize import normalize

logger = logging.getLogger(__name__)

_MIN_TERM = 3
_MAX_TERMS = 32

try:
    from rapidfuzz import fuzz
except ImportError:
    _RATIO: Callable[[str, str], float] = lambda left, right: SequenceMatcher(None, left, right).ratio() * 100
else:
    _RATIO = fuzz.ratio


@dataclass(frozen=True)
class LookupHit:
    entry_id: str
    source: str
    translated: str
    score: int


class CorpusLookup:
    def __init__(
        self,
        db_path: Path | str,
        threshold: int = 85,
        candidates: int = 20,
        scorer: Callable[[str, str], float] | None = None,
    ) -> None:
        self.threshold = int(threshold)
        self.candidates = int(candidates)
        self._scorer = scorer or _RATIO
        self._con = sqlite3.connect(str(db_path), check_same_thread=False)
        self._con.execute("SELECT count(*) FROM entries_fts")
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def lookup(self, text: str) -> LookupHit | None:
        normalized = normalize(text)
        terms = [term for term in normalized.split() if len(term) >= _MIN_TERM][:_MAX_TERMS]
        if not terms:
            with self._lock:
                self._misses += 1
            return None

        query = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        with self._lock:
            rows = self._con.execute(
                "SELECT e.id, e.text, e.text_norm, e.translated "
                "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
                "WHERE entries_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, self.candidates),
            ).fetchall()

            best: LookupHit | None = None
            for entry_id, source, text_norm, translated in rows:
                score = int(round(self._scorer(normalized, text_norm)))
                if best is None or score > best.score:
                    best = LookupHit(entry_id, source, translated, score)

            if best is not None and best.score >= self.threshold:
                self._hits += 1
                return best
            self._misses += 1
            return None

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"hits": self._hits, "misses": self._misses}

    def close(self) -> None:
        with self._lock:
            self._con.close()


def load_corpus(path: str | None, threshold: int) -> CorpusLookup | None:
    """Open a configured corpus, degrading cleanly to no corpus on failure."""
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        logger.warning("Corpus %s was not found; using Google translation directly", target)
        return None
    try:
        return CorpusLookup(target, threshold=threshold)
    except (OSError, sqlite3.Error) as exc:
        logger.warning("Could not open corpus %s (%s); using Google translation directly", target, exc)
        return None
