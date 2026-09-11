"""Find the placeholder format that survives Google Translate.

Run with ``python -m scripts.placeholder_probe`` to rank the candidates and
write the result to ``docs/phase2-placeholder-notes.md``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from waen.translate.glossary import DEFAULT_TEMPLATES, Glossary

REPORT_PATH = Path("docs/phase2-placeholder-notes.md")

SENTENCES: tuple[str, ...] = (
    "Ryuji is waiting outside the Palace.",
    "We need to steal the Treasure before the deadline.",
    "Makoto said the Velvet Room is not a dream.",
    "Morgana thinks the Phantom Thieves should rest.",
    "Your Persona has awakened, Joker.",
    "The Shadow guarding this floor is dangerous.",
    "Futaba sent a Calling Card to Mementos.",
    "Ann and Yusuke are already in the Safe Room.",
)


def score_template(
    template: str, glossary: Glossary, translator, sentences: Sequence[str]
) -> tuple[int, int]:
    """Return completed placeholder survivals and sentences containing terms."""
    survived = 0
    counted = 0
    for sentence in sentences:
        protected, replacements = glossary.protect(sentence, template)
        if not replacements:
            continue
        counted += 1
        translated = translator.translate_many([protected])[0]
        if translated is not None and not glossary.missing(translated, replacements, template):
            survived += 1
    return survived, counted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find placeholder templates Google Translate preserves"
    )
    parser.add_argument("--glossary", default="glossary/persona5.json")
    parser.add_argument("--out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    from waen.translate.google import GoogleTranslateBackend

    glossary = Glossary.from_file(args.glossary)
    translator = GoogleTranslateBackend(source="en", target="th")

    rows = []
    for template in DEFAULT_TEMPLATES:
        survived, counted = score_template(template, glossary, translator, SENTENCES)
        ratio = survived / counted if counted else 0.0
        rows.append((template, survived, counted, ratio))
        print(f"{template:12s} {survived}/{counted}  ({ratio:.0%})")

    rows.sort(key=lambda row: row[3], reverse=True)
    winner = rows[0][0] if rows and rows[0][3] > 0 else None

    lines = [
        "# Phase 2 - Google Translate placeholder survival",
        "",
        "| template | survived | total | rate |",
        "|---|---|---|---|",
    ]
    lines += [f"| `{template}` | {survived} | {counted} | {ratio:.0%} |" for template, survived, counted, ratio in rows]
    lines += [
        "",
        (
            f"Recommended config value: `placeholder_template = {winner!r}`"
            if winner
            else "**No template survived.** Translate without term protection and report the status to the user."
        ),
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote report to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
