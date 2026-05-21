"""Data models for Vermont 100 race results."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from vt100_data_hub.duv_events import Distance

Status = Literal["FINISH", "DNF", "DNS"]
Gender = Literal["M", "F", "NB"]


class AidStationSplit:
    """One runner's split time at one named aid station.

    Attributes:
        station_name: The aid station name as it appears on DUV
            (e.g., "Camp 10 Bear", "Spirit of 76").
        elapsed_time: Time elapsed from race start to this station.
            None if the runner did not reach this station.
    """

    def __init__(
        self,
        station_name: str,
        elapsed_time: timedelta | None,
    ) -> None:
        self.station_name = station_name
        self.elapsed_time = elapsed_time


class RaceResult:
    """One runner's result for one edition of the Vermont 100.

    Attributes:
        year: The race year.
        distance: "100M" or "100K".
        runner_name: Surname, firstname as printed on DUV.
        status: FINISH, DNF, or DNS.
        rank_overall: Overall finishing place. None for DNF/DNS.
        finish_time: Total race time. None for DNF/DNS.
        duv_runner_id: DUV's stable runner ID across all events. None if absent.
        gender: M, F, or NB. None if not published.
        year_of_birth: Four-digit year. None if not published.
        nationality: Three-letter country code. None if not published.
        category: Age/gender category (e.g., "M40"). None if not published.
        rank_gender: Place within gender. None for DNF/DNS.
        rank_category: Place within age/gender category. None for DNF/DNS.
        club: Running club. None if not published.
        is_awd: True if Athletes With Disabilities division.
        splits: Ordered list of aid station splits. Empty if none published.
    """

    def __init__(
        self,
        year: int,
        distance: Distance,
        runner_name: str,
        status: Status,
        rank_overall: int | None = None,
        finish_time: timedelta | None = None,
        duv_runner_id: int | None = None,
        gender: Gender | None = None,
        year_of_birth: int | None = None,
        nationality: str | None = None,
        category: str | None = None,
        rank_gender: int | None = None,
        rank_category: int | None = None,
        club: str | None = None,
        is_awd: bool = False,
        splits: list[AidStationSplit] | None = None,
    ) -> None:
        self.year = year
        self.distance = distance
        self.runner_name = runner_name
        self.status = status
        self.rank_overall = rank_overall
        self.finish_time = finish_time
        self.duv_runner_id = duv_runner_id
        self.gender = gender
        self.year_of_birth = year_of_birth
        self.nationality = nationality
        self.category = category
        self.rank_gender = rank_gender
        self.rank_category = rank_category
        self.club = club
        self.is_awd = is_awd
        self.splits = splits if splits is not None else []