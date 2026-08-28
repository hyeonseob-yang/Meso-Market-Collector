"""Real screen/process I/O backing routine.GameActions.

Untested directly (needs an actual display and the real game), by design —
see routine.py for the testable dispatch logic this implements for.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .capture import capture_region
from .config import load_regions
from .parser import parse_price
from .storage import append_price, save_snapshot

try:
    import pyautogui
except Exception as exc:  # pragma: no cover - environment dependent
    raise RuntimeError(
        "pyautogui could not find a display. Run this from a session that "
        "has GUI/screen access (e.g. the machine actually running the "
        "game), not a headless shell."
    ) from exc

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


class ScreenActions:
    def __init__(
        self,
        poll_interval: float = 0.5,
        timeout: float = 30.0,
        stable_seconds: float = 1.0,
        confidence: float = 0.8,
        templates_dir: Path = TEMPLATES_DIR,
    ):
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.stable_seconds = stable_seconds
        self.confidence = confidence
        self.templates_dir = templates_dir
        self._process: subprocess.Popen | None = None

    def _locate(self, template: str):
        return pyautogui.locateOnScreen(
            str(self.templates_dir / template), confidence=self.confidence
        )

    def launch(self, launcher_path: str) -> None:
        self._process = subprocess.Popen([launcher_path])

    def wait_for_image(self, template: str):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            box = self._locate(template)
            if box:
                return box
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timed out waiting for {template!r} to appear")

    def wait_for_stable_image(self, template: str):
        """Wait until the template is found in the same place for
        `stable_seconds` straight - a rough stand-in for "has finished
        appearing/animating in and is now safe to click"."""
        deadline = time.monotonic() + self.timeout
        stable_since = None
        while time.monotonic() < deadline:
            box = self._locate(template)
            now = time.monotonic()
            if box:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= self.stable_seconds:
                    return box
            else:
                stable_since = None
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timed out waiting for {template!r} to stabilize")

    def click_image(self, template: str) -> None:
        box = self.wait_for_image(template)
        pyautogui.click(pyautogui.center(box))

    def wait_and_click_image(self, template: str) -> None:
        self.click_image(template)

    def record_prices(self, region_names: list[str], label_prefix: str | None = None) -> None:
        # region boxes are shared between tabs (same on-screen position); the
        # prefix (e.g. "sell"/"buy") is what keeps the recorded rows apart.
        regions_by_name = {r.name: r for r in load_regions()}
        for name in region_names:
            region = regions_by_name[name]
            image = capture_region(region)
            price = parse_price(image)
            label = f"{label_prefix}_{name}" if label_prefix else name
            if price is None:
                save_snapshot(label, image)
            append_price(label, price)

    def press_key(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, keys: list[str]) -> None:
        pyautogui.hotkey(*keys)

    def close(self) -> None:
        # Note: if the launcher spawns the actual game as a separate,
        # detached process and exits on its own, this only terminates the
        # (already-gone) launcher PID, not the game. If "close" isn't
        # actually closing the game, this needs to find the game's own
        # process (e.g. by name via psutil) instead.
        if self._process is not None:
            self._process.terminate()
