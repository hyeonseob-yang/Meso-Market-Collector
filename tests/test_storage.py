import csv

from meso_market_collector.storage import append_price_row, append_region_reading


def test_append_region_reading_writes_header_and_row(tmp_path):
    csv_path = tmp_path / "region_readings.csv"

    append_region_reading("meso_price", 1234.0, csv_path=csv_path)
    append_region_reading("meso_price", 1250.5, csv_path=csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [r["item"] for r in rows] == ["meso_price", "meso_price"]
    assert [r["price"] for r in rows] == ["1234.0", "1250.5"]
    assert all(r["timestamp"] for r in rows)


def test_append_price_row_fills_missing_columns_blank(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price_row({"Average": 377}, csv_path=csv_path, timestamp="2/9/2026 17:50:00")

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "Date": "2/9/2026 17:50:00",
            "Average": "377",
            "Buy Buyout 100M": "",
            "Buy Buyout 1B": "",
            "Buy Buyout 10B": "",
            "Sell Buyout 100M": "",
            "Sell Buyout 1B": "",
            "Sell Buyout 10B": "",
            "Notes": "",
        }
    ]


def test_append_price_row_writes_template_format_header_and_row(tmp_path):
    csv_path = tmp_path / "price_history.csv"
    row = {
        "Average": 377,
        "Buy Buyout 100M": 382,
        "Buy Buyout 1B": 382,
        "Buy Buyout 10B": 382,
        "Sell Buyout 100M": 375,
        "Sell Buyout 1B": 375,
        "Sell Buyout 10B": 375,
    }

    append_price_row(row, csv_path=csv_path, timestamp="2/9/2026 17:50:00")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == [
            "Date",
            "Average",
            "Buy Buyout 100M",
            "Buy Buyout 1B",
            "Buy Buyout 10B",
            "Sell Buyout 100M",
            "Sell Buyout 1B",
            "Sell Buyout 10B",
            "Notes",
        ]
        rows = list(reader)

    assert rows == [
        {
            "Date": "2/9/2026 17:50:00",
            "Average": "377",
            "Buy Buyout 100M": "382",
            "Buy Buyout 1B": "382",
            "Buy Buyout 10B": "382",
            "Sell Buyout 100M": "375",
            "Sell Buyout 1B": "375",
            "Sell Buyout 10B": "375",
            "Notes": "",
        }
    ]


def test_append_price_row_uses_current_local_time_by_default(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price_row({}, csv_path=csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # M/D/YYYY H:MM:SS, no leading zeros on month/day/hour - matches
    # data/template.csv's existing hand-entered date format.
    import re

    assert re.match(r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$", rows[0]["Date"])
