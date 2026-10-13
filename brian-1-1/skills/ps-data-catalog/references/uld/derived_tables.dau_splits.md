# `derived_tables.dau_splits`: DAU user-day segmentation backbone

> **Engine:** Trino. Write `derived_tables.dau_splits` (no `delta.` prefix). **Category:** DAU / segmentation
> **Grain:** one row per active user (`rid`) per `dau_date` per `gid` × `cli`. **Partition / mandatory date filter:** `dau_date` (DATE).

> **Used by (BRIAN):** driving table for every ULD join; `investigate-retention` / `investigate-rolling-retention` D3 (segment combinations); the DAU denominator for every D3 per-user cut. Read `references/uld.md` first for the layer-wide rules.

## What it is
The user-day DAU fact behind the Druid DAU-segment and rolling-retention charts (`chart_2076`, `chart_2301`). Each active user-day is **inner-joined to the user's first `analytics.adjust_installs` row** (`refid = rid`) and labelled with acquisition (`install_source` / `install_bucket` via `analytics.network_mapping`, plus xpromo, quest-center and DT-T1 overrides), install-age `cohort`, payer status, device / OS / ATT, install vs reinstall, day build, stability model, language, and next-day / day+3 return flags. Population = active users **with an Adjust install record**, not all server DAU.

## When to use it — and when not to
- **Use for:** user-level analysis only — and as the **driving table whenever another ULD table is joined**, since it supplies the DAU denominator and the segment labels (install source/bucket, cohort, payer, LAT, device, OS) for every user-level cut.
- **Don't use for:** headline DAU (`chart_579-vN`), headline DAU by segment (`chart_2076-vN`, `id_type='rid'`) or headline rolling retention (`chart_2301-vN`). Because of the Adjust inner join, totals run slightly below server DAU for most games and far below for a few — they will not tie to `chart_579`.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Unique key | `(dau_date, gid, cli, rid)` — verified unique. `unique_key` is the same tuple as a string (`dau_date_gid_cli_rid`), but NULL on older history. |
| Partition column | `dau_date` — **always filter on it**. |
| Freshness / lag | Daily run (~00:10 UTC) **rewrites the last 5 `dau_date`s** (all share one `inserted_at`). D-1 is present but partial; a date is final after its last rewrite (≈ today−5). |
| Types | `gid`, `cli`, `actual_diff`, `build`, `dau_build` INTEGER; `rid` and labels VARCHAR; `install_date`, `dau_date` DATE; `inserted_at` TIMESTAMP(3) WITH TIME ZONE. |

