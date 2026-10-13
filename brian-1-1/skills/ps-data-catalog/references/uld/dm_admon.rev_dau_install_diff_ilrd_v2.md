# `dm_admon.rev_dau_install_diff_ilrd_v2`: user-day revenue (ILRD ads + IAP) by install cohort

> **Engine:** Trino. Write `dm_admon.rev_dau_install_diff_ilrd_v2` (no `delta.` prefix). **Category:** Revenue
> **Grain:** one row per active user (`rid`) of one game-platform (`gid`, `cli`) on one `dau_date`, with the user's install date, Adjust attribution and that day's revenue. **Partition / mandatory date filter:** `dau_date` (DATE).

> **Used by (BRIAN):** `investigate-rev-dau` D3 (payer/whale concentration, per-user ad revenue and impressions by format). Read `references/uld.md` first for the layer-wide rules.

## What it is
The per-user, per-day revenue ledger. The row set is every active user of the day (payers or not — a sizeable minority of rows have zero revenue), LEFT JOINed to Adjust attribution (`country`, `network_name`, `adid`) and to impression-level ad revenue (ILRD), pivoted into one revenue / network-impression / ILRD-impression triple per ad format. All amounts are USD. Ad revenue is as reported by ILRD; IAP enters net as a flat `0.7 × dollar_value`. Cross-promo (`xpromo_rev`) is carried separately and is **not** in `total_rev`.

## When to use it — and when not to
- **Use for:** per-user revenue distributions (payer / whale / ad-whale percentiles, top-N users); rev/DAU or ARPU for segments the Druid charts don't carry (rid lists, engagement or economy segments joined on rid); cohort cumulative revenue curves by `diff` for custom cohorts; ad-format mix and per-format eCPM per user segment; ad-vs-IAP split at user level; "distinct users who earned / paid X".
- **Don't use for:** headline revenue, DAU or Rev/DAU (`chart_579-vN` net revenue + `chart_579-vN-source-source_category` DAU); gross revenue (`chart_1170`); cohort LTV / ROAS headlines (`chart_1706`); network / mediation drill-downs (`chart_2077-vN`). Totals won't tie exactly: IAP net is a flat 0.7 here (chart_2077 uses 0.85 for Android until company Android IAP passes $1M YTD), `total_rev` has no xpromo, the table includes `reject` / untrusted traffic and unmatched-Adjust rows, and ILRD rows whose rid isn't an active user that day are dropped.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Unique key | (`dau_date`, `gid`, `cli`, `rid`). `rid` alone is **not** unique — the same rid string can exist in several gids. |
| Partition column | `dau_date` — **always filter on it**. Filtering only on `install_date` scans the whole table; add a `dau_date` bound too. |
| Freshness / lag | Daily load ~00:45 UTC. Each run deletes and re-appends the last 15 `dau_date`s, so they are restated daily. D-1 is loaded with ILRD ad revenue before `revenue_reports` has it — treat D-1 as provisional, D-2 as the default. `xpromo_rev` lags ~10 days (0 on recent days). |
| Row set vs `dau_splits` | A superset of `derived_tables.dau_splits` for the same day, with identical `install_date`; the extra rows are the unmatched-Adjust `country = 'NA'` rows (plus a handful of others). |
| Types | `gid`, `cli` INTEGER; `rid` VARCHAR; `diff` BIGINT; dates DATE; revenue DOUBLE; impressions BIGINT. Use integer literals (`gid = 22`, `cli = 0`). Dates as written by the DAU spine (UTC assumed). |

