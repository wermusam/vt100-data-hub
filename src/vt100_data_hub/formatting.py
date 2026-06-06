"""Display helpers for the Vermont 100 data hub UI.

These convert raw database values into human-friendly display strings.
Kept separate from the UI so they can be unit-tested and reused across
multiple front-ends (Streamlit today, possibly others later).
"""

from __future__ import annotations

from datetime import time


class DisplayFormatters:
    """Display helpers for converting raw values to human-readable strings."""

    def format_name(self, name: str) -> str:
        """Convert 'Last, First' (DUV format) to 'First Last' for display.

        Args:
            name: A runner name. Typically "Last, First" as DUV publishes it.

        Returns:
            "First Last" if the input contains a comma+space separator;
            otherwise the input is returned unchanged.
        """
        if ", " in name:
            last, first = name.split(", ", 1)
            return f"{first} {last}"
        return name

    def buffer_category(self, minutes: float) -> str:
        """Bucket a buffer (minutes) into a cushion category for color coding.

        Args:
            minutes: Buffer in minutes (cutoff close minus target arrival).
                Negative means the goal time misses that cutoff.

        Returns:
            One of "Tight (under 30m)", "Caution (30m to 1h)", or
            "Comfortable (over 1h)".
        """
        if minutes < 30:
            return "Tight (under 30m)"
        if minutes <= 60:
            return "Caution (30m to 1h)"
        return "Comfortable (over 1h)"

    def format_clock_time(self, t: time) -> str:
        """Format a time of day as '6:15 AM'.

        Args:
            t: A datetime.time.

        Returns:
            The 12-hour clock string, e.g. '6:15 AM' or '12:55 AM'.
        """
        hour_12 = (
            t.hour if 1 <= t.hour <= 12 else (t.hour - 12 if t.hour > 12 else 12)
        )
        period = "AM" if t.hour < 12 else "PM"
        return f"{hour_12}:{t.minute:02d} {period}"

    def format_clock_time_with_day(
        self,
        t: time,
        minutes_from_start: float,
        start_hour: int,
        start_minute: int,
    ) -> str:
        """Format a clock time, adding '(next day)' once it crosses midnight.

        Args:
            t: The time-of-day to display.
            minutes_from_start: Minutes elapsed from race start to this time.
            start_hour: Race start hour (0-23).
            start_minute: Race start minute (0-59).

        Returns:
            The clock string, suffixed with ' (next day)' if the elapsed time
            has rolled past midnight at least once.
        """
        start_of_day = start_hour * 60 + start_minute
        total = start_of_day + int(round(minutes_from_start))
        base = self.format_clock_time(t)
        return f"{base} (next day)" if total // (24 * 60) >= 1 else base

    def format_pace(self, minutes_per_mile: float) -> str:
        """Format a pace in minutes-per-mile as 'MM:SS/mi'.

        Args:
            minutes_per_mile: Pace in decimal minutes per mile.

        Returns:
            A 'MM:SS/mi' string, or 'n/a' if the pace is non-positive.
        """
        if minutes_per_mile <= 0:
            return "n/a"
        whole = int(minutes_per_mile)
        seconds = int(round((minutes_per_mile - whole) * 60))
        if seconds == 60:
            whole, seconds = whole + 1, 0
        return f"{whole}:{seconds:02d}/mi"

    def format_duration(self, minutes: float) -> str:
        """Format a duration in minutes as 'Xh YYm'.

        Args:
            minutes: A duration in minutes. Negative values keep a '-' sign.

        Returns:
            An 'Xh YYm' string, e.g. '2h 15m' or '-0h 03m'.
        """
        sign = "-" if minutes < 0 else ""
        total = abs(int(round(minutes)))
        hours, mins = divmod(total, 60)
        return f"{sign}{hours}h {mins:02d}m"

    def format_hours(self, hours: float) -> str:
        """Format decimal hours as 'Xh YYm'.

        Args:
            hours: A duration in decimal hours, e.g. 24.75.

        Returns:
            An 'Xh YYm' string, e.g. '24h 45m'.
        """
        whole = int(hours)
        mins = int(round((hours - whole) * 60))
        if mins == 60:
            whole, mins = whole + 1, 0
        return f"{whole}h {mins:02d}m"

    def parse_hm_label(self, label: str) -> float:
        """Parse an 'Xh YYm' label back to decimal hours.

        Args:
            label: A label like '20h 15m'.

        Returns:
            The value in decimal hours, e.g. 20.25.
        """
        hours_part, minutes_part = label.split()
        return int(hours_part.rstrip("h")) + int(minutes_part.rstrip("m")) / 60.0
