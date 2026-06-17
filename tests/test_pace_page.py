"""Tests for the Pace Planner page.

These drive the real Streamlit page through Streamlit's AppTest harness so the
slider-and-stops wiring is exercised exactly as a runner would, without a
browser. The model under test: the plan is built backward from the cutoffs, the
baseline stop is absorbed so the default never misses, and stop time above the
baseline is additive and can cause a miss.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

PACE_PAGE = str(
    Path(__file__).parent.parent / "app" / "Responsible_Pace_Chart.py"
)


class TestPacePlannerPage:
    """The page renders and the goal slider and stops behave per the model."""

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

    def test_thirty_hour_goal_clears_every_cutoff(self) -> None:
        """The whole point: the slowest goal (30h) with default stops makes it,
        instead of clipping a late cutoff."""
        app = self._fresh_app()
        app.select_slider[0].set_value("30h 00m").run()
        assert not app.exception
        assert app.success and not app.error

    def test_raising_average_keeps_the_goal_slider(self) -> None:
        """Changing the average stop does not move the goal slider; the goal is
        the runner's target, stops are separate."""
        app = self._fresh_app()
        app.number_input[0].set_value(8.0).run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"

    def test_too_much_aid_time_shows_a_miss(self) -> None:
        """Stop time well above the baseline pushes later arrivals past their
        cutoffs and shows a miss (red)."""
        app = self._fresh_app()
        app.number_input[0].set_value(30.0).run()
        assert not app.exception
        assert app.error and not app.success

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

    def test_reset_works_after_dragging_the_slider(self) -> None:
        """Reset must restore the goal even after the slider was dragged."""
        app = self._fresh_app()
        app.select_slider[0].set_value("25h 00m").run()
        app.button[0].click().run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"
        assert set(app.session_state["aid_times_100M"][:-1]) == {5.0}

    def test_thirty_hour_floor_arrives_early_and_leaves_on_time(self) -> None:
        """At the 30h floor with 5-min stops you arrive 5 min before every cutoff
        and leave right at it — so you make it, the arrival caption shows, and
        there is NO leave-after-closing warning."""
        app = self._fresh_app()
        app.select_slider[0].set_value("30h 00m").run()
        assert not app.exception
        assert app.success
        assert any("arriving" in c.value for c in app.caption)
        assert not any("leave after closing" in w.value for w in app.warning)

    def test_switching_distance_and_back_starts_clean(self) -> None:
        """Customizing 100M, switching to 100K, and returning must give 100M's
        clean defaults, not a goal drifted by purged widget state."""
        app = self._fresh_app()
        app.number_input[0].set_value(10.0).run()
        app.select_slider[0].set_value("26h 00m").run()
        app.radio[0].set_value("100K").run()
        app.radio[0].set_value("100M").run()
        assert not app.exception
        assert app.select_slider[0].value == "28h 00m"
        assert app.number_input[0].value == 5.0
        assert set(app.session_state["aid_times_100M"][:-1]) == {5.0}

    def test_100k_distance_loads_and_clears_at_default(self) -> None:
        """Switching to the 100K loads cleanly at its 23h default and makes it."""
        app = self._fresh_app()
        app.radio[0].set_value("100K").run()
        assert not app.exception
        assert app.select_slider[0].value == "23h 00m"
        assert app.success and not app.error

    def test_100k_average_change_keeps_its_goal(self) -> None:
        """On the 100K, changing the average stop does not move the goal."""
        app = self._fresh_app()
        app.radio[0].set_value("100K").run()
        app.number_input[0].set_value(8.0).run()
        assert not app.exception
        assert app.select_slider[0].value == "23h 00m"
