"""Coordinate helpers for the application.

Every ``Box`` in the pipeline uses physical screen pixels on the virtual
desktop.  Conversion between Qt logical coordinates and physical pixels lives
here so other modules never need to apply DPI scaling themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MIN_SIZE = 8


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return max(0, self.w) * max(0, self.h)

    def union(self, other: "Box") -> "Box":
        x = min(self.x, other.x)
        y = min(self.y, other.y)
        return Box(x, y, max(self.right, other.right) - x, max(self.bottom, other.bottom) - y)

    def intersection(self, other: "Box") -> "Box | None":
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        w = min(self.right, other.right) - x
        h = min(self.bottom, other.bottom) - y
        if w <= 0 or h <= 0:
            return None
        return Box(x, y, w, h)

    def iou(self, other: "Box") -> float:
        inter = self.intersection(other)
        if inter is None:
            return 0.0
        union_area = self.area + other.area - inter.area
        if union_area <= 0:
            return 0.0
        return inter.area / union_area

    def offset_by(self, dx: int, dy: int) -> "Box":
        return Box(self.x + dx, self.y + dy, self.w, self.h)

    def is_valid(self, min_size: int = DEFAULT_MIN_SIZE) -> bool:
        return self.w >= min_size and self.h >= min_size


def to_physical(box: Box, scale: float) -> Box:
    """Convert a Qt logical-coordinate box to physical screen pixels."""
    return Box(
        round(box.x * scale),
        round(box.y * scale),
        max(1, round(box.w * scale)),
        max(1, round(box.h * scale)),
    )


def to_logical(box: Box, scale: float) -> Box:
    """Convert a physical-pixel box to Qt logical coordinates."""
    if scale == 0:
        raise ValueError("scale must not be zero")
    return Box(
        round(box.x / scale),
        round(box.y / scale),
        max(1, round(box.w / scale)),
        max(1, round(box.h / scale)),
    )
