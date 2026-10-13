# `server_tables.economy_master_cc`: per-user daily virtual-currency earn / spend / purchase

> **Engine:** Trino. Write `server_tables.economy_master_cc` (no `delta.` prefix). **Category:** Economy
> **Grain:** one row per user (`rid`) × `gid` × `cli` × `build` × `cash_type` × `earn_type` × `category` × `sub_category` on one `date_field`. **Partition / mandatory date filter:** `date_field` (DATE).

> **Used by (BRIAN):** `investigate-engagement` D3 economy cross-check (% of DAU spending, sink / source mix). Read `references/uld.md` first for the layer-wide rules.

## What it is
The user-level ledger of in-game currency and item movements, aggregated to the user-day from raw `earn` / `spend` / `purchase` tracking events. `total_cash` is the summed signed amount and `actions` the number of distinct events. Population = every user with ≥1 qualifying economy event that day, whether or not they are in `derived_tables.dau_splits`. Build rules that explain later gotchas:
- Drops categories `wte` and `inactivity_expiry`, sub_category `bz`, and NULL / empty / NaN amounts.
- Keeps only `cash_type` in (cash, cash_2, hints, spins, lives, spin, pu, skipit); gids 50 and 52 also keep `inventory`.
- Drops gid 29 iOS amounts with |amount| > 999,999,999.
- Forces positive spends negative **only for gids 8, 10 and 11**.
- Dedupes gid 11 `cash` purchases to the latest event per (event, rid, category).
- Rewrites `cash_type` for gid 24 and `category` for gids 9 and 10 (see gotchas).

## When to use it — and when not to
- **Use for:** user-level economy questions the Druid chart can't answer — distinct users who spent on category X; per-user earn / spend / purchase distributions; % of DAU spending and spend per spender; sink and source breakdowns by `sub_category` or `build`; hint-use counts (`actions`); joins to payer status, revenue, sessions or engagement on the user-day key.
- **Don't use for:** headline economy totals by segment — use Druid `chart_2917-vN` (`category='overall'` for totals; it has no `id_type` column). That chart is this table INNER JOINed to `derived_tables.dau_splits` with **no `cash_type` filter**, and matches it exactly; raw totals here sit slightly higher because economy users missing from dau_splits drop out of the chart. For gid 8 the chart reads a separate Crossword source (cash only) that agrees closely.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Unique key | (date_field, gid, cli, rid, build, cash_type, earn_type, category, sub_category). |
| Partition column | `date_field` — **always filter on it**. |
| Freshness / lag | D-1 lands shortly after 00:00 UTC and **each run rewrites the trailing ~5 dates** — treat D-1…D-5 as provisional; use D-2 or earlier. `date_field` comes from raw tracking; treat as UTC. |
| Types | `gid`, `cli` INTEGER; `total_cash`, `actions` BIGINT; `build` VARCHAR (numeric strings); `date_field` DATE; `inserted_at` TIMESTAMP(3) WITH TIME ZONE; everything else VARCHAR. |

## Rollups, mandatory pins & gotchas
- **No rollup or sentinel rows** (no `'overall'` — that exists only on chart_2917). SUM is safe once the slice is pinned.
- **Always pin `cash_type`.** Units differ and must never be summed together:

  > **Examples only.** New games, cash types and categories keep appearing. Before filtering on these lists, confirm the live values for the gid and date window (`SELECT DISTINCT ...`); for mirrored categories, detect them live with template 3 (|earn + spend| ≤ 5% of earn) rather than trusting this list.

  | cash_type | gids | Unit |
  |---|---|---|
  | `cash` | all | Coins (nearly all rows). Most analyses use only this. |
  | `spin` | 9, 11, 14, 15, 17, 31, 34 | Item count |
  | `hints` | 37, 58 | Item count |
  | `hint` | 24 | Item count |
  | `lives` | 8, 37, 58 | Item count |
  | `skipit` | 37 | Item count |
  | `inventory` | 50, 52 | Mixed item counts and **seconds** (e.g. gid 50 `infinite_lives_1h` earn adds 3,600) |

  `cash_2`, `pu`, `spins` and `gems` are allowed by the build but not seen. chart_2917 doesn't filter `cash_type`, so its totals for gids with non-cash types include item units — expect a small gap vs a cash-only ULD query.
