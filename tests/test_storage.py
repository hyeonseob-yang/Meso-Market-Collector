import csv
from datetime import datetime, timedelta, timezone

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


COLLECTED_AT = datetime(2026, 2, 9, 17, 50, tzinfo=timezone.utc)


def test_append_price_row_fills_missing_columns_blank(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price_row({"average": 377}, csv_path=csv_path, collected_at=COLLECTED_AT)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "datetime": "2026-02-09T17:50:00+00:00",
            "average": "377",
            "buy100M": "",
            "buy1B": "",
            "buy10B": "",
            "sell100M": "",
            "sell1B": "",
            "sell10B": "",
            "notes": "",
        }
    ]


def test_append_price_row_writes_tracker_named_header_and_row(tmp_path):
    csv_path = tmp_path / "price_history.csv"
    row = {
        "average": 377,
        "buy100M": 382,
        "buy1B": 382,
        "buy10B": 382,
        "sell100M": 375,
        "sell1B": 375,
        "sell10B": 375,
    }

    append_price_row(row, csv_path=csv_path, collected_at=COLLECTED_AT)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == [
            "datetime",
            "average",
            "buy100M",
            "buy1B",
            "buy10B",
            "sell100M",
            "sell1B",
            "sell10B",
            "notes",
        ]
        rows = list(reader)

    assert rows == [{"datetime": "2026-02-09T17:50:00+00:00", **{k: str(v) for k, v in row.items()}, "notes": ""}]


def test_append_price_row_writes_collected_at_in_utc(tmp_path):
    csv_path = tmp_path / "price_history.csv"
    pacific = datetime(2026, 10, 15, 3, 2, 41, tzinfo=timezone(timedelta(hours=-7)))

    append_price_row({}, csv_path=csv_path, collected_at=pacific)

    with open(csv_path, newline="", encoding="utf-8") as f:
        (row,) = csv.DictReader(f)

    assert row["datetime"] == "2026-10-15T10:02:41+00:00"


def test_append_price_row_uses_current_utc_time_by_default(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price_row({}, csv_path=csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        (row,) = csv.DictReader(f)

    assert datetime.fromisoformat(row["datetime"]).utcoffset() == timedelta(0)


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


def test_append_price_row_writes_notes(tmp_path):
    csv_path = tmp_path / "price_history.csv"

    append_price_row(
        {"average": 420, "buy100M": 42},
        csv_path=csv_path,
        collected_at=COLLECTED_AT,
        notes="Possible OCR misread: buy100M=42",
    )

    with open(csv_path, newline="", encoding="utf-8") as f:
        (row,) = csv.DictReader(f)

    assert row["buy100M"] == "42"
    assert row["notes"] == "Possible OCR misread: buy100M=42"


def _timeout_screenshot(tmp_path, taken_at):
    path = tmp_path / _snapshot_filename("timeout_quick_move_button", taken_at)
    path.write_bytes(b"fake png")
    return path


def test_clear_old_snapshots_keeps_failure_screenshots_for_their_own_longer_limit(tmp_path):
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    month_old_failure = _timeout_screenshot(tmp_path, datetime(2026, 2, 1, tzinfo=timezone.utc))
    month_old_price = tmp_path / _snapshot_filename("average_406",datetime(2026, 2, 1, tzinfo=timezone.utc))
    month_old_price.write_bytes(b"fake png")

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=now, failure_max_age_days=90)

    assert deleted == [month_old_price]
    assert month_old_failure.exists()


def test_clear_old_snapshots_deletes_failure_screenshots_past_their_own_limit(tmp_path):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    ancient_failure = _timeout_screenshot(tmp_path, datetime(2026, 2, 1, tzinfo=timezone.utc))

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=now, failure_max_age_days=90)

    assert deleted == [ancient_failure]


def test_clear_old_snapshots_treats_failure_screenshots_like_any_other_without_a_separate_limit(tmp_path):
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    month_old_failure = _timeout_screenshot(tmp_path, datetime(2026, 2, 1, tzinfo=timezone.utc))

    deleted = clear_old_snapshots(max_age_days=7, snapshot_dir=tmp_path, now=now)

    assert deleted == [month_old_failure]
