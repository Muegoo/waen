"""Run the offline corpus extractor: ``python -m waen.corpus extract|stats``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .adapters.plaintext import PlaintextAdapter
from .extract import corpus_stats, extract_entries, read_jsonl, write_jsonl

ADAPTERS: dict[str, type] = {
    PlaintextAdapter.id: PlaintextAdapter,
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
