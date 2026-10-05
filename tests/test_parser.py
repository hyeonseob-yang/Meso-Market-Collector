from PIL import Image

import pytest

from meso_market_collector.parser import _parse_price_text, _prepare_image, find_implausible_prices


def _row(average, buy, sell):
    return {
        "Average": average,
        "Buy Buyout 100M": buy[0],
        "Buy Buyout 1B": buy[1],
        "Buy Buyout 10B": buy[2],
        "Sell Buyout 100M": sell[0],
        "Sell Buyout 1B": sell[1],
        "Sell Buyout 10B": sell[2],
    }


@pytest.mark.parametrize(
    "row",
    [
        _row(428, (432, 432, 432), (425, 425, 425)),  # ordinary
        _row(424, (425, 425, 430), (423, 423, 423)),  # tiers a few points apart (Tracker id 42)
        _row(427, (430, 430, 430), (428, 422, 422)),  # (Tracker id 45)
        _row(488, (480, 480, 480), (413, 413, 413)),  # real 9/30 spike: 16% buy/sell gap
    ],
)
def test_find_implausible_prices_accepts_real_rows(row):
    assert find_implausible_prices(row) == []


def test_find_implausible_prices_catches_dropped_trailing_digit():
    # Tracker id 52: Buy 100M showed 427, OCR dropped the 7.
    row = _row(419, (42, 427, 427), (418, 418, 418))

    assert find_implausible_prices(row) == ["Buy Buyout 100M"]


def test_find_implausible_prices_catches_both_sides_at_once():
    # Tracker id 55: both 100M boxes lost their trailing 7.
    row = _row(419, (42, 427, 427), (41, 417, 417))

    assert sorted(find_implausible_prices(row)) == ["Buy Buyout 100M", "Sell Buyout 100M"]


def test_find_implausible_prices_catches_wrong_digit_within_a_side():
    # Three digits, so the digit-count rule can't see it - but 472 is
    # more than 10% off its side's other tiers.
    row = _row(424, (472, 427, 427), (420, 420, 420))

    assert find_implausible_prices(row) == ["Buy Buyout 100M"]


def test_find_implausible_prices_catches_misread_average():
    row = _row(41, (420, 420, 420), (417, 417, 417))

    assert find_implausible_prices(row) == ["Average"]


def test_find_implausible_prices_ignores_missing_values():
    row = _row(None, (None, 427, 427), (418, 418, None))

    assert find_implausible_prices(row) == []


def test_prepare_image_grayscales_and_upscales_3x():
    prepared = _prepare_image(Image.new("RGB", (65, 20), (120, 130, 140)))

    assert prepared.mode == "L"
    assert prepared.size == (195, 60)


def test_parses_plain_digits():
    result = _parse_price_text("377")
    assert result == 377
    assert isinstance(result, int)  # not 377.0 - meso prices are whole numbers


def test_strips_surrounding_whitespace_and_newlines():
    assert _parse_price_text("  377\n") == 377


def test_strips_thousands_separator_commas():
    assert _parse_price_text("1,234") == 1234
    assert _parse_price_text("12,345,678") == 12345678


def test_returns_none_for_empty_string():
    assert _parse_price_text("") is None


def test_returns_none_for_whitespace_only():
    assert _parse_price_text("   \n  ") is None


def test_returns_none_for_non_numeric_garbage():
    assert _parse_price_text("abc") is None


def test_returns_none_for_mixed_garbage():
    # OCR noise that isn't cleanly a number shouldn't be guessed at -
    # better to fall back to the saved snapshot than record a wrong price.
    assert _parse_price_text("37b") is None


def test_ignores_trailing_punctuation_noise():
    assert _parse_price_text("377.") == 377
