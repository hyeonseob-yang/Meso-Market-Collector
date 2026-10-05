"""Turn a captured screen region into a price value via OCR.

Split into two pieces on purpose:
  - `_parse_price_text` is pure text-in/number-out logic - unit-testable
    with no OCR engine involved.
  - `parse_price` calls the actual OCR engine (pytesseract, needing the
    real Tesseract binary installed - see requirements.txt/README) and is
    untested directly here, same as capture.py/screen_actions.py: it needs
    a real environment, verified live rather than in this test suite.
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
        # Not on PATH (common right after installing - the installer's
        # PATH update needs a fresh shell to take effect). Fall back to
        # the default Windows install location rather than requiring
        # everyone to configure this by hand.
        _default_windows_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if _default_windows_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(_default_windows_path)

# Meso prices are always whole numbers; restrict Tesseract to digits and a
# few OCR-noise-prone punctuation marks so it doesn't guess at letters that
# happen to look like digits (e.g. reading "O" as a letter instead of 0).
_TESSERACT_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789,."

# Price boxes are small (~20px tall) grey-on-grey text, which Tesseract
# misreads fed raw (e.g. 408 as 405). Grayscale + 3x upscale read every
# sample correctly; inverting or thresholding as well did worse, breaking
# up the digits.
_UPSCALE = 3

# Tesseract needs clear space around the text: with digits touching the
# crop's top edge (a region box set a few pixels low) it dropped a trailing
# 7 - 417 read as 41, 427 as 42 - which is still a valid number, so it got
# recorded and posted. Padding with the box's own background colour before
# OCR read all of those correctly, so a slightly-off box no longer matters.
_PADDING = 6


def _prepare_image(image: Image.Image) -> Image.Image:
    """Grayscale, pad with the background colour, and upscale a captured
    region for OCR."""
    gray = ImageOps.grayscale(image)
    background = ImageStat.Stat(gray).median[0]
    padded = ImageOps.expand(gray, border=_PADDING, fill=background)
    return padded.resize((padded.width * _UPSCALE, padded.height * _UPSCALE), Image.LANCZOS)


def _parse_price_text(text: str) -> int | None:
    """Turn raw OCR output into a price, or None if it doesn't cleanly
    parse as one. Deliberately conservative: garbage in means None out,
    not a best-effort guess - a wrong recorded price is worse than a
    missing one (the raw snapshot is kept either way, see storage.py).
    Returns an int, not a float - meso prices are always whole numbers."""
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

# Same-side tiers (100M/1B/10B) sit within a few points of each other;
# 10% apart means a misread. Deliberately not applied across sides: a real
# spike had Buy 480 vs Sell 413, a 16% gap.
_MAX_TIER_DEVIATION = 0.10


def find_implausible_prices(row: dict[str, int | None]) -> list[str]:
    """Return the columns of `row` whose value is almost certainly an OCR
    misread, even though it parsed as a clean number - e.g. a 100M box read
    as 42 when it showed 427 (a trailing 7 dropped by a tight crop), which
    happened on 13 hourly runs in Oct 2026. Two rules:
      - under half or over double the median of all the row's prices (a
        dropped or extra digit);
      - more than 10% from the median of its own side's three tiers.
    Missing (None) values are ignored - those are already handled as
    unreadable."""
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
