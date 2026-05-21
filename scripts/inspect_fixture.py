"""One-off script to inspect the structure of a DUV fixture file."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


def inspect_fixture(fixture_path: Path) -> None:
    """Print the number of rows in each table of a DUV fixture.

    Args:
        fixture_path: Path to a saved DUV HTML fixture.
    """
    html = fixture_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"Fixture: {fixture_path.name}")
    print(f"Total tables: {len(tables)}")
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        print(f"Table {i}: {len(rows)} rows")


def main() -> None:
    """Inspect a fixture file passed as a command-line argument."""
    if len(sys.argv) < 2:
        fixture_path = Path("tests/fixtures/duv_2024_100m.html")
    else:
        fixture_path = Path(sys.argv[1])
    inspect_fixture(fixture_path)


if __name__ == "__main__":
    main()