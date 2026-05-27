"""Vermont 100 Data Hub Streamlit app."""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

import streamlit as st

from vt100_data_hub.duv_events import DUVEventRegistry
from vt100_data_hub.formatting import DisplayFormatters
from vt100_data_hub.queries import RunnerQueries

DB_PATH = Path(__file__).parent.parent / "data" / "vt100.db"


class DataHubApp:
    """The Vermont 100 Data Hub Streamlit application.

    Attributes:
        db_path: Path to the SQLite database with race_results.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def render(self) -> None:
        """Render the data hub page."""
        st.set_page_config(
            page_title="Vermont 100 Data Hub",
            page_icon="🏃",
            layout="wide",
        )
        st.title("Vermont 100 Data Hub")
        st.subheader("Returning Runners — the 4-of-8 list")

        st.sidebar.header("Filters")
        distance = st.sidebar.radio(
            "Distance", options=["100M", "100K"], index=0
        )
        n = st.sidebar.slider(
            "Minimum finishes",
            min_value=1,
            max_value=8,
            value=4,
            help="How many times a runner must have finished to qualify.",
        )
        window = st.sidebar.slider(
            "Recent races to count",
            min_value=1,
            max_value=8,
            value=8,
            help=(
                "How many of the most recent editions to look at. "
                "Default 8 = all available."
            ),
        )

        st.markdown(
            f"This page lists every runner who has finished the Vermont 100 "
            f"**{distance}** at least **{n}** times in the last **{window}** "
            f"editions held. The race director uses this for the 4-of-8 "
            f"early-entry rule. (Cancelled years 2020, 2021, and 2023 are "
            f"excluded — only races actually held count.)"
        )

        with st.expander("How to read this page"):
            st.markdown(
                "- **Runner**: name as published by DUV.\n"
                "- **Finishes**: number of times this runner has finished "
                "in the selected window.\n"
                "- **Latest Year**: most recent year they finished.\n"
                "- **Years**: every year they finished within the window.\n\n"
                "The 4-of-8 rule means a runner who finished at least 4 of "
                "the last 8 editions held qualifies for early entry the "
                "following year."
            )

        registry = DUVEventRegistry()
        years_in_window = [
            year for year, _ in registry.last_n_editions(window, distance)
        ]
        st.caption(
            f"Counting these editions: {', '.join(str(y) for y in years_in_window)}"
        )

        connection = sqlite3.connect(self.db_path)
        queries = RunnerQueries(connection=connection, registry=registry)
        results = queries.runners_with_n_finishes(
            n=n, distance=distance, last_n_editions=window
        )

        formatter = DisplayFormatters()

        if not results:
            st.info(
                "No runners match these filters. "
                "Try lowering the minimum finishes or expanding the window."
            )
        else:
            st.markdown(f"**{len(results)} runners qualify**")
            table_data = [
                {
                    "Runner": formatter.format_name(name),
                    "Finishes": count,
                    "Latest Year": latest_year,
                    "Years": years_string.replace(",", ", "),
                }
                for name, count, latest_year, years_string in results
            ]
            st.dataframe(table_data, hide_index=True, width="stretch")

            csv_lines = ["Runner,Finishes,Latest Year,Years"]
            for name, count, latest_year, years_string in results:
                formatted_name = formatter.format_name(name)
                csv_lines.append(
                    f'"{formatted_name}",{count},{latest_year},"{years_string}"'
                )
            st.download_button(
                label="Download CSV",
                data="\n".join(csv_lines),
                file_name=f"vt100_returning_runners_{distance.lower()}.csv",
                mime="text/csv",
            )

        st.divider()
        total = connection.execute(
            "SELECT COUNT(*) FROM race_results"
        ).fetchone()[0]
        last_updated = datetime.datetime.fromtimestamp(
            self.db_path.stat().st_mtime
        ).strftime("%B %d, %Y")
        st.caption(
            f"Data source: [DUV](https://statistik.d-u-v.org). "
            f"Database last updated {last_updated}. "
            f"{total:,} finishers across all editions."
        )


DataHubApp().render()
