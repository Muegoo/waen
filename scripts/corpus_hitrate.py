"""Report corpus lookup hit rate from a --debug-dump directory.

    python scripts/corpus_hitrate.py <dump_dir> [--kind paragraph|standalone|all] [--top 20]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(dump_dir: Path, kind: str = "paragraph", top: int = 20) -> dict:
    """Summarize corpus results for translated blocks in debug-dump JSON files."""
    total = hits = 0
    misses: Counter[str] = Counter()
    scores: list[int] = []
    for path in sorted(Path(dump_dir).glob("[0-9][0-9][0-9][0-9].json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in payload.get("translated", []):
            if kind != "all" and entry.get("kind") != kind:
                continue
            total += 1
            if entry.get("corpus_hit"):
                hits += 1
            else:
                misses[entry.get("source_text", "")] += 1
                scores.append(int(entry.get("corpus_score", 0)))
    return {
        "total": total,
        "hits": hits,
        "rate": (hits / total) if total else 0.0,
        "top_misses": misses.most_common(top),
        "miss_scores": scores,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dump_dir")
    parser.add_argument(
        "--kind", default="paragraph", choices=["paragraph", "standalone", "all"]
    )
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)

    report = summarize(Path(args.dump_dir), args.kind, args.top)
    print(
        f"kind={args.kind}  total={report['total']}  "
        f"hits={report['hits']}  rate={report['rate']:.1%}"
    )
    near = sum(1 for score in report["miss_scores"] if score >= 70)
    print(f"misses scoring 70-84 (consider a lower threshold): {near}")
    print("\nMost frequent misses:")
    for text, count in report["top_misses"]:
        print(f"  {count:3d}x  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
