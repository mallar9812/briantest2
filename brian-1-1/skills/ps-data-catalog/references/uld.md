# User-Level Data (ULD) — Trino warehouse tables

The ULD layer is eight Trino warehouse tables at **user (`rid`) grain** (seven) or reported-revenue
grain (one). They answer what the pre-aggregated Druid charts cannot: distinct users, per-user
distributions, segment combinations no chart variant carries, and user-level joins across revenue,
sessions, engagement and economy. **Read this page first, pick the table from the routing table, then
read only that table's file under `references/uld/`.** Each table file holds: what it is, when to use it
and when not, verified grain and key, partition column, freshness, pins and gotchas, every column with
its observed values, metric formulas, join recipes, and query templates that were executed live.
Live data is the source of truth — if a table file and a live probe disagree, the probe wins.

> **Engine:** Trino (the `execute_query` tool). Write `schema.table` — never `delta.schema.table`.
> Typed literals (`DATE '2026-10-01'`). On every ULD table `gid` and `cli` are **INTEGER** — unquoted
> literals (`gid = 22`); `rid` is VARCHAR. `cli`: 0 = Android, 1 = iOS, 2 = Amazon
> (`revenue_reports` also has −1 = unknown).

## Rollups & mandatory pins (layer-wide)

- **Partition filter on every statement** — the column in the routing table below. These are
  multi-billion-row tables; a query filtered only on `install_date` scans the whole table.
- **Invalid traffic:** exclude `derived_tables.dau_splits.install_bucket = 'reject'` (join dau_splits) and
  say so. `sessions_master_cc` and `engagement_puzzle_master_cc_col` include test users — anti-join
  `server_tables.test_rid_master_cc` when tying to a chart.
- **Table-specific rollups/pins** (details in each file): `engagement_puzzle_master_cc_col`
  `puzzle_type = 'overall'` is a rollup for gids 10/20; `economy_master_cc` always filter `cash_type`
  (`'cash'` = coins); `revenue_reports` always filter `rev_type` (`earn` / `bookings` / `spend` / `tax`
  stack in one `amount` column); `adjust_installs` dedupe on `(gid, cli, refid)` before counting.

## Charts first, ULD second — the decision rule

**Every headline number still comes from the Druid chart** (`chart_579`, `chart_1170`, `chart_1706`,
`chart_2076`, `chart_2524`, `chart_2898`, `chart_2917`, …). Reach for ULD only when the question needs:

1. **Distinct users or a per-user distribution** — "% of DAU who spent coins", p50/p90 minutes, whale
   concentration, top-N users, zero-session DAU.
2. **A segment combination no chart variant carries** — payer × LAT × install_source × build, a campaign
   or creative, an arbitrary user list.
3. **A user-level join across domains** — revenue of heavy players, engagement of users with a large
   wallet, minutes per DAU of payers vs non-payers.
4. **Attribution detail below the chart grain** — Adjust campaign / adgroup / creative / device at install.
5. **Reported revenue by source × country** where `chart_2077` doesn't carry the cut, or a feed-lag
   check (`revenue_reports`).

ULD totals **do not tie exactly** to the charts (Adjust inner join in `dau_splits`, test-rid handling,
restatement timing, different IAP shares). Never put a ULD figure and a chart figure in one ratio or one
headline series. Label ULD numbers "user-level (ULD)", name the population filter, and when a chart
exists for the same metric, quote the chart figure as the headline and use ULD only for the cut.

## Routing — which table answers which question

