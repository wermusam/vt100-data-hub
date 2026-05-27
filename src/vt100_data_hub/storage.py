"""Persist Vermont 100 race results in a SQLite database.

The storage layer caches parsed DUV results so the data hub can
answer queries without re-parsing HTML on every request.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import timedelta

from vt100_data_hub.race_result import RaceResult

logger = logging.getLogger(__name__)


class ResultStorage:
    """Persist Vermont 100 race results in a SQLite database.

    Attributes:
        connection: A SQLite connection holding the race_results table.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_schema(self) -> None:
        """Create the race_results table if it does not already exist.

        The table mirrors the fields on RaceResult, with finish_time
        stored as integer seconds (SQLite has no timedelta type).
        """
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS race_results (
                id INTEGER PRIMARY KEY,
                year INTEGER NOT NULL,
                distance TEXT NOT NULL,
                runner_name TEXT NOT NULL,
                status TEXT NOT NULL,
                rank_overall INTEGER,
                finish_time_seconds INTEGER,
                duv_runner_id INTEGER,
                gender TEXT,
                year_of_birth INTEGER,
                nationality TEXT,
                category TEXT,
                rank_gender INTEGER,
                rank_category INTEGER
            )
            """
        )
        self.connection.commit()
        logger.info("Created race_results table")

    def save_result(self, result: RaceResult) -> None:
        """Insert one RaceResult and commit immediately.

        Args:
            result: A RaceResult to insert.
        """
        self._insert_result(result)
        self.connection.commit()

    def save_results(self, results: list[RaceResult]) -> None:
        """Insert many RaceResults in a single transaction.

        Inserts every row without committing in between, then commits
        once at the end. Much faster than calling save_result in a loop.

        Args:
            results: A list of RaceResults to insert.
        """
        for result in results:
            self._insert_result(result)
        self.connection.commit()
        logger.info("Saved %d race results", len(results))

    def load_all_results(self) -> list[RaceResult]:
        """Return every row in race_results as RaceResult objects.

        Integer finish_time_seconds is converted back to timedelta on the
        way out. NULL values are mapped to Python None.

        Returns:
            A list of RaceResult objects in the order SQLite returns them.
        """
        cursor = self.connection.execute(
            """
            SELECT year, distance, runner_name, status,
                   rank_overall, finish_time_seconds, duv_runner_id,
                   gender, year_of_birth, nationality,
                   category, rank_gender, rank_category
            FROM race_results
            """
        )
        results: list[RaceResult] = []
        for row in cursor:
            (
                year, distance, runner_name, status,
                rank_overall, finish_time_seconds, duv_runner_id,
                gender, year_of_birth, nationality,
                category, rank_gender, rank_category,
            ) = row
            finish_time = (
                timedelta(seconds=finish_time_seconds)
                if finish_time_seconds is not None
                else None
            )
            results.append(
                RaceResult(
                    year=year,
                    distance=distance,
                    runner_name=runner_name,
                    status=status,
                    rank_overall=rank_overall,
                    finish_time=finish_time,
                    duv_runner_id=duv_runner_id,
                    gender=gender,
                    year_of_birth=year_of_birth,
                    nationality=nationality,
                    category=category,
                    rank_gender=rank_gender,
                    rank_category=rank_category,
                )
            )
        return results

    def _insert_result(self, result: RaceResult) -> None:
        """Execute the INSERT for one result. Does not commit.

        Args:
            result: A RaceResult to insert.
        """
        finish_time_seconds = (
            int(result.finish_time.total_seconds())
            if result.finish_time is not None
            else None
        )
        self.connection.execute(
            """
            INSERT INTO race_results (
                year, distance, runner_name, status,
                rank_overall, finish_time_seconds, duv_runner_id,
                gender, year_of_birth, nationality,
                category, rank_gender, rank_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.year,
                result.distance,
                result.runner_name,
                result.status,
                result.rank_overall,
                finish_time_seconds,
                result.duv_runner_id,
                result.gender,
                result.year_of_birth,
                result.nationality,
                result.category,
                result.rank_gender,
                result.rank_category,
            ),
        )
