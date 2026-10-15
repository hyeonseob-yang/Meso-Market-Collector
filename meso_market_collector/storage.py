"""Append-only CSV storage for collected price points, plus raw snapshots."""
from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from .config import CSV_PATH, DATA_DIR, REGION_READINGS_CSV_PATH

# Captures the timestamp from save_snapshot's "<item>_<timestamp>.png".
_SNAPSHOT_TIMESTAMP_RE = re.compile(r"_(\d{8}T\d{12})\.png$")

FAILURE_SNAPSHOT_PREFIX = "timeout_"

REGION_READING_FIELDNAMES = ["timestamp", "item", "price"]

# One row per collection run, matching the hand-maintained price sheet.
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
    row: dict[str, int | None],
    csv_path: Path = CSV_PATH,
    timestamp: str | None = None,
    notes: str = "",
) -> None:
    """Append one row per collection run. `row` is keyed by
    PRICE_ROW_FIELDNAMES' price columns. Date is the current local time
    (the price sheet's convention, not UTC) unless `timestamp` is given."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    if timestamp is None:
        now = datetime.now()
        timestamp = f"{now.month}/{now.day}/{now.year} {now.hour}:{now.minute:02d}:{now.second:02d}"
    full_row = {"Date": timestamp, **row, "Notes": notes}
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRICE_ROW_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(full_row)


def append_region_reading(item: str, price: float | None, csv_path: Path = REGION_READINGS_CSV_PATH) -> None:
    """Append one row per captured region - collect.py's flat output, as
    opposed to append_price_row's one row per run."""
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
    max_age_days: float,
    snapshot_dir: Path = DATA_DIR / "snapshots",
    now: datetime | None = None,
    failure_max_age_days: float | None = None,
) -> list[Path]:
    """Delete snapshot PNGs older than `max_age_days` and return their
    paths. Age comes from the timestamp in the filename, not file mtime,
    which a copy or backup could reset; other files are left alone.
    Failure screenshots use `failure_max_age_days` instead, when given."""
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    failure_cutoff = cutoff if failure_max_age_days is None else now - timedelta(days=failure_max_age_days)

    deleted: list[Path] = []
    if not snapshot_dir.exists():
        return deleted
    for path in sorted(snapshot_dir.glob("*.png")):
        match = _SNAPSHOT_TIMESTAMP_RE.search(path.name)
        if not match:
            continue
        taken_at = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)
        if taken_at < (failure_cutoff if path.name.startswith(FAILURE_SNAPSHOT_PREFIX) else cutoff):
            path.unlink()
            deleted.append(path)
    return deleted
