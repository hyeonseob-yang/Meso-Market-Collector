"""CLI entrypoint: launch the game and run the full price-collection routine.

    python -m meso_market_collector.session --task-name "MesoMarketCollector_MapleStoryViaLauncher"

The task name refers to the Scheduled Task that launches the game elevated,
without a UAC prompt.
"""
from __future__ import annotations

import argparse
import ctypes

from .routine import load_steps, run_routine
from .screen_actions import ScreenActions

DEFAULT_ROUTINE_PATH = "config/routine.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task-name",
        required=True,
        help="Name of the Scheduled Task that launches the game.",
    )
    parser.add_argument(
        "--routine",
        default=DEFAULT_ROUTINE_PATH,
        help=f"Path to the routine step list (default: {DEFAULT_ROUTINE_PATH})",
    )
    parser.add_argument(
        "--notes",
        default="",
        help='Text saved in the row\'s Notes, in the CSV and on Tracker - e.g. "manual" '
        "to tell a hand-started run from a scheduled one (which leaves it blank).",
    )
    args = parser.parse_args()

    # The game runs elevated (via the launch task), and Windows silently
    # drops simulated input sent to an elevated window from a
    # non-elevated process - clicks/keys would just do nothing, no error.
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print(
            "WARNING: not running elevated - simulated clicks/keys won't "
            "reach the game. Run via the MesoMarketCollector_Session "
            "scheduled task, or from an Administrator PowerShell.",
            flush=True,
        )

    steps = load_steps(args.routine)
    actions = ScreenActions(notes=args.notes)
    run_routine(steps, task_name=args.task_name, actions=actions)


if __name__ == "__main__":
    main()
