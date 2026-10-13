---
name: w2e-incremental-reach-cohort
description: "Calculate incremental, unique w2e users/install for D0, D1..D30 cohort Specify game, platform and geo"
---

# W2E Incremental Reach — Cohort-Tracked

Answers "of the users who installed on day X, what % watched W2E for the first time on their D1?
D2-D7?" — tracked per exact install date, not approximated from daily age-bucket rollups.

## Why this exists, and when NOT to use it

`chart_2077-vN` (Druid; used by `game-performance-verdict`) tags each row with a `cohort` age-bucket
computed from `time` (event date), pre-aggregated across users. It's fast and fine for **daily
trend/dashboard** questions ("what's D2-D7 W2E reach looking like this week"). But it has two
things it structurally cannot do:

1. **True de-duplication across a multi-day bucket.** A D02-D07 row's `users` field is a *daily*
   unique count; summing it across days double-counts anyone active on more than one day in that
   window. `game-performance-verdict` will hand you this number if asked for "unique users" without
   qualification — it is not wrong, but it is **user-days**, not unique people. Flag this whenever
   it's the source.
2. **Incremental/new-only watchers.** Cannot tell you whether a D02-D07 watcher already watched on
   D00 or D01, because it never resolves to a person — only a daily count.

This skill fixes both by resolving every event to an exact `rid` and an exact `install_date`, so
"unique" and "new" mean what they say. It costs more (row-level joins over `rid`), so scope the
date range the user actually needs rather than defaulting to a huge window.

## Core tables

| Table | Grain | Use |
|---|---|---|
| `hive_metastore.psg_users.rid_info` | one row per `rid` (+gid, cli, country, install_date, install_bucket, install_source) | exact install-date cohort membership — this is what makes the whole approach possible |
| `hive_metastore.dm_admon.user_ad_funnel` | one row per (rid, dau_date, ad_type, funnel_type, ...) | W2E watch events. Filter `ad_type='w2e'`, `funnel_type='view'` (= an ad actually shown/watched; other values include `view_request`, `video_completed`, `grant` — ask if the user wants completions or grants instead of views) |
| `hive_metastore.dm_admon.ilrd_rev_master_cc` | one row per (rid, date_field, ad_type, network, ...) with a `revenue` column | W2E revenue at user grain, for the revenue-per-watcher variant |

**Gotchas:**
- `country` is lowercase (`'us'`, not `'US'`) in all three tables.
- Always exclude `install_bucket = 'reject'` and `install_source = 'untrusted'` (default fraud/QA
  exclusion — matches the convention used elsewhere in the portfolio's Databricks views).
- `rid_info` install counts run ~0.1-0.5% below `chart_1706`'s `installs` field (ETL timing, not a
  bug) — when doing this cohort-tracked join, use `rid_info`'s own `COUNT(DISTINCT rid)` as the
  denominator, not `chart_1706`, so numerator and denominator come from the same population.
- Resolve game name → `gid` from the game-name mapping in `game-performance-verdict`'s SKILL.md
  (no clean lookup table exists). `cli`: Android=0, iOS=1.

## Method

### Step 1 — Build the exact install cohort
```sql
installs_base: DISTINCT rid, install_date FROM rid_info
  WHERE gid=<gid> AND cli=<cli> AND country='<country>'
    AND install_date BETWEEN <start> AND <end>
    AND install_bucket <> 'reject' AND install_source <> 'untrusted'
installs_count: COUNT(DISTINCT rid) GROUP BY install_date
```

### Step 2 — Pull W2E watch events and join to the exact install date
```sql
w2e_events: DISTINCT rid, dau_date FROM user_ad_funnel
  WHERE ad_type='w2e' AND funnel_type='view' AND same gid/cli/country/exclusions
joined: installs_base JOIN w2e_events ON rid
  day_offset = DATEDIFF(dau_date, install_date), keep 0-30
```

