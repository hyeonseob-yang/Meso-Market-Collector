# Working in this repo

## Test-driven development

Use test-driven development for every change to Python behaviour (docs,
comments, and tuning values in `config/*.json` don't need a test first —
though a change to `config/routine.json`'s step order does, see below):

1. **Write a failing test first** that describes the behaviour you're about
   to add or the bug you're about to fix.
2. **Run it and confirm it fails** — and fails for the expected reason, not
   an import error or typo. A test that has never failed proves nothing.
3. **Write the smallest change that makes it pass**, then run the full
   suite.
4. **Refactor** with the suite green.

For a bug, the failing test should reproduce the bug as it was observed
(e.g. a crop that OCR'd 427 as 42), so the fix is shown to address it.

Run the tests with the project venv:

```
.\.venv\Scripts\python.exe -m pytest      # PowerShell
./.venv/Scripts/python.exe -m pytest      # Git Bash
```

## Where tests go

- Pure logic (`config.py`, `storage.py`, `parser.py`'s text/plausibility
  functions, `routine.py` dispatch, `api_client.py`) — test directly.
- `screen_actions.py` — test with fakes swapped in for `pyautogui`,
  `pygetwindow` and `time` (see `tests/test_screen_actions.py`); the file
  skips itself where no display is available.
- `config/routine.json` ordering — guarded by tests that load the real file
  (see `tests/test_routine.py`).
- Things that only show up against the real game (template matching,
  OCR accuracy, window focus) can't be unit-tested: still write the tests
  that *can* be written first, then verify the rest with a real session
  run, and say which parts were verified live rather than by tests.
