"""Turn a captured screen region into a price value via OCR.

`parse_price` needs the real Tesseract binary (see README), so it's
verified live; the text and plausibility logic around it is unit-tested.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

try:
    import pytesseract
except ImportError:
    pytesseract = None
else:
    if shutil.which("tesseract") is None:
        # Not on PATH (common right after installing): fall back to the
        # default Windows install location.
        _default_windows_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if _default_windows_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(_default_windows_path)

# Digits and separators only, so Tesseract can't read a 0 as the letter O.
_TESSERACT_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789,."

# The ~20px-tall grey-on-grey digits are misread at native size (408 as
# 405). Inverting or thresholding as well did worse.
_UPSCALE = 3

# Tesseract needs clear space around the text: with digits touching the
# crop's edge it dropped a trailing 7 (427 read as 42).
_PADDING = 6


def _prepare_image(image: Image.Image) -> Image.Image:
    """Grayscale, pad with the background colour, and upscale a captured
    region for OCR."""
    gray = ImageOps.grayscale(image)
    background = ImageStat.Stat(gray).median[0]
    padded = ImageOps.expand(gray, border=_PADDING, fill=background)
    return padded.resize((padded.width * _UPSCALE, padded.height * _UPSCALE), Image.LANCZOS)


def _parse_price_text(text: str) -> int | None:
    """Turn raw OCR output into a whole-number price, or None if it
    doesn't cleanly parse - a wrong recorded price is worse than a missing
    one."""
    text = text.strip()
    if not text:
        return None
    text = text.replace(",", "")  # thousands separators
    text = text.rstrip(".")  # trailing punctuation noise, not a decimal
    if not text.isdigit():
        return None
    return int(text)


_BUY_TIERS = ("Buy Buyout 100M", "Buy Buyout 1B", "Buy Buyout 10B")
_SELL_TIERS = ("Sell Buyout 100M", "Sell Buyout 1B", "Sell Buyout 10B")

# Same-side tiers sit within a few points of each other. Not applied
# across sides: a real spike had Buy 480 vs Sell 413, a 16% gap.
_MAX_TIER_DEVIATION = 0.10


def find_implausible_prices(row: dict[str, int | None]) -> list[str]:
    """Return the columns of `row` whose value is almost certainly an OCR
    misread despite parsing as a number (e.g. 427 read as 42). Two rules:
      - under half or over double the median of all the row's prices (a
        dropped or extra digit);
      - more than 10% from the median of its own side's three tiers.
    Missing (None) values are ignored."""
    def median(values):
        values = sorted(values)
        mid = len(values) // 2
        return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2

    present = {column: value for column, value in row.items() if isinstance(value, int)}
    if not present:
        return []
    overall = median(present.values())
    bad = [c for c, v in present.items() if not overall / 2 <= v <= overall * 2]

    for side in (_BUY_TIERS, _SELL_TIERS):
        tiers = {c: present[c] for c in side if c in present and c not in bad}
        if len(tiers) < 2:
            continue
        side_median = median(tiers.values())
        bad += [c for c, v in tiers.items() if abs(v - side_median) > side_median * _MAX_TIER_DEVIATION]
    return bad


def parse_price(image: Image.Image) -> int | None:
    """Extract a numeric price from a captured region via OCR."""
    if pytesseract is None:
        return None
    text = pytesseract.image_to_string(_prepare_image(image), config=_TESSERACT_CONFIG)
    return _parse_price_text(text)
