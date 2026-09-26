# Meso Market Collector

Automates recording in-game Meso market price changes: launches the game,
logs in, navigates to the Meso Market, and reads the Sell/Buy price boxes —
using [PyAutoGUI](https://pyautogui.readthedocs.io/) for screen capture and
UI automation and [Pillow](https://pillow.readthedocs.io/) for image
handling.

## Setup

This project is Windows-only, not just "needs a real desktop" — a few
specific things about it don't run anywhere else:

- `screen_actions.py` imports [PyGetWindow](https://github.com/asweigart/pygetwindow)
  for `focus_window`, which raises `NotImplementedError` at import time on
  Linux ("PyGetWindow currently does not support Linux") - the module fails
  to load before PyAutoGUI's own screen access even comes into play.
- `launch`/`run_task` shell out to `schtasks`, the Windows Task Scheduler
  CLI, to start/kill the game - chosen specifically to get around Windows
  UAC elevation (see below). There's no equivalent command on other OSes.
- MapleStory itself has no native Linux client; running it via Wine/Proton
  isn't something this project targets or accounts for (elevation, window
  titles, and process names would all differ).

Develop and run it directly on Windows — clone straight onto the Windows
filesystem (not through a WSL mount) and use Windows Python throughout,
from PowerShell/cmd:

```powershell
git clone <this-repo-url>
cd Meso-Market-Collector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

(If activation fails with an execution-policy error rather than running,
run `Set-ExecutionPolicy -Scope Process RemoteSigned` first and retry.)

`routine.py` and everything else that doesn't touch a real screen
(`config.py`, `storage.py`, `api_client.py`) is plain, portable Python, so
the whole non-screen test suite also just runs there with `pytest` — no
separate Linux/WSL venv needed for that anymore.

## Configure

1. **Region boxes.** The 4 Sell-tab and 4 Buy-tab price boxes sit at the
   same on-screen position — only the tab changes — so `config/regions.json`
   defines just one shared set. They're also stacked in a column with
   identical `left`/`width`/`height`, only `top` differing per row, so
   they're defined with the "column" shorthand, with an explicit `names`
   list (rather than the shorthand's default `meso_1`, `meso_2`, ... —
   the actual tier each box shows is more meaningful than its position):
   ```json
   {
     "meso": {
       "left": 412, "width": 90, "height": 22,
       "tops": [588, 620, 652, 684],
       "names": ["meso_average", "meso_100m", "meso_1b", "meso_10b"]
     }
   }
   ```
   see [`config.py`](meso_market_collector/config.py). A plain box
   (`{"left", "top", "width", "height"}`, no `tops`) still works too, for
   anything that isn't a column-shaped layout.

   With the game window in place, find the pixel coordinates:
   ```bash
   python -m tools.find_coords
   ```
   Copy [`config/regions.json`](config/regions.json) to
   `config/regions.local.json` and edit that copy — it's gitignored, and
   used instead of `regions.json` whenever it exists, so each machine keeps
   its own coordinates without touching the committed default (which is
   still used when there's no local copy). `meso_average` reads
   identically regardless of which tab is showing (confirmed, not just
   assumed), so it's only captured once, on the Sell pass. Each
   `record_prices` step in [`config/routine.json`](config/routine.json)
   maps region names directly to their final CSV column name — e.g.
   `{"meso_100m": "Sell Buyout 100M"}` — so what you see in
   `data/price_history.csv` matches what's in `config/routine.json`
   directly, with no separate relabeling step in between.

2. **Launch task.** The game is started via a Windows Scheduled Task rather
   than running the launcher/game exe directly — see "Why a Scheduled Task"
   below for why. One-time setup, from an **Administrator** PowerShell:
   ```powershell
   $shell = New-Object -ComObject WScript.Shell
   $sc = $shell.CreateShortcut("$env:USERPROFILE\Desktop\MapleStory.lnk")  # or wherever your game's shortcut is
   $sc.TargetPath; $sc.Arguments  # sanity check: launcher exe, e.g. nxl://launch/10100

   $action = New-ScheduledTaskAction -Execute $sc.TargetPath -Argument $sc.Arguments
   $principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
   Register-ScheduledTask -TaskName "MesoMarketCollector_MapleStoryViaLauncher" -Action $action -Principal $principal -Trigger $trigger -Force
   ```
   The action is built straight from the shortcut (`$sc`), so there's
   nothing to fill in by hand. If the sanity-check line prints nothing, the
   shortcut path is wrong — `tools/find_shortcut_target.ps1` lists any
   Maple shortcuts on your desktop(s) along with their targets/arguments.
   Verify it works with
   `schtasks /run /tn "MesoMarketCollector_MapleStoryViaLauncher"` from a
   normal (non-admin) shell — it should go straight to the game's login
   screen with no prompt.

   If nothing opens, check the task's last result:
   ```powershell
   Get-ScheduledTaskInfo -TaskName "MesoMarketCollector_MapleStoryViaLauncher" | Select-Object LastRunTime, LastTaskResult
   ```
   `2147942402` (`0x80070002`, file not found) means the task's program
   path doesn't exist — e.g. it was registered with the wrong path, or the
   launcher moved. Fix the existing task in place (Administrator
   PowerShell, with `$sc` set as above) rather than re-registering:
   ```powershell
   Set-ScheduledTask -TaskName "MesoMarketCollector_MapleStoryViaLauncher" -Action (New-ScheduledTaskAction -Execute $sc.TargetPath -Argument $sc.Arguments)
   ```

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

5. **Template images.** The routine finds what to click, and confirms
   where it is, by matching template screenshots — see
   [`assets/templates/README.md`](assets/templates/README.md) for which
   ones are used and how to recapture them.

6. **Routine steps.** [`config/routine.json`](config/routine.json) holds
   the ordered cleanup → launch → login → navigate → record → close
   sequence, fully automated. Cleanup runs both close tasks first and waits
   for the processes to actually exit (`wait_for_process_exit`), so a
   leftover game/launcher — which the launch task's `nxl://` link would
   otherwise be handed to, and the likely cause of an occasional UAC
   prompt at launch — never carries into a run. (This also closes a
   launcher you opened yourself.) The launcher starts the game already
   signed in, so login is just a click on the Log In button, followed by
   Quick Move, Meso Market, and the Buy tab. The Log In click is a
   `click_until_image` step: if Quick Move hasn't appeared 20 seconds after
   a click, it clicks again (up to 3 times) — the game sometimes ignores a
   click while it's still getting ready. Each tab is confirmed by a
   `wait_for_image` checkpoint before recording, which prints what it's
   waiting for so you can finish a step by hand if a click ever misses. Any
   wait that times out saves a full screenshot to `data/snapshots/`
   (`timeout_<template>_<timestamp>.png`) so an unattended failure can be
   diagnosed afterward. Edit it if the actual flow differs.

7. **Session task.** The collector itself has to run elevated (see
   "Simulated input in the game" below), so it gets a Scheduled Task too —
   then any normal shell (or a schedule) can start it without a UAC
   prompt. One-time setup, from an **Administrator** PowerShell in the
   repo root:
   ```powershell
   $repo = (Get-Location).Path
   $action = New-ScheduledTaskAction -Execute "cmd.exe" -WorkingDirectory $repo -Argument "/c `"`"$repo\.venv\Scripts\python.exe`" -u -m meso_market_collector.session --task-name MesoMarketCollector_MapleStoryViaLauncher >> data\session.log 2>&1`""
   $principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
   Register-ScheduledTask -TaskName "MesoMarketCollector_Session" -Action $action -Principal $principal -Trigger $trigger -Force
   ```
   The working directory matters — the default `--routine` path
   (`config/routine.json`) is relative to it. Output is appended to
   `data/session.log` rather than shown, since the task's console window
   closes as soon as the run ends (taking any error with it). To run it on
   a schedule, swap the `-Once` trigger for e.g.
   `New-ScheduledTaskTrigger -Daily -At 9am`.

### Simulated input in the game

Two things have to be true for simulated clicks/keys to register in the
game client (confirmed in both MapleStory and Terraria):

- **Every click/key is held, not tapped.** Games poll input state once per
  frame; PyAutoGUI's `click()`/`press()` send down and up back to back, so
  the whole press falls between two polls and is never seen (mouse
  *movement* still registers, being continuous — which is what made this
  look like the game was filtering input). `ScreenActions` holds each
  press for `hold_seconds` (default 50 ms) instead.
- **The collector runs elevated** (MapleStory only). The game runs elevated
  via the launch task, and Windows silently drops input sent to an
  elevated window from a non-elevated process. `session.py` prints a
  warning at startup if it isn't elevated.

### Why a Scheduled Task, not a direct launch/close?

Several things ruled out the simpler options, for both launching and
closing:
- Launching the game's exe directly (even elevated, even with the
  `__COMPAT_LAYER=RunAsInvoker` environment variable set) still triggered a
  UAC prompt with no way found to suppress it — the launcher requests
  elevation for it explicitly, which overrides both approaches.

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
launcher's own UI (e.g. its Play button) responds fine to simulated
clicks. The reason: the launcher is a multi-process
Electron-style app, and while its main window accepts clicks normally,
some of its background/helper processes run elevated (inherited from
being started by our elevated launch task) while others don't — a plain
`taskkill`/`Stop-Process` only ever gets the non-elevated ones, silently
leaving the rest running. So both "close" steps are process-kill tasks.

## Run the full session (launch game, log in, record both tabs, close)

From any shell, via the session task (Configure step 7):

```powershell
schtasks /run /tn "MesoMarketCollector_Session"
```

It runs start to finish unattended, appending its output to
`data/session.log`. If a click ever misses, the routine logs which screen
it's waiting for, and you have a few minutes to get there by hand for it
to continue.

To watch the output live instead (e.g. while debugging), run it directly
from an **Administrator** PowerShell (see "Simulated input in the game"
above) with the Windows Python venv:

```powershell
python -m meso_market_collector.session --task-name "MesoMarketCollector_MapleStoryViaLauncher"
```

The launch task name is passed in each run rather than stored in config. Recorded
prices are read via OCR
([`meso_market_collector/parser.py`](meso_market_collector/parser.py),
using [pytesseract](https://github.com/madmaze/pytesseract)) and appended
to `data/price_history.csv` as **one row per run**, matching the columns of
`data/template.csv` (a hand-maintained example of the desired shape):
`Date, Average, Buy Buyout 100M, Buy Buyout 1B, Buy Buyout 10B,
Sell Buyout 100M, Sell Buyout 1B, Sell Buyout 10B, Notes` (`Notes` is
always left blank for you to fill in by hand). `Average` comes from the
`meso_average` box, which reads identically regardless of which tab is
showing — confirmed empirically, not just assumed — so it's captured once
per row rather than separately for each tab. If OCR can't cleanly read a
box (blank, or anything that isn't purely digits), that cell is left
blank. Every box's raw crop is saved to `data/snapshots/` each run, named
with what OCR read (e.g. `Average_406_<timestamp>.png`, or
`..._unreadable_...`) — a misread digit (3 vs 6, say) still parses as a
valid number, so comparing a crop to its filename is the only way to
catch one. The same row is then POSTed to the sibling
[Meso-Market-Tracker](../Meso-Market-Tracker) project's GraphQL API
(`post_price_row` step, right after `save_price_row`, in
`config/routine.json`) — see
[`meso_market_collector/api_client.py`](meso_market_collector/api_client.py)
for the request built. It's sent to Tracker's deployed API Gateway endpoint
(`config.DEFAULT_TRACKER_API_URL`) by default — set `MESO_TRACKER_API_URL`
to override it (e.g. to point at a local `flask run` dev server instead).
Like any other step, a failed request (via `requests`' `raise_for_status()`)
stops
the routine there, skipping the cleanup steps after it — same as an OCR
`wait_for_image` timeout already could; the CSV row from `save_price_row`
is unaffected either way since it happens first. Snapshots older than 7
days get cleared
automatically each run (`clear_old_snapshots` step in
`config/routine.json`, by the timestamp embedded in each filename — not
file mtime, which a copy/backup could reset); adjust `max_age_days` there
if you want to keep them longer.

**OCR needs the actual Tesseract engine, not just the `pytesseract` pip
package** (`pytesseract` is a thin wrapper — pip alone doesn't install the
underlying OCR binary). On Windows: `winget install --id tesseract-ocr.tesseract -e`
(or install manually from
[UB-Mannheim's Tesseract builds](https://github.com/UB-Mannheim/tesseract/wiki)).
`parser.py` auto-detects the default install location
(`C:\Program Files\Tesseract-OCR\tesseract.exe`) if it's not on PATH yet
(common right after installing, until you open a fresh shell), so no
manual configuration is usually needed. If you installed somewhere else,
set it explicitly near the top of `parser.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\path\to\tesseract.exe"
```

## Run a bare capture pass (game already running, no launch/navigation)

```bash
python -m meso_market_collector.collect
```

Captures every region in `config/regions.json` once and appends a flat,
one-row-per-box reading to `data/region_readings.csv` (a different, simpler
format from `price_history.csv` above — this entrypoint is generic across
arbitrary regions, with no sell/buy-tab concept to build a combined row
from) — useful for a cron job when the game/market screen is already open:

```cron
* * * * * cd /path/to/Meso-Market-Collector && .venv/bin/python -m meso_market_collector.collect >> data/collector.log 2>&1
```

## Test

```bash
pytest
```

The launch/login/navigate routine (`meso_market_collector/routine.py`) is
unit-tested with a fake screen backend — no display needed. The real screen
I/O (`screen_actions.py`, `capture.py`) needs an actual display/game and
isn't covered by automated tests.
