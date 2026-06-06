"""Tests for the Pace Planner page's two-way goal/stop behavior.

These drive the real Streamlit page through Streamlit's AppTest harness so the
slider-and-stops wiring is exercised exactly as a runner would, without a
browser. The model under test: goal time = running time + aid-station time.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

PACE_PAGE = str(
    Path(__file__).parent.parent / "app" / "pages" / "Responsible_Pace_Chart.py"
)


def st_note(app: AppTest, distance: str = "100M") -> str:
    """Return the page's current 'what changed' note for a distance, or ''."""
    key = f"last_note_{distance}"
    return app.session_state[key] if key in app.session_state else ""


class TestPacePlannerPage:
    """The page renders and the goal slider and stops move together correctly."""

    def _fresh_app(self) -> AppTest:
        """Return a freshly run AppTest for the pace planner page."""
        app = AppTest.from_file(PACE_PAGE, default_timeout=30)
        app.run()
        return app

    def test_page_loads_without_exception(self) -> None:
        """The page renders cleanly and starts at the 28h default goal."""
        app = self._fresh_app()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"

    def test_raising_average_slides_goal_later(self) -> None:
        """Raising the average stop by 2 min across 25 stops slides the goal
        50 minutes later (28h00m -> 28h50m), holding running pace."""
        app = self._fresh_app()
        app.number_input[0].set_value(7.0).run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 50m"

    def test_goal_is_capped_at_the_race_cutoff(self) -> None:
        """Stops big enough to push past 30h clamp the goal at the cutoff."""
        app = self._fresh_app()
        app.number_input[0].set_value(15.0).run()
        assert not app.exception
        assert app.select_slider[0].value == "30h 00m"

    def test_dragging_the_slider_leaves_stops_untouched(self) -> None:
        """Dragging the goal re-paces running; it must not change any stop."""
        app = self._fresh_app()
        before = list(app.session_state["aid_times_100M"])
        app.select_slider[0].set_value("26h 00m").run()
        assert not app.exception
        assert app.session_state["aid_times_100M"] == before

    def test_reset_button_restores_defaults(self) -> None:
        """After changing the average and the goal, Reset returns the goal to
        28h, the average to 5, and every stop to the 5-minute default."""
        app = self._fresh_app()
        app.number_input[0].set_value(9.0).run()
        app.select_slider[0].set_value("25h 00m").run()
        app.button[0].click().run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"
        assert app.number_input[0].value == 5.0
        assert set(app.session_state["aid_times_100M"][:-1]) == {5.0}
        assert app.session_state["aid_times_100M"][-1] == 0.0

    def test_100k_distance_loads_and_renders_a_verdict(self) -> None:
        """Switching to the 100K loads cleanly with its own 20h default and a
        make-it/miss-it verdict."""
        app = self._fresh_app()
        app.radio[0].set_value("100K").run()
        assert not app.exception
        assert app.select_slider[0].value == "20h 00m"
        assert app.success or app.error

    def test_100k_average_change_slides_its_goal(self) -> None:
        """On the 100K, raising the average stop slides the 100K goal later."""
        app = self._fresh_app()
        app.radio[0].set_value("100K").run()
        app.number_input[0].set_value(8.0).run()
        assert not app.exception
        assert app.select_slider[0].value != "20h 00m"

    def test_reset_works_after_dragging_the_slider(self) -> None:
        """Reset must restore the goal even after the slider was dragged — the
        case the keyed slider fixes."""
        app = self._fresh_app()
        app.select_slider[0].set_value("25h 00m").run()
        app.button[0].click().run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"
        assert set(app.session_state["aid_times_100M"][:-1]) == {5.0}

    def test_average_slides_goal_from_the_dragged_value(self) -> None:
        """After dragging to 26h, raising the average by 2 min across 25 stops
        slides the goal to 26h50m, not back from 28h."""
        app = self._fresh_app()
        app.select_slider[0].set_value("26h 00m").run()
        app.number_input[0].set_value(7.0).run()
        assert not app.exception
        assert app.select_slider[0].value == "26h 50m"

    def test_dragging_the_slider_shows_a_repace_note(self) -> None:
        """Dragging the goal posts a note that running re-paced, stops held."""
        app = self._fresh_app()
        app.select_slider[0].set_value("26h 00m").run()
        assert not app.exception
        assert "running pace adjusted" in st_note(app)

    def test_raising_the_average_shows_an_added_time_note(self) -> None:
        """Raising the average posts a note that the goal time slid later."""
        app = self._fresh_app()
        app.number_input[0].set_value(6.0).run()
        assert not app.exception
        assert "slid" in st_note(app) and "later" in st_note(app)
