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

from PIL import Image

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


def parse_price(image: Image.Image) -> int | None:
    """Extract a numeric price from a captured region via OCR."""
    if pytesseract is None:
        return None
    text = pytesseract.image_to_string(image, config=_TESSERACT_CONFIG)
    return _parse_price_text(text)
