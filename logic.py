"""Core logic for the Borderless Meeting Planner.

Pure functions: every entrypoint takes an injectable reference time ``dt``
(tz-aware) instead of reading a clock, so tests are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

WORK_START = 9
WORK_END = 17
WINDOW_DAYS = 7


@dataclass(frozen=True)
class CityRecord:
    name: str
    tz: str


CATALOG: tuple[CityRecord, ...] = (
    CityRecord("London", "Europe/London"),
    CityRecord("Bali", "Asia/Makassar"),
    CityRecord("New York", "America/New_York"),
    CityRecord("Los Angeles", "America/Los_Angeles"),
    CityRecord("Chicago", "America/Chicago"),
    CityRecord("Toronto", "America/Toronto"),
    CityRecord("Mexico City", "America/Mexico_City"),
    CityRecord("São Paulo", "America/Sao_Paulo"),
    CityRecord("Buenos Aires", "America/Argentina/Buenos_Aires"),
    CityRecord("Bogotá", "America/Bogota"),
    CityRecord("Lima", "America/Lima"),
    CityRecord("Reykjavik", "Atlantic/Reykjavik"),
    CityRecord("Lisbon", "Europe/Lisbon"),
    CityRecord("Madrid", "Europe/Madrid"),
    CityRecord("Paris", "Europe/Paris"),
    CityRecord("Berlin", "Europe/Berlin"),
    CityRecord("Amsterdam", "Europe/Amsterdam"),
    CityRecord("Zurich", "Europe/Zurich"),
    CityRecord("Rome", "Europe/Rome"),
    CityRecord("Stockholm", "Europe/Stockholm"),
    CityRecord("Warsaw", "Europe/Warsaw"),
    CityRecord("Istanbul", "Europe/Istanbul"),
    CityRecord("Moscow", "Europe/Moscow"),
    CityRecord("Dubai", "Asia/Dubai"),
    CityRecord("Mumbai", "Asia/Kolkata"),
    CityRecord("Kathmandu", "Asia/Kathmandu"),
    CityRecord("Bangkok", "Asia/Bangkok"),
    CityRecord("Jakarta", "Asia/Jakarta"),
    CityRecord("Singapore", "Asia/Singapore"),
    CityRecord("Hong Kong", "Asia/Hong_Kong"),
    CityRecord("Shanghai", "Asia/Shanghai"),
    CityRecord("Tokyo", "Asia/Tokyo"),
    CityRecord("Seoul", "Asia/Seoul"),
    CityRecord("Sydney", "Australia/Sydney"),
    CityRecord("Auckland", "Pacific/Auckland"),
    CityRecord("Honolulu", "Pacific/Honolulu"),
)


class CellStatus(Enum):
    OUTSIDE = "outside"
    WORKING = "working"
    OVERLAP = "overlap"


@dataclass(frozen=True)
class Cell:
    hour: int
    status: CellStatus


@dataclass(frozen=True)
class DayGrid:
    city: str
    local_date: date
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class OverlapWindow:
    start_utc: datetime
    end_utc: datetime
    local_ranges: dict[str, str] = field(default_factory=dict)


def _as_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)


def local_time(dt: datetime, tz: str) -> datetime:
    return dt.astimezone(ZoneInfo(tz))


def offset_label(dt: datetime) -> str:
    total = int(dt.utcoffset().total_seconds())
    sign = "+" if total >= 0 else "-"
    minutes = abs(total) // 60
    hours, mins = divmod(minutes, 60)
    if mins:
        return f"UTC{sign}{hours}:{mins:02d}"
    return f"UTC{sign}{hours}"


def clock_badge(dt: datetime, tz: str) -> str:
    local = local_time(dt, tz)
    return f"\u2191 {local:%A} \u00b7 {offset_label(local)}"


def _block_within_working(start_utc: datetime, tz: str) -> bool:
    """True if local time stays inside [WORK_START:00, WORK_END:00) for the whole block."""
    end_utc = start_utc + timedelta(hours=1)
    zone = ZoneInfo(tz)
    local_start = start_utc.astimezone(zone)
    local_end = end_utc.astimezone(zone)
    work_open = local_start.replace(
        hour=WORK_START, minute=0, second=0, microsecond=0
    )
    work_close = local_start.replace(
        hour=WORK_END, minute=0, second=0, microsecond=0
    )
    return work_open <= local_start and local_end <= work_close


def _all_working(start_utc: datetime, cities: tuple[CityRecord, ...] | list[CityRecord]) -> bool:
    if not cities:
        return False
    return all(_block_within_working(start_utc, c.tz) for c in cities)


def _utc_days(dt: datetime) -> list[date]:
    day0 = _as_utc(dt).date()
    return [day0 + timedelta(days=i) for i in range(WINDOW_DAYS)]


def _iter_block_starts(day: date):
    base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    for hour in range(24):
        yield base + timedelta(hours=hour)


def build_grid(
    dt: datetime, cities: tuple[CityRecord, ...] | list[CityRecord]
) -> list[DayGrid]:
    grids: list[DayGrid] = []
    for city in cities:
        local_date = local_time(dt, city.tz).date()
        cells: list[Cell] = []
        for hour in range(24):
            start_local = datetime(
                local_date.year, local_date.month, local_date.day, hour, 0,
                tzinfo=ZoneInfo(city.tz),
            )
            start_utc = start_local.astimezone(timezone.utc)
            if not _block_within_working(start_utc, city.tz):
                status = CellStatus.OUTSIDE
            elif _all_working(start_utc, cities):
                status = CellStatus.OVERLAP
            else:
                status = CellStatus.WORKING
            cells.append(Cell(hour=hour, status=status))
        grids.append(
            DayGrid(city=city.name, local_date=local_date, cells=tuple(cells))
        )
    return grids


def total_overlap_hours(
    dt: datetime, cities: tuple[CityRecord, ...] | list[CityRecord]
) -> float:
    if not cities:
        return 0.0
    count = 0
    for day in _utc_days(dt):
        if day.weekday() >= 5:
            continue
        for start in _iter_block_starts(day):
            if _all_working(start, cities):
                count += 1
    return float(count)


def overlap_windows(
    dt: datetime, cities: tuple[CityRecord, ...] | list[CityRecord]
) -> list[OverlapWindow]:
    if not cities:
        return []
    windows: list[OverlapWindow] = []
    for day in _utc_days(dt):
        if day.weekday() >= 5:
            continue
        run_start: datetime | None = None
        run_end: datetime | None = None

        def close(run_start: datetime, run_end: datetime) -> OverlapWindow:
            local_ranges = {
                c.name: (
                    f"{run_start.astimezone(ZoneInfo(c.tz)):%H:%M}"
                    f"\u2013{run_end.astimezone(ZoneInfo(c.tz)):%H:%M}"
                )
                for c in cities
            }
            return OverlapWindow(run_start, run_end, local_ranges)

        for start in _iter_block_starts(day):
            if _all_working(start, cities):
                if run_start is None:
                    run_start = start
                run_end = start + timedelta(hours=1)
            elif run_start is not None:
                windows.append(close(run_start, run_end))
                run_start = run_end = None
        if run_start is not None:
            windows.append(close(run_start, run_end))
    return windows


def format_window(window: OverlapWindow) -> str:
    parts = " \u00b7 ".join(
        f"{name} {rng}" for name, rng in window.local_ranges.items()
    )
    return (
        f"{window.start_utc:%a %d %b} \u2014 {parts} \u00b7 "
        f"{window.start_utc:%H:%M}\u2013{window.end_utc:%H:%M} UTC"
    )
