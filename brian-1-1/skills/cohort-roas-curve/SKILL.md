---
name: cohort-roas-curve
description: "Computes a Playsimple install cohort's age-by-age ROAS curve, dollar revenue recovery, and payback timing, live from play_data.monthly_rev_diff. Use for the monthly/age-level ROAS curve of a specific install cohort (\"ROAS by month for [game]'s [month] cohort\", \"age 0-12 ROAS for this installment\"), the dollar revenue a cohort has recovered or will recover (\"how much will [game]'s March cohort make back\", \"recovery curve for this install month\", \"when does this cohort pay back its spend\"), or a calendar-month revenue projection built up from cohort curves (\"project monthly revenue for [game] over the next year\"). Actual-or-forecast per age: real data where monthly_rev_diff has it, else near-term ages forecast by chaining a trailing-cohort trend with a same-calendar-month seasonal pattern, and long-tail ages via a historical tail-share curve applied to the cohort's own anchor ROAS. NOT for a future install month with zero history -- that's revenue-projection instead.\n"
---

# Cohort ROAS & Revenue Recovery Curve

Builds one install cohort's full economics curve -- ROAS by age, dollar revenue
recovered by age, which calendar month each age's recovery lands in, and (with a
requested range of cohorts) a calendar-month revenue projection -- straight from
live data, so it's never stale.

**Scope note:** this fills in the *remaining, not-yet-happened ages of a cohort
that has already started*. If someone wants a portfolio revenue/spend forecast, a
scenario plan, or a brand-new future install month with no history at all, that's
a different job -- use the `revenue-projection` skill instead.

## The data model

| col | meaning |
|---|---|
| `gid` | game id |
| `cli` | platform (0/1/2) |
| `install_month` | cohort (DATE, first of month) |
| `diff` | months since install (0,1,2,...) |
| `rev` | incremental revenue earned in that diff-month |
| `spend` | cohort acquisition spend, repeated on every diff row -- take `MAX(spend)` per cohort, never `SUM` |

**Incremental ROAS at age *a*** = `rev_at_diff_a / cohort_spend`. **Recovery ($)
at age *a*** = `ROAS_at_age_a * cohort_spend` -- the dollar-scaled view of the same
number. **Return month** = `install_month + a months` -- the calendar month that
age's recovery lands in.

## Resolve the game first

Use `ps-entities`' resolution rule: match the user's game name case-insensitively
against `public.gid_mapping` (`SELECT gid, game_name FROM public.gid_mapping`),
resolve on exactly one candidate, ask once on two or more. If the user doesn't
name a platform, default to **all platforms combined** for that gid (sum `rev`,
sum `MAX(spend)` per cli); if they name one, filter to it.

## The model

For cohort row *r* (chronological) and age *a*:

1. **Actual first.** If `(install_month=r, diff=a)` exists in `monthly_rev_diff`,
   use its incremental ROAS. Done.
2. **Not enough history yet (fewer than 6 cohorts precede this one).** Leave as
   `no_data` -- there isn't yet a trailing window to build a trend ratio from.
3. **Age 0 with no actual.** Leave as `no_data` -- there's no previous age to
   chain from, and if this is happening it means the cohort hasn't installed yet
   (a genuinely future month), which this model isn't for (see Scope note above).
4. **Core ages (1 through 12), forecast by chaining off this cohort's own
   previous age:**
   ```
   value(r, a) = value(r, a-1) * blended_ratio(r, a)
   ```
   where `blended_ratio` mixes two ratios-between-consecutive-ages:
   - **Trend ratio** = `median(value(·, a) over the 6 cohorts immediately before r)
     / median(value(·, a-1) over those same 6 cohorts)` -- how this age's typical
     value has moved relative to the previous age's, recently.
   - **Seasonal ratio** = `seasonal_table[calendar_month(r)][a] /
     seasonal_table[calendar_month(r)][a-1]`, where `seasonal_table[m][a]` is the
     mean actual incremental ROAS at age `a`, pooled over every mature cohort (all
     13 core ages observed) that started in calendar month `m`. Recomputed live
     from history every run.
   - **Blend weight**: `w = clamp((a-1) * 5%, 0, 1)` -- 0% at age 1, ramping to
     55% at age 12. `blended_ratio = (1-w)*trend_ratio + w*seasonal_ratio`. Younger
     ages lean on the recent trend; older core ages lean more on the seasonal
     pattern.
   - Any division hiccup (no valid trailing data, zero denominator) falls back to
     `no_data` for that cell.
