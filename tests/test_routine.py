import json

import pytest

from meso_market_collector.routine import Step, load_steps, run_routine


class FakeActions:
    """Records every call made on it, in order, instead of touching a screen."""

    def __init__(self):
        self.calls: list[tuple] = []

    def launch(self, launcher_path):
        self.calls.append(("launch", launcher_path))

    def wait_and_click_image(self, template):
        self.calls.append(("wait_and_click_image", template))

    def wait_for_image(self, template):
        self.calls.append(("wait_for_image", template))

    def wait_for_stable_image(self, template):
        self.calls.append(("wait_for_stable_image", template))

    def click_image(self, template):
        self.calls.append(("click_image", template))

    def record_prices(self, region_names, label_prefix=None):
        self.calls.append(("record_prices", tuple(region_names), label_prefix))

    def close(self):
        self.calls.append(("close",))


def test_load_steps_parses_json(tmp_path):
    routine_file = tmp_path / "routine.json"
    routine_file.write_text(
        json.dumps(
            [
                {"action": "launch"},
                {"action": "click_image", "template": "login_button.png"},
                {"action": "record_prices", "regions": ["meso_1", "meso_2"], "label_prefix": "sell"},
                {"action": "close"},
            ]
        )
    )

    steps = load_steps(routine_file)

    assert steps == [
        Step(action="launch"),
        Step(action="click_image", template="login_button.png"),
        Step(action="record_prices", regions=["meso_1", "meso_2"], label_prefix="sell"),
        Step(action="close"),
    ]


def test_run_routine_dispatches_each_step_in_order():
    steps = [
        Step(action="launch"),
        Step(action="wait_and_click_image", template="windows_run_prompt.png"),
        Step(action="wait_for_image", template="login_button.png"),
        Step(action="wait_for_stable_image", template="login_button.png"),
        Step(action="click_image", template="login_button.png"),
        Step(action="click_image", template="quick_move_button.png"),
        Step(action="click_image", template="meso_market_icon.png"),
        Step(
            action="record_prices",
            regions=["meso_1", "meso_2", "meso_3", "meso_4"],
            label_prefix="sell",
        ),
        Step(action="click_image", template="buy_mesos_tab.png"),
        Step(
            action="record_prices",
            regions=["meso_1", "meso_2", "meso_3", "meso_4"],
            label_prefix="buy",
        ),
        Step(action="close"),
    ]
    actions = FakeActions()

    run_routine(steps, launcher_path="C:/Games/Launcher.exe", actions=actions)

    assert actions.calls == [
        ("launch", "C:/Games/Launcher.exe"),
        ("wait_and_click_image", "windows_run_prompt.png"),
        ("wait_for_image", "login_button.png"),
        ("wait_for_stable_image", "login_button.png"),
        ("click_image", "login_button.png"),
        ("click_image", "quick_move_button.png"),
        ("click_image", "meso_market_icon.png"),
        ("record_prices", ("meso_1", "meso_2", "meso_3", "meso_4"), "sell"),
        ("click_image", "buy_mesos_tab.png"),
        ("record_prices", ("meso_1", "meso_2", "meso_3", "meso_4"), "buy"),
        ("close",),
    ]


def test_run_routine_rejects_unknown_action():
    actions = FakeActions()

    with pytest.raises(ValueError, match="Unknown action"):
        run_routine([Step(action="teleport")], launcher_path="x", actions=actions)
