"""session.main's command-line handling, with the routine itself faked."""
import sys

import pytest

try:
    from meso_market_collector import session
except RuntimeError:  # pyautogui can't import without a display
    pytest.skip("session needs a display to import", allow_module_level=True)


@pytest.fixture
def created(monkeypatch):
    """Runs main() with everything past argument parsing faked; returns the
    keyword arguments each ScreenActions was created with."""
    made = []

    def fake_screen_actions(**kwargs):
        made.append(kwargs)
        return object()

    monkeypatch.setattr(session, "ScreenActions", fake_screen_actions)
    monkeypatch.setattr(session, "load_steps", lambda path: [])
    monkeypatch.setattr(session, "run_routine", lambda steps, task_name, actions: None)
    return made


def test_notes_option_is_passed_to_the_run(monkeypatch, created):
    monkeypatch.setattr(sys, "argv", ["session", "--task-name", "Launch", "--notes", "manual"])

    session.main()

    assert created == [{"notes": "manual"}]


def test_notes_default_to_blank(monkeypatch, created):
    monkeypatch.setattr(sys, "argv", ["session", "--task-name", "Launch"])

    session.main()

    assert created == [{"notes": ""}]