## Rollups, mandatory pins & gotchas
- **DAU = `COUNT(DISTINCT rid)` per `dau_date`** (× gid × cli). Every per-DAU rate uses that as its denominator, computed per day — never `COUNT(*)`, never a multi-day row count. Across dates count distinct users; never sum daily DAU for WAU/MAU.
- **Exclude `install_bucket = 'reject'` by default and say so** — invalid traffic (sources `untrusted`, `test`, `website`, `unattributed`). Experiment reads pin `install_bucket <> 'reject'`; the `chart_2076` DAU build does not.
- **Adjust coverage gap:** users without an Adjust record are dropped. Most games lose only a small share; a few lose much more, and **Word Trails (gid 28) is almost entirely missing — never use this table for its DAU.**
- **`d1_rr_flag` / `d3_rr_flag` are relative to `dau_date`, not install:** 'Y' = active exactly on `dau_date + 1` / `dau_date + 3`. They read 'N' (not NULL) until that future day lands and its rewrite window closes — **use only dates ≤ today−5** for rolling retention.
- **`payer_flag = 'payer'` means a purchase strictly before `dau_date`.** Same-day first purchasers are `non_payer`, so `non_payer` rows can carry IAP revenue.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| install_date | DATE | Date | User's install date. |
| dau_date | DATE | Date (partition) | Activity date. Always filter. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| rid | VARCHAR | Key | Playsimple user id (= Adjust `refid`). Never NULL. Never output. |
| country | VARCHAR | Dimension | Install country from Adjust, lowercase ISO-2. |
| install_source | VARCHAR | Dimension | Network (lowercase `network_mapping.tag_name`) with overrides: `organic (google play)` / `organic (w/o google play)` and `adwords (search)` / `adwords (others)` on cli 0, `quest_center (high)`, `xpromo (others)`, `organic (dt_t1)`, `digitalturbine_t1`, `untagged`, `unattributed`. |
| install_bucket | VARCHAR | Dimension | Acquisition bucket: `paid`, `paid (preloads)`, `paid (preloads dt_t1)`, `organic`, `organic (google play)`, `organic (w/o google play)`, `organic (dt_t1)`, `xpromo`, `reject`, `untagged`, `p2e`. Exclude `reject` by default. This is the bucket list to use whenever anyone asks for acquisition buckets — for Adjust installs too (join `dau_splits` on install day). |
| cohort | VARCHAR | Dimension | Bucket of `actual_diff`: D00, D01, D02-D07, D08-D14, D15-D30, D31-D60, D61-D120, LD121-D180, LD181-D240, LD241-D360, LD361-D720, LD720+. |
| actual_diff | INTEGER | Dimension | Days since install = `date_diff('day', install_date, dau_date)`. Never negative. |
| lat_flag | VARCHAR | Dimension | Limited ad tracking: `lat` / `non-lat`. Android non-lat iff Adjust android_id present; iOS from OS ≥ 14.5 + ATT state. |
| payer_flag | VARCHAR | Dimension | `payer` if any purchase strictly before `dau_date`, else `non_payer`. |
| device_type | VARCHAR | Dimension | Adjust device class at install (phone, tablet, pc, ipod, tv, console). |
| os_version | VARCHAR | Dimension | OS version on `dau_date` (current, not at install). |
| install_type | VARCHAR | Dimension | `reinstall` if the rid differs from the user's g_psid (global player id), else `only_install`. |
| build | INTEGER | Dimension | App build at install (first Adjust row). |
| dau_build | INTEGER | Dimension | Max build seen on `dau_date`; -1 if none. |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Load time; identical for the 5 dates of each run. |
| att_status | VARCHAR | Dimension | iOS ATT state: `authorized`, `local_denied`, `global_denied`, `restricted`, `not_determined`. NULL on cli 0/2. |
| stable_flag | VARCHAR | Meta | Legacy data-science flag — ignore; don't filter or group by it. |
| device_language | VARCHAR | Dimension | Device language; `'NA'` if not logged. |
| selected_language | VARCHAR | Dimension | In-app language; `'NA'` if not logged. |
| unique_key | VARCHAR | Key | `dau_date_gid_cli_rid` string. NULL for `dau_date` ≤ 2023-06. |
| d1_rr_flag | VARCHAR | Dimension | `Y` if active on `dau_date + 1`, else `N` (also `N` while immature). |
| d3_rr_flag | VARCHAR | Dimension | `Y` if active on `dau_date + 3`, else `N` (also `N` while immature). |
| os_version_bucket | VARCHAR | Dimension | Major OS bucket. Android: `<13`, `13`–`16`, `others`; iOS: `<14`, `14`–`19`, `26`, `others`; cli 2: `others`; rarely `'NA'`. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| DAU | `COUNT(DISTINCT {rid})` per `{dau_date}` (× `{gid}`, `{cli}`) | The denominator of every rate below. Exclude `reject` by default. Runs below `chart_579` / server DAU by the Adjust gap. |
| Multi-day unique users | `COUNT(DISTINCT ({gid},{cli},{rid}))` over a date range | Never sum daily DAU for WAU/MAU. |
| D1 rolling retention | `COUNT(DISTINCT CASE WHEN {d1_rr_flag}='Y' THEN {rid} END) / COUNT(DISTINCT {rid})` per `{dau_date}` | Final dates only (≤ today−5). Matches `chart_2301` `D01_rolling` / dau. |
| D3 rolling retention | `COUNT(DISTINCT CASE WHEN {d3_rr_flag}='Y' THEN {rid} END) / COUNT(DISTINCT {rid})` per `{dau_date}` | Same; D1 and D3 populations overlap — never add them. |
| Payer share of DAU | `COUNT(DISTINCT CASE WHEN {payer_flag}='payer' THEN {rid} END) / COUNT(DISTINCT {rid})` per `{dau_date}` | Prior-day payers only. |
| Rev/DAU by segment | `SUM(rev.{total_ad_rev} + rev.{net_iap_rev}) / COUNT(DISTINCT {rid})` per `{dau_date}` | LEFT JOIN `dm_admon.rev_dau_install_diff_ilrd_v2` on the 4-key; DAU from this table. |

