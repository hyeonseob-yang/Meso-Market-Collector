from PIL import Image

from meso_market_collector.parser import _parse_price_text, _prepare_image


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
