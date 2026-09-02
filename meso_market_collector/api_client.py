"""Reporting a collected price row to Meso-Market-Tracker's backend.

`build_price_payload` is pure and testable. `post_price_row` does the actual
network call and is untested directly (needs a reachable server), by design
- same split as screen_actions.py vs routine.py.

See the sibling Meso-Market-Tracker project's backend/schema.py for the
PriceInput type and mutation this targets.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

TRACKER_API_URL = "http://localhost:5000/price"

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
    the same reading dict around for both. Missing price columns default
    to 0.0, matching PriceInput's non-nullable float fields; a missing
    "Notes" defaults to "". `timestamp` mirrors append_price_row's
    parameter (mainly for tests) - defaults to now (UTC, ISO 8601), unlike
    append_price_row's local-time format, since this feeds an API rather
    than a hand-read CSV."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    price = {"datetime": timestamp, "notes": row.get("Notes") or ""}
    for column, field in _FIELD_MAP.items():
        value = row.get(column)
        price[field] = float(value) if value is not None else 0.0
    return {"query": RECORD_PRICE_MUTATION, "variables": {"price": price}}


def post_price_row(row: dict[str, int | None], url: str = TRACKER_API_URL, timeout: float = 10.0) -> None:
    payload = build_price_payload(row)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
