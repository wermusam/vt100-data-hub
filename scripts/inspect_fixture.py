"""One-off script to inspect the structure of the DUV 2024 100M fixture."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

FIXTURE_PATH = Path("tests/fixtures/duv_2024_100m.html")

def show_first_finisher_row() -> None:
    """Print the second row of Table 5 (first row after the header)."""
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    results_table = soup.find_all("table")[5]
    rows = results_table.find_all("tr")
    print("HEADER ROW:")
    print(rows[0])
    print()
    print("FIRST FINISHER ROW:")
    print(rows[1])


def main() -> None:
    """Print the number of rows in each table, then inspect the results table."""
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"Total tables: {len(tables)}")
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        print(f"Table {i}: {len(rows)} rows")
    print()
    show_first_finisher_row()


if __name__ == "__main__":
    main()