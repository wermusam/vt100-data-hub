"""Tests for the fixture saver script."""

from __future__ import annotations

from pathlib import Path

import pytest

from save_fixtures import FixtureSaver


class FakeFetcher:
    """A DUVFetcher stand-in that returns a fixed HTML string.

    Attributes:
        html: The HTML content returned from every fetch_event call.
        fetched_event_ids: A record of every event_id requested, in order.
    """

    def __init__(self) -> None:
        self.html = "<html><body>fake DUV page</body></html>"
        self.fetched_event_ids: list[int] = []

    def fetch_event(self, event_id: int) -> str:
        """Record the event_id and return the fixed fake HTML."""
        self.fetched_event_ids.append(event_id)
        return self.html


class TestFixturePath:
    """Tests for FixtureSaver.fixture_path."""

    def test_filename_uses_lowercase_distance(self, tmp_path: Path) -> None:
        """A 100M fixture path should be named duv_<year>_100m.html."""
        saver = FixtureSaver(fixtures_dir=tmp_path)
        path = saver.fixture_path(2024, "100M")
        assert path == tmp_path / "duv_2024_100m.html"


class TestSaveOne:
    """Tests for FixtureSaver.save_one with a fake fetcher."""

    def _make_saver(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> FixtureSaver:
        """Build a FixtureSaver with the live fetcher swapped for FakeFetcher."""
        monkeypatch.setattr("save_fixtures.DUVFetcher", FakeFetcher)
        return FixtureSaver(fixtures_dir=tmp_path)

    def test_writes_fetched_html_to_disk(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """save_one should write the fetched HTML to the fixtures directory."""
        saver = self._make_saver(monkeypatch, tmp_path)
        path = saver.save_one(2024, "100M")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "<html><body>fake DUV page</body></html>"

    def test_uses_correct_event_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """save_one should fetch using the registry's event ID for 2024 100M."""
        saver = self._make_saver(monkeypatch, tmp_path)
        saver.save_one(2024, "100M")
        assert saver.fetcher.fetched_event_ids == [110321]

    def test_returns_written_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """save_one should return the path of the written fixture."""
        saver = self._make_saver(monkeypatch, tmp_path)
        path = saver.save_one(2024, "100M")
        assert path == tmp_path / "duv_2024_100m.html"
