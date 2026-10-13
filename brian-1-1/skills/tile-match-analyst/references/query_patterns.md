# Tile Match — reusable query patterns

These are the recurring shapes found across the 19 source queries (funnels, retention, streak/DLR
cycles, engagement rollups, "what happened next" analyses). Read `tables_and_columns.md` first for
the schema; this file is the recipes built on top of it. Every pattern below generalizes what was a
one-off, hardcoded query in the source dump — reuse the shape, re-derive the specifics from the
current question and from `event_taxonomy_full.csv`.

## 1. Build the cohort/experiment base table first

Almost every analysis starts by materializing a base population as its own table, then builds
everything else on top of it (see `tables_and_columns.md` for the naming convention). Do this before
writing any funnel/engagement query — it's what lets every downstream query stay a simple join on
`(rid, date_field)`.

```sql
DROP TABLE IF EXISTS delta.play_zenconnect.${exp_name}$;
CREATE TABLE delta.play_zenconnect.${exp_name}$ AS
SELECT
    a.install_date, a.date_field, a.diff, a.country, a.network_name, a.rid, b.variant,
    a.user_flag, install_type, actual_diff
FROM (
    SELECT DISTINCT install_date, dau_date AS date_field, rid,
        CASE WHEN LOWER(country) IN (${country}$) THEN LOWER(country) ELSE 'others' END AS country,
        CASE WHEN cohort LIKE 'LD%' THEN 'LD120+' ELSE cohort END AS diff,          -- normalize long-dormant buckets
        CASE                                                                        -- network bucketing, see §2
            WHEN install_source IN ('adwords (others)', 'adwords (search)') THEN 'adwords'
            WHEN install_source IN ('digitalturbine','dt','ironsource_aura','dt_push','ironsource') THEN 'paid (preloads)'
            WHEN install_source IN ('tyrads','xiaomi','untrusted','untagged','molocoads',
                                     'digitalturbine_dsp','mistplay','prodege','tapjoy','liftoff','mintegral','gamelight') THEN 'others'
            WHEN install_bucket = 'paid' THEN install_source
            ELSE install_bucket
        END AS network_name,
        install_type, actual_diff,
        CASE WHEN install_date >= CAST('${start_date}$' AS DATE) THEN 'new_user' ELSE 'old_user' END AS user_flag
    FROM derived_tables.dau_splits
    WHERE dau_date BETWEEN CAST('${start_date}$' AS DATE) AND CAST('${end_date}$' AS DATE)
      AND CAST(gid AS INT) = 26 AND CAST(cli AS INT) IN (0, 1)
      AND install_bucket <> 'reject' AND LOWER(country) <> 'in'
) a
JOIN (                                                                              -- de-duped experiment allocation, see §3
    SELECT rid, variant, date_field FROM (
        SELECT rid, variant, date_field,
               ROW_NUMBER() OVER (PARTITION BY rid ORDER BY date_field ASC, cs DESC) AS rn
        FROM server_tables.experiments_master_cc_alldata
        WHERE CAST(experiment AS VARCHAR) = '${exp_name}$' AND CAST(version AS VARCHAR) = '${version}$'
          AND date_field BETWEEN CAST('${expt_start_date}$' AS DATE) AND CAST('${end_date}$' AS DATE)
          AND CAST(gid AS INT) = 26 AND CAST(cli AS INT) = ${cli}$
    ) WHERE rn = 1
) b
ON a.rid = b.rid AND a.date_field >= b.date_field
GROUP BY 1,2,3,4,5,6,7,8,9,10;
```

**Not every analysis is an experiment.** When there's no A/B test involved (a plain funnel/behavioral
question), drop the join to `experiments_master_cc_alldata` entirely and keep `variant` out of the
base table — several of the source queries (e.g. the "no matches available" / churn analyses) skip
it and just use `dau_splits` directly, sometimes filtering `LOWER(country) = 'us'` instead of
bucketing every country.

**Android/iOS often carry different experiment `version` numbers for the same test.** When a cohort
needs both platforms, union an Android branch (`cli IN (0)`, `version_And`) with an iOS branch
(`cli IN (1)`, `version_iOS`) rather than assuming one `version` covers both — see `0. base query.sql`
for the two-branch `UNION ALL` shape.

## 2. Network/source bucketing — reuse this CASE, don't re-derive it

The install-source-to-network normalization above (`adwords`, `paid (preloads)`, the "others" catch
list, else `install_source` if `install_bucket = 'paid'`, else `install_bucket`) is copied verbatim
across every query in this dump. Reuse it exactly rather than inventing a new bucketing — a different
grouping will silently break comparability with every past analysis on this game.

## 3. Funnel between two anchor points via `cc`-bucketing

`cc` orders events but isn't a timestamp, so "what happened between screen view A and the next screen
view" is computed by tagging a start event with the position of the *next* start event, then joining
any candidate "end" event that falls in that window:

