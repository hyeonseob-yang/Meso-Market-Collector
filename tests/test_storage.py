import csv

from meso_market_collector.storage import append_price


def test_append_price_writes_header_and_row(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price("meso_price", 1234.0, csv_path=csv_path)
    append_price("meso_price", 1250.5, csv_path=csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [r["item"] for r in rows] == ["meso_price", "meso_price"]
    assert [r["price"] for r in rows] == ["1234.0", "1250.5"]
    assert all(r["timestamp"] for r in rows)
