"""One screen of dialogue: the unit the OCR engine sees."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScriptEntry:
    """A stable, extracted page of game dialogue."""

    id: str
    game: str
    scene: str
    order: int
    speaker: str | None
    text_raw: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ScriptEntry":
        return cls(
            id=str(d["id"]),
            game=str(d["game"]),
            scene=str(d["scene"]),
            order=int(d["order"]),
            speaker=d.get("speaker"),
            text_raw=str(d.get("text_raw", "")),
            text=str(d["text"]),
        )
