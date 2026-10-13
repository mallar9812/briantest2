---
name: "revenue-projection-chat"
description: "Fast, chat-only Playsimple revenue projection: give a spend plan (either a month-by-month list, or a single starting spend + growth rate) and get the calendar-month revenue numbers for a target year answered directly in the conversation -- no workbook, no Google Sheet, just the table and the total. Use this whenever someone hands you a spend number/schedule and asks 'what revenue does this get us', 'project revenue for year X', 'if we spend $X/month what do we make back', especially when they want the answer now rather than a file to open. This is the SAME cohort model as revenue-roas-projection, run the fast way: one merged SQL pull instead of many, and a chat answer instead of a workbook. Push for this skill over building a spreadsheet whenever the request doesn't actually ask for a deliverable file -- most 'what's the revenue projection' questions just want the numbers, and building a file first only slows the answer down and can always be added after, on request."
---

# Revenue Projection -- Chat Mode

Same cohort model as `revenue-roas-projection` (read that skill's SKILL.md for
the full mechanics: the three regimes, seasonal/tail-share tables, how
projected-cohort assumptions are derived) -- this skill is about running it
**fast** and answering **in the chat**, because most of the time someone
hands you a spend plan they want the numbers back, not a file to open.

A run of this pipeline earlier took over 20 minutes. Two things caused nearly
all of that, and neither is inherent to the math:

1. **Pulling the raw cohort data in many small sequential round trips**
   instead of one compact query.
2. **Building a deliverable (workbook, then an attempted Google Drive upload)
   when nobody had actually asked for a file yet.**

Fix both and this comes back in a few minutes. This skill exists to make
those two fixes the default path, not something you have to rediscover each
time.

## Step 0 -- read the request

- **Scope**: portfolio-wide (all games combined) unless a specific game or
  franchise is named. Portfolio-wide is the default per the last
  conversation with the user -- don't ask unless a game name actually
  appears in the request. If a game IS named, resolve it via `ps-entities`
  (or the `gid_mapping` query in `revenue-roas-projection`) and filter to
  that `gid` instead of aggregating.
- **Spend input** -- two shapes, both fine, don't ask the user to reformat:
  - **A month-by-month list or schedule** ("13.5M in Aug, 16M in Sept, ...")
    -- write it straight to `spend_schedule.csv` (`install_month,spend`) and
    pass `--spend-schedule spend_schedule.csv` to the script.
  - **A single starting figure + growth rate** ("$18M/month starting Sept,
    growing 2%/mo", or just "$18M/month flat") -- no CSV needed at all, pass
    `--assumed-spend 18000000 --spend-growth 0.02` (or `--spend-growth 0` for
    flat) directly. Don't hand-build a monthly schedule for this case --
    the script already compounds it per month on its own.
  - If they only gave a flat annual total with no monthly shape and no
    growth rate, say so and default to an even monthly split, same as
    `revenue-roas-projection` recommends -- but flag that a real plan is
    rarely flat.
- **Target year(s)**: whatever return year(s) they asked about. If genuinely
  ambiguous (no year mentioned and none inferable from the spend schedule's
  own date range), ask once rather than guessing.

## Step 1 -- ONE merged SQL pull, not a batch loop

This is the single biggest speed lever. Don't pull spend and the cohort grid
as two queries, and don't paginate the cohort grid with LIMIT/OFFSET across
several round trips -- both of those are what turned this into a 20+ minute
job before. Instead use the merged, compacted query documented in
`revenue-roas-projection`'s "Step 1" (reproduced here for the portfolio-wide
case -- drop the `WHERE gid = <GID>` filter entirely for portfolio-wide, add
it back for a single named game):

```sql
WITH sp AS (
  SELECT install_month, SUM(spend) AS spend FROM (
    SELECT gid, cli, install_month, MAX(spend) AS spend
    FROM play_data.monthly_rev_diff
    GROUP BY 1,2,3
  ) GROUP BY 1
),
coh AS (
  SELECT install_month, diff, SUM(rev) AS rev
  FROM play_data.monthly_rev_diff
  GROUP BY 1,2
)
SELECT concat_ws('~',
  concat_ws('|', collect_list(concat_ws(',',
    cast(c.install_month as string), cast(c.diff as string), cast(c.rev/s.spend as string)))),
  (SELECT concat_ws('|', collect_list(concat_ws(',', cast(install_month as string), cast(spend as string)))) FROM sp)
)
FROM coh c JOIN sp s ON c.install_month = s.install_month
```

**This `gid` in the inner GROUP BY is load-bearing, not optional.** `spend` is
repeated on every `diff` row for a given (gid, cli, install_month) cohort --
if you group by `(cli, install_month)` only, `MAX(spend)` silently collapses
every game sharing that platform+month down to whichever ONE game happened to
have the largest spend, discarding every other game's spend entirely. On a
real portfolio pull (2026-01, portfolio-wide) this undercounted total spend
by roughly 4x ($4.6M measured vs. the correct $18.3M, verified by summing
`MAX(spend)` per `(gid, cli)` directly against Databricks) -- and because
`inc_roas = rev/spend`, an undercounted spend inflates every derived ROAS by
that same factor, which then compounds through the trend/seasonal/tail
tables into a badly overstated revenue projection (confirmed: this exact
mistake, made independently by two different test runs of this pipeline,
produced 2027 totals near $1.0-1.06B against a same-inputs number of $334.8M
that was independently pulled correctly and audited). Any hand-written
fallback query must preserve this same `(gid, cli, install_month)` grouping
before summing spend across games -- never take `MAX(spend)` grouped by
platform+month alone.

