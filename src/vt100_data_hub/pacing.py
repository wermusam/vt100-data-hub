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
        target_arrival_minutes_from_start: Minutes elapsed from race start to target arrival.
        buffer_minutes: cutoff_minutes minus target_arrival_minutes (negative = miss cutoff).
        your_section_pace_min_per_mile: Pace this runner needs to maintain from
            previous station to this one at their goal time. Varies with goal_hours.
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
        self.buffer_minutes = buffer_minutes
        self.your_section_pace_min_per_mile = your_section_pace_min_per_mile


class PacePlan:
    """A pace plan for one Vermont 100 race attempt.

    Attributes:
        schedule: The CutoffSchedule of aid stations for the race.
        goal_hours: Target finish time in hours.
        start_time: Race start time (default 4:00 AM Saturday).
        race_distance_miles: Total race distance (from the last station's mileage).
        pace_per_mile_minutes: Required overall average pace, given goal_hours.
        rows: One StationPaceRow per aid station, in course order.
    """

    def __init__(
        self,
        schedule: CutoffSchedule,
        goal_hours: float,
        start_time: time = time(4, 0),
    ) -> None:
        self.schedule = schedule
        self.goal_hours = goal_hours
        self.start_time = start_time
        self.race_distance_miles = schedule.stations[-1].mileage  # last station = finish line
        self.pace_per_mile_minutes = (goal_hours * 60.0) / self.race_distance_miles
        self.rows = self._compute_rows()

    def _compute_rows(self) -> list[StationPaceRow]:
        """Walk every station and build the pace plan rows in course order.

        Target arrival uses cutoff-proportional scaling: at goal_hours equal
        to the total race cutoff, target arrival matches cutoff_close exactly
        (buffer = 0). At a faster goal, target arrival shifts earlier in
        proportion to (goal_hours / total_race_cutoff_hours).
        """
        start_minutes_of_day = self.start_time.hour * 60 + self.start_time.minute
        rows: list[StationPaceRow] = []
        prev_mile = 0.0
        prev_cutoff_minutes = 0
        last_minutes_of_day = start_minutes_of_day
        days_after_start = 0

        # First pass: compute cutoff_minutes_from_start for every station so
        # we know the total race cutoff window.
        cutoffs_from_start: list[int] = []
        for station in self.schedule.stations:
            cutoff_minutes_of_day = (
                station.closes_time.hour * 60 + station.closes_time.minute
            )
            if cutoff_minutes_of_day < last_minutes_of_day:
                days_after_start += 1
            last_minutes_of_day = cutoff_minutes_of_day
            cutoff_minutes_from_start = (
                cutoff_minutes_of_day - start_minutes_of_day
                + days_after_start * 24 * 60
            )
            cutoffs_from_start.append(cutoff_minutes_from_start)

        total_race_cutoff_minutes = cutoffs_from_start[-1]
        scale = (self.goal_hours * 60.0) / total_race_cutoff_minutes

        # Second pass: build rows using the cutoff-proportional target arrival.
        prev_target_minutes = 0.0
        for station, cutoff_minutes_from_start in zip(
            self.schedule.stations, cutoffs_from_start
        ):
            target_minutes_from_start = cutoff_minutes_from_start * scale
            target_arrival_time = self._minutes_to_time_of_day(
                start_minutes_of_day + target_minutes_from_start
            )

            buffer_minutes = cutoff_minutes_from_start - target_minutes_from_start

            section_distance = station.mileage - prev_mile
            cutoff_window_minutes = cutoff_minutes_from_start - prev_cutoff_minutes
            your_section_minutes = target_minutes_from_start - prev_target_minutes
            your_section_pace = (
                your_section_minutes / section_distance
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
                    target_arrival_time=target_arrival_time,
                    target_arrival_minutes_from_start=target_minutes_from_start,
                    buffer_minutes=buffer_minutes,
                    your_section_pace_min_per_mile=your_section_pace,
                )
            )

            prev_mile = station.mileage
            prev_cutoff_minutes = cutoff_minutes_from_start
            prev_target_minutes = target_minutes_from_start

        return rows

    def _minutes_to_time_of_day(self, total_minutes: float) -> time:
        """Convert minutes-since-midnight (possibly > 24*60) to a wall-clock time."""
        minute_of_day = int(round(total_minutes)) % (24 * 60)
        return time(minute_of_day // 60, minute_of_day % 60)
