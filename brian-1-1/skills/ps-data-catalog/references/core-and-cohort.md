# Core KPIs & Cohort — tables, formulas, dimensions

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`. Exception:
> `play_data.monthly_rev_diff` runs in Trino.

## Rollups & mandatory pins

**`chart_579`, `chart_1170`, `chart_1706`, `monthly_rev_diff` carry NO rollup value on any dimension and
need no mandatory pin.** `SUM()` across `gid`, `cli`, `country`, `source`, `source_category`,
`install_bucket`, `install_source`, `install_type` or `dt_flag` is the correct total — do not spend a probe
looking for an `'overall'` or `'rid'` value here; those belong to other charts.

Two narrow exceptions, both on the gross chart's geography columns: **`geo_bucket` is a rollup, not a
country**, and **`country_bucket` is a language-similarity rollup — ignore it entirely.** Never sum either
alongside `country`.

## Table routing and hard filter rules

| Metric(s) | Datasource | Engine | Hard filter rules |
|---|---|---|---|
| revenue (net) | `chart_579-vN` | Druid | All filters allowed, including `source` / `source_category`. |
| dau | `chart_579-vN-source-source_category` | Druid | **`source` / `source_category` do not exist on this variant** — DAU is independent of them. Any other chart dimension is available. |
| revenue (gross) | `chart_1170-vN` | Druid | `source` / `source_category` allowed. Source of truth for gross: query the `revenue` field directly, **never derive gross from net**. |
| dau (gross-side) | `chart_1170-vN-source-source_category` | Druid | Same variant rule as `chart_579`. Prefer `chart_579` for headline DAU; this exists so gross-side ratios can be built without crossing charts. |
| installs, `dX_retained`, `overall_rev_dX`, `dX_active_days` | `chart_1706-vN` | Druid | All chart dimensions available. **NEVER** use this variant for `spend` — it isn't in its `metrics` array. |
| spend | `chart_1706-vN-dt_flag-install_type` | Druid | **`install_type` / `dt_flag` do not exist here.** Always the spend source. ⚠️ `chart_config` lists this suffix as `install_type-dt_flag`; the real Druid name sorts alphabetically to `dt_flag-install_type`. |
| **long-horizon monthly cohort**: `rev`, `spend` past the day-grain dX caps (`diff` 0–103 confirmed live) | `play_data.monthly_rev_diff` | **Trino** | The one core table with **no Druid equivalent**. Only 6 columns: `gid`, `cli`, `install_month`, `rev`, `spend`, `diff` — **NEVER** filter `country` / `network` / `source` / `install_type`. **No `__time`** — grained by `install_month` + `diff`. **`spend` repeats on every `diff` row of a cohort — always `MAX(spend)`, never `SUM(spend)`.** |

Date column on the Druid datasources is `"__time"` — always filter it, anchored to calendar periods.
`play_data.monthly_rev_diff` has no `__time`; scope it by `install_month`.

**The retired warehouse originals** — `play_data.Revenue_dataset`,
`Revenue_dataset_Source_Source_category`, `Gross_revenue_dataset`,
`retention_ltv_ratio_independent`, `retention_ltv_ratio_dataset` — must not be queried. They lag the
Druid datasources: on a July 2026 spot-check net revenue ran 0.34–1.62% low and DAU 2.2–6.9% low per
game, enough to shift a close ranking. Spend ties exactly between the two (`chart_1706-vN-dt_flag-install_type`
matched `retention_ltv_ratio_independent` to the rupee on all eight games checked).

## Grain

Core KPI charts (`chart_579`, `chart_1170`) are **daily-activity** grain — revenue and DAU on the
reporting date. Cohort charts (`chart_1706`) are **install-date-cohort** grain: `"__time"` is the
install date, and a `dX` field describes that cohort's behaviour X days later. Never treat the two
grains as interchangeable, and never join cohort age fields against a calendar date axis.

`play_data.monthly_rev_diff` is a third grain: **install-month cohort × month offset** — one row per
(`gid`, `cli`, `install_month`, `diff`), where `diff` is an integer count of months since
`install_month`.

## Metric formulas

### Core KPIs

| Name | Type | Formula | Description |
|---|---|---|---|
| revenue (net) | Normal | `revenue` on `chart_579-vN` | Net revenue — after the store/platform cut. |
| revenue (gross) | Normal | `revenue` on `chart_1170-vN` | Gross revenue — before the cut. Source of truth for gross; never derive it from net. |
| dau | Normal | `dau` on `chart_579-vN-source-source_category` | Daily active users. |
| Revenue per DAU | Custom | `revenue / dau` | Query each variant separately, compute after. Default companion metric whenever revenue and DAU both appear in a response. |

### Cohort metrics

Install-date-cohort grain. All `/ installs` unless noted. Spend comes only from the spend variant.

| Name | Type | Formula | Description |
|---|---|---|---|
| LTV (DX) | Custom | `overall_rev_dX / installs` | Cumulative cohort revenue to Day X ÷ installs. X ∈ {1,3,7,14,21,30,60,90}. |
| Retention (DX) | Custom | `dX_retained / installs` | Share of the cohort active on Day X post-install. X ∈ {1,3,7,14,21,30,60,90,120,150,180,210,240,270,300,330,360}. |
| LTDays (DX) | Custom | `dX_active_days / installs` | Average active days per install to Day X — cumulative. X ∈ {3,7,14,21,30,60,90}. |
| **ROAS (DX) — actual** | Custom | `overall_rev_dX / spend` | **Observed** return on ad spend. Numerator from `chart_1706-vN`, denominator from `chart_1706-vN-dt_flag-install_type` — **one statement per variant** (Druid cannot join variants), each covering every period, game and segment the answer needs; combined client-side. Total numerator and denominator over the period *before* dividing — never average daily ROAS. Report at the highest mature dX, labeled "actual", alongside the predicted D365 ROAS. |
| eCPI | Custom | `spend / installs` | Effective cost per install — same two-variant split. |
| installs | Normal | `installs` | Installs in the cohort. |
| spend | Normal | `spend` | Marketing spend on the install date. |
| `dX_retained` | Normal | raw | Cohort users active on day X post-install. |
| `overall_rev_dX` | Normal | raw | Cumulative cohort revenue through day X. |
| `dX_active_days` | Normal | raw | Cumulative active days through day X. |

### Long-horizon monthly cohort metrics (`play_data.monthly_rev_diff`, Trino)

Use when a question needs cohort revenue or ROAS **past the day-grain caps** — `overall_rev_dX` and
`dX_active_days` stop at d90, `dX_retained` at d360, while `diff` here runs 0 to 103 (~8.5 years).
Dims: `gid`, `cli` only.

| Name | Type | Formula | Description |
|---|---|---|---|
| rev | Normal | `rev` | Revenue earned by the cohort **during month `diff` only — not cumulative**. Sum across `diff` for a running total. |
| spend | Normal | `MAX(spend)` grouped by (`gid`, `cli`, `install_month`) | Total UA spend for the cohort. **The identical value repeats on every `diff` row — confirmed live, one cohort carried the same value on 104 rows. Always `MAX()`, never `SUM()`.** |
| dau_month | Derived (dimension) | `date_add('month', diff, install_month)` | The calendar month `rev` was earned in. `diff` is a monthly aging index loosely analogous to the day-based `dX` windows (each step ≈ 30 days) — approximate, not an exact day-boundary match. |
| Monthly ROAS (diff) | Custom | `rev / spend` (spend via the `MAX()` rule) | Return from month `diff`'s revenue alone against total cohort spend. |
| Cumulative ROAS through diff N | Custom | `SUM(rev WHERE diff <= N) / MAX(spend)` | Running ROAS through N months post-install — usable well past the day-based caps. |

Plain Trino SQL — there is no `__time`, and `install_month` is a real `date` column (no `to_date()`
wrapper), while `gid`, `cli` and `diff` are `BIGINT` (compare unquoted):

```sql
SELECT gid, cli, install_month, diff,
       date_add('month', diff, install_month) AS dau_month, rev
