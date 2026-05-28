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
    ) -> list[tuple[str, int, int, str]]:
        """Return runners with at least n finishes in the last N editions held.

        This is the building block for the 4-of-8 early-entry rule the race
        director uses each year.

        Args:
            n: Minimum number of finishes required (default 4).
            distance: "100M" or "100K" (default "100M").
            last_n_editions: How many recent editions to count over (default 8).

        Returns:
            A list of (runner_name, finish_count, latest_year, years_string)
            tuples, sorted by finish_count desc, then latest_year desc, then
            name. years_string is a comma-separated list of every year the
            runner finished (e.g., "2015,2016,2018").
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
                MAX(year) AS latest_year,
                GROUP_CONCAT(DISTINCT year) AS years_string
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

    def runners_who_did_both_distances(
        self,
    ) -> list[tuple[str, int, int, str, str, int]]:
        """Return runners who have finished both 100M and 100K editions.

        Counts every edition we have data for — not bounded by a window.
        A "crossover" runner is one who has at least one finish in each
        distance.

        Returns:
            A list of (runner_name, finishes_100m, finishes_100k,
            years_100m, years_100k, latest_year) tuples, sorted by total
            finishes desc, then runner_name. years_100m and years_100k
            are comma-separated strings of years (e.g., "2015,2018,2022").
            latest_year is the most recent year the runner finished either
            distance. Runners without a DUV runner ID are excluded.
        """
        sql = """
            SELECT
                runner_name,
                COUNT(DISTINCT CASE WHEN distance = '100M' THEN year END)
                    AS finishes_100m,
                COUNT(DISTINCT CASE WHEN distance = '100K' THEN year END)
                    AS finishes_100k,
                GROUP_CONCAT(DISTINCT CASE WHEN distance = '100M' THEN year END)
                    AS years_100m,
                GROUP_CONCAT(DISTINCT CASE WHEN distance = '100K' THEN year END)
                    AS years_100k,
                MAX(year) AS latest_year
            FROM race_results
            WHERE duv_runner_id IS NOT NULL
            GROUP BY duv_runner_id
            HAVING finishes_100m >= 1 AND finishes_100k >= 1
            ORDER BY (finishes_100m + finishes_100k) DESC, runner_name
        """
        cursor = self.connection.execute(sql)
        return cursor.fetchall()
