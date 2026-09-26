"""Print the mouse position every second so you can find region coordinates.

Move the mouse to a corner of the price display in the game and read off
the (x, y) printed here. Run twice per region (top-left, then bottom-right)
to work out left/top/width/height for config/regions.local.json (or
config/regions.json, if you're changing the shared default).

Usage: python -m tools.find_coords
"""
import time

import pyautogui

if __name__ == "__main__":
    print("Move the mouse over the point you want the coordinates of.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\r x={x:5d} y={y:5d}", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()
