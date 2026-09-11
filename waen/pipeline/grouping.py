"""Group OCR lines into paragraphs or independent blocks.

Dialogue boxes wrap a sentence across nearby aligned rows, while dispersed menu
items must remain independent.  The grouping criteria here are geometry-only.
"""

from __future__ import annotations

from typing import Sequence

from ..config import GroupingConfig
from ..models import TextBlock, TextLine

MAX_VERTICAL_OVERLAP_RATIO = 0.5


def join_lines(lines: Sequence[TextLine]) -> str:
    """Join line text, removing a hyphen that represents a wrapped word."""
    parts: list[str] = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        if parts and parts[-1].endswith("-"):
            parts[-1] = parts[-1][:-1] + text
        else:
            parts.append(text)
    return " ".join(parts)


def same_paragraph(a: TextLine, b: TextLine, config: GroupingConfig) -> bool:
    """Return whether b continues a's paragraph, assuming a is above b."""
    average_height = (a.box.h + b.box.h) / 2
    if average_height <= 0:
        return False

    gap = b.box.y - a.box.bottom
    if gap > config.vertical_gap_ratio * average_height:
        return False
    if gap < -MAX_VERTICAL_OVERLAP_RATIO * average_height:
        return False

    widest = max(a.box.w, b.box.w)
    if abs(b.box.x - a.box.x) > config.left_align_tolerance * widest:
        return False

    overlap = min(a.box.right, b.box.right) - max(a.box.x, b.box.x)
    narrower = min(a.box.w, b.box.w)
    if narrower <= 0 or overlap / narrower < config.horizontal_overlap_min:
        return False
    return True


def group_lines(lines: Sequence[TextLine], config: GroupingConfig) -> list[TextBlock]:
    if not lines:
        return []

    ordered = sorted(lines, key=lambda line: (line.box.y, line.box.x))
    groups: list[list[TextLine]] = [[ordered[0]]]
    for line in ordered[1:]:
        if same_paragraph(groups[-1][-1], line, config):
            groups[-1].append(line)
        else:
            groups.append([line])

    blocks: list[TextBlock] = []
    for group in groups:
        if len(group) == 1:
            blocks.append(
                TextBlock.from_lines(group, group[0].text.strip(), "standalone")
            )
        else:
            blocks.append(TextBlock.from_lines(group, join_lines(group), "paragraph"))
    return blocks
