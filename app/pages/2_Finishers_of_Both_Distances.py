"""Vermont 100 Data Hub — Finishers of Both Distances page."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from vt100_data_hub.duv_events import DUVEventRegistry
from vt100_data_hub.formatting import DisplayFormatters
from vt100_data_hub.queries import RunnerQueries

DB_PATH = Path(__file__).parent.parent.parent / "data" / "vt100.db"


@st.cache_data(show_spinner=False)
def _load_crossover_runners(
    db_path: str,
) -> list[tuple[str, int, int, str, str, int]]:
    """Load runners who finished both distances, cached and self-closing.

    Opens its own connection and closes it in a finally block, so no SQLite
    connection is leaked across Streamlit reruns.

    Args:
        db_path: Path to the SQLite database, as a string (cache key).

    Returns:
        The query's per-runner crossover rows.
    """
    connection = sqlite3.connect(db_path)
    try:
        queries = RunnerQueries(
            connection=connection, registry=DUVEventRegistry()
        )
        return queries.runners_who_did_both_distances()
    finally:
        connection.close()


class FinishersOfBothDistancesPage:
    """The Finishers of Both Distances page — runners with both 100M and 100K.

    Attributes:
        db_path: Path to the SQLite database with race_results.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def render(self) -> None:
        """Render the Finishers of Both Distances page."""
        st.set_page_config(
            page_title="Vermont 100 Data Hub",
            page_icon="🏃",
            layout="wide",
        )
        st.title("Finishers of Both Distances")
        st.subheader("Runners who've finished both the 100M and the 100K")
        st.markdown(
            "This page lists every runner who has finished at least one "
            "Vermont 100 **100M** *and* at least one Vermont 100 **100K**. "
            "Covers all editions we have data for since 2015 (cancelled years "
            "2020, 2021, and 2023 are excluded)."
        )

        if not self.db_path.exists():
            st.error(
                "The results database is missing, so runner data can't be "
                "loaded right now. If this was just deployed, make sure "
                "`data/vt100.db` is included in the repository."
            )
            return

        results = _load_crossover_runners(str(self.db_path))

        formatter = DisplayFormatters()

        if not results:
            st.info("No crossover runners found.")
        else:
            st.markdown(
                f"**{len(results)} runners have finished both distances**"
            )
            table_data = [
                {
                    "Runner": formatter.format_name(name),
                    "100M Finishes": m_count,
                    "100K Finishes": k_count,
                    "Total Finishes": m_count + k_count,
                    "Years (100M)": years_m.replace(",", ", "),
                    "Years (100K)": years_k.replace(",", ", "),
                    "Latest Year": latest_year,
                }
                for name, m_count, k_count, years_m, years_k, latest_year in results
            ]
            st.dataframe(table_data, hide_index=True, width="stretch")

            csv_lines = [
                "Runner,100M Finishes,100K Finishes,Total Finishes,"
                "Years (100M),Years (100K),Latest Year"
            ]
            for name, m_count, k_count, years_m, years_k, latest_year in results:
                formatted_name = formatter.format_name(name)
                csv_lines.append(
                    f'"{formatted_name}",{m_count},{k_count},'
                    f'{m_count + k_count},"{years_m}","{years_k}",{latest_year}'
                )
            st.download_button(
                label="Download CSV",
                data="\n".join(csv_lines),
                file_name="vt100_crossover_runners.csv",
                mime="text/csv",
            )

        st.divider()
        st.caption(
            "Data source: [DUV](https://statistik.d-u-v.org)."
        )


FinishersOfBothDistancesPage().render()
