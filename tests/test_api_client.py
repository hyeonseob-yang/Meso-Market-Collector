from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from meso_market_collector.api_client import RECORD_PRICE_MUTATION, build_price_payload, post_price_row

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
    payload = build_price_payload(COMPLETE_ROW)

    assert payload == {
        "query": RECORD_PRICE_MUTATION,
        "variables": {
            "price": {
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
    payload = build_price_payload(COMPLETE_ROW)

    assert isinstance(payload["variables"]["price"]["average"], int)
    assert not isinstance(payload["variables"]["price"]["average"], bool)


def test_build_price_payload_sends_no_datetime_without_collected_at():
    # No collection time given - Tracker stamps the row itself at insert
    # time. See build_price_payload's docstring.
    payload = build_price_payload(COMPLETE_ROW)

    assert "datetime" not in payload["variables"]["price"]


def test_build_price_payload_sends_collected_at_as_utc_iso_datetime():
    collected_at = datetime(2026, 9, 30, 23, 19, 51, tzinfo=timezone(timedelta(hours=-7)))

    payload = build_price_payload(COMPLETE_ROW, collected_at=collected_at)

    # Converted to UTC, whatever zone it was given in.
    assert payload["variables"]["price"]["datetime"] == "2026-10-01T06:19:51+00:00"


def test_build_price_payload_rejects_naive_collected_at():
    # A naive time would be silently read as whatever zone Tracker assumes.
    with pytest.raises(ValueError, match="timezone-aware"):
        build_price_payload(COMPLETE_ROW, collected_at=datetime(2026, 9, 30, 23, 19, 51))


def test_build_price_payload_raises_on_missing_price(capsys):
    # A `None` price (ScreenActions.record_prices' value when OCR couldn't
    # read a box) must never silently become a fabricated 0 sent to
    # Tracker - see the incident this guards against in api_client.py's
    # build_price_payload docstring.
    row = dict(COMPLETE_ROW, **{"Buy Buyout 100M": None})

    with pytest.raises(ValueError, match="Buy Buyout 100M"):
        build_price_payload(row)

    assert "Buy Buyout 100M" in capsys.readouterr().err


def test_build_price_payload_raises_on_missing_price_key():
    # Same as an explicit None - a column absent from the row entirely
    # (e.g. a routine.json authoring gap) is just as unreadable.
    row = {k: v for k, v in COMPLETE_ROW.items() if k != "Sell Buyout 10B"}

    with pytest.raises(ValueError, match="Sell Buyout 10B"):
        build_price_payload(row)


def test_build_price_payload_reports_all_missing_prices_at_once():
    row = {"Average": 377}

    with pytest.raises(ValueError) as exc_info:
        build_price_payload(row)

    message = str(exc_info.value)
    for column in ["Buy Buyout 100M", "Buy Buyout 1B", "Buy Buyout 10B", "Sell Buyout 100M", "Sell Buyout 1B", "Sell Buyout 10B"]:
        assert column in message


def test_build_price_payload_passes_through_notes():
    row = dict(COMPLETE_ROW, Notes="Fluctuating rapidly")

    payload = build_price_payload(row)

    assert payload["variables"]["price"]["notes"] == "Fluctuating rapidly"


def test_build_price_payload_defaults_notes_to_empty_string():
    payload = build_price_payload(COMPLETE_ROW)

    assert payload["variables"]["price"]["notes"] == ""


@pytest.fixture(autouse=True)
def no_secret(monkeypatch):
    # Never read this machine's real .env file or environment variable.
    monkeypatch.setattr("meso_market_collector.api_client.get_record_price_secret", lambda: None)


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_sends_secret_header_when_configured(mock_post, monkeypatch, capsys):
    monkeypatch.setattr("meso_market_collector.api_client.get_record_price_secret", lambda: "s3cret")
    mock_post.return_value = _fake_response({"data": {"recordPrice": "42"}})

    post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")

    assert mock_post.call_args.kwargs["headers"] == {"x-record-price-secret": "s3cret"}
    out = capsys.readouterr()
    assert "s3cret" not in out.out + out.err  # never logged


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_posts_without_header_and_warns_when_no_secret(mock_post, capsys):
    mock_post.return_value = _fake_response({"data": {"recordPrice": "42"}})

    post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")

    assert mock_post.call_args.kwargs["headers"] == {}
    assert "no Tracker secret configured" in capsys.readouterr().out


def _fake_response(body, raise_for_status_error=None):
    response = MagicMock()
    response.json.return_value = body
    response.raise_for_status.side_effect = raise_for_status_error
    return response


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_succeeds_when_recordPrice_returns_an_id(mock_post, capsys):
    # record_price returns the new row's id as a String (schema.py), not a
    # boolean.
    mock_post.return_value = _fake_response({"data": {"recordPrice": "42"}})

    post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")  # must not raise

    args, kwargs = mock_post.call_args
    assert args[0] == "https://tracker.example/graphql"
    assert kwargs["json"]["variables"]["price"]["average"] == COMPLETE_ROW["Average"]
    assert "datetime" not in kwargs["json"]["variables"]["price"]
    # printed (not just silently discarded) so the id is available for
    # cross-referencing against Tracker/Supabase later.
    assert "42" in capsys.readouterr().out


COLLECTED_AT = datetime(2026, 10, 1, 6, 19, 51, tzinfo=timezone.utc)
UNKNOWN_DATETIME_FIELD = {
    "errors": [{"message": "Field 'datetime' is not defined by type 'PriceInput'."}],
    "data": None,
}


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_sends_collected_at(mock_post):
    mock_post.return_value = _fake_response({"data": {"recordPrice": "42"}})

    post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql", collected_at=COLLECTED_AT)

    assert mock_post.call_count == 1
    sent = mock_post.call_args.kwargs["json"]["variables"]["price"]
    assert sent["datetime"] == "2026-10-01T06:19:51+00:00"


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_raises_when_tracker_rejects_the_datetime(mock_post):
    mock_post.return_value = _fake_response(UNKNOWN_DATETIME_FIELD)

    with pytest.raises(ValueError, match="datetime"):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql", collected_at=COLLECTED_AT)

    assert mock_post.call_count == 1


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_raises_on_graphql_errors(mock_post, capsys):
    # HTTP 200 (raise_for_status doesn't fire) but the body carries a
    # GraphQL-level error - the exact case that slipped through silently
    # before this check existed (caught via CloudWatch, not the Collector).
    mock_post.return_value = _fake_response(
        {"errors": [{"message": "average must be a positive integer"}], "data": None}
    )

    with pytest.raises(ValueError, match="average must be a positive integer"):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")

    assert "average must be a positive integer" in capsys.readouterr().err


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_raises_when_recordPrice_id_is_empty(mock_post):
    # No `errors`, but the mutation didn't actually return an id either -
    # still shouldn't be treated as a successful write.
    mock_post.return_value = _fake_response({"data": {"recordPrice": ""}})

    with pytest.raises(ValueError, match="did not confirm"):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_raises_when_data_missing_entirely(mock_post):
    mock_post.return_value = _fake_response({})

    with pytest.raises(ValueError, match="did not confirm"):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")


@patch("meso_market_collector.api_client.requests.post")
@pytest.mark.parametrize("placeholder", ["None", "null", "NaN", "undefined", "  none  "])
def test_post_price_row_raises_on_placeholder_id(mock_post, placeholder):
    # Real incident: a Tracker-side insert that itself returned `None` had
    # its resolver do `str(price_id)`, producing the literal string "None" -
    # non-empty, so a bare truthiness check let it through as a false
    # success. Covers case and surrounding whitespace too.
    mock_post.return_value = _fake_response({"data": {"recordPrice": placeholder}})

    with pytest.raises(ValueError, match="did not confirm"):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")


@patch("meso_market_collector.api_client.requests.post")
def test_post_price_row_still_propagates_http_level_errors(mock_post):
    # raise_for_status() must still fire, and fire before any body parsing -
    # a transport-level failure shouldn't be masked by the new checks below it.
    mock_post.return_value = _fake_response(
        {"unreachable": "body should never be read"},
        raise_for_status_error=requests.HTTPError("500 Server Error"),
    )

    with pytest.raises(requests.HTTPError):
        post_price_row(COMPLETE_ROW, url="https://tracker.example/graphql")
