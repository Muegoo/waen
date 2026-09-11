"""Configuration storage with per-field fallback for corrupt input.

Invalid or future-version configuration files must never prevent the
application from starting.  Unreadable fields fall back to their defaults.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .geometry import Box

logger = logging.getLogger(__name__)

CONFIG_VERSION = 1


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "waen"


def default_config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class GroupingConfig:
    vertical_gap_ratio: float = 0.8
    left_align_tolerance: float = 0.15
    horizontal_overlap_min: float = 0.5


@dataclass
class OverlayConfig:
    font_family: str = "Leelawadee UI"
    font_size: int = 16
    min_font_size: int = 11
    background_opacity: float = 0.8
    gap_px: int = 4


def _default_hotkeys() -> dict[str, str]:
    return {
        "toggle": "ctrl+alt+t",
        "select_region": "ctrl+alt+r",
        "hide": "ctrl+alt+h",
    }


@dataclass
class AppConfig:
    version: int = CONFIG_VERSION
    region: dict | None = None
    region_scale: float = 1.0
    source_lang: str = "en"
    target_lang: str = "th"
    # Keep automatic selection until the Phase 0 report identifies a clear winner.
    ocr_engine: str = "auto"
    capture_backend: str = "auto"
    poll_interval_ms: int = 250
    diff_threshold: float = 4.0
    stable_frames: int = 2
    min_stable_ms: int = 250
    grouping: GroupingConfig = field(default_factory=GroupingConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    glossary_path: str = "glossary/persona5.json"
    placeholder_template: str = "[[{i}]]"
    hotkeys: dict[str, str] = field(default_factory=_default_hotkeys)

    def region_box(self) -> Box | None:
        if not self.region:
            return None
        try:
            return Box(
                int(self.region["x"]),
                int(self.region["y"]),
                int(self.region["w"]),
                int(self.region["h"]),
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Invalid region in config; treating it as unset")
            return None

    def set_region(self, box: Box, scale: float) -> None:
        self.region = {"x": box.x, "y": box.y, "w": box.w, "h": box.h}
        self.region_scale = float(scale)


def _coerce(value: Any, default: Any) -> Any:
    """Coerce to the default's scalar type, or return the default on failure."""
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    for kind in (int, float, str):
        if isinstance(default, kind):
            try:
                return kind(value)
            except (TypeError, ValueError):
                return default
    if isinstance(default, dict):
        return {**default, **value} if isinstance(value, dict) else default
    return value


def _load_section(raw: Any, section_cls: type[GroupingConfig] | type[OverlayConfig]) -> Any:
    section = section_cls()
    if not isinstance(raw, dict):
        return section
    for item in fields(section_cls):
        if item.name in raw:
            setattr(section, item.name, _coerce(raw[item.name], getattr(section, item.name)))
    return section


def load_config(path: Path | None = None) -> AppConfig:
    target = path or default_config_path()
    config = AppConfig()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Unable to read config (%s); using defaults", exc)
        return config

    if not isinstance(raw, dict):
        return config

    for item in fields(AppConfig):
        if item.name not in raw:
            continue
        if item.name == "grouping":
            config.grouping = _load_section(raw[item.name], GroupingConfig)
        elif item.name == "overlay":
            config.overlay = _load_section(raw[item.name], OverlayConfig)
        elif item.name == "region":
            config.region = raw[item.name] if isinstance(raw[item.name], dict) else None
        else:
            setattr(config, item.name, _coerce(raw[item.name], getattr(config, item.name)))
    return config


def save_config(config: AppConfig, path: Path | None = None) -> None:
    target = path or default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False), encoding="utf-8"
    )