FROM play_data.monthly_rev_diff
WHERE gid = <GID> AND cli = <CLI>
ORDER BY install_month, diff
```

```sql
-- spend must be deduplicated per cohort — never sum across diff
SELECT gid, cli, install_month, MAX(spend) AS spend
FROM play_data.monthly_rev_diff
WHERE gid = <GID> AND cli = <CLI>
GROUP BY 1, 2, 3
```

## Field-range facts

`dX_retained` is confirmed through **d360** on `chart_1706` (config `metrics` array: d1…d90, then d120,
d150, d180, d210, d240, d270, d300, d330, d360). It is the **only** cohort field family past d90 —
`overall_rev_dX` and `dX_active_days` are confirmed **capped at d90**. For cohort **revenue or ROAS**
past that cap, switch to `play_data.monthly_rev_diff` and say which grain the figure came from. Never
assume one family's range extends to another; the `metrics` array in `chart_config` is the check.

## Cohort maturity

A `dX` value only means something once `install_date + X days` has elapsed. An immature cohort shows a
near-zero `dX_retained` or `overall_rev_dX` next to a full `installs` count — a maturity artifact, not a
collapse. For multi-month windows: group by install month, work out the last fully-matured dX per month
against today's date, and state which dX was used for which cohort month.

**A `dX` metric is expected to be absent for recent cohorts, and that absence is never a finding.** A
cohort that installed yesterday has no D7 retention and no `overall_rev_d7`; asked for D7 ROAS on a window
ending yesterday, report it only for the install dates that have actually aged 7 days and say which dates
those are — never a near-zero D7 figure covering unaged cohorts, and never a shorter-horizon dX silently
substituted for the one requested.

## Data-delivery lag — the D-2 default (distinct from cohort maturity)

**Assume `spend` and revenue are complete only through D-2.** This is delivery lag, not maturity: the
cohort has aged fine, the ETL simply hasn't shipped that date. It hits every metric on the datasource,
including `installs` and `spend` for a cohort old enough to be fully mature.

- **Establish each variant's own freshness.** Confirmed live Aug 2026: the base `chart_1706-vN` carried
  `installs` one full day later than `chart_1706-vN-dt_flag-install_type` carried `spend` — same chart,
  same version, delivered a day apart. Every eCPI and actual-ROAS figure crosses those two variants, so
  check both before building the ratio. **Read it off the day-grained query you are already running
  against each variant rather than spending a separate `MAX("__time")` statement** — see "Query
  consolidation" in `references/query-engines.md`.
- **A trailing `spend = 0` beside live `installs` is the signature of this lag**, and it inflates eCPI
  toward zero and ROAS toward infinity if the date is left in. Drop the date per the alignment rule below,
  disclose it, and don't report it as a spend cut or a campaign pause.
- **Distinguish it from a genuine channel stop.** Delivery lag shows `spend = 0` with installs intact for
  only the trailing 1–2 dates, across *every* segment on the datasource. A real pause shows spend and
  installs falling together, in a specific segment, on dates already inside the delivered window. Check
  which pattern holds before describing either — they call for opposite conclusions.

**Known data-delivery gaps — xpromo and Apple Arcade (expected, not a drop).** Two revenue feeds arrive
on a lag by design. (1) **Xpromo** revenue is delivered in a ~10-day batch, so the **last ~10 days are
usually absent**. (2) **Apple Arcade** revenue trails ~4 days, so the **last ~4 days are usually
absent**. When a query touches xpromo revenue (e.g. `source_category` = `xpromo`) or Apple Arcade
revenue, exclude those trailing days from any trend or WoW/MoM read, or state plainly that the tail
isn't yet delivered. Never read the empty tail as a decline or flag it as an anomaly.

## Aligning ratios and comparisons when dates are dropped

Dropping an unmatured or undelivered date from a ratio (the catalog's date-alignment rule) shortens the
window. **Two periods of unequal length cannot be compared on an absolute metric.** Having trimmed one
period, either:

- **Trim the comparison period to the same day count** — a 6-day current week compares against the first
  6 days of the prior week, stated explicitly ("Aug 3–8 vs Jul 27–Aug 1, both 6 days"); or
- **Restrict the comparison to rate metrics** (eCPI, ROAS, Rev/DAU, retention), which are day-count
  neutral — and say so, rather than letting a spend or installs delta stand on mismatched windows.

Never report an absolute WoW/MoM delta across unequal day counts. It is the failure mode that looks fully
rule-compliant: every individual figure is correctly date-aligned, and the comparison between them is
still wrong.

## Ratio metrics with mismatched variant support

Applies **only** to the documented gaps below. Leave the unsupported side as a total, never drop the
ratio or substitute another dimension, and state the compromise explicitly.

- **rev/dau filtered by `source` / `source_category`** → filter revenue only; DAU stays total. State it:
  "rev/DAU (source_category=iap) = revenue filtered to iap ÷ total DAU (all sources) — the DAU variant
  has no source_category column."
- **A spend ratio filtered by `install_type` / `dt_flag`** → filter the installs side only; spend stays
  total.

## Dimensions

### Core KPI charts (`chart_579`, `chart_1170`)

- `gid` — game; resolve via `ps-entities`. **VARCHAR in Druid — quote the literal (`"gid" = '22'`).**
- `cli` — platform: 0 = Android, 1 = iOS, 2 = Amazon. Also VARCHAR.
- `country` — ISO code, stored **lowercase** (`us`, `gb`, `ca`, `au`, …); Tier-1 = US, GB, CA, AU as
  display labels, but filter on the lowercase literal (`country IN ('us','gb','ca','au')`) or the
  query silently returns zero rows instead of erroring.
- `source_category` — interstitial, banner, app_open, video, others, NA, xpromo, offerwall, iap, audio.
  **Base variant only** — absent from the `-source-source_category` DAU variant.
- `source` — ~80 values (applovin, appstore, fan…). **No default exclusion**; any exclusion list in a
  reference query is case-specific — ask before carrying one over. Base variant only.
- `geo_bucket` (gross) — a rollup, not a country. `country_bucket` — language-similarity rollup; ignore it.

### Cohort chart (`chart_1706`)

- `gid`, `cli`, `country`.
- `install_bucket` — organic, paid, untagged, organic (dt_t1), p2e, paid (preloads dt_t1),
  paid (preloads), organic (google play), xpromo, organic (w/o google play).
- `install_source` — facebook, apple search, applovin, organic (google play), …
- `install_type` — only_install / reinstall. **Absent from the spend variant.**
- `dt_flag` — true / false / NULL; business meaning unconfirmed. **Absent from the spend variant.**
- `device_language`, `install_build`.
