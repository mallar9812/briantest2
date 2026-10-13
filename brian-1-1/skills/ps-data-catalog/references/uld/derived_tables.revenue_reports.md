# `derived_tables.revenue_reports`: reported revenue, spend and bookings ledger

> **Engine:** Trino. Write `derived_tables.revenue_reports` (no `delta.` prefix). **Category:** Revenue
> **Grain:** one row per `report_date × gid × cli × country × rev_source × rev_type`. **Aggregate table, not user-level — there is no `rid`.** **Partition / mandatory date filter:** `report_date` (DATE).

> **Used by (BRIAN):** `investigate-rev-dau` D2/D3 (reported revenue by source × country, feed-lag checks); `analyst-game-performance` D2-R appendix cuts. Read `references/uld.md` first for the layer-wide rules.

## What it is
The reported-revenue ledger: daily USD amounts as reported by each external party — ad-network earnings from the mediation and demand partners, store proceeds and gross bookings from App Store, Play Store and Amazon, plus Apple Arcade payouts, internal xpromo transfer value and paid-UA spend — for all games, platforms and countries. It is **the upstream of BRIAN's headline revenue charts**, and they tie to the cent:
- `chart_579` (net) = exactly `SUM(amount) WHERE rev_type = 'earn'`.
- `chart_1170` (gross) = exactly non-store `earn` + store `bookings` (formula below).

## When to use it — and when not to
- **Use for:**
  - Network-level questions ("how much did AppLovin / APS / Moloco pay for gid X yesterday"), including network × ad-format splits (`data_source` × `ad_type`).
  - Store net proceeds (`earn`) vs gross bookings (`bookings`) and Play Store `tax`.
  - Daily UA spend and paid installs by acquisition network (`rev_type = 'spend'`, `data_source = 'acquired'`).
  - Apple Arcade payouts and xpromo transfer values.
  - Full country granularity (the Druid charts collapse countries to tier-1 + `others`).
  - Reconciling user-level revenue against reported totals.
- **Don't use for:**
  - Headline KPIs: net revenue → `chart_579-vN`; gross → `chart_1170-vN`; drill-downs by install cohort, source or LAT → `chart_2077-vN`; spend for ROAS → `chart_1706`. Numbers tie exactly, but the charts carry the geo_bucket / source_category conventions and DAU.
  - Revenue per user, payer counts, cohorts or retention — no rid, no install date. Use `dm_admon.rev_dau_install_diff_ilrd_v2`.
  - DAU — the `dau` column is legacy and always 0.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Unique key | (`report_date`, `gid`, `cli`, `country`, `rev_source`, `rev_type`). `data_source` and `ad_type` are determined by `rev_source`. No duplicate rows. |
| Partition column | `report_date` — **always filter on it**; the table is large. |
| Freshness / lag | Ad networks and App Store are complete through **D-2**. Play Store, Amazon, acquired spend and xpromo installs have D-1 rows, but D-1 is a stub — don't read it. **Apple Arcade** and **xpromo amounts** lag ~9–10 days (xpromo rows exist to D-1 with `amount = 0`). `xsolla` is sparse. Partner feeds (e.g. the APS family) can go missing for days and be backfilled later. |
| Restatement | Each (`data_source`, date) slice is deleted and re-inserted on later loads; `inserted_at` = last reload. **Treat the last ~7–10 days as provisional.** |
| Types | `gid`, `cli` INTEGER (`cli`: 0 Android, 1 iOS, 2 Amazon, -1 unknown); `report_date` DATE; `amount` DOUBLE; `installs`, `dau` INTEGER; `inserted_at` TIMESTAMP(3) WITH TIME ZONE; everything else VARCHAR. |

## Rollups, mandatory pins & gotchas
- **Always pin `rev_type`.** `amount` mixes four measures: `earn` (net revenue), `bookings` (gross store revenue), `spend` (UA cost) and `tax`. An unfiltered `SUM(amount)` adds revenue and spend.
- **Net vs gross — never add `earn` + `bookings` for the same store.** Store IAP appears twice: `earn` is net proceeds (≈ 0.7 × bookings), `bookings` is gross.
  - Net revenue = `SUM(amount) WHERE rev_type = 'earn'` (= `chart_579`).
  - Gross revenue = `earn` where `rev_source NOT LIKE '%store%'` + `bookings` where `rev_source LIKE '%store%' OR rev_source IN ('xsolla','appcharge')` (= `chart_1170`).
  - Play Store `tax` rows are used by neither formula.
