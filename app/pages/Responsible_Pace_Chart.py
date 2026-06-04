"""Vermont 100 Data Hub — Pace Planner page."""

from __future__ import annotations

from datetime import time
from pathlib import Path

# Imported for its side effect: pandas must be fully initialized before
# Plotly's lazy pandas check runs while rendering the chart, or Plotly 6 with
# pandas 3 raises a circular-import error. Not referenced directly here.
import pandas  # noqa: F401
import plotly.graph_objects as go
import streamlit as st

from vt100_data_hub.cutoffs import CutoffSchedule
from vt100_data_hub.formatting import DisplayFormatters
from vt100_data_hub.pacing import PacePlan

CUTOFFS_100M_PATH = (
    Path(__file__).parent.parent.parent / "data" / "cutoffs_2026_100m.csv"
)
CUTOFFS_100K_PATH = (
    Path(__file__).parent.parent.parent / "data" / "cutoffs_2026_100k.csv"
)

# The stop time the goal is measured against. A goal finish assumes this many
# minutes at every station; planning more (a longer average or a drop bag)
# pushes the finish later, planning less pulls it in.
NOMINAL_AID_MINUTES = 3.0


class PacePlannerPage:
    """The Pace Planner page — interactive pacing against real VT100 cutoffs.

    Attributes:
        cutoffs_100m_path: Path to the 100M cutoffs CSV.
        cutoffs_100k_path: Path to the 100K cutoffs CSV.
    """

    def __init__(
        self,
        cutoffs_100m_path: Path = CUTOFFS_100M_PATH,
        cutoffs_100k_path: Path = CUTOFFS_100K_PATH,
    ) -> None:
        self.cutoffs_100m_path = cutoffs_100m_path
        self.cutoffs_100k_path = cutoffs_100k_path

    def render(self) -> None:
        """Render the pace planner page."""
        st.markdown(
            "<style>"
            '[data-testid="stElementToolbar"]{display:none;}'
            '[data-testid="StyledFullScreenButton"]{display:none;}'
            'button[title="View fullscreen"]{display:none;}'
            "</style>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h1 style='text-align: center;'>Vermont 100 Data Hub</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h2 style='text-align: center;'>Responsible Pace Chart</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "Set your goal finish time and your time at each aid station. "
            "The table shows your arrival, departure, and the cushion you'd "
            "have against every 2026 cutoff."
        )

        formatter = DisplayFormatters()

        st.sidebar.header("Your Race")
        distance = st.sidebar.radio(
            "Distance", options=["100M", "100K"], index=0
        )
        # VT100 start times are fixed by the race: 4:00 AM for the 100M,
        # 9:00 AM for the 100K (vermont100.com/race-details).
        start_hour, start_minute = (4, 0) if distance == "100M" else (9, 0)
        start_time = time(start_hour, start_minute)

        csv_path = (
            self.cutoffs_100m_path if distance == "100M" else self.cutoffs_100k_path
        )
        schedule = CutoffSchedule(csv_path=csv_path, distance=distance)

        # Only offer goals up to this race's real time limit, so a runner
        # can't pick an impossible finish. Default a few hours under the limit
        # so the cutoff and plan lines are clearly separated on the chart.
        total_cutoff_minutes = schedule.cutoff_minutes_from_start(start_time)[-1]
        min_minutes = 15 * 60 if distance == "100M" else 10 * 60
        default_label = "28h 00m" if distance == "100M" else "20h 00m"
        goal_options = [
            formatter.format_hours(minutes / 60.0)
            for minutes in range(min_minutes, total_cutoff_minutes + 1, 15)
        ]
        goal_label = st.select_slider(
            "Goal finish time",
            options=goal_options,
            value=default_label,
            key=f"goal_{distance}",
            help=(
                "Target finish time. This race's cutoff is "
                f"{formatter.format_hours(total_cutoff_minutes / 60.0)}."
            ),
        )
        goal_hours = formatter.parse_hm_label(goal_label)
        aid_col, _aid_spacer = st.columns([1, 2])
        with aid_col:
            aid_minutes = st.number_input(
                "Avg time at each aid station (minutes)",
                min_value=0.0,
                value=NOMINAL_AID_MINUTES,
                step=1.0,
                help=(
                    "Sets the time at every station. Override individual stops "
                    "(drop bags) in the table below; Reset re-applies this average."
                ),
            )

        # Per-station aid times live in session state so the table can edit
        # individual stops. Changing the average (or the distance) re-applies
        # it to every station; the finish line never has a stop.
        station_count = len(schedule.stations)
        times_key = f"aid_times_{distance}"
        avg_key = f"aid_avg_{distance}"
        if (
            times_key not in st.session_state
            or len(st.session_state[times_key]) != station_count
            or st.session_state.get(avg_key) != aid_minutes
        ):
            st.session_state[avg_key] = aid_minutes
            st.session_state[times_key] = PacePlan.stop_minutes_with_no_finish_stop(
                [aid_minutes] * station_count
            )

        plan = PacePlan(
            schedule=schedule,
            goal_hours=goal_hours,
            start_time=start_time,
            aid_minutes_per_station=st.session_state[times_key],
            nominal_aid_minutes=NOMINAL_AID_MINUTES,
        )

        finish_row = plan.rows[-1]
        tightest = min(plan.rows, key=lambda r: r.buffer_minutes)
        total_aid_minutes = sum(row.aid_minutes for row in plan.rows)
        moving_minutes = goal_hours * 60.0 - NOMINAL_AID_MINUTES * max(
            station_count - 1, 0
        )
        longest = max(plan.rows, key=lambda row: row.aid_minutes)
        st.markdown(
            "<div style='text-align:center; line-height:1.45;'>"
            f"<div style='font-size:2.2rem; font-weight:700; color:#1565C0;'>"
            f"{formatter.format_duration(finish_row.target_arrival_minutes_from_start)}"
            f"</div>"
            f"<div style='font-size:0.8rem; color:#555; margin-top:-0.2rem;'>"
            f"projected finish</div>"
            f"<div style='font-size:1.05rem;'>"
            f"{formatter.format_duration(moving_minutes)} running</div>"
            f"<div style='font-size:1.05rem;'>"
            f"{formatter.format_duration(total_aid_minutes)} at aid stations</div>"
            f"<div style='font-size:0.9rem; color:#555;'>Longest stop: "
            f"{formatter.format_duration(longest.aid_minutes)} at "
            f"{longest.station_name}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**Start:** {formatter.format_clock_time(start_time)} &nbsp;|&nbsp; "
            f"**Required overall pace:** {formatter.format_pace(plan.pace_per_mile_minutes)} &nbsp;|&nbsp; "
            f"**Expected finish:** {formatter.format_clock_time(finish_row.target_arrival_time)}"
        )
        st.caption(
            "These are estimates to plan with, not a guarantee. Adjust any "
            "stop in the table to match your own race."
        )
        st.markdown(
            f"**Tightest buffer:** {tightest.station_name} at mile {tightest.mile}, "
            f"{formatter.format_duration(tightest.buffer_minutes)}"
        )

        self._render_chart(plan, start_hour, start_minute)

        st.markdown(
            "**Aid station plan** — edit **Time at Station** for any stop "
            "(🎒 = drop bag). A longer stop shifts the stations after it."
        )
        if st.button("Reset all aid-station times to the average"):
            st.session_state[times_key] = PacePlan.stop_minutes_with_no_finish_stop(
                [aid_minutes] * station_count
            )
            st.rerun()

        table_data = [
            {
                "Aid Station": (
                    f"{row.station_name} 🎒"
                    if "D" in station.station_type
                    else row.station_name
                ),
                "Mile": row.mile,
                "Cutoff Close": formatter.format_clock_time_with_day(
                    row.cutoff_close_time,
                    row.cutoff_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Arrival": formatter.format_clock_time_with_day(
                    row.target_arrival_time,
                    row.target_arrival_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Time at Station (min)": row.aid_minutes,
                "Departure": formatter.format_clock_time_with_day(
                    row.departure_time,
                    row.departure_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Buffer": formatter.format_duration(row.buffer_minutes),
            }
            for row, station in zip(plan.rows, schedule.stations)
        ]
        edited = st.data_editor(
            table_data,
            hide_index=True,
            width="stretch",
            column_order=[
                "Aid Station",
                "Mile",
                "Cutoff Close",
                "Arrival",
                "Time at Station (min)",
                "Departure",
                "Buffer",
            ],
            disabled=[
                "Aid Station",
                "Mile",
                "Cutoff Close",
                "Arrival",
                "Departure",
                "Buffer",
            ],
            column_config={
                "Mile": st.column_config.NumberColumn(format="%.1f"),
                "Time at Station (min)": st.column_config.NumberColumn(
                    min_value=0, step=1
                ),
            },
        )
        edited_times = PacePlan.stop_minutes_with_no_finish_stop(
            [r["Time at Station (min)"] for r in edited]
        )
        if edited_times != st.session_state[times_key]:
            st.session_state[times_key] = edited_times
            st.rerun()

        st.divider()

    def _render_chart(
        self, plan: PacePlan, start_hour: int, start_minute: int
    ) -> None:
        """Render the cutoff-vs-pace-plan chart with Plotly.

        Purple line = when each aid station closes (the wall). The blue line is
        your plan drawn as a staircase: at each station it rises by the time
        you spend there (arrival up to departure), so a long stop is a tall
        step. Each station has an open dot at arrival and a colored dot at
        departure; the departure dot's color is your cushion before the cutoff
        (red/amber/green). Two dashed horizontal lines mark the race time limit
        (purple) and your goal (blue).
        """
        formatter = DisplayFormatters()
        miles = [row.mile for row in plan.rows]
        cutoff_hours = [
            round(row.cutoff_minutes_from_start / 60.0, 2) for row in plan.rows
        ]
        target_hours = [
            round(row.target_arrival_minutes_from_start / 60.0, 2)
            for row in plan.rows
        ]
        names = [row.station_name for row in plan.rows]
        cutoff_clocks = [
            formatter.format_clock_time_with_day(
                row.cutoff_close_time,
                row.cutoff_minutes_from_start,
                start_hour,
                start_minute,
            )
            for row in plan.rows
        ]
        target_clocks = [
            formatter.format_clock_time_with_day(
                row.target_arrival_time,
                row.target_arrival_minutes_from_start,
                start_hour,
                start_minute,
            )
            for row in plan.rows
        ]
        departure_hours = [
            round(row.departure_minutes_from_start / 60.0, 2) for row in plan.rows
        ]
        departure_clocks = [
            formatter.format_clock_time_with_day(
                row.departure_time,
                row.departure_minutes_from_start,
                start_hour,
                start_minute,
            )
            for row in plan.rows
        ]
        buffers = [formatter.format_duration(row.buffer_minutes) for row in plan.rows]
        cushions = [
            formatter.buffer_category(row.buffer_minutes) for row in plan.rows
        ]

        figure = go.Figure()

        # Cutoff line (purple): hover shows the station and its cutoff only.
        figure.add_trace(
            go.Scatter(
                x=miles,
                y=cutoff_hours,
                mode="lines+markers",
                name="Cutoff",
                legendgroup="times",
                legendgrouptitle_text="Times",
                line={"color": "#7B1FA2", "width": 2.5},
                marker={"color": "#7B1FA2", "size": 7},
                customdata=[[n, c] for n, c in zip(names, cutoff_clocks)],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Cutoff closes: %{customdata[1]}<extra></extra>"
                ),
            )
        )

        # Goal line (blue): a staircase. At each station it rises vertically by
        # the time spent there (arrival up to departure), then slopes to the
        # next station. A long stop becomes a tall step you can't miss.
        stair_x: list[float] = []
        stair_y: list[float] = []
        for i in range(len(plan.rows)):
            stair_x.extend([miles[i], miles[i]])
            stair_y.extend([target_hours[i], departure_hours[i]])
        figure.add_trace(
            go.Scatter(
                x=stair_x,
                y=stair_y,
                mode="lines",
                name="Goal",
                legendgroup="times",
                line={"color": "#1565C0", "width": 2.5},
                hoverinfo="skip",
            )
        )
        # Open blue dot at each station's arrival.
        figure.add_trace(
            go.Scatter(
                x=miles,
                y=target_hours,
                mode="markers",
                name="Arrival",
                legendgroup="times",
                marker={
                    "color": "white",
                    "size": 7,
                    "line": {"color": "#1565C0", "width": 2},
                },
                customdata=[
                    [
                        names[i],
                        target_clocks[i],
                        departure_clocks[i],
                        cutoff_clocks[i],
                        buffers[i],
                    ]
                    for i in range(len(plan.rows))
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Arrive: %{customdata[1]}<br>"
                    "Leave: %{customdata[2]}<br>"
                    "Cutoff closes: %{customdata[3]}<br>"
                    "Cutoff cushion: %{customdata[4]}<extra></extra>"
                ),
            )
        )

        # Cushion dots on the goal line, one trace per category so each gets
        # its own legend entry.
        cushion_colors = {
            "Tight (under 30m)": "#C62828",
            "Caution (30m-1h)": "#F9A825",
            "Comfortable (over 1h)": "#2E7D32",
        }
        # Always add all three categories (even when empty) so the legend
        # stays stable as the goal slider changes which cushions appear.
        for category, color in cushion_colors.items():
            indices = [i for i, c in enumerate(cushions) if c == category]
            xs = [miles[i] for i in indices]
            ys = [departure_hours[i] for i in indices]
            custom = [
                [
                    names[i],
                    target_clocks[i],
                    departure_clocks[i],
                    cutoff_clocks[i],
                    buffers[i],
                ]
                for i in indices
            ]
            figure.add_trace(
                go.Scatter(
                    x=xs or [None],
                    y=ys or [None],
                    mode="markers",
                    name=category,
                    legendgroup="cushion",
                    legendgrouptitle_text="Cutoff Cushion (when you leave)",
                    marker={
                        "color": color,
                        "size": 10,
                        "line": {"color": "white", "width": 1},
                    },
                    customdata=custom or [[None, None, None, None, None]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Arrive: %{customdata[1]}<br>"
                        "Leave: %{customdata[2]}<br>"
                        "Cutoff closes: %{customdata[3]}<br>"
                        "Cutoff cushion: %{customdata[4]}<extra></extra>"
                    ),
                )
            )

        total_cutoff_hours = round(
            plan.rows[-1].cutoff_minutes_from_start / 60.0, 2
        )
        figure.add_hline(
            y=total_cutoff_hours,
            line_dash="dash",
            line_color="#7B1FA2",
            line_width=1.5,
        )
        figure.add_hline(
            y=round(plan.goal_hours, 2),
            line_dash="dash",
            line_color="#1565C0",
            line_width=1.5,
        )

        tightest = min(plan.rows, key=lambda r: r.buffer_minutes)
        figure.add_annotation(
            x=tightest.mile,
            y=round(tightest.departure_minutes_from_start / 60.0, 2),
            text=f"Tightest: {formatter.format_duration(tightest.buffer_minutes)}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#C62828",
            ax=0,
            ay=-40,
            font={"size": 11, "color": "#C62828"},
        )

        figure.update_layout(
            template="simple_white",
            title={
                "text": (
                    "Your Pace Plan vs the Cutoffs<br>"
                    "<sub>Stay under the purple line. Blue is your plan.</sub>"
                ),
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis={
                "title": "Mile",
                "showgrid": True,
                "gridcolor": "rgba(0,0,0,0.18)",
                "dtick": 5,
            },
            yaxis={
                "title": "Hours elapsed since race start",
                "showgrid": True,
                "gridcolor": "rgba(0,0,0,0.18)",
                "dtick": 5,
            },
            height=440,
            dragmode="zoom",
            legend={"groupclick": "toggleitem"},
            margin={"t": 80},
        )
        st.plotly_chart(figure, width="stretch", config={"scrollZoom": True})
        st.caption(
            "Each station has two dots: an open dot when you arrive and a "
            "colored dot when you leave. The step between them is your time "
            "there. The leave dot's color is your cutoff cushion: red under "
            "30 min, amber 30 min to 1 hour, green over 1 hour. Drag a box to "
            "zoom; double-click to reset."
        )


PacePlannerPage().render()
