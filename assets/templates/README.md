# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references.

These are read-only detection targets — used to notice you've reached a
screen, never to click anything:

| Filename | What to crop |
|---|---|
| `login_button.png` | The in-game "Log In" button — detects the login screen has loaded |
| `sell_mesos_active.png` | **Still needed.** Something visible only when the Meso Market's Sell Mesos tab is actually showing/active (e.g. the tab in its selected/highlighted state, distinct from how it looks inactive) — lets the script notice you've logged in and navigated there, instead of you pressing Enter |
| `buy_mesos_active.png` | **Still needed.** Same idea, for the Buy Mesos tab in its active state |

To capture the two `_active` ones: navigate there manually once, take a
screenshot, crop tightly around whatever visually distinguishes "this tab is
the one currently selected" (e.g. a highlighted background, different text
color/weight) — not the tab's label text alone, since that's identical
whether the tab is active or not.

`quick_move_button.png`, `meso_market_icon.png`, `buy_mesos_tab.png`,
`yes_button.png`, `play_button.png`, `windows_run_prompt.png`, and
`windows_run_button.png` are all unused — simulated clicks/keys don't
register inside the actual game client at all (see the main
[README.md](../../README.md)'s "Why a Scheduled Task" section), so
`config/routine.json` polls for the `_active` images above instead of
trying to click through those steps. Not deleted from the repo in case
that ever changes, but nothing currently references them.

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
