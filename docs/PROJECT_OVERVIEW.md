# Vermont 100 Data Hub — Project Overview

A plain-language tour of what this project does, how the pace math works, how
it compares to other tools, and what is and isn't done yet. Written so a runner
or the race director can read it without digging through code.

There are **two tools** here, answering two real Vermont 100 questions.

---

## 1. The Responsible Pace Chart (the planner)

**The question it answers:** *"At my goal time, will I beat every cutoff, and
how fast do I actually have to move between aid stations?"*

### How it works, in one idea

> **The plan is built backward from the cutoffs, so you never miss one by
> default.**

Each aid station's target arrival is its real cutoff clock scaled by your goal,
and the finish line is the endpoint you cross at your goal time. So a generous
section is run easier and a tight one harder, and at the slowest goal (30 hours,
the race limit) you arrive right at every cutoff and finish at exactly 30 hours.

You turn two knobs:

- **The goal slider** — your target finish (about 15 to 30 hours). Faster runs
  every leg quicker and gives more cushion; the slowest setting rides the
  cutoffs. It changes only your running pace, not your stops.
- **Aid-station time** — minutes at each stop (default 5 everywhere, editable
  per station). The first 5 minutes at each stop are built into the pace, so the
  default plan stays ahead of every cutoff. Spend *more* than that and it adds to
  your finish and eats your cushion (too much shows a red miss); spend *less* and
  you gain cushion. A table edit only shifts that station and the ones after it.

### What the runner sees

- A **make-it / miss-it verdict** at the top: green "you clear every cutoff,
  tightest is *Densmore Hill, 13 min*," or red "this plan misses the cutoff at
  *[station]*."
- A **line graph** of the plan against the cutoffs, with red/yellow/green
  cushion dots.
- A **table** of every aid station — cutoff, arrival, your stop, departure, and
  a **color-shaded buffer** (🔴 under 30 min, 🟡 30–60 min, 🟢 over 1 hour) that
  matches the graph.

The default goal is **28 hours**, not the 30-hour cutoff — a deliberate choice
so runners aim for a cushion rather than the edge.

### Why this beats a generic pace calculator

Most tools (see below) are general: you type a finish time and get even splits.
This one is **built on Vermont 100's actual published 2026 cutoffs and its own
aid-station codes** (drop bags 🎒, handler access, night sections). It tells you
*whether you survive*, station by station — the thing a road-race pace band
can't do. None of the general tools also carry the race's real cutoff data or a
returning-runner eligibility view.

---

## 2. Returning Runners + Finishers of Both Distances (the data hub)

**The question it answers (the race director's "4-of-8"):** *"Who has finished
at least 4 of the last 8 editions held?"* — the early-entry rule.

### How it works, and why it's trustworthy

- Results come from **DUV** (statistik.d-u-v.org), the deepest public Vermont
  100 archive, 2015–2025.
- Runners are grouped by their **DUV runner ID**, a stable identifier — **not by
  name**. This is the accuracy guarantee: two different people who share a name
  stay separate, and one person whose printed name changes (e.g. marriage)
  stays a single runner. Verified against the live database: 2,450 finishers,
  zero missing IDs, no duplicate IDs within an edition, no name drift.
- Cancelled years (2020, 2021 COVID; 2023 flooding) are **excluded**, so "last
  8 editions" counts editions *held*, not calendar years.
- A second page lists runners who've finished **both** the 100M and the 100K.

Both pages export CSV, so the race director can take the list and work with it.

---

## How the pacing method compares (research)

Pace charts and pace bands are an old, well-worn idea from road marathoning;
applying aid-station cutoff math is standard practice in race handbooks. This
tool automates what serious runners already do by hand on spreadsheets.

A few comparable tools exist, all more general than race-specific:

- **UltraPacer** — upload-a-course pacing with terrain/heat/night/fatigue
  factors; its most-requested feature is per-segment cheat sheets (which this
  tool already gives for VT100).
- **UltraSplits**, **Ultra Planner**, **Ready for Ultra**, **My Pace Chart** —
  split predictors and spreadsheet builders, not tied to a specific race's
  cutoffs.

**Does the method hold up?** It is a **cutoff-survival** tool, not a
performance-optimization pacer, and the page says so. Sports-science research is
consistent that **even or slightly-negative splits finish fastest** and runners
should bank time early. This tool guarantees you stay ahead of the cutoffs and
notes plainly that "most finishers run the first half with more cushion than
this," so a runner treats it as the floor, not the plan.

Sources: [UltraPacer](https://ultrapacer.com/) ·
[iRunFar pacing methods](https://www.irunfar.com/emergent-methods-for-determining-ultramarathon-race-day-pacing) ·
[Even pacing at UTMB (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7578994/) ·
[100 km pacing study (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4376307/)

---

## What's tested

161 automated tests cover the parser, storage, the 4-of-8 and both-distances
queries (including the same-name/name-change accuracy cases), the cutoff loader,
the cutoff-anchored pace math (never-miss at the baseline across the whole goal
range, additive extra-stop misses, forward-only stop edits), the make-it/miss-it
verdict, and the live page itself (slider, average, reset, both distances)
driven through Streamlit's test harness. The DUV event IDs have a separate
verification script.

---

## Honest gaps and natural next steps

- **An optional built-in longer night stop** (a drop-bag recovery default),
  still undecided.
- **A printable pace band / PDF** for race day — the artifact a race director
  forwards in a newsletter.
- **Verify the 2026 cutoff numbers** in `data/cutoffs_2026_100m.csv` against the
  official published schedule (the loader is correct; the source values need a
  human eyeball).
- **A "fade" pacing option** to match the even/negative-split research.

Nothing here is required for the core to be useful today — these are the
directions to grow it if the race director asks for more.
