"""Vermont 100 data-hub queries against the race_results table."""

from __future__ import annotations

import logging
import sqlite3

from vt100_data_hub.duv_events import Distance, DUVEventRegistry

logger = logging.getLogger(__name__)


class RunnerQueries:
    """Runner-history queries against the race_results table.

    Attributes:
        connection: A SQLite connection to a populated race_results table.
        registry: A DUVEventRegistry used for year-window lookups.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        registry: DUVEventRegistry,
    ) -> None:
        self.connection = connection
        self.registry = registry

    def runners_with_n_finishes(
        self,
        n: int = 4,
        distance: Distance = "100M",
        last_n_editions: int = 8,
    ) -> list[tuple[str, int, int]]:
        """Return runners with at least n finishes in the last N editions held.

        This is the building block for the 4-of-8 early-entry rule the race
        director uses each year.

        Args:
            n: Minimum number of finishes required (default 4).
            distance: "100M" or "100K" (default "100M").
            last_n_editions: How many recent editions to count over (default 8).

        Returns:
            A list of (runner_name, finish_count, latest_year) tuples,
            sorted by finish_count desc, then latest_year desc, then name.
            Runners without a DUV runner ID are excluded — we cannot reliably
            group them across years without a stable identifier.
        """
        years = [
            year
            for year, _ in self.registry.last_n_editions(last_n_editions, distance)
        ]
        placeholders = ",".join(["?"] * len(years))
        sql = f"""
            SELECT
                runner_name,
                COUNT(DISTINCT year) AS finish_count,
                MAX(year) AS latest_year
            FROM race_results
            WHERE distance = ?
              AND year IN ({placeholders})
              AND duv_runner_id IS NOT NULL
            GROUP BY duv_runner_id
            HAVING COUNT(DISTINCT year) >= ?
            ORDER BY finish_count DESC, latest_year DESC, runner_name
        """
        cursor = self.connection.execute(sql, [distance, *years, n])
        return cursor.fetchall()
