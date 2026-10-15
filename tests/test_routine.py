import json

import pytest

from meso_market_collector.routine import Step, load_steps, run_routine


class FakeActions:
    """Records every call made on it, in order, instead of touching a screen."""

    def __init__(self):
        self.calls: list[tuple] = []

    def launch(self, task_name):
        self.calls.append(("launch", task_name))

    def wait_and_click_image(self, template):
        self.calls.append(("wait_and_click_image", template))

    def wait_for_image(self, template, message=None, confidence=None):
        self.calls.append(("wait_for_image", template, message, confidence))

    def wait_for_stable_image(self, template):
        self.calls.append(("wait_for_stable_image", template))

    def click_image(self, template, confidence=None):
        # Confidence only recorded when a step sets one, so the many
        # plain-click expectations stay ("click_image", template).
        call = ("click_image", template) if confidence is None else ("click_image", template, confidence)
        self.calls.append(call)

    def click_image_if_present(self, template, confidence=None, **timing):
        self.calls.append(("click_image_if_present", template, confidence, timing))

    def click_until_image(self, template, until, message=None, confidence=None, **tuning):
        self.calls.append(("click_until_image", template, until, message, confidence, tuning))

    def record_prices(self, regions):
        self.calls.append(("record_prices", dict(regions)))

    def press_key(self, key):
        self.calls.append(("press_key", key))

    def hotkey(self, keys):
        self.calls.append(("hotkey", tuple(keys)))

    def focus_window(self, window_title):
        self.calls.append(("focus_window", window_title))

    def run_task(self, task_name):
        self.calls.append(("run_task", task_name))

    def wait_for_process_exit(self, processes):
        self.calls.append(("wait_for_process_exit", tuple(processes)))

    def record_leftovers(self, processes):
        self.calls.append(("record_leftovers", tuple(processes)))

    def wait_for_user(self, message):
        self.calls.append(("wait_for_user", message))

    def wait(self, seconds):
        self.calls.append(("wait", seconds))

    def save_price_row(self):
        self.calls.append(("save_price_row",))

    def post_price_row(self):
        self.calls.append(("post_price_row",))

    def clear_old_snapshots(self, max_age_days):
        self.calls.append(("clear_old_snapshots", max_age_days))


def test_real_routine_cleans_up_then_focuses_game_before_any_screen_check():
    """Guards config/routine.json's ordering: close leftovers, then launch,
    then focus the game *before* anything looks at the screen - screenshots
    only see the top window, so an image wait before focusing just times out
    behind whatever else is in front (e.g. the terminal)."""
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    actions = [s.action for s in steps]

    launch = actions.index("launch")
    assert [s.task_name for s in steps[:launch] if s.action == "run_task"] == [
        "MesoMarketCollector_KillMapleStory",
        "MesoMarketCollector_KillNexonLauncher",
    ]
    assert steps[launch + 1] == Step(action="focus_window", window_title="MapleStory")
    screen_checks = {"wait_for_image", "wait_for_stable_image", "click_image", "click_until_image", "record_prices"}
    assert not screen_checks & set(actions[: launch + 1])


def test_load_steps_parses_json(tmp_path):
    routine_file = tmp_path / "routine.json"
    routine_file.write_text(
        json.dumps(
            [
                {"action": "launch"},
                {"action": "focus_window", "window_title": "MapleStory"},
                {"action": "wait_for_image", "template": "login_button.png", "confidence": 0.986},
                {"action": "wait_for_user", "message": "Log in, then press Enter"},
                {"action": "record_prices", "regions": {"meso_1": "average", "meso_2": "sell100M"}},
                {"action": "press_key", "key": "esc"},
                {"action": "hotkey", "keys": ["alt", "f4"]},
                {"action": "save_price_row"},
                {"action": "post_price_row"},
                {"action": "clear_old_snapshots", "max_age_days": 7},
                {"action": "run_task", "task_name": "MesoMarketCollector_KillMapleStory"},
            ]
        )
    )

    steps = load_steps(routine_file)

    assert steps == [
        Step(action="launch"),
        Step(action="focus_window", window_title="MapleStory"),
        Step(action="wait_for_image", template="login_button.png", confidence=0.986),
        Step(action="wait_for_user", message="Log in, then press Enter"),
        Step(action="record_prices", regions={"meso_1": "average", "meso_2": "sell100M"}),
        Step(action="press_key", key="esc"),
        Step(action="hotkey", keys=["alt", "f4"]),
        Step(action="save_price_row"),
        Step(action="post_price_row"),
        Step(action="clear_old_snapshots", max_age_days=7),
        Step(action="run_task", task_name="MesoMarketCollector_KillMapleStory"),
    ]


