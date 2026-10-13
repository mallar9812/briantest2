# `derived_tables.wallet_dau_install_diff`: per-user daily wallet (soft-currency) balance

> **Engine:** Trino. Write `derived_tables.wallet_dau_install_diff` (no `delta.` prefix). **Category:** Economy
> **Grain:** one row per active user (`rid` × `gid` × `cli`) per `dau_date`, carrying the user's latest known soft-currency ("cash" / coins) balance as of that day — **but the key is not unique; dedupe first.** **Partition / mandatory date filter:** `dau_date` (DATE).

> **Used by (BRIAN):** `investigate-engagement` D3 economy cross-check (median wallet by cohort age, hoarding). Read `references/uld.md` first for the layer-wide rules.

## What it is
The wallet balance for every server DAU user-day (all active users, not only Adjust-attributed ones). `cash` is the balance from the user's **last cash event (earn / spend / purchase) on the latest day ≤ `dau_date` that had one** — effectively an end-of-day balance, **carried forward** when the user had no cash event that day. Values are absolute (never negative) and capped at a per-game wallet limit. Users with no balance history get a hardcoded default for 5 gids and NULL everywhere else.

## When to use it — and when not to
- **Use for:** the per-user wallet distribution (median / percentiles / buckets) by game, platform, cohort age (`diff`) or install cohort; hoarding and inflation checks (share of users above X coins); out-of-currency risk; wallet vs payer status or acquisition segment (join `dau_splits`); wallet as a per-user feature next to revenue or engagement.
- **Don't use for:** earn / spend / sink / source flows — this is a balance level only; flows come from Druid `chart_2917-vN` or `server_tables.economy_master_cc` (spend velocity needs flows too). Not for DAU headlines (`chart_2076-vN`): its distinct-rid count is server DAU and won't tie to the charts. No Druid chart carries the wallet balance.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Intended key | `(dau_date, gid, cli, rid)`; `install_date` and `diff` depend on it. **Not unique** — a small share of keys have 2 rows with different `cash`. Dedupe with `MAX(cash)` per user-day (templates). |
| Partition column | `dau_date` — **always filter on it** (history is very large). |
| Freshness / lag | D-1. Each daily run (~00:07 UTC) **rewrites the trailing 5 `dau_date`s** (identical `inserted_at`). D-1 is partial; use D-2 or older for stable reads. |
| Types | `gid`, `cli` INTEGER; `rid` VARCHAR; `install_date`, `dau_date` DATE; `diff`, `cash` BIGINT; `inserted_at` TIMESTAMP. |

