"""Append-only CSV storage for collected price points, plus raw snapshots."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .config import CSV_PATH, DATA_DIR, REGION_READINGS_CSV_PATH

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


def price_row_from_readings(readings: dict[str, int | None]) -> dict[str, int | None]:
    """Map raw per-box OCR readings (keyed like "sell_meso_1", "buy_meso_2",
    as produced by ScreenActions.record_prices) into the wide-row columns
    used by append_price_row. meso_1 is a single "Average" display that's
    identical regardless of which tab is showing (confirmed: it read the
    same value on both the Sell and Buy tab in testing), so either
    reading of it works - prefer the Sell one, falling back to Buy's if
    that one's missing/unreadable."""
    average = readings.get("sell_meso_1")
    if average is None:
        average = readings.get("buy_meso_1")
    return {
        "Average": average,
        "Buy Buyout 100M": readings.get("buy_meso_2"),
        "Buy Buyout 1B": readings.get("buy_meso_3"),
        "Buy Buyout 10B": readings.get("buy_meso_4"),
        "Sell Buyout 100M": readings.get("sell_meso_2"),
        "Sell Buyout 1B": readings.get("sell_meso_3"),
        "Sell Buyout 10B": readings.get("sell_meso_4"),
    }


def append_price_row(
    row: dict[str, int | None], csv_path: Path = CSV_PATH, timestamp: str | None = None
) -> None:
    """Append one wide-format row (see data/template.csv) - one row per
    collection run. `row` should already be shaped like
    price_row_from_readings' output; Date (local time, matching the
    template's hand-entered convention - not the UTC timestamps
    append_region_reading uses) and a blank Notes column are filled in
    automatically unless a `timestamp` is given (mainly for tests)."""
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
    """Save the raw captured region, useful whenever OCR can't read it."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = snapshot_dir / f"{item}_{timestamp}.png"
    image.save(path)
    return path
