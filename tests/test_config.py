import json

import pytest

from meso_market_collector import config
from meso_market_collector.config import DEFAULT_TRACKER_API_URL, Region, get_tracker_api_url, load_regions


def test_get_template_path_prefers_local_copy_per_file(tmp_path, monkeypatch):
    shared, local = tmp_path / "templates", tmp_path / "templates.local"
    shared.mkdir()
    local.mkdir()
    (shared / "login_button.png").write_bytes(b"shared")
    (shared / "quick_move_button.png").write_bytes(b"shared")
    (local / "login_button.png").write_bytes(b"local")
    monkeypatch.setattr(config, "TEMPLATES_DIR", shared)
    monkeypatch.setattr(config, "LOCAL_TEMPLATES_DIR", local)

    assert config.get_template_path("login_button.png") == local / "login_button.png"
    assert config.get_template_path("quick_move_button.png") == shared / "quick_move_button.png"


def test_get_template_path_falls_back_without_local_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(config, "LOCAL_TEMPLATES_DIR", tmp_path / "missing")

    assert config.get_template_path("login_button.png") == tmp_path / "templates" / "login_button.png"


def _write_box(path, left):
    path.write_text(json.dumps({"meso_price": {"left": left, "top": 20, "width": 150, "height": 30}}))


def test_load_regions_defaults_to_committed_file_without_local_override(tmp_path, monkeypatch):
    default_file = tmp_path / "regions.json"
    _write_box(default_file, left=10)
    monkeypatch.setattr(config, "REGIONS_FILE", default_file)
    monkeypatch.setattr(config, "LOCAL_REGIONS_FILE", tmp_path / "regions.local.json")

    assert load_regions()[0].left == 10


def test_load_regions_prefers_local_override_when_present(tmp_path, monkeypatch):
    default_file = tmp_path / "regions.json"
    local_file = tmp_path / "regions.local.json"
    _write_box(default_file, left=10)
    _write_box(local_file, left=99)
    monkeypatch.setattr(config, "REGIONS_FILE", default_file)
    monkeypatch.setattr(config, "LOCAL_REGIONS_FILE", local_file)

    assert load_regions()[0].left == 99


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


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    """Points config at an empty temp .env (never this machine's real one)
    and clears the real environment variables it would read."""
    path = tmp_path / ".env"
    monkeypatch.setattr(config, "ENV_FILE", path)
    monkeypatch.delenv("MESO_TRACKER_API_URL", raising=False)
    monkeypatch.delenv("MESO_TRACKER_RECORD_PRICE_SECRET", raising=False)
    return path


def test_get_tracker_api_url_defaults_to_deployed_endpoint(env_file):
    assert get_tracker_api_url() == DEFAULT_TRACKER_API_URL


def test_get_tracker_api_url_reads_env_override(env_file, monkeypatch):
    monkeypatch.setenv("MESO_TRACKER_API_URL", "http://localhost:5000/price")

    assert get_tracker_api_url() == "http://localhost:5000/price"


def test_get_tracker_api_url_reads_env_file(env_file):
    env_file.write_text("MESO_TRACKER_API_URL=http://localhost:5000/price\n")

    assert get_tracker_api_url() == "http://localhost:5000/price"


def test_env_file_ignores_a_comment_after_a_value(env_file):
    env_file.write_text("MESO_TRACKER_API_URL=http://localhost:5000/price # dev server\n")

    assert get_tracker_api_url() == "http://localhost:5000/price"


def test_get_record_price_secret_is_none_when_unconfigured(env_file):
    assert config.get_record_price_secret() is None


def test_get_record_price_secret_reads_env_file(env_file):
    env_file.write_text("# Tracker\n\nMESO_TRACKER_RECORD_PRICE_SECRET=from-file\n")

    assert config.get_record_price_secret() == "from-file"


@pytest.mark.parametrize(
    "line",
    [
        'MESO_TRACKER_RECORD_PRICE_SECRET="a=b c"',
        "MESO_TRACKER_RECORD_PRICE_SECRET='a=b c'",
        "export MESO_TRACKER_RECORD_PRICE_SECRET = a=b c  ",
    ],
)
def test_get_record_price_secret_handles_quotes_export_and_equals_in_value(env_file, line):
    env_file.write_text(line + "\n")

    assert config.get_record_price_secret() == "a=b c"


def test_get_record_price_secret_real_environment_wins_over_env_file(env_file, monkeypatch):
    env_file.write_text("MESO_TRACKER_RECORD_PRICE_SECRET=from-file\n")
    monkeypatch.setenv("MESO_TRACKER_RECORD_PRICE_SECRET", "from-env")

    assert config.get_record_price_secret() == "from-env"


def test_get_record_price_secret_treats_empty_value_as_unconfigured(env_file):
    env_file.write_text("MESO_TRACKER_RECORD_PRICE_SECRET=\n")

    assert config.get_record_price_secret() is None