| Question is about | Table | Grain / key | Partition filter | Read |
|---|---|---|---|---|
| User-day backbone: DAU with segments (install_source/bucket, cohort, payer, LAT, device, OS, ATT, build, language), next-day/day+3 return flags, custom cohorts. **Driving table for every user-level join.** | `derived_tables.dau_splits` | 1 row per `(dau_date, gid, cli, rid)` | `dau_date` | `uld/derived_tables.dau_splits.md` |
| Per-user revenue per day: ad revenue by format, impressions, IAP, cohort LTV by `diff`, payer/whale distributions, rev/DAU for custom segments | `dm_admon.rev_dau_install_diff_ilrd_v2` | 1 row per `(dau_date, gid, cli, rid)` | `dau_date` | `uld/dm_admon.rev_dau_install_diff_ilrd_v2.md` |
| Reported (network/store) revenue, net vs gross, by source × rev_type × country; UA spend; feed lag — **aggregate, no rid** | `derived_tables.revenue_reports` | `(report_date, gid, cli, country, rev_source, rev_type)` | `report_date` | `uld/derived_tables.revenue_reports.md` |
| Per-user in-game actions: clears, views, hints, plays by action_type × puzzle_type × build | `server_tables.engagement_puzzle_master_cc_col` | `(date_field, gid, cli, rid, action_type, build, puzzle_type)` | `date_field` | `uld/server_tables.engagement_puzzle_master_cc_col.md` |
| Per-user sessions & time spent, session-count / length distributions, intra-day timing | `server_tables.sessions_master_cc` | one row per session **event** (no key) | `date_field` | `uld/server_tables.sessions_master_cc.md` |
| Per-user virtual-currency earn / spend / purchase by source & sink | `server_tables.economy_master_cc` | `(date_field, gid, cli, rid, cash_type, earn_type, category, sub_category, build)` | `date_field` | `uld/server_tables.economy_master_cc.md` |
| Per-user wallet (coin) balance — level, by cohort age | `derived_tables.wallet_dau_install_diff` | `(dau_date, gid, cli, rid)` — **not unique, dedupe `MAX(cash)`** | `dau_date` | `uld/derived_tables.wallet_dau_install_diff.md` |
| Adjust install records: network / campaign / adgroup / creative / country / device / OS at install | `analytics.adjust_installs` | one row per Adjust **callback**; install = `(gid, cli, refid)` | `installed_date` | `uld/analytics.adjust_installs.md` |

## Where BRIAN uses it — skill × stage

ULD is a **drill layer**. It never runs at D0/D1 and never replaces a chart query. Each owning skill
reaches for it only at the stage named here, after the chart-level steps of that stage are done.

| Skill | Stage | Table(s) | Question it answers |
|---|---|---|---|
| `investigate-engagement` | D3 | `sessions_master_cc`, `engagement_puzzle_master_cc_col` (+ `dau_splits`) | Is the move breadth or depth — did fewer users play, or did the same users play less? p50/p90 minutes and clears per user, zero-session DAU share, heavy-player bucket shift |
| `investigate-engagement` | D3 | `economy_master_cc`, `wallet_dau_install_diff` | Did an economy change (hint price, reward size, wallet inflation) coincide with the move? % of DAU spending, sink mix, median wallet by cohort age |
| `investigate-rev-dau` | D3 | `rev_dau_install_diff_ilrd_v2` (+ `dau_splits`) | Concentration — did whales/payers or the broad base move? Per-user ad-revenue percentiles, impressions per user by format, payer vs non-payer rev/DAU |
| `investigate-rev-dau` | D2/D3 | `revenue_reports` | Reported revenue by `rev_source` × country when `chart_2077` lacks the cut; is a trailing dip a feed lag (APS, Apple Arcade, xpromo)? |
| `investigate-retention`, `investigate-rolling-retention` | D3 | `dau_splits`, `adjust_installs` | Mix questions the chart variants can't cut: campaign / creative / adgroup cohorts, combined segments (LAT × install_source × device), activity of a cohort on D0 (sessions/clears) vs its return |
| `analyst-game-performance` | D1-C / D2-R, on request | `adjust_installs`, `revenue_reports` | Campaign- or creative-level installs and D0/Dn revenue per install; reported revenue by source/country for a deck appendix |
| `analyst-general-questions` | D0 | this page + table files | "Which table has user-level X", column meanings, value sets — answered from the files without querying |
| `brian-investigator` agent | any D3 branch | per the hand-off | A ULD branch is a legitimate independent axis to fan out (e.g. "per-user distribution" next to "mix shift-share") |

## Rules that hold for every ULD table

