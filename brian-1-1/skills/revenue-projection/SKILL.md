---
name: revenue-projection
description: Project Playsimple revenue from spend and existing cohort revenue. Use for "revenue projection/forecast", "project revenue to some future year", "if we spend $X what revenue do we get", cohort LTV/ROAS forecasting, or backcasting a past year to check accuracy. Keeps observed months as actuals and predicts every future return month — for existing cohorts and for future install months out to the horizon (e.g. the next 5 years). Everything (share profile, tail, per-cohort ROAS) is derived live from play_data.monthly_rev_diff each run; nothing is hardcoded.
---

# Revenue Projection (Playsimple cohort LTV model)

Given spend and the revenue cohorts have earned so far, this projects revenue forward by month and year. It keeps observed months as **actuals** and **predicts** everything after the data edge — both the remaining tail of existing cohorts and entirely new **future install months** out to whatever horizon you ask for (next year, next 5 years, to 2035, etc.). Every ingredient — the monetization share curve, the long tail, each cohort's lifetime ROAS — is recomputed from the data on every run, so it self-updates as new data lands.

It answers three shapes of question:
1. **Forecast** — actuals to date + a spend/ROAS assumption -> revenue by month and year.
2. **Scenario** — an explicit future **spend plan** (one row per future install month, optional ROAS) -> the revenue it produces.
3. **Backcast** — rebuild the inputs as-of a past month, project, and compare to what actually happened (accuracy check).

---

## The data model (read this first — it drives everything)

`play_data.monthly_rev_diff` is a cohort grid:

| col | meaning |
|---|---|
| `gid` | game id |
| `cli` | platform (0/1/2) |
| `install_month` | cohort (DATE, first of month) |
| `diff` | months since install (0,1,2,...) |
| `rev` | **incremental** revenue earned in that diff-month (NOT cumulative) |
| `spend` | the cohort's acquisition spend — **repeated identically on every diff row** |

Two facts everything depends on:
- **`rev` is incremental** and lands in calendar month `add_months(install_month, diff)`. Rolling `rev` up by return month reproduces reported monthly revenue exactly.
- **`spend` is repeated per diff row.** True cohort spend = `MAX(spend)` per `(gid,cli,install_month)`. **Never `SUM(spend)` across diff** — it over-counts ~100x.

Portfolio cohort = `SUM(rev)` over gid/cli per (install_month, diff); cohort spend = `SUM(MAX(spend))`. Incremental ROAS at diff *d* = `rev_d / spend`; M12 ROAS = `sum rev_(0..12) / spend`.

---

## Method (all quantities derived live)

