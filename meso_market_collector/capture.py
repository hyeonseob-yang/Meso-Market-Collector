"""Screen capture helpers built on PyAutoGUI (which itself returns Pillow images)."""
from __future__ import annotations

from PIL import Image

from .config import Region

try:
    import pyautogui
except Exception as exc:  # pragma: no cover - environment dependent
    # pyautogui fails at import time without a display; surface a clearer error.
    raise RuntimeError(
        "pyautogui could not find a display. Run the collector from a "
        "session that has GUI/screen access (e.g. the machine actually "
        "running the game), not a headless shell."
    ) from exc


def capture_region(region: Region) -> Image.Image:
    """Grab the pixels for one configured region as a Pillow Image."""
    return pyautogui.screenshot(region=region.box)
