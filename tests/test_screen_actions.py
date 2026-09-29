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


def test_focus_window_times_out_if_window_never_appears(monkeypatch, clock):
    monkeypatch.setattr(screen_actions, "gw", _fake_gw([[]]))

    with pytest.raises(TimeoutError, match="MapleStory"):
        screen_actions.ScreenActions(poll_interval=0.5, timeout=3).focus_window("MapleStory")

    assert clock.now >= 3


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

    def __init__(self):
        self.located: list[str] = []

    def locateOnScreen(self, path, confidence):
        self.located.append(path)
        raise self.ImageNotFoundException


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
