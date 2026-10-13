#!/usr/bin/env python3
"""
roas_curve.py -- cohort ROAS curve + dollar revenue/recovery/projection.

Builds a chronological grid of cohort-start-month x cohort-age, where each cell is
an incremental ROAS (revenue recognized at that age / total cohort spend). Every
cohort row falls into one of three regimes, evaluated in this priority order:

  1. ACTUAL -- if the exact (install_month, diff) already has recorded data, use it.

  2. FORECAST -- this cohort has *started* (at least one actual data point exists
     for it) but this particular age hasn't happened/landed yet:
       - core ages (1..CORE_MAX): chain off this cohort's own previous age, scaled
         by a blend of a recent-trend ratio (trailing 6 cohorts) and a
         same-calendar-month seasonal ratio, shifting toward seasonal as age rises.
       - tail ages (CORE_MAX+1..horizon): this cohort's own core cumulative
         ("anchor") ROAS times a historical tail-share curve for that age.

  3. PROJECTED -- this cohort has NO actual data at all yet (a genuinely future
     install month that hasn't happened). There's nothing of its own to chain off
     or anchor on, so instead:
       - Input ROAS is assumed: the previous cohort's own anchor ROAS (real,
         forecast, or itself assumed), grown by --roas-growth per month (if not
         given, auto-derived from the trailing reliable cohorts' own trend), or
         a flat --assumed-roas if given.
       - Input Spend is assumed the same way, compounding off the latest actual
         spend at --spend-growth per month (default 0.01 = 1%/month if not
         given), a flat --assumed-spend, or specific --spend-schedule months.
       - Every age's value = Input ROAS * that age's normalized share of a typical
         cohort's lifetime ROAS -- core ages from a same-calendar-month share
         table (each calendar month's shares sum to 1 across ages 0..CORE_MAX),
         tail ages from the same tail-share curve used in regime 2.
     PROJECTED cells are flagged distinctly from FORECAST ones everywhere in the
     output, because they rest on an explicit growth assumption rather than on
     this cohort's own realized data -- never blend the two together silently.

Recovery ($) = ROAS(age) * cohort spend (real for actual/forecast cohorts, assumed
for projected ones), for any age where a spend figure -- real or assumed -- exists.

Input:
  --raw   CSV with columns install_month,diff,inc_roas -- every (install_month, diff)
          combination that ALREADY has actual data. Pull whatever diff range you
          have; more tail history makes the tail-share fit more reliable.
  --spend CSV with columns install_month,spend -- each cohort's total acquisition
          spend, for every cohort that has actually started. Needed for dollar
          Recovery figures and as the seed for future-cohort spend assumptions.

Output:
  Prints each requested cohort's age-by-age ROAS + Recovery($) curve, flagged
  actual/forecast/projected/no_data, the core (age 0-12) cumulative ROAS, and (if
  spend is known or assumed) an estimated payback age. For any PROJECTED cohort in
  the range it also prints the Input Spend/Input ROAS assumption and growth rates
  used, so an assumption-driven number is never mistaken for a data-grounded one.
  Writes roas_grid.csv (every requested cohort x age cell) and, with --rollup,
  rev_by_month.csv (Recovery $ summed by the calendar month it lands in -- a
  revenue-by-month projection that includes future cohorts if the requested range
  extends past the last real install month).
"""
import argparse
import csv
import sys
from collections import defaultdict

CORE_MAX = 12   # ages 0..CORE_MAX use the chained trend+seasonal model (or, for
                # projected cohorts, the normalized core-share model)
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


def load_raw(path):
    actual = defaultdict(dict)  # actual[cohort_key][age] = inc_roas
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            y, m = ym(row["install_month"])
            age = int(float(row["diff"]))
            if age >= 0:
                actual[key(y, m)][age] = float(row["inc_roas"])
    return actual


