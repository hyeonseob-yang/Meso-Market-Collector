"""Configuration loading for the price collector.

Screen regions are machine-specific, so they live in JSON files; find the
coordinates with tools/find_coords.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGIONS_FILE = PROJECT_ROOT / "config" / "regions.json"
# Per-machine override (gitignored): coordinates depend on the display.
LOCAL_REGIONS_FILE = PROJECT_ROOT / "config" / "regions.local.json"
TEMPLATES_DIR = PROJECT_ROOT / "assets" / "templates"
# Per-machine overrides (gitignored): a template only matches at the
# resolution/UI scale it was captured at.
LOCAL_TEMPLATES_DIR = PROJECT_ROOT / "assets" / "templates.local"
DATA_DIR = PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "price_history.csv"

ENV_FILE = PROJECT_ROOT / ".env"  # gitignored - never commit it
load_dotenv(ENV_FILE)  # doesn't override variables already set

def get_tracker_api_url() -> str:
    url = os.environ.get("MESO_TRACKER_API_URL")
    if not url:
        raise RuntimeError("MESO_TRACKER_API_URL isn't set - add Tracker's address to .env")
    return url


def get_record_price_secret() -> str | None:
    return os.environ.get("MESO_TRACKER_RECORD_PRICE_SECRET") or None


@dataclass(frozen=True)
class Region:
    name: str
    left: int
    top: int
    width: int
    height: int

    @property
    def box(self) -> tuple[int, int, int, int]:
        """(left, top, width, height) as expected by pyautogui.screenshot()."""
        return (self.left, self.top, self.width, self.height)


def get_regions_file() -> Path:
    """regions.local.json if it exists, else the committed regions.json."""
    return LOCAL_REGIONS_FILE if LOCAL_REGIONS_FILE.exists() else REGIONS_FILE


def get_template_path(name: str) -> Path:
    """assets/templates.local/<name> if it exists, else the committed
    assets/templates/<name> - so a machine overrides only what differs."""
    local = LOCAL_TEMPLATES_DIR / name
    return local if local.exists() else TEMPLATES_DIR / name


def load_regions(path: Path | None = None) -> list[Region]:
    """Load regions from `path` (default: get_regions_file()).

    Each entry is a column, {"left", "width", "height", "tops": [...]},
    expanded into one Region per top. Rows are named "<key>_1", "<key>_2",
    ... unless a "names" list (paired with "tops") is given.
    """
    if path is None:
        path = get_regions_file()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    regions: list[Region] = []
    for name, column in raw.items():
        if "tops" not in column:
            raise ValueError(f"Region entry {name!r} has no 'tops' list")
        tops = column["tops"]
        names = column.get("names", [f"{name}_{i}" for i in range(1, len(tops) + 1)])
        for row_name, top in zip(names, tops):
            regions.append(
                Region(name=row_name, left=column["left"], top=top, width=column["width"], height=column["height"])
            )
    return regions
