import json

from meso_market_collector.config import DEFAULT_TRACKER_API_URL, Region, get_tracker_api_url, load_regions


def test_load_regions_parses_named_boxes(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps(
            {
                "meso_price": {"left": 10, "top": 20, "width": 150, "height": 30},
            }
        )
    )

    regions = load_regions(regions_file)

    assert regions == [Region(name="meso_price", left=10, top=20, width=150, height=30)]
    assert regions[0].box == (10, 20, 150, 30)


def test_load_regions_expands_column_shorthand(tmp_path):
    """A column shares left/width/height across rows; only `tops` varies,
    and each row becomes its own named Region (`<key>_1`, `<key>_2`, ...)."""
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps(
            {
                "meso": {
                    "left": 10,
                    "width": 150,
                    "height": 30,
                    "tops": [100, 140, 180, 220],
                },
            }
        )
    )

    regions = load_regions(regions_file)

    assert regions == [
        Region(name="meso_1", left=10, top=100, width=150, height=30),
        Region(name="meso_2", left=10, top=140, width=150, height=30),
        Region(name="meso_3", left=10, top=180, width=150, height=30),
        Region(name="meso_4", left=10, top=220, width=150, height=30),
    ]


def test_load_regions_column_shorthand_accepts_explicit_names(tmp_path):
    """An optional `names` list overrides the default `<key>_<i>` naming,
    for when the index position isn't meaningful on its own."""
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps(
            {
                "meso": {
                    "left": 10,
                    "width": 150,
                    "height": 30,
                    "tops": [100, 140, 180, 220],
                    "names": ["meso_average", "meso_100m", "meso_1b", "meso_10b"],
                },
            }
        )
    )

    regions = load_regions(regions_file)

    assert regions == [
        Region(name="meso_average", left=10, top=100, width=150, height=30),
        Region(name="meso_100m", left=10, top=140, width=150, height=30),
        Region(name="meso_1b", left=10, top=180, width=150, height=30),
        Region(name="meso_10b", left=10, top=220, width=150, height=30),
    ]


def test_load_regions_mixes_boxes_and_columns(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps(
            {
                "meso": {"left": 10, "width": 150, "height": 30, "tops": [100, 140]},
                "other_price": {"left": 300, "top": 50, "width": 80, "height": 20},
            }
        )
    )

    regions = load_regions(regions_file)

    assert regions == [
        Region(name="meso_1", left=10, top=100, width=150, height=30),
        Region(name="meso_2", left=10, top=140, width=150, height=30),
        Region(name="other_price", left=300, top=50, width=80, height=20),
    ]


def test_get_tracker_api_url_defaults_to_deployed_endpoint(monkeypatch):
    monkeypatch.delenv("MESO_TRACKER_API_URL", raising=False)

    assert get_tracker_api_url() == DEFAULT_TRACKER_API_URL


def test_get_tracker_api_url_reads_env_override(monkeypatch):
    monkeypatch.setenv("MESO_TRACKER_API_URL", "http://localhost:5000/price")

    assert get_tracker_api_url() == "http://localhost:5000/price"
