"""Tests for the aid station cutoff loader."""

from __future__ import annotations

from datetime import time
from pathlib import Path

from vt100_data_hub.cutoffs import CutoffSchedule

CUTOFFS_2026_100M_PATH = (
    Path(__file__).parent.parent / "data" / "cutoffs_2026_100m.csv"
)


class TestCutoffSchedule:
    """Tests for CutoffSchedule loading from the 2026 100M CSV."""

    def _load_2026_100m(self) -> CutoffSchedule:
        """Load the saved 2026 100M cutoff schedule."""
        return CutoffSchedule(csv_path=CUTOFFS_2026_100M_PATH, distance="100M")

    def test_loads_twenty_six_stations(self) -> None:
        """The 2026 100M CSV should yield 26 aid stations."""
        schedule = self._load_2026_100m()
        assert len(schedule.stations) == 26

    def test_first_station_is_densmore_hill(self) -> None:
        """First station should be Densmore Hill at mile 7.4."""
        schedule = self._load_2026_100m()
        first = schedule.stations[0]
        assert first.name == "Densmore Hill"
        assert first.mileage == 7.4

    def test_parses_opens_and_closes_times(self) -> None:
        """Densmore Hill opens 4:35 AM and closes 6:15 AM."""
        schedule = self._load_2026_100m()
        densmore = schedule.stations[0]
        assert densmore.opens_time == time(4, 35)
        assert densmore.closes_time == time(6, 15)

    def test_camp_10_bear_appears_twice(self) -> None:
        """Runners hit Camp 10 Bear twice (outbound at 47.6, returning at 69.7)."""
        schedule = self._load_2026_100m()
        camp_10_bears = [s for s in schedule.stations if s.name == "Camp 10 Bear"]
        assert len(camp_10_bears) == 2

    def test_finish_line_is_at_mile_100(self) -> None:
        """The last station is FINISH LINE at mile 100."""
        schedule = self._load_2026_100m()
        last = schedule.stations[-1]
        assert last.name == "FINISH LINE"
        assert last.mileage == 100.0


class TestCutoffMinutesFromStart:
    """Tests for CutoffSchedule.cutoff_minutes_from_start."""

    def _load_2026_100m(self) -> CutoffSchedule:
        """Load the saved 2026 100M cutoff schedule."""
        return CutoffSchedule(csv_path=CUTOFFS_2026_100M_PATH, distance="100M")

    def test_first_station_window(self) -> None:
        """Densmore Hill closes 6:15 AM = 135 minutes from a 4 AM start."""
        schedule = self._load_2026_100m()
        minutes = schedule.cutoff_minutes_from_start(time(4, 0))
        assert minutes[0] == 135

    def test_finish_is_30_hours_from_4am_start(self) -> None:
        """The 100M finish (10 AM Sunday) is 1800 minutes from a 4 AM start."""
        schedule = self._load_2026_100m()
        minutes = schedule.cutoff_minutes_from_start(time(4, 0))
        assert minutes[-1] == 1800

    def test_handles_midnight_rollover(self) -> None:
        """Camp 10 Bear returning closes 12:55 AM (next day) = 1255 minutes."""
        schedule = self._load_2026_100m()
        minutes = schedule.cutoff_minutes_from_start(time(4, 0))
        returning_index = next(
            i
            for i, station in enumerate(schedule.stations)
            if station.name == "Camp 10 Bear" and station.mileage == 69.7
        )
        assert minutes[returning_index] == 1255
