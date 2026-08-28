"""CLI entrypoint: launch the game and run the full price-collection routine.

    python -m meso_market_collector.session --task-name "MesoMarketCollector_MapleStoryViaLauncher"

The task name refers to a pre-configured Windows Scheduled Task (RunLevel:
Highest) that launches the game - see README.md for why a raw exe path
isn't used here (UAC prompts that couldn't be suppressed, and anti-cheat
flagging a direct exe launch as a "hacking program").
"""
from __future__ import annotations

import argparse

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
    args = parser.parse_args()

    steps = load_steps(args.routine)
    actions = ScreenActions()
    run_routine(steps, task_name=args.task_name, actions=actions)


if __name__ == "__main__":
    main()
