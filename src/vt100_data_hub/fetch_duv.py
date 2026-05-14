"""Fetch Vermont 100 race results from DUV (statistik.d-u-v.org).

DUV maintains the deepest public archive of Vermont 100 results,
covering every edition from 1989 through 2025.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class DUVFetchError(Exception):
    """Raised when fetching a DUV results page fails."""


class DUVFetcher:
    """Fetch raw HTML from DUV event-result pages.

    Attributes:
        base_url: The DUV result endpoint, parameterized by event ID.
        timeout: HTTP request timeout in seconds.
        session: A requests Session for connection reuse.
    """

    base_url: str = "https://statistik.d-u-v.org/getresultevent.php"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "vt100-data-hub/0.1.0 (research; contact: amwermus@gmail.com)"
            }
        )

    def fetch_event(self, event_id: int) -> str:
        """Fetch the HTML for a single DUV event page.

        Args:
            event_id: The numeric DUV event ID (e.g., 110321 for VT100 2024).

        Returns:
            The raw HTML body of the response as a string.

        Raises:
            DUVFetchError: If the HTTP request fails or returns a non-200 status.
        """
        params = {"event": event_id}
        logger.info("Fetching DUV event %s", event_id)
        try:
            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DUVFetchError(f"Failed to fetch event {event_id}") from exc
        return response.text


def main() -> None:
    """Smoke-test the fetcher against VT100 2024 (DUV event 110321)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fetcher = DUVFetcher()
    html = fetcher.fetch_event(event_id=110321)
    logger.info("Received %d characters of HTML", len(html))


if __name__ == "__main__":
    main()
