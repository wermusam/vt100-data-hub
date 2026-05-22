"""Tests for the result storage layer."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from vt100_data_hub.race_result import RaceResult
from vt100_data_hub.storage import ResultStorage


class TestCreateSchema:
    """Tests for ResultStorage.create_schema on an in-memory database."""

    def _make_storage(self) -> ResultStorage:
        """Build a ResultStorage backed by an in-memory SQLite connection."""
        return ResultStorage(sqlite3.connect(":memory:"))

    def test_creates_race_results_table(self) -> None:
        """After create_schema, a table named race_results should exist."""
        storage = self._make_storage()
        storage.create_schema()
        cursor = storage.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='race_results'"
        )
        assert cursor.fetchone() == ("race_results",)


class TestSaveResult:
    """Tests for ResultStorage.save_result on an in-memory database."""

    def _make_storage(self) -> ResultStorage:
        """Build a ResultStorage with the schema already created."""
        storage = ResultStorage(sqlite3.connect(":memory:"))
        storage.create_schema()
        return storage

    def _make_result(self) -> RaceResult:
        """Build a sample RaceResult matching the 2024 winner."""
        return RaceResult(
            year=2024,
            distance="100M",
            runner_name="Gage, Sarah",
            status="FINISH",
            rank_overall=1,
            finish_time=timedelta(hours=17, minutes=19, seconds=45),
            duv_runner_id=1645043,
            gender="F",
            year_of_birth=1995,
            nationality="USA",
            category="W23",
            rank_gender=1,
            rank_category=1,
        )

    def test_saves_runner_name(self) -> None:
        """After save_result, the runner_name should be retrievable."""
        storage = self._make_storage()
        storage.save_result(self._make_result())
        cursor = storage.connection.execute("SELECT runner_name FROM race_results")
        assert cursor.fetchone() == ("Gage, Sarah",)

    def test_saves_finish_time_as_seconds(self) -> None:
        """timedelta should be converted to integer seconds on insert."""
        storage = self._make_storage()
        storage.save_result(self._make_result())
        cursor = storage.connection.execute(
            "SELECT finish_time_seconds FROM race_results"
        )
        expected_seconds = 17 * 3600 + 19 * 60 + 45
        assert cursor.fetchone() == (expected_seconds,)

    def test_saves_year_and_distance(self) -> None:
        """Year and distance tags should round-trip."""
        storage = self._make_storage()
        storage.save_result(self._make_result())
        cursor = storage.connection.execute("SELECT year, distance FROM race_results")
        assert cursor.fetchone() == (2024, "100M")
