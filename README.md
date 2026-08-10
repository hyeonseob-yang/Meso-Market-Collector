# Meso Market Collector

Automates recording in-game market price changes by taking screenshots of a
configured screen region and appending each reading to a CSV, using
[PyAutoGUI](https://pyautogui.readthedocs.io/) for screen capture and
[Pillow](https://pillow.readthedocs.io/) for image handling.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Must be run from a session with real screen/GUI access (i.e. the machine
actually displaying the game) — it will not work from a headless shell.

## Configure the region to watch

1. With the game window in place, find the pixel coordinates of the price
   display:
   ```bash
   python -m tools.find_coords
   ```
2. Edit [`config/regions.json`](config/regions.json) with the box for each
   item you want to track:
   ```json
   {
     "meso_price": { "left": 100, "top": 200, "width": 150, "height": 30 }
   }
   ```

## Run once

```bash
python -m meso_market_collector.collect
```

Each run captures every configured region and appends a row to
`data/price_history.csv` (created on first run). Price parsing (turning the
screenshot into a number) isn't implemented yet — see the note in
[`meso_market_collector/parser.py`](meso_market_collector/parser.py) for
options (OCR via pytesseract, template matching, etc). Until then, each run
also saves the raw crop to `data/snapshots/` so no data is lost.

## Run on a schedule (cron)

```cron
* * * * * cd /home/hya81/Meso-Market-Collector && .venv/bin/python -m meso_market_collector.collect >> data/collector.log 2>&1
```

## Test

```bash
pytest
```
