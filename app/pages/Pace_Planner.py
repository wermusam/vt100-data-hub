"""Vermont 100 Data Hub — Pace Planner page."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import altair as alt
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
        st.title("Vermont 100 Data Hub")
        st.subheader("Pace Planner")
        st.markdown(
            "Set your goal finish time. The table shows the required pace "
            "between each aid station to hit every cutoff, your target "
            "arrival, and the buffer you'd have at each station."
        )

        goal_options = self._build_goal_options()
        goal_label = st.select_slider(
            "Goal finish time",
            options=goal_options,
            value="28h 00m",
            help="Target time to finish. The official race cutoff is 30h 00m.",
        )
        goal_hours = self._parse_goal_label(goal_label)

        st.sidebar.header("Your Race")
        distance = st.sidebar.radio(
            "Distance", options=["100M", "100K"], index=0
        )
        start_hour = st.sidebar.number_input(
            "Race start hour (24h)", min_value=0, max_value=23, value=4
        )
        start_minute = st.sidebar.number_input(
            "Race start minute", min_value=0, max_value=59, value=0
        )

        csv_path = (
            self.cutoffs_100m_path if distance == "100M" else self.cutoffs_100k_path
        )
        schedule = CutoffSchedule(csv_path=csv_path, distance=distance)
        plan = PacePlan(
            schedule=schedule,
            goal_hours=goal_hours,
            start_time=time(start_hour, start_minute),
        )

        finish_row = plan.rows[-1]
        tightest = min(plan.rows, key=lambda r: r.buffer_minutes)
        st.markdown(
            f"**Goal:** {self._format_hours_long(goal_hours)} &nbsp;|&nbsp; "
            f"**Required overall pace:** {self._format_pace(plan.pace_per_mile_minutes)} &nbsp;|&nbsp; "
            f"**Expected finish:** {self._format_time(finish_row.target_arrival_time)}"
        )
        st.markdown(
            f"**Tightest buffer:** {tightest.station_name} at mile {tightest.mile}, "
            f"{self._format_buffer(tightest.buffer_minutes)}"
        )

        self._render_chart(plan, start_hour, start_minute)

        table_data = [
            {
                "Aid Station": row.station_name,
                "Mile": row.mile,
                "Section Distance": round(row.section_distance_miles, 1),
                "Cutoff Close": self._format_time_with_day(
                    row.cutoff_close_time,
                    row.cutoff_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Time Window": self._format_buffer(row.cutoff_window_minutes),
                "Your Pace": self._format_pace(
                    row.your_section_pace_min_per_mile
                ),
                "Your Target Arrival": self._format_time_with_day(
                    row.target_arrival_time,
                    row.target_arrival_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Buffer": self._format_buffer(row.buffer_minutes),
            }
            for row in plan.rows
        ]
        st.dataframe(
            table_data,
            hide_index=True,
            width="stretch",
            column_config={
                "Section Distance": st.column_config.NumberColumn(format="%.1f"),
            },
        )

        st.divider()

    def _format_hours_long(self, hours: float) -> str:
        """Format decimal hours (e.g., 24.75) as 'Xh YYm'."""
        whole = int(hours)
        minutes = int(round((hours - whole) * 60))
        if minutes == 60:
            whole += 1
            minutes = 0
        return f"{whole}h {minutes:02d}m"

    def _build_goal_options(self) -> list[str]:
        """Build the list of selectable goal-time labels in 15-minute steps."""
        options: list[str] = []
        for total_minutes in range(15 * 60, 30 * 60 + 1, 15):
            hours, minutes = divmod(total_minutes, 60)
            options.append(f"{hours}h {minutes:02d}m")
        return options

    def _parse_goal_label(self, label: str) -> float:
        """Parse 'Xh YYm' back to decimal hours (e.g., 20.25)."""
        hours_part, minutes_part = label.split()
        hours = int(hours_part.rstrip("h"))
        minutes = int(minutes_part.rstrip("m"))
        return hours + minutes / 60.0

    def _render_chart(
        self, plan: PacePlan, start_hour: int, start_minute: int
    ) -> None:
        """Render the cutoff-vs-pace-plan chart using Altair.

        Purple line = when each aid station closes (the wall). Blue line =
        when you plan to arrive. Both appear in a line legend. The dots on
        the blue line are colored by how much cushion you have, in a separate
        cushion legend (red/amber/green). Two dashed horizontal lines mark
        the race time limit (purple) and your goal (blue). Hovering a station
        shows clock times and cushion, never raw decimals.
        """
        formatter = DisplayFormatters()
        point_data = []
        line_data = []
        for row in plan.rows:
            cutoff_hours = round(row.cutoff_minutes_from_start / 60.0, 2)
            target_hours = round(row.target_arrival_minutes_from_start / 60.0, 2)
            shared = {
                "Mile": row.mile,
                "Station": row.station_name,
                "CutoffClock": self._format_time_with_day(
                    row.cutoff_close_time,
                    row.cutoff_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "TargetClock": self._format_time_with_day(
                    row.target_arrival_time,
                    row.target_arrival_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "BufferLabel": self._format_buffer(row.buffer_minutes),
            }
            point_data.append(
                {
                    **shared,
                    "Target": target_hours,
                    "Cushion": formatter.buffer_category(row.buffer_minutes),
                }
            )
            line_data.append(
                {
                    **shared,
                    "Hours": cutoff_hours,
                    "Line": "Cutoff",
                    "Clock": shared["CutoffClock"],
                }
            )
            line_data.append(
                {
                    **shared,
                    "Hours": target_hours,
                    "Line": "Goal",
                    "Clock": shared["TargetClock"],
                }
            )

        total_cutoff_hours = round(
            plan.rows[-1].cutoff_minutes_from_start / 60.0, 2
        )
        station_tooltip = [
            alt.Tooltip("Station:N", title="Aid Station"),
            alt.Tooltip("CutoffClock:N", title="Cutoff closes"),
            alt.Tooltip("TargetClock:N", title="Your arrival"),
            alt.Tooltip("BufferLabel:N", title="Cutoff cushion"),
        ]
        line_tooltip = [
            alt.Tooltip("Station:N", title="Aid Station"),
            alt.Tooltip("Line:N", title="Line"),
            alt.Tooltip("Clock:N", title="Time"),
        ]

        line_scale = alt.Scale(
            domain=["Cutoff", "Goal"],
            range=["#7B1FA2", "#1565C0"],
        )
        lines = (
            alt.Chart(alt.Data(values=line_data))
            .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X("Mile:Q", title="Mile"),
                y=alt.Y("Hours:Q", title="Hours elapsed since race start"),
                color=alt.Color("Line:N", title="Times", scale=line_scale),
                tooltip=line_tooltip,
            )
        )

        cushion_scale = alt.Scale(
            domain=[
                "Tight (under 30m)",
                "Caution (30m-1h)",
                "Comfortable (over 1h)",
            ],
            range=["#C62828", "#F9A825", "#2E7D32"],
        )
        target_points = (
            alt.Chart(alt.Data(values=point_data))
            .mark_point(filled=True, size=95)
            .encode(
                x="Mile:Q",
                y="Target:Q",
                color=alt.Color("Cushion:N", title="Cutoff Cushion", scale=cushion_scale),
                tooltip=station_tooltip,
            )
        )

        limit_rule = (
            alt.Chart(alt.Data(values=[{"y": total_cutoff_hours}]))
            .mark_rule(color="#7B1FA2", strokeDash=[6, 4], strokeWidth=1.5)
            .encode(y="y:Q")
        )
        goal_rule = (
            alt.Chart(alt.Data(values=[{"y": round(plan.goal_hours, 2)}]))
            .mark_rule(color="#1565C0", strokeDash=[6, 4], strokeWidth=1.5)
            .encode(y="y:Q")
        )

        chart = (
            (limit_rule + goal_rule + lines + target_points)
            .resolve_scale(color="independent")
            .properties(
                height=380,
                title=alt.TitleParams(
                    text="Your Pace Plan vs the Cutoffs",
                    subtitle="Stay under the purple line. Blue is your plan.",
                    anchor="middle",
                ),
            )
            .configure_axis(grid=True, gridOpacity=0.4, gridColor="#5A7D2A")
        )
        st.altair_chart(chart, width="stretch")
        st.caption(
            "Hover a station for its cutoff, your arrival, and cushion. "
            "Dot color: red under 30 min, amber 30 min to 1 hour, green "
            "over 1 hour."
        )

    def _format_time(self, t: time) -> str:
        """Format a time of day as '6:15 AM'."""
        hour_12 = t.hour if 1 <= t.hour <= 12 else (t.hour - 12 if t.hour > 12 else 12)
        am_pm = "AM" if t.hour < 12 else "PM"
        return f"{hour_12}:{t.minute:02d} {am_pm}"

    def _format_time_with_day(
        self,
        t: time,
        minutes_from_start: float,
        start_hour: int,
        start_minute: int,
    ) -> str:
        """Format a time and add '(next day)' if the arrival has crossed midnight."""
        start_minutes_of_day = start_hour * 60 + start_minute
        total_clock_minutes = start_minutes_of_day + int(round(minutes_from_start))
        days_after_start = total_clock_minutes // (24 * 60)
        base = self._format_time(t)
        if days_after_start >= 1:
            return f"{base} (next day)"
        return base

    def _format_pace(self, minutes: float) -> str:
        """Format a pace in minutes-per-mile as 'MM:SS/mi'."""
        if minutes <= 0:
            return "—"
        whole = int(minutes)
        seconds = int(round((minutes - whole) * 60))
        if seconds == 60:
            whole += 1
            seconds = 0
        return f"{whole}:{seconds:02d}/mi"

    def _format_buffer(self, minutes: float) -> str:
        """Format a duration in minutes as 'Xh YYm' (with leading '-' if negative)."""
        sign = "-" if minutes < 0 else ""
        abs_min = abs(int(round(minutes)))
        h, m = divmod(abs_min, 60)
        return f"{sign}{h}h {m:02d}m"


PacePlannerPage().render()
