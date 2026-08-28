# Template images

`screen_actions.ScreenActions` finds on-screen buttons with
`pyautogui.locateOnScreen`, which needs a small reference screenshot of each
button/element. Capture a tight crop of just the button (no surrounding
window chrome) at the resolution you'll actually run at, save it here under
the exact filename `config/routine.json` references:

| Filename | What to crop |
|---|---|
| `play_button.png` | The launcher's "Play" button |
| `windows_run_prompt.png` | Any stable part of the Windows UAC elevation prompt ("Do you want to allow this app to make changes to your device?") |
| `windows_run_button.png` | That prompt's "Yes" button |
| `login_button.png` | The in-game "Log In" button |
| `quick_move_button.png` | The "Quick Move" button |
| `meso_market_icon.png` | The "Meso Market" menu icon |
| `buy_mesos_tab.png` | The "Buy Mesos" tab |
| `yes_button.png` | The "Yes" confirmation button on the exit-game dialog (after Alt+F4) |

**Secure Desktop caveat:** the UAC elevation prompt above runs on Windows'
Secure Desktop (screen dims, and normal screenshot tools error/return
nothing while it's open). Neither capturing its template nor the automated
`wait_and_click_image`/`click_image` steps at runtime will work there:
nothing outside the secure desktop, including PyAutoGUI, can see or click
into it. Fix — Control Panel → User Account Control Settings → "Show more
details" → "Change when these notifications appear" → move the slider to
"Notify me only when apps try to make changes to my computer (do not dim my
desktop)" → OK → Yes.

This is a real (if usually minor) security trade-off — it's what stops a
malicious app from drawing a fake elevation prompt over the real one — so
it's reasonable to only turn it on while capturing the template and revert
it after. But if this same UAC prompt reappears every time the routine
actually launches the game (not just once, e.g. after a game update), the
automated click step will hit the same secure-desktop block your screenshot
tool did — so the setting would need to stay changed while running the
routine for real, not just during calibration.

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
