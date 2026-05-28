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