def test_run_routine_dispatches_each_step_in_order():
    # "launch" triggers a scheduled task that goes straight to the login
    # screen (see screen_actions.ScreenActions.launch) - no Play click or
    # Windows Run prompt to handle here anymore.
    steps = [
        Step(action="launch"),
        Step(action="focus_window", window_title="MapleStory"),
        Step(action="wait_for_image", template="login_button.png"),
        Step(
            action="wait_for_image",
            template="sell_mesos_active.png",
            message="Log in and navigate to the Meso Market Sell tab",
        ),
        Step(
            action="record_prices",
            regions={
                "meso_1": "average",
                "meso_2": "sell100M",
                "meso_3": "sell1B",
                "meso_4": "sell10B",
            },
        ),
        Step(
            action="wait_for_image",
            template="buy_mesos_active.png",
            message="Click the Buy Mesos tab",
        ),
        Step(
            action="record_prices",
            regions={
                "meso_2": "buy100M",
                "meso_3": "buy1B",
                "meso_4": "buy10B",
            },
        ),
        Step(action="save_price_row"),
        Step(action="post_price_row"),
        Step(action="run_task", task_name="MesoMarketCollector_KillMapleStory"),
        Step(action="run_task", task_name="MesoMarketCollector_KillNexonLauncher"),
    ]
    actions = FakeActions()

    run_routine(steps, task_name="MesoMarketCollector_MapleStoryViaLauncher", actions=actions)

    assert actions.calls == [
        ("launch", "MesoMarketCollector_MapleStoryViaLauncher"),
        ("focus_window", "MapleStory"),
        ("wait_for_image", "login_button.png", None, None),
        ("wait_for_image", "sell_mesos_active.png", "Log in and navigate to the Meso Market Sell tab", None),
        (
            "record_prices",
            {
                "meso_1": "average",
                "meso_2": "sell100M",
                "meso_3": "sell1B",
                "meso_4": "sell10B",
            },
        ),
        ("wait_for_image", "buy_mesos_active.png", "Click the Buy Mesos tab", None),
        (
            "record_prices",
            {
                "meso_2": "buy100M",
                "meso_3": "buy1B",
                "meso_4": "buy10B",
            },
        ),
        ("save_price_row",),
        ("post_price_row",),
        ("run_task", "MesoMarketCollector_KillMapleStory"),
        ("run_task", "MesoMarketCollector_KillNexonLauncher"),
    ]


def test_run_routine_dispatches_press_key():
    actions = FakeActions()

    run_routine([Step(action="press_key", key="esc")], task_name="x", actions=actions)

    assert actions.calls == [("press_key", "esc")]


def test_run_routine_dispatches_hotkey():
    actions = FakeActions()

    run_routine([Step(action="hotkey", keys=["alt", "f4"])], task_name="x", actions=actions)

    assert actions.calls == [("hotkey", ("alt", "f4"))]


def test_run_routine_dispatches_focus_window():
    actions = FakeActions()

    run_routine([Step(action="focus_window", window_title="MapleStory")], task_name="x", actions=actions)

    assert actions.calls == [("focus_window", "MapleStory")]


def test_run_routine_passes_click_image_confidence():
    actions = FakeActions()

    run_routine(
        [Step(action="click_image", template="buy_mesos_tab.png", confidence=0.95)], task_name="x", actions=actions
    )

    assert actions.calls == [("click_image", "buy_mesos_tab.png", 0.95)]


