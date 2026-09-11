"""Build a SQLite FTS5-trigram corpus from translated JSONL rows."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .normalize import normalize

SCHEMA = """
DROP TABLE IF EXISTS entries_fts;
DROP TABLE IF EXISTS entries;
CREATE TABLE entries (
    id         TEXT PRIMARY KEY,
    scene      TEXT,
    ord        INTEGER,
    speaker    TEXT,
    text       TEXT NOT NULL,
    text_norm  TEXT NOT NULL,
    translated TEXT NOT NULL
);
CREATE VIRTUAL TABLE entries_fts USING fts5(
    text_norm, content='entries', content_rowid='rowid', tokenize='trigram'
);
"""


def fts5_trigram_available() -> bool:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE VIRTUAL TABLE test_fts USING fts5(text, tokenize='trigram')")
        return True
    except sqlite3.Error:
        return False
    finally:
        if connection is not None:
            connection.close()


def build_corpus_db(rows: Iterable[dict], db_path: Path) -> int:
    if not fts5_trigram_available():
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} does not support the FTS5 trigram tokenizer (requires >= 3.34)"
        )

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    try:
        connection.executescript(SCHEMA)
        count = 0
        for row in rows:
            translated = (row.get("translated") or "").strip()
            normalized = normalize(str(row.get("text", "")))
            if not translated or not normalized:
                continue
            connection.execute(
                "INSERT OR REPLACE INTO entries (id, scene, ord, speaker, text, text_norm, translated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(row["id"]),
                    row.get("scene"),
                    row.get("order"),
                    row.get("speaker"),
                    str(row["text"]),
                    normalized,
                    translated,
                ),
            )
            count += 1
        connection.execute("INSERT INTO entries_fts(entries_fts) VALUES ('rebuild')")
        connection.commit()
        return count
    finally:
        connection.close()
