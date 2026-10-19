# SPEC.md — Borderless Meeting Planner

## 1. Overview

A Streamlit app that helps users find a time window where **every selected city is inside
working hours (09:00–17:00 local time)**. The user picks cities from a fixed catalog of 36,
sees the current local time in each city, a 24-hour per-city grid showing which hours are
working / overlapping / outside, and the concrete overlap windows for the next 7 days.

Core logic lives in `logic.py` (pure functions, no Streamlit import) so it is unit-testable
with `pytest` (`test_logic.py`).

## 2. UI layout (follows the image template)

### Sidebar — "Cities"
- Multi-select with removable chips (e.g. `London ✕` `Bali ✕`).
- Counter line: `2 of 36 cities selected` (N of 36).

### Header
- Title: **Borderless Meeting Planner**
- Subtitle: `Find a window where every city is inside 09:00–17:00 local time.`

### Metrics (two columns)
- **Cities** — number of selected cities.
- **Overlapping hours (next 7 days)** — total hours where all cities are simultaneously in
  working hours, displayed with one decimal, e.g. `5.0 h`.

### Local clocks (one card per selected city)
- Big clock `HH:MM:SS` in the city's local time.
- Badge below: `↑ Monday · UTC+1` → `↑ {Weekday} · {UTC offset label}`.
- Each clock shows that city's own current local date (cities may disagree on the date).

