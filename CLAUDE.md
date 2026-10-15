# Working in this repo

## Test-driven development

Use test-driven development for every change to Python behaviour. Docs,
comments and tuning values in `config/*.json` don't need a test first, but a
change to `config/routine.json`'s step order does (see below).

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
  `pygetwindow` and `time` (see `tests/test_screen_actions.py`).
  `session.py` — test with `ScreenActions` and the routine faked (see
  `tests/test_session.py`). Both test files skip themselves where no display
  is available.
- `config/routine.json` ordering — guarded by tests that load the real file
  (see `tests/test_routine.py`).
- Things that only show up against the real game (template matching,
  OCR accuracy, window focus) can't be unit-tested: still write the tests
  that *can* be written first, then verify the rest with a real session
  run, and say which parts were verified live rather than by tests.

To verify live, start a run with `schtasks /run /tn "MesoMarketCollector_Session"`
and check the end of `data/session.log` and the new files in
`data/snapshots/`. Scheduled collection runs on a separate machine, so a run
on a development machine is a manual test.

## Comments

Keep comments and docstrings minimal: at most a line or two giving a reason
the code doesn't show, and none where the code is self-explanatory. Put the
history of a change — what was tried, what went wrong — in the commit
message, not the code. The exception is a usage header at the top of a
standalone tool (see `tools/find_coords.py`): what it does, when to use it,
and the exact command.