1. **Share profile (diff 0..12), keyed by install calendar month.** For every *mature* cohort (all 13 months d=0..12 observed), `share_d = rev_d / M12rev`. The profile for calendar month *m* is the mean of `share_d` across those cohorts, so it captures that (say) Nov cohorts monetize differently from Feb, and sums to 100%. By default it pools cohorts from `<PROFILE_FROM>` onward (a stable-revenue-source cutoff), so early, differently-measured history doesn't distort the curve.
2. **Tail ratios (diff >= 13).** `tail_d = rev_d / M12rev`, meaned over the same cohort set, for each observed tail diff. Beyond the last observed tail diff it decays geometrically at `--tail-yearly-decay` per 12 months. Recovery stops at a per-cohort cap (`--old-cap`, or `--new-cap` for cohorts installed on/after `--new-cap-from`).
3. **Input ROAS per install month** (the cohort's lifetime M12 ROAS):
   - **actual** `M12rev/spend` if all 13 months are observed;
   - **calculated** `= (rev_to_date / spend) / sum share(0..k)` once the cohort has `--calc-min-months` observed months — its ROAS-to-date completed along the seasonal curve;
   - **assumed** (`--assumed-roas` or a `plan.csv` value) for cohorts still younger than that, and for all future install months.
4. **Projection.** For each install cohort x future diff:
   `recovery(d) = input_spend x input_roas x share(cal_month, d)` for d <= 12, else `x tail_d`. Observed months pass through as actuals.
5. **Future install months.** From the data edge to the horizon, each new month gets its spend (plan, or previous month x `--spend-growth`) and ROAS (plan, or previous x `--roas-growth`, or `--assumed-roas`), then the same share+tail projection. This is what extends the forecast years into the future.
6. **Rollup.** Sum recovery by return month -> by year. Report calendar `Rev/Spend` and, for scenarios, the cohort ROAS of each year's spend.

---

## How to run it

Work in a scratch dir (e.g. the outputs folder). All SQL runs against Databricks via the SQL tool.

**Scope.** Default is the whole portfolio. To scope to a game/platform, add the *same* filter (e.g. `AND gid = 8 AND cli = 1`, resolve names via ps-entities) to **every** `monthly_rev_diff` scan below. Keep it identical across all pulls or the profiles won't match the cohorts.

**Data edge.** The table usually already holds the current, partial month. Set `EDGE` to the last **complete** month and add `AND add_months(install_month, diff) <= DATE'<EDGE>'` to every scan. The same knob backcasts — set `EDGE` to any past month and each cohort's observed depth truncates automatically.

### Step 1 — pull the four input CSVs

**`cohorts.csv`** — header `install_month,spend,max_obs_diff,m12_rev_obs`
```sql
WITH coh AS (SELECT install_month, diff, SUM(rev) rev FROM play_data.monthly_rev_diff
             WHERE add_months(install_month,diff) <= DATE'<EDGE>' /*SCOPE*/ GROUP BY 1,2),
sp AS (SELECT install_month, SUM(spend) spend FROM
        (SELECT gid,cli,install_month,MAX(spend) spend FROM play_data.monthly_rev_diff WHERE 1=1 /*SCOPE*/ GROUP BY 1,2,3) GROUP BY 1)
SELECT c.install_month, sp.spend, MAX(c.diff) AS max_obs_diff,
       SUM(CASE WHEN c.diff<=12 THEN c.rev ELSE 0 END) AS m12_rev_obs
FROM coh c JOIN sp ON c.install_month=sp.install_month
GROUP BY c.install_month, sp.spend ORDER BY c.install_month;
```
(`m12_rev_obs` = full M12 revenue for mature cohorts, or revenue-to-date for younger ones — the engine turns the latter into a calculated ROAS.)

**`seasonal.csv`** — header `cal_month,diff,share`
```sql
WITH coh AS (SELECT install_month, diff, SUM(rev) rev FROM play_data.monthly_rev_diff
             WHERE add_months(install_month,diff) <= DATE'<EDGE>' /*SCOPE*/ GROUP BY 1,2),
m12 AS (SELECT install_month, SUM(rev) m12rev, MAX(diff) mx FROM coh WHERE diff<=12 GROUP BY 1)
SELECT month(c.install_month) AS cal_month, c.diff, AVG(c.rev/NULLIF(m.m12rev,0)) AS share
FROM coh c JOIN m12 m ON c.install_month=m.install_month
WHERE c.diff<=12 AND m.mx>=12 AND c.install_month >= DATE'<PROFILE_FROM>'
GROUP BY 1,2 ORDER BY 1,2;
```

**`tail.csv`** — header `diff,tail_share`
```sql
WITH coh AS (SELECT install_month, diff, SUM(rev) rev FROM play_data.monthly_rev_diff
             WHERE add_months(install_month,diff) <= DATE'<EDGE>' /*SCOPE*/ GROUP BY 1,2),
m12 AS (SELECT install_month, SUM(rev) m12rev, MAX(diff) mx FROM coh WHERE diff<=12 GROUP BY 1)
SELECT c.diff, AVG(c.rev/NULLIF(m.m12rev,0)) AS tail_share
FROM coh c JOIN m12 m ON c.install_month=m.install_month
WHERE c.diff >= 13 AND m.mx>=12 AND c.install_month >= DATE'<PROFILE_FROM>'
GROUP BY 1 ORDER BY 1;
```

**`actuals.csv`** — header `return_month,rev`
```sql
SELECT add_months(install_month, diff) AS return_month, SUM(rev) AS rev
FROM play_data.monthly_rev_diff WHERE add_months(install_month,diff) <= DATE'<EDGE>' /*SCOPE*/ GROUP BY 1 ORDER BY 1;
```

Pick `<PROFILE_FROM>` as the point where the revenue source is consistent (a few years of mature cohorts is plenty). The SQL tool returns JSON — for compact rows wrap each query body in `concat_ws('|', collect_list(concat_ws(',', ...)))` and split in Python.

**`trend.csv`** (optional — only for `--blend-recent-trend`, see below) — header `diff,inc_roas`. Median incremental ROAS (`rev_d / spend`) at each diff over the last `N` install cohorts, so young cohorts are projected off recent behaviour rather than the long-run curve:
```sql
WITH sp AS (SELECT install_month, SUM(spend) spend FROM
        (SELECT gid,cli,install_month,MAX(spend) spend FROM play_data.monthly_rev_diff WHERE 1=1 /*SCOPE*/ GROUP BY 1,2,3) GROUP BY 1),
coh AS (SELECT install_month, diff, SUM(rev) rev FROM play_data.monthly_rev_diff
        WHERE add_months(install_month,diff) <= DATE'<EDGE>' /*SCOPE*/ GROUP BY 1,2)
SELECT c.diff, percentile(c.rev/s.spend, 0.5) AS inc_roas
FROM coh c JOIN sp s ON c.install_month=s.install_month
WHERE c.install_month BETWEEN add_months(DATE'<EDGE>', -6) AND DATE'<EDGE>'   -- last ~6 install cohorts
GROUP BY 1 ORDER BY 1;
```

### Step 2 — `plan.csv` (optional: future spend / ROAS)

Header `install_month,spend,roas`; one row per future install month (either column may be blank to fall back). Also overrides the assumed ROAS of an existing young cohort (its `roas` is used only while the cohort has no calculated ROAS yet).
```
install_month,spend,roas
2027-01-01,17000000,1.15
2027-02-01,17000000,
2028-01-01,,1.16
```
Months not in the plan fall back to `--spend-growth` / `--roas-growth` (compounding from the previous month) and `--assumed-roas`.

### Step 3 — write `project_revenue.py` (bundled beside this file; source at the bottom) and run

```bash
# Forecast to 2030, flat spend and a fixed assumed ROAS for future/young cohorts:
python3 project_revenue.py --dir . --horizon-end 2030-12 --assumed-roas 1.10 --spend-growth 0

# Five years out with modest growth:
python3 project_revenue.py --dir . --horizon-end 2031-12 --assumed-roas 1.10 --spend-growth 0.005

# Scenario driven by an explicit plan:
python3 project_revenue.py --dir . --horizon-end 2029-12 --assumed-roas 1.10 --plan plan.csv

# Recency-weighted mode (mirrors hand-built trackers): needs trend.csv
python3 project_revenue.py --dir . --horizon-end 2030-12 --assumed-roas 1.10 --blend-recent-trend --blend-ramp 0.05
```

**Two projection modes.** By default each unobserved diff is `spend x (single M12 ROAS) x seasonal_share(cal_month, d)` — one ROAS number (assumed or calculated) times a long-run pooled seasonal curve. With `--blend-recent-trend` (needs `trend.csv`), the *fraction of spend* recovered at each projected diff instead blends the **recent-cohort trend** (median incremental ROAS of the last ~6 cohorts at that diff) with the **seasonal index** (`this cohort's ROAS x seasonal_share`), shifting `--blend-ramp` of the weight per diff-step away from the recent trend and toward seasonal as the cohort ages — so it leans on very recent behaviour early and the long-run curve once mature. Use this when you need to reconcile with a tracker built that way; the flat mode is the stable default.

Outputs: `projection_by_month.csv` (return_month, projected_rev, actual_rev, is_actual), `projection_by_cohort.csv` (install_month, diff, return_month, recovery), `projection_inputs.csv` (install_month, input_spend, input_roas, source=actual/calculated/assumed/plan/future, projected_m12_recovery), `projection_yearly.csv`, plus a printed year table.

**Backcast** to check accuracy: rebuild the four CSVs with an earlier `<EDGE>`, run to a horizon you already have actuals for, and compare `projection_yearly.csv`'s projected vs actual. Feed the real spend that occurred via `--plan` to isolate curve error from the spend/ROAS assumption.

### Parameters
- `--horizon-end YYYY-MM` — last projected month.
- `--assumed-roas` — M12 ROAS for cohorts too young for a calculated ROAS and for future install months (unless a plan row gives one). Always state it in the answer.
- `--calc-min-months` (default 8) — observed months a cohort needs before its own seasonally-completed ROAS is used.
- `--spend-growth`, `--roas-growth` — month-over-month compounding for future install months (0.01 = +1%/mo).
- `<PROFILE_FROM>` is not a script flag — it's the date you bake into the seasonal/tail SQL (cohort window for the curves).
- `--tail-yearly-decay` (default 0.75) — tail decay per 12 months beyond the last observed tail diff.
- `--blend-recent-trend` — switch to the recency-weighted mode above (requires `trend.csv`); `--blend-ramp` (default 0.05) sets how fast the weight ramps from recent trend to seasonal per diff-step.
- `--old-cap` (90), `--new-cap` (120), `--new-cap-from` (YYYY-MM) — max months-since-install projected per cohort.
- `--plan file.csv`, `--data-edge YYYY-MM` (default = latest install month in cohorts.csv).

---

## Presenting results
Report the yearly table (revenue, spend, Rev/Spend) and **always state the assumptions**: data edge, assumed ROAS, spend/ROAS growth or plan, horizon. Actual months reproduce reported revenue exactly; only post-edge months are modeled, so far-out years swing entirely with the spend/ROAS assumption — never show a far-year total without it. For a visual, hand `projection_by_month.csv` to `game-viz-design`; for a deck, use `ps-brand-report`. **Revenue, spend and retention are out of scope for the BRIAN analyst build (SR-30)** — this is a separate, explicitly revenue-focused tool; use it only when the user asks for a revenue projection/forecast.

## "Why doesn't this match my sheet / tracker?"
Different projection *methods* give different numbers off the same data — that's expected, not a bug. Work it in this order:
1. **Check the observed diffs first.** In `projection_by_cohort.csv`, the actual (already-observed) diffs should match the other model to the decimal. If they do, the data source is fine and the entire gap is projection method — don't go re-pulling data. If they *don't*, then it's scope/edge/source (check the `AND gid/cli` filter, the `<EDGE>`, and that both read the same revenue definition).
2. **Compare the projection formula, not the totals.** Ask for (or extract) the other model's per-diff formula. The common divergence: this skill uses one M12 ROAS x a long-run pooled seasonal curve, whereas hand-built trackers often **blend a recent-cohort trend** early and only trust the long-run curve as a cohort matures. If recent cohorts under- or over-perform the long-run curve, the two M12 estimates split — run `--blend-recent-trend` to reconcile.
3. **Check the ROAS assumption.** A young cohort here projects at `--assumed-roas` (or its calculated ROAS), not its own last-month run-rate; a tracker leaning on recent months will differ. Override per-cohort via `plan.csv`.

**Reading a large/complex Google Sheet to do this comparison:** the Drive tools often can't help — `download_file_content` may fail with *"File too large for export"* and `read_file_content` returns one flattened, un-addressable dump (you can't target a specific tab or cell). Ask the user to **upload the `.xlsx` directly**, then parse the raw OOXML by hand: `unzip` it and read `xl/worksheets/sheetN.xml` + `xl/sharedStrings.xml` with `xml.etree` to get real cell coordinates and formulas. Note `openpyxl.load_workbook()` can throw on workbooks with pivot caches (e.g. `Nested.from_tree() missing 1 required positional argument`) — bypass it and parse the XML directly.

