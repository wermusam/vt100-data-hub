# Verifying the 2026 Cutoffs

Everything in the Responsible Pace Chart is computed from two files:

- `data/cutoffs_2026_100m.csv` (100 mile)
- `data/cutoffs_2026_100k.csv` (100K)

The code that reads them is correct and tested. What still needs a human
eye is whether the **numbers in those files match the official published
2026 schedule**. If a single close time is wrong, every arrival, buffer,
and verdict downstream of it is wrong too. This page lists exactly what
the files currently say so you (or Amy) can tick each row against the
official sheet.

## Things to confirm first

- **Start times.** The chart assumes the 100 mile starts at **4:00 AM**
  and the 100K at **9:00 AM**. These are set in the page, not the CSV.
- **The 100K shares aid stations and close times with the 100 mile.** The
  same physical station closes at the same clock time for both races, so
  the close-time column should match between the two files for shared
  stations. The mileage differs because the courses differ.
- **Drop bag / handler / unmanned codes** in the TYPE column drive the 🎒
  markers, so confirm those too.

## 100 mile  (start 4:00 AM)

| ✓ | # | Aid Station | Mile | Opens | Closes | Type | Hours from start |
|---|---|---|---|---|---|---|---|
| ☐ | 1 | Densmore Hill | 7.4 | 4:35 AM | 6:15 AM | U | 2h 15m |
| ☐ | 2 | Dunham Hill | 12.0 | 5:15 AM | 7:35 AM | UP | 3h 35m |
| ☐ | 3 | Taftsville Bridge | 15.5 | 5:45 AM | 8:40 AM | AE | 4h 40m |
| ☐ | 4 | So. Pomfret | 17.5 | 6:05 AM | 9:15 AM | U | 5h 15m |
| ☐ | 5 | Pretty House | 21.5 | 6:40 AM | 10:25 AM | AHDP | 6h 25m |
| ☐ | 6 | U-Turn | 25.5 | 7:15 AM | 11:40 AM | U | 7h 40m |
| ☐ | 7 | Stage Rd | 31.2 | 8:05 AM | 1:20 PM | AE | 9h 20m |
| ☐ | 8 | Route 12 | 34.4 | 8:35 AM | 2:20 PM | A | 10h 20m |
| ☐ | 9 | Lincoln Covered Bridge | 39.4 | 9:15 AM | 3:50 PM | AHDP | 11h 50m |
| ☐ | 9a | Barr House | 41.8 | 9:40 AM | 4:30 PM | U | 12h 30m |
| ☐ | 10 | Lillians | 44.9 | 9:30 AM | 5:30 PM | AP | 13h 30m |
| ☐ | 11 | Camp 10 Bear | 47.6 | 10:00 AM | 6:15 PM | AHDP | 14h 15m |
| ☐ | 12 | Pinky's | 50.7 | 10:25 AM | 7:10 PM | AE | 15h 10m |
| ☐ | 13 | Birminghams | 54.2 | 11:00 AM | 8:15 PM | A | 16h 15m |
| ☐ | 14 | Margaritaville | 58.8 | 11:30 AM | 9:40 PM | AHDP | 17h 40m |
| ☐ | 15 | Puckerbrush | 62.0 | 12:00 PM | 10:35 PM | APE | 18h 35m |
| ☐ | 16 | Brown School House | 65.0 | 12:30 PM | 11:30 PM | A | 19h 30m |
| ☐ | 17 | Camp 10 Bear | 69.7 | 1:00 PM | 12:55 AM | AHDP | 20h 55m |
| ☐ | 18 | Seabrook | 74.1 | 1:45 PM | 2:15 AM | U | 22h 15m |
| ☐ | 19 | Spirit of 76 | 76.6 | 2:00 PM | 3:00 AM | AHDP | 23h 00m |
| ☐ | 20 | Goodman's | 80.5 | 2:30 PM | 4:10 AM | U | 24h 10m |
| ☐ | 21 | Cow Shed | 83.5 | 3:00 PM | 5:00 AM | APE | 25h 00m |
| ☐ | 22 | Bill's | 88.6 | 3:30 PM | 6:35 AM | AHDP | 26h 35m |
| ☐ | 23 | Keating's | 91.5 | 4:00 PM | 7:25 AM | A | 27h 25m |
| ☐ | 24 | Polly's | 95.5 | 4:30 PM | 8:40 AM | AHDP | 28h 40m |
| ☐ | 25 | FINISH LINE | 100.0 | 5:00 PM | 10:00 AM | AHDP | 30h 00m |

Total time limit: **30h 00m** (finish closes 10:00 AM).

## 100K  (start 9:00 AM)

| ✓ | # | Aid Station | Mile | Opens | Closes | Type | Hours from start |
|---|---|---|---|---|---|---|---|
| ☐ | 10 | Lillians | 7.1 | 9:30 AM | 5:30 PM | AP | 8h 30m |
| ☐ | 11 | Camp 10 Bear | 9.8 | 10:00 AM | 6:15 PM | AHDP | 9h 15m |
| ☐ | 12 | Pinky's | 12.9 | 10:25 AM | 7:10 PM | AE | 10h 10m |
| ☐ | 13 | Birminghams | 16.4 | 11:00 AM | 8:15 PM | A | 11h 15m |
| ☐ | 14 | Margaritaville | 21.0 | 11:30 AM | 9:40 PM | AHDP | 12h 40m |
| ☐ | 15 | Puckerbrush | 24.2 | 12:00 PM | 10:35 PM | APE | 13h 35m |
| ☐ | 16 | Brown School House | 27.2 | 12:30 PM | 11:30 PM | A | 14h 30m |
| ☐ | 17 | Camp 10 Bear | 31.9 | 1:00 PM | 12:55 AM | AHDP | 15h 55m |
| ☐ | 18 | Seabrook | 36.3 | 1:45 PM | 2:15 AM | U | 17h 15m |
| ☐ | 19 | Spirit of 76 | 38.8 | 2:00 PM | 3:00 AM | AHDP | 18h 00m |
| ☐ | 20 | Goodman's | 42.7 | 2:30 PM | 4:10 AM | U | 19h 10m |
| ☐ | 21 | Cow Shed | 45.7 | 3:00 PM | 5:00 AM | APE | 20h 00m |
| ☐ | 22 | Bill's | 50.8 | 3:30 PM | 6:35 AM | AHDP | 21h 35m |
| ☐ | 23 | Keating's | 53.7 | 4:00 PM | 7:25 AM | A | 22h 25m |
| ☐ | 24 | Polly's | 57.7 | 4:30 PM | 8:40 AM | AHDP | 23h 40m |
| ☐ |  | FINISH LINE | 62.2 | 5:00 PM | 10:00 AM | AHDP | 25h 00m |

Total time limit: **25h 00m** (finish closes 10:00 AM).

## If a number is wrong

Edit the value in the CSV and re-run the tests (`uv run pytest`). The
chart, table, and graph all recompute from the file, so no code changes
are needed for a corrected time or mileage.