- **Sign convention:** `earn` and `purchase` ≥ 0; `spend` ≤ 0 for cash in almost every case. Exceptions: gid 17 `spin` spend is **always positive**; gid 26 `w2e_powerup_inventory` spend has many positive rows, and a few other gids (9, 29, 37, 38, 53) have scattered ones; gid 24 `hint` spend is **logged twice** — once under category `hint` (+) and once under `-GameScreen` / `/GameScreen` (−), netting to ~0. For spend volume use `-SUM(LEAST(total_cash, 0))` or `ABS`; never assume one sign.
- **Pass-through (mirrored) categories inflate gross earn and spend.** Many free grants log an earn plus an equal spend in the same category; net is unaffected, but they can be a large share of gross earn (e.g. most of gid 26 earn). Known cash examples:

  > **Examples only — mirrored categories.** New games, cash types and categories keep appearing. Before filtering on these lists, confirm the live values for the gid and date window (`SELECT DISTINCT ...`); for mirrored categories, detect them live with template 3 (|earn + spend| ≤ 5% of earn) rather than trusting this list.

  | gid | Mirrored categories |
  |---|---|
  | 26 | `w2e_powerup_inventory`, `pu_icon_inventory` |
  | 22, 43 | `normal_hint_notif`, `normal_hint_w2e_shelf` |
  | 29 | `magnet_w2e`, `oom_hint_w2e` |
  | 8 | `w2e_c`, `w2e_p`, `w2e_gb`, `w2e_sw`, `w2e_*`, `timed_*`, `paper_plane` |
  | 17 | `free_p`, `w2e_p`, `w2e_c` |
  | 37 | `chain_hint_w2e` |
  | 9 | `free_hint_notif`, `free_word_notif` |
  | 49, 53 | `w2e_powerup_inventory` |

  For true sources and sinks, exclude categories where |earn + spend| ≤ 5% of earn (template 3) and say so.
- **NULL `total_cash`:** gid 9 `spin` spend is nearly all NULL (empty `category`, `sub_category` '1'…'4'), gid 34 `spin` spend is all NULL, gid 8 `subscription` purchase is NULL. SUM ignores them silently — count these with `actions`. `cash_type`, `rid`, `category` and `sub_category` are never NULL.
- **Zero-amount rows are common** (free item uses / grants in the coin stream, e.g. gid 9 `lady_bug`, `disc_burst_hint`; gid 22 `auto_applied_wind_hint`). **"Spender" means `total_cash < 0`**, not just having a spend row.
- **Empty strings:** `category = ''` is mostly spin spend for gids 9, 11, 14, 15, 31; `sub_category = ''` is common.
- **Game-specific rewrites:**
  - gid 9: `daily_bonus_calendar` becomes `daily_bonus_calendar` + sub_category (`daily_bonus_calendarcoins`, `…free_hint`, `…lady_bug`, `…free_burst_hint`).
  - gid 10: `powerups` spend is replaced by the sub_category (`super_swap`, `word_radar`, `booster`, …).
  - gid 24 `cash_type`: sub_category like `%gem%` → `gems`, purchase → `cash`, `hint` → `hint`, `coins` → `cash`, otherwise NULL (only `cash` and `hint` seen).
  - chart_2917 and team pipelines exclude gid 9/11 `category = 'free_burst_hint'`.
