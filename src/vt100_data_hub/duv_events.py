"""DUV event ID lookup for Vermont 100 editions.

DUV (statistik.d-u-v.org) assigns each race a numeric event ID.
This module exposes a registry that maps (year, distance) pairs
to those IDs and supports the queries the race director needs,
including the last-N-editions window used for the 4-of-8 rule.
"""

from __future__ import annotations

from typing import Literal

Distance = Literal["100M", "100K"]


class UnknownEditionError(KeyError):
    """Raised when no DUV event ID is registered for a requested edition."""


class DUVEventRegistry:
    """Registry of DUV event IDs for Vermont 100 editions.

    Cancelled editions (2020, 2021 COVID; 2023 flooding) are deliberately
    absent from the registry so that the last-N-editions queries used by
    the race director count editions held, not calendar years.

    Attributes:
        event_ids: The (year, distance) -> DUV event ID mapping.
    """

    DEFAULT_EVENT_IDS: dict[tuple[int, Distance], int] = {
        # 100-mile event IDs
        (2015, "100M"): 25502,
        (2016, "100M"): 28015,
        (2017, "100M"): 35857,
        (2018, "100M"): 49457,
        (2019, "100M"): 58261,
        (2022, "100M"): 82819,
        (2024, "100M"): 110321,
        (2025, "100M"): 113387,
        # 100-km event IDs (sourced from DUV master page event=125333)
        (2015, "100K"): 25503,
        (2016, "100K"): 28016,
        (2017, "100K"): 35858,
        (2018, "100K"): 49458,
        (2019, "100K"): 58262,
        (2022, "100K"): 82820,
        (2024, "100K"): 110320,
        (2025, "100K"): 115430,
    }

    def __init__(
        self,
        event_ids: dict[tuple[int, Distance], int] | None = None,
    ) -> None:
        self.event_ids = (
            dict(event_ids) if event_ids is not None else dict(self.DEFAULT_EVENT_IDS)
        )

    def get_event_id(self, year: int, distance: Distance = "100M") -> int:
        """Return the DUV event ID for a given Vermont 100 edition.

        Args:
            year: The race year (e.g., 2024).
            distance: Either "100M" (default) or "100K".

        Returns:
            The DUV event ID as an integer.

        Raises:
            UnknownEditionError: If no event ID is registered for this edition.
        """
        try:
            return self.event_ids[(year, distance)]
        except KeyError as exc:
            raise UnknownEditionError(
                f"No DUV event ID for Vermont 100 {year} {distance}"
            ) from exc

    def available_editions(
        self, distance: Distance | None = None
    ) -> list[tuple[int, Distance]]:
        """Return all (year, distance) pairs in the registry, sorted oldest first.

        Args:
            distance: If provided, only return editions for this distance.

        Returns:
            A sorted list of available editions.
        """
        editions = list(self.event_ids.keys())
        if distance is not None:
            editions = [edition for edition in editions if edition[1] == distance]
        return sorted(editions)

    def last_n_editions(
        self, n: int, distance: Distance = "100M"
    ) -> list[tuple[int, Distance]]:
        """Return the most recent N editions held for a given distance.

        This is the building block for the 4-of-8 early-entry rule:
        call last_n_editions(8, "100M") to get the window over which
        the race director counts finishes.

        Args:
            n: Number of recent editions to return.
            distance: The distance to filter to.

        Returns:
            The N most recent editions for that distance, oldest first.

        Raises:
            ValueError: If n is not a positive integer.
        """
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        editions = self.available_editions(distance=distance)
        return editions[-n:]
