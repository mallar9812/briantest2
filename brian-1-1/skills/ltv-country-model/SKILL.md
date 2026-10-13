---
name: "ltv-country-model"
description: "Playsimple cohort LTV/ROAS at gid × platform × country (US / non-US Tier-1) — the Claude prediction, the revision-feedback lever and Claude revised, always compared against Growth, Growth_daily, DS and Actual. Use for D360/dX LTV or ROAS predictions, \"how accurate is the model\", per-game or per-platform prediction comparisons, over/under-prediction investigations, retention-vs-monetisation decomposition of a tail move, or to rebuild the LTV dashboard or the Google-Sheets prototype."
---

# Playsimple cohort LTV — Claude prediction & Claude revised

Predicts cumulative cohort revenue at dX (d30…d360) per **game × platform × country-bucket ×
install month**, and always shows it beside the other boards and the realised actual.

Supersedes the earlier "minimal one-lever" model. If you find notes describing a 10% day-7
floor, a ≥3-voter rule, or rolling retention as unusable, they are out of date.

---

## Rule 1 — never show one series alone

| Series | Source | Ladder published |
|---|---|---|
| **Actual** | `chart_1071-v40-accuracy-dn-model_type` · `actual_recovery` | every dX, matured only |
| **Claude prediction** | this model | d30…d360 |
| **Claude revised** | prediction re-read against the cohort's own ladder | d30…d360 |
| **Growth prediction** | `chart_3730-v44-target_bucket` · `weekly_d365_recovery_d7`, `d30_recovery` | **d30 and D365 only** |
| **Growth_daily** | `chart_1071-v40` · `model_type='Growth_daily'` | d30…d360, **no d60** |
| **DS prediction** | `chart_1071-v40` · `model_type='DS_DAU_model'` | d30…d360 |

- Omit a series **only** where its board publishes nothing at that horizon, and **name the board
  and the reason**. Never let a line silently vanish.
- **Growth prediction and Growth_daily are different boards and disagree.** Never blend them.
- Actual is blank for young cohorts by design — state it, never read it as a decline.

## Rule 2 — terminology, fixed

**Actual · Claude prediction · Claude revised · Growth prediction · Growth_daily · DS
prediction.** No synonyms ("forecast", "nowcast", "model", "v3"). Horizons are
`d30, d60, d90, d120, d180, d240, d360`. Metrics name themselves: "D360 revenue per install ($)",
"d120 ROAS", "Retention d30".

**Claude revised is a nowcast.** It uses data that did not exist when the prediction was made.
Report it to run the business; use the prediction to judge the model; **never compare their
errors**.

---

## The cell universe

Grain `(gid, cli, country-bucket, install month)`; bucket `u` = US, `n` = non-US Tier-1
(GB+CA+AU). Tier-1 only.

**Gate — both:** installs ≥ 1,500 (US) or ≥ 500 (non-US), **and** day-7 revenue ≥ $500. The
revenue gate is not optional: cells clear the install gate on ~1,500 installs while carrying
$1–$47 of day-7 revenue, which makes dX/d7 explode. They are 0.14% of revenue and produced the
entire error tail — mean error fell **51.8% → 18.4%** when it was added.

**Maturity:** a horizon is usable only when `as-of ≥ end_of_month(install month) + X days`.
Druid returns *partially accumulated* values, not nulls — reading one as an actual invents a
shortfall.

---

## Claude prediction

`prediction_dX = day-7 revenue × M`:

1. **Own multiple** — the cell's matured vintages (age ≥ 12 months, dX observable), recency
   half-life 6 months, weighted by day-7 dollars.
2. **Donor multiple** — 10 nearest cells, Gaussian kernel `H = 0.15` on log distance over
   `(r2/r7, ret_d7/ret_d1, r7/installs)`, relation weights same game ×3, platform ×1.5,
   country ×1.3, times log revenue.
3. **Credibility blend** in logs, `λ = n/(n+20000)` day-7 dollars behind the own estimate.
4. **Levers**, each vs the vintages behind the own estimate:
   `F_shape = (voters' r2/r7 ÷ cohort's) ^ 0.50` ·
   `F_decay = (cohort's ret_d7/ret_d1 ÷ voters') ^ 0.80` ·
   `F_vint = (observable-diagonal drift) ^ 0.60`
