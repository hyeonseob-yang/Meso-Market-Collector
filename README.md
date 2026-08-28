# Meso Market Collector

Automates recording in-game Meso market price changes: launches the game,
logs in, navigates to the Meso Market, and reads the Sell/Buy price boxes —
using [PyAutoGUI](https://pyautogui.readthedocs.io/) for screen capture and
UI automation and [Pillow](https://pillow.readthedocs.io/) for image
handling.

## Setup

This code is edited from WSL but must actually **run under Windows Python**,
not WSL Python: `session.py`/`screen_actions.py` need PyAutoGUI to see and
click the real Windows desktop, which isn't accessible from inside WSL (WSL
can launch a Windows `.exe`, but can't screenshot or click its window).

From a Windows terminal (PowerShell/cmd, with Python installed on Windows):

```powershell
cd \\wsl$\Ubuntu\home\hya81\Meso-Market-Collector
python -m venv .venv-windows
.venv-windows\Scripts\activate
pip install -r requirements-dev.txt
```

(`\\wsl$\...` runs Windows Python directly against the files in this WSL
repo — no need to copy anything. Adjust the distro name if not `Ubuntu`.)

The plain `.venv` at the repo root (`python3 -m venv .venv` from WSL) is
still useful for editing/running the display-independent tests
(`routine.py`, `config.py`, `storage.py`) from within WSL — just not for
actually running the game automation.

## Configure

1. **Region boxes.** The 4 Sell-tab and 4 Buy-tab price boxes sit at the
   same on-screen position — only the tab changes — so `config/regions.json`
   defines just one shared set, `meso_1..4`. They're also stacked in a
   column with identical `left`/`width`/`height`, only `top` differing per
   row, so they're defined with the "column" shorthand:
   ```json
   {
     "meso": { "left": 412, "width": 90, "height": 22, "tops": [588, 620, 652, 684] }
   }
   ```
   which expands into 4 named regions (`meso_1`..`meso_4`) at load time —
   see [`config.py`](meso_market_collector/config.py). A plain box
   (`{"left", "top", "width", "height"}`, no `tops`) still works too, for
   anything that isn't a column-shaped layout.

   With the game window in place, find the pixel coordinates:
   ```bash
   python -m tools.find_coords
   ```
   Edit [`config/regions.json`](config/regions.json). The routine captures
   this same set twice — once per tab — and labels each recording
   `sell_meso_*`/`buy_meso_*` via `label_prefix` in
   [`config/routine.json`](config/routine.json), so the two tabs still end
   up as distinct rows in the CSV.

2. **Launch task.** The game is started via a Windows Scheduled Task rather
   than running the launcher/game exe directly — see "Why a Scheduled Task"
   below for why. One-time setup, from an **Administrator** PowerShell:
   ```powershell
   $shell = New-Object -ComObject WScript.Shell
   $sc = $shell.CreateShortcut("$env:USERPROFILE\Desktop\MapleStory.lnk")  # or wherever your game's shortcut is
   $sc.TargetPath; $sc.Arguments  # note these two values

   $action = New-ScheduledTaskAction -Execute "<TargetPath from above>" -Argument "<Arguments from above>"
   $principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
   Register-ScheduledTask -TaskName "MesoMarketCollector_MapleStoryViaLauncher" -Action $action -Principal $principal -Trigger $trigger -Force
   ```
   (`tools/find_shortcut_target.ps1` does the first part — finding a
   shortcut's target/arguments — for you.) Verify it works with
   `schtasks /run /tn "MesoMarketCollector_MapleStoryViaLauncher"` from a
   normal (non-admin) shell — it should go straight to the game's login
   screen with no prompt.

3. **Close task.** Closing the game hits a related problem — see "Why a
   Scheduled Task" below — so it's also done via a second task, this one
   just running `taskkill`. One-time setup, from an **Administrator**
   PowerShell:
   ```powershell
   $action = New-ScheduledTaskAction -Execute "taskkill.exe" -Argument "/F /IM MapleStory.exe"
   $principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
   Register-ScheduledTask -TaskName "MesoMarketCollector_KillMapleStory" -Action $action -Principal $principal -Trigger $trigger -Force
   ```
   (Adjust `/IM MapleStory.exe` if your game's actual process name differs
   — check with `Get-Process` while it's running.) Verify with
   `schtasks /run /tn "MesoMarketCollector_KillMapleStory"` from a normal
   (non-admin) shell while the game is open — it should close immediately,
   no prompt.

4. **Close-launcher task.** The launcher (e.g. `nexon_client.exe`) also
   needs closing, and — surprisingly — it needs the same elevated-task
   treatment even though the launcher itself never shows a UAC prompt: its
   process is a multi-process Electron-style app, and only *some* of its
   processes run at normal integrity — a plain `taskkill`/`Stop-Process`
   silently leaves the elevated ones running ("Access is denied" per
   process, easy to miss if you don't check each one). Same one-time
   setup as above:
   ```powershell
   $action = New-ScheduledTaskAction -Execute "taskkill.exe" -Argument "/F /IM nexon_client.exe"
   $principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
   Register-ScheduledTask -TaskName "MesoMarketCollector_KillNexonLauncher" -Action $action -Principal $principal -Trigger $trigger -Force
   ```
   Verify with `Get-Process -Name nexon_client` before and after running
   `schtasks /run /tn "MesoMarketCollector_KillNexonLauncher"` — the count
   should drop to zero, not just decrease.

5. **Template image.** Only `login_button.png` is still used — to confirm
   the login screen has actually loaded before handing off to you (see
   [`assets/templates/README.md`](assets/templates/README.md)). The others
   (Quick Move, Meso Market, Buy tab, exit-confirm) were used to click
   through those steps automatically; that doesn't work (see below) so
   they're no longer referenced by the routine, though the files are still
   there in case that changes.

6. **Routine steps.** [`config/routine.json`](config/routine.json) holds
   the ordered launch → login → navigate → record → close sequence,
   including `wait_for_image` polling checkpoints where a real click is
   needed (see "What's still automatable" below). Edit it if the actual
   flow differs.

### Why a Scheduled Task, not a direct launch/close?

Several things ruled out the simpler options, for both launching and
closing:
- Launching the game's exe directly (even elevated, even with the
  `__COMPAT_LAYER=RunAsInvoker` environment variable set) still triggered a
  UAC prompt with no way found to suppress it — the launcher requests
  elevation for it explicitly, which overrides both approaches.
- Once actually logged in, **simulated mouse clicks and keyboard shortcuts
  (Alt+F4) don't register in the game client at all** — found while trying
  to click Log In/Quick Move/Meso Market and to close via Alt+F4. Confirmed
  it wasn't a focus or coordinate problem (explicit window activation,
  verified-correct click coordinates, `pydirectinput` as an alternative
  input method, windowed vs. fullscreen mode — none of it changed the
  result). The same symptom (mouse position updates, hover-highlighting
  works, but click/key state never registers) reproduces identically in
  Terraria, an unrelated game. Attempts to get synthetic input registering
  past this anyway - a kernel-level input driver (Interception), direct
  calls to the legacy `mouse_event`/`keybd_event` Win32 APIs - are blocked
  by this coding environment's own automated safety controls, independent
  of anything decided in this project. That's the actual, complete reason
  these steps stay manual. Directly killing the elevated game process also
  fails the same way `Stop-Process` fails on any elevated process from a
  non-elevated caller (`Access is denied`) — just normal Windows privilege
  separation, unrelated to the input-registration issue above.

A Scheduled Task configured with `RunLevel: Highest` sidesteps all of
this by never asking the game to accept simulated input as if it were
real: the **launch** task points at the launcher exe with the same "jump
straight to this game" argument a desktop shortcut uses (e.g.
`nxl://launch/10100` for MapleStory) — functionally identical to
right-clicking the desktop shortcut and choosing "Run as administrator,"
just without the interactive prompt. The **close** tasks just run
`taskkill` directly against a process, which is normal OS process
management, not simulated input anything has to interpret at all.

There are two close tasks, not one — closing the *launcher* needed the
same treatment as the game, which was initially surprising since the
launcher's own UI (e.g. its Play button) does respond fine to simulated
clicks, unlike the game. The reason: the launcher is a multi-process
Electron-style app, and while its main window accepts clicks normally,
some of its background/helper processes run elevated (inherited from
being started by our elevated launch task) while others don't — a plain
`taskkill`/`Stop-Process` only ever gets the non-elevated ones, silently
leaving the rest running. So both "close" steps are process-kill tasks,
even though only one of the two targets is actually input-resistant.

**What's still automatable vs. not:** launching, reaching the login screen,
capturing price regions (pure screenshot reads, no input needed), and
closing are all automatable. Logging in and navigating the actual game
world (Quick Move, Meso Market, tab switching) needs real input, so the
routine polls for a screenshot match instead of trying to click through
those steps — `wait_for_image` with a `message` prints what to do, then
keeps checking the screen until it sees you've actually gotten there
(no Enter needed; see `assets/templates/README.md` for the `_active`
template images this needs). So a run looks like: script launches the
game, waits for the login screen, prints "log in and navigate to the Sell
tab" → **you** do that → script notices and captures Sell prices, prints
"click the Buy tab" → **you** do that → script notices, captures Buy
prices, closes the game, and closes the launcher.

## Run the full session (launch game, log in, record both tabs, close)

From the Windows Python venv set up above, run where you can see its
output (it prints what to do at each manual step, then polls the screen
and continues on its own once it detects you've done it — no keypress
needed, but you do need to actually be at the game to do the clicking):

```powershell
python -m meso_market_collector.session --task-name "MesoMarketCollector_MapleStoryViaLauncher"
```

The task name is passed in each run rather than stored in config. Recorded
prices are appended to `data/price_history.csv`. Price parsing (turning a
screenshot into a number) isn't implemented yet — see the note in
[`meso_market_collector/parser.py`](meso_market_collector/parser.py) for
options (OCR via pytesseract, etc). Until then, each recorded box also saves
its raw crop to `data/snapshots/` so no data is lost.

## Run a bare capture pass (game already running, no launch/navigation)

```bash
python -m meso_market_collector.collect
```

Captures every region in `config/regions.json` once and appends to the CSV
— useful for a cron job when the game/market screen is already open:

```cron
* * * * * cd /home/hya81/Meso-Market-Collector && .venv/bin/python -m meso_market_collector.collect >> data/collector.log 2>&1
```

## Test

```bash
pytest
```

The launch/login/navigate routine (`meso_market_collector/routine.py`) is
unit-tested with a fake screen backend — no display needed. The real screen
I/O (`screen_actions.py`, `capture.py`) needs an actual display/game and
isn't covered by automated tests.
