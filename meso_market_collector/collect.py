"""Single-shot collection run: capture every configured region, parse, store.

Meant to be invoked once per run by a scheduler (cron), not looped forever:

    * * * * * cd /home/hya81/Meso-Market-Collector && .venv/bin/python -m meso_market_collector.collect
"""
from __future__ import annotations

from .capture import capture_region
from .config import load_regions
from .parser import parse_price
from .storage import append_region_reading, save_snapshot


def run() -> None:
    for region in load_regions():
        image = capture_region(region)
        price = parse_price(image)
        if price is None:
            # No parser wired up yet - keep the raw crop so it can be
            # labeled/inspected later instead of silently losing the data.
            save_snapshot(region.name, image)
        append_region_reading(region.name, price)


if __name__ == "__main__":
    run()