5. **`F_feedback` — see below. Do not omit it.**
6. **Calibration**, fitted on 2024 only: d30 1.062 · d60 1.053 · d90 1.049 · d120 1.046 ·
   d180 1.042 · d240 1.039 · d360 1.034.

Everything must be observable at `end of month + 10 days`. Audit it: a sampled re-run with
future horizons blanked must show **zero** violations.

---

## F_feedback — the revision-feedback lever

**The hole it fills.** The own-multiple pool needs cohorts ≥ 12 months old with d360 observable,
so the most recent twelve months of evidence — exactly where a regime break lives — never
reaches the multiple. `F_vint` was meant to cover it and measures ~1.00–1.04 in practice, i.e.
nearly inert. Result: months keep being revised down by 5–11% and the next month's prediction
comes in as high as ever.

```
R_m       = Σ revised_d360 / Σ prediction_d360   over cells of month m that have a revision
F_feedback(M) = ( recency-weighted geomean of R_{M-1}, R_{M-2}, R_{M-3} ) ^ k
                weights 3 / 2 / 1;  include a month only if its d30 had matured by
                end_of_month(M) + 10 days  (it always has for M-1, so this is observable)
prediction_dX  ×=  F_feedback(M)
```

**k = 1.0.** Revenue-weighted deviation of prediction ÷ actual at each month's deepest matured
horizon:

| k | 2024-01…2025-06 | 2025-11…2026-06 |
|---|---|---|
| 0.00 | 3.96% | 11.55% |
| 0.50 | 3.77% | 8.31% |
| 0.75 | 3.75% | 6.73% |
| **1.00** | **3.74%** | **5.21%** |

Monotonically better in **both** windows, so it passes the keep-both-years rule. Use 0.75 if you
want a conservative setting; the two differ by ~2% on a headline.

**Why it is safe in a calm regime.** `R_m` averaged **1.0006** across 2024 — the lever is
inert when the model is unbiased and only bites when revisions are persistently one-sided.

**Why it works.** Lag-1 autocorrelation of `R_m` is **+0.776** over 29 months. Last month's
revision genuinely predicts this month's.

**⚠ Do not confuse this with the residual-feedback idea recorded as rejected.** That test used
the model's own error on *matured* 2024/2025-H1 vintages, where `R_m ≈ 1.00` and there was
nothing to exploit — the correct conclusion for that period, and the wrong one to carry forward.
The regime changed in Nov-2025 (`R_m` 0.89–0.95 for eight straight months) and the signal
appeared. **Re-measure `R_m` before trusting any verdict about feedback.**

---

## Claude revised — the calculation

Measure the correction **once**, at the deepest fully matured rung, then apply it across the
ladder.

```
rung        = deepest dX whose actual is present AND > 0        (d360 → d240 → … → d30)
expected    = prediction_d360 × share_rung
ratio       = actual_at_rung / expected
revised_dX  = prediction_dX × ratio ^ rho                       rho = 0.75
```

**Ladder shares** (revenue-weighted mean of dX/d360 over matured gated cells):
d30 **0.417** · d60 0.555 · d90 0.647 · d120 0.716 · d180 0.819 · d240 0.893 · d360 1.000.

- **Why revise.** The prediction is made at ~day 10 then ignores the cohort. By d30 the cohort
  has banked 41.7% of its eventual d360 revenue, by d180 81.9%.
- **Why the deepest rung.** An immature rung compares a complete prediction against a
  part-accumulated actual and manufactures a shortfall.