1. **Freshness & restatement — default to D-2, and know the rewrite window:**

   | Table | Rewrite / late-arrival window | Notes |
   |---|---|---|
   | dau_splits | last 5 `dau_date`s | `d1_rr_flag` / `d3_rr_flag` are final only at ≤ today−5 |
   | rev_dau_install_diff_ilrd_v2 | last 15 `dau_date`s | `xpromo_rev` lags ~9–10 days |
   | revenue_reports | ~7–10 days of revisions | Apple Arcade & xpromo amounts lag ~9–10 days |
   | engagement_puzzle_master_cc_col | last ~5 dates | D-1 incomplete |
   | sessions_master_cc | rows keep landing to ~D+5 | D-1 partial |
   | economy_master_cc | last ~5 dates | — |
   | wallet_dau_install_diff | last 5 `dau_date`s | — |
   | adjust_installs | last ~10 event dates; installs keep landing for weeks | counts < ~14 days old are provisional |

2. **The user-day key is `(date, gid, cli, rid)`.** `dau_date` (dau_splits, rev, wallet) equals
   `date_field` (sessions, engagement, economy). `analytics.adjust_installs.refid` = `rid`.
   **Aggregate every multi-row table to one row per user-day before joining** — sessions (event grain),
   engagement and economy (many rows per user-day), wallet (duplicates), adjust (callbacks). Otherwise
   revenue and DAU fan out silently.
3. **`dau_splits` drives, activity tables LEFT JOIN onto it.** a small share of DAU have no sessions row; not
   every DAU has engagement or economy rows; zero is a real value for them. `dau_splits` is an Adjust
   inner join — it covers nearly all server DAU for most games but far less for a few (notably Word
   Trails, gid 28). State the coverage when it matters; never use it for those games' DAU.
4. **Additive vs level.** Revenue, actions, sessions, seconds, coins earned/spent, installs → sum.
   DAU → average per day (summing gives user-days). Wallet `cash` → median/percentiles of a balance,
   never summed across days or users as a "total".
4a. **Percentiles / medians are computed per cut.** Partition (or `GROUP BY`) by exactly the dimensions
   the question asks for — always including the date — and filter everything else. A percentile can't be
   summed, averaged or user-weighted into a coarser cut, and a coarser one can't be reused for a finer
   cut. When reading a pre-computed percentile output partitioned by many dimensions, filter **every**
   partition dimension to one value. Exact interpolated template: wallet file, template 4 (same pattern
   for minutes, clears, revenue per user).
5. **Per-game semantics are real.** Action types, puzzle types, cash types, session definitions and coin
   values differ by `gid`. Never compare raw engagement or economy values across games without the
   per-gid notes in the table file.
   The per-gid value lists in the table files (action types, puzzle types, cash types, mirrored
   categories) are **examples only** — new games and new values keep appearing and names change across
   builds, so confirm the live values for the gid and date window before filtering on them.
6. **Identifiers are join keys only.** `rid`, `adid`, `idfa`, `idfv`, `android_id` — never print them.
7. **Cost discipline.** Narrowest window that answers the question; one game unless the question is
   portfolio-wide; `approx_percentile` / `approx_distinct` for distributions; LIMIT on any row-level
   output. `COUNT(DISTINCT …)` is exact in Trino and fine at user-day grain.
8. **Timezone:** UTC where verified (`sessions_master_cc`, `adjust_installs`); inherited and unconfirmed
   on the rest.

## Canonical user-day join (verified)

The pattern every cross-domain ULD question builds on — `dau_splits` drives, each activity table is
pre-aggregated to the user-day, then LEFT JOINed:

