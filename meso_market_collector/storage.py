"""Append-only CSV storage for collected price points, plus raw snapshots."""
from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from .config import CSV_PATH, DATA_DIR, REGION_READINGS_CSV_PATH

# Matches the "<item>_<timestamp>.png" naming save_snapshot uses, e.g.
# "sell_meso_average_20260828T103454672715.png" - captures just the
# timestamp portion (%Y%m%dT%H%M%S%f).
_SNAPSHOT_TIMESTAMP_RE = re.compile(r"_(\d{8}T\d{12})\.png$")

REGION_READING_FIELDNAMES = ["timestamp", "item", "price"]

# Matches data/template.csv (a hand-maintained example of the desired
# output) - one row per collection run, not per box.
PRICE_ROW_FIELDNAMES = [
    "Date",
    "Average",
    "Buy Buyout 100M",
    "Buy Buyout 1B",
    "Buy Buyout 10B",
    "Sell Buyout 100M",
    "Sell Buyout 1B",
    "Sell Buyout 10B",
    "Notes",
]


def append_price_row(
    row: dict[str, int | None], csv_path: Path = CSV_PATH, timestamp: str | None = None
) -> None:
    """Append one wide-format row (see data/template.csv) - one row per
    collection run. `row` should already have PRICE_ROW_FIELDNAMES'
    price columns as keys (e.g. "Average", "Buy Buyout 100M") - see
    ScreenActions.record_prices, which captures directly under these
    names. Date (local time, matching the template's hand-entered
    convention - not the UTC timestamps append_region_reading uses) and a
    blank Notes column are filled in automatically unless a `timestamp` is
    given (mainly for tests)."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    if timestamp is None:
        now = datetime.now()
        timestamp = f"{now.month}/{now.day}/{now.year} {now.hour}:{now.minute:02d}:{now.second:02d}"
    full_row = {"Date": timestamp, **row, "Notes": ""}
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRICE_ROW_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(full_row)


def append_region_reading(item: str, price: float | None, csv_path: Path = REGION_READINGS_CSV_PATH) -> None:
    """Append one row per captured region (flat, one row per box) - used by
    the generic collect.py entrypoint, which captures arbitrary configured
    regions without a sell/buy-tab concept. See append_price_row for the
    main session's wide, per-run output matching data/template.csv."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REGION_READING_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "item": item,
                "price": price,
            }
        )


def save_snapshot(item: str, image: Image.Image, snapshot_dir: Path = DATA_DIR / "snapshots") -> Path:
    """Save the raw captured region, for checking OCR against what it read."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = snapshot_dir / f"{item}_{timestamp}.png"
    image.save(path)
    return path


def clear_old_snapshots(
    max_age_days: float, snapshot_dir: Path = DATA_DIR / "snapshots", now: datetime | None = None
) -> list[Path]:
    """Delete snapshot PNGs older than `max_age_days`, going by the
    timestamp embedded in each filename (see save_snapshot) rather than
    filesystem mtime, which copying/backing up a file could reset.
    Anything not matching that naming is left alone. Returns the paths
    that were actually deleted, for logging/testing. `now` is mainly for
    tests - defaults to the current UTC time."""
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    deleted: list[Path] = []
    if not snapshot_dir.exists():
        return deleted
    for path in sorted(snapshot_dir.glob("*.png")):
        match = _SNAPSHOT_TIMESTAMP_RE.search(path.name)
        if not match:
            continue
        taken_at = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)
        if taken_at < cutoff:
            path.unlink()
            deleted.append(path)
    return deleted
