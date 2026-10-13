# `server_tables.sessions_master_cc`: session event log (session starts + foreground-segment lengths)

> **Engine:** Trino. Write `server_tables.sessions_master_cc` (no `delta.` prefix). **Category:** Engagement
> **Grain:** one row per deduplicated session-lifecycle event (`start` / `resume` / `length` / `app_pause`) per (date_field, gid, cli, rid, cc) — **not** one row per user-day and **not** one row per session. **Partition / mandatory date filter:** `date_field` (DATE, UTC).

> **Used by (BRIAN):** `investigate-engagement` D3 (per-user sessions / minutes distributions, zero-session DAU). Read `references/uld.md` first for the layer-wide rules.

## What it is
Event-level log of session activity for every game, built from raw session tracking events. It holds two kinds of rows: (1) **session starts** — raw `start` / `resume` events kept only if the gap since the user's previous `end` is > 300 s (or there is no preceding `end`), written with `seconds = 0`; (2) **time rows** — one `length` row per foreground segment (gids 10 and 20: `app_pause`) with `seconds` = that segment's length, so several per session. Raw `end` / `minimize` events are not carried. Population = all tracked users, including test rids and users not in DAU.

## When to use it — and when not to
- **Use for:** per-user session counts and time spent (distributions, p50/p90/p99, zero-session DAU); sessions / time for custom user sets (payers, install cohorts, network, country); first-session / D0 time; intra-day timing of sessions (`cc`); build-level engagement.
- **Don't use for:** headline sessions, time spent or sessions-per-DAU by standard dimensions — use Druid `chart_2524-vN`. Template 1 ties to chart_2524 **exactly** when you inner-join `derived_tables.dau_splits` and exclude `server_tables.test_rid_master_cc`; without those two steps totals come out slightly higher.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Key | No natural key — only the full row (date_field, gid, cli, rid, status, cc, seconds, build) is unique; several `length` rows can share one `cc` second. Aggregate to (date_field, gid, cli, rid) before any join. |
| Partition column | `date_field` (UTC date of `cc`) — **always filter on it**. |
| Freshness / lag | Loaded incrementally in batches: rows for a date keep arriving until ~D+5, and D-1 is partial. Use D-2 as the latest usable day and expect small upward revisions for ~5 days. |
| Types | `gid`, `cli`, `seconds` INTEGER; `cc` BIGINT; `date_field` DATE; `inserted_at` TIMESTAMP(3) WITH TIME ZONE; `rid`, `status`, `build` VARCHAR. Use unquoted int literals (`gid = 22`). |

## Rollups, mandatory pins & gotchas
- **Rows ≠ sessions.** `length` / `app_pause` rows are per foreground segment (several per session). Never `COUNT(*)` for sessions; sessions = `count_if(status <> 'length')`.
- **Always cap `seconds`.** Some `length` rows carry an epoch timestamp (`seconds = cc`, ≈1.7–1.8e9), concentrated in newer gids (39, 45, 51, 60; also 22, 42, 43); an uncapped SUM is garbage. Use the chart_2524 cap `seconds BETWEEN 0 AND 100000` (gid 20: `0 AND 7200`) — rows outside are dropped, not truncated. This also removes the rare negatives. Some team pipelines use 43200; the difference is negligible.
- **Per-gid session definition:**
  - **gid 20 (Word Bingo):** no `start` / `resume` rows. Sessions = `app_pause` count, i.e. pause events — not comparable to other games.
  - **gid 10 (Word Wars):** has both `start` and `app_pause`. chart_2524 counts **both**, giving sessions/DAU several times higher than counting only `start` / `resume` (which some team pipelines do). State which definition you use.
  - **All other gids:** time from `length`, sessions from `start` + `resume`. Only gids 10, 18, 24, 26, 33, 48, 49, 53 emit `resume`.
