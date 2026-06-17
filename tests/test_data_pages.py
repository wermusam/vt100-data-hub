"""Smoke tests for the two data-hub pages.

These drive the real Streamlit pages through the AppTest harness to confirm
each renders against the committed database without raising, and produces the
table a visitor would see. They guard against a page breaking before the race
director opens it.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).parent.parent / "app"
RETURNING_RUNNERS = str(APP_DIR / "pages" / "1_Returning_Runners.py")
FINISHERS_BOTH = str(APP_DIR / "pages" / "2_Finishers_of_Both_Distances.py")


class TestReturningRunnersPage:
    """The Returning Runners page renders and lists qualifiers."""

    def test_renders_without_exception_and_shows_a_table(self) -> None:
        """The page loads against the real database and shows a results table."""
        app = AppTest.from_file(RETURNING_RUNNERS, default_timeout=30)
        app.run()
        assert not app.exception
        assert len(app.dataframe) == 1

    def test_switching_distance_does_not_break(self) -> None:
        """Choosing the 100K re-runs the query cleanly."""
        app = AppTest.from_file(RETURNING_RUNNERS, default_timeout=30)
        app.run()
        app.radio[0].set_value("100K").run()
        assert not app.exception


class TestFinishersOfBothDistancesPage:
    """The Finishers of Both Distances page renders and lists crossover runners."""

    def test_renders_without_exception_and_shows_a_table(self) -> None:
        """The page loads against the real database and shows a results table."""
        app = AppTest.from_file(FINISHERS_BOTH, default_timeout=30)
        app.run()
        assert not app.exception
        assert len(app.dataframe) == 1