- **xpromo is internal and nets to zero.** `data_source = 'xpromo'` rows appear as `earn` (promoting gid) and `spend` (promoted gid) with identical totals. `chart_579` includes it as source_category `xpromo`; exclude it for external-only revenue. For UA spend always pin `data_source = 'acquired'`.
- **Never `SUM(installs)` across rev_types** — xpromo installs are duplicated on the earn and spend rows.
- **Apple Arcade is a flat weekly payout spread evenly across the days of the week** (gid 21 and gid 30, cli 1, `ad_type = 'None'`). Don't read day-to-day movement in it; its last ~9 days are empty by design.
- **Restatements:** for audits, Delta time travel (`FOR TIMESTAMP AS OF`) works — one snapshot per statement; a multi-snapshot CTE returned wrong legs.
- **Unmapped traffic:** `gid = -1` (`game = 'unknown_game'`) and `cli = -1` carry a small amount of earn. For P&L, exclude `gid IN (-1, 0)` and `cli = -1`.
- **Country is uppercase ISO-2 with dirty values.** APS reports Great Britain as **`UK`** — map `UK` → `GB` or a tier-1 filter misses it. Sentinels that carry revenue: `ZZ`, `N/A`, `NONE`, `OTHER`, `UNKNOWN`, `XX`, `0`, `''`. ULD tables use lowercase — join on `lower(country)`.
- **`data_source = 'facebook'` on earn rows is Meta Audience Network ad revenue** (`rev_source` `fan_*`), not Facebook IAP.
- **`ad_type` has blanks:** `''` on `*_others` rows, literal `'None'` on store, Apple Arcade and bright rows. Map formats from `rev_source` (`%banner%`, `%interstitial%`, `%video%` …), checking `%video%` before `%interstitial%` so `video interstitial` counts as **video**.
- **Minor gross double-count:** `xsolla` has both earn and bookings rows, and the gross formula picks up both (small).
- **Use `game` only as a label** (some names have trailing spaces); join on `gid`.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| game | VARCHAR | Dimension | Lowercase game name; label only. `unknown_game` for gid -1. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). -1 = unmapped. |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon, -1 unknown. |
| country | VARCHAR | Key | Uppercase ISO-2. Includes `UK` (APS, = GB) and sentinels (`ZZ`, `N/A`, `NONE`, `OTHER`, `UNKNOWN`, `XX`, `0`, `''`). |
| rev_source | VARCHAR | Key | Fine-grained source: `<network>_<ad format>` for ads (`applovin_interstitial`, `fan_rewarded video`, `aps~~inmobi_banner`, `unity_others`); store names (`appstore`, `playstore`, `*_subscription`, `amazonstore`, `xsolla`); `apple_arcade`; `bright`; `tapresearch`; `xpromo_<placement>`; UA network names on spend rows. |
| rev_type | VARCHAR | Key | `earn` (net revenue), `bookings` (gross store IAP), `spend` (UA cost; also the xpromo mirror), `tax` (Play Store tax). Always pin. |
| amount | DOUBLE | Metric (Normal) | USD; meaning depends on `rev_type`. SUM only, always with a `rev_type` pin. Many rows are 0. |
| installs | INTEGER | Metric (Normal) | Non-zero only on `spend`/`acquired` (Adjust paid installs per UA network), xpromo earn **and** spend (duplicated), and `tapresearch` earn. |
| dau | INTEGER | Metric (legacy) | Always 0. Do not use. |
| report_date | DATE | Date (partition) | Partner reporting date (partner timezone, not normalised). Always filter. |
| data_source | VARCHAR | Dimension | Reporting partner / feed (ad networks incl. `aps~~*` sub-partners, `facebook` = FAN; `appstore`, `playstore`, `amazonstore`, `xsolla`, `apple_arcade`; spend: `acquired`, `xpromo`). |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Last (re)load of this (`data_source`, date) slice; advances as dates are restated. |
| ad_type | VARCHAR | Dimension | Ad format (interstitial, banner, rewarded video, video, video interstitial, …). `''` = others, `'None'` = store / arcade / bright, `growth` = spend rows, `xpromo_default` = xpromo. |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Net revenue | `SUM({amount}) WHERE {rev_type} = 'earn'` | Equals `chart_579` `revenue` exactly. Includes xpromo and Apple Arcade; exclude them for external-only. |
| Gross revenue | `SUM({amount}) WHERE ({rev_type} = 'earn' AND {rev_source} NOT LIKE '%store%') OR ({rev_type} = 'bookings' AND ({rev_source} LIKE '%store%' OR {rev_source} IN ('xsolla','appcharge')))` | Equals `chart_1170` `revenue` exactly. |
| Net ad revenue (IAA) | `SUM({amount}) WHERE {rev_type} = 'earn' AND {data_source} NOT IN ('appstore','playstore','amazonstore','xsolla','appcharge','xpromo','apple_arcade')` | Includes small bright / tapresearch / steam amounts. |
| IAP net / gross | `SUM({amount})` with `{rev_type} = 'earn'` / `'bookings'` AND store `data_source` | Store cut ≈ 30%. |
| UA spend / paid installs | `SUM({amount})`, `SUM({installs})` WHERE `{rev_type} = 'spend' AND {data_source} = 'acquired'` | `rev_source` = UA network. Treat as complete at D-2. |
| Rev/DAU | net revenue ÷ DAU | DAU from `chart_579` or `derived_tables.dau_splits` — never the `dau` column. |
| Network eCPM | — | No impressions here. Use `dm_admon.rev_dau_install_diff_ilrd_v2` (`*_rev` / `*_imp`) for per-format eCPM. |