- **`category` is high-cardinality and inconsistently cased** (`DBC_coins`, `Leagues`, `SW_1`; both `daily_bonus_calendar` and `daily_bonus_calender`). Match exact case and check values per gid. chart_2917 keeps a fixed allow-list and maps the rest to `'others'`.
- **Don't filter builds to ≤ 4 digits** — gid 10 uses 5-digit builds and would vanish. `build = '0'` = unknown.
- **Currencies are game-specific** — never blend `total_cash` across gids; compare ratios.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon (Amazon only for gids 8, 9, 10, 11, 17, 22). |
| cash_type | VARCHAR | Dimension | Currency / item key (see matrix). **Always pin**; gid 24 rewritten. |
| earn_type | VARCHAR | Dimension | `earn`, `spend`, or `purchase` (currency granted by an IAP). |
| category | VARCHAR | Dimension | Source or sink feature, game-specific; rewritten for gids 9 and 10. Exact-case match. |
| build | VARCHAR | Dimension | App build (numeric string; 5 digits for gid 10). `'0'` = unknown. |
| rid | VARCHAR | Key | Playsimple user id (= `refid` in `analytics.adjust_installs`). |
| date_field | DATE | Date (partition) | Event date. Always filter. |
| total_cash | BIGINT | Metric | Signed amount moved, in `cash_type` units. SUM within one gid and cash_type only; NULL for some spin / subscription rows. |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Load time, one per daily run; freshness checks only. |
| sub_category | VARCHAR | Dimension | Item / reward detail (e.g. `coins`, `x2_hint`, `inventory`, `wand`, spin tiers `'1'`…`'6'`, `shuffle`, `undo`). Often `''`. |
| actions | BIGINT | Metric | Number of distinct economy events in the row (≥ 1). Additive within a slice; the only reliable volume measure for zero- or NULL-amount rows. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Coins earned | `SUM({total_cash})` WHERE `{cash_type}='cash' AND {earn_type}='earn'` | Per gid. Gross, includes pass-through categories — state whether excluded. |
| Coins spent | `-SUM(LEAST({total_cash}, 0))` WHERE `{cash_type}='cash' AND {earn_type}='spend'` | LEAST / ABS absorbs positive-spend anomalies. |
| Coins purchased (IAP) | `SUM({total_cash})` WHERE `{cash_type}='cash' AND {earn_type}='purchase'` | gid 8 `subscription` purchase rows are NULL. |
| Net coin flow | `SUM({total_cash})` over earn + spend + purchase, `{cash_type}='cash'` | Ties to chart_2917 only if you also include other cash_types and inner-join `dau_splits`. |
| Earn (spend) per DAU | coins earned (spent) / `COUNT(DISTINCT rid)` from `derived_tables.dau_splits` | Users with no economy rows count as 0. |
| % DAU spending | users with spend `{total_cash} < 0` / DAU | Excludes zero-amount spend rows. |
| Spend per spender | coins spent / spenders | — |
| Economy users | `COUNT(DISTINCT {rid})` | Not additive across categories, earn types or days. |
| Events (e.g. hints used) | `SUM({actions})` for the relevant `category` / `sub_category` | Additive within a slice. |

## Join recipes
**Key:** `e.date_field = t.<date column> AND e.gid = t.gid AND e.cli = t.cli AND e.rid = t.rid` (INTEGER / INTEGER / VARCHAR — no casts). Aggregate economy to the user-day **first** (many rows per user); drive from `dau_splits` with LEFT JOIN so non-spenders count.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | One row per user-day; DAU denominator and segments. An INNER join drops a small share of economy users (more for games with weaker dau_splits coverage, e.g. gid 28). |
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | Pre-aggregate to the user-day. |
| `server_tables.sessions_master_cc`, `server_tables.engagement_puzzle_master_cc_col` | `date_field` | Multi-row per user-day — pre-aggregate both sides. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | A balance (stock), not derived from this table; dedupe with `MAX(cash)` per user-day. Its day-over-day change often doesn't equal this table's net flow — combine, don't reconcile. |
| `analytics.adjust_installs` | `installed_date` | `a.refid = e.rid`; dedupe adjust per `(gid, cli, refid)` first. |
| `derived_tables.revenue_reports` | — | **No user-level join** (no `rid`); compare only as aggregates on date / gid / cli / lowercase country. |

## Query templates (all executed successfully)

