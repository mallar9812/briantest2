#!/usr/bin/env python3
"""
roas_curve.py -- cohort ROAS curve + dollar revenue/recovery projection.

Builds a chronological grid of cohort-start-month x cohort-age, where each cell is
an incremental ROAS (revenue recognized at that age / total cohort spend):

  - If actual data already exists for that (install_month, diff), the cell is ACTUAL.
  - Otherwise it's FORECAST. Two different forecast mechanisms cover two different
    parts of a cohort's life:

    CORE (age 1..CORE_MAX, default 1..12): chain off this cohort's own previous
    age, scaled by a blend of (a) a recent-trend ratio -- the median value at this
    age vs. the median value at the previous age, over the 6 cohorts immediately
    before this one -- and (b) a seasonal ratio -- the historical average value at
    this age vs. the previous age, for cohorts that started in the same calendar
    month. The blend shifts from 100% trend (age 1) toward more seasonal weight as
    age increases (5 percentage points per age step), so young ages lean on what's
    happening recently and older ages lean on the seasonal pattern.

    TAIL (age CORE_MAX+1 .. horizon): once a cohort's core (ages 0..CORE_MAX) is
    known (actual or forecast), its cumulative "anchor" ROAS is fixed. Every tail
    age is anchor * tail_share(age), where tail_share(age) is the historical average
    fraction of a mature cohort's anchor ROAS that shows up at that age, computed
    live from every cohort with enough history to observe it. Beyond the oldest age
    with real observations, tail_share is extended with a geometric decay fitted
    from whatever tail range was actually observed (no fixed constant assumed).

  - The first TRAIL cohort rows (not enough trailing history to build a trend
    ratio) and age 0 with no actual data (nothing to chain from -- this happens
    for a cohort that hasn't installed yet) are left as `no_data`.

Recovery ($) = ROAS(age) * cohort spend, for any age where spend is known.

Input:
  --raw   CSV with columns install_month,diff,inc_roas -- every (install_month, diff)
          combination that ALREADY has actual data, for whatever diff range you have
          (at minimum 0..12; include higher diffs too if you want the tail model to
          calibrate against real long-tail data instead of decaying sooner).
  --spend CSV with columns install_month,spend -- each cohort's total acquisition
          spend. Needed only for the dollar Recovery figures; ROAS-only output works
          without it.

Output:
  Prints each requested cohort's age-by-age ROAS + Recovery($) curve, flagged
  actual/forecast/no_data, plus cumulative ROAS at the core horizon and (if spend is
  known) an estimated payback age -- the first age at which cumulative recovery
  reaches the cohort's spend.
  Writes roas_grid.csv (every requested cohort x age cell) and, with --rollup,
  rev_by_month.csv (Recovery $ summed across cohorts, grouped by the calendar month
  it lands in -- a revenue-by-month projection).
"""
import argparse
import csv
import sys
from collections import defaultdict

CORE_MAX = 12   # ages 0..CORE_MAX use the chained trend+seasonal model
TRAIL = 6       # trailing-cohort window for the trend ratio
RAMP = 0.05     # seasonal weight added per age step past age 1: w(age) = (age-1)*RAMP, clamped [0,1]


def ym(d):
    """'2024-03-01' or '2024-03' -> (2024, 3)"""
    y, m = str(d)[:7].split('-')
    return int(y), int(m)


def add_month(y, m, n):
    idx = (y * 12 + (m - 1)) + n
    return idx // 12, idx % 12 + 1


def key(y, m):
    return f"{y:04d}-{m:02d}"


