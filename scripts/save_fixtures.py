"""Save real DUV event pages as test fixtures.

Tests should not hit DUV directly — that's slow, rude, and flaky.
Instead, this script saves real DUV HTML pages to tests/fixtures/
once, so tests can read from disk for fast, reproducible runs.

Re-run this script only when DUV changes their page format and
the existing fixtures need refreshing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from vt100_data_hub.duv_events import Distance, DUVEventRegistry
from vt100_data_hub.duv import DUVFetcher

logger = logging.getLogger(__name__)

FIXTURES_DIR: Path = Path(__file__).parent.parent / "tests" / "fixtures"


class FixtureSaver:
    """Save DUV event HTML pages to the tests/fixtures/ directory.

    Attributes:
        fetcher: A DUVFetcher used to retrieve event pages.
        registry: A DUVEventRegistry that knows the event IDs.
        fixtures_dir: The directory where HTML fixture files are written.
    """

    def __init__(
        self,
        fetcher: DUVFetcher,
        registry: DUVEventRegistry,
        fixtures_dir: Path = FIXTURES_DIR,
    ) -> None:
        self.fetcher = fetcher
        self.registry = registry
        self.fixtures_dir = fixtures_dir

    def fixture_path(self, year: int, distance: Distance) -> Path:
        """Return the path where a given fixture file should be written.

        Args:
            year: The race year.
            distance: The race distance.

        Returns:
            A Path inside the fixtures directory.
        """
        filename = f"duv_{year}_{distance.lower()}.html"
        return self.fixtures_dir / filename

    def save_one(self, year: int, distance: Distance) -> Path:
        """Fetch one DUV event page and write it to disk as a fixture.

        Args:
            year: The race year to fetch.
            distance: The race distance ("100M" or "100K").

        Returns:
            The Path the fixture was written to.
        """
        event_id = self.registry.get_event_id(year, distance)
        html = self.fetcher.fetch_event(event_id)
        path = self.fixture_path(year, distance)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        logger.info("Saved %d chars to %s", len(html), path)
        return path


def main() -> None:
    """Save the 2024 100M and 2017 100M fixtures as test data."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    saver = FixtureSaver(
        fetcher=DUVFetcher(),
        registry=DUVEventRegistry(),
    )
    saver.save_one(year=2024, distance="100M")
    saver.save_one(year=2017, distance="100M")


if __name__ == "__main__":
    main()