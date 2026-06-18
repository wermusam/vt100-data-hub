# Vermont 100 Data Hub

A small web app for the [Vermont 100 Endurance Race](https://vermont100.com/),
built for the race director and for runners planning their day. It has two
tools:

- **Responsible Pace Chart.** Set a goal finish time and your time at each aid
  station, and see whether you clear every cutoff, how fast you have to run
  between stations, and how much cushion you have. Built on the race's real 2026
  cutoffs and aid-station codes (drop bags, handler access).
- **Returning Runners** and **Finishers of Both Distances.** Answer the race
  director's eligibility questions, like "who has finished at least 4 of the
  last 8 editions held?", grouped reliably by each runner's DUV ID.

For a fuller tour of how it works, the pacing method, and how it compares to
other tools, see [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md).

## Run it locally

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # install dependencies
uv run streamlit run app/Responsible_Pace_Chart.py
```

The app opens in your browser. The other pages appear in the sidebar.

## Deploy a public link (Streamlit Community Cloud)

The end goal is a link anyone can open on a phone.

1. Push this branch to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo,
   and set the main file to `app/Responsible_Pace_Chart.py`.
3. Streamlit installs from `requirements.txt` (which installs this package and
   its dependencies) and serves the app at a public URL.

The results database (`data/vt100.db`) is committed, so the deployed app has
its data with no extra setup.

## Run the tests

```bash
uv run pytest          # 168 tests
uv run ruff check .    # lint
```

## Layout

```
app/                  Streamlit pages (the website)
src/vt100_data_hub/   Core logic: DUV parsing, storage, queries, cutoffs, pacing
scripts/              One-off tools (populate the database, verify DUV IDs)
data/                 Cutoff CSVs and the committed results database
tests/                pytest suite (unit + live-page tests)
docs/                 Project overview
```

## Data source

Results come from [DUV](https://statistik.d-u-v.org), the public ultramarathon
statistics archive, covering Vermont 100 editions 2015–2025. Cancelled years
(2020, 2021, 2023) are excluded.
