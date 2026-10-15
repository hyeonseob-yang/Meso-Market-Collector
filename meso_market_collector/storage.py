"""Append-only CSV storage for collected price points, plus raw snapshots."""
from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from .config import CSV_PATH, DATA_DIR

# Captures the timestamp from save_snapshot's "<item>_<timestamp>.png".
_SNAPSHOT_TIMESTAMP_RE = re.compile(r"_(\d{8}T\d{12})\.png$")

FAILURE_SNAPSHOT_PREFIX = "timeout_"

# Named as in Tracker's PriceInput, so a row is posted as-is.
PRICE_FIELDS = ["average", "buy100M", "buy1B", "buy10B", "sell100M", "sell1B", "sell10B"]
PRICE_ROW_FIELDNAMES = ["datetime", *PRICE_FIELDS, "notes"]


def utc_timestamp(collected_at: datetime | None) -> str:
    """A row's `datetime` as UTC ISO 8601 text, as stored in the CSV and
    sent to Tracker."""
    if collected_at is None:
        raise ValueError("Row has no datetime (collection time)")
    if collected_at.tzinfo is None:
        raise ValueError("A row's datetime must be timezone-aware")
    return collected_at.astimezone(timezone.utc).isoformat()


def append_price_row(row: dict, csv_path: Path = CSV_PATH) -> None:
    """Append one row per collection run: its `datetime`, PRICE_FIELDS and
    `notes`."""
    line = {**row, "datetime": utc_timestamp(row.get("datetime")), "notes": row.get("notes") or ""}

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRICE_ROW_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(line)


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