### 24-hour local view
- Legend: `Working hours` (blue) · `Overlapping hours` (green) · `Outside working hours` (gray).
- One row per city, header: `London — Tue 2026-10-13 local · green = overlap`
  (city name, that city's local date, em-dash separators).
- 24 cells labeled `00`–`23`:
  - **green** = every selected city is in working hours during that local hour;
  - **blue** = this city is in working hours, but not all cities are;
  - **gray** = outside this city's working hours.

### Overlap windows (from requirements text; not in the image)
- List of concrete windows, e.g.
  `Tue 13 Oct — London 09:00–10:00 · Bali 16:00–17:00 · 08:00–09:00 UTC`
- One entry per contiguous run of overlapping hours; grouped per UTC day (never spans midnight).
- Sum of all listed windows **equals** the "Overlapping hours" metric.

## 3. Features

- **F1 City selection** — choose from a fixed catalog of exactly 36 cities (name + IANA tz).
  Chips and `N of 36` counter. Empty selection is allowed and shows zeros/empties.
- **F2 Local clocks** — per city: local `HH:MM:SS`, badge `↑ {Weekday} · {UTC±N}`.
  Offsets rendered as `UTC+1`, `UTC+8`, `UTC+0`, `UTC-5`, `UTC+5:30` (minutes only when nonzero).
- **F3 Metrics** — city count; total overlapping hours over the next 7 days (one decimal).
- **F4 24-hour local view** — per-city grid of 24 cells with the three statuses above; green
  cells are derived from all-cities overlap, not from this city alone.
- **F5 Overlap windows** — concrete per-city local ranges plus the UTC range for each window.
- **F6 Edge cases** — 0 cities → `0.0 h`, empty grids/windows; 1 city → its own working hours
  are fully "overlapping" (e.g. London alone = 40.0 h/weekdays); a pair with disjoint working
  hours → `0.0 h`, an empty window list, and the app shows a warning:
  `No overlapping hours in the next 7 days for these cities.` (example: Tokyo + London).
- **F7 DST correctness** — all conversions via IANA zones (`zoneinfo`); the London badge must
  flip from `UTC+1` to `UTC+0` on 2026-10-25 (BST → GMT), and grids must build on DST days.

## 4. Data structures

```python
WORK_START = 9          # local hour, inclusive
WORK_END = 17           # local hour, exclusive
WINDOW_DAYS = 7         # "next 7 days"

class CellStatus(Enum):        # OUTSIDE | WORKING | OVERLAP

@dataclass(frozen=True)
class CityRecord:               # name: str, tz: str (IANA)
CATALOG: tuple[CityRecord, ...] # exactly 36 entries, unique names, valid IANA zones

@dataclass(frozen=True)
class Cell:                     # hour: int 0..23, status: CellStatus

@dataclass(frozen=True)
class DayGrid:                  # city: str, local_date: date, cells: 24 × Cell

@dataclass(frozen=True)
class OverlapWindow:            # start_utc, end_utc: datetime (tz-aware, UTC),
                                # local_ranges: dict[city_name, "HH:MM–HH:MM"]
```

Public functions in `logic.py` (all take an injectable reference time `dt` so tests are
deterministic; no call to `datetime.now()` inside pure logic):

- `offset_label(dt) -> str`
- `local_time(dt, tz) -> datetime`
- `clock_badge(dt, tz) -> str`
- `build_grid(dt, cities) -> list[DayGrid]`
- `total_overlap_hours(dt, cities) -> float`
- `overlap_windows(dt, cities) -> list[OverlapWindow]`
- `format_window(window) -> str`

## 5. Time & overlap rules

- Timezone math uses `zoneinfo.ZoneInfo` (Python 3.11; `tzdata` package required on Windows).
- Work in UTC hour blocks `[t, t+1h)`. A block counts as **overlapping** iff every selected
  city's local time stays within `09:00–17:00` for the **entire** block.
- A grid cell for city C, local hour `h` (start instant `t`):
  - `OUTSIDE` if C itself is not working through `[t, t+1h)`;
  - `OVERLAP` if all selected cities are working through `[t, t+1h)`;
  - `WORKING` otherwise.
- **Next 7 days** = 7 whole UTC calendar days starting with the UTC date of the reference
  time (today through +6).
- **Weekday rule (reproduces the image's `5.0 h`)**: only Mon–Fri contribute to the metric
  and the window list. Weekend hours can still render green in the grid (they are just not
  counted). London 09:00 ↔ Bali 16:00 overlap is 1 h/day → 5 weekdays → `5.0 h`.
- Grid rows use each city's **own local date** of the reference time.

## 6. Acceptance criteria (example test cases)

Reference instant for most tests: `NOW = 2026-10-13T12:00:00Z` (Tuesday; London `UTC+1`,
Bali `UTC+8`, Honolulu `UTC-10`).

1. **`test_offsets_at_fixed_instant`** — Given `NOW` and cities London/Bali, when offsets are
   computed → `offset_label(local_time(NOW, "Europe/London")) == "UTC+1"` and
   `offset_label(local_time(NOW, "Asia/Makassar")) == "UTC+8"`.
2. **`test_clock_badge`** — Given `NOW`, when the Bali badge is rendered →
   `"↑ Tuesday · UTC+8"`.
3. **`test_green_cells`** — Given `NOW` and London+Bali, when `build_grid` runs →
   London cells: `09 = OVERLAP`, `10 = WORKING`, `16 = WORKING`, `17 = OUTSIDE`,
   `03 = OUTSIDE`; Bali cells: `16 = OVERLAP`, `15 = WORKING`, `09 = WORKING`,
   `08 = OUTSIDE`; grid has 24 cells per city and both rows are dated `2026-10-13`.
4. **`test_local_dates_can_differ`** — Given `2026-10-13T20:30:00Z`, London's grid date is
   `2026-10-13` while Bali's is `2026-10-14`.
5. **`test_total_overlap_next_7_days`** — Given `NOW` and London+Bali →
   `total_overlap_hours == 5.0`.
6. **`test_zero_overlap`** — Given `NOW` and London+Honolulu (disjoint working hours) →
   `total_overlap_hours == 0.0` and `overlap_windows == []`.
7. **`test_single_city`** — Given `NOW` and London alone → `total_overlap_hours == 40.0`
   (8 h × 5 weekdays), one window per weekday, first formatted as
   `"Tue 13 Oct — London 09:00–17:00 · 08:00–16:00 UTC"`.
8. **`test_no_selection`** — Given an empty city list → `0.0` hours, `[]` windows, `[]` grids.
9. **`test_window_list`** — Given `NOW` and London+Bali → 5 windows (Tue–Fri + Mon); first
   window: `start_utc = 2026-10-13T08:00Z`, `end_utc = 09:00Z`,
   `local_ranges == {"London": "09:00–10:00", "Bali": "16:00–17:00"}`, and
   `format_window == "Tue 13 Oct — London 09:00–10:00 · Bali 16:00–17:00 · 08:00–09:00 UTC"`
   (en-dash in ranges, em-dash after the date).
10. **`test_sum_of_windows_equals_metric`** — Sum of all window durations equals
    `total_overlap_hours` for London+Bali, London alone, and the zero-overlap pair.
11. **`test_dst_transition`** — Given `2026-10-24T12:00Z` → London `UTC+1`; given
    `2026-10-25T12:00Z` (BST→GMT day) → London `UTC+0` and badge `"↑ Sunday · UTC+0"`;
    `build_grid` on that day still returns 24 cells without raising.
12. **`test_weekends_render_but_not_counted`** — Given Saturday `2026-10-17T12:00Z`,
    London+Bali total is still `5.0` (Mon–Fri of that window) while London's cell `09` is
    `OVERLAP` (weekend cell renders green).
13. **`test_catalog_has_36_cities`** — `len(CATALOG) == 36`, names unique, every `tz` loads
    via `ZoneInfo`.
14. **`test_warning_when_no_overlap_tokyo_london`** (`test_app.py`, via `AppTest`) — Given
    Tokyo + London selected → metric shows `0.0 h` and exactly one `st.warning` containing
    `"No overlapping hours"`; with the default London + Bali there is no warning.

## 7. Project layout & commands

```
SPEC.md            # this file
AGENTS.md          # agent instructions
logic.py           # pure core logic (no Streamlit)
test_logic.py      # pytest suite for logic.py
app.py             # Streamlit UI (future)
requirements.txt
```

- Run all tests: `.venv\Scripts\python.exe -m pytest`
- Single test: `.venv\Scripts\python.exe -m pytest test_logic.py::test_window_list`
- Run the app (once `app.py` exists): `.venv\Scripts\python.exe -m streamlit run app.py`