## Rollups, mandatory pins & gotchas
- **No rollup or sentinel rows** — every row is one user; `SUM()` across any dimension is correct.
- **`total_rev` = `total_ad_rev` + 0.7 × `dollar_value`, excluding `xpromo_rev`** (0.7 = Playsimple's 70% share of IAP; the store keeps 30%). Add `xpromo_rev` only when cross-promo is explicitly wanted, and remember it lags ~9–10 days.
- **Never use `total_impressions`.** It adds `offerwall_imp` without a NULL guard, and `offerwall_imp` is NULL on many rows, so it is NULL or short for a large share of revenue-bearing rows. Sum per-format `*_imp` with `COALESCE` instead. `total_ilrd_impressions` has no offerwall term and is fine.
- **All `*_imp` and `*_ilrd_imp` columns are NULL (not 0) when the user had no ILRD row that day.** Revenue columns are already 0. `COALESCE` impressions before arithmetic.
- **Exclude unmatched-Adjust rows when counting DAU.** Rows with `country = 'NA'` (also `network_name = 'NA'`, `adid` NULL — the same set) are not in `dau_splits` and carry ~zero revenue. Filter `country <> 'NA'` or join `dau_splits`, or DAU runs slightly high. Lowercase `'na'` is Namibia, not the sentinel; `country = ''` occurs on a few rows.
- **Invalid traffic is included** (`network_name` `Untrusted Devices`, `dau_splits.install_bucket = 'reject'`). Convention: join `dau_splits` and filter `install_bucket <> 'reject'`.
- **`network_name` is the raw Adjust `network_name`** (same value as `analytics.adjust_installs`), case-inconsistent (`Unity` / `unity` / `Unity ads`, `Applovin` / `applovin`, `Digital Turbine` / `digitalturbine`). Map through `analytics.network_mapping` on `(gid, cli, network_name)` before grouping.
- **`country`** is lowercase ISO-2 except the `'NA'` sentinel. Tier-1 = `us, gb, ca, au`.
- **IAP:** `dollar_value` = `gross_iap_rev` (gross USD, client-side purchase value) and `net_iap_rev` = 0.7 × `dollar_value` on recent data (older dates can diverge). Payer flag: `SUM(dollar_value) > 0` (cohort consumers use `> 0.05`).
- **Ad-format mapping:** `w2e_rev` = ILRD ad types `rewarded video`, `video`, `w2e`, plus `video interstitial` for gid ≠ 10; **for gid 10 `video interstitial` goes to `interstitial_rev`**. ILRD ad types outside the mapping (`others`, NULL) are dropped from `total_ad_rev` (negligible).
- **Near-dead format columns:** `app_open`, `btob_w2e`, `btob_inter`, `offerwall`, `screen_transition` and `bright` are ~zero recently. `mid_interstitial` and `ad_on_inactivity` are material but game-specific.
- **`diff` = `date_diff('day', install_date, dau_date)`** exactly; never negative or NULL; `diff = 0` is install day.
- **gid coverage grows over time**, and some gids are tiny or test-like on recent days — don't assume every gid present is a live game.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| install_date | DATE | Key/Date | User's install date (same as `dau_splits`). Never NULL. |
| dau_date | DATE | Date (partition) | Activity / revenue date. Always filter. |
| diff | BIGINT | Dimension | `dau_date − install_date` in days; 0 = install day. |
| country | VARCHAR | Dimension | Adjust install country, lowercase ISO-2. `'NA'` = no Adjust match (exclude). |
| network_name | VARCHAR | Dimension | Raw Adjust `network_name` (as in `analytics.adjust_installs`). Map via `analytics.network_mapping`. |
| rid | VARCHAR | Key | Playsimple user id (= Adjust `refid`). Join with `gid` and `cli`. |
| adid | VARCHAR | Key | Adjust device id; NULL on the `'NA'` rows. Never output. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| dollar_value | DOUBLE | Metric (Normal) | Gross IAP USD that day (client-side). |
| gross_iap_rev | DOUBLE | Metric (Normal) | Gross IAP USD; equals `dollar_value` on recent data. |
| net_iap_rev | DOUBLE | Metric (Normal) | Net IAP USD = 0.7 × `dollar_value` on recent data — Playsimple's 70% share after the store's 30% cut. |
| banner_rev | DOUBLE | Metric (Normal) | ILRD banner revenue. |
| interstitial_rev | DOUBLE | Metric (Normal) | ILRD interstitial revenue (+ video interstitial for gid 10). Largest format. |
| w2e_rev | DOUBLE | Metric (Normal) | ILRD watch-to-earn / rewarded revenue (rewarded video, video, w2e, video interstitial except gid 10). |
| app_open_rev | DOUBLE | Metric (Normal) | ILRD app-open revenue. ~0 recently. |
| audio_rev | DOUBLE | Metric (Normal) | ILRD audio-ad revenue. |
| mid_interstitial_rev | DOUBLE | Metric (Normal) | ILRD mid-level interstitial revenue. Game-specific. |
| screen_transition_rev | DOUBLE | Metric (Normal) | ILRD screen-transition revenue. Small. |
| ad_on_inactivity_rev | DOUBLE | Metric (Normal) | ILRD ad-on-inactivity revenue. Game-specific. |
| btob_w2e_rev | DOUBLE | Metric (Normal) | ILRD back-to-back W2E revenue. ~0. |
| btob_inter_rev | DOUBLE | Metric (Normal) | ILRD back-to-back interstitial revenue. ~0. |
| bright_rev | DOUBLE | Metric (Normal) | ILRD `bright` ad-type revenue. Small. |
| offerwall_rev | DOUBLE | Metric (Normal) | Offerwall revenue (from the DAU spine, not ILRD). ~0. |
| banner_imp | BIGINT | Metric (Normal) | Network-reported impressions, banner. NULL when no ILRD row — COALESCE. |
| interstitial_imp | BIGINT | Metric (Normal) | Network impressions, interstitial. NULL when no ILRD row. |
| w2e_imp | BIGINT | Metric (Normal) | Network impressions, W2E. NULL when no ILRD row. |
| app_open_imp | BIGINT | Metric (Normal) | Network impressions, app open. NULL when no ILRD row. |
| audio_imp | BIGINT | Metric (Normal) | Network impressions, audio. NULL when no ILRD row. |
| mid_interstitial_imp | BIGINT | Metric (Normal) | Network impressions, mid interstitial. NULL when no ILRD row. |
| screen_transition_imp | BIGINT | Metric (Normal) | Network impressions, screen transition. NULL when no ILRD row. |
| ad_on_inactivity_imp | BIGINT | Metric (Normal) | Network impressions, ad on inactivity. NULL when no ILRD row. |
| btob_w2e_imp | BIGINT | Metric (Normal) | Network impressions, btob W2E. NULL when no ILRD row. |
| btob_inter_imp | BIGINT | Metric (Normal) | Network impressions, btob interstitial. NULL when no ILRD row. |
| bright_imp | BIGINT | Metric (Normal) | Network impressions, bright. NULL when no ILRD row. |
| offerwall_imp | BIGINT | Metric (Normal) | Offerwall impressions (from the DAU spine). Often NULL — the cause of the broken `total_impressions`. |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Load time; same for every restated day of a run. Freshness checks only. |
| banner_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, banner (≈ network imps). NULL when no ILRD row. |
| interstitial_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, interstitial. NULL when no ILRD row. |
| w2e_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, W2E. NULL when no ILRD row. |
| app_open_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, app open. NULL when no ILRD row. |
| audio_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, audio. NULL when no ILRD row. |
| mid_interstitial_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, mid interstitial. NULL when no ILRD row. |
| screen_transition_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, screen transition. NULL when no ILRD row. |
| ad_on_inactivity_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, ad on inactivity. NULL when no ILRD row. |
| btob_w2e_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, btob W2E. NULL when no ILRD row. |
| btob_inter_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, btob interstitial. NULL when no ILRD row. |
| bright_ilrd_imp | BIGINT | Metric (Normal) | ILRD impression count, bright. NULL when no ILRD row. |
| xpromo_rev | DOUBLE | Metric (Normal) | Internal cross-promo (PSPN) value credited to the rid. Lags ~9–10 days; **not in `total_rev`**. |
| total_ad_rev | DOUBLE | Metric (Custom) | Sum of the 12 `*_rev` ad-format columns (banner … bright, incl. offerwall). |
| total_rev | DOUBLE | Metric (Custom) | `total_ad_rev` + 0.7 × `dollar_value` (net of store, no xpromo). |
| total_impressions | BIGINT | Metric (Custom) | Σ all `*_imp` incl. `offerwall_imp`. **Unreliable — NULL whenever any term is NULL; never use.** |
| total_ilrd_impressions | BIGINT | Metric (Custom) | Σ all `*_ilrd_imp` (no offerwall). Safe; NULL when no ILRD row. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Net revenue | `SUM({total_rev})` | Ads + 0.7 × IAP. Add `SUM({xpromo_rev})` only if xpromo is explicitly wanted. |
| Ad revenue | `SUM({total_ad_rev})` | Agrees closely with `revenue_reports` ad earn at gid × cli level. |
| IAP gross / net | `SUM({dollar_value})` / `SUM({net_iap_rev})` | Net = 70% of gross — Playsimple's share; the other 30% is the store's (Apple / Google / Amazon) cut. |
| DAU | `COUNT(DISTINCT {rid})` per `{dau_date}` (× gid × cli), with `country <> 'NA'` or joined to `dau_splits` with `install_bucket <> 'reject'` | The denominator of every per-DAU rate below, always computed per day. |
| Rev/DAU (ARPDAU) | `SUM({total_rev}) / COUNT(DISTINCT {rid})` per `{dau_date}` | Same filtered row set for numerator and denominator. |
| Ad share | `SUM({total_ad_rev}) / SUM({total_rev})` | |
| Format eCPM | `1000 × SUM({interstitial_rev}) / SUM(COALESCE({interstitial_imp}, 0))` | Network `*_imp` (chart_2077 convention) or `*_ilrd_imp` — state which. |
| Imps/DAU | `SUM(COALESCE({x}_imp, 0)) / COUNT(DISTINCT {rid})` per `{dau_date}` | Never `{total_impressions}`. |
| Payers / payer rate | `COUNT_IF({dollar_value} > 0)` / DAU | Cohort payer flags use per-user `SUM({dollar_value}) > 0.05`. |
| Cohort cumulative rev per user (LTV dN) | `Σ_{diff≤N} SUM({total_rev}) / COUNT(rid with diff = 0)` | Denominator = D0-active users here (not Adjust installs); bound `dau_date` to `install_date … install_date + N`. |

## Join recipes
**Key:** `(dau_date, gid, cli, rid)` — INTEGER / INTEGER / VARCHAR on both sides, no casts. Filter both sides on the same date range, and pre-aggregate event tables to one row per user-day before joining or revenue fans out.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | Segments (`install_bucket`, `install_source`, payer, cohort, LAT, build). 1:1; INNER JOIN drops only the `'NA'` rows. |
| `analytics.adjust_installs` | `installed_date` | `a.refid = r.rid AND a.gid = r.gid AND a.cli = r.cli`; dedupe adjust to one row per `(gid, cli, refid)` first. Only needed for campaign / adgroup / creative — `network_name`, `country`, `adid` are already here. |
| `server_tables.sessions_master_cc`, `server_tables.engagement_puzzle_master_cc_col`, `server_tables.economy_master_cc` | `date_field` | Multi-row per user-day — aggregate first. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | Dedupe with `MAX(cash)` per user-day first. |
| `analytics.network_mapping` | — | `(gid, cli, network_name)`, exact match. |
| `derived_tables.revenue_reports` | `report_date` | **No user-level join** (no `rid`). Compare as aggregates on date / gid / cli / `lower(country)`; ads ≈ `rev_type = 'earn' AND ad_type <> 'None'`, IAP ≈ `rev_type = 'bookings'`. |
| `public.gid_mapping` | — | Game names on `gid`. |

## Query templates (all executed successfully)

**1. Rev/DAU by platform × Tier-1 (valid traffic only)**
```sql
SELECT r.dau_date, r.cli,
       CASE WHEN r.country IN ('us','gb','ca','au') THEN 'tier1' ELSE 'rest' END AS geo,
       COUNT(DISTINCT r.rid) AS dau,
       ROUND(SUM(r.total_ad_rev),0) AS ad_rev,
       ROUND(SUM(r.net_iap_rev),0)  AS iap_net,
       ROUND(SUM(r.total_rev),0)    AS total_rev,
       ROUND(SUM(r.total_rev)/COUNT(DISTINCT r.rid),4) AS rev_per_dau
FROM dm_admon.rev_dau_install_diff_ilrd_v2 r
JOIN derived_tables.dau_splits d
  ON d.dau_date = r.dau_date AND d.gid = r.gid AND d.cli = r.cli AND d.rid = r.rid
WHERE r.dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND d.dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND r.gid = {gid} AND d.gid = {gid}
  AND d.install_bucket <> 'reject'
GROUP BY 1,2,3 ORDER BY 1,2,3;
```

**2. Cohort curve: active rate + cumulative net revenue per D0 user, diff 0..7**
```sql
WITH coh AS (
  SELECT install_date, gid, cli, rid
  FROM dm_admon.rev_dau_install_diff_ilrd_v2
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'   -- = install dates
    AND diff = 0 AND gid = {gid} AND country <> 'NA'),
rev AS (
  SELECT r.install_date, r.diff, SUM(r.total_rev) AS rev, COUNT(DISTINCT r.rid) AS active
  FROM dm_admon.rev_dau_install_diff_ilrd_v2 r
  JOIN coh c ON c.gid = r.gid AND c.cli = r.cli AND c.rid = r.rid AND c.install_date = r.install_date
  WHERE r.dau_date BETWEEN DATE '{start_date}' AND date_add('day', 7, DATE '{end_date}')
    AND r.gid = {gid} AND r.diff BETWEEN 0 AND 7
  GROUP BY 1,2),
n AS (SELECT install_date, COUNT(DISTINCT rid) AS cohort_users FROM coh GROUP BY 1),
curve AS (
  SELECT rev.install_date, rev.diff, n.cohort_users, rev.active,
         ROUND(CAST(rev.active AS DOUBLE)/n.cohort_users,4) AS active_rate,
         ROUND(SUM(rev.rev) OVER (PARTITION BY rev.install_date ORDER BY rev.diff)/n.cohort_users,4) AS cum_rev_per_user
  FROM rev JOIN n ON n.install_date = rev.install_date)
SELECT * FROM curve ORDER BY 1,2;   -- filter diffs HERE, never before the window
```

**3. Ad vs IAP split and format mix, with interstitial eCPM**
```sql
SELECT dau_date,
       ROUND(SUM(total_ad_rev),0) AS ad_rev, ROUND(SUM(net_iap_rev),0) AS iap_net,
       ROUND(SUM(total_ad_rev)/SUM(total_rev),4) AS ad_share,
       ROUND(SUM(interstitial_rev),0) AS inter, ROUND(SUM(w2e_rev),0) AS w2e, ROUND(SUM(banner_rev),0) AS banner,
       ROUND(SUM(mid_interstitial_rev+screen_transition_rev+ad_on_inactivity_rev+audio_rev+app_open_rev
                 +btob_w2e_rev+btob_inter_rev+bright_rev+offerwall_rev),0) AS other_ad,
       ROUND(1000*SUM(interstitial_rev)/NULLIF(SUM(COALESCE(interstitial_imp,0)),0),3) AS inter_ecpm,
       COUNT_IF(dollar_value > 0) AS payers
FROM dm_admon.rev_dau_install_diff_ilrd_v2
WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
GROUP BY 1 ORDER BY 1;
```

**4. Payer vs non-payer per-user revenue distribution over a window**
```sql
WITH u AS (
  SELECT gid, cli, rid, SUM(total_rev) AS rev, SUM(dollar_value) AS iap_gross, SUM(total_ad_rev) AS ad_rev
  FROM dm_admon.rev_dau_install_diff_ilrd_v2
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid} AND country <> 'NA'
  GROUP BY 1,2,3)
SELECT CASE WHEN iap_gross > 0 THEN 'iap_in_window' ELSE 'no_iap_in_window' END AS seg  -- not dau_splits.payer_flag (lifetime, prior-day),
       COUNT(DISTINCT rid) AS users, ROUND(SUM(rev),0) AS rev, ROUND(SUM(ad_rev),0) AS ad_rev, ROUND(AVG(rev),4) AS arpu,
       ROUND(approx_percentile(rev,0.5),4) AS p50, ROUND(approx_percentile(rev,0.9),4) AS p90,
       ROUND(approx_percentile(rev,0.99),4) AS p99, ROUND(MAX(rev),2) AS max_rev
FROM u GROUP BY 1;
```
Ad whales exist among non-payers — check the non-payer tail before assuming top users are payers.