**1. Earn / spend per DAU by source or sink category (one game)**
```sql
WITH dau AS (
  SELECT dau_date, gid, COUNT(DISTINCT rid) dau
  FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  GROUP BY 1, 2
), eco AS (
  SELECT date_field, gid, earn_type, category,
         SUM(total_cash) AS cash, COUNT(DISTINCT rid) AS users
  FROM server_tables.economy_master_cc
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND cash_type = 'cash' AND earn_type IN ('earn', 'spend')
  GROUP BY 1, 2, 3, 4
)
SELECT e.date_field, e.earn_type, e.category, e.cash, e.users,
       ROUND(1e0 * e.cash / d.dau, 2) AS cash_per_dau,
       ROUND(100e0 * e.users / d.dau, 2) AS pct_dau
FROM eco e JOIN dau d ON d.dau_date = e.date_field AND d.gid = e.gid
ORDER BY e.date_field, e.earn_type, ABS(e.cash) DESC
```

**2. % of DAU spending, earn / spend per DAU, per-user distribution by platform**
```sql
WITH dau AS (
  SELECT dau_date, gid, cli, rid FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
), u AS (
  SELECT date_field, gid, cli, rid,
         SUM(CASE WHEN earn_type = 'earn'     THEN total_cash ELSE 0 END) AS earned,
         SUM(CASE WHEN earn_type = 'spend'    THEN total_cash ELSE 0 END) AS spent,
         SUM(CASE WHEN earn_type = 'purchase' THEN total_cash ELSE 0 END) AS purchased
  FROM server_tables.economy_master_cc
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND cash_type = 'cash'
  GROUP BY 1, 2, 3, 4
)
SELECT d.dau_date, d.cli, COUNT(DISTINCT d.rid) AS dau, COUNT(DISTINCT u.rid) AS econ_users,
       COUNT_IF(u.spent < 0) AS spenders,
       ROUND(100e0 * COUNT(DISTINCT CASE WHEN u.spent < 0 THEN d.rid END) / COUNT(DISTINCT d.rid), 2) AS pct_dau_spending,
       ROUND(1e0 * SUM(COALESCE(u.earned, 0)) / COUNT(DISTINCT d.rid), 1) AS earn_per_dau,
       ROUND(-1e0 * SUM(COALESCE(u.spent, 0)) / COUNT(DISTINCT d.rid), 1) AS spend_per_dau,
       ROUND(-1e0 * SUM(u.spent) / NULLIF(COUNT_IF(u.spent < 0), 0), 1) AS spend_per_spender,
       approx_percentile(COALESCE(u.earned, 0), 0.5) AS p50_earn_per_user,
       approx_percentile(COALESCE(u.earned, 0), 0.9) AS p90_earn_per_user
FROM dau d
LEFT JOIN u ON u.date_field = d.dau_date AND u.gid = d.gid AND u.cli = d.cli AND u.rid = d.rid
GROUP BY 1, 2 ORDER BY 1, 2
```

**3. Sink breakdown with pass-through categories flagged**
```sql
WITH c AS (
  SELECT gid, category,
         SUM(CASE WHEN earn_type = 'earn'  THEN total_cash ELSE 0 END) AS earn_cash,
         SUM(CASE WHEN earn_type = 'spend' THEN total_cash ELSE 0 END) AS spend_cash,
         COUNT(DISTINCT CASE WHEN earn_type = 'spend' THEN rid END) AS spenders,
         SUM(CASE WHEN earn_type = 'spend' THEN actions ELSE 0 END) AS spend_actions
  FROM server_tables.economy_master_cc
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND cash_type = 'cash' AND earn_type IN ('earn', 'spend')
  GROUP BY 1, 2
), f AS (
  SELECT *, (earn_cash > 0 AND spend_cash < 0
             AND ABS(earn_cash + spend_cash) <= 0.05 * earn_cash) AS is_pass_through
  FROM c WHERE spend_cash < 0
)
SELECT category, is_pass_through, -spend_cash AS coins_spent, spenders, spend_actions,
       CASE WHEN NOT is_pass_through THEN ROUND(100e0 * spend_cash /
         SUM(CASE WHEN NOT is_pass_through THEN spend_cash END) OVER (), 1) END AS pct_of_true_sinks
FROM f ORDER BY spend_cash
```
