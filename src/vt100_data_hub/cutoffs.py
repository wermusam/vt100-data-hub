"""Vermont 100 aid station cutoff schedules."""

from __future__ import annotations

import csv
from datetime import datetime, time
from pathlib import Path

from vt100_data_hub.duv_events import Distance


class AidStationCutoff:
    """One aid station's cutoff information.

    Attributes:
        station_number: Identifier in the course (e.g., "1", "9", "9a").
        name: Aid station name as published.
        mileage: Mile marker on the course.
        miles_to_next: Distance to the next aid station.
        opens_time: Time of day the station opens.
        closes_time: Time of day the station closes.
        station_type: Type code from the sheet (e.g., "AHDP", "U").
    """

    def __init__(
        self,
        station_number: str,
        name: str,
        mileage: float,
        miles_to_next: float,
        opens_time: time,
        closes_time: time,
        station_type: str,
    ) -> None:
        self.station_number = station_number
        self.name = name
        self.mileage = mileage
        self.miles_to_next = miles_to_next
        self.opens_time = opens_time
        self.closes_time = closes_time
        self.station_type = station_type


class CutoffSchedule:
    """The aid station cutoffs for one Vermont 100 race edition.

    Attributes:
        distance: "100M" or "100K".
        stations: List of AidStationCutoff objects in course order.
    """

    def __init__(self, csv_path: Path, distance: Distance) -> None:
        self.distance = distance
        self.stations = self._parse_csv(csv_path)

    def cutoff_minutes_from_start(self, start_time: time) -> list[int]:
        """Minutes from race start to each station's cutoff close.

        Handles the course crossing midnight: when a station's clock time is
        earlier than the previous station's, it is counted as the next day.
        The last value is the race's total cutoff window (e.g., 1800 minutes
        for the 100M's 4 AM start to 10 AM finish).

        Args:
            start_time: The race start time of day.

        Returns:
            One integer per station, in course order, giving minutes elapsed
            from the start to that station's cutoff close.
        """
        start_of_day = start_time.hour * 60 + start_time.minute
        minutes_from_start: list[int] = []
        last_minutes_of_day = start_of_day
        days_after_start = 0
        for station in self.stations:
            minutes_of_day = (
                station.closes_time.hour * 60 + station.closes_time.minute
            )
            if minutes_of_day < last_minutes_of_day:
                days_after_start += 1
            last_minutes_of_day = minutes_of_day
            minutes_from_start.append(
                minutes_of_day - start_of_day + days_after_start * 24 * 60
            )
        return minutes_from_start

    def _parse_csv(self, csv_path: Path) -> list[AidStationCutoff]:
        """Read the CSV (with VT100's 3-row header) into AidStationCutoff objects.

        Skips rows without a station_number — that filters out trailing
        legend/footer rows the sheet uses to explain the type codes.
        """
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        data_rows = [row for row in rows[3:] if row and row[0].strip()]
        return [self._parse_row(row) for row in data_rows]

    def _parse_row(self, row: list[str]) -> AidStationCutoff:
        """Convert one CSV row to an AidStationCutoff."""
        return AidStationCutoff(
            station_number=row[0].strip(),
            name=row[1].strip(),
            mileage=float(row[2]),
            miles_to_next=float(row[3]) if row[3].strip() else 0.0,
            opens_time=self._parse_time(row[4]),
            closes_time=self._parse_time(row[5]),
            station_type=row[6].strip(),
        )

    def _parse_time(self, text: str) -> time:
        """Convert '4:35 AM' to a datetime.time."""
        return datetime.strptime(text.strip(), "%I:%M %p").time()
