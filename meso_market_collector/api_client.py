"""Reporting a collected price row to Meso-Market-Tracker's backend.

`build_price_payload` is pure and testable. `post_price_row` does the actual
network call and is untested directly (needs a reachable server), by design
- same split as screen_actions.py vs routine.py.

See the sibling Meso-Market-Tracker project's backend/schema.py for the
PriceInput type and mutation this targets.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import requests

from .config import get_tracker_api_url

RECORD_PRICE_MUTATION = """
mutation RecordPrice($price: PriceInput!) {
  recordPrice(price: $price)
}
"""

# Maps our wide-row column names (storage.PRICE_ROW_FIELDNAMES) to the
# Tracker's PriceInput field names (Meso-Market-Tracker/backend/schema.py).
_FIELD_MAP = {
    "Average": "average",
    "Buy Buyout 100M": "buy100M",
    "Buy Buyout 1B": "buy1B",
    "Buy Buyout 10B": "buy10B",
    "Sell Buyout 100M": "sell100M",
    "Sell Buyout 1B": "sell1B",
    "Sell Buyout 10B": "sell10B",
}


def build_price_payload(row: dict[str, int | None], timestamp: str | None = None) -> dict:
    """Build the GraphQL request body for recording one collected price
    row. `row` uses the same wide-row keys as storage.append_price_row
    (e.g. "Average", "Buy Buyout 100M") - see ScreenActions, which keeps
    the same reading dict around for both. PriceInput's price fields are
    non-nullable ints, but a missing/unreadable OCR reading is `None` here
    (see ScreenActions.record_prices) - rather than silently coercing that
    to 0 (a real, wrong value indistinguishable from an actual 0 reading),
    this raises so the caller stops instead of reporting fabricated data to
    Tracker. The CSV row from save_price_row is unaffected either way,
    since it's written before this ever runs - only the Tracker post is
    skipped. A missing "Notes" still defaults to "". `timestamp` mirrors
    append_price_row's parameter (mainly for tests) - defaults to now
    (UTC, ISO 8601), unlike append_price_row's local-time format, since
    this feeds an API rather than a hand-read CSV."""
    missing = [column for column in _FIELD_MAP if row.get(column) is None]
    if missing:
        message = (
            "Refusing to post price row to Tracker - missing/unreadable "
            f"price(s): {', '.join(missing)} (would otherwise be sent as a "
            "fabricated 0)"
        )
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    price = {"datetime": timestamp, "notes": row.get("Notes") or ""}
    for column, field in _FIELD_MAP.items():
        price[field] = int(row[column])
    return {"query": RECORD_PRICE_MUTATION, "variables": {"price": price}}


def post_price_row(row: dict[str, int | None], url: str | None = None, timeout: float = 10.0) -> None:
    if url is None:
        url = get_tracker_api_url()
    payload = build_price_payload(row)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