```sql
WITH d AS (
  SELECT dau_date, gid, cli, rid, payer_flag
  FROM derived_tables.dau_splits
  WHERE dau_date = DATE '{date}' AND gid = {gid} AND install_bucket <> 'reject'),
r AS (
  SELECT dau_date, gid, cli, rid, SUM(total_rev) AS rev
  FROM dm_admon.rev_dau_install_diff_ilrd_v2
  WHERE dau_date = DATE '{date}' AND gid = {gid}
  GROUP BY 1,2,3,4),
s AS (
  SELECT date_field, gid, cli, rid,
         count_if(status <> 'length') AS sessions, SUM(CAST(seconds AS BIGINT)) AS secs
  FROM server_tables.sessions_master_cc
  WHERE date_field = DATE '{date}' AND gid = {gid}
    AND seconds BETWEEN 0 AND (CASE WHEN gid = 20 THEN 7200 ELSE 100000 END)
  GROUP BY 1,2,3,4),
e AS (
  SELECT date_field, gid, cli, rid,
         SUM(CASE WHEN action_type = 'clear' THEN actions ELSE 0 END) AS clears
  FROM server_tables.engagement_puzzle_master_cc_col
  WHERE date_field = DATE '{date}' AND gid = {gid}
  GROUP BY 1,2,3,4),
u AS (
  SELECT d.cli, d.payer_flag, d.rid, COALESCE(r.rev, 0) AS rev, COALESCE(s.sessions, 0) AS sessions,
         COALESCE(s.secs, 0) AS secs, COALESCE(e.clears, 0) AS clears
  FROM d
  LEFT JOIN r ON r.dau_date = d.dau_date AND r.gid = d.gid AND r.cli = d.cli AND r.rid = d.rid
  LEFT JOIN s ON s.date_field = d.dau_date AND s.gid = d.gid AND s.cli = d.cli AND s.rid = d.rid
  LEFT JOIN e ON e.date_field = d.dau_date AND e.gid = d.gid AND e.cli = d.cli AND e.rid = d.rid)
SELECT cli, payer_flag, COUNT(DISTINCT rid) AS dau,
       ROUND(SUM(rev) / COUNT(DISTINCT rid), 4)              AS rev_per_dau,
       ROUND(1e0 * SUM(sessions) / COUNT(DISTINCT rid), 2)   AS sessions_per_dau,
       ROUND(SUM(secs) / 60e0 / COUNT(DISTINCT rid), 1)      AS minutes_per_dau,
       ROUND(1e0 * SUM(clears) / COUNT(DISTINCT rid), 2)     AS clears_per_dau,
       ROUND(approx_percentile(secs / 60e0, 0.5), 1) AS p50_minutes
FROM u GROUP BY 1, 2 ORDER BY 1, 2
```

`clear` is the action name for gid 22 — check the engagement file's per-gid action matrix for other games.

## Cross-table facts worth knowing before you combine tables

- **Revenue definitions differ.** `rev_dau_install_diff_ilrd_v2.total_rev` = ad revenue + **0.7 × IAP**,
  xpromo excluded. `revenue_reports` `rev_type = 'earn'` = net (exactly `chart_579`); non-store `earn` +
  store `bookings` = gross (exactly `chart_1170`). ULD ad revenue runs about 1% above reported;
  ULD IAP runs higher than store reports (server purchase logs vs store reports).
- **Economy chart vs table.** `chart_2917` = `economy_master_cc` inner-joined to `dau_splits` — but the chart does not filter `cash_type`, so its totals mix coins with
  item counts. Use `cash_type = 'cash'` for coin questions.
- **Sessions recipe ties to `chart_2524` exactly** when joined to `dau_splits` with test rids excluded —
  use template 1 in the sessions file.
- **Wallet is not built from the economy table** — day-over-day wallet change won't reconcile with the
  economy net flow; don't try.
- **Adjust rows ≠ installs.** One row per callback — dedupe on `(gid, cli, refid)`. Ignore `event_type`
  (never filter on it). Network names agree across `adjust_installs`, `rev_dau_install_diff_ilrd_v2` and
  `dau_splits` (via `network_mapping`); the rare `dau_splits` differences are reinstalls, where it keeps
  the user's first attribution.

## Out of scope for now

`experiment.users_v2` (experiment allocation) and `sub_tables.tracking_slice_critical` (raw client
events) appear in these files only as **lineage** (the tables above are built from the raw slice). They
are **not** part of the ULD layer yet — they need game-level analysis first. Don't query them; experiment
reads stay with the `analyst-experiment-reads` stub, and an event not modelled in the tables above is
reported as "not available in the documented ULD layer".
