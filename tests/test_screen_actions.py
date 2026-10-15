"""ScreenActions logic that doesn't need a real display or game: pyautogui,
pygetwindow and time are swapped for fakes, so these only check what
ScreenActions decides to do with them."""
from types import SimpleNamespace

import pytest

from meso_market_collector import config

try:
    from meso_market_collector import screen_actions
except RuntimeError:  # pyautogui can't import without a display
    pytest.skip("screen_actions needs a display to import", allow_module_level=True)


class FakeClock:
    """Stands in for the time module: sleep() just advances monotonic()."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeWindow:
    def __init__(self):
        self.isMinimized = False
        self.activated = 0

    def activate(self):
        self.activated += 1


def _fake_gw(windows_by_poll, active=None):
    """getWindowsWithTitle returns successive entries of `windows_by_poll`
    (repeating the last one once exhausted)."""
    polls = iter(windows_by_poll)
    last = []

    def get_windows_with_title(title):
        nonlocal last
        last = next(polls, last)
        return last

    return SimpleNamespace(
        getWindowsWithTitle=get_windows_with_title,
        getActiveWindow=lambda: active,
        PyGetWindowException=Exception,
    )


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(screen_actions, "time", fake)
    return fake


def test_focus_window_waits_for_window_to_appear(monkeypatch, clock):
    window = FakeWindow()
    # Not there for the first two polls (game still loading), then appears.
    monkeypatch.setattr(screen_actions, "gw", _fake_gw([[], [], [window]], active=window))

    screen_actions.ScreenActions(poll_interval=0.5, timeout=10).focus_window("MapleStory")

    assert window.activated == 1
    assert clock.now >= 1.0  # waited through the two empty polls


@pytest.fixture
def screenshots(monkeypatch, tmp_path):
    """Fakes the screen grab and records each snapshot saved as (name, image)."""
    saved = []

    def save_snapshot(item, image):
        saved.append((item, image))
        return tmp_path / f"{item}.png"

    monkeypatch.setattr(screen_actions, "save_snapshot", save_snapshot)
    monkeypatch.setattr(screen_actions, "pyautogui", SimpleNamespace(screenshot=lambda: "the screen"))
    return saved


def test_focus_window_times_out_if_window_never_appears(monkeypatch, clock, screenshots):
    monkeypatch.setattr(screen_actions, "gw", _fake_gw([[]]))

    with pytest.raises(TimeoutError, match="MapleStory"):
        screen_actions.ScreenActions(poll_interval=0.5, timeout=3).focus_window("MapleStory")

    assert clock.now >= 3
    assert screenshots == [("timeout_MapleStory", "the screen")]


def _running(monkeypatch, *names):
    monkeypatch.setattr(screen_actions.ScreenActions, "_is_running", lambda self, name: name in names)


def test_record_leftovers_screenshots_what_a_previous_run_left_open(monkeypatch, screenshots, capsys):
    _running(monkeypatch, "nexon_client.exe")

    screen_actions.ScreenActions().record_leftovers(["MapleStory.exe", "nexon_client.exe"])

    assert screenshots == [("timeout_leftover", "the screen")]
    out = capsys.readouterr().out
    assert "nexon_client.exe" in out
    assert "MapleStory.exe" not in out


def test_record_leftovers_names_every_process_still_running(monkeypatch, screenshots, capsys):
    _running(monkeypatch, "MapleStory.exe", "nexon_client.exe")

    screen_actions.ScreenActions().record_leftovers(["MapleStory.exe", "nexon_client.exe"])

    out = capsys.readouterr().out
    assert "MapleStory.exe" in out and "nexon_client.exe" in out


def test_record_leftovers_does_nothing_when_nothing_is_running(monkeypatch, screenshots, capsys):
    _running(monkeypatch)

    screen_actions.ScreenActions().record_leftovers(["MapleStory.exe", "nexon_client.exe"])

    assert screenshots == []
    assert capsys.readouterr().out == ""


class FocusableWindow(FakeWindow):
    """A window that actually takes focus when activated (unless `stuck`)."""

    def __init__(self, focus, title, stuck=False):
        super().__init__()
        self.focus, self.title, self.stuck = focus, title, stuck

    def activate(self):
        super().activate()
        if not self.stuck:
            self.focus["active"] = self


class ClickPyautogui:
    def __init__(self, focus):
        self.focus = focus
        self.clicked_with_focus_on = []

    def center(self, box):
        return box

    def moveTo(self, point):
        pass

    def mouseDown(self, _pause=True):
        self.clicked_with_focus_on.append(self.focus["active"])

    def mouseUp(self):
        pass

    def keyDown(self, key, _pause=True):
        pass

    def keyUp(self, key, _pause=True):
        pass

    PAUSE = 0


@pytest.fixture
def focus_setup(monkeypatch, clock):
    focus = {}
    game = FocusableWindow(focus, "MapleStory")
    other = FocusableWindow(focus, "Visual Studio Code")
    monkeypatch.setattr(
        screen_actions,
        "gw",
        SimpleNamespace(
            getWindowsWithTitle=lambda title: [game],
            getActiveWindow=lambda: focus.get("active"),
            PyGetWindowException=Exception,
        ),
    )
    fake = ClickPyautogui(focus)
    monkeypatch.setattr(screen_actions, "pyautogui", fake)
    actions = screen_actions.ScreenActions()
    actions.focus_window("MapleStory")
    return actions, focus, game, other, fake


def test_click_refocuses_game_if_focus_moved_away(focus_setup):
    actions, focus, game, other, fake = focus_setup
    focus["active"] = other  # e.g. the user switched windows mid-run

    actions._click_box((10, 10))

    assert fake.clicked_with_focus_on == [game]


def test_click_does_not_reactivate_when_game_already_focused(focus_setup):
    actions, focus, game, other, fake = focus_setup
    activations = game.activated

    actions._click_box((10, 10))

    assert game.activated == activations
    assert fake.clicked_with_focus_on == [game]


def test_click_refuses_if_game_cannot_be_refocused(focus_setup):
    actions, focus, game, other, fake = focus_setup
    focus["active"] = other
    game.stuck = True  # Windows won't hand focus back

    with pytest.raises(RuntimeError, match="MapleStory"):
        actions._click_box((10, 10))

    assert fake.clicked_with_focus_on == []  # never clicked into the wrong window


class FakePyautogui:
    class ImageNotFoundException(Exception):
        pass

    def __init__(self, found=None):
        self.located: list[str] = []
        self.grayscale: list[bool] = []
        self.found = found  # box to "find" for every template, or None
        self.events: list[tuple] = []

    def locateOnScreen(self, path, confidence, grayscale):
        self.located.append(path)
        self.grayscale.append(grayscale)
        if self.found is None:
            raise self.ImageNotFoundException
        return self.found

    def center(self, box):
        return ("center", box)

    def moveTo(self, point):
        self.events.append(("moveTo", point))

    def mouseDown(self, _pause=True):
        self.events.append(("mouseDown",))

    def mouseUp(self):
        self.events.append(("mouseUp",))


@pytest.fixture
def template_dirs(tmp_path, monkeypatch):
    shared, local = tmp_path / "templates", tmp_path / "templates.local"
    shared.mkdir()
    local.mkdir()
    for name in ("login_button.png", "quick_move_button.png"):
        (shared / name).write_bytes(b"shared")
    (local / "login_button.png").write_bytes(b"local")
    monkeypatch.setattr(config, "TEMPLATES_DIR", shared)
    monkeypatch.setattr(config, "LOCAL_TEMPLATES_DIR", local)
    return shared, local


def test_locate_uses_local_template_when_present_else_shared(monkeypatch, template_dirs):
    shared, local = template_dirs
    fake = FakePyautogui()
    monkeypatch.setattr(screen_actions, "pyautogui", fake)
    actions = screen_actions.ScreenActions()

    assert actions._locate("login_button.png") is None  # not found -> None, not an exception
    actions._locate("quick_move_button.png")

    assert fake.located == [str(local / "login_button.png"), str(shared / "quick_move_button.png")]


def test_locate_explicit_templates_dir_bypasses_local_lookup(monkeypatch, template_dirs, tmp_path):
    fake = FakePyautogui()
    monkeypatch.setattr(screen_actions, "pyautogui", fake)
    explicit = tmp_path / "explicit"

    screen_actions.ScreenActions(templates_dir=explicit)._locate("login_button.png")

    assert fake.located == [str(explicit / "login_button.png")]


def test_locate_matches_in_color_not_grayscale(monkeypatch, template_dirs):
    """In grayscale the Sell tab's "Request Sale" and the Buy tab's "Request
    Purchase" buttons match each other, so the tab checks can't tell the
    tabs apart - matching has to be in color."""
    fake = FakePyautogui()
    monkeypatch.setattr(screen_actions, "pyautogui", fake)

    screen_actions.ScreenActions()._locate("login_button.png")

    assert fake.grayscale == [False]


def test_click_image_if_present_clicks_when_template_shows(monkeypatch, template_dirs, clock):
    fake = FakePyautogui(found="box")
    monkeypatch.setattr(screen_actions, "pyautogui", fake)

    screen_actions.ScreenActions().click_image_if_present("login_button.png", seconds=10)

    assert fake.events == [("moveTo", ("center", "box")), ("mouseDown",), ("mouseUp",)]


def test_click_image_if_present_carries_on_when_template_never_shows(monkeypatch, template_dirs, clock):
    fake = FakePyautogui()
    monkeypatch.setattr(screen_actions, "pyautogui", fake)

    screen_actions.ScreenActions(poll_interval=0.5).click_image_if_present("login_button.png", seconds=10)

    assert fake.events == []  # no click, and no exception
    assert clock.now >= 10  # gave it the full time before moving on


def _readings(buy_100m):
    return {
        "average": 420,
        "buy100M": buy_100m,
        "buy1B": 427,
        "buy10B": 427,
        "sell100M": 418,
        "sell1B": 418,
        "sell10B": 418,
    }


class SavedRows(list):
    """(row, notes) per saved row, plus the collection time each was given."""

    def __init__(self):
        super().__init__()
        self.times = []


@pytest.fixture
def saved_rows(monkeypatch):
    saved = SavedRows()

    def append_price_row(row, collected_at, notes=""):
        saved.append((dict(row), notes))
        saved.times.append(collected_at)

    monkeypatch.setattr(screen_actions, "append_price_row", append_price_row)
    return saved


def test_save_price_row_gives_the_csv_and_tracker_the_same_time(saved_rows):
    actions = screen_actions.ScreenActions()
    actions._readings = _readings(buy_100m=427)

    actions.save_price_row()

    assert saved_rows.times == [actions._last_saved_at]


def test_save_price_row_keeps_an_implausible_price_and_notes_it(saved_rows):
    """A price that doesn't fit the row (427 read as 42) is recorded as
    read, with a note naming it - not blanked, which made the Tracker post
    refuse the row and fail the run."""
    actions = screen_actions.ScreenActions()
    actions._readings = _readings(buy_100m=42)

    actions.save_price_row()

    note = "Possible OCR misread: buy100M=42"
    assert saved_rows == [(_readings(buy_100m=42), note)]
    # ...and the same note rides along to Tracker with the row.
    assert actions._last_saved_row == {**_readings(buy_100m=42), "notes": note}


def test_save_price_row_leaves_notes_blank_for_a_plausible_row(saved_rows):
    actions = screen_actions.ScreenActions()
    actions._readings = _readings(buy_100m=427)

    actions.save_price_row()

    assert saved_rows == [(_readings(buy_100m=427), "")]
    assert actions._last_saved_row["notes"] == ""


def test_save_price_row_records_the_runs_notes(saved_rows):
    """A note given for the whole run (e.g. "manual", from session's
    --notes) is saved with the row and sent to Tracker."""
    actions = screen_actions.ScreenActions(notes="manual")
    actions._readings = _readings(buy_100m=427)

    actions.save_price_row()

    assert saved_rows == [(_readings(buy_100m=427), "manual")]
    assert actions._last_saved_row["notes"] == "manual"


def test_save_price_row_keeps_the_runs_notes_alongside_a_misread_note(saved_rows):
    actions = screen_actions.ScreenActions(notes="manual")
    actions._readings = _readings(buy_100m=42)

    actions.save_price_row()

    note = "manual; Possible OCR misread: buy100M=42"
    assert saved_rows == [(_readings(buy_100m=42), note)]
    assert actions._last_saved_row["notes"] == note


def test_clear_old_snapshots_passes_the_failure_limit_through(monkeypatch):
    calls = []
    monkeypatch.setattr(
        screen_actions, "clear_old_snapshots", lambda max_age_days, **limits: calls.append((max_age_days, limits))
    )

    screen_actions.ScreenActions().clear_old_snapshots(7, failure_max_age_days=90)

    assert calls == [(7, {"failure_max_age_days": 90})]
