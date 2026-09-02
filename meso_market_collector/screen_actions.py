"""Real screen/process I/O backing routine.GameActions.

Untested directly (needs an actual display and the real game), by design —
see routine.py for the testable dispatch logic this implements for.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .api_client import post_price_row as post_price_row_api
from .capture import capture_region
from .config import load_regions
from .parser import parse_price
from .storage import append_price_row, clear_old_snapshots, save_snapshot

try:
    import pyautogui
    import pygetwindow as gw
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
        timeout: float = 180.0,
        stable_seconds: float = 1.0,
        confidence: float = 0.8,
        templates_dir: Path = TEMPLATES_DIR,
    ):
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.stable_seconds = stable_seconds
        self.confidence = confidence
        self.templates_dir = templates_dir
        self._readings: dict[str, int | None] = {}
        self._last_saved_row: dict[str, int | None] = {}

    def _locate(self, template: str):
        # locateOnScreen raises ImageNotFoundException rather than
        # returning None when nothing matches - treat that the same as
        # "not found yet" so callers' retry loops actually get to retry,
        # instead of crashing on the very first failed check.
        try:
            return pyautogui.locateOnScreen(
                str(self.templates_dir / template), confidence=self.confidence
            )
        except pyautogui.ImageNotFoundException:
            return None

    def _run_scheduled_task(self, task_name: str) -> None:
        subprocess.run(["schtasks", "/run", "/tn", task_name], check=True)

    def launch(self, task_name: str) -> None:
        # Runs a pre-configured Scheduled Task (RunLevel: Highest) rather
        # than the exe directly - a UAC prompt neither a scheduled task nor
        # the RunAsInvoker env var could suppress when starting the game
        # exe's usual way (it's explicitly elevated by its caller, not just
        # manifest-declared). The task instead runs the official launcher
        # with its own "jump straight to this game" argument (e.g.
        # nxl://launch/10100), matching a normal desktop shortcut's
        # behavior. See README.md for more.
        self._run_scheduled_task(task_name)

    def run_task(self, task_name: str) -> None:
        # Generic version of the same mechanism as launch() - runs any
        # other pre-configured Scheduled Task. Used to close the game: the
        # process runs elevated (from launch's task), so a normal-integrity
        # taskkill/Stop-Process can't touch it (Access is denied), and
        # simulated input (Alt+F4, clicking an exit-confirm dialog) doesn't
        # register in the game client at all - same as every other in-game
        # click, this input filtering doesn't distinguish "close the game"
        # from any other click. A second elevated task (e.g. running
        # `taskkill /F /IM MapleStory.exe`) sidesteps both problems at once.
        self._run_scheduled_task(task_name)

    def wait_for_image(self, template: str, message: str | None = None):
        if message:
            print(f"\n{message}\n(waiting for {template!r} to appear on screen...)", flush=True)
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

    def record_prices(self, regions: dict[str, str]) -> None:
        # `regions` maps a configured region name to the exact output label
        # to record it under (e.g. "meso_2" -> "Sell Buyout 100M") - the
        # label goes straight into self._readings under the same name
        # save_price_row() will use as the final CSV column, so no
        # separate remapping step is needed afterward. Accumulated here
        # rather than written immediately, since a full row combines
        # readings from both the Sell and Buy tab captures.
        regions_by_name = {r.name: r for r in load_regions()}
        for name, label in regions.items():
            region = regions_by_name[name]
            image = capture_region(region)
            price = parse_price(image)
            if price is None:
                save_snapshot(label, image)
            self._readings[label] = price

    def save_price_row(self) -> None:
        append_price_row(self._readings)
        self._last_saved_row = self._readings
        self._readings = {}

    def post_price_row(self) -> None:
        # Sends whatever save_price_row most recently wrote to the CSV -
        # not self._readings, which save_price_row has already cleared by
        # the time this runs (see routine.json, where this step follows
        # save_price_row).
        post_price_row_api(self._last_saved_row)

    def clear_old_snapshots(self, max_age_days: float) -> None:
        clear_old_snapshots(max_age_days)

    def press_key(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, keys: list[str]) -> None:
        pyautogui.hotkey(*keys)

    def wait_for_user(self, message: str) -> None:
        # Clicks and key presses don't register inside the actual game
        # client (confirmed across both MapleStory and Terraria - not
        # something worth trying to work around further, see README).
        # Everything that needs a real click inside the game itself is a
        # manual checkpoint: print what to do, block until Enter confirms
        # it's done, then resume the automated parts (screenshot capture,
        # scheduled-task launch/close) that don't need simulated input.
        input(f"\n{message}\n(press Enter to continue) ")

    def focus_window(self, window_title: str) -> None:
        # A click's first hit on an unfocused window can just activate it
        # rather than actually registering on whatever's underneath the
        # cursor - bring it to the foreground explicitly first so every
        # click_image afterward lands for real.
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            raise RuntimeError(f"No window found with title containing {window_title!r}")
        window = windows[0]
        if window.isMinimized:
            window.restore()
        try:
            window.activate()
        except gw.PyGetWindowException as exc:
            # pygetwindow's activate() raises even when the underlying
            # Windows call actually succeeded - a known false positive.
            # "Error code from Windows: 0" literally means no error
            # occurred, so only re-raise for an actual nonzero code.
            if "Error code from Windows: 0" not in str(exc):
                raise
