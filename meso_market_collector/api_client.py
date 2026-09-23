"""Reporting a collected price row to Meso-Market-Tracker's backend.

`build_price_payload` is pure and directly testable. `post_price_row`'s
response handling (raising on a GraphQL-level error or an unconfirmed
write, not just an HTTP-level one - see its body-parsing below) is covered
too, with `requests.post` mocked; no test here makes a real network call.

See the sibling Meso-Market-Tracker project's backend/schema.py for the
PriceInput type and mutation this targets.
"""
from __future__ import annotations

import sys

import requests

from .config import get_tracker_api_url

RECORD_PRICE_MUTATION = """
mutation RecordPrice($price: PriceInput!) {
  recordPrice(price: $price)
}
"""

# String values a broken resolver could return in place of a real id - e.g.
# `str(price_id)` on a Tracker-side insert that itself returned `None` gives
# the *string* "None", which is non-empty and so would otherwise pass a bare
# truthiness check (see the incident this guards against in post_price_row).
_PLACEHOLDER_IDS = {"none", "null", "nan", "undefined"}

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


def build_price_payload(row: dict[str, int | None]) -> dict:
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
    skipped. A missing "Notes" still defaults to "". No timestamp is sent -
    PriceInput has no `datetime` field; Tracker stamps `occurred_at` itself
    at insert time (Meso-Market-Tracker/backend/schema.py's record_price),
    since the Collector is its only writer and there's nothing to gain from
    trusting a client clock over the server's own."""
    missing = [column for column in _FIELD_MAP if row.get(column) is None]
    if missing:
        message = (
            "Refusing to post price row to Tracker - missing/unreadable "
            f"price(s): {', '.join(missing)} (would otherwise be sent as a "
            "fabricated 0)"
        )
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    price = {"notes": row.get("Notes") or ""}
    for column, field in _FIELD_MAP.items():
        price[field] = int(row[column])
    return {"query": RECORD_PRICE_MUTATION, "variables": {"price": price}}


def post_price_row(row: dict[str, int | None], url: str | None = None, timeout: float = 10.0) -> None:
    if url is None:
        url = get_tracker_api_url()
    payload = build_price_payload(row)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()

    # A GraphQL server conventionally answers a rejected mutation with HTTP
    # 200 and the failure only in the body - raise_for_status() above can't
    # see that, so a resolver-level failure (e.g. a validation error) would
    # otherwise be silently treated as success, same category of problem
    # build_price_payload guards against for missing prices.
    body = response.json()
    errors = body.get("errors")
    if errors:
        message = f"Tracker rejected the price row - GraphQL errors: {errors}"
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    # record_price returns the new row's id as a String (Meso-Market-Tracker/
    # backend/schema.py) - a missing/empty id, or a placeholder like the
    # string "None", means it didn't actually record.
    price_id = body.get("data", {}).get("recordPrice")
    if not price_id or str(price_id).strip().lower() in _PLACEHOLDER_IDS:
        message = f"Tracker did not confirm the price row was recorded - response: {body!r}"
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    print(f"Recorded on Tracker as price id={price_id}", flush=True)
