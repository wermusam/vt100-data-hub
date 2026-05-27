"""Tests for the DUV event ID verifier script."""

from __future__ import annotations

import pytest

from verify_duv_event_ids import DUVEventIDVerifier


class FakeFetcher:
    """A DUVFetcher stand-in returning configurable HTML per event_id.

    Attributes:
        html_by_event_id: A mapping of event_id -> HTML string to return.
    """

    def __init__(self) -> None:
        self.html_by_event_id: dict[int, str] = {}

    def fetch_event(self, event_id: int) -> str:
        """Return the HTML configured for the requested event_id, or empty string."""
        return self.html_by_event_id.get(event_id, "")


class TestVerifyOne:
    """Tests for DUVEventIDVerifier.verify_one against fake HTML."""

    def _make_verifier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> DUVEventIDVerifier:
        """Build a verifier with the live fetcher swapped for FakeFetcher."""
        monkeypatch.setattr("verify_duv_event_ids.DUVFetcher", FakeFetcher)
        return DUVEventIDVerifier(polite_delay_seconds=0.0)

    def test_returns_true_when_year_and_name_present(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """verify_one should return True when both year and 'Vermont 100' appear."""
        verifier = self._make_verifier(monkeypatch)
        verifier.fetcher.html_by_event_id[110321] = (
            "<html>Vermont 100 2024 results</html>"
        )
        assert verifier.verify_one(2024, "100M", 110321) is True

    def test_returns_false_when_year_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """verify_one should return False when the year is absent from the page."""
        verifier = self._make_verifier(monkeypatch)
        verifier.fetcher.html_by_event_id[110321] = (
            "<html>Vermont 100 results</html>"
        )
        assert verifier.verify_one(2024, "100M", 110321) is False

    def test_returns_false_when_name_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """verify_one should return False when 'Vermont 100' is absent."""
        verifier = self._make_verifier(monkeypatch)
        verifier.fetcher.html_by_event_id[110321] = "<html>2024 results</html>"
        assert verifier.verify_one(2024, "100M", 110321) is False
