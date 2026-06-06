"""Vermont 100 pace plan computation.

Given a cutoff schedule and a goal finish time, compute each aid station's
target arrival, buffer against the cutoff, and the minimum pace required
between consecutive stations.
"""

from __future__ import annotations

from datetime import time

from vt100_data_hub.cutoffs import CutoffSchedule


class StationPaceRow:
    """One row of a pace plan covering one aid station.

    Attributes:
        station_name: Aid station name.
        mile: Mile marker on the course.
        section_distance_miles: Miles from previous station (or from start).
        cutoff_close_time: Time of day the station closes.
        cutoff_minutes_from_start: Minutes elapsed from race start until cutoff close.
        cutoff_window_minutes: Minutes between previous cutoff and this cutoff
            (the time budget for this section).
        target_arrival_time: Clock time when the runner is expected to arrive.
        target_arrival_minutes_from_start: Minutes elapsed from race start to arrival.
        aid_minutes: Minutes the runner plans to spend at this station (0 at the
            finish line, where there is no stop).
        departure_time: Clock time when the runner leaves (arrival + aid_minutes).
        departure_minutes_from_start: Minutes elapsed from race start to departure.
        buffer_minutes: cutoff_minutes minus arrival_minutes. Measured to
            arrival because a runner makes a cutoff by arriving before it
            closes. Negative means the plan arrives after this cutoff.
        your_section_pace_min_per_mile: Moving pace (not counting aid-station
            time) the runner needs from the previous station to this one.
    """

    def __init__(
        self,
        station_name: str,
        mile: float,
        section_distance_miles: float,
        cutoff_close_time: time,
        cutoff_minutes_from_start: int,
        cutoff_window_minutes: int,
        target_arrival_time: time,
        target_arrival_minutes_from_start: float,
        aid_minutes: float,
        departure_time: time,
        departure_minutes_from_start: float,
        buffer_minutes: float,
        your_section_pace_min_per_mile: float,
    ) -> None:
        self.station_name = station_name
        self.mile = mile
        self.section_distance_miles = section_distance_miles
        self.cutoff_close_time = cutoff_close_time
        self.cutoff_minutes_from_start = cutoff_minutes_from_start
        self.cutoff_window_minutes = cutoff_window_minutes
        self.target_arrival_time = target_arrival_time
        self.target_arrival_minutes_from_start = target_arrival_minutes_from_start
        self.aid_minutes = aid_minutes
        self.departure_time = departure_time
        self.departure_minutes_from_start = departure_minutes_from_start
        self.buffer_minutes = buffer_minutes
        self.your_section_pace_min_per_mile = your_section_pace_min_per_mile


class PaceVerdict:
    """A plain-language verdict on whether a plan beats every cutoff.

    This is the one-glance answer a runner (or the race director) wants:
    does this plan make it, where is it tightest, and — if it fails — where
    does the day end. It is intentionally small so more fields can be added
    when the race director asks for more.

    Attributes:
        makes_it: True when every station's buffer is non-negative, i.e. the
            runner departs each aid station on or before its cutoff. A zero
            buffer still counts as making it.
        tightest_row: The StationPaceRow with the smallest buffer — the closest
            call. Shown even on a passing plan so the squeeze is visible.
        first_missed_row: The earliest StationPaceRow with a negative buffer,
            or None when the plan clears every cutoff. This is where a failing
            plan gets the runner pulled.
    """

    def __init__(
        self,
        makes_it: bool,
        tightest_row: StationPaceRow,
        first_missed_row: StationPaceRow | None,
    ) -> None:
        self.makes_it = makes_it
        self.tightest_row = tightest_row
        self.first_missed_row = first_missed_row


