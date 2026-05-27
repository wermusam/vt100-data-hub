"""Tests for the database populator script."""

from __future__ import annotations

from pathlib import Path

import pytest

from populate_database import DatabasePopulator

FIXTURE_2024_100M_PATH = Path(__file__).parent / "fixtures" / "duv_2024_100m.html"


class FakeFetcher:
    """A DUVFetcher stand-in that returns the saved 2024 100M fixture HTML.

    Attributes:
        fetched_event_ids: A record of every event_id requested, in order.
    """

    def __init__(self) -> None:
        self._fixture_html = FIXTURE_2024_100M_PATH.read_text(encoding="utf-8")
        self.fetched_event_ids: list[int] = []

    def fetch_event(self, event_id: int) -> str:
        """Record the event_id and return the saved fixture HTML."""
        self.fetched_event_ids.append(event_id)
        return self._fixture_html


class TestPopulateOne:
    """Tests for DatabasePopulator.populate_one against the 2024 100M fixture."""

    def _make_populator(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> DatabasePopulator:
        """Build a populator with the live fetcher swapped for FakeFetcher."""
        monkeypatch.setattr("populate_database.DUVFetcher", FakeFetcher)
        return DatabasePopulator(
            db_path=tmp_path / "test.db",
            polite_delay_seconds=0.0,
        )

    def test_saves_255_finishers_from_2024_fixture(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Populating 2024 100M from the fixture should save 255 finishers."""
        populator = self._make_populator(monkeypatch, tmp_path)
        populator.storage.create_schema()
        count = populator.populate_one(2024, "100M")
        assert count == 255

    def test_uses_correct_event_id_for_2024_100m(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """populate_one should fetch the 2024 100M event ID (110321)."""
        populator = self._make_populator(monkeypatch, tmp_path)
        populator.storage.create_schema()
        populator.populate_one(2024, "100M")
        assert populator.fetcher.fetched_event_ids == [110321]

    def test_results_are_loadable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """After populate_one, the storage should return 255 RaceResults."""
        populator = self._make_populator(monkeypatch, tmp_path)
        populator.storage.create_schema()
        populator.populate_one(2024, "100M")
        loaded = populator.storage.load_all_results()
        assert len(loaded) == 255
        assert loaded[0].runner_name == "Gage, Sarah"
