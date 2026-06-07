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
    Path(__file__).parent.parent / "data" / "cutoffs_2026_100m.csv"
)
CUTOFFS_100K_PATH = (
    Path(__file__).parent.parent / "data" / "cutoffs_2026_100k.csv"
)

# The stop time the goal is measured against. A goal finish assumes this many
# minutes at every station; planning more (a longer average or a drop bag)
# pushes the finish later, planning less pulls it in. Five minutes is a calmer,
# more realistic default than a rushed three.
NOMINAL_AID_MINUTES = 5.0


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
        st.set_page_config(
            page_title="Vermont 100 Data Hub",
            page_icon="🏃",
            layout="wide",
        )
        st.markdown(
            "<style>"
            '[data-testid="stElementToolbar"]{display:none;}'
            '[data-testid="StyledFullScreenButton"]{display:none;}'
            'button[title="View fullscreen"]{display:none;}'
            "</style>",
            unsafe_allow_html=True,
        )
        st.title("Vermont 100 Responsible Pace Chart")
        st.markdown(
            "Set your goal finish time and your time at each aid station. "
            "The table shows your arrival, departure, and the cushion you'd "
            "have against every 2026 cutoff."
        )
        with st.expander("How this works"):
            st.markdown(
                "**Goal finish time:** your target finish. A faster goal runs "
                "every leg quicker and gives more cushion; the slowest setting "
                "rides the cutoffs. It changes only your running pace, not your "
                "stops.\n\n"
                "**Aid station time:** the first 5 minutes at each stop are built "
                "into the pace, so the default plan stays ahead of every cutoff. "
                "Spend more than that and it adds to your finish and eats your "
                "cushion (too much shows a red miss); spend less and you gain "
                "cushion. A table edit affects that stop and the ones after it, "
                "never before.\n\n"
                "**The verdict** at the top says, in plain words, whether you "
                "clear every cutoff and where it is tightest.\n\n"
                "**Colors:** red means you miss that cutoff, yellow means you "
                "make it but with under 30 minutes to spare, green means 30 "
                "minutes or more. The table and the graph use the same colors."
            )

        formatter = DisplayFormatters()

        distance = st.radio(
            "Distance", options=["100M", "100K"], index=0, horizontal=True
        )
        # Switching distance starts that distance fresh. Streamlit purges the
        # goal and average widgets when they leave the screen but keeps the
        # plain session values, so without this the two drift out of sync and
        # produce a goal the runner never chose.
        if st.session_state.get("last_distance") != distance:
            for key in (
                f"goal_slider_{distance}",
                f"aid_times_{distance}",
                f"aid_avg_{distance}",
                f"avg_input_{distance}",
            ):
                st.session_state.pop(key, None)
            st.session_state["last_distance"] = distance
        # VT100 start times are fixed by the race: 4:00 AM for the 100M,
        # 9:00 AM for the 100K (vermont100.com/race-details).
        start_hour, start_minute = (4, 0) if distance == "100M" else (9, 0)
        start_time = time(start_hour, start_minute)

        csv_path = (
            self.cutoffs_100m_path if distance == "100M" else self.cutoffs_100k_path
        )
        schedule = CutoffSchedule(csv_path=csv_path, distance=distance)

        # The goal slider is your target finish at the baseline stop. Its
        # slowest setting is this race's cutoff; faster settings run every leg
        # quicker and give more cushion. It steps every minute.
        total_cutoff_minutes = schedule.cutoff_minutes_from_start(start_time)[-1]
        min_minutes = 15 * 60 if distance == "100M" else 10 * 60
        default_label = "28h 00m" if distance == "100M" else "23h 00m"
        goal_options = [
            formatter.format_hours(minutes / 60.0)
            for minutes in range(min_minutes, total_cutoff_minutes + 1, 1)
        ]
        goal_key = f"goal_slider_{distance}"
        if goal_key not in st.session_state:
            st.session_state[goal_key] = default_label
        goal_label = st.select_slider(
            "Goal finish time",
            options=goal_options,
            key=goal_key,
            help=(
                "Your target finish at the baseline stop. The slowest setting is "
                f"the {formatter.format_hours(total_cutoff_minutes / 60.0)} cutoff; "
                "faster settings run every leg quicker for more cushion. It does "
                "not change your aid-station time."
            ),
        )
        goal_minutes = formatter.parse_hm_label(goal_label) * 60.0
        aid_col, _aid_spacer = st.columns([1, 2])
        with aid_col:
            avg_input_key = f"avg_input_{distance}"
            if avg_input_key not in st.session_state:
                st.session_state[avg_input_key] = NOMINAL_AID_MINUTES
            aid_minutes = st.number_input(
                "Avg time at each aid station (minutes)",
                min_value=0.0,
                step=1.0,
                key=avg_input_key,
                help=(
                    "Sets the time at every station. Override individual stops "
                    "(drop bags) in the table below; Reset returns everything "
                    "to the defaults."
                ),
            )
        st.caption(
            f"⏱️ The first {int(NOMINAL_AID_MINUTES)} minutes at each stop are "
            "built into the pace. Spend **more** at any stop and it eats your "
            "cushion (too much shows a red miss); spend **less** and you gain it."
        )

        # Per-station aid times live in session state so the table can edit
        # individual stops; the finish line never has a stop. Changing the
        # average re-applies it to every station.
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

        stops = st.session_state[times_key]
        plan = PacePlan(
            schedule=schedule,
            goal_hours=goal_minutes / 60.0,
            start_time=start_time,
            aid_minutes_per_station=stops,
            nominal_aid_minutes=NOMINAL_AID_MINUTES,
            arrival_margin_minutes=NOMINAL_AID_MINUTES,
        )

        self._render_summary(plan, start_time, formatter)

        self._render_chart(plan, start_hour, start_minute)

        st.markdown(
            "**Aid station plan.** Edit **Time at Station** for any stop "
            "(🎒 = drop bag). A longer stop shifts the stations after it."
        )
        st.button(
            "Reset to defaults",
            on_click=self._reset_to_defaults,
            args=(distance, station_count, default_label),
            help="Put the goal, the average, and every stop back to the start.",
        )

        table_data = self._build_table_rows(
            plan, schedule, start_hour, start_minute, formatter
        )
        edited = st.data_editor(
            table_data,
            hide_index=True,
            width="stretch",
            column_order=[
                "Aid Station",
                "Mile",
                "Cutoff Close",
                "Arrival",
                "Your Pace",
                "Time Window",
                "Time at Station (min)",
                "Departure",
                "Buffer",
            ],
            disabled=[
                "Aid Station",
                "Mile",
                "Cutoff Close",
                "Arrival",
                "Your Pace",
                "Time Window",
                "Departure",
                "Buffer",
            ],
            column_config={
                "Mile": st.column_config.NumberColumn(format="%.1f"),
                "Your Pace": st.column_config.TextColumn(
                    help=(
                        "The slowest pace for this leg that still gets you to "
                        "the next cutoff on time. It changes leg to leg because "
                        "the cutoffs are spaced unevenly."
                    ),
                ),
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

        st.download_button(
            "Download my plan (CSV)",
            data=self._plan_as_csv(
                plan, schedule, start_hour, start_minute, formatter
            ),
            file_name=f"vt100_pace_plan_{distance.lower()}.csv",
            mime="text/csv",
            help="Save this plan to print or carry on race day.",
        )

        st.divider()

    def _reset_to_defaults(
        self, distance: str, station_count: int, default_label: str
    ) -> None:
        """Put every control for a distance back to its starting defaults.

        Wired to the Reset button's on_click. Running inside a callback (before
        the script reruns) is what lets it set the average-input and goal-slider
        widgets without Streamlit's "modified after the widget was instantiated"
        error.

        Args:
            distance: "100M" or "100K", used to key the per-distance state.
            station_count: Number of aid stations, for rebuilding stop times.
            default_label: The distance's default goal time, e.g. "28h 00m".
        """
        st.session_state[f"avg_input_{distance}"] = NOMINAL_AID_MINUTES
        st.session_state[f"aid_avg_{distance}"] = NOMINAL_AID_MINUTES
        st.session_state[f"aid_times_{distance}"] = (
            PacePlan.stop_minutes_with_no_finish_stop(
                [NOMINAL_AID_MINUTES] * station_count
            )
        )
        st.session_state[f"goal_slider_{distance}"] = default_label

    def _render_summary(
        self,
        plan: PacePlan,
        start_time: time,
        formatter: DisplayFormatters,
    ) -> None:
        """Render the finish-time headline, the make-it/miss-it verdict, and the
        start / running-pace / finish line.

        Args:
            plan: The computed pace plan.
            start_time: Race start time of day.
            formatter: Display formatter for clock times and durations.
        """
        finish_row = plan.rows[-1]
        total_aid_minutes = sum(row.aid_minutes for row in plan.rows)
        finish_minutes = finish_row.target_arrival_minutes_from_start
        running_minutes = finish_minutes - total_aid_minutes
        st.markdown(
            "<div style='text-align:center; line-height:1.45;'>"
            f"<div style='font-size:2.2rem; font-weight:700; color:#1565C0;'>"
            f"{formatter.format_duration(finish_minutes)}"
            f"</div>"
            f"<div style='font-size:0.8rem; color:#555; margin-top:-0.2rem;'>"
            f"finish time</div>"
            f"<div style='font-size:1.05rem;'>"
            f"{formatter.format_duration(running_minutes)} running + "
            f"{formatter.format_duration(total_aid_minutes)} at aid stations</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        verdict = plan.verdict()
        if verdict.makes_it:
            tight = verdict.tightest_row
            st.success(
                f"✅ **You make it.** This plan clears every cutoff. Tightest "
                f"is **{tight.station_name}** (mile {tight.mile}), "
                f"{formatter.format_duration(tight.buffer_minutes)} to spare."
            )
        else:
            missed = verdict.first_missed_row
            st.error(
                f"⛔ **This plan misses the cutoff at {missed.station_name}** "
                f"(mile {missed.mile}) by "
                f"{formatter.format_duration(-missed.buffer_minutes)}. "
                f"Run faster or trim stops."
            )
        leave_late = [
            row
            for row in plan.rows
            if row.target_arrival_minutes_from_start
            <= row.cutoff_minutes_from_start
            < row.departure_minutes_from_start
        ]
        if leave_late:
            names = ", ".join(f"{row.station_name} (mile {row.mile})" for row in leave_late)
            st.warning(
                f"⏳ You arrive in time but would **leave after closing** at: "
                f"{names}. Keep these stops short so you are not pulled."
            )
        st.markdown(
            f"**Start:** {formatter.format_clock_time(start_time)} &nbsp;|&nbsp; "
            f"**Running pace:** {formatter.format_pace(plan.pace_per_mile_minutes)} &nbsp;|&nbsp; "
            f"**Expected finish:** {formatter.format_clock_time(finish_row.target_arrival_time)}"
        )
        st.caption(
            "Make or miss is based on **arriving** before each cutoff. This pace "
            "is the floor; most finishers bank time in the first half and slow "
            "later."
        )

    def _build_table_rows(
        self,
        plan: PacePlan,
        schedule: CutoffSchedule,
        start_hour: int,
        start_minute: int,
        formatter: DisplayFormatters,
    ) -> list[dict[str, object]]:
        """Build the aid-station table rows for the data editor.

        The Buffer cell is shaded with a red/yellow/green dot using the same
        cushion thresholds as the line graph, so the table and chart read the
        same. Drop-bag stations get a 🎒 on their name.

        Args:
            plan: The computed pace plan, one row per aid station.
            schedule: The cutoff schedule, used for each station's type code.
            start_hour: Race start hour, for day-aware clock formatting.
            start_minute: Race start minute, for day-aware clock formatting.
            formatter: Display formatter for clock times and durations.

        Returns:
            One dict per aid station, in course order, ready for st.data_editor.
        """
        buffer_dots = {
            "Miss (after cutoff)": "🔴",
            "Tight (under 30m)": "🟡",
            "Comfortable (30m+)": "🟢",
        }
        return [
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
                "Your Pace": formatter.format_pace(
                    row.your_section_pace_min_per_mile
                ),
                "Time Window": formatter.format_duration(
                    row.cutoff_window_minutes
                ),
                "Time at Station (min)": row.aid_minutes,
                "Departure": formatter.format_clock_time_with_day(
                    row.departure_time,
                    row.departure_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Buffer": (
                    f"{buffer_dots[formatter.buffer_category(row.buffer_minutes)]} "
                    f"{formatter.format_duration(row.buffer_minutes)}"
                ),
            }
            for row, station in zip(plan.rows, schedule.stations)
        ]

    @staticmethod
    def _plan_as_csv(
        plan: PacePlan,
        schedule: CutoffSchedule,
        start_hour: int,
        start_minute: int,
        formatter: DisplayFormatters,
    ) -> str:
        """Build a downloadable CSV of the current pace plan.

        One row per aid station, in course order, with the same columns as the
        on-screen table plus a plain-text cushion category (the table shows it
        as a color).

        Args:
            plan: The computed pace plan.
            schedule: The cutoff schedule, for each station's type code.
            start_hour: Race start hour, for day-aware clock formatting.
            start_minute: Race start minute, for day-aware clock formatting.
            formatter: Display formatter for clock times and durations.

        Returns:
            The plan as CSV text, with a header row.
        """
        header = (
            "Aid Station,Mile,Cutoff Close,Arrival,Your Pace,Time Window,"
            "Time at Station (min),Departure,Buffer,Cushion"
        )
        lines = [header]
        for row, station in zip(plan.rows, schedule.stations):
            name = row.station_name + (
                " (drop bag)" if "D" in station.station_type else ""
            )
            cells = [
                name,
                f"{row.mile:.1f}",
                formatter.format_clock_time_with_day(
                    row.cutoff_close_time,
                    row.cutoff_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                formatter.format_clock_time_with_day(
                    row.target_arrival_time,
                    row.target_arrival_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                formatter.format_pace(row.your_section_pace_min_per_mile),
                formatter.format_duration(row.cutoff_window_minutes),
                f"{row.aid_minutes:.0f}",
                formatter.format_clock_time_with_day(
                    row.departure_time,
                    row.departure_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                formatter.format_duration(row.buffer_minutes),
                formatter.buffer_category(row.buffer_minutes),
            ]
            lines.append(",".join(f'"{cell}"' for cell in cells))
        return "\n".join(lines)

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
            "Miss (after cutoff)": "#C62828",
            "Tight (under 30m)": "#F9A825",
            "Comfortable (30m+)": "#2E7D32",
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
            "there. The dot's color is your cushion: red means you miss it, "
            "yellow under 30 min to spare, green 30 min or more. Drag a box to "
            "zoom, and double click to reset."
        )


PacePlannerPage().render()
