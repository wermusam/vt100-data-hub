"""Vermont 100 Data Hub: the Responsible Pace Chart page."""

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
    """The Responsible Pace Chart: interactive pacing against real VT100 cutoffs.

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
            "The table shows your arrival, departure, and how you stand "
            "against every 2026 cutoff."
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

        # The 100M is paced backward from its cutoffs (which genuinely bind); the
        # 100K runs one even effort, since its early cutoffs are far too loose to
        # pace against. The 100K slider spans the range people actually finish in
        # (about 10 to 22 hours), not the meaningless 25h cutoff.
        pacing_mode = "cutoff" if distance == "100M" else "even"
        total_cutoff_minutes = schedule.cutoff_minutes_from_start(start_time)[-1]
        if distance == "100M":
            min_minutes, max_minutes = 15 * 60, total_cutoff_minutes
            default_label = "28h 00m"
        else:
            min_minutes, max_minutes = 10 * 60, 22 * 60
            default_label = "17h 00m"

        with st.expander("How this works"):
            if pacing_mode == "cutoff":
                st.markdown(
                    "**Goal finish time:** your target finish. A faster goal runs "
                    "every leg quicker and gives more cushion; the slowest setting "
                    "rides the cutoffs. It changes only your running pace, not your "
                    "stops.\n\n"
                    "**Aid station time:** the first 5 minutes at each stop are "
                    "built into the pace, so the default plan stays ahead of every "
                    "cutoff. Spend more than that and it adds to your finish and "
                    "eats your cushion (too much shows a red miss); spend less and "
                    "you gain cushion. A table edit affects that stop and the ones "
                    "after it, never before.\n\n"
                    "**The verdict** at the top says, in plain words, whether you "
                    "clear every cutoff and where it is tightest.\n\n"
                    "**Colors:** red means you miss that cutoff, yellow means you "
                    "make it but with under 30 minutes to spare, green means 30 "
                    "minutes or more. The table and the graph use the same colors."
                )
            else:
                st.markdown(
                    "**The 100K runs one even pace.** Its aid-station cutoffs are "
                    "set by the 100-mile sweep schedule, so they are far too loose "
                    "to pace against. No recent 100K finisher has come within two "
                    "hours of them. Instead of chasing cutoffs, this plan holds a "
                    "steady effort to your goal and shows how far ahead of every "
                    "cutoff you stay.\n\n"
                    "**Goal finish time:** your target finish. A faster goal runs "
                    "every leg quicker. It changes only your running pace, not your "
                    "stops.\n\n"
                    "**Aid station time:** the first 5 minutes at each stop are "
                    "built into the pace. Spend more than that and it adds to your "
                    "finish; a table edit affects that stop and the ones after it, "
                    "never before.\n\n"
                    "**The verdict** at the top shows your finish and how much room "
                    "you have at the tightest cutoff.\n\n"
                    "**Colors:** green means 30 minutes or more of room, yellow "
                    "under 30, red a miss. On the 100K you should stay green all "
                    "day."
                )

        goal_options = [
            formatter.format_hours(minutes / 60.0)
            for minutes in range(min_minutes, max_minutes + 1, 1)
        ]
        goal_key = f"goal_slider_{distance}"
        if goal_key not in st.session_state:
            st.session_state[goal_key] = default_label
        if pacing_mode == "cutoff":
            goal_help = (
                "Your target finish at the baseline stop. The slowest setting is "
                f"the {formatter.format_hours(total_cutoff_minutes / 60.0)} cutoff; "
                "faster settings run every leg quicker for more cushion. It does "
                "not change your aid-station time."
            )
        else:
            goal_help = (
                "Your target finish. The plan runs one even pace to reach it, and "
                "shows how far ahead of every cutoff you stay. A faster goal runs "
                "every leg quicker. It does not change your aid-station time."
            )
        goal_label = st.select_slider(
            "Goal finish time",
            options=goal_options,
            key=goal_key,
            help=goal_help,
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
        if pacing_mode == "cutoff":
            st.caption(
                f"⏱️ The first {int(NOMINAL_AID_MINUTES)} minutes at each stop are "
                "built into the pace. Spend **more** at any stop and it eats your "
                "cushion (too much shows a red miss); spend **less** and you gain it."
            )
        else:
            st.caption(
                f"⏱️ The first {int(NOMINAL_AID_MINUTES)} minutes at each stop are "
                "built into the pace. Spend **more** and it adds to your finish "
                "and shifts the later stations; the plan holds one even pace and "
                "stays hours ahead of every cutoff."
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
            pacing_mode=pacing_mode,
        )

        self._render_summary(plan, start_time, formatter)

        self._render_chart(plan, start_hour, start_minute)

        st.markdown(
            "**Aid station plan.** Edit **Time at Station** for any stop "
            "(🎒 = drop bag). A longer stop shifts the stations after it."
        )
        control_cols = st.columns([1, 1])
        with control_cols[0]:
            st.button(
                "Reset to defaults",
                on_click=self._reset_to_defaults,
                args=(distance, station_count, default_label),
                help="Put the goal, the average, and every stop back to the start.",
            )
        with control_cols[1]:
            show_all_columns = st.checkbox(
                "Show all columns",
                value=False,
                help=(
                    "Add the planning columns (cutoff close, your pace, time "
                    "window). Off keeps the table compact for phones."
                ),
            )

        # Compact by default so the table fits a phone; the planning columns are
        # opt-in. The station name is pinned so it stays visible when scrolling.
        essential_columns = [
            "Aid Station",
            "Mile",
            "Arrival",
            "Time at Station (min)",
            "Departure",
            "Buffer",
        ]
        all_columns = [
            "Aid Station",
            "Mile",
            "Cutoff Close",
            "Arrival",
            "Your Pace",
            "Time Window",
            "Time at Station (min)",
            "Departure",
            "Buffer",
        ]
        column_order = all_columns if show_all_columns else essential_columns

        table_data = self._build_table_rows(
            plan, schedule, start_hour, start_minute, formatter
        )
        if pacing_mode == "cutoff":
            pace_help = (
                "The slowest pace for this leg that still gets you to the next "
                "cutoff on time. It changes leg to leg because the cutoffs are "
                "spaced unevenly."
            )
        else:
            pace_help = (
                "One steady pace the whole way: your goal, less your stops, "
                "spread evenly over the course."
            )
        edited = st.data_editor(
            table_data,
            hide_index=True,
            width="stretch",
            column_order=column_order,
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
                "Aid Station": st.column_config.TextColumn(pinned=True),
                "Mile": st.column_config.NumberColumn(format="%.1f"),
                "Your Pace": st.column_config.TextColumn(help=pace_help),
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
        """Render the results header: the finish/pace/cushion metrics, the
        make-it or miss-it verdict in plain words, and a single supporting line.

        Args:
            plan: The computed pace plan.
            start_time: Race start time of day.
            formatter: Display formatter for clock times and durations.
        """
        finish_row = plan.rows[-1]
        total_aid_minutes = sum(row.aid_minutes for row in plan.rows)
        finish_minutes = finish_row.target_arrival_minutes_from_start
        running_minutes = finish_minutes - total_aid_minutes
        verdict = plan.verdict()
        is_even = plan.pacing_mode == "even"
        finish_clock = formatter.format_clock_time_with_day(
            finish_row.target_arrival_time,
            finish_minutes,
            start_time.hour,
            start_time.minute,
        )

        finish_col, pace_col, cushion_col = st.columns(3)
        finish_col.metric(
            "Finish time",
            formatter.format_duration(finish_minutes),
            help=f"You cross the line by {finish_clock}.",
        )
        pace_col.metric(
            "Even pace" if is_even else "Average pace",
            formatter.format_pace(plan.pace_per_mile_minutes),
            help=(
                "One steady pace the whole way."
                if is_even
                else "Your legs vary; this is the average across the course."
            ),
        )
        if verdict.makes_it:
            tight = verdict.tightest_row
            cushion_col.metric(
                "Room at tightest cutoff",
                formatter.format_duration(tight.buffer_minutes),
                help=f"At {tight.station_name}, mile {tight.mile}.",
            )
            st.success(
                f"✅ You clear every cutoff. The closest call is "
                f"**{tight.station_name}** at mile {tight.mile}, with "
                f"{formatter.format_duration(tight.buffer_minutes)} to spare."
            )
        else:
            missed = verdict.first_missed_row
            cushion_col.metric(
                "Behind at first miss",
                formatter.format_duration(-missed.buffer_minutes),
                help=f"At {missed.station_name}, mile {missed.mile}.",
            )
            st.error(
                f"⛔ This plan misses the cutoff at **{missed.station_name}** "
                f"(mile {missed.mile}) by "
                f"{formatter.format_duration(-missed.buffer_minutes)}. "
                f"Run faster or trim your stops."
            )
        leave_late = [
            row
            for row in plan.rows
            if row.target_arrival_minutes_from_start
            <= row.cutoff_minutes_from_start
            < row.departure_minutes_from_start
        ]
        if leave_late:
            names = ", ".join(
                f"{row.station_name} (mile {row.mile})" for row in leave_late
            )
            st.warning(
                f"⏳ You arrive in time but would **leave after closing** at "
                f"{names}. Keep these stops short so you are not pulled."
            )
        breakdown = (
            f"Start {formatter.format_clock_time(start_time)}. "
            f"{formatter.format_duration(running_minutes)} running plus "
            f"{formatter.format_duration(total_aid_minutes)} at aid stations."
        )
        disclaimer = (
            " This is a planning estimate, not a guarantee: weather, terrain, "
            "and how your day unfolds will move these times."
        )
        if is_even:
            st.caption(
                f"{breakdown} A steady even effort to your goal; many runners go "
                "out a little quicker and ease back over the final miles."
                f"{disclaimer}"
            )
        else:
            st.caption(
                f"{breakdown} Make or miss is based on **arriving** before each "
                "cutoff. This pace is the floor; most finishers bank time early "
                "and slow later."
                f"{disclaimer}"
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
            height=400,
            dragmode="zoom",
            legend={"groupclick": "toggleitem"},
            margin={"t": 80},
        )
        st.plotly_chart(figure, width="stretch", config={"scrollZoom": True})
        st.caption(
            "Each station has two dots: open when you arrive, filled when you "
            "leave, and the step between them is your time there. Drag a box to "
            "zoom, double click to reset."
        )


PacePlannerPage().render()
