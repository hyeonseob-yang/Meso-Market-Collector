"""CLI entrypoint: launch the game and run the full price-collection routine.

    python -m meso_market_collector.session --launcher-path "C:\\Games\\Launcher.exe"
"""
from __future__ import annotations

import argparse

from .routine import load_steps, run_routine
from .screen_actions import ScreenActions

DEFAULT_ROUTINE_PATH = "config/routine.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--launcher-path",
        required=True,
        help="Path to the game's launcher executable.",
    )
    parser.add_argument(
        "--routine",
        default=DEFAULT_ROUTINE_PATH,
        help=f"Path to the routine step list (default: {DEFAULT_ROUTINE_PATH})",
    )
    args = parser.parse_args()

    steps = load_steps(args.routine)
    actions = ScreenActions()
    run_routine(steps, launcher_path=args.launcher_path, actions=actions)


if __name__ == "__main__":
    main()