```sql
WITH windows AS (
    SELECT date_field, rid, cc,
           ROW_NUMBER() OVER (PARTITION BY date_field, cli, rid ORDER BY cc) AS view_no,
           COALESCE(LEAD(cc) OVER (PARTITION BY date_field, cli, rid ORDER BY cc), 2542104414) AS next_cc
    FROM sub_tables.tracking_slice_zenconnect_trino
    WHERE date_field BETWEEN CAST('${expt_start_date}$' AS DATE) AND CAST('${end_date}$' AS DATE)
      AND CAST(gid AS INT) = ${gid}$ AND CAST(cli AS INT) = ${cli}$
      AND k = 'puzzle' AND o IN ('clear', 'fail')          -- the "start" event
)
SELECT a.date_field, a.rid, a.cc, view_no, MIN(COALESCE(b.cc, w.next_cc)) AS next_cc
FROM windows a
LEFT JOIN (
    SELECT date_field, rid, cc FROM sub_tables.tracking_slice_zenconnect_trino
    WHERE k = 'puzzle' AND o = 'view'                       -- the candidate "end" event
      -- ... same date/gid/cli filters
) b
ON a.rid = b.rid AND a.date_field = b.date_field AND b.cc BETWEEN a.cc AND a.next_cc
GROUP BY 1,2,3,4;
```

`2542104414` is the sentinel used throughout for "no next event this session/date" (an arbitrarily
large `cc`) — keep using the same sentinel so a funnel's tail bucket is comparable across analyses.

Once you have `(rid, date_field, cc, view_no, next_cc)` windows, join any other event type into that
window (`c.cc BETWEEN a.cc AND a.next_cc`) to see what happened inside it — this is how "home →
outro → leaderboard → next puzzle" multi-step funnels get built, one join per step, capped to a
`view_no <= N` (usually 3–50 depending on how deep the funnel needs to go).

## 4. "What did the user do next" pattern

For a single-anchor question ("what does a player do right after seeing 0 matches available"), rank
every later candidate event by `cc` and keep only the immediate next one:

```sql
WITH next_action AS (
    SELECT b.date_field, b.rid, b.cc, c.o,
           ROW_NUMBER() OVER (PARTITION BY b.date_field, b.rid, b.cc ORDER BY c.cc) AS rk
    FROM anchor_events b                                     -- e.g. k='puzzle' AND o='no_match_tile_highlight' AND f='view'
    LEFT JOIN sub_tables.tracking_slice_zenconnect_trino c
      ON b.date_field = c.date_field AND b.rid = c.rid AND c.cc > b.cc
     AND c.p = b.p AND c.c = b.c                              -- same pack/puzzle+seed context — keep it scoped to the SAME level
     AND c.o IN ('clear','fail','quit','tile_select','undo','wand','shuffle','extra_slot','revive')
)
SELECT * FROM next_action WHERE rk = 1;
```

Widen or narrow the candidate `o IN (...)` list depending on how granular the "next action" categories
need to be — the source queries run several variants of this (raw next action, next action restricted
to the same puzzle, next action collapsed to clear/fail outcome only, and a time-delta-bucketed
variant using `c.cc - b.cc`).

## 5. Retention / churn — paired-action recurrence

D0/D1/D3/D7-style retention on a specific in-game action (not just DAU) is computed by pairing a base
action (e.g. level `view`) with a target action (e.g. level `clear`) and counting users where the
target recurs within N days of the base:

```sql
SELECT b.levels, country, network_name, variant, COUNT(DISTINCT b.rid) AS base_users,
    COUNT(DISTINCT CASE WHEN e.date_field = b.date_field THEN e.rid END) AS d0_users,
    COUNT(DISTINCT CASE WHEN e.date_field BETWEEN b.date_field AND DATE_ADD('day', 7, b.date_field) THEN e.rid END) AS d7_users
FROM cohort a
JOIN base_action b ON a.rid = b.rid AND a.date_field = b.date_field
LEFT JOIN target_action e ON b.rid = e.rid AND e.date_field BETWEEN b.date_field AND DATE_ADD('day', 7, b.date_field)
                          AND b.levels = e.levels
GROUP BY 1,2,3,4;
```

The same shape also runs install-date-anchored (engagement within N days of `install_date`, filtering
`install_date <= DATE_ADD('day', -(N+1), CURRENT_DATE)` so every cohort has actually had N days to
mature) — see `lvl churn.sql`.

## 6. Streak / cycle-day calculation (DLR, Daily Victory)

Both the Daily Login Reward (`dlr`) day and the Daily Victory streak day are computed with the same
gap-and-island window pattern, then wrapped to a 7-day cycle:

```sql
WITH base AS (
    SELECT rid, dau_date, LAG(dau_date) OVER (PARTITION BY rid ORDER BY dau_date) AS prev_date
    FROM (SELECT DISTINCT date_field AS dau_date, rid FROM delta.play_zenconnect.${exp_name}$_local) a
), streak_break AS (
    SELECT rid, dau_date,
        CASE WHEN date_diff('day', prev_date, dau_date) = 1 THEN 0 ELSE 1 END AS new_streak
    FROM base
), streak_group AS (
    SELECT rid, dau_date, SUM(new_streak) OVER (PARTITION BY rid ORDER BY dau_date) AS streak_id
    FROM streak_break
), streak_day AS (
    SELECT rid, dau_date, ROW_NUMBER() OVER (PARTITION BY rid, streak_id ORDER BY dau_date) AS streak_day
    FROM streak_group
)
SELECT dau_date AS date_field, ((streak_day - 1) % 7) + 1 AS dlr_day, streak_day, rid FROM streak_day;
```

