"""Configuration loading for the price collector.

Screen regions are game/monitor-specific, so they live in a small JSON file
rather than being hardcoded. Use tools/find_coords.py to figure out the
left/top/width/height for a region you want to track.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGIONS_FILE = PROJECT_ROOT / "config" / "regions.json"
DATA_DIR = PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "price_history.csv"
REGION_READINGS_CSV_PATH = DATA_DIR / "region_readings.csv"

# Meso-Market-Tracker's deployed API Gateway endpoint (see that project's
# backend/infra/outputs.tf -> backend_url). Overridable via
# MESO_TRACKER_API_URL, e.g. to point at a local `flask run` dev server
# instead.
DEFAULT_TRACKER_API_URL = "https://xa6elv0g44.execute-api.us-east-1.amazonaws.com/price"


def get_tracker_api_url() -> str:
    """Resolved fresh on each call (not a module-level constant) so a
    MESO_TRACKER_API_URL set after import - e.g. by a test - still takes
    effect."""
    return os.environ.get("MESO_TRACKER_API_URL", DEFAULT_TRACKER_API_URL)


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


def load_regions(path: Path = REGIONS_FILE) -> list[Region]:
    """Load named regions, or "column" shorthand entries.

    A plain entry is one box: {"left", "top", "width", "height"}.

    A column entry shares left/width/height across several rows that only
    differ in vertical position - {"left", "width", "height", "tops": [...]}
    - and expands into one Region per row, named "<key>_1", "<key>_2", ...
    by default, or using an optional "names" list instead (paired
    positionally with "tops") when the index position on its own isn't
    meaningful. Use this when boxes are stacked in a column (e.g. Sell/Buy
    Meso price rows); fall back to plain boxes for anything that isn't.
    """
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
