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

    def test_returns_years_list_for_qualifier(self) -> None:
        """Alice (5 finishes) should have her years listed in the result."""
        queries = self._make_queries_with_data()
        results = queries.runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        alice_row = next(r for r in results if r[0] == "Smith, Alice")
        years = sorted(int(y) for y in alice_row[3].split(","))
        assert years == [2015, 2016, 2017, 2018, 2019]


class TestGroupingByDuvIdNotName:
    """The 4-of-8 rule groups by DUV runner ID, never by name.

    This is the accuracy guarantee behind the race director's early-entry
    list: two different people who share a name must not be merged into one
    qualifier, and one person whose printed name changes across years (e.g.
    a marriage) must not be split into two.
    """

    def _queries(self, results: list[RaceResult]) -> RunnerQueries:
        """Build a RunnerQueries backed by an in-memory DB with the given data."""
        connection = sqlite3.connect(":memory:")
        storage = ResultStorage(connection)
        storage.create_schema()
        storage.save_results(results)
        return RunnerQueries(connection=connection, registry=DUVEventRegistry())

    def test_same_name_different_ids_stay_separate_runners(self) -> None:
        """Two different people both named 'Smith, John' (IDs 5001 and 5002),
        each with 4 finishes, must show up as two separate qualifiers, not one
        merged runner with 8. Grouping by name would wrongly collapse them."""
        results: list[RaceResult] = []
        for year in [2015, 2016, 2017, 2018]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Smith, John",
                    status="FINISH",
                    duv_runner_id=5001,
                )
            )
        for year in [2019, 2022, 2024, 2025]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Smith, John",
                    status="FINISH",
                    duv_runner_id=5002,
                )
            )
        rows = self._queries(results).runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        smiths = [r for r in rows if r[0] == "Smith, John"]
        assert len(smiths) == 2
        assert all(finish_count == 4 for _, finish_count, _, _ in smiths)

    def test_name_change_under_one_id_stays_one_runner(self) -> None:
        """One runner (ID 6001) whose printed name changes across years is still
        a single qualifier with all four finishes, not two split records."""
        results: list[RaceResult] = []
        for year, name in [
            (2015, "Maiden, Jane"),
            (2016, "Maiden, Jane"),
            (2017, "Married, Jane"),
            (2018, "Married, Jane"),
        ]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name=name,
                    status="FINISH",
                    duv_runner_id=6001,
                )
            )
        rows = self._queries(results).runners_with_n_finishes(
            n=4, distance="100M", last_n_editions=8
        )
        jane_rows = [r for r in rows if r[1] == 4]
        assert len(jane_rows) == 1
        years = sorted(int(y) for y in jane_rows[0][3].split(","))
        assert years == [2015, 2016, 2017, 2018]


class TestRunnersWhoDidBoth:
    """Tests for RunnerQueries.runners_who_did_both_distances.

    Test data:
    - Aria (DUV 2001): 3 100M finishes only (single distance)
    - Bo (DUV 2002): 2 100M finishes + 1 100K finish (crossover, total 3)
    - Cleo (DUV 2003): 2 100K finishes only (single distance)
    - Dax (DUV 2004): 5 100M finishes + 3 100K finishes (crossover, total 8)
    - Ghost (no DUV): 1 100M + 1 100K (crossover but no ID, excluded)
    """

    def _make_queries_with_data(self) -> RunnerQueries:
        """Build a RunnerQueries with crossover-specific test data."""
        connection = sqlite3.connect(":memory:")
        storage = ResultStorage(connection)
        storage.create_schema()
        storage.save_results(self._test_data())
        return RunnerQueries(connection=connection, registry=DUVEventRegistry())

    def _test_data(self) -> list[RaceResult]:
        """Build the list of fake finishers for crossover tests."""
        results: list[RaceResult] = []
        for year in [2015, 2016, 2017]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Smith, Aria",
                    status="FINISH",
                    duv_runner_id=2001,
                    finish_time=timedelta(hours=24),
                )
            )
        for year in [2015, 2016]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Jones, Bo",
                    status="FINISH",
                    duv_runner_id=2002,
                    finish_time=timedelta(hours=25),
                )
            )
        results.append(
            RaceResult(
                year=2017,
                distance="100K",
                runner_name="Jones, Bo",
                status="FINISH",
                duv_runner_id=2002,
                finish_time=timedelta(hours=12),
            )
        )
        for year in [2015, 2016]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100K",
                    runner_name="Lee, Cleo",
                    status="FINISH",
                    duv_runner_id=2003,
                    finish_time=timedelta(hours=13),
                )
            )
        for year in [2015, 2016, 2017, 2018, 2019]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100M",
                    runner_name="Park, Dax",
                    status="FINISH",
                    duv_runner_id=2004,
                    finish_time=timedelta(hours=22),
                )
            )
        for year in [2015, 2016, 2017]:
            results.append(
                RaceResult(
                    year=year,
                    distance="100K",
                    runner_name="Park, Dax",
                    status="FINISH",
                    duv_runner_id=2004,
                    finish_time=timedelta(hours=11),
                )
            )
        results.append(
            RaceResult(
                year=2015,
                distance="100M",
                runner_name="Ghost, Anon",
                status="FINISH",
                duv_runner_id=None,
                finish_time=timedelta(hours=27),
            )
        )
        results.append(
            RaceResult(
                year=2016,
                distance="100K",
                runner_name="Ghost, Anon",
                status="FINISH",
                duv_runner_id=None,
                finish_time=timedelta(hours=14),
            )
        )
        return results

    def test_returns_only_crossover_runners(self) -> None:
        """Bo and Dax have both distances; Aria and Cleo don't."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        names = [row[0] for row in results]
        assert "Jones, Bo" in names
        assert "Park, Dax" in names
        assert "Smith, Aria" not in names
        assert "Lee, Cleo" not in names

    def test_sorts_by_total_finishes_descending(self) -> None:
        """Dax (8 total) should appear before Bo (3 total)."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        names_in_order = [row[0] for row in results]
        dax_index = names_in_order.index("Park, Dax")
        bo_index = names_in_order.index("Jones, Bo")
        assert dax_index < bo_index

    def test_excludes_runners_without_duv_id(self) -> None:
        """Ghost has both distances but no DUV ID, should not appear."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        names = [row[0] for row in results]
        assert "Ghost, Anon" not in names

    def test_returns_correct_counts_per_distance(self) -> None:
        """Dax should have 5 100M finishes and 3 100K finishes."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        dax_row = next(r for r in results if r[0] == "Park, Dax")
        assert dax_row[1] == 5
        assert dax_row[2] == 3

    def test_returns_years_lists_per_distance(self) -> None:
        """Dax's 100M and 100K year lists should match what was inserted."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        dax_row = next(r for r in results if r[0] == "Park, Dax")
        years_100m = sorted(int(y) for y in dax_row[3].split(","))
        years_100k = sorted(int(y) for y in dax_row[4].split(","))
        assert years_100m == [2015, 2016, 2017, 2018, 2019]
        assert years_100k == [2015, 2016, 2017]

    def test_returns_latest_year_across_both_distances(self) -> None:
        """Dax's latest year should be 2019 (his most recent 100M finish)."""
        queries = self._make_queries_with_data()
        results = queries.runners_who_did_both_distances()
        dax_row = next(r for r in results if r[0] == "Park, Dax")
        assert dax_row[5] == 2019
