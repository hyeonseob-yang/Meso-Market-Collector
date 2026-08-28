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

2. **Portability across resolutions.** `find_coords.py` also prints the
   current screen resolution — record it as `reference_resolution` in
   `config/regions.json`:
   ```json
   {
     "reference_resolution": { "width": 2560, "height": 1440 },
     "meso": { "left": 1090, "width": 130, "height": 45, "tops": [300, 395, 470, 545] }
   }
   ```
   With that present, `screen_actions.py` proportionally scales every region
   to whatever resolution is actually running (via `config.scale_regions`)
   instead of using the literal calibrated pixels. **Caveat:** this assumes
   MapleStory's UI positions scale linearly with resolution; if it instead
   anchors elements a fixed pixel offset from an edge, proportional scaling
   will compute the wrong position at a different resolution. Verify by
   calibrating (or at least spot-checking one box) at a second resolution
   before relying on this for a resolution other than the one you
   calibrated at. Omit `reference_resolution` entirely to skip scaling and
   use the literal pixel values as before.

3. **Template images.** The routine finds buttons (Play, Log In, Quick
   Move, etc.) by matching small reference screenshots. See
   [`assets/templates/README.md`](assets/templates/README.md) for exactly
   which crops to capture and their required filenames. Note: unlike the
   region boxes above, templates are **not** scaled for a different
   resolution — a button screenshot captured at one resolution generally
   won't pixel-match the same button rendered at another size. Someone
   running at a different resolution than `reference_resolution` would
   still need to recapture these.

4. **Routine steps.** [`config/routine.json`](config/routine.json) holds
   the ordered launch → login → navigate → record → close sequence. Edit it
   if the actual click order differs.

## Run the full session (launch game, log in, record both tabs, close)

From the Windows Python venv set up above:

```powershell
python -m meso_market_collector.session --launcher-path "C:\Games\Launcher.exe"
```

The launcher path is passed in each run rather than stored in config.
Recorded prices are appended to `data/price_history.csv`. Price parsing
(turning a screenshot into a number) isn't implemented yet — see the note in
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
