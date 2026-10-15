import json

import pytest

from meso_market_collector import config
from meso_market_collector.config import Region, get_tracker_api_url, load_regions


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


def _write_column(path, left):
    path.write_text(json.dumps({"meso": {"left": left, "width": 150, "height": 30, "tops": [20]}}))


def test_load_regions_defaults_to_committed_file_without_local_override(tmp_path, monkeypatch):
    default_file = tmp_path / "regions.json"
    _write_column(default_file, left=10)
    monkeypatch.setattr(config, "REGIONS_FILE", default_file)
    monkeypatch.setattr(config, "LOCAL_REGIONS_FILE", tmp_path / "regions.local.json")

    assert load_regions()[0].left == 10


def test_load_regions_prefers_local_override_when_present(tmp_path, monkeypatch):
    default_file = tmp_path / "regions.json"
    local_file = tmp_path / "regions.local.json"
    _write_column(default_file, left=10)
    _write_column(local_file, left=99)
    monkeypatch.setattr(config, "REGIONS_FILE", default_file)
    monkeypatch.setattr(config, "LOCAL_REGIONS_FILE", local_file)

    assert load_regions()[0].left == 99


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
    assert regions[0].box == (10, 100, 150, 30)


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


def test_load_regions_rejects_an_entry_without_tops(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(json.dumps({"other_price": {"left": 300, "top": 50, "width": 80, "height": 20}}))

    with pytest.raises(ValueError, match="other_price.*tops"):
        load_regions(regions_file)


@pytest.fixture
def clean_env(monkeypatch):
    """Clears the settings the getters read, including any loaded from this
    machine's real .env."""
    monkeypatch.delenv("MESO_TRACKER_API_URL", raising=False)
    monkeypatch.delenv("MESO_TRACKER_RECORD_PRICE_SECRET", raising=False)


def test_get_tracker_api_url_requires_the_setting(clean_env):
    with pytest.raises(RuntimeError, match="MESO_TRACKER_API_URL"):
        get_tracker_api_url()


def test_get_tracker_api_url_reads_the_environment(clean_env, monkeypatch):
    monkeypatch.setenv("MESO_TRACKER_API_URL", "http://localhost:5000/price")

    assert get_tracker_api_url() == "http://localhost:5000/price"


def test_get_record_price_secret_is_none_when_unconfigured(clean_env):
    assert config.get_record_price_secret() is None


def test_get_record_price_secret_reads_the_environment(clean_env, monkeypatch):
    monkeypatch.setenv("MESO_TRACKER_RECORD_PRICE_SECRET", "from-env")

    assert config.get_record_price_secret() == "from-env"


def test_get_record_price_secret_treats_empty_value_as_unconfigured(clean_env, monkeypatch):
    monkeypatch.setenv("MESO_TRACKER_RECORD_PRICE_SECRET", "")

    assert config.get_record_price_secret() is None