- **`start` is a deduplicated session start** (300-s inactivity rule), far fewer than raw start events. Because the gap is computed within each load batch, sessions may be slightly over-counted.
- **Midnight-spanning sessions:** time is booked on the day the `length` event fires, so some users have time but zero `start` rows. chart_2524 `session_users` = DAU rids with *any* in-cap row, not ≥1 start.
- **Not every DAU has a row**, and some rids here are not in DAU. LEFT JOIN from `dau_splits` and `coalesce(…, 0)`.
- **Test rids are included** — exclude `rid NOT IN (SELECT rid FROM server_tables.test_rid_master_cc)` to tie to charts.
- **`cc` is NULL before 2023-01-01** (column added then).
- **`build = '0'`** = unknown build. `build` is per event; users can change build intra-day.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| date_field | DATE | Date (partition) | UTC date of the event (`cc`). Always filter. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| rid | VARCHAR | Key | Playsimple user id (= `refid` in `analytics.adjust_installs`). |
| status | VARCHAR | Dimension | `start` (session start, seconds = 0), `resume` (session start after > 300 s gap, seconds = 0), `length` (foreground-segment length), `app_pause` (gids 10, 20 only: segment length). |
| build | VARCHAR | Dimension | App build at event time; `'0'` = unknown. |
| seconds | INTEGER | Metric | Foreground-segment length in seconds; 0 on start / resume rows. SUM only after the cap. |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Batch load time; several per partition. Freshness checks only. |
| cc | BIGINT | Date | Event epoch seconds (UTC); not unique. NULL before 2023-01-01. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Sessions (chart_2524 definition) | `count_if({status} <> 'length')` with `{seconds} BETWEEN 0 AND cap` | cap = 7200 for gid 20, else 100000. gid 10 includes `app_pause`; gid 20 = `app_pause` only. |
| Time spent (s) | `SUM({seconds})` with `{seconds} BETWEEN 0 AND cap` | Start / resume rows contribute 0, so summing all in-cap rows is safe. |
| Session users | `COUNT(DISTINCT {rid})` with ≥1 in-cap row, inner-joined to DAU | Matches chart_2524 `session_users`. |
| Sessions per DAU | sessions / DAU | DAU = distinct rid in `derived_tables.dau_splits` (test rids excluded), not distinct rid of this table. |
| Minutes per DAU | time spent / 60 / DAU | Same denominator. |
| Session bucket | per-user sessions → S00, S01, S02, S03-S05, S06-S10, S10+ | DAU with no session row → S00 (LEFT JOIN + coalesce). |

## Join recipes
**Key:** `s.date_field = t.<date column> AND s.gid = t.gid AND s.cli = t.cli AND s.rid = t.rid` (INTEGER / INTEGER / VARCHAR — no casts). Aggregate this table to (date_field, gid, cli, rid) **first**; raw rows fan out the other side.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | One row per user-day; DAU denominator and segments (cohort, payer_flag, country, install_source …). Drive from it with LEFT JOIN. |
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | Pre-aggregate to the user-day. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | Dedupe with `MAX(cash)` per user-day first. |
| `server_tables.engagement_puzzle_master_cc_col`, `server_tables.economy_master_cc` | `date_field` | Multi-row per user-day — aggregate them first too. |
| `analytics.adjust_installs` | `installed_date` | `a.refid = s.rid`; dedupe adjust per `(gid, cli, refid)` first. |
| `server_tables.test_rid_master_cc` | — | Exclude its `rid`s to tie to charts. |
| `derived_tables.revenue_reports` | — | **No user-level join** (no `rid`); compare only as aggregates on date / gid / cli / lowercase country. |

## Query templates (all executed successfully)

**1. Sessions/DAU and minutes/DAU per day × platform (ties to chart_2524)**
```sql
WITH s AS (
  SELECT date_field, gid, cli, rid,
         count_if(status <> 'length') AS sessions,
         sum(CAST(seconds AS BIGINT)) AS secs
  FROM server_tables.sessions_master_cc
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}'
    AND gid = {gid}
    AND seconds BETWEEN 0 AND (CASE WHEN gid = 20 THEN 7200 ELSE 100000 END)
  GROUP BY 1,2,3,4),
d AS (
  SELECT DISTINCT dau_date, gid, cli, rid
  FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND rid NOT IN (SELECT rid FROM server_tables.test_rid_master_cc))
SELECT d.dau_date, d.cli,
       count(DISTINCT d.rid) AS dau,
       count(s.rid) AS session_users,
       sum(coalesce(s.sessions, 0)) AS sessions,
       round(sum(coalesce(s.sessions, 0)) * 1e0 / count(DISTINCT d.rid), 3) AS sessions_per_dau,
       round(sum(coalesce(s.secs, 0)) / 60e0 / count(DISTINCT d.rid), 2) AS minutes_per_dau
FROM d LEFT JOIN s
  ON s.date_field = d.dau_date AND s.gid = d.gid AND s.cli = d.cli AND s.rid = d.rid
GROUP BY 1,2 ORDER BY 1,2
```

