"""Tests for the pace plan computation."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

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

    def test_section_paces_are_not_uniform(self) -> None:
        """The plan paces each section to its own cutoff window, so the
        required pace changes station to station — it is not one flat pace
        for the whole race ('you go from pace to pace')."""
        plan = self._make_plan(goal_hours=30.0)
        paces = [
            round(row.your_section_pace_min_per_mile, 2)
            for row in plan.rows
            if row.section_distance_miles > 0
        ]
        # More than one distinct section pace: the course is genuinely
        # paced unevenly, not at a single average.
        assert len(set(paces)) > 1
        # At a 30-hour goal the moving budget equals the cutoff window exactly,
        # so each section's pace is its cutoff window divided by its distance.
        first = plan.rows[0]
        expected = first.cutoff_window_minutes / first.section_distance_miles
        assert abs(first.your_section_pace_min_per_mile - expected) < 0.01


class TestPacePlanWithAidStationTime:
    """Aid-station time on top of the goal.

    The goal is your total finish at the average stop time, so a default plan
    finishes exactly at the goal. Editing one stop beyond the average adds to
    the total and shifts only the stations after it; changing the goal re-paces
    the running and leaves the stop times alone.
    """

    def _make_plan(self, goal_hours: float, aid_minutes: float) -> PacePlan:
        """Build a 2026 100M plan with a uniform average stop time."""
        schedule = CutoffSchedule(
            csv_path=CUTOFFS_2026_100M_PATH, distance="100M"
        )
        return PacePlan(
            schedule=schedule,
            goal_hours=goal_hours,
            start_time=time(4, 0),
            aid_station_minutes=aid_minutes,
            nominal_aid_minutes=3.0,
        )

    def _edited_plan(
        self, edit_index: int, minutes: float
    ) -> tuple[PacePlan, PacePlan]:
        """Return (baseline, edited) 28h plans with a 3-min average.

        `edited` sets the stop at `edit_index` to `minutes`; everything else
        stays at the 3-min average.
        """
        schedule = CutoffSchedule(
            csv_path=CUTOFFS_2026_100M_PATH, distance="100M"
        )
        n = len(schedule.stations)
        base_times = [3.0] * n
        base_times[-1] = 0.0
        baseline = PacePlan(
            schedule=schedule,
            goal_hours=28.0,
            start_time=time(4, 0),
            aid_station_minutes=3.0,
            aid_minutes_per_station=base_times,
            nominal_aid_minutes=3.0,
        )
        edited_times = list(base_times)
        edited_times[edit_index] = minutes
        edited = PacePlan(
            schedule=schedule,
            goal_hours=28.0,
            start_time=time(4, 0),
            aid_station_minutes=3.0,
            aid_minutes_per_station=edited_times,
            nominal_aid_minutes=3.0,
        )
        return baseline, edited

    def test_default_plan_finishes_at_the_goal(self) -> None:
        """28h with a uniform 3-min average finishes exactly at 28h (1680)."""
        plan = self._make_plan(goal_hours=28.0, aid_minutes=3.0)
        assert sum(row.aid_minutes for row in plan.rows) == 75.0
        assert plan.rows[-1].target_arrival_minutes_from_start == 1680.0

    def test_fewer_stops_than_nominal_finishes_early(self) -> None:
        """No stops is 3 min under the nominal at all 25 stations, so the
        finish lands 75 minutes early (1605 instead of 1680)."""
        plan = self._make_plan(goal_hours=28.0, aid_minutes=0.0)
        assert plan.rows[-1].target_arrival_minutes_from_start == 1605.0

    def test_raising_the_average_adds_to_the_total(self) -> None:
        """Raising the average is like editing every stop: 3 to 4 over 25
        stations adds 25 minutes, and the running pace does not change."""
        plan_3 = self._make_plan(goal_hours=28.0, aid_minutes=3.0)
        plan_4 = self._make_plan(goal_hours=28.0, aid_minutes=4.0)
        assert plan_3.rows[-1].target_arrival_minutes_from_start == 1680.0
        assert plan_4.rows[-1].target_arrival_minutes_from_start == 1705.0
        assert (
            plan_4.rows[0].your_section_pace_min_per_mile
            == plan_3.rows[0].your_section_pace_min_per_mile
        )

    def test_finish_line_has_no_stop(self) -> None:
        """No aid-station time is spent at the finish line."""
        plan = self._make_plan(goal_hours=28.0, aid_minutes=3.0)
        assert plan.rows[-1].aid_minutes == 0.0

    def test_departure_is_arrival_plus_aid(self) -> None:
        """An intermediate station departs aid_minutes after arrival."""
        plan = self._make_plan(goal_hours=28.0, aid_minutes=3.0)
        first = plan.rows[0]
        assert first.aid_minutes == 3.0
        assert (
            first.departure_minutes_from_start
            == first.target_arrival_minutes_from_start + 3.0
        )

    def test_zero_aid_leaves_departure_equal_to_arrival(self) -> None:
        """With no aid time, departure equals arrival at every station."""
        plan = self._make_plan(goal_hours=28.0, aid_minutes=0.0)
        for row in plan.rows:
            assert (
                row.departure_minutes_from_start
                == row.target_arrival_minutes_from_start
            )

    def test_editing_one_stop_adds_one_minute_to_the_total(self) -> None:
        """Bumping a 3-min stop to 4 makes the finish one minute later."""
        baseline, edited = self._edited_plan(edit_index=5, minutes=4.0)
        assert baseline.rows[-1].target_arrival_minutes_from_start == 1680.0
        assert edited.rows[-1].target_arrival_minutes_from_start == 1681.0

    def test_drop_bag_adds_only_the_extra_over_the_average(self) -> None:
        """A 20-min drop bag over a 3-min average adds 17 to the total."""
        _baseline, edited = self._edited_plan(edit_index=5, minutes=20.0)
        assert edited.rows[-1].target_arrival_minutes_from_start == 1680.0 + 17.0

    def test_editing_shifts_only_the_stations_after_it(self) -> None:
        """A longer stop leaves earlier stations unchanged and shifts the later
        ones by exactly the added minutes."""
        baseline, edited = self._edited_plan(edit_index=5, minutes=33.0)
        # 33 minus the 3-min average = 30 minutes added.
        assert (
            edited.rows[3].target_arrival_minutes_from_start
            == baseline.rows[3].target_arrival_minutes_from_start
        )
        assert (
            edited.rows[6].target_arrival_minutes_from_start
            == baseline.rows[6].target_arrival_minutes_from_start + 30.0
        )

    def test_goal_change_repaces_running_and_keeps_stop_times(self) -> None:
        """Changing only the goal keeps each stop's minutes and re-paces the
        running, so each plan finishes at its own goal."""
        plan_28 = self._make_plan(goal_hours=28.0, aid_minutes=3.0)
        plan_29 = self._make_plan(goal_hours=29.0, aid_minutes=3.0)
        assert plan_28.rows[-1].target_arrival_minutes_from_start == 1680.0
        assert plan_29.rows[-1].target_arrival_minutes_from_start == 1740.0
        for r28, r29 in zip(plan_28.rows, plan_29.rows):
            assert r28.aid_minutes == r29.aid_minutes
        assert (
            plan_29.rows[0].your_section_pace_min_per_mile
            > plan_28.rows[0].your_section_pace_min_per_mile
        )

    def test_goal_change_keeps_your_edits(self) -> None:
        """Moving the goal after editing a stop keeps that edit and its extra:
        a 20-min drop bag adds 17 minutes at any goal."""
        schedule = CutoffSchedule(
            csv_path=CUTOFFS_2026_100M_PATH, distance="100M"
        )
        n = len(schedule.stations)
        times = [3.0] * n
        times[-1] = 0.0
        times[5] = 20.0
        plan_28 = PacePlan(
            schedule=schedule,
            goal_hours=28.0,
            start_time=time(4, 0),
            aid_minutes_per_station=times,
            nominal_aid_minutes=3.0,
        )
        plan_29 = PacePlan(
            schedule=schedule,
            goal_hours=29.0,
            start_time=time(4, 0),
            aid_minutes_per_station=times,
            nominal_aid_minutes=3.0,
        )
        assert plan_28.rows[-1].target_arrival_minutes_from_start == 1680.0 + 17.0
        assert plan_29.rows[-1].target_arrival_minutes_from_start == 1740.0 + 17.0
        for r28, r29 in zip(plan_28.rows, plan_29.rows):
            assert r28.aid_minutes == r29.aid_minutes

    def test_goal_is_running_plus_stops(self) -> None:
        """Goal time is simply running time plus every aid-station stop."""
        assert PacePlan.goal_minutes_from_running(1500.0, [5.0, 5.0, 20.0]) == 1530.0

    def test_running_is_goal_minus_stops(self) -> None:
        """Dragging the goal holds the stops, so running time is the remainder."""
        assert PacePlan.running_minutes_from_goal(1680.0, [5.0] * 24) == 1560.0

    def test_goal_and_running_are_inverses(self) -> None:
        """Solving running from a goal and rebuilding the goal returns the goal."""
        stops = [5.0, 5.0, 30.0, 0.0]
        running = PacePlan.running_minutes_from_goal(1700.0, stops)
        assert PacePlan.goal_minutes_from_running(running, stops) == 1700.0

    def test_running_from_goal_rejects_impossible_plan(self) -> None:
        """Stops that eat the whole goal leave no time to run, which is invalid."""
        with pytest.raises(ValueError):
            PacePlan.running_minutes_from_goal(60.0, [40.0, 30.0])

    def test_finish_stop_is_zeroed_when_reading_stop_times(self) -> None:
        """A value on the finish row is dropped to zero; ints become floats."""
        assert PacePlan.stop_minutes_with_no_finish_stop([3, 4, 9]) == [
            3.0,
            4.0,
            0.0,
        ]

    def test_modifying_a_table_time_flows_into_the_plan(self) -> None:
        """Typing 20 at one stop, read back the way the page does it, lands that
        stop at 20 and pushes the finish 17 minutes later."""
        schedule = CutoffSchedule(
            csv_path=CUTOFFS_2026_100M_PATH, distance="100M"
        )
        n = len(schedule.stations)
        editor_rows = [{"Time at Station (min)": 3.0} for _ in range(n)]
        editor_rows[5]["Time at Station (min)"] = 20.0
        times = PacePlan.stop_minutes_with_no_finish_stop(
            [row["Time at Station (min)"] for row in editor_rows]
        )
        assert times[-1] == 0.0
        plan = PacePlan(
            schedule=schedule,
            goal_hours=28.0,
            start_time=time(4, 0),
            aid_minutes_per_station=times,
            nominal_aid_minutes=3.0,
        )
        assert plan.rows[5].aid_minutes == 20.0
        assert plan.rows[-1].target_arrival_minutes_from_start == 1680.0 + 17.0
