"""Populate the VT100 results database from DUV.

Fetches every registered DUV edition, parses the finishers,
and writes them to a SQLite database. Run once to bootstrap;
re-run when new editions are added (delete the existing .db
file first to avoid duplicates).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from vt100_data_hub.duv import DUVFetcher, DUVParser
from vt100_data_hub.duv_events import Distance, DUVEventRegistry
from vt100_data_hub.storage import ResultStorage

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "vt100.db"


class DatabasePopulator:
    """Populate a SQLite database with every registered DUV edition.

    Attributes:
        db_path: Path to the SQLite database file.
        polite_delay_seconds: Delay between fetches to be kind to DUV.
        connection: The open SQLite connection.
        fetcher: A DUVFetcher used to retrieve event HTML.
        parser: A DUVParser used to parse fetched HTML.
        registry: A DUVEventRegistry that knows the event IDs.
        storage: A ResultStorage where parsed results are written.
    """

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        polite_delay_seconds: float = 2.0,
    ) -> None:
        self.db_path = db_path
        self.polite_delay_seconds = polite_delay_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.fetcher = DUVFetcher()
        self.parser = DUVParser()
        self.registry = DUVEventRegistry()
        self.storage = ResultStorage(self.connection)

    def populate_one(self, year: int, distance: Distance) -> int:
        """Fetch, parse, and save one DUV edition.

        Args:
            year: The race year.
            distance: The race distance ("100M" or "100K").

        Returns:
            The number of finishers saved for this edition.
        """
        event_id = self.registry.get_event_id(year, distance)
        html = self.fetcher.fetch_event(event_id)
        results = self.parser.parse_all_finishers(html, year, distance)
        self.storage.save_results(results)
        logger.info(
            "Populated %s %s: %d finishers (event=%s)",
            year, distance, len(results), event_id,
        )
        return len(results)

    def populate_all(self) -> int:
        """Populate every edition in the registry.

        Clears any existing race_results before populating, so re-running
        produces a clean dataset every time.

        Creates the schema first (idempotent), then loops every available
        edition with a polite delay between fetches.

        Returns:
            Total number of finishers saved across all editions.
        """
        self.storage.create_schema()
        self.connection.execute("DELETE FROM race_results")
        self.connection.commit()
        total = 0
        for year, distance in self.registry.available_editions():
            count = self.populate_one(year, distance)
            total += count
            time.sleep(self.polite_delay_seconds)
        logger.info("Populated %d total finishers across all editions", total)
        return total

    def run(self) -> None:
        """Configure logging, populate the database, and close the connection.

        Entry point for command-line use.
        """
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        try:
            self.populate_all()
        finally:
            self.connection.close()


if __name__ == "__main__":
    DatabasePopulator().run()