## Rollups, mandatory pins & gotchas
- **Dedupe user-days first:** aggregate to one row per `(dau_date, gid, cli, rid)` with `MAX(cash)`. Never `SUM(cash)` per user-day — that double-counts the duplicates.
- **Percentiles are computed per cut — partition by exactly the dimensions you will show.** A median / p25 / p75 belongs to one partition (e.g. `dau_date × gid × cli × country × cohort × install_source × install_bucket × install_type × lat_flag × payer_flag`). It cannot be summed, averaged or user-weighted into a coarser cut, and a coarser-cut percentile can't be reused for a finer one. So: (1) put every dimension of the requested cut — and only those — in the `PARTITION BY` / `GROUP BY`, always including `dau_date`; (2) filter every other dimension to the population you want; (3) when reading a pre-computed percentile output that was partitioned by many dimensions, filter **every** partition dimension to a single value — rolling rows up gives a weighted average of percentiles, not the percentile. Template 4.
- **`cash` is a level (stock), not a flow.** Never sum it across days; sum across users only as the numerator of a mean. Report median / percentiles — the distribution is heavily right-skewed and the mean is dominated by the top tail.
- **Carried-forward balance:** a user with no cash event today keeps the balance from their last event day, possibly months old. The share of same-day balances varies a lot by game.
- **Hardcoded default when there is no balance history:** gid 8 → 100, gid 4 → 250, gid 9 → 250, gid 11 → 200, gid 24 → 500. These gids have no NULLs, but imputed values are indistinguishable from real ones (e.g. gid 9 D0 median sits at the default).
- **NULL `cash` for every other gid with no history.** Gids 39, 45, 46, 47, 60 have no cash tracking and are entirely NULL; several others are mostly or partly NULL. Filter `cash IS NOT NULL` explicitly and report the NULL share — percentile functions ignore NULLs silently.
- **No negatives by construction.** Zeros are real but rare.
- **Cap artifacts:** 400,000 is the wallet limit hit by gids 11, 18, 25, 26, 29, 37, 50; 35,000 is the ceiling for gids 4, 8, 17; 99,999 for gids 28, 35, 36; 350,000 for gid 20. Don't read users at these values as real hoarders in p99 / max.
- **gid 24 (Jigsaw) is not comparable** — its cash is parsed from a different field and is nearly constant. Exclude it.
- **Currency is game-specific** (each game's own coin denomination) — never compare or blend levels across gids.
- **`diff` = days since install** (`dau_date − install_date`); 0 = install day, never negative. `install_date` is the user's **first-ever** install for `(rid, gid, cli)`, so reinstalls keep the original date.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| rid | VARCHAR | Key | Playsimple user id. Never output. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| install_date | DATE | Date | User's first-ever install date for `(rid, gid, cli)`. |
| dau_date | DATE | Date (partition) | Activity date. Always filter. |
| diff | BIGINT | Dimension | Days since install = `date_diff('day', install_date, dau_date)`. 0 = install day. |
| cash | BIGINT | Metric (level) | Soft-currency balance: end-of-day balance of the latest cash-event day ≤ `dau_date`, carried forward, capped, defaulted for gids 4/8/9/11/24. ≥ 0 or NULL. Aggregate as median / percentiles over deduped user-days; never sum across days. |
| inserted_at | TIMESTAMP | Meta | Run timestamp (UTC), shared by the 5 rewritten dates. Not for analysis. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Median / p25 / p75 wallet | exact: interpolated rank within the partition (template 4); quick: `approx_percentile({cash}, 0.5)` | Computed per `{dau_date}` × exactly the requested cut — never rolled up across partitions. Exclude NULL and disclose the NULL share. |
| Mean wallet per DAU | `SUM({cash}) / COUNT(DISTINCT {rid})` per `dau_date` | Over deduped user-days. Dominated by the top tail and cap values — prefer the median. |
| Hoarding share | `COUNT_IF({cash} >= X) / COUNT({cash})` | Per gid per day; pick X per game. |
| Zero / low-balance share | `COUNT_IF({cash} = 0)` or `< X` over `COUNT({cash})` | Per gid; out-of-currency risk. |
| Wallet by cohort age | median `{cash}` per `{dau_date}` × bucket of `{diff}` | A blended median across ages is its own cut — compute it directly, never from the per-age medians. |

## Join recipes
**Key:** `w.dau_date = t.<date column> AND w.gid = t.gid AND w.cli = t.cli AND w.rid = t.rid` (INTEGER / INTEGER / VARCHAR / DATE — no casts). **Dedupe the wallet side with `MAX(cash)` per user-day first**, and pre-aggregate multi-row tables to the user-day.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | Segments (payer_flag, install_source / bucket, country, lat_flag, build). Near 1:1; a small share of wallet rows are unmatched (users without Adjust). |
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | One row per user-day; same DAU lineage. |
| `server_tables.economy_master_cc` | `date_field` | Holds the earn / spend flows this table lacks. Aggregate to the user-day first. |
| `server_tables.sessions_master_cc`, `server_tables.engagement_puzzle_master_cc_col` | `date_field` | Aggregate to the user-day first. |
| `analytics.adjust_installs` | — | `rid = refid` + gid / cli. Prefer the attribution already resolved in `dau_splits`. |
| `derived_tables.revenue_reports` | — | **No user-level join** (no `rid`); compare only as aggregates on date / gid / cli / lowercase country. |

## Query templates

**1. Median / p90 wallet by cohort age (quick, approximate — per day × platform × age)**
```sql
WITH w AS (
  SELECT dau_date, gid, cli, rid, MAX(diff) AS diff, MAX(cash) AS cash   -- dedupe user-day
  FROM derived_tables.wallet_dau_install_diff
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  GROUP BY 1,2,3,4)
SELECT dau_date, cli,
       CASE WHEN diff = 0 THEN 'D0' WHEN diff <= 6 THEN 'D1-6' WHEN diff <= 29 THEN 'D7-29'
            WHEN diff <= 89 THEN 'D30-89' WHEN diff <= 364 THEN 'D90-364' ELSE 'D365+' END AS age_bucket,
       COUNT(DISTINCT rid) AS users,
       approx_percentile(cash, 0.5) AS median_wallet, approx_percentile(cash, 0.9) AS p90_wallet,
       COUNT_IF(cash IS NULL) AS null_cash
FROM w GROUP BY 1, 2, 3 ORDER BY 1, 2, MIN(diff);
```

**2. Wallet distribution buckets for one day**
```sql
WITH w AS (
  SELECT dau_date, gid, cli, rid, MAX(cash) AS cash
  FROM derived_tables.wallet_dau_install_diff
  WHERE dau_date = DATE '{end_date}' AND gid IN ({gid})
  GROUP BY 1,2,3,4)
SELECT gid,
  CASE WHEN cash IS NULL THEN 'null' WHEN cash = 0 THEN '0' WHEN cash < 100 THEN '1-99'
       WHEN cash < 500 THEN '100-499' WHEN cash < 1000 THEN '500-999' WHEN cash < 5000 THEN '1k-5k'
       WHEN cash < 20000 THEN '5k-20k' ELSE '20k+' END AS bucket,
  COUNT(DISTINCT rid) AS users, ROUND(100e0 * COUNT(DISTINCT rid) / SUM(COUNT(DISTINCT rid)) OVER (PARTITION BY gid), 2) AS pct
FROM w GROUP BY 1,2 ORDER BY 1, MIN(COALESCE(cash,-1));
```

**3. Wallet vs payer status**
```sql
WITH w AS (
  SELECT dau_date, gid, cli, rid, MAX(cash) AS cash
  FROM derived_tables.wallet_dau_install_diff
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  GROUP BY 1,2,3,4),
s AS (
  SELECT DISTINCT dau_date, gid, cli, rid, payer_flag
  FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid})
SELECT w.dau_date, w.cli, COALESCE(s.payer_flag, 'unmatched') AS payer_flag,
       COUNT(DISTINCT w.rid) AS users, approx_percentile(w.cash, 0.5) AS median_wallet,
       approx_percentile(w.cash, 0.9) AS p90_wallet, AVG(w.cash) AS mean_wallet
FROM w LEFT JOIN s ON s.dau_date = w.dau_date AND s.gid = w.gid AND s.cli = w.cli AND s.rid = w.rid
GROUP BY 1,2,3 ORDER BY 1,2,3;
```

**4. Exact p25 / median / p75 for a cut (percentile-cont interpolation)** — replace the cut columns
(`dau_date, gid, cli, cohort, payer_flag` here) with exactly the dimensions the question asks for, **in all
three places** (base SELECT, both `PARTITION BY`s, final `GROUP BY`), and filter the rest.
```sql
WITH w AS (
  SELECT dau_date, gid, cli, rid, MAX(cash) AS wallet                -- dedupe user-day
  FROM derived_tables.wallet_dau_install_diff
  WHERE dau_date = DATE '{end_date}' AND gid = {gid} AND diff >= 0
  GROUP BY 1, 2, 3, 4),
base AS (
  SELECT w.dau_date, w.gid, w.cli, s.cohort, s.payer_flag, w.rid, w.wallet
  FROM w
  JOIN derived_tables.dau_splits s
    ON s.dau_date = w.dau_date AND s.gid = w.gid AND s.cli = w.cli AND s.rid = w.rid
  WHERE s.dau_date = DATE '{end_date}' AND s.gid = {gid}
    AND s.install_bucket <> 'reject'
    AND w.wallet IS NOT NULL),                                        -- NULLs would skew the ranks
ranked AS (
  SELECT dau_date, gid, cli, cohort, payer_flag, rid, wallet,
         ROW_NUMBER() OVER (PARTITION BY dau_date, gid, cli, cohort, payer_flag ORDER BY wallet) AS rn,
         COUNT(*)     OVER (PARTITION BY dau_date, gid, cli, cohort, payer_flag)                 AS n
  FROM base),
p AS (
  SELECT r.*, q.pct,
         q.pct * (n - 1) + 1        AS pos,
         FLOOR(q.pct * (n - 1) + 1) AS lo,
         CEIL(q.pct * (n - 1) + 1)  AS hi
  FROM ranked r CROSS JOIN (VALUES 0.25e0, 0.5e0, 0.75e0) AS q(pct))
SELECT dau_date, gid, cli, cohort, payer_flag,
       COUNT(DISTINCT rid)                        AS users,
       SUM(CASE WHEN pct = 0.5e0 THEN wallet END) AS wallet_balance,
       MAX(CASE WHEN pct = 0.25e0 AND rn = lo THEN wallet END)
         + MAX(CASE WHEN pct = 0.25e0 THEN pos - lo END)
         * (MAX(CASE WHEN pct = 0.25e0 AND rn = hi THEN wallet END) - MAX(CASE WHEN pct = 0.25e0 AND rn = lo THEN wallet END)) AS p25,
       MAX(CASE WHEN pct = 0.5e0 AND rn = lo THEN wallet END)
         + MAX(CASE WHEN pct = 0.5e0 THEN pos - lo END)
         * (MAX(CASE WHEN pct = 0.5e0 AND rn = hi THEN wallet END) - MAX(CASE WHEN pct = 0.5e0 AND rn = lo THEN wallet END)) AS median,
       MAX(CASE WHEN pct = 0.75e0 AND rn = lo THEN wallet END)
         + MAX(CASE WHEN pct = 0.75e0 THEN pos - lo END)
         * (MAX(CASE WHEN pct = 0.75e0 AND rn = hi THEN wallet END) - MAX(CASE WHEN pct = 0.75e0 AND rn = lo THEN wallet END)) AS p75
FROM p
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 2, 3, 4, 5
```
Same interpolation as `PERCENTILE_CONT` and the team's wallet-percentile chart query. `approx_percentile` is
fine for exploration (results land within a few coins); use this template when the number will be reported.
