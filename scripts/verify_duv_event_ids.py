"""Verify that each DUV event ID in our registry points to the correct VT100 edition."""

from __future__ import annotations

import logging
import time

from vt100_data_hub.duv import DUVFetcher
from vt100_data_hub.duv_events import Distance, DUVEventRegistry

logger = logging.getLogger(__name__)


class DUVEventIDVerifier:
    """Verify DUV event IDs by checking each event page's body for the expected year.

    Attributes:
        polite_delay_seconds: Delay between requests to avoid hammering DUV.
        fetcher: A DUVFetcher used to retrieve each event page.
        registry: A DUVEventRegistry whose IDs will be verified.
    """

    def __init__(self, polite_delay_seconds: float = 2.0) -> None:
        self.polite_delay_seconds = polite_delay_seconds
        self.fetcher = DUVFetcher()
        self.registry = DUVEventRegistry()

    def verify_one(self, year: int, distance: Distance, event_id: int) -> bool:
        """Fetch one event page and check the body mentions the expected year.

        DUV's <title> tag is generic across all event pages, so we check the
        page body for the year and the "Vermont 100" race name.

        Args:
            year: The expected race year.
            distance: The expected distance label.
            event_id: The DUV event ID to verify.

        Returns:
            True if both the year and "Vermont 100" appear in the page body.
        """
        html = self.fetcher.fetch_event(event_id)
        year_found = str(year) in html
        name_found = "Vermont 100" in html
        matched = year_found and name_found
        status = "OK " if matched else "FAIL"
        logger.info(
            "%s  %s %s  event=%s  year_in_page=%s  name_in_page=%s",
            status,
            year,
            distance,
            event_id,
            year_found,
            name_found,
        )
        return matched

    def verify_all(self) -> list[tuple[int, Distance, int]]:
        """Verify every event ID in the registry.

        Returns:
            A list of (year, distance, event_id) tuples that failed verification.
            An empty list means all IDs verified successfully.
        """
        failures: list[tuple[int, Distance, int]] = []
        for year, distance in self.registry.available_editions():
            event_id = self.registry.get_event_id(year, distance)
            ok = self.verify_one(year, distance, event_id)
            if not ok:
                failures.append((year, distance, event_id))
            time.sleep(self.polite_delay_seconds)
        return failures

    def run(self) -> None:
        """Configure logging and run verification across all event IDs.

        Entry point for command-line use.
        """
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        failures = self.verify_all()
        if failures:
            logger.error(
                "FAILED: %d event ID(s) did not match: %s", len(failures), failures
            )
        else:
            logger.info("All event IDs verified.")


if __name__ == "__main__":
    DUVEventIDVerifier().run()