5. **Core cumulative ("anchor") ROAS** = `SUM(age 0..12)`, actual-or-forecast.
6. **Tail ages (13 and beyond), forecast as a share of the cohort's own anchor:**
   ```
   value(r, a) = anchor(r) * tail_share(a)
   ```
   where `tail_share(a)` is the historical average of `actual_value_at_age_a /
   that_cohort's_own_core_anchor`, pooled across every cohort that is core-mature
   (ages 0-12 all actual) **and** has at least one actual tail age observed.
   Computed live, one number per age, no calendar-month split (the further out a
   cohort gets, the less a same-month seasonal effect matters relative to the
   simple decay of the tail). Beyond the oldest tail age with real observations,
   extend geometrically: fit a monthly decay rate from the ratio between the
   oldest and newest observed tail-share values (`(newest/oldest)^(1/age gap)`),
   and keep multiplying by that rate for every age past the observed range.
   Actual data always overrides the tail-share estimate when it exists, same
   priority as the core ages.
7. **Payback age** = the first age at which cumulative Recovery($) reaches the
   cohort's spend (cumulative ROAS crosses 1.0), within whatever horizon was
   projected. Report "not reached within N months" if it never crosses.

## How to run it

Work in a scratch dir (e.g. the outputs folder).

### Step 1 -- resolve gid, pull the actual grid and spend

```sql
SELECT gid, game_name FROM public.gid_mapping
```
Match the user's game name; get its `gid`.

**Actual ROAS grid** -- pull every diff you have, not just 0-12; more tail history
makes the tail-share fit more reliable:
```sql
WITH sp AS (
  SELECT install_month, SUM(spend) AS spend FROM (
    SELECT cli, install_month, MAX(spend) AS spend
    FROM play_data.monthly_rev_diff WHERE gid = <GID> /* AND cli = <CLI> if scoped */
    GROUP BY 1,2
  ) GROUP BY 1
),
coh AS (
  SELECT install_month, diff, SUM(rev) AS rev
  FROM play_data.monthly_rev_diff WHERE gid = <GID> /* AND cli = <CLI> if scoped */
  GROUP BY 1,2
)
SELECT concat_ws('|', collect_list(concat_ws(',',
  cast(c.install_month as string), cast(c.diff as string), cast(c.rev/s.spend as string))))
FROM coh c JOIN sp s ON c.install_month = s.install_month
```
Split the returned string on `|` then `,` and write to `raw.csv` with header
`install_month,diff,inc_roas`.

**Cohort spend** (needed for dollar Recovery figures, optional for ROAS-only asks):
```sql
SELECT concat_ws('|', collect_list(concat_ws(',', cast(install_month as string), cast(spend as string))))
FROM (
  SELECT install_month, SUM(spend) AS spend FROM (
    SELECT cli, install_month, MAX(spend) AS spend
    FROM play_data.monthly_rev_diff WHERE gid = <GID> /* AND cli = <CLI> if scoped */
    GROUP BY 1,2
  ) GROUP BY 1
)
```
Split the same way into `spend.csv` with header `install_month,spend`.

### Step 2 -- run the script