Why this is fast where a batched pull isn't: it returns ONE string (blob),
not one JSON row per data point, so there's no per-row formatting overhead --
years of portfolio history compact down to a size that normally clears the
per-call output limit in a single round trip. Split the result on `~` first,
then the grid half on `|` then `,` into `raw.csv` (`install_month,diff,inc_roas`),
and the spend half the same way into `spend.csv` (`install_month,spend`).

**If it still comes back truncated to a file**, that's expected on a full
multi-year portfolio history, not a failure: parse the saved file
programmatically (`json.load` then split on `~`/`|`/`,`), don't manually
re-paginate with LIMIT/OFFSET and don't hand-retype any of the blob -- a
dropped digit in a hand-copied float silently corrupts a spend figure.

**If it instead comes back as an undecodable binary blob** (observed in
practice: a `PROTOBUF_ARRAY`-serialized result with no text form to parse),
don't improvise a different SQL shape from memory -- that's exactly how the
`gid`-dropping bug above gets reintroduced. Fall back to the two separate
queries below instead (still correct, just two round trips instead of one),
batching each with LIMIT/OFFSET only if needed:

```sql
-- spend.csv
SELECT install_month, SUM(spend) AS spend FROM (
  SELECT gid, cli, install_month, MAX(spend) AS spend
  FROM play_data.monthly_rev_diff GROUP BY 1,2,3
) GROUP BY 1 ORDER BY 1
-- raw.csv
SELECT install_month, diff, SUM(rev) AS rev
FROM play_data.monthly_rev_diff GROUP BY 1,2 ORDER BY 1,2
```
(then divide rev by that install_month's spend to get `inc_roas` per row).

**Either way, spot-check one recent month before trusting the pull**: pick
any install month you have a rough sense of scale for (e.g. one from the
user's own spend plan, or the most recent actual month) and sum `MAX(spend)`
grouped by `(gid, cli)` for it directly -- a few seconds, and it catches the
gid-dropping bug immediately, since the buggy version undercounts by roughly
however many games share that platform+month (a 3-5x gap is typical, not a
rounding difference). Don't skip this because the merged query "should" be
correct -- it's the cheapest possible check against a genuinely expensive
mistake to ship.

## Step 2 -- run the model

```bash
python3 scripts/roas_curve.py --raw raw.csv --spend spend.csv \
  --from-cohort 2018-01 --to-cohort <last month of target year> \
  --start 2018-01 --horizon <big enough to reach the target year from your oldest cohort> \
  --rollup [--spend-schedule spend_schedule.csv | --assumed-spend N --spend-growth R]
```

`--horizon` must be large enough for your OLDEST pulled cohort to reach the
target return year (see `revenue-roas-projection` for why -- an old cohort's
long tail still contributes revenue to this year). `--from-cohort` should be
your earliest pulled month, not the first future one, for the same reason.

This finishes in seconds -- the SQL pull is what takes time, not the local
script. Skip `--roas-growth` unless the user gave you one; the script
auto-derives it from the portfolio's own recent trend and prints what it
used.

## Step 3 -- answer in the chat, not a file

Read `rev_by_month.csv`, filter to the requested year(s), and answer with
this template -- don't create a workbook, don't attempt a Google Sheet or
Drive upload, unless Step 4 applies:

```
**[Scope] revenue projection -- [Year]**

| Month | Revenue |
|---|---|
| Jan | $X |
| ... | ... |
| Dec | $X |

**Total: $X**

Assumptions: <the spend-growth / roas-growth notes the script printed, in
plain language -- e.g. "ROAS growth wasn't given, so it's auto-derived at
-1.5%/mo from the trailing 6 cohorts' own trend">
```

Do a quick sanity pass before answering, not a formal audit: spot-check that
a couple of `recovery` values equal `roas * spend` for their row, that no
month is negative, and that the row count roughly matches what you'd expect
(months in range x contributing cohorts). This takes seconds in the same
script run or a short follow-up read of the CSV -- it is not the multi-step
audit workflow described in Step 4.

## Step 4 -- only if a file is explicitly requested (slower, opt-in)

If the user asks for a spreadsheet, workbook, or Google Sheet on this same
turn (rather than the earlier chat answer being enough), that's a separate,
slower ask -- say so, then follow the `xlsx` skill's conventions to build the
workbook from `roas_grid.csv`/`rev_by_month.csv`, recalculate it, and hand it
to the user as a file. Do **not** attempt to embed the file's raw bytes into
a Google Drive API call to auto-convert it into a native Sheet -- a base64
string of any real size is exactly the kind of thing that silently corrupts
on a single dropped or duplicated character when reconstructed from chunked
reads, and that failure mode has already been hit once. If the user wants it
in Drive as a native Sheet, either they drag the file in themselves (fastest,
zero risk), or use a real browser to do the upload through the actual file
picker rather than pasting raw bytes into an API call.

## Bundled

`scripts/roas_curve.py` -- identical copy of the model script from
`revenue-roas-projection`, so this skill is self-contained. If that skill's
script is ever updated, re-sync this copy.
