# AGENTS.md

## Repo state

- **`SPEC.md` is the authority** for behavior, data structures, and acceptance cases — read it before changing anything.
- Layout: `logic.py` (pure core, no Streamlit import) · `test_logic.py` (pytest suite) · `app.py` (Streamlit UI) · `requirements.txt`.
- Windows + Python 3.11.9 venv at `.venv/`. Run: `.venv\Scripts\python.exe -m pytest` (single test: append `test_logic.py::test_name`); app: `.venv\Scripts\python.exe -m streamlit run app.py`.

## Gotchas

- **`tzdata` is required on Windows** — `zoneinfo` has no OS tz database; keep `tzdata` in `requirements.txt` or all tz lookups fail.
- Logic must accept an **injected reference time**; never call `datetime.now()` inside `logic.py` (tests depend on fixed instants like `2026-10-13T12:00Z`).
- Overlap is computed on **UTC hour blocks**; a block counts only if every city stays in 09:00–17:00 local for the *entire* block. Time-of-day-only comparisons break on midnight wrap (past bug).
- **Weekday rule**: the 7-day metric and window list count Mon–Fri only (reproduces the mockup's `5.0 h` for London+Bali); weekend cells still render green in the grid.
- Non-ASCII output is intentional: en dash `–` in time ranges, em dash `—` in labels, `↑` in clock badges.
