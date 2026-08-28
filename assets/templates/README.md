# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references:

| Filename | What to crop |
|---|---|
| `play_button.png` | The launcher's "Play" button |
| `windows_run_prompt.png` | Any stable part of the Windows "Open File - Security Warning" dialog (e.g. its title bar) |
| `windows_run_button.png` | That dialog's "Run" button |
| `login_button.png` | The in-game "Log In" button |
| `quick_move_button.png` | The "Quick Move" button |
| `meso_market_icon.png` | The "Meso Market" menu icon |
| `buy_mesos_tab.png` | The "Buy Mesos" tab |
| `yes_button.png` | The "Yes" confirmation button on the exit-game dialog (after Alt+F4) |

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
