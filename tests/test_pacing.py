"""Tests for the pace plan computation."""

from __future__ import annotations

from datetime import time
from pathlib import Path

from vt100_data_hub.cutoffs import CutoffSchedule
from vt100_data_hub.pacing import PacePlan

CUTOFFS_2026_100M_PATH = (
    Path(__file__).parent.parent / "data" / "cutoffs_2026_100m.csv"
)


class TestPacePlan:
    """Tests for PacePlan against the 2026 100M cutoff schedule."""

    def _make_plan(self, goal_hours: float = 30.0) -> PacePlan:
        """Build a PacePlan for the 2026 100M with the given goal time."""
        schedule = CutoffSchedule(
            csv_path=CUTOFFS_2026_100M_PATH, distance="100M"
        )
        return PacePlan(
            schedule=schedule, goal_hours=goal_hours, start_time=time(4, 0)
        )

    def test_30_hour_goal_gives_18_minute_overall_pace(self) -> None:
        """A 30-hour goal at 100 miles = exactly 18 min/mile overall pace."""
        plan = self._make_plan(goal_hours=30.0)
        assert plan.pace_per_mile_minutes == 18.0

    def test_24_hour_goal_gives_faster_overall_pace(self) -> None:
        """A 24-hour goal at 100 miles = 14.4 min/mile overall pace."""
        plan = self._make_plan(goal_hours=24.0)
        assert plan.pace_per_mile_minutes == 14.4

    def test_finish_line_target_arrival_at_30_hour_goal(self) -> None:
        """At a 30-hour goal, finish line target arrival = 10:00 AM (next day)."""
        plan = self._make_plan(goal_hours=30.0)
        finish_row = plan.rows[-1]
        assert finish_row.station_name == "FINISH LINE"
        assert finish_row.target_arrival_minutes_from_start == 1800.0

    def test_30_hour_goal_yields_zero_buffer_at_finish(self) -> None:
        """At a 30-hour goal, the buffer at the finish line is zero."""
        plan = self._make_plan(goal_hours=30.0)
        finish_row = plan.rows[-1]
        assert finish_row.buffer_minutes == 0.0

    def test_faster_goal_yields_positive_buffer_at_finish(self) -> None:
        """A 24-hour goal leaves 6 hours of buffer at the finish."""
        plan = self._make_plan(goal_hours=24.0)
        finish_row = plan.rows[-1]
        assert finish_row.buffer_minutes == 360.0

    def test_cutoff_minutes_handle_midnight_rollover(self) -> None:
        """Camp 10 Bear (returning) closes 12:55 AM Sunday = 1255 min from start."""
        plan = self._make_plan(goal_hours=30.0)
        # Second Camp 10 Bear is at mile 69.7
        returning_camp = next(
            r for r in plan.rows if r.station_name == "Camp 10 Bear" and r.mile == 69.7
        )
        assert returning_camp.cutoff_minutes_from_start == 1255

    def test_your_section_pace_for_first_station_at_30_hour_goal(self) -> None:
        """At 30hr goal, Densmore Hill section pace = 135/7.4 (matches cutoff)."""
        plan = self._make_plan(goal_hours=30.0)
        first = plan.rows[0]
        assert first.station_name == "Densmore Hill"
        expected_pace = 135.0 / 7.4
        assert abs(first.your_section_pace_min_per_mile - expected_pace) < 0.01

    def test_your_section_pace_scales_with_goal(self) -> None:
        """At 24hr goal, section pace = 30hr-pace × (24/30) — proportionally faster."""
        plan_30 = self._make_plan(goal_hours=30.0)
        plan_24 = self._make_plan(goal_hours=24.0)
        first_30 = plan_30.rows[0]
        first_24 = plan_24.rows[0]
        expected_24 = first_30.your_section_pace_min_per_mile * (24.0 / 30.0)
        assert abs(first_24.your_section_pace_min_per_mile - expected_24) < 0.01

    def test_cutoff_window_for_first_station(self) -> None:
        """Densmore Hill cutoff window = 135 minutes (race start to 6:15 AM)."""
        plan = self._make_plan(goal_hours=30.0)
        first = plan.rows[0]
        assert first.cutoff_window_minutes == 135