- **Why one ratio for the ladder.** The correction is one statement about the cohort ("running
  8% cold"). Per-horizon ratios let a noisy d30 and a solid d180 contradict each other.
- **Why rho = 0.75.** rho = 1 over-reacts to month-specific noise (a promotion, an ad outage, a
  seasonal week) that does not persist to d360; rho = 0 ignores the cohort.
- **Why exponential.** Symmetric in proportional terms, can never go negative.
- **No revision exists** until the cohort's first rung matures — d30, about 30 days after the
  month closes. Return blank, never echo the prediction.

---

## Extraction — mandatory pins

Resolve versions every session; never hardcode `-vN`. Build the Druid name as
`chart_id + '-v' + version + independent_columns SORTED ALPHABETICALLY` — `chart_version` is not
reliably sorted.

```sql
SELECT chart_id, version, chart_version, independent_columns, metrics
FROM hive_metastore.play_data.chart_config
WHERE chart_id IN ('chart_1706','chart_1071','chart_3730') ORDER BY chart_id, chart_version
```

| Datasource | Mandatory pins |
|---|---|
| `chart_1071-v40-accuracy-dn-model_type` (actuals) | `reattribution_flag='installs'` |
| `chart_1071-v40` (DS, Growth_daily) | `reattribution_flag='installs'`, `accuracy='more accurate'`, **`dn='D7'`**, `model_type IN ('DS_DAU_model','Growth_daily')` |
| `chart_3730-v44-target_bucket` (Growth) | `accuracy='pred'` (**not** 'more accurate' — zero rows), `geo_bucket IN ('us','non_us_tier1')` |
| `chart_1706-v20` (installs, retention) | none; `country` is lowercase ISO here |
| `chart_1706-v20-dt_flag-install_type` (spend) | suffix sorts to `dt_flag-install_type` |

Pivot horizons with conditional aggregation, compress with `STRING_AGG`, split by
`country × cli` (and by year) when a result exceeds the inline limit:

```sql
SELECT STRING_AGG("rec", '|', 2000000) AS "d" FROM (
SELECT CONCAT("gid",'~',"cli",'~',"cb",'~',"ym",',',
  CAST("r30" AS VARCHAR),',',CAST("r360" AS VARCHAR)) AS "rec"
FROM (
  SELECT "gid","cli",
    CASE WHEN UPPER("country")='US' THEN 'u' ELSE 'n' END AS "cb",
    TIME_FORMAT(TIME_FLOOR("__time",'P1M'),'yyyyMM') AS "ym",
    CAST(ROUND(COALESCE(SUM(CASE WHEN "diff"='30'  THEN "actual_recovery" END),0),0) AS BIGINT) AS "r30",
    CAST(ROUND(COALESCE(SUM(CASE WHEN "diff"='360' THEN "actual_recovery" END),0),0) AS BIGINT) AS "r360"
  FROM "chart_1071-v40-accuracy-dn-model_type"
  WHERE "__time" >= TIMESTAMP '2023-01-01 00:00:00'
    AND "__time" <  TIMESTAMP '2026-08-01 00:00:00'
    AND "reattribution_flag" = 'installs'
    AND UPPER("country") = 'US' AND "cli" = '0'
  GROUP BY 1,2,3,4
) "t") "t2"
```

Then verify the record count against the Druid group count — any shortfall means records were
dropped:

```sql
SELECT COUNT(*) FROM (SELECT "gid","cli",UPPER("country"),
  TIME_FORMAT(TIME_FLOOR("__time",'P1M'),'yyyyMM')
  FROM "chart_1071-v40-accuracy-dn-model_type"
  WHERE "__time" >= TIMESTAMP '2023-01-01 00:00:00'
    AND "__time" < TIMESTAMP '2026-08-01 00:00:00'
    AND "reattribution_flag"='installs' GROUP BY 1,2,3,4) t
```

---

## Traps that have each cost real time

1. **`COALESCE` on every aggregate.** `CONCAT` returns NULL if any argument is NULL and
   `STRING_AGG` then drops the whole record — silently lost **287 of 3,621 cells**, biased
   toward sparse and young cohorts.
2. **`chart_1071.country` is `'US'` / `'TIER1(NON-US)'`, not ISO.** A `CA/GB/AU` filter returns
   zero rows silently. `chart_1706.country` *is* lowercase ISO.
3. **`dn` carries `'D2'` and `'D7'`.** Unpinned, DS double-counts ~1.7× and scores at +72% bias,
   looking broken when it is fine.
4. **Geo split disagrees.** `chart_1071` and `chart_1706` agree on Tier-1 *total* to 3.4% but
   split it 12.4% vs 8.4% non-US. Totals and the combined view are sound; non-US-only
   per-install mixes a 1071 numerator with a 1706 denominator — disclose it.
5. **Rolling retention (`chart_2301`) is unusable here** — daily user counts, no cohort
   attribution. Use `chart_1706` `dX_retained`, which runs to **d360** at cohort grain.
6. **Growth_daily has no `diff='60'`.** With COALESCE it arrives as 0 — treat 0 as absent.
7. **Never compare recent cohorts at shallow horizons against old ones at d360.** That mixes a
   horizon effect into a vintage effect. Hold the horizon fixed.
8. **Check the concentration before believing a portfolio number.** A single game can carry the
   whole disagreement — in Jul-2026, Crossword Go was 11% of installs and the entire gap to
   Growth (ex-Crossword Go the model sat 1.04× Growth; including it, 1.25×). Always report
   with-and-without the top contributor.

---

## Diagnosing a tail move

`d360/d7` is an identity:

```
d360/d7  =  (d360 active days ÷ d7 active days)  ×  (revenue per active day, d360 vs d7)
```

Active days from `actual_active_dau_days`. That is how the 2023→2025 decline was attributed:
active-days multiple 6.64 → 5.15 (−22%, the whole decline) while revenue per active day rose
0.86 → 0.90. Retention, not monetisation. Cross-check on `chart_1706`: d360 retention
1.63% → 0.89%, shape ratio d180/d7 down 33%.

**The trap this creates:** recent cohorts show *higher* d1/d7 retention and a *steeper* decay,
so a day-7 anchor reads a strong early signal and projects a tail that is gone.

---

## Rejected — but re-measure before trusting these

- **Retention-drift lever as a timing signal.** Scores 0.89–0.94 exactly when the model
  overshoots, so it looks right, but it had been falling since early 2025 while the break starts
  Nov-2025. At any strength it shifts every month, not the guilty ones.
- **Seasonality.** The raw calendar spread is a trend confound.
- **Engagement shape as a donor-matching feature.** Worse in both years.
- **Residual feedback on matured vintages** — superseded by `F_feedback`, which uses the
  *revision* on *recent* months instead. See the warning in that section.

---

## Honest findings to keep repeating

- **Growth is the better single D360 predictor on matured cohorts** — 2024 mean error 12.3% vs
  Claude 19.2%; 2025-H1 12.1% vs 16.1%. Say so. Claude's value is the full ladder, coverage of
  every gated cell, and the revision.
- **Some cells everything misses**: Crossword Go (Claude 0.63, Growth 0.60), Cryptogram,
  Word Wars. That is the cohorts, not the method.
- **The current break is not validatable on a d360 backtest** — it happened after the last
  matured cohort. The fixed-horizon ratio grid is the only honest test surface; re-check monthly,
  and re-fit `F_feedback` as `R_m` moves.

---

## Deliverables and verification

**Dashboard** — one self-contained HTML file, no external assets, no charting library (SVG built
by a small inline renderer; a library that sizes canvases while tabs are hidden draws nothing).
Global filters: country, platform, game, **horizon (drives every tab)**, install-months-from.

**Google-Sheets prototype** — Read me · Pipeline & method · SQL (every query verbatim with its
pins) · Controls (dropdowns, rho, ladder shares, feedback k) · Data · Claude revised calc (the
four steps as columns, cross-checked) · Monthly · Accuracy · Game × platform. Everything
downstream of the prediction is live formula. The prediction itself is a similarity search over
~2,000 cells and is **not** reproducible as a formula — say so rather than faking it.

**Before shipping either:**
- Execute the dashboard renderer headlessly across filter × horizon combinations and inspect the
  markup produced. A chart that renders empty must fail the build. **Stubbing the chart library
  proves nothing** — that mistake shipped a blank dashboard twice.
- Fail the build if any chart falls back to an empty state on the *unfiltered* view, or if any
  column the page reads is null on every row. That is how a silently-zero spend column is caught.
- Round-trip values out of the rendered output and compare against an independent recompute.
- Recalculate the workbook, require zero formula errors, **then still value-check** — an
  off-by-one yields a clean file with wrong numbers.

**Spreadsheet gotchas:** an inline data-validation list over 255 characters is malformed and
makes LibreOffice loop — point dropdowns at a cell range. openpyxl charts also stall it, so
verify a formula-identical chartless twin. `CHOOSE` evaluates every branch; prefer `INDEX` over
the contiguous block. Array `SUMPRODUCT` with `N(range)` is pathologically slow — use per-row
helper columns.

