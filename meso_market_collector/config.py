"""Configuration loading for the price collector.

Screen regions are machine-specific, so they live in JSON files; find the
coordinates with tools/find_coords.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

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
REGION_READINGS_CSV_PATH = DATA_DIR / "region_readings.csv"

# Meso-Market-Tracker's deployed endpoint (its backend_url Terraform
# output). Override with MESO_TRACKER_API_URL, e.g. for a local dev server.
DEFAULT_TRACKER_API_URL = "https://xa6elv0g44.execute-api.us-east-1.amazonaws.com/price"


def get_tracker_api_url() -> str:
    """MESO_TRACKER_API_URL (environment or .env) if set, else the default."""
    return _env("MESO_TRACKER_API_URL") or DEFAULT_TRACKER_API_URL


# KEY=VALUE settings, including secrets. Gitignored - never commit it.
ENV_FILE = PROJECT_ROOT / ".env"


def _env(name: str) -> str | None:
    """A setting from the environment, else from .env, else None. The
    file matters for the scheduled task, which may not see a variable set
    after the last logon. Read on each call, so later changes take effect."""
    return os.environ.get(name) or dotenv_values(ENV_FILE).get(name) or None


def get_record_price_secret() -> str | None:
    """The shared secret Tracker's recordPrice mutation requires, from
    MESO_TRACKER_RECORD_PRICE_SECRET - or None if it isn't set."""
    return _env("MESO_TRACKER_RECORD_PRICE_SECRET")


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

    A plain entry is one box: {"left", "top", "width", "height"}.

    A column entry, {"left", "width", "height", "tops": [...]}, expands
    into one Region per top - for boxes stacked in a column. Rows are
    named "<key>_1", "<key>_2", ... unless a "names" list (paired with
    "tops") is given.
    """
    if path is None:
        path = get_regions_file()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    regions: list[Region] = []
    for name, box in raw.items():
        if "tops" in box:
            tops = box["tops"]
            names = box.get("names", [f"{name}_{i}" for i in range(1, len(tops) + 1)])
            for row_name, top in zip(names, tops):
                regions.append(
                    Region(name=row_name, left=box["left"], top=top, width=box["width"], height=box["height"])
                )
        else:
            regions.append(Region(name=name, **box))
    return regions