## Join recipes
**Key:** `s.dau_date = t.<date column> AND s.gid = t.gid AND s.cli = t.cli AND s.rid = t.rid` (all INTEGER / INTEGER / VARCHAR / DATE — no casts). Use dau_splits as the left / driving table, filter both sides on the date, and pre-aggregate multi-row tables to the user-day first or segment counts fan out.

| Table | Date column | Notes |
|---|---|---|
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | One row per user-day; every dau_splits row matches. Its extra unmatched-Adjust rows (`country = 'NA'`) are not in dau_splits. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | Dedupe with `MAX(cash)` per user-day first. Wallet covers all server DAU, so a small share of its rows have no dau_splits match. |
| `server_tables.sessions_master_cc`, `server_tables.engagement_puzzle_master_cc_col`, `server_tables.economy_master_cc` | `date_field` | Many rows per user-day — aggregate to the 4-key first. |
| `analytics.adjust_installs` | — | `s.rid = a.refid AND s.gid = a.gid AND s.cli = a.cli`. Dedupe adjust to one row per `(gid, cli, refid)` first (multiple rows per install). Use dau_splits for the chart taxonomy, adjust for campaign / adgroup / creative. |
| `derived_tables.revenue_reports` | `report_date` | **No user-level join** (no `rid`). Aggregate dau_splits to date / gid / cli / country, then match `lower(r.country) = s.country` (remap `UK` → `GB` on the revenue side). |

## Query templates

**1. DAU by platform × install bucket (reject excluded)**
```sql
SELECT dau_date, cli, install_bucket, COUNT(DISTINCT rid) AS dau
FROM derived_tables.dau_splits
WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND gid = {gid}
  AND install_bucket <> 'reject'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 4 DESC;
```

**2. D1 / D3 rolling retention by install-age cohort (use `end_date` ≤ today−5)**
```sql
SELECT dau_date, cli,
  CASE WHEN cohort LIKE 'LD%' THEN replace(cohort, 'LD', 'D') ELSE cohort END AS cohort,
  COUNT(DISTINCT rid) AS dau,
  COUNT(DISTINCT CASE WHEN d1_rr_flag = 'Y' THEN rid END) AS d1_rolling_retained,
  COUNT(DISTINCT CASE WHEN d3_rr_flag = 'Y' THEN rid END) AS d3_rolling_retained,
  ROUND(1e0 * COUNT(DISTINCT CASE WHEN d1_rr_flag = 'Y' THEN rid END) / COUNT(DISTINCT rid), 4) AS d1_rolling_rate,
  ROUND(1e0 * COUNT(DISTINCT CASE WHEN d3_rr_flag = 'Y' THEN rid END) / COUNT(DISTINCT rid), 4) AS d3_rolling_rate
FROM derived_tables.dau_splits
WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND gid = {gid}
  AND install_bucket <> 'reject'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

**3. Rev/DAU by payer_flag (revenue side pre-aggregated to the 4-key)**
```sql
WITH d AS (
  SELECT dau_date, gid, cli, rid, payer_flag
  FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid} AND install_bucket <> 'reject'),
r AS (
  SELECT dau_date, gid, cli, rid, SUM(total_ad_rev) AS ad_rev, SUM(net_iap_rev) AS iap_rev
  FROM dm_admon.rev_dau_install_diff_ilrd_v2
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  GROUP BY 1, 2, 3, 4)
SELECT d.dau_date, d.payer_flag,
  COUNT(DISTINCT d.rid) AS dau,
  ROUND(SUM(COALESCE(r.ad_rev, 0)), 2) AS ad_rev,
  ROUND(SUM(COALESCE(r.iap_rev, 0)), 2) AS iap_rev,
  ROUND(SUM(COALESCE(r.ad_rev, 0) + COALESCE(r.iap_rev, 0)) / COUNT(DISTINCT d.rid), 4) AS rev_per_dau
FROM d LEFT JOIN r ON d.dau_date = r.dau_date AND d.gid = r.gid AND d.cli = r.cli AND d.rid = r.rid
GROUP BY 1, 2 ORDER BY 1, 2;
```