## Known limits & pitfalls
- **`SUM(spend)` across diff is wrong** (~100x). Always `MAX(spend)` per cohort — the SQL above does.
- **Method differences are not errors.** Flat `ROAS x pooled seasonal` won't tie out to a recency-weighted or blended tracker; reconcile by matching methodology (`--blend-recent-trend`), not by re-running the same method harder.
- **Young cohorts project at the assumed ROAS**, not their own actuals, until they reach `--calc-min-months`. If one is clearly off-trend, note it or override via `plan.csv`.
- **Far-year totals are only as good as the spend/ROAS plan.** They move entirely with `--spend-growth` / `--roas-growth` / `--plan`.
- **Spend-driven projection ignores organic/unfunded revenue**: cohorts with `spend=0` contribute their actuals but no future.
- **Caps** (`--old-cap` / `--new-cap`) bound each cohort's tail length; the tail beyond the last observed diff is a geometric decay, not measured data.
- The engine recomputes the profile, tail and per-cohort ROAS every run, so results move slightly month to month as cohorts mature — that's expected.

---

## `project_revenue.py` (write this file verbatim if it is not bundled, then run)

```python
#!/usr/bin/env python3
"""Cohort revenue projection engine for play_data.monthly_rev_diff.

Projects portfolio (or scoped) revenue forward: keeps observed months as actuals and
predicts every future return month, for every install cohort AND for future install
months out to the horizon (e.g. the next 5 years). Nothing is hardcoded — the share
profile, tail ratios and per-cohort ROAS are all derived live from the input CSVs each run.

Reads (from --dir):
  cohorts.csv   install_month,spend,max_obs_diff,m12_rev_obs   (one row per observed install month)
  seasonal.csv  cal_month,diff,share                           (mean incremental share of M12 by install calendar month, diff 0..12)
  tail.csv      diff,tail_share                                (mean incremental share of M12 at diff 13..60)
  actuals.csv   return_month,rev                               (reported revenue by calendar month; optional)
  plan.csv      install_month,spend,roas                       (optional future spend / ROAS, and ROAS overrides)
Writes projection_by_month.csv, projection_by_cohort.csv, projection_inputs.csv, projection_yearly.csv.

Per install cohort, per months-since-install d, for return months after the data edge:
  recovery(d) = input_spend * input_roas * share(install_cal_month, d)   for d <= 12
  recovery(d) = input_spend * input_roas * tail_ratio(d)                 for 13 <= d <= cap
  cap = 120 months for cohorts installed in/after --new-cap-from (default 2024-01), else --old-cap (90).
  input_roas = m12_rev_obs / spend                          if the cohort has all 13 months (d 0..12) observed
             = (rev_to_date / spend) / sum(share(0..k))      if it has >= --calc-min-months observed months
             = plan roas, else --assumed-roas                otherwise, and for future install months
Observed months always pass through unchanged.
"""

import argparse, csv, os

def parse_ym(s):
    y, m = s.split("-")[:2]; return int(y), int(m)
def ym_idx(y, m): return y * 12 + (m - 1)
def idx_ym(i): return (i // 12, i % 12 + 1)
def key(i): y, m = idx_ym(i); return f"{y:04d}-{m:02d}"
def load(d, name):
    with open(os.path.join(d, name), newline="") as f: return list(csv.DictReader(f))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--horizon-end", default="2030-12")
    ap.add_argument("--assumed-roas", type=float, default=None,
                    help="Assumed M12 ROAS for cohorts too young to have a calculated ROAS and for future install months, unless a plan.csv row gives one.")
    ap.add_argument("--calc-min-months", type=int, default=8,
                    help="Observed months a cohort needs before its own seasonally-completed ROAS is used instead of --assumed-roas.")
    ap.add_argument("--spend-growth", type=float, default=0.0, help="Month-over-month spend growth for future install months not set in plan.csv (0.01 = +1%/mo, compounding).")
    ap.add_argument("--roas-growth", type=float, default=0.0, help="Month-over-month ROAS growth for future install months not set in plan.csv (compounding).")
    ap.add_argument("--tail-yearly-decay", type=float, default=0.75, help="Tail ratio decays by this factor per 12 months beyond the last observed tail diff.")
    ap.add_argument("--old-cap", type=int, default=90, help="Max months-since-install projected for older cohorts.")
    ap.add_argument("--new-cap", type=int, default=120, help="Max months-since-install projected for newer cohorts.")
    ap.add_argument("--new-cap-from", default="2024-01", help="Install month (YYYY-MM) from which --new-cap applies instead of --old-cap.")
    ap.add_argument("--blend-recent-trend", action="store_true",
                    help="Blend a recent-cohort trend into each projected diff instead of a single flat ROAS x seasonal share. "
                         "Mirrors hand-built trackers that lean on the last few cohorts early and the long-run seasonal curve as a cohort ages. Requires trend.csv.")
    ap.add_argument("--blend-ramp", type=float, default=0.05,
                    help="Per-diff-step weight shifted from the recent trend toward the seasonal index under --blend-recent-trend (0.05 = 5 pct/diff).")
    ap.add_argument("--plan", default="plan.csv")
    ap.add_argument("--data-edge", default=None, help="YYYY-MM of the last complete actual month; default = latest install_month in cohorts.csv.")
    a = ap.parse_args(); D = a.dir

    SEAS = {}
    for r in load(D, "seasonal.csv"):
        SEAS.setdefault(int(r["cal_month"]), {})[int(r["diff"])] = float(r["share"])
    TAIL = {int(r["diff"]): float(r["tail_share"]) for r in load(D, "tail.csv") if int(r["diff"]) >= 13}
    TMAX = max(TAIL); g = a.tail_yearly_decay ** (1 / 12)
    def tail_ratio(d): return TAIL[d] if d <= TMAX else TAIL[TMAX] * g ** (d - TMAX)  # decay past last observed tail diff
    # Optional recent-cohort trend: incremental ROAS (rev_d/spend) by diff, pooled over the last N cohorts.
    TREND = {}
    if a.blend_recent_trend:
        tp = os.path.join(D, "trend.csv")
        if not os.path.exists(tp): raise SystemExit("--blend-recent-trend needs trend.csv (diff,inc_roas) — see the skill's Step 1 optional pull.")
        TREND = {int(r["diff"]): float(r["inc_roas"]) for r in load(D, "trend.csv")}
    COH = {r["install_month"][:7]: (float(r["spend"]), int(r["max_obs_diff"]), float(r["m12_rev_obs"])) for r in load(D, "cohorts.csv")}
    ACTUAL = {r["return_month"][:7]: float(r["rev"]) for r in load(D, "actuals.csv")} if os.path.exists(os.path.join(D, "actuals.csv")) else {}
    PLAN = {}
    pth = a.plan if os.path.isabs(a.plan) else os.path.join(D, a.plan)
    if os.path.exists(pth):
        with open(pth, newline="") as f:
          for r in csv.DictReader(f):
            PLAN[r["install_month"][:7]] = (float(r["spend"]) if r.get("spend") not in (None, "") else None,
                                              float(r["roas"]) if r.get("roas") not in (None, "") else None)

    LAST = a.data_edge or max(COH)
    LY, LM = parse_ym(LAST); LAST_IDX = ym_idx(LY, LM)
    HY, HM = parse_ym(a.horizon_end); HORIZON = ym_idx(HY, HM)
    NCY, NCM = parse_ym(a.new_cap_from); NEWCAP_IDX = ym_idx(NCY, NCM)

    # ---- Input Spend / Input ROAS per install month ----
    inputs = {}  # install -> (spend, roas, source)
    for ins, (sp, k, m12obs) in COH.items():
        y, m = parse_ym(ins)
        p = PLAN.get(ins, (None, None))
        if k >= 12:
            roas, src = (m12obs / sp if sp else 0.0), "actual"
        elif k + 1 >= a.calc_min_months and sp > 0:
            roas, src = (m12obs / sp) / sum(SEAS[m][d] for d in range(k + 1)), "calculated"
        elif p[1] is not None:
            roas, src = p[1], "plan"
        else:
            if a.assumed_roas is None: raise SystemExit(f"{ins}: no Calculated ROAS yet ({k+1} obs months) — give --assumed-roas or a plan.csv roas")
            roas, src = a.assumed_roas, "assumed"
        inputs[ins] = (sp, roas, src)
    # future install months: plan value if given, else carry the previous month forward (x growth)
    i = LAST_IDX + 1; prev_sp = inputs[LAST][0]
    prev_roas = a.assumed_roas if a.assumed_roas is not None else inputs[LAST][1]
    while i <= HORIZON:
        ky = key(i); p = PLAN.get(ky, (None, None))
        sp = p[0] if p[0] is not None else prev_sp * (1 + a.spend_growth)
        roas = p[1] if p[1] is not None else prev_roas * (1 + a.roas_growth)
        inputs[ky] = (sp, roas, "plan" if p != (None, None) else "future"); prev_sp, prev_roas = sp, roas; i += 1

    # ---- Projections: recovery per install x diff ----
    proj = dict(ACTUAL); bycoh = []
    for ins, (sp, roas, src) in inputs.items():
        y, m = parse_ym(ins); ii = ym_idx(y, m); cap = a.new_cap if ii >= NEWCAP_IDX else a.old_cap
        m12 = sp * roas
        k = COH[ins][1] if ins in COH else -1
        for d in range(k + 1, cap + 1):
            ri = ii + d
            if ri <= LAST_IDX or ri > HORIZON: continue
            seasonal_frac = (SEAS[m][d] if d <= 12 else tail_ratio(d))   # fraction of M12 revenue at this diff
            if a.blend_recent_trend and d in TREND:
                # recovery as a fraction of spend: recent-trend inc-ROAS vs seasonal-index (this cohort's ROAS x share),
                # weight ramping from trend toward seasonal by --blend-ramp per diff-step.
                w_seas = min(1.0, max(0.0, a.blend_ramp * (d - 1)))
                frac_of_spend = (1 - w_seas) * TREND[d] + w_seas * (roas * seasonal_frac)
                rec = sp * frac_of_spend
            else:
                rec = m12 * seasonal_frac
            proj[key(ri)] = proj.get(key(ri), 0.0) + rec
            bycoh.append((ins, d, key(ri), round(rec, 2)))

    def yr(dd):
        o = {}
        for k2, v in dd.items(): o[int(k2[:4])] = o.get(int(k2[:4]), 0.0) + v
        return o
    ysp = {}
    for ins, (sp, roas, src) in inputs.items(): ysp[int(ins[:4])] = ysp.get(int(ins[:4]), 0.0) + sp
    pr = yr(proj); ar = yr(ACTUAL)

    with open(os.path.join(D, "projection_by_month.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["return_month", "projected_rev", "actual_rev", "is_actual"])
        for k2 in sorted(proj): w.writerow([k2, round(proj[k2], 2), round(ACTUAL.get(k2, 0), 2), int(k2 <= LAST)])
    with open(os.path.join(D, "projection_by_cohort.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["install_month", "diff", "return_month", "recovery"]); w.writerows(bycoh)
    with open(os.path.join(D, "projection_inputs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["install_month", "input_spend", "input_roas", "source", "projected_m12_recovery"])
        for ins in sorted(inputs): sp, roas, src = inputs[ins]; w.writerow([ins, round(sp, 2), round(roas, 4), src, round(sp * roas, 2)])
    with open(os.path.join(D, "projection_yearly.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["year", "projected_rev", "spend", "roas", "actual_rev"])
        for y in sorted(pr):
            s = ysp.get(y, 0); w.writerow([y, round(pr[y], 2), round(s, 2), round(pr[y] / s, 4) if s else "", round(ar.get(y, 0), 2)])

    print(f"Data edge: {LAST} | horizon: {a.horizon_end} | assumed ROAS: {a.assumed_roas} | calc-min-months: {a.calc_min_months} | spend growth/mo: {a.spend_growth} | roas growth/mo: {a.roas_growth}")
    print(f"{'YEAR':6}{'Rev$M':>10}{'Spend$M':>10}{'Rev/Spend':>10}")
    for y in sorted(pr):
        s = ysp.get(y, 0); print(f"{y:<6}{pr[y]/1e6:>10.1f}{s/1e6:>10.1f}{(pr[y]/s if s else 0):>10.2f}")
    print("-> projection_by_month.csv, projection_by_cohort.csv, projection_inputs.csv, projection_yearly.csv")

if __name__ == "__main__": main()
```
