# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references.

Used by `config/routine.json`:

| Filename | What to crop | Used to |
|---|---|---|
| `login_button.png` | The in-game "Log In" button, in its enabled state | Detect the login screen has loaded, then click it |
| `quick_move_button.png` | The Quick Move button | Detect you're in the game world, then click it |
| `meso_market_icon.png` | The Meso Market entry in the Quick Move menu | Click it |
| `sell_mesos_active.png` | Something visible only when the Sell Mesos tab is active (e.g. the tab in its selected/highlighted state) | Confirm the Sell tab is showing before recording |
| `buy_mesos_tab.png` | The Buy Mesos tab (inactive state) | Click it |
| `buy_mesos_active.png` | Same idea as `sell_mesos_active.png`, for the Buy Mesos tab | Confirm the Buy tab is showing before recording |

To capture the two `_active` ones: navigate there manually once, take a
screenshot, crop tightly around whatever visually distinguishes "this tab is
the one currently selected" (e.g. a highlighted background, different text
color/weight) — not the tab's label text alone, since that's identical
whether the tab is active or not.

`yes_button.png`, `play_button.png`, `windows_run_prompt.png`, and
`windows_run_button.png` are unused — left over from earlier launch/close
approaches (see the main [README.md](../../README.md)'s "Why a Scheduled
Task" section).

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
- On a machine whose display differs from the one these were snipped on, save your recaptures to `assets/templates.local/` (gitignored) under the same filenames instead of overwriting these. Any template found there is used in place of the one here, per file, so the shared set keeps working on the other machine.
