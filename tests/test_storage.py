"""Tests for the result storage layer."""

from __future__ import annotations

import sqlite3

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
