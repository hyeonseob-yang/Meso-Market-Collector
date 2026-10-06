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
# Per-machine override (gitignored) - coordinates depend on this machine's
# screen/window layout, so edit this instead of the committed default.
LOCAL_REGIONS_FILE = PROJECT_ROOT / "config" / "regions.local.json"
TEMPLATES_DIR = PROJECT_ROOT / "assets" / "templates"
# Per-machine template overrides (gitignored) - same reason as
# regions.local.json: a template only matches at the resolution/UI scale it
# was snipped at, so machines with different displays need their own.
LOCAL_TEMPLATES_DIR = PROJECT_ROOT / "assets" / "templates.local"
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


# Per-machine Tracker settings (gitignored via config/*.local.json) - holds
# the shared secret, which must never be committed:
#   {"record_price_secret": "..."}
LOCAL_TRACKER_FILE = PROJECT_ROOT / "config" / "tracker.local.json"


def get_record_price_secret() -> str | None:
    """The shared secret Tracker's recordPrice mutation requires (sent as
    the x-record-price-secret header - see Meso-Market-Tracker's
    record_price_secret Terraform variable), or None if this machine has
    none configured. MESO_TRACKER_RECORD_PRICE_SECRET wins if set;
    otherwise it's read from config/tracker.local.json, which is the
    dependable option for the scheduled session task (a task doesn't
    reliably see an environment variable set after the last logon).
    Resolved fresh on each call, like get_tracker_api_url."""
    secret = os.environ.get("MESO_TRACKER_RECORD_PRICE_SECRET")
    if not secret and LOCAL_TRACKER_FILE.exists():
        with open(LOCAL_TRACKER_FILE, "r", encoding="utf-8") as f:
            secret = json.load(f).get("record_price_secret")
    return secret or None


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
    """regions.local.json if it exists, else the committed regions.json.
    Resolved fresh on each call so a local file created after import still
    takes effect."""
    return LOCAL_REGIONS_FILE if LOCAL_REGIONS_FILE.exists() else REGIONS_FILE


def get_template_path(name: str) -> Path:
    """assets/templates.local/<name> if it exists, else the committed
    assets/templates/<name>. Checked per file, so a machine only needs to
    override the templates that actually differ on it."""
    local = LOCAL_TEMPLATES_DIR / name
    return local if local.exists() else TEMPLATES_DIR / name


def load_regions(path: Path | None = None) -> list[Region]:
    """Load named regions, or "column" shorthand entries, from `path` -
    or, if not given, from get_regions_file().

    A plain entry is one box: {"left", "top", "width", "height"}.

    A column entry shares left/width/height across several rows that only
    differ in vertical position - {"left", "width", "height", "tops": [...]}
    - and expands into one Region per row, named "<key>_1", "<key>_2", ...
    by default, or using an optional "names" list instead (paired
    positionally with "tops") when the index position on its own isn't
    meaningful. Use this when boxes are stacked in a column (e.g. Sell/Buy
    Meso price rows); fall back to plain boxes for anything that isn't.
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
