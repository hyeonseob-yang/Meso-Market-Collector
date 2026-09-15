import pytest

from meso_market_collector.api_client import RECORD_PRICE_MUTATION, build_price_payload

# A fully-read row - every price field present, as record_prices leaves it
# when OCR succeeds on all of them.
COMPLETE_ROW = {
    "Average": 310,
    "Buy Buyout 100M": 313,
    "Buy Buyout 1B": 313,
    "Buy Buyout 10B": 313,
    "Sell Buyout 100M": 311,
    "Sell Buyout 1B": 311,
    "Sell Buyout 10B": 307,
}


def test_build_price_payload_maps_wide_row_to_price_input():
    payload = build_price_payload(COMPLETE_ROW, timestamp="2026-02-11T16:21:00")

    assert payload == {
        "query": RECORD_PRICE_MUTATION,
        "variables": {
            "price": {
                "datetime": "2026-02-11T16:21:00",
                "average": 310,
                "buy100M": 313,
                "buy1B": 313,
                "buy10B": 313,
                "sell100M": 311,
                "sell1B": 311,
                "sell10B": 307,
                "notes": "",
            }
        },
    }


def test_build_price_payload_sends_ints_not_floats():
    # PriceInput's price fields are `int` (Meso-Market-Tracker/backend/schema.py)
    payload = build_price_payload(COMPLETE_ROW, timestamp="2026-02-11T16:21:00")

    assert isinstance(payload["variables"]["price"]["average"], int)
    assert not isinstance(payload["variables"]["price"]["average"], bool)


def test_build_price_payload_raises_on_missing_price(capsys):
    # A `None` price (ScreenActions.record_prices' value when OCR couldn't
    # read a box) must never silently become a fabricated 0 sent to
    # Tracker - see the incident this guards against in api_client.py's
    # build_price_payload docstring.
    row = dict(COMPLETE_ROW, **{"Buy Buyout 100M": None})

    with pytest.raises(ValueError, match="Buy Buyout 100M"):
        build_price_payload(row, timestamp="2026-02-09T17:50:00")

    assert "Buy Buyout 100M" in capsys.readouterr().err


def test_build_price_payload_raises_on_missing_price_key():
    # Same as an explicit None - a column absent from the row entirely
    # (e.g. a routine.json authoring gap) is just as unreadable.
    row = {k: v for k, v in COMPLETE_ROW.items() if k != "Sell Buyout 10B"}

    with pytest.raises(ValueError, match="Sell Buyout 10B"):
        build_price_payload(row, timestamp="2026-02-09T17:50:00")


def test_build_price_payload_reports_all_missing_prices_at_once():
    row = {"Average": 377}

    with pytest.raises(ValueError) as exc_info:
        build_price_payload(row, timestamp="2026-02-09T17:50:00")

    message = str(exc_info.value)
    for column in ["Buy Buyout 100M", "Buy Buyout 1B", "Buy Buyout 10B", "Sell Buyout 100M", "Sell Buyout 1B", "Sell Buyout 10B"]:
        assert column in message


def test_build_price_payload_passes_through_notes():
    row = dict(COMPLETE_ROW, Notes="Fluctuating rapidly")

    payload = build_price_payload(row, timestamp="2026-02-04T17:30:00")

    assert payload["variables"]["price"]["notes"] == "Fluctuating rapidly"


def test_build_price_payload_defaults_notes_to_empty_string():
    payload = build_price_payload(COMPLETE_ROW, timestamp="2026-02-09T17:50:00")

    assert payload["variables"]["price"]["notes"] == ""


def test_build_price_payload_defaults_timestamp_to_now():
    payload = build_price_payload(COMPLETE_ROW)

    assert payload["variables"]["price"]["datetime"]