class PacePlan:
    """A pace plan for one Vermont 100 race attempt.

    The plan is built backward from the cutoffs. Each intermediate arrival is the
    station's cutoff clock scaled by the goal, so the finish (the endpoint) is
    reached at the goal and every intermediate is reached with a buffer. The
    baseline stop is absorbed into the leg paces, so a plan at the baseline stop
    never misses a cutoff. Only stop time above the baseline is additive: it
    shifts that station and the ones after it later, and can eat a buffer into a
    miss.

    Attributes:
        schedule: The CutoffSchedule of aid stations for the race.
        goal_hours: Your target finish time in hours, assuming the baseline stop
            at every station. Arrivals are scaled to it; a plan at the baseline
            stop finishes exactly here. Extra stop time pushes the finish later.
        start_time: Race start time (default 4:00 AM Saturday).
        aid_station_minutes: Uniform actual minutes at each stop, used only
            when aid_minutes_per_station is not given.
        aid_minutes_per_station: Optional actual per-station times (one value
            per station, in course order) for drop-bag and other custom stops.
        nominal_aid_minutes: The baseline stop absorbed into the leg paces
            (default 0.0). Stop time above this is additive and can cause a miss;
            below this pulls arrivals in.
        race_distance_miles: Total race distance (from the last station's mileage).
        pace_per_mile_minutes: Overall running pace (moving only), i.e. the goal
            less the baseline stops, spread over the distance.
        rows: One StationPaceRow per aid station, in course order.
    """

    def __init__(
        self,
        schedule: CutoffSchedule,
        goal_hours: float,
        start_time: time = time(4, 0),
        aid_station_minutes: float = 0.0,
        aid_minutes_per_station: list[float] | None = None,
        nominal_aid_minutes: float = 0.0,
    ) -> None:
        self.schedule = schedule
        self.goal_hours = goal_hours
        self.start_time = start_time
        self.aid_station_minutes = aid_station_minutes
        self.aid_minutes_per_station = aid_minutes_per_station
        self.nominal_aid_minutes = nominal_aid_minutes
        self.race_distance_miles = schedule.stations[-1].mileage  # last station = finish line
        # Overall running pace is the goal less the baseline stops (which are
        # absorbed into the legs), spread over the distance.
        moving_budget_minutes = goal_hours * 60.0 - nominal_aid_minutes * max(
            len(schedule.stations) - 1, 0
        )
        self.pace_per_mile_minutes = moving_budget_minutes / self.race_distance_miles
        self.rows = self._compute_rows()

    def verdict(self) -> PaceVerdict:
        """Summarize whether this plan clears every Vermont 100 cutoff.

        Buffers are measured to arrival, so a runner who arrives at a station
        exactly at its cutoff (zero buffer) still makes it.

        Returns:
            A PaceVerdict with the pass/fail flag, the tightest station, and
            the first missed cutoff (or None when every cutoff is cleared).
        """
        tightest_row = min(self.rows, key=lambda row: row.buffer_minutes)
        first_missed_row = next(
            (row for row in self.rows if row.buffer_minutes < 0), None
        )
        return PaceVerdict(
            makes_it=first_missed_row is None,
            tightest_row=tightest_row,
            first_missed_row=first_missed_row,
        )

    def _compute_rows(self) -> list[StationPaceRow]:
        """Walk every station and build the pace plan rows in course order.

        Arrivals are built backward from the cutoffs: each station's arrival is
        its cutoff clock scaled by goal/total, so the finish lands at the goal
        and every intermediate is reached with a buffer. The baseline stop is
        absorbed into the leg paces (so a baseline plan never misses); stop time
        above the baseline is additive, shifting this station and the ones after
        it later, and can eat a buffer into a miss. Cushion is measured to
        arrival, and each leg's pace is the running time from leaving the
        previous station to arriving at this one, over the leg's miles.
        """
        start_minutes_of_day = self.start_time.hour * 60 + self.start_time.minute
        rows: list[StationPaceRow] = []

        cutoffs_from_start = self.schedule.cutoff_minutes_from_start(self.start_time)
        total_race_cutoff_minutes = cutoffs_from_start[-1]

        # Per-station aid time: an explicit override list if given, else the
        # uniform value for every station. No stop at the finish line.
        station_count = len(self.schedule.stations)
        if self.aid_minutes_per_station is not None:
            aids = [float(minutes) for minutes in self.aid_minutes_per_station]
        else:
            aids = [self.aid_station_minutes] * station_count
        if aids:
            aids[-1] = 0.0

        # Scale the cutoff clock by the goal. At the 30h goal scale is 1.0 (you
        # ride the cutoffs); a faster goal pulls every arrival earlier.
        scale = (self.goal_hours * 60.0) / total_race_cutoff_minutes

        prev_mile = 0.0
        prev_cutoff_minutes = 0
        prev_departure_minutes = 0.0
        # Running total of stop time above the baseline; this is what shifts
        # later arrivals (the baseline itself is absorbed into the leg paces).
        extra_aid_before = 0.0
        for index, (station, cutoff_minutes_from_start) in enumerate(
            zip(self.schedule.stations, cutoffs_from_start)
        ):
            arrival_minutes = cutoff_minutes_from_start * scale + extra_aid_before
            aid_minutes = aids[index]
            departure_minutes = arrival_minutes + aid_minutes

            arrival_time = self._minutes_to_time_of_day(
                start_minutes_of_day + arrival_minutes
            )
            departure_time = self._minutes_to_time_of_day(
                start_minutes_of_day + departure_minutes
            )

            buffer_minutes = cutoff_minutes_from_start - arrival_minutes

            section_distance = station.mileage - prev_mile
            cutoff_window_minutes = cutoff_minutes_from_start - prev_cutoff_minutes
            section_moving_minutes = arrival_minutes - prev_departure_minutes
            your_section_pace = (
                section_moving_minutes / section_distance
                if section_distance > 0
                else 0.0
            )

            rows.append(
                StationPaceRow(
                    station_name=station.name,
                    mile=station.mileage,
                    section_distance_miles=section_distance,
                    cutoff_close_time=station.closes_time,
                    cutoff_minutes_from_start=cutoff_minutes_from_start,
                    cutoff_window_minutes=cutoff_window_minutes,
                    target_arrival_time=arrival_time,
                    target_arrival_minutes_from_start=arrival_minutes,
                    aid_minutes=aid_minutes,
                    departure_time=departure_time,
                    departure_minutes_from_start=departure_minutes,
                    buffer_minutes=buffer_minutes,
                    your_section_pace_min_per_mile=your_section_pace,
                )
            )

            prev_mile = station.mileage
            prev_cutoff_minutes = cutoff_minutes_from_start
            prev_departure_minutes = departure_minutes
            extra_aid_before += aid_minutes - self.nominal_aid_minutes

        return rows

    def _minutes_to_time_of_day(self, total_minutes: float) -> time:
        """Convert minutes-since-midnight (possibly > 24*60) to a wall-clock time."""
        minute_of_day = int(round(total_minutes)) % (24 * 60)
        return time(minute_of_day // 60, minute_of_day % 60)

    @staticmethod
    def goal_minutes_from_running(
        running_minutes: float, stop_minutes: list[float]
    ) -> float:
        """Total goal time = running time plus every aid-station stop.

        This is the forward direction of the planner's core identity:
        goal = running + stops. Editing a stop holds the running time and
        moves the goal by the change, so a longer rest pushes the finish later.

        Args:
            running_minutes: Pure moving time over the whole course, in minutes.
            stop_minutes: Time spent at each aid station, in minutes.

        Returns:
            The total goal finish time in minutes.
        """
        return running_minutes + sum(stop_minutes)

    @staticmethod
    def running_minutes_from_goal(
        goal_minutes: float, stop_minutes: list[float]
    ) -> float:
        """Running time left once every aid-station stop is taken out of the goal.

        This is the inverse of :meth:`goal_minutes_from_running`, used when the
        runner drags the goal slider: the new goal is fixed and the stops are
        held, so the running time (and therefore the pace) is what gives.

        Args:
            goal_minutes: Target total finish time, in minutes.
            stop_minutes: Time spent at each aid station, in minutes.

        Returns:
            The moving time the runner has left, in minutes.

        Raises:
            ValueError: If the stops meet or exceed the goal, leaving no time
                to actually run — an impossible plan.
        """
        running_minutes = goal_minutes - sum(stop_minutes)
        if running_minutes <= 0:
            raise ValueError(
                "Aid-station stops meet or exceed the goal time; "
                "no time left to run."
            )
        return running_minutes

    @staticmethod
    def stop_minutes_with_no_finish_stop(minutes: list[float]) -> list[float]:
        """Normalize per-station stop minutes for use as a plan input.

        Coerces every value to a float and zeroes the finish line (the last
        station), since the finish never has a stop. This is what the table's
        edited values and the reset-to-average control pass back in.

        Args:
            minutes: One stop time per station, in course order.

        Returns:
            A new list of floats with the last entry set to 0.0 (the input is
            returned unchanged when empty).
        """
        times = [float(value) for value in minutes]
        if times:
            times[-1] = 0.0
        return times