def load_spend(path, value_col="spend"):
    spend = {}
    if not path:
        return spend
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            y, m = ym(row["install_month"])
            spend[key(y, m)] = float(row[value_col])
    return spend


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def build_seasonal_ratio_table(actual):
    """Mean inc_roas by (calendar_month, age) for age 0..CORE_MAX, pooled over MATURE
    cohorts (all CORE_MAX+1 ages observed). Used only for the *ratio* between
    consecutive ages in the chain-forecast method (regime 2) -- normalization
    doesn't matter there since it cancels out of a ratio."""
    buckets = defaultdict(list)
    for ck, ages in actual.items():
        if not all(a in ages for a in range(0, CORE_MAX + 1)):
            continue
        y, m = ym(ck + "-01")
        for age in range(0, CORE_MAX + 1):
            buckets[(m, age)].append(ages[age])
    table = {k: sum(v) / len(v) for k, v in buckets.items()}
    overall = defaultdict(list)
    for (m, age), avg in table.items():
        overall[age].append(avg)
    fallback = {age: sum(v) / len(v) for age, v in overall.items()}
    return table, fallback


def build_core_share_table(actual):
    """Normalized share by (calendar_month, age): each mature cohort's own age-value
    divided by that SAME cohort's own core (0..CORE_MAX) total, averaged per (month,
    age). By construction every calendar month's shares sum to ~1.0 across ages
    0..CORE_MAX. Used to originate a PROJECTED (never-started) cohort's core curve
    directly as Input_ROAS * share, since there's no real previous age to chain off."""
    buckets = defaultdict(list)
    for ck, ages in actual.items():
        if not all(a in ages for a in range(0, CORE_MAX + 1)):
            continue
        core_m12 = sum(ages[a] for a in range(0, CORE_MAX + 1))
        if core_m12 <= 0:
            continue
        y, m = ym(ck + "-01")
        for age in range(0, CORE_MAX + 1):
            buckets[(m, age)].append(ages[age] / core_m12)
    table = {k: sum(v) / len(v) for k, v in buckets.items()}
    overall = defaultdict(list)
    for (m, age), avg in table.items():
        overall[age].append(avg)
    fallback = {age: sum(v) / len(v) for age, v in overall.items()}
    return table, fallback


def derive_roas_growth(actual, anchor_by_cohort, ordered_keys, flags,
                        min_actual_ages=3, trail=6, clamp=0.03):
    """Default monthly ROAS growth rate for projected (never-started) cohorts,
    derived from the portfolio/game's own recent trend instead of assuming
    flat carry-forward. Uses the trailing `trail` non-future cohorts whose own
    core (age 0..CORE_MAX) curve already has at least `min_actual_ages` real
    data points -- this deliberately excludes the newest cohort(s) when they
    only have a handful of actual ages (often just age 0), since the model's
    own known-limitations note flags those as the least reliable to anchor on.
    Returns (rate, cohorts_used) so the caller can report what went into it.
    Geometric mean of month-over-month change in the (forecast-completed)
    anchor ROAS across those cohorts; clamped to +/-`clamp`/month so a short
    recent window can't compound into an extreme long-run assumption -- the
    same kind of sanity bound already applied to tail-share extrapolation."""
    candidates = []
    for ck in ordered_keys:
        if flags[ck][0] not in ("actual", "forecast"):
            continue
        n_actual = sum(1 for a in range(CORE_MAX + 1) if a in actual.get(ck, {}))
        if n_actual >= min_actual_ages:
            candidates.append((ck, anchor_by_cohort[ck]))
    used = candidates[-trail:]
    if len(used) < 2:
        return 0.0, used
    ratios = [used[i + 1][1] / used[i][1] for i in range(len(used) - 1) if used[i][1] > 0]
    if not ratios:
        return 0.0, used
    geo_mean = 1.0
    for r in ratios:
        geo_mean *= r
    geo_mean **= (1.0 / len(ratios))
    rate = geo_mean - 1.0
    rate = max(-clamp, min(clamp, rate))
    return rate, used


