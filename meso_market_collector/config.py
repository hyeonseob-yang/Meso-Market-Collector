"""Configuration loading for the price collector.

Screen regions are game/monitor-specific, so they live in a small JSON file
rather than being hardcoded. Use tools/find_coords.py to figure out the
left/top/width/height for a region you want to track.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGIONS_FILE = PROJECT_ROOT / "config" / "regions.json"
DATA_DIR = PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "price_history.csv"


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
    Use this when boxes are stacked in a column (e.g. Sell/Buy Meso price
    rows); fall back to plain boxes for anything that isn't.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    regions: list[Region] = []
    for name, box in raw.items():
        if "tops" in box:
            tops = box["tops"]
            for i, top in enumerate(tops, start=1):
                regions.append(
                    Region(name=f"{name}_{i}", left=box["left"], top=top, width=box["width"], height=box["height"])
                )
        else:
            regions.append(Region(name=name, **box))
    return regions
