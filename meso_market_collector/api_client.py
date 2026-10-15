"""Reporting a collected price row to Meso-Market-Tracker's backend.

Targets the PriceInput type and recordPrice mutation in
Meso-Market-Tracker/backend/schema.py.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import requests

from .config import get_record_price_secret, get_tracker_api_url

RECORD_PRICE_SECRET_HEADER = "x-record-price-secret"

RECORD_PRICE_MUTATION = """
mutation RecordPrice($price: PriceInput!) {
  recordPrice(price: $price)
}
"""

# Strings a broken resolver can return in place of a real id - e.g.
# str(None) when the insert failed. Non-empty, so a truthiness check passes.
_PLACEHOLDER_IDS = {"none", "null", "nan", "undefined"}

# CSV column name (storage.PRICE_ROW_FIELDNAMES) -> PriceInput field name.
_FIELD_MAP = {
    "Average": "average",
    "Buy Buyout 100M": "buy100M",
    "Buy Buyout 1B": "buy1B",
    "Buy Buyout 10B": "buy10B",
    "Sell Buyout 100M": "sell100M",
    "Sell Buyout 1B": "sell1B",
    "Sell Buyout 10B": "sell10B",
}


def build_price_payload(row: dict[str, int | None], collected_at: datetime | None = None) -> dict:
    """Build the GraphQL request body for one price row, keyed like
    storage.append_price_row's rows.

    Raises if any price is missing (None): sending 0 instead would record
    a fabricated value. `collected_at` (timezone-aware) is sent as
    `datetime` in UTC so a row posted late keeps its real time; without
    it, Tracker stamps the row at insert time."""
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
    if collected_at is not None:
        if collected_at.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware")
        price["datetime"] = collected_at.astimezone(timezone.utc).isoformat()

    for column, field in _FIELD_MAP.items():
        price[field] = int(row[column])
    return {"query": RECORD_PRICE_MUTATION, "variables": {"price": price}}


def _post(url: str, payload: dict, timeout: float) -> dict:
    # Without a secret the post is still attempted: it works if Tracker
    # doesn't enforce one, and fails with an error if it does.
    headers = {}
    secret = get_record_price_secret()
    if secret:
        headers[RECORD_PRICE_SECRET_HEADER] = secret
    else:
        print(
            "WARNING: no Tracker secret configured "
            "(MESO_TRACKER_RECORD_PRICE_SECRET, e.g. in .env) - posting without one",
            flush=True,
        )
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_price_row(
    row: dict[str, int | None],
    url: str | None = None,
    timeout: float = 10.0,
    collected_at: datetime | None = None,
) -> None:
    if url is None:
        url = get_tracker_api_url()
    body = _post(url, build_price_payload(row, collected_at), timeout)

    # GraphQL reports a rejected mutation as HTTP 200 with the failure in
    # the body, which raise_for_status() can't see.
    errors = body.get("errors")
    if errors:
        message = f"Tracker rejected the price row - GraphQL errors: {errors}"
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    # recordPrice returns the new row's id; an empty or placeholder id
    # means nothing was recorded.
    price_id = body.get("data", {}).get("recordPrice")
    if not price_id or str(price_id).strip().lower() in _PLACEHOLDER_IDS:
        message = f"Tracker did not confirm the price row was recorded - response: {body!r}"
        print(message, file=sys.stderr, flush=True)
        raise ValueError(message)
    print(f"Recorded on Tracker as price id={price_id}", flush=True)
