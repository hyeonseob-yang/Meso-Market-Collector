import csv
from datetime import datetime, timezone

from meso_market_collector.storage import append_price_row, append_region_reading, clear_old_snapshots


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
    # the hand-maintained price sheet's existing hand-entered date format.
    import re

    assert re.match(r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$", rows[0]["Date"])


def _snapshot_filename(item: str, when: datetime) -> str:
    return f"{item}_{when.strftime('%Y%m%dT%H%M%S%f')}.png"


def test_clear_old_snapshots_deletes_files_past_max_age(tmp_path):
    now = datetime(2026, 1, 30, tzinfo=timezone.utc)
    old_file = tmp_path / _snapshot_filename("sell_meso_average", datetime(2026, 1, 1, tzinfo=timezone.utc))
    old_file.write_bytes(b"fake png")

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=now)

    assert deleted == [old_file]
    assert not old_file.exists()


def test_clear_old_snapshots_keeps_files_within_max_age(tmp_path):
    now = datetime(2026, 1, 30, tzinfo=timezone.utc)
    recent_file = tmp_path / _snapshot_filename("sell_meso_average", datetime(2026, 1, 29, tzinfo=timezone.utc))
    recent_file.write_bytes(b"fake png")

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=now)

    assert deleted == []
    assert recent_file.exists()


def test_clear_old_snapshots_ignores_non_matching_filenames(tmp_path):
    unrelated = tmp_path / "not_a_snapshot.png"
    unrelated.write_bytes(b"fake png")

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=datetime.now(timezone.utc))

    assert deleted == []
    assert unrelated.exists()


def test_clear_old_snapshots_handles_missing_directory(tmp_path):
    missing_dir = tmp_path / "does_not_exist"

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=missing_dir, now=datetime.now(timezone.utc))

    assert deleted == []
