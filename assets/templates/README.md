# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references.

Only one is actually used by the routine now:

| Filename | What to crop |
|---|---|
| `login_button.png` | The in-game "Log In" button — used only to detect that the login screen has loaded (`wait_for_image`), not to click it |

`quick_move_button.png`, `meso_market_icon.png`, `buy_mesos_tab.png`,
`yes_button.png`, `play_button.png`, `windows_run_prompt.png`, and
`windows_run_button.png` are all unused — simulated clicks/keys don't
register inside the actual game client at all (see the main
[README.md](../../README.md)'s "Why a Scheduled Task" section), so
`config/routine.json` uses `wait_for_user` checkpoints for those steps
instead of trying to click them. Not deleted from the repo in case that
ever changes, but nothing currently references them.

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
