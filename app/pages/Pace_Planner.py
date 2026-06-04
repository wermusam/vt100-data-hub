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
        st.subheader("Responsible Pace Chart")
        st.markdown(
            "Set your goal finish time. The table shows the required pace "
            "between each aid station to hit every cutoff, your target "
            "arrival, and the buffer you'd have at each station."
        )

        formatter = DisplayFormatters()
        goal_options = [
            formatter.format_hours(total_minutes / 60.0)
            for total_minutes in range(15 * 60, 30 * 60 + 1, 15)
        ]
        goal_label = st.select_slider(
            "Goal finish time",
            options=goal_options,
            value="28h 00m",
            help="Target time to finish. The official race cutoff is 30h 00m.",
        )
        goal_hours = formatter.parse_hm_label(goal_label)

        st.sidebar.header("Your Race")
        distance = st.sidebar.radio(
            "Distance", options=["100M", "100K"], index=0
        )
        # VT100 start times are fixed by the race: 4:00 AM for the 100M,
        # 9:00 AM for the 100K (vermont100.com/race-details).
        start_hour, start_minute = (4, 0) if distance == "100M" else (9, 0)

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
            f"**Goal:** {formatter.format_hours(goal_hours)} &nbsp;|&nbsp; "
            f"**Required overall pace:** {formatter.format_pace(plan.pace_per_mile_minutes)} &nbsp;|&nbsp; "
            f"**Expected finish:** {formatter.format_clock_time(finish_row.target_arrival_time)}"
        )
        st.markdown(
            f"**Tightest buffer:** {tightest.station_name} at mile {tightest.mile}, "
            f"{formatter.format_duration(tightest.buffer_minutes)}"
        )

        self._render_chart(plan, start_hour, start_minute)

        table_data = [
            {
                "Aid Station": row.station_name,
                "Mile": row.mile,
                "Section Distance": round(row.section_distance_miles, 1),
                "Cutoff Close": formatter.format_clock_time_with_day(
                    row.cutoff_close_time,
                    row.cutoff_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Time Window": formatter.format_duration(row.cutoff_window_minutes),
                "Your Pace": formatter.format_pace(
                    row.your_section_pace_min_per_mile
                ),
                "Your Target Arrival": formatter.format_clock_time_with_day(
                    row.target_arrival_time,
                    row.target_arrival_minutes_from_start,
                    start_hour,
                    start_minute,
                ),
                "Buffer": formatter.format_duration(row.buffer_minutes),
            }
            for row in plan.rows
        ]
        st.dataframe(
            table_data,
            hide_index=True,
            width="stretch",
            column_config={
                "Mile": st.column_config.NumberColumn(format="%.1f"),
                "Section Distance": st.column_config.NumberColumn(format="%.1f"),
            },
        )

        st.divider()

    def _render_chart(
        self, plan: PacePlan, start_hour: int, start_minute: int
    ) -> None:
        """Render the cutoff-vs-pace-plan chart with Plotly.

        Purple line = when each aid station closes (the wall). Blue line =
        when you plan to arrive. The dots on the blue line are colored by how
        much cushion you have before each cutoff (red/amber/green). Two dashed
        horizontal lines mark the race time limit (purple) and your goal
        (blue). Drag a box to zoom, double-click to reset; hovering a station
        shows clock times and cushion.
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

        # Goal line (blue): fills the cushion band down to the cutoff line
        # above it. The cushion dots carry the hover detail.
        figure.add_trace(
            go.Scatter(
                x=miles,
                y=target_hours,
                mode="lines",
                name="Goal",
                legendgroup="times",
                line={"color": "#1565C0", "width": 2.5},
                fill="tonexty",
                fillcolor="rgba(46,125,50,0.12)",
                hoverinfo="skip",
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
            ys = [target_hours[i] for i in indices]
            custom = [
                [names[i], cutoff_clocks[i], target_clocks[i], buffers[i]]
                for i in indices
            ]
            figure.add_trace(
                go.Scatter(
                    x=xs or [None],
                    y=ys or [None],
                    mode="markers",
                    name=category,
                    legendgroup="cushion",
                    legendgrouptitle_text="Cutoff Cushion",
                    marker={
                        "color": color,
                        "size": 10,
                        "line": {"color": "white", "width": 1},
                    },
                    customdata=custom or [[None, None, None, None]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Cutoff closes: %{customdata[1]}<br>"
                        "Your arrival: %{customdata[2]}<br>"
                        "Cutoff cushion: %{customdata[3]}<extra></extra>"
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
            y=round(tightest.target_arrival_minutes_from_start / 60.0, 2),
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
            "Drag a box to zoom in; double-click to reset. Hover a station "
            "for its cutoff, your arrival, and cushion. Dot color: red under "
            "30 min, amber 30 min to 1 hour, green over 1 hour."
        )


PacePlannerPage().render()
