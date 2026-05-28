"""Vermont 100 Data Hub — Pace Planner page."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import streamlit as st

from vt100_data_hub.cutoffs import CutoffSchedule
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
            value="30h 00m",
            help="Target time to finish. Default 30h 00m is the official race cutoff.",
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

        table_data = [
            {
                "Aid Station": row.station_name,
                "Mile": row.mile,
                "Section Distance": round(row.section_distance_miles, 1),
                "Cutoff Close": self._format_time(row.cutoff_close_time),
                "Time Window": self._format_buffer(row.cutoff_window_minutes),
                "Your Pace": self._format_pace(
                    row.your_section_pace_min_per_mile
                ),
                "Your Target Arrival": self._format_time(row.target_arrival_time),
                "Buffer": self._format_buffer(row.buffer_minutes),
            }
            for row in plan.rows
        ]
        st.dataframe(table_data, hide_index=True, width="stretch")

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

    def _format_time(self, t: time) -> str:
        """Format a time of day as '6:15 AM'."""
        hour_12 = t.hour if 1 <= t.hour <= 12 else (t.hour - 12 if t.hour > 12 else 12)
        am_pm = "AM" if t.hour < 12 else "PM"
        return f"{hour_12}:{t.minute:02d} {am_pm}"

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
