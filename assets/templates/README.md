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

**If this dialog runs on the Secure Desktop** (screen dims, and normal
screenshot tools error/return nothing while it's open — used for UAC
elevation prompts), neither capturing the template nor the automated
`wait_for_image`/`click_image` steps at runtime will work: nothing outside
the secure desktop, including PyAutoGUI, can see or click into it. This
isn't just a calibration hurdle — it'll break the routine every time this
dialog appears during an actual run. Fix: disable "switch to the secure
desktop when prompting for elevation" (Local Security Policy →
Local Policies → Security Options, or the `PromptOnSecureDesktop` registry
value). This is a real (if usually minor) security trade-off — it's what
stops a malicious app from drawing a fake elevation prompt over the real
one — worth being aware you've turned off if you use this setup long-term.
| `login_button.png` | The in-game "Log In" button |
| `quick_move_button.png` | The "Quick Move" button |
| `meso_market_icon.png` | The "Meso Market" menu icon |
| `buy_mesos_tab.png` | The "Buy Mesos" tab |
| `yes_button.png` | The "Yes" confirmation button on the exit-game dialog (after Alt+F4) |

Tips:
- Crop tight and avoid text that could change (timestamps, counters).
- If matches are unreliable, lower `confidence` in `ScreenActions(...)` (default 0.8) — this requires OpenCV (`pip install opencv-python`), otherwise pyautogui falls back to exact pixel matching.
- Screen scaling/resolution changes will break existing templates — recapture if you change display settings.
