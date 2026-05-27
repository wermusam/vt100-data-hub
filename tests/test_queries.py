"""Tests for Vermont 100 data-hub queries."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from vt100_data_hub.duv_events import DUVEventRegistry
from vt100_data_hub.queries import RunnerQueries
from vt100_data_hub.race_result import RaceResult
from vt100_data_hub.storage import ResultStorage


class TestRunnersWithNFinishes:
    """Tests for RunnerQueries.runners_with_n_finishes.

    Test data:
    - Alice (DUV 1001): 5 100M finishes (2015-2019)
    - Bob (DUV 1002): 3 100M finishes (2015-2017)
    - Carol (DUV 1003): 4 100M finishes (2015, 2017, 2019, 2022)
    - Dave (DUV 1004): 4 100K finishes (2015-2018, wrong distance for 100M query)
    - Ghost (no DUV ID): 4 100M finishes (2015-2018, anonymous)
    """

    def _make_queries_with_data(self) -> RunnerQueries:
        """Build a RunnerQueries backed by an in-memory DB seeded with test data."""
        connection = sqlite3.connect(":memory:")
        storage = ResultStorage(connection)
        storage.create_schema()
        storage.save_results(self._test_data())
        return RunnerQueries(connection=connection, registry=DUVEventRegistry())

    def _test_data(self) -> list[RaceResult]:
        """Build the list of fake finishers used across all tests."""
        results: list[RaceResult] = []
        for year in [2015, 2016, 2017, 2018, 2019]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Smith, Alice",
                    status="FINISH",
                    duv_runner_id=1001,
                    finish_time=timedelta(hours=24),
                )
            )
        for year in [2015, 2016, 2017]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Jones, Bob",
                    status="FINISH",
                    duv_runner_id=1002,
                    finish_time=timedelta(hours=25),
                )
            )
        for year in [2015, 2017, 2019, 2022]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Lee, Carol",
                    status="FINISH",
                    duv_runner_id=1003,
                    finish_time=timedelta(hours=26),
                )
            )
        for year in [2015, 2016, 2017, 2018]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100K",
                    runner_name="Park, Dave",
                    status="FINISH",
                    duv_runner_id=1004,
                    finish_time=timedelta(hours=12),
                )
            )
        for year in [2015, 2016, 2017, 2018]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Ghost, Anonymous",
                    status="FINISH",
                    duv_runner_id=None,
                    finish_time=timedelta(hours=27),
                )
            )
        return results

    def test_returns_runners_with_four_or_more_finishes(self) -> None:
        """Alice (5) and Carol (4) qualify. Bob (3) does not."""
        queries = self._make_queries_with_data()
        results = queries.runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        names = [row[0] for row in results]
        assert "Smith, Alice" in names
        assert "Lee, Carol" in names
        assert "Jones, Bob" not in names

    def test_excludes_wrong_distance(self) -> None:
        """Dave has 4 100K finishes but should not appear in a 100M query."""
        queries = self._make_queries_with_data()
        results = queries.runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        names = [row[0] for row in results]
        assert "Park, Dave" not in names

    def test_sorts_by_finish_count_descending(self) -> None:
        """Alice (5 finishes) should appear before Carol (4 finishes)."""
        queries = self._make_queries_with_data()
        results = queries.runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        names_in_order = [row[0] for row in results]
        alice_index = names_in_order.index("Smith, Alice")
        carol_index = names_in_order.index("Lee, Carol")
        assert alice_index < carol_index

    def test_excludes_runners_without_duv_id(self) -> None:
        """Anonymous (no DUV ID) has 4 100M finishes but should not appear."""
        queries = self._make_queries_with_data()
        results = queries.runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        names = [row[0] for row in results]
        assert "Ghost, Anonymous" not in names
