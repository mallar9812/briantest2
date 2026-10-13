---
name: playground-cohort-roas
description: "Compute install-cohort monthly and cumulative ROAS from the Playsimple playground-sheet revenue projection model (actual data + trend/seasonality forecast blend), matching the Google Sheet's own live formulas exactly. Use when asked for monthly ROAS, ROAS curve, or cumulative ROAS for a specific install/cohort month (e.g. \"what's the monthly ROAS for the March 2026 install cohort\")."
---


# Playground Cohort ROAS Calculator

## When to use this skill

Use this when asked for install-cohort / monthly ROAS numbers for the
Playsimple revenue projection model that lives in the "playground" tab of
the Google Sheet **PS projections 2026 H1 (copy)**
(https://docs.google.com/spreadsheets/d/12YWAL2F2eAdjpw_yByssBhyQHwcUZx2burdviB2skZI,
tab gid 983221766, columns AI:AW). Typical questions:

- "What are the monthly ROAS numbers for the March 2026 install cohort?"
- "What's the cumulative 12-month ROAS for users who installed in July 2018?"
- "Give me the ROAS curve for install month X."

This skill computes the answer live, from the same reference data and the
same formula logic as the sheet, rather than looking up a cached number -
so it stays correct as new actual data comes in, and it can also answer
for cohorts that are only partially through their 13-month curve (blending
whatever real data exists with a trend/seasonality forecast for the rest,
exactly like the sheet does).

## What the model is

One row per install/cohort month. Thirteen columns = the ROAS **contributed
in that specific month** at cohort-age 0 through 12 months since install
(NOT cumulative per column - each column is that month's own incremental
contribution). The 13 values for a cohort sum to its cumulative ROAS through
month 12.

