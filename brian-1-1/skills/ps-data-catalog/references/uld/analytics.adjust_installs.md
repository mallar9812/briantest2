# `analytics.adjust_installs`: Adjust install attribution (user level)

> **Engine:** Trino. Write `analytics.adjust_installs` (no `delta.` prefix). **Category:** Installs / attribution
> **Grain:** one row per Adjust attribution callback — **not one row per install**. An install is `(gid, cli, refid)`; dedupe to it before counting. **Partition / mandatory date filter:** `installed_date` (DATE, UTC).

> **Used by (BRIAN):** `investigate-retention` / `investigate-rolling-retention` D3 (campaign / creative cohorts); `analyst-game-performance` campaign- or creative-level cuts. Read `references/uld.md` first for the layer-wide rules.

## What it is
Adjust install attribution for every Playsimple game on Adjust, across Android (0), iOS (1) and Amazon (2). Each row carries the attributed network, campaign, adgroup and creative, plus install country, device and OS, and `refid` — the Playsimple user id, equal to `rid` in every other ULD table and the only key that links attribution to user activity. Organic installs are included (`network_name = 'Organic'`); reattributions are not.

## When to use it — and when not to
- **Use for:** user-level analysis only — attribution below the chart grain, joined to user activity on `refid = rid`: installs, D0/Dn revenue per install, or return rates by **network × campaign × adgroup × creative**, by install country, device model or OS version; preload (`dt_build`) and GetApps (`install_platform`) cuts; which network a given user came from.
- **Don't use for:** headline installs, eCPI or cohort KPIs — those come from Druid `chart_1706-vN` and its spend variant, and totals here will not tie to it (server-side installs vs Adjust callbacks, late-arriving rows, raw `network_name` instead of `install_source`). For the chart taxonomy (`install_source` / `install_bucket`) on active users, use `derived_tables.dau_splits` instead of re-deriving it here. For creative-type CPI use `chart_2454`.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Install key | `(gid, cli, refid)` — rows repeat per callback type and hour, so always dedupe (template 1). |
| Partition column | `installed_date` — **always filter on it**. |
| Freshness / lag | Each daily run rewrites roughly the last 10 days, and late callbacks keep landing for weeks. D-1 is partial; treat install counts younger than ~14 days as provisional and compare periods at the same age. |
| Types | `gid`, `cli`, `build` INTEGER; `installed_date` DATE; `event_time`, `inserted_at` TIMESTAMP WITH TIME ZONE; everything else VARCHAR (including `installed_at`, `is_organic`, `dt_build`). |

