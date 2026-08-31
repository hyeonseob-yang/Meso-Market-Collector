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

    def wait_for_image(self, template, message=None):
        self.calls.append(("wait_for_image", template, message))

    def wait_for_stable_image(self, template):
        self.calls.append(("wait_for_stable_image", template))

    def click_image(self, template):
        self.calls.append(("click_image", template))

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

    def wait_for_user(self, message):
        self.calls.append(("wait_for_user", message))

    def save_price_row(self):
        self.calls.append(("save_price_row",))

    def clear_old_snapshots(self, max_age_days):
        self.calls.append(("clear_old_snapshots", max_age_days))


def test_load_steps_parses_json(tmp_path):
    routine_file = tmp_path / "routine.json"
    routine_file.write_text(
        json.dumps(
            [
                {"action": "launch"},
                {"action": "focus_window", "window_title": "MapleStory"},
                {"action": "wait_for_user", "message": "Log in, then press Enter"},
                {"action": "record_prices", "regions": {"meso_1": "Average", "meso_2": "Sell Buyout 100M"}},
                {"action": "press_key", "key": "esc"},
                {"action": "hotkey", "keys": ["alt", "f4"]},
                {"action": "save_price_row"},
                {"action": "clear_old_snapshots", "max_age_days": 7},
                {"action": "run_task", "task_name": "MesoMarketCollector_KillMapleStory"},
            ]
        )
    )

    steps = load_steps(routine_file)

    assert steps == [
        Step(action="launch"),
        Step(action="focus_window", window_title="MapleStory"),
        Step(action="wait_for_user", message="Log in, then press Enter"),
        Step(action="record_prices", regions={"meso_1": "Average", "meso_2": "Sell Buyout 100M"}),
        Step(action="press_key", key="esc"),
        Step(action="hotkey", keys=["alt", "f4"]),
        Step(action="save_price_row"),
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
                "meso_1": "Average",
                "meso_2": "Sell Buyout 100M",
                "meso_3": "Sell Buyout 1B",
                "meso_4": "Sell Buyout 10B",
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
                "meso_2": "Buy Buyout 100M",
                "meso_3": "Buy Buyout 1B",
                "meso_4": "Buy Buyout 10B",
            },
        ),
        Step(action="save_price_row"),
        Step(action="run_task", task_name="MesoMarketCollector_KillMapleStory"),
        Step(action="run_task", task_name="MesoMarketCollector_KillNexonLauncher"),
    ]
    actions = FakeActions()

    run_routine(steps, task_name="MesoMarketCollector_MapleStoryViaLauncher", actions=actions)

    assert actions.calls == [
        ("launch", "MesoMarketCollector_MapleStoryViaLauncher"),
        ("focus_window", "MapleStory"),
        ("wait_for_image", "login_button.png", None),
        ("wait_for_image", "sell_mesos_active.png", "Log in and navigate to the Meso Market Sell tab"),
        (
            "record_prices",
            {
                "meso_1": "Average",
                "meso_2": "Sell Buyout 100M",
                "meso_3": "Sell Buyout 1B",
                "meso_4": "Sell Buyout 10B",
            },
        ),
        ("wait_for_image", "buy_mesos_active.png", "Click the Buy Mesos tab"),
        (
            "record_prices",
            {
                "meso_2": "Buy Buyout 100M",
                "meso_3": "Buy Buyout 1B",
                "meso_4": "Buy Buyout 10B",
            },
        ),
        ("save_price_row",),
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

    assert actions.calls == [("wait_for_image", "thing.png", "do the thing")]


def test_run_routine_dispatches_wait_for_image_without_message():
    actions = FakeActions()

    run_routine([Step(action="wait_for_image", template="thing.png")], task_name="x", actions=actions)

    assert actions.calls == [("wait_for_image", "thing.png", None)]


def test_run_routine_dispatches_wait_for_user():
    actions = FakeActions()

    run_routine([Step(action="wait_for_user", message="do the thing")], task_name="x", actions=actions)

    assert actions.calls == [("wait_for_user", "do the thing")]


def test_run_routine_dispatches_save_price_row():
    actions = FakeActions()

    run_routine([Step(action="save_price_row")], task_name="x", actions=actions)

    assert actions.calls == [("save_price_row",)]


def test_run_routine_dispatches_clear_old_snapshots():
    actions = FakeActions()

    run_routine([Step(action="clear_old_snapshots", max_age_days=7)], task_name="x", actions=actions)

    assert actions.calls == [("clear_old_snapshots", 7)]


def test_run_routine_rejects_unknown_action():
    actions = FakeActions()

    with pytest.raises(ValueError, match="Unknown action"):
        run_routine([Step(action="teleport")], task_name="x", actions=actions)