## Join recipes
**Key:** aggregate only — `report_date = <date>`, `gid`, `cli`, `lower(country)`. **Never join at row level** (no `rid`, fan-out guaranteed); aggregate both sides to date × gid × cli × country first, and remap `UK` → `GB` on this side.

| Table | Date column | Notes |
|---|---|---|
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | Ad revenue agrees closely at gid × cli level (Amazon / cli 2 can differ materially). Its IAP is client-side purchase value, so per-game IAP gaps go either way — use this table for reported totals, ILRD only for per-user splits. |
| `derived_tables.dau_splits` | `dau_date` | DAU denominator; aggregate to the same key. |
| `analytics.adjust_installs` | `installed_date` | Only spend rows carry installs; compare at date × gid × cli × country × network after aggregation. Spend `rev_source` values are lowercase acquired-network names and may not equal Adjust `network_name`. |
| `public.gid_mapping` | — | `LEFT JOIN public.gid_mapping m ON r.gid = m.gid` (both INTEGER). |

## Query templates (all executed successfully)

**1. Daily net vs gross revenue for a game, with IAP / ads / xpromo / arcade split**
```sql
SELECT report_date, cli,
  SUM(CASE WHEN rev_type = 'earn' THEN amount ELSE 0 END) AS net_revenue,
  SUM(CASE WHEN rev_type = 'earn' AND rev_source NOT LIKE '%store%' THEN amount
           WHEN rev_type = 'bookings' AND (rev_source LIKE '%store%' OR rev_source IN ('xsolla','appcharge')) THEN amount
           ELSE 0 END) AS gross_revenue,
  SUM(CASE WHEN rev_type = 'earn' AND data_source IN ('appstore','playstore','amazonstore','xsolla','appcharge') THEN amount ELSE 0 END) AS iap_net,
  SUM(CASE WHEN rev_type = 'bookings' THEN amount ELSE 0 END) AS iap_gross,
  SUM(CASE WHEN rev_type = 'earn' AND data_source NOT IN ('appstore','playstore','amazonstore','xsolla','appcharge','xpromo','apple_arcade') THEN amount ELSE 0 END) AS ad_revenue,
  SUM(CASE WHEN rev_type = 'earn' AND data_source = 'xpromo' THEN amount ELSE 0 END) AS xpromo_internal,
  SUM(CASE WHEN rev_type = 'earn' AND data_source = 'apple_arcade' THEN amount ELSE 0 END) AS apple_arcade
FROM derived_tables.revenue_reports
WHERE report_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND gid = {gid}
GROUP BY 1, 2
ORDER BY 1, 2;
```
`net_revenue` and `gross_revenue` per cli equal `chart_579` / `chart_1170`.

**2. Network × ad-format split of ad revenue**
```sql
SELECT data_source AS network,
  CASE WHEN ad_type IN ('', 'None') THEN 'others' ELSE ad_type END AS ad_format,
  ROUND(SUM(amount), 2) AS net_ad_revenue,
  ROUND(100e0 * SUM(amount) / SUM(SUM(amount)) OVER (), 2) AS pct_of_ad_rev
FROM derived_tables.revenue_reports
WHERE report_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND gid = {gid}
  AND rev_type = 'earn'
  AND data_source NOT IN ('appstore','playstore','amazonstore','xsolla','appcharge','xpromo','apple_arcade')
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 15;
```

**3. Tier-1 revenue vs UA spend and paid installs (UK folded into GB)**
```sql
SELECT report_date,
  CASE WHEN country IN ('GB','UK') THEN 'GB' WHEN country IN ('US','CA','AU') THEN country ELSE 'ROW' END AS geo,
  ROUND(SUM(CASE WHEN rev_type = 'earn' THEN amount ELSE 0 END), 2) AS net_revenue,
  ROUND(SUM(CASE WHEN rev_type = 'spend' AND data_source = 'acquired' THEN amount ELSE 0 END), 2) AS ua_spend,
  SUM(CASE WHEN rev_type = 'spend' AND data_source = 'acquired' THEN installs ELSE 0 END) AS paid_installs
FROM derived_tables.revenue_reports
WHERE report_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND gid = {gid}
GROUP BY 1, 2
ORDER BY 1, 2;
```
