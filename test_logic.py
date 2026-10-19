"""Pytest suite for logic.py — mirrors the acceptance cases in SPEC.md §6."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from logic import (
    CATALOG,
    CellStatus,
    CityRecord,
    build_grid,
    clock_badge,
    format_window,
    local_time,
    offset_label,
    overlap_windows,
    total_overlap_hours,
)

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
LONDON = CityRecord("London", "Europe/London")
BALI = CityRecord("Bali", "Asia/Makassar")
HONOLULU = CityRecord("Honolulu", "Pacific/Honolulu")


def cells_by_hour(grid):
    return {c.hour: c.status for c in grid.cells}


def test_offsets_at_fixed_instant():
    assert offset_label(local_time(NOW, LONDON.tz)) == "UTC+1"
    assert offset_label(local_time(NOW, BALI.tz)) == "UTC+8"


def test_clock_badge():
    assert clock_badge(NOW, BALI.tz) == "\u2191 Tuesday \u00b7 UTC+8"
    assert clock_badge(NOW, LONDON.tz) == "\u2191 Tuesday \u00b7 UTC+1"


def test_green_cells():
    grids = build_grid(NOW, [LONDON, BALI])
    assert len(grids) == 2
    london, bali = grids
    assert len(london.cells) == 24
    assert london.local_date == date(2026, 10, 13)
    assert bali.local_date == date(2026, 10, 13)

    lon = cells_by_hour(london)
    assert lon[9] is CellStatus.OVERLAP
    assert lon[10] is CellStatus.WORKING
    assert lon[16] is CellStatus.WORKING
    assert lon[17] is CellStatus.OUTSIDE
    assert lon[3] is CellStatus.OUTSIDE

    bali_hours = cells_by_hour(bali)
    assert bali_hours[16] is CellStatus.OVERLAP
    assert bali_hours[15] is CellStatus.WORKING
    assert bali_hours[9] is CellStatus.WORKING
    assert bali_hours[8] is CellStatus.OUTSIDE
    assert bali_hours[20] is CellStatus.OUTSIDE


def test_local_dates_can_differ():
    dt = datetime(2026, 10, 13, 20, 30, tzinfo=timezone.utc)
    grids = build_grid(dt, [LONDON, BALI])
    assert grids[0].local_date == date(2026, 10, 13)
    assert grids[1].local_date == date(2026, 10, 14)


def test_total_overlap_next_7_days():
    assert total_overlap_hours(NOW, [LONDON, BALI]) == 5.0


def test_zero_overlap():
    cities = [LONDON, HONOLULU]
    assert total_overlap_hours(NOW, cities) == 0.0
    assert overlap_windows(NOW, cities) == []


def test_zero_overlap_tokyo_london():
    tokyo = CityRecord("Tokyo", "Asia/Tokyo")
    cities = [tokyo, LONDON]
    assert total_overlap_hours(NOW, cities) == 0.0
    assert overlap_windows(NOW, cities) == []


def test_single_city():
    windows = overlap_windows(NOW, [LONDON])
    assert total_overlap_hours(NOW, [LONDON]) == 40.0
    assert len(windows) == 5
    assert format_window(windows[0]) == (
        "Tue 13 Oct \u2014 London 09:00\u201317:00 \u00b7 08:00\u201316:00 UTC"
    )


def test_no_selection():
    assert total_overlap_hours(NOW, []) == 0.0
    assert overlap_windows(NOW, []) == []
    assert build_grid(NOW, []) == []


def test_window_list():
    windows = overlap_windows(NOW, [LONDON, BALI])
    assert len(windows) == 5
    first = windows[0]
    assert first.start_utc == datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)
    assert first.end_utc == datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)
    assert first.local_ranges == {"London": "09:00\u201310:00", "Bali": "16:00\u201317:00"}
    assert format_window(first) == (
        "Tue 13 Oct \u2014 London 09:00\u201310:00 \u00b7 Bali 16:00\u201317:00 "
        "\u00b7 08:00\u201309:00 UTC"
    )
    last = windows[-1]
    assert last.start_utc == datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
    assert last.start_utc.strftime("%A") == "Monday"


@pytest.mark.parametrize(
    "cities",
    [[LONDON, BALI], [LONDON], [LONDON, HONOLULU]],
)
def test_sum_of_windows_equals_metric(cities):
    windows = overlap_windows(NOW, cities)
    total = sum((w.end_utc - w.start_utc).total_seconds() for w in windows) / 3600
    assert total == total_overlap_hours(NOW, cities)


def test_dst_transition():
    before = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
    after = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    assert offset_label(local_time(before, LONDON.tz)) == "UTC+1"
    assert offset_label(local_time(after, LONDON.tz)) == "UTC+0"
    assert clock_badge(after, LONDON.tz) == "\u2191 Sunday \u00b7 UTC+0"
    grid = build_grid(after, [LONDON, BALI])[0]
    assert len(grid.cells) == 24


def test_weekends_render_but_not_counted():
    saturday = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    cities = [LONDON, BALI]
    assert total_overlap_hours(saturday, cities) == 5.0
    windows = overlap_windows(saturday, cities)
    assert all(w.start_utc.weekday() < 5 for w in windows)
    grid = build_grid(saturday, cities)[0]
    assert grid.local_date == date(2026, 10, 17)
    assert cells_by_hour(grid)[9] is CellStatus.OVERLAP


def test_catalog_has_36_cities():
    assert len(CATALOG) == 36
    names = [c.name for c in CATALOG]
    assert len(set(names)) == 36
    for city in CATALOG:
        ZoneInfo(city.tz)