### Step 3a — GROSS unique watchers per window
Bucket every row in `joined` by `day_offset` (D00=0, D01=1, D02-D07=2-7, D08-D14=8-14,
D15-D30=15-30), then `COUNT(DISTINCT rid)` per (install_date, bucket). This is "how many people
were active in this window," repeats included.

### Step 3b — INCREMENTAL/NEW unique watchers per window (the one that answers "new users")
Do **not** bucket every row. First collapse to `MIN(day_offset)` per (install_date, rid) — i.e.
each user's first-ever W2E watch — **then** bucket that single value. `COUNT(DISTINCT rid)` per
(install_date, bucket) now gives users whose *first* watch fell in that window, with no double
counting of repeat watchers across windows. This is the number that must be used whenever the
person says "new," "incremental," "first-time," or asks "how many *additional* users."

Never present 3a as if it were 3b. If asked for one and you're not sure which, ask — the two can
differ by 2-3x from D02-D07 onward (repeat watchers dominate gross reach quickly).

### Step 4 — Ratio, with a full grid (don't drop zero-watcher days)
`ratio = unique_or_new_users / installs_count` per (install_date, bucket). Build install_date ×
bucket as a full cross join before joining watcher counts, so an install date with zero D08-D14
watchers contributes a true `0` to the average rather than being silently absent.

### Step 5 — Maturity gate, then average
A bucket can only be averaged over install dates old enough for that window to have fully
elapsed as of the latest available `dau_date` (call it `max_date`):

| Bucket | Latest eligible install_date |
|---|---|
| D00 | `max_date` |
| D01 | `max_date - 1` |
| D02-D07 | `max_date - 7` |
| D08-D14 | `max_date - 14` |
| D15-D30 | `max_date - 30` |

Average `ratio` across all eligible install dates per bucket. Report `num_install_dates` alongside
so the person can see how much each bucket's average is resting on (D15-D30 will always have the
fewest observations).

### Step 5b — Sanity check
Compute both the per-date-averaged ratio and the pooled ratio (`SUM(new_users)/SUM(installs)`
across the eligible window). If they diverge by more than ~10-15%, a single high/low-install day is
skewing the average — flag it rather than silently reporting the averaged number.

### Optional — Revenue per watcher, same windows
Join `ilrd_rev_master_cc` (`ad_type='w2e'`, sum `revenue` per rid/date_field) the same way as Step
2, using **gross** unique watchers (3a) as the denominator, not incremental — revenue is earned by
anyone active that window, repeat or not. `rev_per_watcher = SUM(revenue) / COUNT(DISTINCT rid)`
per (install_date, bucket), averaged with the same maturity gate as Step 5.

## Multi-game comparison
Run the identical query (same date range, same `cli`, same country, swap `gid`) for each game and
present a single side-by-side table per metric — never blend platforms or countries across games in
one row. Call out where the gap is concentrated (early windows vs. late windows) rather than just
the cumulative number, since front-loaded vs. gradually-building reach implies different levers
(feature discovery/onboarding vs. long-tail engagement).

## Output format
Always report, per bucket: `num_install_dates`, the ratio (as % for reach metrics, $ for revenue),
and — for the incremental metric specifically — a one-line reminder of what "incremental" excludes,
since this is the metric most likely to be misread as gross reach in a follow-up question.

For a cumulative "% of installs who ever watch W2E within 30 days" figure, sum the five
**incremental** bucket percentages (never the gross ones — those double count).

## Non-negotiables
- **Incremental ≠ gross.** State which one you're reporting every time; don't let "unique" alone be
  read as "new."
- **Never sum gross bucket percentages into a cumulative figure** — only incremental buckets sum
  cleanly to a cumulative reach number.
- **Maturity-gate every bucket independently.** Comparing D15-D30 against install dates from last
  week silently reports on an incomplete window.
- **`country` is lowercase.** Exclude `reject`/`untrusted`.
- **State the exact `funnel_type` used** (default `view`) since `view_request` / `video_completed`
  / `grant` give materially different, non-interchangeable numbers.
- **Strictly per `cli`.** Never blend Android and iOS.