## Rollups, mandatory pins & gotchas
- **Never `COUNT(*)`.** Dedupe with `ROW_NUMBER() OVER (PARTITION BY gid, cli, refid ORDER BY installed_at, event_time) = 1`, or count `DISTINCT (gid, cli, refid)`. Take dimension values from the deduped row so one install can't land in two networks.
- **`event_type` — ignore it.** Never filter on it; dedupe on `(gid, cli, refid)` instead. Some games' installs arrive only under a non-`install` value (e.g. gids 10, 20, 26, 33, 49, 53), so `event_type = 'install'` would silently drop whole games.
- **Drop blank refids** (`LENGTH(TRIM(refid)) > 0`) — they can't join to any user table.
- **Test builds:** odd `build` numbers are internal test builds — exclude with `MOD(build, 2) = 0`.
- **`network_name` is raw Adjust text** with inconsistent case and spelling (`Unity` / `unity` / `Unity ads`). Normalise through `analytics.network_mapping` on `(gid, cli, network_name)` — exact match, unique on that key, no fan-out — and classify with its `bucket` (not `is_organic`). Exclude bucket `reject` (untrusted devices) for UA questions.
- **Country** is lowercase ISO-2 — use lowercase on both sides when joining.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| network_name | VARCHAR | Dimension | Adjust attributed network. Raw text — map through `analytics.network_mapping` before grouping. For acquisition buckets, use the `dau_splits.install_bucket` list (join `dau_splits` on install day); `network_mapping.bucket` carries only the base buckets (`paid`, `organic`, `xpromo`, `reject`, `untagged`, `p2e`). |
| campaign_name | VARCHAR | Dimension | Adjust campaign; empty for organic. Often embeds the network's campaign id. |
| adgroup_name | VARCHAR | Dimension | Adjust adgroup; empty or `unknown` is common, some networks put the publisher app here. |
| creative_name | VARCHAR | Dimension | Adjust creative (Playsimple creative code); empty for organic. |
| is_organic | VARCHAR | Dimension | Adjust organic flag ('0'/'1'). Misses some organic networks — use `network_mapping.bucket`. |
| app_name | VARCHAR | Dimension | Store package / bundle id of the game. |
| app_version | VARCHAR | Dimension | App version string at install; format varies by game — prefer `build`. |
| store | VARCHAR | Dimension | Store (`google`, `itunes`, `amazon`); mirrors `cli`. |
| adid | VARCHAR | Key | Adjust device id. Join/count key only — never output. |
| country | VARCHAR | Dimension | Install country, lowercase ISO-2. |
| language | VARCHAR | Dimension | Device language at install. |
| device_name | VARCHAR | Dimension | Device model. |
| device_type | VARCHAR | Dimension | Device class (phone, tablet, pc, tv, …). |
| os_name | VARCHAR | Dimension | OS name. Pin `cli` for platform, not this. |
| os_version | VARCHAR | Dimension | OS version at install. |
| idfa | VARCHAR | Key | iOS advertising id (mostly empty under ATT). Never output. |
| android_id | VARCHAR | Key | Hashed Android id. Never output. |
| installed_at | VARCHAR | Date | Install time as epoch seconds in a string — `from_unixtime(CAST(installed_at AS BIGINT))`. |
| refid | VARCHAR | Key | Playsimple user id = `rid` in all other ULD tables. The join key; always join with `gid` and `cli`. |
| tracker | VARCHAR | Dimension | Adjust tracker token (the attribution leaf). |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| build | INTEGER | Dimension | App build at install. Odd = test build (exclude); 0 = unknown. |
| installed_date | DATE | Date (partition) | UTC install date. Always filter. |
| tag_name | VARCHAR | Meta | Unused placeholder — take the tag from `network_mapping`. |
| inserted_at | TIMESTAMP WITH TIME ZONE | Meta | Load time; freshness checks only. |
| event_type | VARCHAR | Meta | Callback type. Ignore — never filter on it. |
| event_time | TIMESTAMP WITH TIME ZONE | Meta | Hour of the Adjust callback; can trail the install by days. |
| idfv | VARCHAR | Key | iOS vendor id. Never output. |
| dt_build | VARCHAR | Dimension | Digital Turbine preload build flag ('true'/'false'/NULL). Use `LOWER(COALESCE(dt_build, 'false')) = 'true'`. |
| label | VARCHAR | Meta | Adjust click label. Not an analysis field. |
| install_platform | VARCHAR | Dimension | Alternate store (`getapps` = Xiaomi GetApps), also appended to `network_name` as `_getapps`. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Adjust installs | `COUNT(DISTINCT ({gid},{cli},{refid}))` | After dropping blank refid and test builds. Does not tie to `chart_1706`. |
| Installs by bucket / source | installs grouped by `network_mapping.{bucket}` / `{tag_name}` | LEFT JOIN on `(gid, cli, network_name)`; unmapped → `untagged`. |
| Organic share | installs(bucket = 'organic') / installs(bucket ≠ 'reject') | Use the bucket, not `is_organic`. |
| D0 revenue per install | `SUM(rev.{total_rev}) / installs` with `rev.dau_date = {installed_date}` | Revenue from `dm_admon.rev_dau_install_diff_ilrd_v2`, pre-aggregated per user-day; installs with no revenue count as 0. |
| Preload share | installs with `{dt_build}` = 'true' / installs | NULL counts as false. |

