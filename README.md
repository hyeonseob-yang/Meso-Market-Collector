# Meso Market Collector

Automates recording in-game Meso market price changes: launches the game,
logs in, navigates to the Meso Market, and reads the Sell/Buy price boxes —
using [PyAutoGUI](https://pyautogui.readthedocs.io/) for screen capture and
UI automation and [Pillow](https://pillow.readthedocs.io/) for image
handling.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Must be run from a session with real screen/GUI access (i.e. the machine
actually displaying the game) — it will not work from a headless shell.

## Configure

1. **Region boxes.** With the game window in place, find the pixel
   coordinates of each price box:
   ```bash
   python -m tools.find_coords
   ```
   Edit [`config/regions.json`](config/regions.json) — placeholders are
   already there for `sell_meso_1..4` and `buy_meso_1..4` (assumes 4 boxes
   per tab; add/remove entries if the real layout differs).

2. **Template images.** The routine finds buttons (Play, Log In, Quick
   Move, etc.) by matching small reference screenshots. See
   [`assets/templates/README.md`](assets/templates/README.md) for exactly
   which crops to capture and their required filenames.

3. **Routine steps.** [`config/routine.json`](config/routine.json) holds
   the ordered launch → login → navigate → record → close sequence. Edit it
   if the actual click order differs.

## Run the full session (launch game, log in, record both tabs, close)

```bash
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
