import json

from meso_market_collector.config import Region, load_regions


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
