"""Fetch and parse Vermont 100 results from DUV (statistik.d-u-v.org).

DUV maintains the deepest public archive of Vermont 100 results,
covering every edition from 1989 through 2025.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import requests
from bs4 import BeautifulSoup, Tag

from vt100_data_hub.race_result import Distance, RaceResult

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


class DUVParseError(Exception):
    """Raised when parsing a DUV results page fails."""


class DUVParser:
    """Parse Vermont 100 race results from a DUV event-page HTML string.

    DUV pages contain multiple tables for layout, navigation, and filtering.
    The actual finisher results live in a single table that this parser
    locates and walks.
    """

    def parse_all_finishers(self, html: str, year: int, distance: Distance) -> list[RaceResult]:
        """Parse every finisher row from a DUV event page.

        Walks every row of the results table except the header row and
        returns one RaceResult per finisher.

        Args:
            html: The full HTML body of a DUV event-result page.
            year: The race year, used to tag each RaceResult.
            distance: The race distance, used to tag each RaceResult.

        Returns:
            A list of RaceResult objects, one per finisher row, in the
            order DUV returned them.

        Raises:
            DUVParseError: If the results table cannot be located.
        """
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        results_table = self._find_results_table(tables)
        rows = results_table.find_all("tr")
        finishers: list[RaceResult] = []
        for row in rows[1:]:
            try:
                finishers.append(self._parse_finisher_row(row, year, distance))
            except DUVParseError as exc:
                logger.warning("Skipping unparseable row: %s", exc)
        return finishers

    def parse_first_finisher(self, html: str, year: int, distance: Distance) -> RaceResult:
        """Parse just the rank-1 finisher row from a DUV event page.

        This is the smallest possible parser entry point — it confirms
        we can locate the results table and extract one runner's fields
        before extending to all finishers.

        Args:
            html: The full HTML body of a DUV event-result page.
            year: The race year, used to tag the resulting RaceResult.
            distance: The race distance, used to tag the resulting RaceResult.

        Returns:
            A RaceResult populated from the first finisher row.

        Raises:
            DUVParseError: If the results table cannot be located or the
                first finisher row cannot be parsed.
        """
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        results_table = self._find_results_table(tables)
        rows = results_table.find_all("tr")
        if len(rows) < 2:
            raise DUVParseError("Results table has no finisher rows")
        return self._parse_finisher_row(rows[1], year, distance)

    def _find_results_table(self, tables: list[Tag]) -> Tag:
        """Locate the results table among all tables in the page.

        DUV pages currently put the results table at the position with the
        most rows. We pick the largest table rather than hard-coding an
        index so the parser tolerates DUV adding or removing layout tables.

        Args:
            tables: All <table> elements found in the page.

        Returns:
            The single table holding finisher rows.

        Raises:
            DUVParseError: If no tables are present.
        """
        if not tables:
            raise DUVParseError("No tables found in HTML")
        return max(tables, key=lambda t: len(t.find_all("tr")))

    def _parse_finisher_row(
        self,
        row: Tag,
        year: int,
        distance: Distance,
    ) -> RaceResult:
        """Parse one finisher <tr> into a RaceResult.

        Args:
            row: A <tr> element containing 12 <td> cells for one finisher.
            year: The race year.
            distance: The race distance.

        Returns:
            A RaceResult populated from the row's cells.

        Raises:
            DUVParseError: If the row does not have the expected cell count.
        """
        cells = row.find_all("td")
        if len(cells) < 12:
            raise DUVParseError(f"Expected 12 cells, got {len(cells)}")
        rank_overall = int(cells[0].get_text(strip=True))
        finish_time = self._parse_finish_time(cells[1].get_text(strip=True))
        runner_name, duv_runner_id = self._parse_name_cell(cells[2])
        nationality = cells[4].get_text(strip=True) or None
        year_of_birth_text = cells[5].get_text(strip=True)
        year_of_birth = int(year_of_birth_text) if year_of_birth_text else None
        gender_text = cells[6].get_text(strip=True)
        gender = gender_text if gender_text in ("M", "F", "NB") else None
        rank_gender = int(cells[7].get_text(strip=True))
        category_text = cells[8].get_text(strip=True)
        category = category_text if category_text and category_text != "#NA" else None
        rank_category_text = cells[9].get_text(strip=True)
        rank_category = int(rank_category_text) if rank_category_text else None
        return RaceResult(
            year=year,
            distance=distance,
            runner_name=runner_name,
            status="FINISH",
            rank_overall=rank_overall,
            finish_time=finish_time,
            duv_runner_id=duv_runner_id,
            gender=gender,
            year_of_birth=year_of_birth,
            nationality=nationality,
            category=category,
            rank_gender=rank_gender,
            rank_category=rank_category,
        )

    def _parse_finish_time(self, text: str) -> timedelta:
        """Convert a DUV time string like '17:19:45 h' to a timedelta.

        Args:
            text: The cell text, e.g., '17:19:45 h'.

        Returns:
            A timedelta of the finish time.

        Raises:
            DUVParseError: If the text cannot be parsed as H:MM:SS.
        """
        cleaned = text.replace("h", "").strip()
        parts = cleaned.split(":")
        if len(parts) != 3:
            raise DUVParseError(f"Cannot parse time {text!r}")
        hours, minutes, seconds = (int(p) for p in parts)
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    def _parse_name_cell(self, cell: Tag) -> tuple[str, int | None]:
        """Extract runner name and DUV runner ID from the name cell.

        The cell contains an <a> linking to a runner profile URL of the
        form 'getresultperson.php?runner=NNNNNNN'. The link text is the
        runner's name.

        Args:
            cell: The <td> cell containing the name link.

        Returns:
            A tuple of (runner_name, duv_runner_id). The ID is None if
            no profile link is present.
        """
        link = cell.find("a")
        if link is None:
            return (cell.get_text(strip=True), None)
        runner_name = link.get_text(strip=True)
        href = link.get("href", "")
        runner_id: int | None = None
        if "runner=" in href:
            runner_id = int(href.split("runner=")[1].split("&")[0])
        return (runner_name, runner_id)