```bash
python3 scripts/roas_curve.py --raw raw.csv --spend spend.csv --cohort 2026-03 --start 2018-01 --horizon 36
```
- `--cohort YYYY-MM` -- report a single install-month row (the common case: "ROAS
  and recovery for [game]'s March 2026 cohort").
- `--from-cohort YYYY-MM --to-cohort YYYY-MM` -- report a range instead.
- `--start YYYY-MM` -- earliest cohort month present in `raw.csv` (defaults to
  2018-01). The grid is built chronologically from here, so it must match (or
  predate) the earliest row actually pulled -- the trailing-cohort trend and the
  seasonal/tail tables all need that history in place before the requested
  cohort.
- `--horizon N` -- how many ages to project (0-indexed; default 36 = a 3-year
  curve). Raise it for a longer payback/recovery view (e.g. 120 for a 10-year
  curve), lower it for a quick 12-month ROAS-only look.
- `--rollup` -- when reporting a range, also sums Recovery($) across every cohort
  in that range grouped by the calendar month it lands in, writing
  `rev_by_month.csv` -- a monthly revenue projection built up from the individual
  cohort curves.
- `--tail-share-override FILE.csv` -- optional; columns `age,share`. Substitutes
  an externally-sourced tail-share-by-age table for the one this script would
  otherwise derive from `raw.csv` itself. Use this when cross-checking against
  another team's model or a reference spreadsheet that already has its own
  tail-share table -- pull their table, save it in this format, and pass it here
  so the rest of the run (core ages, spend, rollup) stays apples-to-apples while
  isolating whether the tail curve is the source of any discrepancy.

It prints each requested cohort's age-by-age ROAS + Recovery($) curve with an
`actual`/`forecast`/`no_data` flag per cell, the core (age 0-12) cumulative ROAS,
and the estimated payback age. It writes the full grid (every requested cohort x
age, with return month and both calendar-year flags) to `roas_grid.csv` for
spot-checking, and `rev_by_month.csv` if `--rollup` was used.

### Step 3 -- present it

Report the age-by-age table (age, ROAS, Recovery $, actual/forecast) and the
payback estimate, flagging clearly where actual data runs out and forecast begins.
For a revenue-projection ask, lead with the calendar-month rollup instead of the
per-cohort tables.

## Known limitations (be upfront about these)

- **Can't originate a curve with zero history.** A cohort with no age-0 actual
  data (hasn't installed yet) can't be forecast -- there's nothing to chain from.
  Say so plainly and point to `revenue-projection` for that use case.
- **First 6 cohorts of whatever range you pulled** have no trailing-cohort window
  yet, so missing actual cells there stay `no_data` rather than forecast.
- **Seasonal and tail tables both need mature cohorts.** A very young game (fewer
  than ~13 months of history, or no cohort yet with tail ages observed) won't have
  a real seasonal or tail-share table -- the trend ratio and a flat share estimate
  still work as a fallback, but flag the thin data if it comes up.
- **The tail-share geometric fit is only as good as the observed range.** If only
  a handful of tail ages have been observed, the decay rate extrapolated from them
  is a rough estimate -- say so when projecting far beyond the observed tail. The
  fitted rate is clamped so it can never come out as *growth* (see below), but a
  clamped-to-flat rate on thin data is still just a rough floor, not a confident
  estimate.

### Fixed issues (previously produced wrong or crashing output)

Both of these were found by running this script against real, live portfolio data
-- not hypothetical edge cases -- so they're documented here rather than silently
patched:

- **Crash on some real games.** The trend-ratio step divided `med_this / med_prev`
  after only checking that `med_prev` wasn't empty/zero. When the trailing cohorts
  had data at the *previous* age but not yet at the *current* age (`med_this`
  empty), this raised a `TypeError` and the whole run failed -- confirmed on a
  real game (Destination Solitaire, gid 18) with no workaround short of editing
  the script. Fixed by treating `med_this is None` as `no_data`, same as an empty
  `med_prev`.
- **Runaway tail-share growth on thin-tail games.** The geometric decay rate for
  extrapolating tail-share beyond the observed range was fit from just two points
  (the oldest and newest observed tail ages) with no sanity bound. For a young
  game with only a handful of tail ages observed, sampling noise can make that
  fit come out *above* 1.0 -- i.e. the model concludes the cohort's revenue tail
  *grows* forever. Applied across 50-100+ extrapolated ages, even a mild spurious
  rate compounds explosively: one real game's projection came out ~28% inflated
  *per month*, compounding into a multi-billion-dollar number for what should have
  been a low-six-figure curve. A cohort's long-run tail should decay or hold flat,
  never grow indefinitely, so the fitted rate is now clamped to a maximum of 1.0.