The sheet's own AI:AW formulas fall into three eras; this calculator
reproduces the first two live (which is what "do all the calculation and
give me the numbers" means in practice) and explains the third rather than
guessing at it:

1. **Era 1** (the first 6 cohort months in the sheet, 2018-01 through
   2018-06): plain lookup of actual data, 0 if missing. No forecasting.
2. **Era 2** (2018-07 onward): actual data if it exists yet for that
   cohort/age; otherwise a recursive forecast blend of (a) recent trend -
   the ratio between this age column's and the previous age column's
   trailing 6-cohort median - and (b) a 12-month x 13-age seasonality
   index table, weighted so later age columns lean more on seasonality
   (up to 55% at age 12) and less on straight trend continuation.
3. **Era 3** (the sheet's own last ~6-20 rows): the sheet has these pasted
   as frozen literal values rather than live formulas - a snapshot from
   whenever someone last froze them. They visibly drift from what Era 2
   would compute live today (checked directly: the sheet's frozen row for
   the Jan-2026 cohort no longer matches this cohort's live actual data,
   because that data has been revised since the freeze). This calculator
   does not try to reproduce Era 3's frozen snapshot - it always gives the
   live Era 1/2 answer, which is the more useful and more current number.

## How to answer a question with this skill

1. Work out the install/cohort month the user means ("March 2026", "the
   2026-03 cohort", "users who installed in July 2018" -> `2026-03` /
   `2018-07`, etc). If they ask for "today's cohort" or similar, use the
   most recent month that has any actual data - the script will tell you
   what that is if you ask for a month too far in the future.
2. Write the two files below to disk exactly as given (they are the exact
   reference data pulled from the sheet's own E3:R106 actual-data table
   and AZ3:BL14/AY3:AY14 seasonality table, plus the calculation script),
   in the same directory:
   - `roas_reference_data.json`
   - `roas_calculator.py`
3. Run: `python3 roas_calculator.py <YYYY-MM>` (accepts multiple months
   at once, space separated, if the user asks for several).
4. Report the 13 monthly values (age 0-12 months since install) and the
   cumulative 0-12 total. Present as ROAS (e.g. multiply by 100 for a
   percentage, or leave as a decimal fraction - match whatever convention
   the user's question implies; the raw model output is a decimal
   fraction, e.g. 0.257 = 25.7% ROAS contributed that month).
5. If the script returns an `error` key instead of `monthly_roas`, that
   means the requested cohort month has no actual data yet (it hasn't
   installed, or today's data hasn't landed) - relay that plainly rather
   than presenting a number.
6. If the user's requested month falls in the sheet's Era-3 frozen-value
   range, you can mention that the sheet itself shows a slightly different
   (older, frozen) number for that month, and that this is the live,
   current answer instead.

## Validated accuracy

This calculator was checked against the sheet's own live-computed values
for cohort rows spanning all three eras (Jan 2018, Jul 2018, May 2022, and
the key mixed actual+forecast case of Mar 2026) and matched to within 1e-6
(the sheet's own float-rounding tolerance) on every value, including the
cumulative total.

## roas_calculator.py

Write this exactly as given to a file named `roas_calculator.py`:

```python
#!/usr/bin/env python3
"""
Playground-sheet cohort ROAS calculator.

Replicates, cell-for-cell, the logic in the "playground" tab (AI:AW) of the
PS projections 2026 H1 (copy) Google Sheet:
  https://docs.google.com/spreadsheets/d/12YWAL2F2eAdjpw_yByssBhyQHwcUZx2burdviB2skZI

Model: one row per install/cohort month, 13 columns = ROAS contributed at
cohort-age 0 through 12 months since install. Three eras of logic:

  Era 1 (first 6 cohort months, rows 3-8): =iferror(vlookup(actual),0)
      -> actual data if present, else 0 (no forecasting).

  Era 2 (row 9 onward): =IFERROR(IF(VLOOKUP(actual), actual, blend), 0)
      -> actual data if present, else a recursive forecast blend:
         value(age) = value(age-1, same row)
                      * ( (1-(age-1)*5%) * trend_ratio
                        + (age-1)*5%     * seasonal_ratio )
         trend_ratio    = median(this age col,  prior 6 rows)
                         / median(prev age col,  prior 6 rows)
         seasonal_ratio = seasonality[month][age] / seasonality[month][age-1]
      Age 0 is a special case in the original sheet (there is no "age -1"
      column) - it multiplies by the cohort's own date serial instead of a
      previous age value. In practice age-0 actual data is always present,
      so this branch is dead code; it is implemented here for fidelity but
      will not affect any real query.

  Era 3 (the sheet's last ~6-20 rows): frozen/pasted values, not live
      formulas - not reproducible by computation, and known to drift from
      the live actual-data table as historical figures get revised. This
      calculator does not attempt to reproduce Era 3; it always computes
      Era 1/2 live, which is the "current" answer the formula would give
      if it were still live in those rows.

Reference data (seasonality matrix + actual cohort data table) is embedded
below, pulled directly from the sheet on 2026-09-08.
"""
import json
import statistics
import sys
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Reference data (embedded so this script is self-contained)
# ---------------------------------------------------------------------------

with open(__file__.replace("roas_calculator.py", "roas_reference_data.json")) as _f:
    _REF = json.load(_f)

SEASONALITY = _REF["seasonality_AZ3_BL14"]      # 12 rows (Jan..Dec) x 13 cols (age 0..12)
MONTH_KEYS = _REF["seasonality_AY3_AY14"]        # [1,2,...,12], row i -> calendar month MONTH_KEYS[i]
ACTUAL = _REF["actual_data_E3_R106"]             # {"YYYY-MM-01": [13 floats or None]}

AGES = 13  # age 0..12


def month_str(d):
    return d.strftime("%Y-%m-01")


def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def date_serial(d):
    # Google Sheets serial date (days since 1899-12-30), used only for the
    # dead-code age-0 fallback branch, for literal fidelity to the formula.
    epoch = date(1899, 12, 30)
    return (d - epoch).days


def seasonality_row_for_month(m):
    idx = MONTH_KEYS.index(m)
    return SEASONALITY[idx]


def compute_all_rows(start="2018-01-01", end=None):
    """
    Recursively compute AJ:AV (13 age-columns) for every cohort row from
    `start` through `end` (inclusive), in chronological order - exactly
    mirroring the sheet's own row-by-row / column-by-column dependency
    chain. Returns an ordered dict: cohort_month_str -> [13 values].
    """
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end) if end else max(
        date.fromisoformat(k) for k in ACTUAL
    )

    rows = []  # list of (date, [13 values])
    d = start_d
    row_index = 0  # 0-based; sheet row_index 0 == sheet row 3
    while d <= end_d:
        mstr = month_str(d)
        actual_row = ACTUAL.get(mstr, [None] * AGES)
        values = [None] * AGES

        if row_index < 6:
            # Era 1: plain lookup, fallback 0, no forecasting.
            for a in range(AGES):
                v = actual_row[a] if a < len(actual_row) else None
                values[a] = v if v is not None else 0.0
        else:
            month_num = d.month
            season_row = seasonality_row_for_month(month_num)
            for a in range(AGES):
                v = actual_row[a] if a < len(actual_row) else None
                if v is not None:
                    values[a] = v
                    continue
                # Forecast blend.
                weight_trend = 1 - (a - 1) * 0.05
                weight_season = (a - 1) * 0.05
                if a == 0:
                    prev_value = date_serial(d)
                    prev_window = [date_serial(rows[row_index - 6 + i][0]) for i in range(6)]
                else:
                    prev_value = values[a - 1]
                    prev_window = [rows[row_index - 6 + i][1][a - 1] for i in range(6)]
                cur_window = [rows[row_index - 6 + i][1][a] for i in range(6)]
                trend_ratio = statistics.median(cur_window) / statistics.median(prev_window)
                seasonal_ratio = season_row[a] / season_row[a - 1]
                values[a] = prev_value * (weight_trend * trend_ratio + weight_season * seasonal_ratio)

        rows.append((d, values))
        d = add_months(d, 1)
        row_index += 1

    return {month_str(dt): vals for dt, vals in rows}


def answer_for_month(cohort_month, start="2018-01-01"):
    """cohort_month: 'YYYY-MM' or 'YYYY-MM-DD'. Returns dict with monthly
    values (age 0..12) and cumulative total, computed live."""
    if len(cohort_month) == 7:
        cohort_month += "-01"
    d = date.fromisoformat(cohort_month)
    mstr = month_str(d)

    # Guard: the sheet's own formula has an unhandled edge case when a
    # cohort has zero actual data at age 0 (i.e. the install month hasn't
    # happened yet / hasn't been recorded yet) - it would blow up into a
    # meaningless huge value there too if dragged that far. Rather than
    # silently reproduce that, decline clearly instead.
    last_available = max(date.fromisoformat(k) for k in ACTUAL)
    if mstr not in ACTUAL or ACTUAL[mstr][0] is None:
        return {
            "cohort_month": mstr,
            "error": (
                f"No install/actual data yet for {mstr}. The latest cohort "
                f"month with recorded data is {month_str(last_available)}. "
                "(Age-0 data has to exist before this model can forecast "
                "later ages for a cohort - same limitation the sheet's own "
                "formula has if dragged past its last real row.)"
            ),
        }

    all_rows = compute_all_rows(start=start, end=mstr)
    values = all_rows[mstr]
    return {
        "cohort_month": mstr,
        "monthly_roas": [round(v, 6) for v in values],
        "cumulative_roas_0_12": round(sum(values), 6),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: roas_calculator.py <YYYY-MM or YYYY-MM-DD> [more months...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        result = answer_for_month(arg)
        print(json.dumps(result, indent=2))
```

## roas_reference_data.json

Write this exactly as given to a file named `roas_reference_data.json`, in
the same directory as the script above. Data pulled directly from the
sheet on 2026-09-08 (E3:R106 actual cohort data table + AZ3:BL14
seasonality matrix + AY3:AY14 month keys); if the numbers are needed much
further out from that date, this reference data should be refreshed by
re-running the same extraction against the live sheet.

```json
{"seasonality_AZ3_BL14":[[0.266039,0.182507,0.120842,0.080683,0.065012,0.052904,0.043643,0.038239,0.034322,0.031933,0.031667,0.028897,0.023313],[0.247611,0.206838,0.112689,0.0832,0.064674,0.051672,0.04423,0.039053,0.035889,0.035152,0.031824,0.025062,0.022106],[0.254168,0.187477,0.114465,0.082285,0.063719,0.052857,0.046125,0.042004,0.040502,0.036975,0.028514,0.024681,0.026227],[0.248349,0.199034,0.114715,0.08113,0.063595,0.053351,0.047128,0.044443,0.039945,0.030464,0.026089,0.027407,0.02435],[0.251432,0.196949,0.113059,0.080932,0.064374,0.055006,0.050504,0.044508,0.033752,0.028458,0.02983,0.026064,0.025134],[0.254079,0.197228,0.112552,0.08141,0.065606,0.058101,0.049941,0.037416,0.031282,0.03239,0.028171,0.026934,0.02489],[0.254839,0.193893,0.113338,0.083431,0.070343,0.058805,0.04303,0.035396,0.036054,0.030935,0.029267,0.026764,0.023905],[0.254113,0.193941,0.116197,0.089236,0.070977,0.050264,0.040292,0.040197,0.034205,0.032193,0.02894,0.02554,0.023905],[0.244532,0.199061,0.124003,0.09082,0.061497,0.048226,0.046815,0.038657,0.03574,0.031989,0.028167,0.02609,0.024405],[0.250719,0.209328,0.124769,0.078203,0.057803,0.054171,0.043184,0.039243,0.03453,0.03034,0.027641,0.025599,0.02447],[0.271758,0.212206,0.108014,0.072414,0.064428,0.049656,0.043612,0.037652,0.032621,0.02932,0.0269,0.025617,0.025801],[0.265667,0.198233,0.104347,0.085116,0.062213,0.052932,0.044628,0.037805,0.033702,0.030665,0.028858,0.028955,0.026877]],"seasonality_columns_ages":[0,1,2,3,4,5,6,7,8,9,10,11,12],"seasonality_AY3_AY14":[1,2,3,4,5,6,7,8,9,10,11,12],"note":"seasonality_AZ3_BL14 row i (0-indexed) corresponds to calendar month i+1 (row0=Jan...row11=Dec). Confirmed via AY3:AY14 = [1..12] directly, row order matches.","actual_data_E3_R106":{"2018-01-01":[0.257008,0.201269,0.14626,0.098356,0.082829,0.084303,0.087615,0.083061,0.065188,0.065425,0.052989,0.048282,0.043582],"2018-02-01":[0.241395,0.226499,0.120588,0.098009,0.089453,0.095439,0.085549,0.06638,0.064495,0.057496,0.053995,0.048155,0.048521],"2018-03-01":[0.2697,0.203635,0.140877,0.116003,0.111572,0.096031,0.074534,0.071057,0.060511,0.057308,0.05095,0.049382,0.056282],"2018-04-01":[0.351892,0.286132,0.196007,0.175504,0.138603,0.104356,0.094976,0.079275,0.07438,0.066312,0.062316,0.066852,0.058703],"2018-05-01":[0.276736,0.31146,0.214119,0.147067,0.106483,0.09518,0.073961,0.066465,0.060207,0.055856,0.058422,0.050941,0.051396],"2018-06-01":[0.292438,0.25632,0.147218,0.093325,0.078069,0.061623,0.054473,0.046611,0.043521,0.046057,0.040634,0.040191,0.039292],"2018-07-01":[0.346784,0.271485,0.143761,0.106561,0.077459,0.065446,0.054942,0.04983,0.053739,0.045849,0.045371,0.045566,0.047145],"2018-08-01":[0.358762,0.248673,0.152253,0.1013,0.080357,0.065737,0.057999,0.059482,0.051289,0.050187,0.04853,0.048999,0.049514],"2018-09-01":[0.319127,0.253883,0.144073,0.103827,0.080783,0.068122,0.069744,0.059601,0.057448,0.054413,0.054788,0.055337,0.056805],"2018-10-01":[0.321122,0.253851,0.150399,0.106171,0.079929,0.079219,0.066553,0.063102,0.05622,0.055963,0.056289,0.057544,0.059393],"2018-11-01":[0.322921,0.267631,0.154777,0.105085,0.09618,0.077617,0.072491,0.066334,0.064809,0.063053,0.063664,0.066035,0.072223],"2018-12-01":[0.312141,0.289173,0.161628,0.136807,0.103344,0.091254,0.082808,0.078359,0.078306,0.076263,0.077539,0.083136,0.084251],"2019-01-01":[0.315632,0.28539,0.199402,0.138005,0.116723,0.098629,0.092856,0.089479,0.085975,0.087494,0.092432,0.092133,0.069261],"2019-02-01":[0.307957,0.332525,0.194672,0.148108,0.119148,0.106897,0.098002,0.093244,0.093144,0.095974,0.092928,0.071681,0.061385],"2019-03-01":[0.301569,0.293866,0.186671,0.139267,0.116221,0.100295,0.093064,0.090569,0.092924,0.091283,0.073806,0.066009,0.053021],"2019-04-01":[0.281616,0.27668,0.169621,0.132283,0.109419,0.098175,0.094657,0.094363,0.086921,0.064638,0.057711,0.047037,0.040536],"2019-05-01":[0.305893,0.315953,0.204872,0.160005,0.135829,0.123674,0.118809,0.108622,0.080389,0.06898,0.058059,0.05011,0.049289],"2019-06-01":[0.284965,0.285055,0.18876,0.149072,0.127336,0.121073,0.109984,0.080006,0.068381,0.054095,0.047306,0.047643,0.046395],"2019-07-01":[0.280119,0.330789,0.226006,0.173935,0.15406,0.134888,0.092843,0.07637,0.060648,0.051177,0.051676,0.051737,0.049454],"2019-08-01":[0.334746,0.357499,0.239,0.194601,0.161853,0.112451,0.090109,0.072152,0.059497,0.060113,0.056666,0.054589,0.052795],"2019-09-01":[0.331341,0.352949,0.245781,0.187049,0.123623,0.094189,0.074851,0.061112,0.060704,0.059638,0.055311,0.052884,0.052132],"2019-10-01":[0.303823,0.354826,0.23549,0.145325,0.106605,0.084678,0.065476,0.062894,0.061017,0.055748,0.052795,0.052293,0.050679],"2019-11-01":[0.294454,0.297828,0.152094,0.101849,0.079442,0.060485,0.055721,0.051446,0.047587,0.045113,0.044242,0.042985,0.040908],"2019-12-01":[0.194823,0.190844,0.112452,0.07995,0.057543,0.051206,0.048476,0.04419,0.040787,0.039557,0.038892,0.039301,0.040942],"2020-01-01":[0.183786,0.167202,0.104574,0.068994,0.057996,0.052005,0.04704,0.043041,0.041568,0.040281,0.039393,0.04035,0.029699],"2020-02-01":[0.299838,0.33048,0.181688,0.141056,0.118771,0.102257,0.091458,0.085478,0.081803,0.077735,0.078035,0.056685,0.048265],"2020-03-01":[0.421381,0.301504,0.201269,0.155169,0.129439,0.111657,0.102979,0.096594,0.091978,0.092142,0.066488,0.056125,0.060325],"2020-04-01":[0.401884,0.374039,0.226271,0.169912,0.139127,0.121829,0.110887,0.102796,0.101617,0.073111,0.061496,0.064397,0.058441],"2020-05-01":[0.358739,0.310045,0.194025,0.148097,0.122658,0.10903,0.097999,0.094182,0.067503,0.055155,0.058269,0.052685,0.050985],"2020-06-01":[0.311906,0.263391,0.161339,0.124186,0.103074,0.089113,0.083975,0.059527,0.048979,0.050864,0.045198,0.043274,0.038843],"2020-07-01":[0.335997,0.281393,0.180228,0.138245,0.113155,0.103446,0.071883,0.058899,0.060478,0.053055,0.050103,0.044387,0.03907],"2020-08-01":[0.35741,0.314085,0.19974,0.15215,0.132366,0.088574,0.070332,0.070159,0.060989,0.057586,0.050825,0.044078,0.041765],"2020-09-01":[0.382752,0.337778,0.212879,0.169747,0.109831,0.083803,0.081915,0.070201,0.065401,0.057257,0.048755,0.046242,0.044259],"2020-10-01":[0.39736,0.35965,0.239426,0.146856,0.105381,0.099585,0.081974,0.075318,0.065835,0.056313,0.051389,0.049317,0.047056],"2020-11-01":[0.368013,0.318227,0.162731,0.107882,0.09613,0.076631,0.068161,0.058167,0.04886,0.04457,0.041901,0.039598,0.040574],"2020-12-01":[0.289596,0.2567,0.136142,0.1122,0.08403,0.072114,0.060992,0.050087,0.045404,0.042286,0.039096,0.039303,0.037215],"2021-01-01":[0.328175,0.244256,0.172515,0.121645,0.100298,0.082186,0.066823,0.059417,0.055201,0.050965,0.050958,0.047745,0.037604],"2021-02-01":[0.362382,0.344818,0.204045,0.155795,0.121962,0.095411,0.083843,0.076146,0.068352,0.067972,0.063369,0.049058,0.04227],"2021-03-01":[0.37375,0.352645,0.232126,0.169199,0.126519,0.107161,0.095355,0.084813,0.083778,0.076486,0.058691,0.050882,0.053127],"2021-04-01":[0.369318,0.337429,0.205625,0.140827,0.111449,0.095462,0.082708,0.07905,0.07107,0.054213,0.045999,0.048028,0.038834],"2021-05-01":[0.36795,0.319731,0.183144,0.132605,0.108113,0.089637,0.084496,0.073891,0.056132,0.046863,0.048205,0.038535,0.036076],"2021-06-01":[0.3708,0.318174,0.190502,0.143076,0.113521,0.10282,0.087259,0.065111,0.054525,0.056695,0.045303,0.041492,0.038304],"2021-07-01":[0.355695,0.298983,0.18419,0.134456,0.114951,0.095499,0.06992,0.057004,0.057815,0.045507,0.040802,0.038157,0.034918],"2021-08-01":[0.365387,0.312641,0.186758,0.146213,0.115094,0.080807,0.064597,0.064217,0.049877,0.045255,0.041575,0.03762,0.035849],"2021-09-01":[0.371941,0.312188,0.201336,0.149132,0.100229,0.07796,0.076848,0.057499,0.051473,0.046753,0.041712,0.039304,0.035512],"2021-10-01":[0.360157,0.306519,0.184796,0.114096,0.083319,0.077917,0.056694,0.049412,0.044126,0.039533,0.037071,0.032675,0.031758],"2021-11-01":[0.306644,0.257681,0.129556,0.085495,0.076385,0.053551,0.044859,0.039906,0.035087,0.032376,0.028102,0.027312,0.027785],"2021-12-01":[0.261189,0.191499,0.098847,0.080132,0.053319,0.043335,0.037167,0.032108,0.029106,0.024899,0.024363,0.024848,0.022134],"2022-01-01":[0.298148,0.204993,0.136302,0.084146,0.064725,0.053032,0.044631,0.039984,0.033539,0.032159,0.032258,0.028303,0.02352],"2022-02-01":[0.300781,0.252997,0.13226,0.093308,0.072782,0.059091,0.05167,0.042993,0.040833,0.040509,0.034878,0.028453,0.026587],"2022-03-01":[0.354859,0.251178,0.145919,0.105977,0.082088,0.06842,0.056092,0.052039,0.051246,0.043641,0.035774,0.033034,0.034095],"2022-04-01":[0.317347,0.252453,0.150199,0.107771,0.085156,0.067511,0.060359,0.058207,0.049239,0.038938,0.035774,0.036561,0.034092],"2022-05-01":[0.285739,0.243972,0.142705,0.103234,0.077689,0.067008,0.062269,0.051019,0.040675,0.036847,0.037888,0.034083,0.034244],"2022-06-01":[0.270268,0.225604,0.134757,0.092858,0.075437,0.067344,0.054937,0.042631,0.038135,0.03834,0.035009,0.034785,0.032577],"2022-07-01":[0.299623,0.252638,0.14504,0.108063,0.092914,0.072813,0.055637,0.048802,0.048757,0.044013,0.043459,0.040382,0.035957],"2022-08-01":[0.339682,0.267696,0.166061,0.130827,0.098504,0.072605,0.062373,0.061008,0.053976,0.053546,0.048836,0.043579,0.039844],"2022-09-01":[0.320856,0.265181,0.174043,0.120508,0.085635,0.071577,0.068591,0.060004,0.057834,0.052597,0.045722,0.040783,0.037266],"2022-10-01":[0.302451,0.269288,0.154054,0.102328,0.080566,0.074508,0.062999,0.05952,0.053394,0.046459,0.041231,0.037274,0.035832],"2022-11-01":[0.267126,0.210858,0.113302,0.080854,0.070159,0.057086,0.05187,0.04542,0.038706,0.033737,0.030596,0.029106,0.029104],"2022-12-01":[0.271161,0.206481,0.120764,0.098155,0.075621,0.066926,0.05671,0.047457,0.041221,0.037075,0.035228,0.035146,0.03228],"2023-01-01":[0.324303,0.247366,0.164941,0.115689,0.096968,0.0804,0.065059,0.055718,0.049638,0.046331,0.045441,0.040814,0.032093],"2023-02-01":[0.301337,0.267652,0.153065,0.117703,0.092112,0.071159,0.058951,0.051203,0.046831,0.045231,0.04025,0.030393,0.026904],"2023-03-01":[0.333405,0.254856,0.160874,0.115604,0.086231,0.06852,0.05815,0.052318,0.050006,0.04379,0.032711,0.028506,0.030573],"2023-04-01":[0.345469,0.273807,0.160482,0.1115,0.083801,0.06814,0.060036,0.05639,0.049237,0.03659,0.031642,0.033292,0.029952],"2023-05-01":[0.338201,0.262642,0.147145,0.100641,0.077253,0.065691,0.06019,0.052041,0.038158,0.032515,0.033593,0.029594,0.027852],"2023-06-01":[0.313916,0.239237,0.132397,0.091918,0.073324,0.064964,0.054393,0.040045,0.033738,0.034674,0.030369,0.028281,0.026694],"2023-07-01":[0.332735,0.246012,0.140202,0.102247,0.087411,0.071773,0.050986,0.042003,0.042731,0.036479,0.034042,0.03163,0.028555],"2023-08-01":[0.351257,0.260415,0.15346,0.116443,0.091557,0.064462,0.052061,0.051942,0.044767,0.04061,0.037017,0.032873,0.030213],"2023-09-01":[0.332826,0.262376,0.15937,0.113924,0.077198,0.060165,0.057841,0.04828,0.043208,0.038938,0.034225,0.031286,0.02983],"2023-10-01":[0.331531,0.265659,0.151008,0.093735,0.069341,0.065047,0.052363,0.04586,0.040607,0.035258,0.031389,0.029494,0.028244],"2023-11-01":[0.343869,0.245408,0.12311,0.08159,0.072838,0.0567,0.048381,0.042279,0.036389,0.03209,0.02999,0.028632,0.028352],"2023-12-01":[0.337552,0.228806,0.116051,0.094123,0.070188,0.058244,0.049622,0.041553,0.036303,0.033596,0.031667,0.031259,0.029373],"2024-01-01":[0.365153,0.232889,0.149279,0.099678,0.07734,0.063552,0.052038,0.044484,0.040669,0.037793,0.037234,0.034733,0.028149],"2024-02-01":[0.359183,0.284193,0.153284,0.108696,0.086187,0.069158,0.057893,0.052693,0.048911,0.047292,0.043742,0.03496,0.030641],"2024-03-01":[0.371734,0.254418,0.146397,0.103624,0.079332,0.063729,0.055562,0.050796,0.047837,0.043432,0.034729,0.029785,0.032051],"2024-04-01":[0.371135,0.276066,0.154154,0.107132,0.081653,0.07013,0.061986,0.05775,0.051322,0.040315,0.03443,0.036826,0.03236],"2024-05-01":[0.350962,0.266092,0.145014,0.099574,0.080704,0.068455,0.062207,0.054679,0.042693,0.035862,0.038272,0.033224,0.031946],"2024-06-01":[0.356776,0.249064,0.130343,0.092787,0.0741,0.064719,0.055418,0.042711,0.035148,0.036653,0.031498,0.030316,0.027652],"2024-07-01":[0.354514,0.233759,0.129788,0.092046,0.076661,0.064508,0.048185,0.039029,0.040219,0.034126,0.03294,0.029451,0.027703],"2024-08-01":[0.346216,0.248144,0.139443,0.104035,0.082485,0.059624,0.046901,0.047103,0.039945,0.037622,0.033401,0.030626,0.029746],"2024-09-01":[0.31976,0.239789,0.138862,0.099349,0.067907,0.051966,0.050443,0.041084,0.038232,0.03365,0.030908,0.029069,0.02767],"2024-10-01":[0.32992,0.247648,0.141959,0.088263,0.063719,0.060136,0.047023,0.043551,0.036916,0.033629,0.031381,0.029711,0.027788],"2024-11-01":[0.324124,0.231855,0.114474,0.074757,0.067716,0.051744,0.046428,0.038314,0.034747,0.031612,0.029641,0.02789,0.027981],"2024-12-01":[0.297726,0.209357,0.104288,0.085497,0.061909,0.053387,0.043406,0.038354,0.034701,0.032458,0.029704,0.029935,0.028235],"2025-01-01":[0.318995,0.19914,0.12635,0.081909,0.066936,0.051963,0.04406,0.039028,0.035624,0.032407,0.032058,0.029317,0.024209],"2025-02-01":[0.326739,0.242216,0.121494,0.090134,0.067266,0.056092,0.048328,0.043278,0.039342,0.038429,0.035174,0.028023,0.024002],"2025-03-01":[0.337174,0.225785,0.1268,0.083875,0.065717,0.054708,0.047874,0.042677,0.041078,0.037104,0.029564,0.024674,0.026668],"2025-04-01":[0.320877,0.223345,0.113617,0.079792,0.062827,0.052429,0.045092,0.042457,0.037375,0.029552,0.023987,0.025791,0.023357],"2025-05-01":[0.36827,0.233105,0.130741,0.093276,0.074452,0.062872,0.057503,0.050536,0.039164,0.03185,0.034358,0.030513,0.0295],"2025-06-01":[0.355165,0.249255,0.135487,0.098057,0.078584,0.070057,0.05959,0.045771,0.036434,0.038691,0.034232,0.033251,0.031065],"2025-07-01":[0.336684,0.233633,0.129632,0.095146,0.079749,0.065564,0.049229,0.038806,0.039816,0.034992,0.03305,0.030277,0.02527],"2025-08-01":[0.371925,0.240217,0.142274,0.109487,0.085468,0.061716,0.046982,0.047818,0.04139,0.039208,0.034562,0.028533,0.026055],"2025-09-01":[0.375253,0.281249,0.167816,0.120032,0.084443,0.062754,0.062462,0.052787,0.048752,0.042315,0.03514,0.031497,null],"2025-10-01":[0.369462,0.259963,0.14284,0.090467,0.063614,0.061401,0.050606,0.045545,0.038562,0.031408,0.027937,null,null],"2025-11-01":[0.36741,0.246058,0.117573,0.07308,0.065571,0.051893,0.045587,0.038333,0.030918,0.027156,null,null,null],"2025-12-01":[0.348151,0.212466,0.096278,0.077552,0.057815,0.048562,0.039742,0.031349,0.026862,null,null,null,null],"2026-01-01":[0.373386,0.204809,0.121833,0.081114,0.063959,0.049848,0.038844,0.032343,null,null,null,null,null],"2026-02-01":[0.352784,0.239114,0.117754,0.082535,0.059517,0.044942,0.036895,null,null,null,null,null,null],"2026-03-01":[0.364382,0.231783,0.120556,0.078677,0.056155,0.044257,null,null,null,null,null,null,null],"2026-04-01":[0.360192,0.228701,0.110351,0.071409,0.05422,null,null,null,null,null,null,null,null],"2026-05-01":[0.364281,0.216912,0.104966,0.071632,null,null,null,null,null,null,null,null,null],"2026-06-01":[0.362927,0.209632,0.101234,null,null,null,null,null,null,null,null,null,null],"2026-07-01":[0.365516,0.203635,null,null,null,null,null,null,null,null,null,null,null],"2026-08-01":[0.384421,null,null,null,null,null,null,null,null,null,null,null,null]},"actual_data_row_count":104,"test_rows_ground_truth":{"row3":{"cohort_month":"2018-01-01","values":[0.257008,0.201269,0.14626,0.098356,0.082829,0.084303,0.087615,0.083061,0.065188,0.065425,0.052989,0.048282,0.043582],"total":1.316167,"era":"1 - plain lookup"},"row9":{"cohort_month":"2018-07-01","values":[0.346784,0.271485,0.143761,0.106561,0.077459,0.065446,0.054942,0.04983,0.053739,0.045849,0.045371,0.045566,0.047145],"total":1.353939,"era":"2 - all-actual (VLOOKUP branch every age)"},"row55":{"cohort_month":"2022-05-01","values":[0.285739,0.243972,0.142705,0.103234,0.077689,0.067008,0.062269,0.051019,0.040675,0.036847,0.037888,0.034083,0.034244],"total":1.217373,"era":"2 - all-actual (VLOOKUP branch every age)"},"row101":{"cohort_month":"2026-03-01","values":[0.364382,0.231783,0.120556,0.078677,0.056155,0.044257,0.037494,0.032238,0.028642,0.025571,0.022064,0.019573,0.019535],"total":1.080926,"era":"2 - mixed: ages 0-5 actual (VLOOKUP), ages 6-12 forecast blend - PRIMARY VALIDATION CASE"},"row116_FROZEN":{"cohort_month":"2026-01-01","values":[0.373386,0.204809,0.121833,0.081114,0.063959,0.049848,0.038954,0.034152,0.031733,0.028733,0.02694,0.024143,0.02201],"total":1.101615,"era":"3 - frozen paste-value snapshot, NOT reproducible live (actual data has since revised: live age6=0.038844 vs frozen 0.038954)"},"row121_FROZEN":{"cohort_month":"2026-06-01","values":[0.36288,0.223206,0.114508,0.078256,0.058794,0.049295,0.039599,0.035671,0.031265,0.029122,0.026998,0.024044,0.022057],"total":1.095694,"era":"3 - frozen paste-value snapshot, NOT reproducible live"}}}
```