`streak_day` is the uninterrupted consecutive-active-days count (breaks to 1 on any gap);
`dlr_day` wraps it to the 1–7 reward-cycle position. There's a **stricter variant** used for the
"login_streak"/"daily_victory" trackers themselves (`k = 'login_streak' AND o IN ('dlr','daily_victory')`)
that requires the specific in-app action, not just DAU presence, to count toward the streak — check
which one the question needs (raw day-active streak vs. the actual reward-cycle progression the game
tracked server-side) before picking a base table.

## 7. Wide engagement rollup via `UNION ALL`

Rather than one big query with many joins, the source queries build a single `(date_field, rid,
action_, actions)` engagement table by `UNION ALL`-ing many small, independently-filtered
aggregations, then join that once into whatever cohort/funnel table needs it:

```sql
SELECT date_field, rid, o||'_view' AS action_, COUNT(DISTINCT cc) AS actions
FROM sub_tables.tracking_slice_zenconnect_trino WHERE k = 'dialog' AND o IN ('dlr','daily_victory') AND f = 'view'
GROUP BY 1,2,3
UNION ALL
SELECT date_field, rid, o AS action_, COUNT(DISTINCT cc) AS actions
FROM sub_tables.tracking_slice_zenconnect_trino WHERE k IN ('puzzle','dp','bonus_level') AND o IN ('view','clear')
GROUP BY 1,2,3
UNION ALL
SELECT date_field, rid, p AS action_, SUM(TRY_CAST(g AS DOUBLE)) AS actions      -- economy: earn/spend amounts
FROM sub_tables.tracking_slice_zenconnect_trino WHERE k = 'cash' AND p IN ('earn','spend')
GROUP BY 1,2,3
-- ... one UNION ALL branch per metric you want in the rollup
```

This is the pattern to extend when a new metric needs adding to an existing engagement table — add one
more `UNION ALL` branch with its own filter, don't restructure the joins.

## 8. Unassisted-clear filtering (powerup exclusion)

Engagement/difficulty analyses on levels often need "clears without powerup help" to compare raw
difficulty. Left-join clear events against powerup-success events on the same `(date, rid, level[,
seed, diff_preset])` key and keep only the unmatched side:

```sql
WITH pu_data AS (
    SELECT date_field, rid, split_part(p,'_',2) AS puzzle_id
    FROM sub_tables.tracking_slice_zenconnect_trino
    WHERE k = 'puzzle' AND o IN ('undo','wand','shuffle','revive','extra_slot') AND f = 'success'
    GROUP BY 1,2,3
)
SELECT DISTINCT a.date_field, a.rid, a.puzzle_id, clears
FROM clear_data a
LEFT JOIN pu_data b ON a.date_field=b.date_field AND a.rid=b.rid AND a.puzzle_id=b.puzzle_id
WHERE b.rid IS NULL;   -- pu_flag = 0, i.e. no powerup usage matched this clear
```

## 9. Monetization / ads funnels — the event shapes to filter on

- **IAP / store (OOC flow):** `k='dialog' AND o='store_page'` (popup shown, `f`=package id tapped) →
  `k='store' AND p='store_page' AND c IN ('start','success','fail')` (purchase attempt) →
  `k='store' AND p='store_page' AND c='grant'` (currency granted) → `k='store' AND
  p='receipt_to_appstore'` (receipt verification). A cancelled purchase surfaces as
  `k='store' AND o='purchase' AND f='failed'` with a platform error code in `g` (e.g. `-1005`).
- **Watch-to-earn (w2e):** `k='ad_tracking'/'ad_tracking_max' AND o='w2e'` for the ad-server side
  (`load`, `view_request`, `click`, `grant_approved`, `close`) and `k='dialog' AND o='w2e'` for the
  in-game click/success/grant/failure funnel (`f` = click/success/fail/grant; `g` distinguishes the
  surfacing context — revive, outro, store, puzzle — see the taxonomy for the exact `g` values per
  surface). "No video available" / "no internet" toasters are `k='dialog' AND o='w2e' AND f IN
  ('no_video_available','no_internet')`.
- **Interstitials:** `k='ad_tracking_max' AND p='interstitial' AND c IN ('view_request','view','close')`.

Cross-reference `event_feature_index.md`'s monetization/ads-tagged features for the full event list
before writing a new funnel — new live-ops events (Golden Tile, Sky Sprint, Picnic Rush, Stamps,
Streak Event a.k.a. "Lily's Adventure") each have their own w2e/economy touchpoints layered on top of
the base ones above.