**2. Session-count distribution of DAU (chart_2524 buckets)**
```sql
WITH s AS (
  SELECT date_field, gid, cli, rid, count_if(status <> 'length') AS sessions
  FROM server_tables.sessions_master_cc
  WHERE date_field = DATE '{end_date}' AND gid = {gid}
    AND seconds BETWEEN 0 AND (CASE WHEN gid = 20 THEN 7200 ELSE 100000 END)
  GROUP BY 1,2,3,4),
d AS (SELECT DISTINCT dau_date, gid, cli, rid FROM derived_tables.dau_splits
      WHERE dau_date = DATE '{end_date}' AND gid = {gid}),
u AS (SELECT d.rid, coalesce(s.sessions, 0) AS sessions
      FROM d LEFT JOIN s ON s.date_field = d.dau_date AND s.gid = d.gid AND s.cli = d.cli AND s.rid = d.rid)
SELECT CASE WHEN sessions = 0 THEN 'S00' WHEN sessions = 1 THEN 'S01' WHEN sessions = 2 THEN 'S02'
            WHEN sessions BETWEEN 3 AND 5 THEN 'S03-S05' WHEN sessions BETWEEN 6 AND 10 THEN 'S06-S10'
            ELSE 'S10+' END AS session_bucket,
       count(DISTINCT rid) AS users,
       round(count(DISTINCT rid) * 100e0 / sum(count(DISTINCT rid)) OVER (), 2) AS pct_of_dau
FROM u GROUP BY 1 ORDER BY 1
```

**3. Segment cut — payer × user age via dau_splits**
```sql
WITH s AS (
  SELECT date_field, gid, cli, rid,
         count_if(status <> 'length') AS sessions,
         sum(CAST(seconds AS BIGINT)) AS secs
  FROM server_tables.sessions_master_cc
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND seconds BETWEEN 0 AND (CASE WHEN gid = 20 THEN 7200 ELSE 100000 END)
  GROUP BY 1,2,3,4),
d AS (SELECT dau_date, gid, cli, rid, payer_flag, cohort
      FROM derived_tables.dau_splits
      WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid})
SELECT d.dau_date, d.payer_flag,
       CASE WHEN d.cohort IN ('D00','D01','D02-D07') THEN 'D0-D7' ELSE 'D8+' END AS age,
       count(DISTINCT d.rid) AS dau,
       round(sum(coalesce(s.sessions, 0)) * 1e0 / count(DISTINCT d.rid), 2) AS sessions_per_dau,
       round(sum(coalesce(s.secs, 0)) / 60e0 / count(DISTINCT d.rid), 1) AS minutes_per_dau
FROM d LEFT JOIN s ON s.date_field = d.dau_date AND s.gid = d.gid AND s.cli = d.cli AND s.rid = d.rid
GROUP BY 1,2,3 ORDER BY 1,2,3
```

**4. Per-user time-spent percentiles (users with any in-cap row)**
```sql
WITH s AS (
  SELECT date_field, gid, cli, rid,
         sum(CAST(seconds AS BIGINT)) AS secs,
         count_if(status <> 'length') AS sessions
  FROM server_tables.sessions_master_cc
  WHERE date_field = DATE '{end_date}' AND gid = {gid}
    AND seconds BETWEEN 0 AND (CASE WHEN gid = 20 THEN 7200 ELSE 100000 END)
  GROUP BY 1,2,3,4)
SELECT cli, count(DISTINCT rid) AS users_with_rows,
       approx_percentile(secs / 60e0, ARRAY[0.5, 0.9, 0.99]) AS minutes_p50_p90_p99,
       approx_percentile(sessions, ARRAY[0.5, 0.9, 0.99]) AS sessions_p50_p90_p99,
       round(avg(CASE WHEN secs = 0 THEN 1e0 ELSE 0 END), 4) AS zero_time_share
FROM s GROUP BY 1 ORDER BY 1
```
