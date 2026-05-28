"""Display helpers for the Vermont 100 data hub UI.

These convert raw database values into human-friendly display strings.
Kept separate from the UI so they can be unit-tested and reused across
multiple front-ends (Streamlit today, possibly others later).
"""

from __future__ import annotations


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
