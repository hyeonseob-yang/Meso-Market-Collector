# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references:

| Filename | What to crop |
|---|---|
| `login_button.png` | The in-game "Log In" button |
| `quick_move_button.png` | The "Quick Move" button |
| `meso_market_icon.png` | The "Meso Market" menu icon |
| `buy_mesos_tab.png` | The "Buy Mesos" tab |
| `yes_button.png` | The "Yes" confirmation button on the exit-game dialog (after Alt+F4) |

`play_button.png`, `windows_run_prompt.png`, and `windows_run_button.png`
are no longer used — the Scheduled Task launch method (see main
[README.md](../../README.md)) goes straight to the login screen, skipping
the Play click and the Windows UAC prompt entirely. Not deleted from the
repo in case that method ever needs a manual-launcher fallback, but
`config/routine.json` doesn't reference them anymore.

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