def load_pairs(path, cols):
    out = defaultdict(dict) if len(cols) == 3 else {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            yield row


def load_raw(path):
    actual = defaultdict(dict)  # actual[cohort_key][age] = inc_roas
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            y, m = ym(row["install_month"])
            age = int(float(row["diff"]))
            if age >= 0:
                actual[key(y, m)][age] = float(row["inc_roas"])
    return actual


def load_spend(path):
    spend = {}
    if not path:
        return spend
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            y, m = ym(row["install_month"])
            spend[key(y, m)] = float(row["spend"])
    return spend


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def build_seasonal_table(actual):
    """Mean inc_roas by (calendar_month, age) for age 0..CORE_MAX, pooled over MATURE
    cohorts only (all CORE_MAX+1 ages observed). Falls back to the age's overall mean
    across all calendar months if a specific (month, age) bucket has no mature data."""
    buckets = defaultdict(list)
    for ck, ages in actual.items():
        if not all(a in ages for a in range(0, CORE_MAX + 1)):
            continue
        y, m = ym(ck + "-01")
        for age in range(0, CORE_MAX + 1):
            buckets[(m, age)].append(ages[age])
    seasonal = {k: sum(v) / len(v) for k, v in buckets.items()}
    overall = defaultdict(list)
    for (m, age), avg in seasonal.items():
        overall[age].append(avg)
    fallback = {age: sum(v) / len(v) for age, v in overall.items()}
    return seasonal, fallback


def seasonal_value(seasonal, fallback, cal_month, age):
    return seasonal.get((cal_month, age), fallback.get(age))


def build_core_grid(actual, cohort_keys):
    """Ages 0..CORE_MAX for every cohort in cohort_keys (chronological)."""
    seasonal, fallback = build_seasonal_table(actual)
    grid, flags, order = {}, {}, []

    for row_idx, ck in enumerate(cohort_keys):
        grid[ck], flags[ck] = {}, {}
        y, m = ym(ck + "-01")
        acts = actual.get(ck, {})
        for age in range(0, CORE_MAX + 1):
            if age in acts:
                grid[ck][age] = acts[age]
                flags[ck][age] = "actual"
                continue
            if row_idx < TRAIL:
                grid[ck][age] = 0.0
                flags[ck][age] = "no_data"        # not enough trailing cohorts to forecast yet
                continue
            if age == 0:
                grid[ck][age] = 0.0
                flags[ck][age] = "no_data"        # nothing to chain age 0 off of
                continue
            prev_val = grid[ck][age - 1]
            trail_rows = order[row_idx - TRAIL:row_idx]
            this_col = [grid[r][age] for r in trail_rows if flags[r].get(age) in ("actual", "forecast")]
            prev_col = [grid[r][age - 1] for r in trail_rows if flags[r].get(age - 1) in ("actual", "forecast")]
            med_this, med_prev = median(this_col), median(prev_col)
            if not med_prev or med_this is None:
                grid[ck][age] = 0.0
                flags[ck][age] = "no_data"
                continue
            trend_ratio = med_this / med_prev
            w = min(1.0, max(0.0, (age - 1) * RAMP))
            s_this = seasonal_value(seasonal, fallback, m, age)
            s_prev = seasonal_value(seasonal, fallback, m, age - 1)
            seasonal_ratio = (s_this / s_prev) if (s_this is not None and s_prev) else trend_ratio
            blended = (1 - w) * trend_ratio + w * seasonal_ratio
            grid[ck][age] = prev_val * blended
            flags[ck][age] = "forecast"
        order.append(ck)
    return grid, flags


def build_tail_share(actual):
    """For every cohort mature enough to have both a full core (0..CORE_MAX) and at
    least one tail age observed, share(age) = actual_tail_value / core_M12_actual.
    Averaged per age across all such cohorts. Returns (tail_share dict, max observed
    tail age, fitted monthly decay rate beyond that age)."""
    per_age = defaultdict(list)
    for ck, ages in actual.items():
        if not all(a in ages for a in range(0, CORE_MAX + 1)):
            continue
        core_m12 = sum(ages[a] for a in range(0, CORE_MAX + 1))
        if core_m12 <= 0:
            continue
        for age, val in ages.items():
            if age > CORE_MAX:
                per_age[age].append(val / core_m12)
    tail_share = {age: sum(v) / len(v) for age, v in per_age.items()}
    if not tail_share:
        return {}, CORE_MAX, 1.0
    max_age = max(tail_share)
    ages_sorted = sorted(tail_share)
    lo, hi = ages_sorted[0], ages_sorted[-1]
    if hi > lo and tail_share[lo] > 0:
        monthly_decay = (tail_share[hi] / tail_share[lo]) ** (1.0 / (hi - lo))
    else:
        monthly_decay = 1.0
    # A cohort's long-run revenue tail should decay or hold flat, never grow
    # indefinitely. With only a handful of observed tail ages the fit above is
    # noisy and can spuriously come out above 1.0 -- and because this rate gets
    # applied multiplicatively for every age beyond the observed range (often
    # 50-100+ ages), even a mild spurious >1.0 fit compounds into wildly
    # overstated long-horizon numbers. Clamp it as a sanity bound.
    monthly_decay = min(monthly_decay, 1.0)
    return tail_share, max_age, monthly_decay


def tail_share_at(tail_share, max_age, monthly_decay, age):
    if age in tail_share:
        return tail_share[age]
    if not tail_share:
        return 0.0
    return tail_share[max_age] * (monthly_decay ** (age - max_age))


def extend_with_tail(core_grid, core_flags, actual, cohort_keys, horizon, tail_share_override=None):
    """Extend each cohort's grid from CORE_MAX+1 up to horizon-1 using the tail-share
    model anchored on that cohort's own core cumulative ROAS (actual-or-forecast)."""
    if tail_share_override is not None:
        tail_share = dict(tail_share_override)
        if tail_share:
            max_age = max(tail_share)
            ages_sorted = sorted(tail_share)
            lo, hi = ages_sorted[0], ages_sorted[-1]
            monthly_decay = (tail_share[hi] / tail_share[lo]) ** (1.0 / (hi - lo)) if (hi > lo and tail_share[lo] > 0) else 1.0
            monthly_decay = min(monthly_decay, 1.0)
        else:
            max_age, monthly_decay = CORE_MAX, 1.0
    else:
        tail_share, max_age, monthly_decay = build_tail_share(actual)
    grid, flags = {ck: dict(core_grid[ck]) for ck in cohort_keys}, {ck: dict(core_flags[ck]) for ck in cohort_keys}
    anchor = {}
    for ck in cohort_keys:
        anchor[ck] = sum(core_grid[ck][a] for a in range(0, CORE_MAX + 1))
        acts = actual.get(ck, {})
        for age in range(CORE_MAX + 1, horizon):
            if age in acts:
                grid[ck][age] = acts[age]
                flags[ck][age] = "actual"
                continue
            if core_flags[ck][0] == "no_data":
                grid[ck][age] = 0.0
                flags[ck][age] = "no_data"
                continue
            share = tail_share_at(tail_share, max_age, monthly_decay, age)
            grid[ck][age] = anchor[ck] * share
            flags[ck][age] = "forecast"
    return grid, flags, anchor, (tail_share, max_age, monthly_decay)


def build_full_grid(actual, start_key, end_key, horizon, tail_share_override=None):
    sy, sm = ym(start_key + "-01")
    ey, em = ym(end_key + "-01")
    n_months = (ey * 12 + em) - (sy * 12 + sm) + 1
    if n_months < 1:
        sys.exit(f"end cohort {end_key} is before start {start_key}")
    cohort_keys = [key(*add_month(sy, sm, i)) for i in range(n_months)]

    core_grid, core_flags = build_core_grid(actual, cohort_keys)
    if horizon > CORE_MAX + 1:
        grid, flags, anchor, tail_info = extend_with_tail(
            core_grid, core_flags, actual, cohort_keys, horizon, tail_share_override=tail_share_override)
    else:
        grid, flags = core_grid, core_flags
        anchor = {ck: sum(core_grid[ck][a] for a in range(0, CORE_MAX + 1)) for ck in cohort_keys}
        tail_info = ({}, CORE_MAX, 1.0)
    return grid, flags, anchor, cohort_keys, tail_info


def return_month(cohort_key, age):
    y, m = ym(cohort_key + "-01")
    ry, rm = add_month(y, m, age)
    return key(ry, rm)


def crosses_calendar_year(cohort_key, ret_month):
    return int(cohort_key[:4]) < int(ret_month[:4])


def payback_age(grid_row, spend_val, horizon):
    if not spend_val:
        return None
    cum = 0.0
    for age in range(horizon):
        cum += grid_row[age]
        if cum >= 1.0:
            return age
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw.csv")
    ap.add_argument("--spend", default=None, help="csv: install_month,spend (needed for dollar Recovery)")
    ap.add_argument("--cohort", help="single install month to report, YYYY-MM")
    ap.add_argument("--from-cohort", dest="from_cohort", help="range start, YYYY-MM")
    ap.add_argument("--to-cohort", dest="to_cohort", help="range end, YYYY-MM")
    ap.add_argument("--start", default="2018-01",
                     help="earliest cohort month present in the source data (the grid needs history from here)")
    ap.add_argument("--horizon", type=int, default=36,
                     help="total ages to project, 0-indexed (default 36 = ages 0..35, i.e. 3 years)")
    ap.add_argument("--rollup", action="store_true",
                     help="also aggregate Recovery($) across the reported cohort range, grouped by the "
                          "calendar month it lands in, and write rev_by_month.csv")
    ap.add_argument("--tail-share-override", default=None,
                     help="csv: age,share -- replace the internally-derived tail-share-by-age table with an "
                          "external one (e.g. pulled directly from a reference spreadsheet or BI tool, for "
                          "cross-checking this model against another team's numbers). Extrapolation beyond the "
                          "max listed age still uses a fitted decay rate (clamped <=1.0) derived from this "
                          "table's own tail.")
    a = ap.parse_args()

    actual = load_raw(a.raw)
    if not actual:
        sys.exit(f"No rows read from {a.raw}")
    spend = load_spend(a.spend)
    tail_share_override = None
    if a.tail_share_override:
        tail_share_override = {}
        with open(a.tail_share_override, newline='') as f:
            for row in csv.DictReader(f):
                tail_share_override[int(row['age'])] = float(row['share'])

    end_key = a.to_cohort or a.cohort
    if not end_key:
        sys.exit("Provide --cohort YYYY-MM (single) or --from-cohort/--to-cohort (range)")
    grid, flags, anchor, cohort_keys, (tail_share, max_tail_age, monthly_decay) = \
        build_full_grid(actual, a.start, end_key, a.horizon, tail_share_override=tail_share_override)

    report_keys = [a.cohort] if a.cohort else \
        [k for k in cohort_keys if k >= (a.from_cohort or a.start)]

    with open("roas_grid.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["install_month", "age", "return_month", "roas", "recovery", "source",
                    "within_first_year", "crosses_calendar_year"])
        for ck in cohort_keys:
            sp = spend.get(ck)
            for age in range(a.horizon):
                rm = return_month(ck, age)
                roas = grid[ck][age]
                rec = round(roas * sp, 2) if sp else ""
                w.writerow([ck, age, rm, round(roas, 6), rec, flags[ck][age],
                            int(age <= CORE_MAX), int(crosses_calendar_year(ck, rm))])

    for ck in report_keys:
        sp = spend.get(ck)
        core_total = anchor[ck]
        if flags[ck][0] == "no_data":
            print(f"\nCohort {ck} -- NO ACTUAL DATA AT AGE 0 (this cohort hasn't installed yet, "
                  f"or spend/rev hasn't landed yet). A curve can't be originated without at least "
                  f"one real data point to chain from.")
            continue
        print(f"\nCohort {ck} -- core (age 0-{CORE_MAX}) cumulative ROAS: {core_total:.4f}"
              + (f" | spend: {sp:,.0f}" if sp else " | spend: unknown (no dollar figures below)"))
        pay = payback_age(grid[ck], sp, a.horizon) if sp else None
        if sp:
            print(f"Estimated payback: {'age ' + str(pay) if pay is not None else f'not reached within {a.horizon} months'}")
        print(f"{'age':>4}  {'roas':>10}  {'recovery($)':>14}  source")
        for age in range(a.horizon):
            roas = grid[ck][age]
            rec = f"{roas*sp:,.2f}" if sp else "--"
            print(f"{age:>4}  {roas:>10.4f}  {rec:>14}  {flags[ck][age]}")

    if a.rollup:
        by_month = defaultdict(float)
        missing_spend = set()
        for ck in report_keys:
            sp = spend.get(ck)
            if not sp:
                missing_spend.add(ck)
                continue
            for age in range(a.horizon):
                rm = return_month(ck, age)
                by_month[rm] += grid[ck][age] * sp
        with open("rev_by_month.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["return_month", "revenue"])
            for rm in sorted(by_month):
                w.writerow([rm, round(by_month[rm], 2)])
        print(f"\n-> rev_by_month.csv (Recovery $ summed by calendar month, across {len(report_keys)-len(missing_spend)} "
              f"cohort(s) with known spend{', skipped ' + str(len(missing_spend)) + ' with no spend' if missing_spend else ''})")

    print("\n-> roas_grid.csv (every reported cohort x age cell, with ROAS, Recovery $, and actual/forecast/no_data flag)")


if __name__ == "__main__":
    main()
