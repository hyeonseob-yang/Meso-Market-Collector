"""Real screen/process I/O backing routine.GameActions.

Needs a real display and game; tests swap in fakes (see
tests/test_screen_actions.py).
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .api_client import post_price_row as post_price_row_api
from .capture import capture_region
from .config import get_template_path, load_regions
from .parser import find_implausible_prices, parse_price
from .storage import FAILURE_SNAPSHOT_PREFIX, append_price_row, clear_old_snapshots, save_snapshot

try:
    import pyautogui
    import pygetwindow as gw
except Exception as exc:  # pragma: no cover - environment dependent
    raise RuntimeError(
        "pyautogui could not find a display. Run this from a session that "
        "has GUI/screen access (e.g. the machine actually running the "
        "game), not a headless shell."
    ) from exc


class ScreenActions:
    def __init__(
        self,
        poll_interval: float = 0.5,
        timeout: float = 180.0,
        stable_seconds: float = 1.0,
        confidence: float = 0.8,
        templates_dir: Path | None = None,
        hold_seconds: float = 0.05,
        notes: str = "",
    ):
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.stable_seconds = stable_seconds
        self.confidence = confidence
        self.templates_dir = templates_dir
        self.hold_seconds = hold_seconds
        # Saved in the Notes of every row this run records (e.g. "manual").
        self.notes = notes
        self._readings: dict[str, int | None] = {}
        self._last_saved_row: dict[str, int | None] = {}
        self._last_saved_at: datetime | None = None
        self._focus_target = None  # set by focus_window

    def _locate(self, template: str, confidence: float | None = None):
        # Returns None when nothing matches (locateOnScreen raises instead),
        # so callers' polling loops can retry.
        path = self.templates_dir / template if self.templates_dir else get_template_path(template)
        try:
            # grayscale=False: in grayscale the Sell and Buy tab buttons,
            # which differ mainly by color, match each other.
            return pyautogui.locateOnScreen(
                str(path),
                confidence=confidence if confidence is not None else self.confidence,
                grayscale=False,
            )
        except pyautogui.ImageNotFoundException:
            return None

    def _run_scheduled_task(self, task_name: str) -> None:
        subprocess.run(["schtasks", "/run", "/tn", task_name], check=True)

    def launch(self, task_name: str) -> None:
        # Via an elevated Scheduled Task, not the exe directly, to avoid a
        # UAC prompt.
        self._run_scheduled_task(task_name)

    def run_task(self, task_name: str) -> None:
        # Used to close the game: it runs elevated, so only an elevated
        # task's taskkill can end it.
        self._run_scheduled_task(task_name)

    def wait_for_process_exit(self, processes: list[str]) -> None:
        # schtasks /run returns when a task starts, not when it finishes.
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            running = [p for p in processes if self._is_running(p)]
            if not running:
                return
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timed out waiting for {running} to exit")

    def record_leftovers(self, processes: list[str]) -> None:
        running = [p for p in processes if self._is_running(p)]
        if not running:
            return
        path = save_snapshot(f"{FAILURE_SNAPSHOT_PREFIX}leftover", pyautogui.screenshot())
        print(f"Still running from before this run: {', '.join(running)} - screenshot {path.name}", flush=True)

    def _is_running(self, image_name: str) -> bool:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True, text=True, check=True,
        ).stdout
        # No match prints an "INFO: ..." line instead of a CSV row.
        return f'"{image_name.lower()}"' in out.lower()

    def wait_for_image(
        self, template: str, message: str | None = None, confidence: float | None = None
    ):
        if message:
            print(f"\n{message}\n(waiting for {template!r} to appear on screen...)", flush=True)
        box = self._poll_for(template, self.timeout, confidence)
        if box:
            return box
        self._save_timeout_screenshot(template)
        raise TimeoutError(f"Timed out waiting for {template!r} to appear")

    def _poll_for(self, template: str, seconds: float, confidence: float | None = None):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            box = self._locate(template, confidence)
            if box:
                return box
            time.sleep(self.poll_interval)
        return None

    def _save_timeout_screenshot(self, template: str) -> None:
        # Shows what was on screen when an unattended run gave up.
        path = save_snapshot(f"{FAILURE_SNAPSHOT_PREFIX}{Path(template).stem}", pyautogui.screenshot())
        print(f"Saved a screenshot of the timeout to {path}", flush=True)

    def wait_for_stable_image(self, template: str):
        """Wait until the template stays found for `stable_seconds` - i.e.
        it has finished animating in and is safe to click."""
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
        self._save_timeout_screenshot(template)
        raise TimeoutError(f"Timed out waiting for {template!r} to stabilize")

    def click_image(self, template: str, confidence: float | None = None) -> None:
        self._click_box(self.wait_for_image(template, confidence=confidence))

    def click_image_if_present(
        self, template: str, seconds: float = 10.0, confidence: float | None = None
    ) -> None:
        """Click `template` if it shows up within `seconds`; otherwise carry
        on. For a click that's only sometimes needed, e.g. the Sell tab
        when the market opened on the Buy tab."""
        box = self._poll_for(template, seconds, confidence)
        if box:
            self._click_box(box)

    def _click_box(self, box) -> None:
        # Held, not pyautogui.click(): games poll input once per frame and
        # miss an instant down/up.
        self._ensure_focus()
        pyautogui.moveTo(pyautogui.center(box))
        pyautogui.mouseDown(_pause=False)
        time.sleep(self.hold_seconds)
        pyautogui.mouseUp()

    def _ensure_focus(self) -> None:
        """Refocus the game window if something else took focus, and refuse
        to click if that fails rather than click into another window.
        Compared by window handle, since other windows can share the title."""
        if self._focus_target is None or gw.getActiveWindow() == self._focus_target:
            return
        if not self._activate(self._focus_target):
            raise RuntimeError(
                f"Couldn't bring {self._focus_target.title!r} back into focus before clicking"
            )

    def click_until_image(
        self,
        template: str,
        until: str,
        message: str | None = None,
        confidence: float | None = None,
        attempts: int = 3,
        retry_seconds: float = 20.0,
    ) -> None:
        """Click `template`, then wait for `until`, re-clicking every
        `retry_seconds` (up to `attempts` clicks) while `template` is still
        showing. After the last click, waits normally, printing `message`
        so the step can be finished by hand."""
        box = self.wait_for_image(template, confidence=confidence)
        self._record_click(template, 1)
        self._click_box(box)
        clicks = 1

        for _ in range(attempts - 1):
            if self._poll_for(until, retry_seconds):
                print(f"{until!r} appeared after click {clicks}", flush=True)
                return
            box = self._locate(template, confidence)
            if box:
                print(
                    f"{until!r} not showing after {retry_seconds:.0f}s - clicking {template!r} again",
                    flush=True,
                )
                clicks += 1
                self._record_click(template, clicks)
                self._click_box(box)

        self.wait_for_image(until, message)
        print(f"{until!r} appeared after click {clicks}", flush=True)

    def _record_click(self, template: str, n: int) -> None:
        # Diagnostic for clicks that sometimes don't register: keeps the
        # screen as it was just before each one, for comparison.
        path = save_snapshot(f"click{n}_{Path(template).stem}", pyautogui.screenshot())
        active = gw.getActiveWindow()
        print(
            f"[{time.strftime('%H:%M:%S')}] click {n} on {template!r}: "
            f"cursor at {tuple(pyautogui.position())}, "
            f"focused {active.title if active else None!r}, screenshot {path.name}",
            flush=True,
        )

    def wait_and_click_image(self, template: str) -> None:
        self.click_image(template)

    def record_prices(self, regions: dict[str, str]) -> None:
        # `regions` maps a region name to the CSV column to record it
        # under. Readings accumulate until save_price_row, since one row
        # combines the Sell and Buy tabs.
        regions_by_name = {r.name: r for r in load_regions()}
        for name, label in regions.items():
            region = regions_by_name[name]
            image = capture_region(region)
            price = parse_price(image)
            # Saved every time, named with the OCR result: a misread digit
            # still parses, so the crop is the only way to check it.
            save_snapshot(f"{label}_{price if price is not None else 'unreadable'}", image)
            self._readings[label] = price

    def save_price_row(self) -> None:
        # A suspect price is kept as read and flagged in Notes, not
        # blanked - a blank would make post_price_row refuse the row.
        suspect = find_implausible_prices(self._readings)
        notes = self.notes
        if suspect:
            misread = "Possible OCR misread: " + ", ".join(f"{c}={self._readings[c]}" for c in suspect)
            print(f"WARNING: {misread} - doesn't fit the rest of the row; noted on the row", flush=True)
            notes = "; ".join(filter(None, [notes, misread]))

        collected_at = datetime.now(timezone.utc)
        append_price_row(self._readings, collected_at=collected_at, notes=notes)
        self._last_saved_row = {**self._readings, "notes": notes}
        self._last_saved_at = collected_at
        self._readings = {}

    def post_price_row(self) -> None:
        # Sends the last saved row with its collection time, so Tracker
        # doesn't record the posting time instead.
        post_price_row_api(self._last_saved_row, collected_at=self._last_saved_at)

    def clear_old_snapshots(self, max_age_days: float, failure_max_age_days: float | None = None) -> None:
        clear_old_snapshots(max_age_days, failure_max_age_days=failure_max_age_days)

    def press_key(self, key: str) -> None:
        # Held, like clicks - see _click_box.
        self.hotkey([key])

    def hotkey(self, keys: list[str]) -> None:
        for key in keys:
            pyautogui.keyDown(key, _pause=False)
        time.sleep(self.hold_seconds)
        for key in reversed(keys):
            pyautogui.keyUp(key, _pause=False)
        time.sleep(pyautogui.PAUSE)

    def wait_for_user(self, message: str) -> None:
        input(f"\n{message}\n(press Enter to continue) ")

    def wait(self, seconds: float) -> None:
        # For something visible before it's usable, where click-and-retry
        # fails: a missed click leaves the cursor hovering the button, and
        # its hover look no longer matches the template.
        time.sleep(seconds)

    def focus_window(self, window_title: str) -> bool:
        # Needed before clicks (a click on an unfocused window may only
        # activate it) and before image waits (screenshots only see what's
        # on top). Polls because the window may not exist yet after launch.
        deadline = time.monotonic() + self.timeout
        while not (windows := gw.getWindowsWithTitle(window_title)):
            if time.monotonic() >= deadline:
                self._save_timeout_screenshot(window_title)
                raise TimeoutError(f"Timed out waiting for a window with title containing {window_title!r}")
            time.sleep(self.poll_interval)
        window = windows[0]
        self._focus_target = window  # for _ensure_focus
        return self._activate(window)

    def _activate(self, window) -> bool:
        if window.isMinimized:
            window.restore()
        for attempt in range(3):
            if attempt:
                # A held Alt gets past Windows' foreground lock, which
                # blocks focus changes from a process that wasn't the last
                # to receive input.
                self.hotkey(["alt"])
            try:
                window.activate()
            except gw.PyGetWindowException as exc:
                # pygetwindow raises on success too: "Error code from
                # Windows: 0" means no error.
                if "Error code from Windows: 0" not in str(exc):
                    raise
            time.sleep(0.3)
            if gw.getActiveWindow() == window:
                return True
        active = gw.getActiveWindow()
        print(
            f"WARNING: couldn't focus {window.title!r} - "
            f"{active.title if active else 'nothing'!r} has focus instead",
            flush=True,
        )
        return False
