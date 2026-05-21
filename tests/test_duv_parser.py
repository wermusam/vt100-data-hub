"""Tests for the DUV results parser."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from vt100_data_hub.duv import DUVParser

FIXTURE_2024_PATH = Path(__file__).parent / "fixtures" / "duv_2024_100m.html"
FIXTURE_2017_PATH = Path(__file__).parent / "fixtures" / "duv_2017_100m.html"


class TestParseFirstFinisher:
    """Tests for DUVParser.parse_first_finisher against the 2024 100M fixture."""

    def _load_fixture(self) -> str:
        """Read the saved 2024 100M HTML fixture."""
        return FIXTURE_2024_PATH.read_text(encoding="utf-8")

    def test_extracts_runner_name(self) -> None:
        """Rank-1 row should yield Sarah Gage."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.runner_name == "Gage, Sarah"

    def test_extracts_finish_time(self) -> None:
        """Rank-1 finish time should be 17:19:45."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.finish_time == timedelta(hours=17, minutes=19, seconds=45)

    def test_extracts_overall_rank(self) -> None:
        """Rank-1 row should report rank_overall = 1."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.rank_overall == 1

    def test_extracts_nationality(self) -> None:
        """Rank-1 finisher is from the USA."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.nationality == "USA"

    def test_extracts_year_of_birth(self) -> None:
        """Sarah Gage's YOB on DUV is 1995."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.year_of_birth == 1995

    def test_extracts_gender(self) -> None:
        """Sarah Gage is recorded as F."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.gender == "F"

    def test_extracts_category(self) -> None:
        """Sarah Gage was in the W23 age category in 2024."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.category == "W23"

    def test_extracts_duv_runner_id(self) -> None:
        """Sarah Gage's DUV runner ID is 1645043."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.duv_runner_id == 1645043

    def test_status_is_finish(self) -> None:
        """A finisher row always produces status FINISH."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.status == "FINISH"

    def test_year_and_distance_tagged(self) -> None:
        """Caller-provided year and distance are stored on the result."""
        parser = DUVParser()
        result = parser.parse_first_finisher(self._load_fixture(), year=2024, distance="100M")
        assert result.year == 2024
        assert result.distance == "100M"

class TestParseAllFinishers:
    """Tests for DUVParser.parse_all_finishers against the 2024 100M fixture."""

    def _load_fixture(self) -> str:
        """Read the saved 2024 100M HTML fixture."""
        return FIXTURE_2024_PATH.read_text(encoding="utf-8")

    def test_returns_a_list(self) -> None:
        """Parsing should return a list."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        assert isinstance(results, list)

    def test_returns_expected_finisher_count(self) -> None:
        """The 2024 100M fixture should yield 255 finishers."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        assert len(results) == 255

    def test_first_finisher_is_sarah_gage(self) -> None:
        """The first result should match the rank-1 finisher."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        assert results[0].runner_name == "Gage, Sarah"
        assert results[0].rank_overall == 1

    def test_rank_50_is_vail_rooney(self) -> None:
        """Spot-check: rank-50 finisher should be Vail Rooney."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        rank_50 = next(r for r in results if r.rank_overall == 50)
        assert rank_50.runner_name == "Rooney, Vail"

    def test_rank_100_is_carolyn_wisnowski(self) -> None:
        """Spot-check: rank-100 finisher should be Carolyn Wisnowski."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        rank_100 = next(r for r in results if r.rank_overall == 100)
        assert rank_100.runner_name == "Wisnowski, Carolyn"

    def test_all_results_tagged_with_year_and_distance(self) -> None:
        """Every parsed result should carry the year and distance we asked for."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        assert all(r.year == 2024 for r in results)
        assert all(r.distance == "100M" for r in results)

    def test_all_results_have_finish_status(self) -> None:
        """parse_all_finishers should only produce status=FINISH rows."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2024, distance="100M")
        assert all(r.status == "FINISH" for r in results)



class TestParseAllFinishers2017:
    """Tests confirming the parser works against the 2017 100M fixture too.

    The parser was originally written for the 2024 page. These tests
    confirm DUV's page format is stable across years and the same parser
    handles 2017 without modification.
    """

    def _load_fixture(self) -> str:
        """Read the saved 2017 100M HTML fixture."""
        return FIXTURE_2017_PATH.read_text(encoding="utf-8")

    def test_returns_expected_finisher_count(self) -> None:
        """The 2017 100M fixture should yield 270 finishers."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2017, distance="100M")
        assert len(results) == 270

    def test_first_finisher_is_brian_rusiecki(self) -> None:
        """The 2017 winner is Brian Rusiecki."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2017, distance="100M")
        assert results[0].runner_name == "Rusiecki, Brian"
        assert results[0].rank_overall == 1

    def test_first_finisher_finish_time(self) -> None:
        """Brian Rusiecki's 2017 finish time is 15:12:28."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2017, distance="100M")
        assert results[0].finish_time == timedelta(hours=15, minutes=12, seconds=28)

    def test_year_tagging(self) -> None:
        """Every parsed result should be tagged year=2017."""
        parser = DUVParser()
        results = parser.parse_all_finishers(self._load_fixture(), year=2017, distance="100M")
        assert all(r.year == 2017 for r in results)