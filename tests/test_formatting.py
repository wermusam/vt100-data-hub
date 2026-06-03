"""Tests for the display formatters."""

from __future__ import annotations

from vt100_data_hub.formatting import DisplayFormatters


class TestFormatName:
    """Tests for DisplayFormatters.format_name."""

    def test_flips_last_comma_first(self) -> None:
        """A 'Last, First' name should flip to 'First Last'."""
        formatter = DisplayFormatters()
        assert formatter.format_name("Larson, Daniel") == "Daniel Larson"

    def test_returns_input_when_no_comma(self) -> None:
        """A name without a comma should be returned unchanged."""
        formatter = DisplayFormatters()
        assert formatter.format_name("Madonna") == "Madonna"

    def test_handles_extra_commas_by_splitting_once(self) -> None:
        """Multiple commas: split only on the first comma+space."""
        formatter = DisplayFormatters()
        assert formatter.format_name("Smith Jr., John A.") == "John A. Smith Jr."

    def test_returns_empty_string_unchanged(self) -> None:
        """An empty string should remain empty."""
        formatter = DisplayFormatters()
        assert formatter.format_name("") == ""


class TestBufferCategory:
    """Tests for DisplayFormatters.buffer_category."""

    def test_under_30_minutes_is_tight(self) -> None:
        """A buffer below 30 minutes is Tight."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(0) == "Tight (under 30m)"
        assert formatter.buffer_category(29) == "Tight (under 30m)"

    def test_negative_buffer_is_tight(self) -> None:
        """A negative buffer (missed cutoff) is Tight."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(-15) == "Tight (under 30m)"

    def test_30_to_60_minutes_is_caution(self) -> None:
        """A buffer from 30 to 60 minutes is Caution."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(30) == "Caution (30m-1h)"
        assert formatter.buffer_category(60) == "Caution (30m-1h)"

    def test_over_60_minutes_is_comfortable(self) -> None:
        """A buffer over 60 minutes is Comfortable."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(61) == "Comfortable (over 1h)"
        assert formatter.buffer_category(300) == "Comfortable (over 1h)"