## Join recipes
**Key:** `a.refid = t.rid AND a.gid = t.gid AND a.cli = t.cli` (INTEGER / INTEGER / VARCHAR on both sides — no casts). **Dedupe adjust to one row per `(gid, cli, refid)` first**, and pre-aggregate the other side to the user-day. Align days with `<date column> = installed_date + n`.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | Nearly every Adjust install appears in DAU on install day. Its `install_source` / `install_bucket` agree with `network_mapping` for ≥99.8% of users; the rest are reinstalls, where dau_splits keeps the user's **first** Adjust attribution. Use dau_splits for the chart taxonomy, adjust for campaign / adgroup / creative. |
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | Its `network_name` is the same raw Adjust value — map it through `network_mapping` the same way. |
| `server_tables.sessions_master_cc`, `server_tables.engagement_puzzle_master_cc_col`, `server_tables.economy_master_cc` | `date_field` | Multi-row per user-day — aggregate first. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | Dedupe with `MAX(cash)` per user-day first. |
| `analytics.network_mapping` | — | `(gid, cli, network_name)`, exact match. |
| `derived_tables.revenue_reports` | — | **No user-level join** (no `rid`); compare only as aggregates on date / gid / cli / lowercase country. |

## Query templates (all executed successfully)

**1. Deduped installs by network × country**
```sql
WITH ai AS (
  SELECT * FROM (
    SELECT gid, cli, refid, installed_date, network_name, LOWER(country) AS country,
           ROW_NUMBER() OVER (PARTITION BY gid, cli, refid ORDER BY installed_at, event_time) AS rn
    FROM analytics.adjust_installs
    WHERE installed_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
      AND gid = {gid}
      AND LENGTH(TRIM(refid)) > 0
      AND MOD(build, 2) = 0
  ) WHERE rn = 1)
SELECT installed_date, cli, network_name, country, COUNT(DISTINCT refid) AS installs
FROM ai
GROUP BY 1, 2, 3, 4
ORDER BY installs DESC
LIMIT 50
```

**2. Installs by normalised bucket / source (network_mapping)**
```sql
WITH ai AS (
  SELECT * FROM (
    SELECT gid, cli, refid, installed_date, network_name,
           ROW_NUMBER() OVER (PARTITION BY gid, cli, refid ORDER BY installed_at, event_time) AS rn
    FROM analytics.adjust_installs
    WHERE installed_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
      AND gid = {gid} AND LENGTH(TRIM(refid)) > 0 AND MOD(build, 2) = 0
  ) WHERE rn = 1)
SELECT ai.cli,
       COALESCE(nm.bucket, 'untagged') AS bucket,
       LOWER(nm.tag_name)              AS source,
       COUNT(DISTINCT ai.refid)        AS installs
FROM ai
LEFT JOIN analytics.network_mapping nm
  ON ai.gid = nm.gid AND ai.cli = nm.cli AND ai.network_name = nm.network_name
GROUP BY 1, 2, 3
ORDER BY installs DESC
```

**3. D0 revenue per install by campaign**
```sql
WITH ai AS (
  SELECT * FROM (
    SELECT gid, cli, refid, installed_date, network_name, campaign_name,
           ROW_NUMBER() OVER (PARTITION BY gid, cli, refid ORDER BY installed_at, event_time) AS rn
    FROM analytics.adjust_installs
    WHERE installed_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
      AND gid = {gid} AND LENGTH(TRIM(refid)) > 0 AND MOD(build, 2) = 0
  ) WHERE rn = 1),
rev AS (
  SELECT gid, cli, rid, dau_date, SUM(total_rev) AS total_rev
  FROM dm_admon.rev_dau_install_diff_ilrd_v2
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  GROUP BY 1, 2, 3, 4)
SELECT LOWER(nm.tag_name)                                     AS source,
       ai.campaign_name,
       COUNT(DISTINCT ai.refid)                               AS installs,
       ROUND(SUM(COALESCE(rev.total_rev, 0)) / COUNT(DISTINCT ai.refid), 4) AS d0_rev_per_install
FROM ai
LEFT JOIN analytics.network_mapping nm
  ON ai.gid = nm.gid AND ai.cli = nm.cli AND ai.network_name = nm.network_name
LEFT JOIN rev
  ON ai.gid = rev.gid AND ai.cli = rev.cli AND ai.refid = rev.rid AND rev.dau_date = ai.installed_date
WHERE COALESCE(nm.bucket, 'untagged') <> 'reject'
GROUP BY 1, 2
HAVING COUNT(DISTINCT ai.refid) >= 100
ORDER BY installs DESC
LIMIT 50
```