def test_real_routine_tab_clicks_use_a_strict_confidence():
    """The Sell and Buy tabs look alike (light "... Mesos" label on a plain
    tab) and cross-match at ~0.75-0.94, so the default 0.8 could click the
    wrong one - an exact template scores ~1.0, so 0.95 separates them."""
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    tab_clicks = [s for s in steps if s.template in ("sell_mesos_tab.png", "buy_mesos_tab.png")]

    assert len(tab_clicks) == 2
    assert all(s.confidence is not None and s.confidence >= 0.95 for s in tab_clicks)


def test_run_routine_dispatches_click_image_if_present():
    actions = FakeActions()

    run_routine(
        [
            Step(action="click_image_if_present", template="sell_mesos_tab.png", seconds=10),
            Step(action="click_image_if_present", template="sell_mesos_tab.png"),
        ],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [
        ("click_image_if_present", "sell_mesos_tab.png", None, {"seconds": 10}),
        # No `seconds` on the step -> the implementation's own default applies.
        ("click_image_if_present", "sell_mesos_tab.png", None, {}),
    ]


def test_real_routine_selects_each_tab_before_recording_it():
    """The market can open on either tab, so the routine must click the Sell
    tab (when it isn't already selected) and confirm it before recording
    Sell prices - then the same for Buy - rather than assume which tab is
    showing."""
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    described = [(s.action, s.template) for s in steps]
    sell_record, buy_record = [i for i, s in enumerate(steps) if s.action == "record_prices"]

    assert described[sell_record - 2 : sell_record] == [
        ("click_image_if_present", "sell_mesos_tab.png"),
        ("wait_for_image", "sell_mesos_active.png"),
    ]
    assert described[buy_record - 2 : buy_record] == [
        ("click_image", "buy_mesos_tab.png"),
        ("wait_for_image", "buy_mesos_active.png"),
    ]


def test_run_routine_dispatches_wait():
    actions = FakeActions()

    run_routine([Step(action="wait", seconds=25)], task_name="x", actions=actions)

    assert actions.calls == [("wait", 25)]


def test_real_routine_pauses_between_seeing_and_clicking_log_in():
    """The Log In button shows before the game accepts clicks, and a missed
    click can't be retried (the hovered button no longer matches) - so the
    first click has to wait."""
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    seen = next(i for i, s in enumerate(steps) if s.action == "wait_for_image" and s.template == "login_button.png")
    clicked = next(i for i, s in enumerate(steps) if s.action == "click_until_image" and s.template == "login_button.png")

    assert any(s.action == "wait" and s.seconds for s in steps[seen + 1 : clicked])


def test_run_routine_dispatches_run_task():
    actions = FakeActions()

    run_routine([Step(action="run_task", task_name="SomeOtherTask")], task_name="x", actions=actions)

    assert actions.calls == [("run_task", "SomeOtherTask")]


def test_run_routine_dispatches_wait_for_image_with_message():
    actions = FakeActions()

    run_routine(
        [Step(action="wait_for_image", template="thing.png", message="do the thing")],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [("wait_for_image", "thing.png", "do the thing", None)]


def test_run_routine_dispatches_wait_for_image_without_message():
    actions = FakeActions()

    run_routine([Step(action="wait_for_image", template="thing.png")], task_name="x", actions=actions)

    assert actions.calls == [("wait_for_image", "thing.png", None, None)]


def test_run_routine_dispatches_wait_for_image_with_confidence():
    # e.g. login_button.png needs a stricter-than-default confidence to tell
    # the button's disabled and enabled states apart - see config/routine.json.
    actions = FakeActions()

    run_routine(
        [Step(action="wait_for_image", template="login_button.png", confidence=0.986)],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [("wait_for_image", "login_button.png", None, 0.986)]


def test_run_routine_dispatches_click_until_image_with_defaults():
    actions = FakeActions()

    run_routine(
        [Step(action="click_until_image", template="login_button.png", until="quick_move_button.png")],
        task_name="x",
        actions=actions,
    )

    # Unset attempts/retry_seconds aren't passed, so the implementation's
    # own defaults apply.
    assert actions.calls == [
        ("click_until_image", "login_button.png", "quick_move_button.png", None, None, {})
    ]


def test_run_routine_dispatches_click_until_image_with_tuning():
    actions = FakeActions()

    run_routine(
        [
            Step(
                action="click_until_image",
                template="login_button.png",
                until="quick_move_button.png",
                message="click it by hand",
                confidence=0.986,
                attempts=5,
                retry_seconds=10,
            )
        ],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [
        (
            "click_until_image",
            "login_button.png",
            "quick_move_button.png",
            "click it by hand",
            0.986,
            {"attempts": 5, "retry_seconds": 10},
        )
    ]


def test_run_routine_dispatches_wait_for_process_exit():
    actions = FakeActions()

    run_routine(
        [Step(action="wait_for_process_exit", processes=["MapleStory.exe", "nexon_client.exe"])],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [("wait_for_process_exit", ("MapleStory.exe", "nexon_client.exe"))]


def test_run_routine_dispatches_wait_for_user():
    actions = FakeActions()

    run_routine([Step(action="wait_for_user", message="do the thing")], task_name="x", actions=actions)

    assert actions.calls == [("wait_for_user", "do the thing")]


def test_run_routine_dispatches_save_price_row():
    actions = FakeActions()

    run_routine([Step(action="save_price_row")], task_name="x", actions=actions)

    assert actions.calls == [("save_price_row",)]


def test_run_routine_dispatches_post_price_row():
    actions = FakeActions()

    run_routine([Step(action="post_price_row")], task_name="x", actions=actions)

    assert actions.calls == [("post_price_row",)]


def test_run_routine_dispatches_clear_old_snapshots():
    actions = FakeActions()

    run_routine([Step(action="clear_old_snapshots", max_age_days=7)], task_name="x", actions=actions)

    assert actions.calls == [("clear_old_snapshots", 7)]


def test_run_routine_rejects_unknown_action():
    actions = FakeActions()

    with pytest.raises(ValueError, match="Unknown action"):
        run_routine([Step(action="teleport")], task_name="x", actions=actions)


def test_run_routine_passes_failure_max_age_days_to_clear_old_snapshots():
    calls = []

    class Actions(FakeActions):
        def clear_old_snapshots(self, max_age_days, **limits):
            calls.append((max_age_days, limits))

    run_routine(
        [Step(action="clear_old_snapshots", max_age_days=7, failure_max_age_days=90)],
        task_name="x",
        actions=Actions(),
    )

    assert calls == [(7, {"failure_max_age_days": 90})]


def test_real_routine_keeps_failure_screenshots_longer_than_ordinary_snapshots():
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    (cleanup,) = [s for s in steps if s.action == "clear_old_snapshots"]

    assert cleanup.failure_max_age_days is not None
    assert cleanup.failure_max_age_days > cleanup.max_age_days


def test_run_routine_dispatches_record_leftovers():
    actions = FakeActions()

    run_routine(
        [Step(action="record_leftovers", processes=["MapleStory.exe", "nexon_client.exe"])],
        task_name="x",
        actions=actions,
    )

    assert actions.calls == [("record_leftovers", ("MapleStory.exe", "nexon_client.exe"))]


def test_real_routine_records_leftovers_before_closing_anything():
    from pathlib import Path

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")

    assert steps[0] == Step(action="record_leftovers", processes=["MapleStory.exe", "nexon_client.exe"])


def test_real_routine_records_every_price_field_once():
    from pathlib import Path

    from meso_market_collector.storage import PRICE_FIELDS

    steps = load_steps(Path(__file__).resolve().parent.parent / "config" / "routine.json")
    recorded = [field for s in steps if s.action == "record_prices" for field in s.regions.values()]

    assert sorted(recorded) == sorted(PRICE_FIELDS)
