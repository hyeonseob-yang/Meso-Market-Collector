"""Real screen/process I/O backing routine.GameActions.

Untested directly (needs an actual display and the real game), by design —
see routine.py for the testable dispatch logic this implements for.
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .api_client import post_price_row as post_price_row_api
from .capture import capture_region
from .config import get_template_path, load_regions
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


class ScreenActions:
    def __init__(
        self,
        poll_interval: float = 0.5,
        timeout: float = 180.0,
        stable_seconds: float = 1.0,
        confidence: float = 0.8,
        templates_dir: Path | None = None,
        hold_seconds: float = 0.05,
    ):
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.stable_seconds = stable_seconds
        self.confidence = confidence
        self.templates_dir = templates_dir
        self.hold_seconds = hold_seconds
        self._readings: dict[str, int | None] = {}
        self._last_saved_row: dict[str, int | None] = {}
        self._last_saved_at: datetime | None = None
        self._focus_target = None  # set by focus_window

    def _locate(self, template: str, confidence: float | None = None):
        # locateOnScreen raises ImageNotFoundException rather than
        # returning None when nothing matches - treat that the same as
        # "not found yet" so callers' retry loops actually get to retry,
        # instead of crashing on the very first failed check.
        # An explicit templates_dir is used as-is; otherwise each template
        # comes from assets/templates.local/ if this machine has its own
        # copy, else the shared assets/templates/ (see get_template_path).
        path = self.templates_dir / template if self.templates_dir else get_template_path(template)
        try:
            return pyautogui.locateOnScreen(
                str(path),
                confidence=confidence if confidence is not None else self.confidence,
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
        # taskkill/Stop-Process can't touch it (Access is denied). A second
        # elevated task (e.g. running `taskkill /F /IM MapleStory.exe`)
        # works regardless of whether this script itself is elevated.
        self._run_scheduled_task(task_name)

    def wait_for_process_exit(self, processes: list[str]) -> None:
        # schtasks /run returns as soon as a task starts, not when it's
        # done - so after a kill task, poll until the processes are really
        # gone. tasklist sees elevated processes' names even from a
        # non-elevated caller (it just can't touch them).
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            running = [p for p in processes if self._is_running(p)]
            if not running:
                return
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timed out waiting for {running} to exit")

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
        # A timeout means the screen wasn't what the routine expected - keep
        # what it actually was, since an unattended run has no one watching.
        # Lands in data/snapshots/, so clear_old_snapshots cleans it up too.
        path = save_snapshot(f"timeout_{Path(template).stem}", pyautogui.screenshot())
        print(f"Saved a screenshot of the timeout to {path}", flush=True)

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
        self._save_timeout_screenshot(template)
        raise TimeoutError(f"Timed out waiting for {template!r} to stabilize")

    def click_image(self, template: str, confidence: float | None = None) -> None:
        self._click_box(self.wait_for_image(template, confidence=confidence))

    def _click_box(self, box) -> None:
        # Held rather than pyautogui.click(): games poll input state once
        # per frame, and click()'s back-to-back down/up falls between polls
        # and never registers (confirmed in both Terraria and MapleStory -
        # mouse movement still registers either way, since it's continuous).
        self._ensure_focus()
        pyautogui.moveTo(pyautogui.center(box))
        pyautogui.mouseDown(_pause=False)
        time.sleep(self.hold_seconds)
        pyautogui.mouseUp()

    def _ensure_focus(self) -> None:
        """Before a click, bring back the window focus_window last focused
        if something else has taken focus since (e.g. a window switch
        mid-run) - and refuse to click at all if that fails, rather than
        clicking into whatever window is on top instead. Compared by
        window handle, not title, so e.g. a browser tab with "MapleStory"
        in its title never counts."""
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
        """Click `template`, then wait for `until` to appear - re-clicking
        (if `template` is still showing) every `retry_seconds`, up to
        `attempts` clicks in total, in case a click didn't take (e.g. the
        game wasn't ready for input yet). After the last attempt, falls
        back to a normal wait_for_image, printing `message` so someone can
        finish the step by hand."""
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
        # Diagnostic: the first Log In click sometimes doesn't take while a
        # retry does, even with the game focused and no consistent timing
        # pattern - so keep what the screen looked like right before each
        # click, to compare a missed one against one that worked.
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
            # Saved every time, not just when parsing fails, with the OCR
            # result in the filename - a misread digit (e.g. 3 vs 6) still
            # parses fine, so the only way to catch one is to compare the
            # crop against what was recorded.
            save_snapshot(f"{label}_{price if price is not None else 'unreadable'}", image)
            self._readings[label] = price

    def save_price_row(self) -> None:
        append_price_row(self._readings)
        self._last_saved_row = self._readings
        self._last_saved_at = datetime.now(timezone.utc)
        self._readings = {}

    def post_price_row(self) -> None:
        # Sends whatever save_price_row most recently wrote to the CSV -
        # not self._readings, which save_price_row has already cleared by
        # the time this runs (see routine.json, where this step follows
        # save_price_row) - along with when it was saved, so Tracker
        # records the collection time rather than the posting time.
        post_price_row_api(self._last_saved_row, collected_at=self._last_saved_at)

    def clear_old_snapshots(self, max_age_days: float) -> None:
        clear_old_snapshots(max_age_days)

    def press_key(self, key: str) -> None:
        # Held for the same reason as click_image - pyautogui.press() taps
        # too briefly for the game to see.
        self.hotkey([key])

    def hotkey(self, keys: list[str]) -> None:
        for key in keys:
            pyautogui.keyDown(key, _pause=False)
        time.sleep(self.hold_seconds)
        for key in reversed(keys):
            pyautogui.keyUp(key, _pause=False)
        time.sleep(pyautogui.PAUSE)

    def wait_for_user(self, message: str) -> None:
        # A manual checkpoint: print what to do, block until Enter confirms
        # it's done, then resume the automated parts.
        input(f"\n{message}\n(press Enter to continue) ")

    def wait(self, seconds: float) -> None:
        # A fixed pause, for when something is visible before it's usable -
        # e.g. the Log In button shows before the game accepts clicks, and a
        # click-and-retry doesn't work there: the missed click leaves the
        # cursor hovering the button, whose hover look no longer matches its
        # template, so the retry can't find it to click again.
        time.sleep(seconds)

    def focus_window(self, window_title: str) -> bool:
        # A click's first hit on an unfocused window can just activate it
        # rather than actually registering on whatever's underneath the
        # cursor - bring it to the foreground explicitly first so every
        # click_image afterward lands for real. Also needed before any
        # wait_for_image on the game: screenshots only see what's on top,
        # so a game window behind e.g. the terminal never matches. Polls
        # for the window since, run right after launch, the game may not
        # have created it yet.
        deadline = time.monotonic() + self.timeout
        while not (windows := gw.getWindowsWithTitle(window_title)):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for a window with title containing {window_title!r}")
            time.sleep(self.poll_interval)
        window = windows[0]
        # Remembered so every later click can make sure it's still this
        # window that has focus - see _ensure_focus.
        self._focus_target = window
        return self._activate(window)

    def _activate(self, window) -> bool:
        if window.isMinimized:
            window.restore()
        for attempt in range(3):
            if attempt:
                # Windows refuses to hand focus to a window when the
                # requesting process wasn't the last to receive input
                # (the "foreground lock") - a held Alt press makes this
                # process that one, so the next activate() is allowed.
                self.hotkey(["alt"])
            try:
                window.activate()
            except gw.PyGetWindowException as exc:
                # pygetwindow's activate() raises even when the underlying
                # Windows call actually succeeded - a known false positive.
                # "Error code from Windows: 0" literally means no error
                # occurred, so only re-raise for an actual nonzero code.
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
