"""Tests for the DUV results parser."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from vt100_data_hub.duv import DUVParser

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "duv_2024_100m.html"


class TestParseFirstFinisher:
    """Tests for DUVParser.parse_first_finisher against the 2024 100M fixture."""

    def _load_fixture(self) -> str:
        """Read the saved 2024 100M HTML fixture."""
        return FIXTURE_PATH.read_text(encoding="utf-8")

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