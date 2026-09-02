from meso_market_collector.api_client import RECORD_PRICE_MUTATION, build_price_payload


def test_build_price_payload_maps_wide_row_to_price_input():
    row = {
        "Average": 310,
        "Buy Buyout 100M": 313,
        "Buy Buyout 1B": 313,
        "Buy Buyout 10B": 313,
        "Sell Buyout 100M": 311,
        "Sell Buyout 1B": 311,
        "Sell Buyout 10B": 307,
    }

    payload = build_price_payload(row, timestamp="2026-02-11T16:21:00")

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
    payload = build_price_payload({"Average": 310}, timestamp="2026-02-11T16:21:00")

    assert isinstance(payload["variables"]["price"]["average"], int)
    assert not isinstance(payload["variables"]["price"]["average"], bool)


def test_build_price_payload_defaults_missing_prices_to_zero():
    payload = build_price_payload({"Average": 377}, timestamp="2026-02-09T17:50:00")

    price = payload["variables"]["price"]
    assert price["average"] == 377
    assert price["buy100M"] == 0
    assert price["buy1B"] == 0
    assert price["buy10B"] == 0
    assert price["sell100M"] == 0
    assert price["sell1B"] == 0
    assert price["sell10B"] == 0
    assert isinstance(price["buy100M"], int)


def test_build_price_payload_passes_through_notes():
    payload = build_price_payload({"Notes": "Fluctuating rapidly"}, timestamp="2026-02-04T17:30:00")

    assert payload["variables"]["price"]["notes"] == "Fluctuating rapidly"


def test_build_price_payload_defaults_notes_to_empty_string():
    payload = build_price_payload({"Average": 300}, timestamp="2026-02-09T17:50:00")

    assert payload["variables"]["price"]["notes"] == ""


def test_build_price_payload_defaults_timestamp_to_now():
    payload = build_price_payload({"Average": 300})

    assert payload["variables"]["price"]["datetime"]
