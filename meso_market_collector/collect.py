"""Single-shot collection run: capture every configured region, parse, store.

Runs once per invocation, with the game already on the Meso Market:

    python -m meso_market_collector.collect
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
            # OCR couldn't read it: keep the crop to check by hand.
            save_snapshot(region.name, image)
        append_region_reading(region.name, price)


if __name__ == "__main__":
    run()
