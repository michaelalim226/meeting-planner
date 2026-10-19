"""Streamlit UI for the Borderless Meeting Planner (SPEC.md §2)."""

from datetime import datetime, timedelta, timezone

import streamlit as st

from logic import (
    CATALOG,
    CellStatus,
    CityRecord,
    build_grid,
    clock_badge,
    format_window,
    local_time,
    overlap_windows,
    total_overlap_hours,
)

STATUS_STYLE = {
    CellStatus.OUTSIDE: ("#f1f5f9", "#cbd5e1", "400"),
    CellStatus.WORKING: ("#60a5fa", "#ffffff", "600"),
    CellStatus.OVERLAP: ("#22c55e", "#ffffff", "700"),
}


def pill(label: str, bg: str, fg: str) -> str:
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;'
        f'background:{bg};color:{fg};font-size:13px;font-weight:600;'
        f'margin-right:6px;">{label}</span>'
    )


def render_grid_row(grid) -> None:
    st.markdown(
        f"**{grid.city}** \u2014 {grid.local_date:%a %Y-%m-%d} local "
        f"\u00b7 green = overlap"
    )
    cells = []
    for cell in grid.cells:
        bg, fg, weight = STATUS_STYLE[cell.status]
        cells.append(
            f'<span style="display:inline-flex;align-items:center;'
            f'justify-content:center;width:30px;height:28px;border-radius:6px;'
            f'font-size:12px;font-weight:{weight};background:{bg};color:{fg};">'
            f'{cell.hour:02d}</span>'
        )
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;gap:4px;">' + "".join(cells) + "</div>",
        unsafe_allow_html=True,
    )


@st.fragment(run_every=timedelta(seconds=1))
def local_clocks(cities: list[CityRecord]) -> None:
    now = datetime.now(timezone.utc)
    st.subheader("Local clocks")
    for i in range(0, len(cities), 4):
        row = cities[i : i + 4]
        cols = st.columns(len(row))
        for col, city in zip(cols, row):
            with col:
                local = local_time(now, city.tz)
                st.markdown(
                    f'<div style="color:#64748b;font-size:14px;">{city.name}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:34px;font-weight:700;line-height:1.3;">'
                    f"{local:%H:%M:%S}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    pill(clock_badge(now, city.tz), "#f1f5f9", "#475569"),
                    unsafe_allow_html=True,
                )


st.set_page_config(page_title="Borderless Meeting Planner", layout="wide")

st.sidebar.header("Cities")
catalog_names = [c.name for c in CATALOG]
selected_names = st.sidebar.multiselect(
    "Add or remove cities",
    catalog_names,
    default=["London", "Bali"],
)
st.sidebar.caption(f"{len(selected_names)} of {len(CATALOG)} cities selected")

cities = [c for c in CATALOG if c.name in set(selected_names)]
now = datetime.now(timezone.utc)

st.title("Borderless Meeting Planner")
st.caption("Find a window where every city is inside 09:00\u201317:00 local time.")

overlap = total_overlap_hours(now, cities)
m1, m2 = st.columns(2)
m1.metric("Cities", len(cities))
m2.metric("Overlapping hours (next 7 days)", f"{overlap:.1f} h")

if not cities:
    st.info("Add cities in the sidebar to see clocks and overlap windows.")
    st.stop()

if overlap == 0.0:
    st.warning("No overlapping hours in the next 7 days for these cities.")

local_clocks(cities)

st.subheader("24-hour local view")
st.markdown(
    pill("Working hours", "#60a5fa", "#ffffff")
    + pill("Overlapping hours", "#22c55e", "#ffffff")
    + pill("Outside working hours", "#f1f5f9", "#94a3b8"),
    unsafe_allow_html=True,
)
for grid in build_grid(now, cities):
    render_grid_row(grid)

windows = overlap_windows(now, cities)
if windows:
    st.subheader("Overlap windows")
    for window in windows:
        st.markdown(f"- {format_window(window)}")
