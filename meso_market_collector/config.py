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

# Top-level regions.json key holding the resolution regions were calibrated
# at, rather than a region/column to expand - see load_reference_resolution.
REFERENCE_RESOLUTION_KEY = "reference_resolution"


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


@dataclass(frozen=True)
class Resolution:
    width: int
    height: int


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
        if name == REFERENCE_RESOLUTION_KEY:
            continue
        if "tops" in box:
            tops = box["tops"]
            for i, top in enumerate(tops, start=1):
                regions.append(
                    Region(name=f"{name}_{i}", left=box["left"], top=top, width=box["width"], height=box["height"])
                )
        else:
            regions.append(Region(name=name, **box))
    return regions


def load_reference_resolution(path: Path = REGIONS_FILE) -> Resolution | None:
    """The screen resolution regions.json's coordinates were calibrated at,
    if recorded - see scale_regions to adapt them to a different resolution.
    Returns None if not present (regions are then used as literal pixels)."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    ref = raw.get(REFERENCE_RESOLUTION_KEY)
    return Resolution(**ref) if ref is not None else None


def scale_regions(regions: list[Region], reference: Resolution, current: Resolution) -> list[Region]:
    """Proportionally scale regions calibrated at `reference` resolution to
    fit `current` resolution instead.

    Assumes the game's UI positions scale linearly with resolution (i.e. as
    a fixed fraction of screen width/height). That's true for many games but
    not all - some anchor elements a fixed pixel offset from an edge instead,
    which this would scale incorrectly. Verify by comparing a couple of
    known-good coordinates at a second resolution before relying on this.
    """
    x_scale = current.width / reference.width
    y_scale = current.height / reference.height
    return [
        Region(
            name=r.name,
            left=round(r.left * x_scale),
            top=round(r.top * y_scale),
            width=round(r.width * x_scale),
            height=round(r.height * y_scale),
        )
        for r in regions
    ]
