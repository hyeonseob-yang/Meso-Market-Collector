"""The launch -> login -> navigate -> record -> close routine, as data.

Kept deliberately separate from anything that touches a real screen: `Step`
and `run_routine` are pure dispatch logic, testable with a fake `actions`
object. The real screen/process I/O lives in screen_actions.ScreenActions,
which implements the same methods `run_routine` calls here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Step:
    action: str
    template: str | None = None
    regions: dict[str, str] | None = None
    key: str | None = None
    keys: list[str] | None = None
    window_title: str | None = None
    task_name: str | None = None
    message: str | None = None


def load_steps(path: Path) -> list[Step]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Step(**entry) for entry in raw]


class GameActions(Protocol):
    """What run_routine needs; screen_actions.ScreenActions implements this
    for real, tests use a fake."""

    def launch(self, task_name: str) -> None: ...
    def wait_and_click_image(self, template: str) -> None: ...
    def wait_for_image(self, template: str, message: str | None = None) -> None: ...
    def wait_for_stable_image(self, template: str) -> None: ...
    def click_image(self, template: str) -> None: ...
    def record_prices(self, regions: dict[str, str]) -> None: ...
    def press_key(self, key: str) -> None: ...
    def hotkey(self, keys: list[str]) -> None: ...
    def focus_window(self, window_title: str) -> None: ...
    def run_task(self, task_name: str) -> None: ...
    def wait_for_user(self, message: str) -> None: ...
    def save_price_row(self) -> None: ...


def run_routine(steps: list[Step], task_name: str, actions: GameActions) -> None:
    for step in steps:
        if step.action == "launch":
            actions.launch(task_name)
        elif step.action == "wait_and_click_image":
            actions.wait_and_click_image(step.template)
        elif step.action == "wait_for_image":
            actions.wait_for_image(step.template, step.message)
        elif step.action == "wait_for_stable_image":
            actions.wait_for_stable_image(step.template)
        elif step.action == "click_image":
            actions.click_image(step.template)
        elif step.action == "record_prices":
            actions.record_prices(step.regions)
        elif step.action == "press_key":
            actions.press_key(step.key)
        elif step.action == "hotkey":
            actions.hotkey(step.keys)
        elif step.action == "focus_window":
            actions.focus_window(step.window_title)
        elif step.action == "run_task":
            actions.run_task(step.task_name)
        elif step.action == "wait_for_user":
            actions.wait_for_user(step.message)
        elif step.action == "save_price_row":
            actions.save_price_row()
        else:
            raise ValueError(f"Unknown action: {step.action!r}")
