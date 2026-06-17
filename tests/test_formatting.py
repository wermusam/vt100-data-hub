"""Tests for the display formatters."""

from __future__ import annotations

from datetime import time

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

    def test_negative_buffer_is_a_miss(self) -> None:
        """A negative buffer (arrive after the cutoff) is a Miss."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(-1) == "Miss (after cutoff)"
        assert formatter.buffer_category(-15) == "Miss (after cutoff)"

    def test_zero_to_30_minutes_is_tight(self) -> None:
        """Making it with under 30 minutes to spare is Tight."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(0) == "Tight (under 30m)"
        assert formatter.buffer_category(29) == "Tight (under 30m)"

    def test_30_minutes_or_more_is_comfortable(self) -> None:
        """A buffer of 30 minutes or more is Comfortable."""
        formatter = DisplayFormatters()
        assert formatter.buffer_category(30) == "Comfortable (30m+)"
        assert formatter.buffer_category(300) == "Comfortable (30m+)"


class TestFormatClockTime:
    """Tests for DisplayFormatters.format_clock_time."""

    def test_morning_time(self) -> None:
        """6:15 AM formats with AM."""
        formatter = DisplayFormatters()
        assert formatter.format_clock_time(time(6, 15)) == "6:15 AM"

    def test_midnight_hour_shows_12_am(self) -> None:
        """Hour 0 shows as 12 AM."""
        formatter = DisplayFormatters()
        assert formatter.format_clock_time(time(0, 55)) == "12:55 AM"

    def test_noon_shows_12_pm(self) -> None:
        """Hour 12 shows as 12 PM."""
        formatter = DisplayFormatters()
        assert formatter.format_clock_time(time(12, 0)) == "12:00 PM"

    def test_afternoon_time(self) -> None:
        """1:20 PM formats in 12-hour form with PM."""
        formatter = DisplayFormatters()
        assert formatter.format_clock_time(time(13, 20)) == "1:20 PM"


class TestFormatClockTimeWithDay:
    """Tests for DisplayFormatters.format_clock_time_with_day."""

    def test_same_day_has_no_suffix(self) -> None:
        """An arrival before midnight gets no '(next day)' suffix."""
        formatter = DisplayFormatters()
        result = formatter.format_clock_time_with_day(time(6, 0), 120, 4, 0)
        assert result == "6:00 AM"

    def test_next_day_has_suffix(self) -> None:
        """An arrival past midnight is marked '(next day)'."""
        formatter = DisplayFormatters()
        result = formatter.format_clock_time_with_day(time(0, 55), 1255, 4, 0)
        assert result == "12:55 AM (next day)"


class TestFormatPace:
    """Tests for DisplayFormatters.format_pace."""

    def test_typical_pace(self) -> None:
        """14.85 min/mi formats as 14:51/mi."""
        formatter = DisplayFormatters()
        assert formatter.format_pace(14.85) == "14:51/mi"

    def test_non_positive_returns_na(self) -> None:
        """A non-positive pace returns 'n/a'."""
        formatter = DisplayFormatters()
        assert formatter.format_pace(0) == "n/a"

    def test_rounds_up_to_next_minute(self) -> None:
        """A pace that rounds to 60 seconds rolls into the next minute."""
        formatter = DisplayFormatters()
        assert formatter.format_pace(17.999) == "18:00/mi"


class TestFormatDuration:
    """Tests for DisplayFormatters.format_duration."""

    def test_positive_duration(self) -> None:
        """135 minutes formats as 2h 15m."""
        formatter = DisplayFormatters()
        assert formatter.format_duration(135) == "2h 15m"

    def test_negative_duration_keeps_sign(self) -> None:
        """A negative duration keeps a leading minus."""
        formatter = DisplayFormatters()
        assert formatter.format_duration(-3) == "-0h 03m"

    def test_zero_duration(self) -> None:
        """Zero formats as 0h 00m."""
        formatter = DisplayFormatters()
        assert formatter.format_duration(0) == "0h 00m"


class TestFormatHours:
    """Tests for DisplayFormatters.format_hours."""

    def test_decimal_hours(self) -> None:
        """24.75 hours formats as 24h 45m."""
        formatter = DisplayFormatters()
        assert formatter.format_hours(24.75) == "24h 45m"

    def test_whole_hours(self) -> None:
        """30.0 hours formats as 30h 00m."""
        formatter = DisplayFormatters()
        assert formatter.format_hours(30.0) == "30h 00m"


class TestParseHmLabel:
    """Tests for DisplayFormatters.parse_hm_label."""

    def test_parses_label(self) -> None:
        """'20h 15m' parses to 20.25 decimal hours."""
        formatter = DisplayFormatters()
        assert formatter.parse_hm_label("20h 15m") == 20.25

    def test_round_trips_with_format_hours(self) -> None:
        """format_hours and parse_hm_label are inverses."""
        formatter = DisplayFormatters()
        assert formatter.parse_hm_label(formatter.format_hours(27.5)) == 27.5
