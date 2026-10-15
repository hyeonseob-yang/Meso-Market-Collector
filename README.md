# Meso Market Collector

Records MapleStory's Meso Market prices automatically. Each run launches the
game, logs in, opens the Meso Market, reads the Average price and the
100M / 1B / 10B Buy and Sell prices off the screen with OCR, saves them as
one row, posts the row to
[Meso-Market-Tracker](../Meso-Market-Tracker), and closes the game. Run on
an hourly schedule, it builds a price history for analysis.

## Requirements

- Windows, with MapleStory installed through the Nexon launcher and the
  launcher signed in (the game then needs only a Log In click).
- Python 3.10+.
- The [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) OCR engine:
  `winget install --id tesseract-ocr.tesseract -e`. The default install
  location is found automatically.

## Install

```powershell
git clone https://github.com/hyeonseob-yang/Meso-Market-Collector.git
cd Meso-Market-Collector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

If activation fails with an execution-policy error, run
`Set-ExecutionPolicy -Scope Process RemoteSigned` and retry.

## Setup

Do these once per machine.

### 1. Scheduled tasks

The game runs elevated, so launching it, closing it, and running the
collector all go through Scheduled Tasks that run elevated without a UAC
prompt. Open an **Administrator** PowerShell and `cd` to this repo's
folder first — an admin shell starts in `C:\Windows\System32`. Then paste
the whole block:

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw "Not in the repo folder - cd there first, then paste this again" }

$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)

# Launch the game, using your MapleStory desktop shortcut's target
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:USERPROFILE\Desktop\MapleStory.lnk")
$sc.TargetPath; $sc.Arguments   # should print the launcher exe and e.g. nxl://launch/10100
$action = New-ScheduledTaskAction -Execute $sc.TargetPath -Argument $sc.Arguments
Register-ScheduledTask -TaskName "MesoMarketCollector_MapleStoryViaLauncher" -Action $action -Principal $principal -Trigger $trigger -Force

# Close the game
$action = New-ScheduledTaskAction -Execute "taskkill.exe" -Argument "/F /IM MapleStory.exe"
Register-ScheduledTask -TaskName "MesoMarketCollector_KillMapleStory" -Action $action -Principal $principal -Trigger $trigger -Force

# Close the launcher
$action = New-ScheduledTaskAction -Execute "taskkill.exe" -Argument "/F /IM nexon_client.exe"
Register-ScheduledTask -TaskName "MesoMarketCollector_KillNexonLauncher" -Action $action -Principal $principal -Trigger $trigger -Force

# Run the collector, logging to data\session.log
$repo = (Get-Location).Path
$action = New-ScheduledTaskAction -Execute "cmd.exe" -WorkingDirectory $repo -Argument "/c `"(if not exist data mkdir data) & `"$repo\.venv\Scripts\python.exe`" -u -m meso_market_collector.session --task-name MesoMarketCollector_MapleStoryViaLauncher >> data\session.log 2>&1`""
Register-ScheduledTask -TaskName "MesoMarketCollector_Session" -Action $action -Principal $principal -Trigger $trigger -Force
```

If the shortcut line prints nothing, your shortcut is somewhere else (for
example, OneDrive moves the desktop to `OneDrive\Desktop`). Right-click the
MapleStory shortcut → **Properties** → **Open File Location** to see its
full path, put that path in place of
`$env:USERPROFILE\Desktop\MapleStory.lnk`, and paste the block again.

Check the launch task from a normal shell: it should open the game's login
screen with no prompt.

```powershell
schtasks /run /tn "MesoMarketCollector_MapleStoryViaLauncher"
```

### 2. Screen regions and templates

The committed coordinates and template images match one specific display.
On a machine with a different resolution or scaling, make local copies
(both are gitignored and used in place of the committed ones):

- **Price boxes:** copy `config/regions.json` to
  `config/regions.local.json`. With the Meso Market open, run
  `python -m tools.find_coords` to read pixel coordinates, and edit the
  copy. `tops` lists the top edge of the Average, 100M, 1B and 10B boxes.
- **Template images:** put recaptured images in `assets/templates.local/`
  under the same filenames. See
  [assets/templates/README.md](assets/templates/README.md) for what each
  one shows.

### 3. Tracker secret

Posting to Tracker needs its shared secret. Create a `.env` file in the
repo root (gitignored — never commit it):

```
MESO_TRACKER_RECORD_PRICE_SECRET=your-secret-here
```

`MESO_TRACKER_API_URL` can be set the same way to post somewhere other than
the deployed Tracker.

### 4. Hourly schedule (optional)

From an **Administrator** PowerShell:

```powershell
$start = (Get-Date).Date.AddHours((Get-Date).Hour + 1)   # next full hour
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Hours 1)
Set-ScheduledTask -TaskName "MesoMarketCollector_Session" -Trigger $trigger
```

A scheduled run:

- takes over the screen for a few minutes — the game must stay the front
  window;
- closes MapleStory and the Nexon launcher at the start and end, including
  a game you're playing;
- needs you logged in with the screen unlocked;
- doesn't start on battery power, and doesn't make up a missed hour.

To go back to manual runs:

```powershell
Set-ScheduledTask -TaskName "MesoMarketCollector_Session" -Trigger (New-ScheduledTaskTrigger -Once -At (Get-Date))
```

### 5. Running with the laptop lid closed (optional)

With the lid closed there's no display to capture, so add a virtual one:

1. `winget install --id VirtualDrivers.Virtual-Display-Driver -e`, then run
   **VDD Control** as administrator and click **Install Driver**.
2. In Settings → System → Display, set the displays to **Extend**, keep the
   laptop screen as the main display, and give the virtual display the same
   resolution and scale as the laptop screen.
3. In Control Panel → Power Options, set the lid close action to
   **Do nothing** when plugged in.

Uninstall the driver before a major graphics driver update and reinstall it
after.

## Run

Start a run from any shell:

```powershell
schtasks /run /tn "MesoMarketCollector_Session"
```

It runs unattended and appends its output to `data/session.log`.

To watch the output live, or to mark a run as manual, run it directly from
an **Administrator** PowerShell:

```powershell
python -m meso_market_collector.session --task-name "MesoMarketCollector_MapleStoryViaLauncher" --notes manual
```

`--notes` is optional; its text is saved in the row's Notes. Scheduled runs
leave Notes blank.

## Output

- **`data/price_history.csv`** — one row per run, with the same column
  names as Tracker: `datetime` (collection time, UTC), `average`,
  `buy100M`, `buy1B`, `buy10B`, `sell100M`, `sell1B`, `sell10B`, `notes`.
- **Tracker** — the same row.
- **`data/snapshots/`** — the image of every price box, named with the
  value OCR read (e.g. `average_406_<timestamp>.png`), for checking a
  reading. Deleted after 7 days (`max_age_days` in `config/routine.json`).
  The full-screen `timeout_…png` screenshots saved when a run fails are
  kept for 90 days (`failure_max_age_days`), so a rare failure, such as on
  a patch day, can still be examined later.
- **`data/session.log`** — the log of every run started through the
  session task.

A price that doesn't fit the rest of its row (e.g. 427 read as 42) is still
recorded, with `Possible OCR misread: …` in `notes`.

## Troubleshooting

- **A run failed.** The error is at the end of `data/session.log`. If a
  screen check timed out, `data/snapshots/timeout_<template>_<timestamp>.png`
  shows the screen at that moment. The game stays open until the next run
  closes it; that run first logs what was still open and saves
  `timeout_leftover_<timestamp>.png`.
- **A screen check keeps timing out.** The template image no longer matches
  (display change or game update): recapture it into
  `assets/templates.local/`.
- **Prices are misread.** Open the box's snapshot; if digits touch an edge
  or part of another box is included, adjust `config/regions.local.json`.
- **Nothing opens when the launch task runs.**
  `Get-ScheduledTaskInfo -TaskName "MesoMarketCollector_MapleStoryViaLauncher"`
  showing `LastTaskResult` `2147942402` means the task's program path is
  wrong; re-register it from step 1.
- **Clicks don't register.** The collector isn't running elevated (the log
  says so at startup): start it through the session task or an
  Administrator PowerShell.
- **Tracker rejects the row.** Check the secret in `.env`. If Tracker
  answers with an id of `None` and returns no prices, its database is
  paused.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The steps of a run are listed in `config/routine.json`. See
[CLAUDE.md](CLAUDE.md) for how changes are tested.
