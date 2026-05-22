"""Persist Vermont 100 race results in a SQLite database.

The storage layer caches parsed DUV results so the data hub can
answer queries without re-parsing HTML on every request.
"""

from __future__ import annotations

import logging
import sqlite3

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

    def save_result(self, result: RaceResult) -> None:
        """Insert one RaceResult into the race_results table.

        The RaceResult's finish_time (timedelta) is converted to integer
        seconds for SQLite storage. Optional fields are stored as NULL
        when absent.

        Args:
            result: A RaceResult parsed from DUV or another source.
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
        self.connection.commit()
