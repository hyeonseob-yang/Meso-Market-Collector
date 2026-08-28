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
    regions: list[str] | None = None
    label_prefix: str | None = None


def load_steps(path: Path) -> list[Step]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Step(**entry) for entry in raw]


class GameActions(Protocol):
    """What run_routine needs; screen_actions.ScreenActions implements this
    for real, tests use a fake."""

    def launch(self, launcher_path: str) -> None: ...
    def wait_and_click_image(self, template: str) -> None: ...
    def wait_for_image(self, template: str) -> None: ...
    def wait_for_stable_image(self, template: str) -> None: ...
    def click_image(self, template: str) -> None: ...
    def record_prices(self, region_names: list[str], label_prefix: str | None = None) -> None: ...
    def close(self) -> None: ...


def run_routine(steps: list[Step], launcher_path: str, actions: GameActions) -> None:
    for step in steps:
        if step.action == "launch":
            actions.launch(launcher_path)
        elif step.action == "wait_and_click_image":
            actions.wait_and_click_image(step.template)
        elif step.action == "wait_for_image":
            actions.wait_for_image(step.template)
        elif step.action == "wait_for_stable_image":
            actions.wait_for_stable_image(step.template)
        elif step.action == "click_image":
            actions.click_image(step.template)
        elif step.action == "record_prices":
            actions.record_prices(step.regions, step.label_prefix)
        elif step.action == "close":
            actions.close()
        else:
            raise ValueError(f"Unknown action: {step.action!r}")
