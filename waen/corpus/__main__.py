"""Run the offline corpus extractor: ``python -m waen.corpus extract|stats``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..translate.glossary import Glossary
from .adapters.plaintext import PlaintextAdapter
from .adapters.persona5r import Persona5RoyalAdapter
from .build import build_corpus_db
from .extract import corpus_stats, extract_entries, read_jsonl, write_jsonl
from .translate import (
    Checkpoint,
    LineByLineCorpusTranslator,
    read_translated_jsonl,
    translate_corpus,
    write_translated_jsonl,
)

ADAPTERS: dict[str, type] = {
    PlaintextAdapter.id: PlaintextAdapter,
    Persona5RoyalAdapter.id: Persona5RoyalAdapter,
}


def _parse_vars(pairs: list[str]) -> dict[str, str]:
    values = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator:
            raise SystemExit(f"--var ต้องอยู่ในรูป name=value ไม่ใช่ {pair!r}")
        values[key.strip()] = value
    return values


def cmd_extract(args) -> int:
    adapter_cls = ADAPTERS.get(args.game)
    if adapter_cls is None:
        print(f"ไม่รู้จักเกม {args.game!r} — มี: {', '.join(sorted(ADAPTERS))}", file=sys.stderr)
        return 2
    adapter = adapter_cls()
    game_dir = Path(args.game_dir)
    if not adapter.detect(game_dir):
        print(f"{game_dir} ไม่มีไฟล์ที่ adapter {adapter.id} คาดหวัง", file=sys.stderr)
        return 2
    count = write_jsonl(extract_entries(adapter, game_dir, _parse_vars(args.var)), Path(args.out))
    print(f"เขียน {count} entries → {args.out}")
    return 0


def cmd_stats(args) -> int:
    stats = corpus_stats(read_jsonl(Path(args.path)))
    for key in ("entries", "scenes", "chars", "unique_texts"):
        print(f"{key}: {stats[key]}")
    return 0


def make_backend(name: str, glossary_path: str) -> LineByLineCorpusTranslator:
    if name == "google":
        from ..translate.google import GoogleTranslateBackend

        return LineByLineCorpusTranslator(
            GoogleTranslateBackend(source="en", target="th"),
            Glossary.from_file(Path(glossary_path)),
        )
    raise SystemExit(f"Unknown backend {name!r}")


def cmd_translate(args) -> int:
    entries = read_jsonl(Path(args.input))
    stats = corpus_stats(entries)
    for key in ("entries", "scenes", "chars", "unique_texts"):
        print(f"{key}: {stats[key]}")
    if args.dry_run:
        return 0

    checkpoint = Checkpoint(args.checkpoint or Path(args.out).with_suffix(".checkpoint.json"))
    translations = translate_corpus(entries, make_backend(args.backend, args.glossary), checkpoint, progress=print)
    count = write_translated_jsonl(entries, translations, Path(args.out))
    print(f"Wrote {count}/{len(entries)} entries → {args.out}")
    return 0


def cmd_build(args) -> int:
    count = build_corpus_db(read_translated_jsonl(Path(args.input)), Path(args.out))
    print(f"Built corpus with {count} entries → {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m waen.corpus")
    sub = parser.add_subparsers(dest="command", required=True)

    extract_parser = sub.add_parser("extract", help="Extract dialogue into .src.jsonl")
    extract_parser.add_argument("--game", required=True)
    extract_parser.add_argument("--game-dir", required=True)
    extract_parser.add_argument("--out", required=True)
    extract_parser.add_argument("--var", action="append", default=[], help="name=value")
    extract_parser.set_defaults(func=cmd_extract)

    stats_parser = sub.add_parser("stats", help="Report corpus entry and character counts")
    stats_parser.add_argument("path")
    stats_parser.set_defaults(func=cmd_stats)

    translate_parser = sub.add_parser("translate", help="Translate .src.jsonl into resumable .th.jsonl")
    translate_parser.add_argument("--in", dest="input", required=True)
    translate_parser.add_argument("--out", required=True)
    translate_parser.add_argument("--backend", default="google")
    translate_parser.add_argument("--glossary", default="glossary/persona5.json")
    translate_parser.add_argument("--checkpoint", default=None)
    translate_parser.add_argument("--dry-run", action="store_true", help="Report size without translating")
    translate_parser.set_defaults(func=cmd_translate)

    build_parser = sub.add_parser("build", help="Build runtime SQLite corpus from .th.jsonl")
    build_parser.add_argument("--in", dest="input", required=True)
    build_parser.add_argument("--out", required=True)
    build_parser.set_defaults(func=cmd_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    # คอนโซล Windows เป็น cp1252 โดยปริยาย ข้อความไทยจะทำให้ล้ม จึงบังคับ UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
