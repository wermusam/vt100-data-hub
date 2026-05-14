"""Tests for the DUV event ID registry."""

from __future__ import annotations

import pytest

from vt100_data_hub.duv_events import Distance, DUVEventRegistry, UnknownEditionError

class TestGetEventID:
    """Tests for DUVEventRegistry.get_event_id."""

    def test_returns_known_event_id_for_2024_100m(self) -> None:
        """2024 100M should resolve to DUV event 110321."""
        registry = DUVEventRegistry()
        assert registry.get_event_id(2024, "100M") == 110321

    def test_returns_known_event_id_for_2025_100m(self) -> None:
        """2025 100M should resolve to DUV event 113387."""
        registry = DUVEventRegistry()
        assert registry.get_event_id(2025, "100M") == 113387

    def test_defaults_to_100m_when_distance_omitted(self) -> None:
        """Omitting distance should default to the 100-mile race."""
        registry = DUVEventRegistry()
        assert registry.get_event_id(2024) == registry.get_event_id(2024, "100M")

    def test_raises_for_cancelled_year_2020(self) -> None:
        """2020 was cancelled; lookup should raise UnknownEditionError."""
        registry = DUVEventRegistry()
        with pytest.raises(UnknownEditionError):
            registry.get_event_id(2020, "100M")

    def test_raises_for_cancelled_year_2023(self) -> None:
        """2023 was cancelled due to flooding; lookup should raise."""
        registry = DUVEventRegistry()
        with pytest.raises(UnknownEditionError):
            registry.get_event_id(2023, "100M")

    def test_raises_for_year_outside_mapped_window(self) -> None:
        """Years not in the registry should raise."""
        registry = DUVEventRegistry()
        with pytest.raises(UnknownEditionError):
            registry.get_event_id(1995, "100M")


class TestAvailableEditions:
    """Tests for DUVEventRegistry.available_editions."""

    def test_returns_eight_editions(self) -> None:
        """The default registry should expose exactly eight 100M editions."""
        registry = DUVEventRegistry()
        assert len(registry.available_editions()) == 8

    def test_returns_sorted_oldest_first(self) -> None:
        """Editions should be sorted oldest first."""
        registry = DUVEventRegistry()
        editions = registry.available_editions()
        assert editions == sorted(editions)

    def test_does_not_include_cancelled_years(self) -> None:
        """Cancelled editions (2020, 2021, 2023) must not appear."""
        registry = DUVEventRegistry()
        years = {year for year, _ in registry.available_editions()}
        assert 2020 not in years
        assert 2021 not in years
        assert 2023 not in years

    def test_filter_by_distance(self) -> None:
        """Filtering to 100M should return only 100M editions."""
        registry = DUVEventRegistry()
        editions = registry.available_editions(distance="100M")
        assert all(distance == "100M" for _, distance in editions)


class TestLastNEditions:
    """Tests for DUVEventRegistry.last_n_editions."""

    def test_returns_eight_when_asked_for_eight(self) -> None:
        """Requesting the last 8 editions should return 8."""
        registry = DUVEventRegistry()
        assert len(registry.last_n_editions(8, "100M")) == 8

    def test_returns_most_recent_three_in_order(self) -> None:
        """Last 3 100M editions should be 2022, 2024, 2025 in that order."""
        registry = DUVEventRegistry()
        assert registry.last_n_editions(3, "100M") == [
            (2022, "100M"),
            (2024, "100M"),
            (2025, "100M"),
        ]

    def test_raises_for_zero(self) -> None:
        """Requesting zero editions is a programmer error."""
        registry = DUVEventRegistry()
        with pytest.raises(ValueError):
            registry.last_n_editions(0, "100M")


class TestCustomRegistry:
    """Tests for constructing a registry with custom data."""

    def test_can_inject_custom_event_ids(self) -> None:
        """The constructor accepts a custom mapping for testing."""
        custom: dict[tuple[int, Distance], int] = {(2030, "100M"): 999999}
        registry = DUVEventRegistry(event_ids=custom)
        assert registry.get_event_id(2030, "100M") == 999999
        assert len(registry.available_editions()) == 1