def build_tail_share(actual):
    """share(age) = actual_tail_value / that cohort's own core anchor, averaged per
    age across every cohort that is core-mature AND has that tail age observed.
    Returns (tail_share dict, max observed age, fitted monthly decay beyond it)."""
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
    monthly_decay = (tail_share[hi] / tail_share[lo]) ** (1.0 / (hi - lo)) if (hi > lo and tail_share[lo] > 0) else 1.0
    # A long-run per-cohort revenue tail should decay or hold flat, never grow indefinitely.
    # With only a handful of observed tail ages the fit is noisy and can spuriously exceed 1.0,
    # which compounds explosively over 100+ extrapolated ages. Clamp to <=1.0 as a sanity bound.
    monthly_decay = min(monthly_decay, 1.0)
    return tail_share, max_age, monthly_decay


def tail_share_at(tail_share, max_age, monthly_decay, age):
    if age in tail_share:
        return tail_share[age]
    if not tail_share:
        return 0.0
    return tail_share[max_age] * (monthly_decay ** (age - max_age))


def core_share_at(share_table, fallback, cal_month, age):
    v = share_table.get((cal_month, age))
    return v if v is not None else fallback.get(age, 0.0)


def build_full_grid(actual, spend, start_key, end_key, horizon,
                     a_assumed_roas=None, a_assumed_spend=None, roas_growth=0.0, spend_growth=0.0,
                     spend_schedule=None, roas_schedule=None, core_share_override=None, tail_share_override=None):
    spend_schedule = spend_schedule or {}
    roas_schedule = roas_schedule or {}
    sy, sm = ym(start_key + "-01")
    ey, em = ym(end_key + "-01")
    n_months = (ey * 12 + em) - (sy * 12 + sm) + 1
    if n_months < 1:
        sys.exit(f"end cohort {end_key} is before start {start_key}")
    cohort_keys = [key(*add_month(sy, sm, i)) for i in range(n_months)]

    seasonal_ratio, seasonal_ratio_fb = build_seasonal_ratio_table(actual)
    if core_share_override is not None:
        core_share, core_share_fb = core_share_override, {}
    else:
        core_share, core_share_fb = build_core_share_table(actual)
    tail_share, max_tail_age, monthly_decay = build_tail_share(actual)
    if tail_share_override is not None:
        tail_share = dict(tail_share_override)
        max_tail_age = max(tail_share)
        ages_sorted = sorted(tail_share)
        lo, hi = ages_sorted[0], ages_sorted[-1]
        monthly_decay = (tail_share[hi] / tail_share[lo]) ** (1.0 / (hi - lo)) if (hi > lo and tail_share[lo] > 0) else 1.0
        monthly_decay = min(monthly_decay, 1.0)

    grid, flags, order = {}, {}, []
    anchor = {}                      # each cohort's core (0..CORE_MAX) cumulative ROAS
    effective_spend = dict(spend)    # real spend, extended with assumed spend for projected cohorts
    input_used = {}                  # cohort_key -> (input_roas, input_spend) for cohorts that used assumptions
    prev_anchor, prev_spend = None, None

    for row_idx, ck in enumerate(cohort_keys):
        grid[ck], flags[ck] = {}, {}
        y, m = ym(ck + "-01")
        acts = actual.get(ck, {})
        is_future = len(acts) == 0

        if not is_future:
            # regime 1 (actual) + regime 2 (forecast off this cohort's own data)
            for age in range(0, CORE_MAX + 1):
                if age in acts:
                    grid[ck][age] = acts[age]
                    flags[ck][age] = "actual"
                    continue
                if row_idx < TRAIL or age == 0:
                    grid[ck][age] = 0.0
                    flags[ck][age] = "no_data"
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
                s_this = seasonal_ratio.get((m, age), seasonal_ratio_fb.get(age))
                s_prev = seasonal_ratio.get((m, age - 1), seasonal_ratio_fb.get(age - 1))
                seasonal_r = (s_this / s_prev) if (s_this is not None and s_prev) else trend_ratio
                grid[ck][age] = prev_val * ((1 - w) * trend_ratio + w * seasonal_r)
                flags[ck][age] = "forecast"
            anchor[ck] = sum(grid[ck][a] for a in range(0, CORE_MAX + 1))
            for age in range(CORE_MAX + 1, horizon):
                if age in acts:
                    grid[ck][age] = acts[age]
                    flags[ck][age] = "actual"
                    continue
                if flags[ck][0] == "no_data":
                    grid[ck][age] = 0.0
                    flags[ck][age] = "no_data"
                    continue
                share = tail_share_at(tail_share, max_tail_age, monthly_decay, age)
                grid[ck][age] = anchor[ck] * share
                flags[ck][age] = "forecast"
            cohort_spend = spend.get(ck)
            if flags[ck][0] != "no_data":
                prev_anchor = anchor[ck]
            if cohort_spend:
                prev_spend = cohort_spend
        else:
            # regime 3: PROJECTED -- cohort hasn't started, nothing of its own to use.
            if ck in roas_schedule:
                input_roas = roas_schedule[ck]
            elif a_assumed_roas is not None:
                input_roas = a_assumed_roas
            else:
                input_roas = prev_anchor * (1 + roas_growth) if prev_anchor is not None else None
            if ck in spend_schedule:
                input_spend = spend_schedule[ck]
            elif a_assumed_spend is not None:
                input_spend = a_assumed_spend
            else:
                input_spend = prev_spend * (1 + spend_growth) if prev_spend is not None else None
            input_used[ck] = (input_roas, input_spend)
            for age in range(0, CORE_MAX + 1):
                share = core_share_at(core_share, core_share_fb, m, age)
                grid[ck][age] = (input_roas * share) if input_roas is not None else 0.0
                flags[ck][age] = "projected" if input_roas is not None else "no_data"
            anchor[ck] = sum(grid[ck][a] for a in range(0, CORE_MAX + 1))
            for age in range(CORE_MAX + 1, horizon):
                share = tail_share_at(tail_share, max_tail_age, monthly_decay, age)
                grid[ck][age] = (input_roas * share) if input_roas is not None else 0.0
                flags[ck][age] = "projected" if input_roas is not None else "no_data"
            if input_roas is not None:
                prev_anchor = input_roas
            if input_spend is not None:
                effective_spend[ck] = input_spend
                prev_spend = input_spend
        order.append(ck)

    return grid, flags, anchor, cohort_keys, effective_spend, input_used


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
    ap.add_argument("--spend", default=None, help="csv: install_month,spend (real cohorts; also seeds future-cohort assumptions)")
    ap.add_argument("--cohort", help="single install month to report, YYYY-MM (may be in the future)")
    ap.add_argument("--from-cohort", dest="from_cohort", help="range start, YYYY-MM")
    ap.add_argument("--to-cohort", dest="to_cohort", help="range end, YYYY-MM (may be in the future)")
    ap.add_argument("--start", default="2018-01",
                     help="earliest cohort month present in the source data (the grid needs history from here)")
    ap.add_argument("--horizon", type=int, default=36,
                     help="ages to project per cohort, 0-indexed (default 36 = ages 0..35, i.e. 3 years)")
    ap.add_argument("--rollup", action="store_true",
                     help="also aggregate Recovery($) across the reported cohort range, grouped by the "
                          "calendar month it lands in, and write rev_by_month.csv")
    ap.add_argument("--roas-growth", type=float, default=None,
                     help="monthly growth rate applied when carrying Input ROAS forward into projected "
                          "(never-started) future cohorts. If omitted, derived automatically from the "
                          "trailing reliable cohorts' own recent trend (see derive_roas_growth) instead "
                          "of assuming flat -- pass 0.0 explicitly to force flat carry-forward instead.")
    ap.add_argument("--spend-growth", type=float, default=None,
                     help="monthly growth rate applied when carrying Input Spend forward into projected "
                          "future cohorts, compounding off the latest actual spend (e.g. Aug=$100K, "
                          "1%%/mo -> Sep=$101K, Oct=$102.01K, ...). If omitted, defaults to 0.01 "
                          "(1%%/month) as a stated baseline assumption, not flat -- pass 0.0 explicitly "
                          "for flat carry-forward, or use --spend-schedule/--assumed-spend when the "
                          "person gives you real figures instead of wanting this default.")
    ap.add_argument("--assumed-roas", type=float, default=None,
                     help="flat Input ROAS to use for every projected future cohort, overriding carry-forward.")
    ap.add_argument("--assumed-spend", type=float, default=None,
                     help="flat Input Spend to seed the first projected future cohort, overriding carry-forward "
                          "(subsequent projected cohorts still grow from it via --spend-growth).")
    ap.add_argument("--spend-schedule", default=None,
                     help="csv: install_month,spend -- explicit Input Spend for specific future (projected) "
                          "cohort months, overriding carry-forward/growth for those months. Months not listed "
                          "fall back to carrying forward the last explicit or derived spend value.")
    ap.add_argument("--roas-schedule", default=None,
                     help="csv: install_month,roas -- explicit Input ROAS for specific future (projected) "
                          "cohort months, overriding carry-forward/growth for those months.")
    ap.add_argument("--core-share-override", default=None,
                     help="csv: month,age,share -- replace the internally-derived core-share-by-calendar-month "
                          "table with an external one (e.g. pulled directly from a reference spreadsheet).")
    ap.add_argument("--tail-share-override", default=None,
                     help="csv: age,share -- replace the internally-derived tail-share-by-age table with an "
                          "external one. Extrapolation beyond the max listed age still uses a fitted decay rate "
                          "(clamped <=1.0) derived from this table's own tail.")
    a = ap.parse_args()

    actual = load_raw(a.raw)
    if not actual:
        sys.exit(f"No rows read from {a.raw}")
    spend = load_spend(a.spend)
    spend_schedule = load_spend(a.spend_schedule) if a.spend_schedule else {}
    roas_schedule = load_spend(a.roas_schedule, value_col="roas") if a.roas_schedule else {}
    core_share_override = None
    if a.core_share_override:
        core_share_override = {}
        with open(a.core_share_override, newline='') as f:
            for row in csv.DictReader(f):
                core_share_override[(int(row['month']), int(row['age']))] = float(row['share'])
    tail_share_override = None
    if a.tail_share_override:
        tail_share_override = {}
        with open(a.tail_share_override, newline='') as f:
            for row in csv.DictReader(f):
                tail_share_override[int(row['age'])] = float(row['share'])

    end_key = a.to_cohort or a.cohort
    if not end_key:
        sys.exit("Provide --cohort YYYY-MM (single) or --from-cohort/--to-cohort (range)")

    roas_growth_explicit = a.roas_growth is not None
    first_pass_growth = a.roas_growth if roas_growth_explicit else 0.0

    spend_growth_explicit = a.spend_growth is not None
    a.spend_growth = a.spend_growth if spend_growth_explicit else 0.01
    spend_growth_note = None
    if not spend_growth_explicit and a.assumed_spend is None:
        spend_growth_note = (
            f"Input Spend growth not given -- defaulting to {a.spend_growth:+.2%}/mo MoM off the latest "
            f"actual spend for any future month not covered by --spend-schedule; pass --spend-growth 0 "
            f"for flat carry-forward instead, or --spend-schedule for real monthly figures.")

    grid, flags, anchor, cohort_keys, eff_spend, input_used = build_full_grid(
        actual, spend, a.start, end_key, a.horizon,
        a_assumed_roas=a.assumed_roas, a_assumed_spend=a.assumed_spend,
        roas_growth=first_pass_growth, spend_growth=a.spend_growth,
        spend_schedule=spend_schedule, roas_schedule=roas_schedule,
        core_share_override=core_share_override, tail_share_override=tail_share_override)

    if spend_growth_note:
        print(f"\n{spend_growth_note}")

    derived_growth_note = None
    if not roas_growth_explicit and a.assumed_roas is None:
        derived_rate, used_cohorts = derive_roas_growth(actual, anchor, cohort_keys, flags)
        if used_cohorts:
            derived_growth_note = (
                f"Input ROAS growth not given -- auto-derived {derived_rate:+.3%}/mo from the trailing "
                f"{len(used_cohorts)} reliable cohorts' own recent trend ({used_cohorts[0][0]} to "
                f"{used_cohorts[-1][0]}, anchor {used_cohorts[0][1]:.4f} -> {used_cohorts[-1][1]:.4f}); "
                f"pass --roas-growth 0 to force flat carry-forward instead.")
            a.roas_growth = derived_rate
            grid, flags, anchor, cohort_keys, eff_spend, input_used = build_full_grid(
                actual, spend, a.start, end_key, a.horizon,
                a_assumed_roas=a.assumed_roas, a_assumed_spend=a.assumed_spend,
                roas_growth=derived_rate, spend_growth=a.spend_growth,
                spend_schedule=spend_schedule, roas_schedule=roas_schedule,
                core_share_override=core_share_override, tail_share_override=tail_share_override)
        else:
            a.roas_growth = 0.0
    elif not roas_growth_explicit:
        a.roas_growth = 0.0

    if derived_growth_note:
        print(f"\n{derived_growth_note}")

    report_keys = [a.cohort] if a.cohort else \
        [k for k in cohort_keys if k >= (a.from_cohort or a.start)]

    with open("roas_grid.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["install_month", "age", "return_month", "roas", "recovery", "source",
                    "within_first_year", "crosses_calendar_year"])
        for ck in cohort_keys:
            sp = eff_spend.get(ck)
            for age in range(a.horizon):
                rm = return_month(ck, age)
                roas = grid[ck][age]
                rec = round(roas * sp, 2) if sp else ""
                w.writerow([ck, age, rm, round(roas, 6), rec, flags[ck][age],
                            int(age <= CORE_MAX), int(crosses_calendar_year(ck, rm))])

    any_projected = False
    for ck in report_keys:
        sp = eff_spend.get(ck)
        core_total = anchor[ck]
        if flags[ck][0] == "no_data":
            print(f"\nCohort {ck} -- no actual data and no prior cohort to carry forward from; "
                  f"can't originate a curve here.")
            continue
        if ck in input_used:
            any_projected = True
            in_roas, in_spend = input_used[ck]
            if in_roas is None:
                print(f"\nCohort {ck} -- no actual data and no prior cohort to derive an Input ROAS "
                      f"assumption from; can't project this one.")
                continue
            roas_note = ", overridden by --assumed-roas" if a.assumed_roas is not None else ""
            spend_note = ", overridden by --assumed-spend" if a.assumed_spend is not None else ""
            print(f"\nCohort {ck} -- PROJECTED (no actual data yet; assumed inputs, not a data-grounded number)")
            print(f"  Input ROAS assumed: {in_roas:.4f}  (roas-growth={a.roas_growth:+.2%}/mo{roas_note})")
            if in_spend:
                print(f"  Input Spend assumed: {in_spend:,.0f}  (spend-growth={a.spend_growth:+.2%}/mo{spend_note})")
            else:
                print(f"  Input Spend: unknown -- no prior cohort spend to carry forward, no dollar figures below")
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
        by_month_projected = defaultdict(float)
        missing_spend = set()
        for ck in report_keys:
            sp = eff_spend.get(ck)
            if not sp:
                missing_spend.add(ck)
                continue
            for age in range(a.horizon):
                rm = return_month(ck, age)
                by_month[rm] += grid[ck][age] * sp
                if ck in input_used or flags[ck][age] == "projected":
                    by_month_projected[rm] += grid[ck][age] * sp
        with open("rev_by_month.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["return_month", "revenue", "includes_projected_cohort"])
            for rm in sorted(by_month):
                w.writerow([rm, round(by_month[rm], 2), int(rm in by_month_projected)])
        note = f", skipped {len(missing_spend)} with no spend" if missing_spend else ""
        print(f"\n-> rev_by_month.csv (Recovery $ by calendar month, across "
              f"{len(report_keys)-len(missing_spend)} cohort(s){note})")
        if any_projected:
            print("   NOTE: some months include PROJECTED (assumption-driven) cohorts -- "
                  "see the includes_projected_cohort column and the assumptions printed above.")

    print("\n-> roas_grid.csv (every reported cohort x age cell, with ROAS, Recovery $, and actual/forecast/projected/no_data flag)")


if __name__ == "__main__":
    main()
