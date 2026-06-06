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
        buffer_minutes: cutoff_minutes minus departure_minutes. Measured to
            departure because the runner must leave by the cutoff. Negative
            means the plan misses this cutoff.
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


class PacePlan:
    """A pace plan for one Vermont 100 race attempt.

    Attributes:
        schedule: The CutoffSchedule of aid stations for the race.
        goal_hours: Your total finish time in hours, measured at the nominal
            stop time. The moving pace is solved against that fixed allowance,
            so a plan with every stop at the nominal finishes at the goal.
        start_time: Race start time (default 4:00 AM Saturday).
        aid_station_minutes: Uniform actual minutes at each stop, used only
            when aid_minutes_per_station is not given.
        aid_minutes_per_station: Optional actual per-station times (one value
            per station, in course order) for drop-bag and other custom stops.
        nominal_aid_minutes: The assumed stop time the goal is measured against
            (default 0.0, so the goal is pure running time). The app sets it to
            its nominal stop time, so actual stop time above or below the
            nominal adds to or trims from the finish without re-pacing.
        race_distance_miles: Total race distance (from the last station's mileage).
        pace_per_mile_minutes: Required overall average pace, given goal_hours.
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
        self.pace_per_mile_minutes = (goal_hours * 60.0) / self.race_distance_miles
        self.rows = self._compute_rows()

    def _compute_rows(self) -> list[StationPaceRow]:
        """Walk every station and build the pace plan rows in course order.

        The goal time is your total finish assuming the nominal stop time:
        that fixed allowance is carved out of the goal and the remaining moving
        budget is spread across the course in proportion to the cutoffs. Actual
        stop time above or below the nominal (a longer average or one big stop)
        adds to or trims from the finish instead of being absorbed, and shifts
        only the stations after it. Cushion is measured to departure.
        """
        start_minutes_of_day = self.start_time.hour * 60 + self.start_time.minute
        rows: list[StationPaceRow] = []

        cutoffs_from_start = self.schedule.cutoff_minutes_from_start(self.start_time)
        total_race_cutoff_minutes = cutoffs_from_start[-1]

        # Per-station aid time: an explicit override list if given, else the
        # uniform average for every station. No stop at the finish line.
        station_count = len(self.schedule.stations)
        if self.aid_minutes_per_station is not None:
            aids = [float(minutes) for minutes in self.aid_minutes_per_station]
        else:
            aids = [self.aid_station_minutes] * station_count
        if aids:
            aids[-1] = 0.0
        # The goal is your total finish assuming the NOMINAL stop time at every
        # station. That fixed allowance is folded into the goal and sets the
        # moving pace. Any actual stop time above or below the nominal is not
        # absorbed by the pace; it adds to (or trims from) the finish and shifts
        # the stations after it. Raising the average or one stop pushes the
        # finish later; the goal slider re-solves the pace and leaves stops be.
        baseline_aid_minutes = self.nominal_aid_minutes * max(station_count - 1, 0)
        moving_scale = (
            self.goal_hours * 60.0 - baseline_aid_minutes
        ) / total_race_cutoff_minutes

        prev_mile = 0.0
        prev_cutoff_minutes = 0
        prev_moving_minutes = 0.0
        aid_before = 0.0
        for index, (station, cutoff_minutes_from_start) in enumerate(
            zip(self.schedule.stations, cutoffs_from_start)
        ):
            moving_minutes = cutoff_minutes_from_start * moving_scale
            arrival_minutes = moving_minutes + aid_before
            aid_minutes = aids[index]
            departure_minutes = arrival_minutes + aid_minutes

            arrival_time = self._minutes_to_time_of_day(
                start_minutes_of_day + arrival_minutes
            )
            departure_time = self._minutes_to_time_of_day(
                start_minutes_of_day + departure_minutes
            )

            buffer_minutes = cutoff_minutes_from_start - departure_minutes

            section_distance = station.mileage - prev_mile
            cutoff_window_minutes = cutoff_minutes_from_start - prev_cutoff_minutes
            section_moving_minutes = moving_minutes - prev_moving_minutes
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
            prev_moving_minutes = moving_minutes
            aid_before += aid_minutes

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
