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
    effect. Like any setting here, it can also come from .env (see _env)."""
    return _env("MESO_TRACKER_API_URL") or DEFAULT_TRACKER_API_URL


# Secrets and other environment-style settings (gitignored - never commit
# it). Plain KEY=VALUE lines:
#   MESO_TRACKER_RECORD_PRICE_SECRET=...
ENV_FILE = PROJECT_ROOT / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file's KEY=VALUE lines (blank lines and # comments
    skipped, optional `export ` prefix and surrounding quotes stripped).
    Read by hand rather than via python-dotenv so the collector has no
    extra package to install on every machine."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _env(name: str) -> str | None:
    """A setting from the real environment, else from the .env file, else
    None. The real environment wins (the usual dotenv convention). The
    file matters for the scheduled session task, which doesn't reliably
    see an environment variable set after the last logon. Read fresh on
    each call so a value set after import - e.g. by a test - takes effect."""
    return os.environ.get(name) or _read_env_file(ENV_FILE).get(name) or None


def get_record_price_secret() -> str | None:
    """The shared secret Tracker's recordPrice mutation requires (sent as
    the x-record-price-secret header - see Meso-Market-Tracker's
    record_price_secret Terraform variable), from
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
