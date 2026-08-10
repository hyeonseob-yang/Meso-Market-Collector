"""Append-only CSV storage for collected price points, plus raw snapshots."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .config import CSV_PATH, DATA_DIR

FIELDNAMES = ["timestamp", "item", "price"]


def append_price(item: str, price: float | None, csv_path: Path = CSV_PATH) -> None:
    """Append one row to the CSV, creating it (with header) if needed."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
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
    """Save the raw captured region, useful while price-parsing isn't wired up yet."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = snapshot_dir / f"{item}_{timestamp}.png"
    image.save(path)
    return path
