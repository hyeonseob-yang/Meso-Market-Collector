import json

from meso_market_collector.config import (
    Region,
    Resolution,
    load_reference_resolution,
    load_regions,
    scale_regions,
)


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


def test_load_regions_ignores_reference_resolution_key(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps(
            {
                "reference_resolution": {"width": 2560, "height": 1440},
                "meso_price": {"left": 10, "top": 20, "width": 150, "height": 30},
            }
        )
    )

    regions = load_regions(regions_file)

    assert regions == [Region(name="meso_price", left=10, top=20, width=150, height=30)]


def test_load_reference_resolution_present(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps({"reference_resolution": {"width": 2560, "height": 1440}})
    )

    assert load_reference_resolution(regions_file) == Resolution(width=2560, height=1440)


def test_load_reference_resolution_absent(tmp_path):
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(json.dumps({"meso_price": {"left": 10, "top": 20, "width": 150, "height": 30}}))

    assert load_reference_resolution(regions_file) is None


def test_scale_regions_scales_proportionally_to_current_resolution():
    regions = [Region(name="meso_1", left=1090, top=300, width=130, height=45)]
    reference = Resolution(width=2560, height=1440)
    current = Resolution(width=1280, height=720)  # exactly half

    scaled = scale_regions(regions, reference=reference, current=current)

    assert scaled == [Region(name="meso_1", left=545, top=150, width=65, height=22)]


def test_scale_regions_is_a_no_op_when_resolution_matches():
    regions = [Region(name="meso_1", left=1090, top=300, width=130, height=45)]
    same = Resolution(width=2560, height=1440)

    assert scale_regions(regions, reference=same, current=same) == regions
