"""Turn a captured screen region into a price value.

Not decided yet: how the price gets read out of the image. Options to
implement here later:
  - OCR via pytesseract (crop tightly, threshold/binarize with Pillow first
    for better accuracy, then int(text.strip().replace(",", "")))
  - Template/digit matching if the game uses a fixed bitmap font
  - Manual: just keep the saved screenshots and label them yourself

For now this just saves the raw crop to disk (via storage.save_snapshot)
and returns None, so the rest of the pipeline (capture -> parse -> store)
is already wired up and testable.
"""
from __future__ import annotations

from PIL import Image


def parse_price(image: Image.Image) -> float | None:
    """Extract a numeric price from a captured region.

    Returns None until an extraction method is chosen and implemented.
    """
    return None
