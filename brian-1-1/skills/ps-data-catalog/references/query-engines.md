# Query Engines — Druid vs Trino Routing

**Druid is the default engine.** Almost every metric in Playsimple analytics is served by a versioned
Druid chart datasource. Trino is the exception, not the rule — it serves four chart-adjacent things plus the user-level-data
(ULD) layer (all listed below). **Route every query before writing it.** A wrong route fails loudly (syntax/connector
error) or silently (stale chart version, wrong variant, duplicated rows).

## Connection check — Trino must be a connected tool

Druid and Trino are **separate connectors**. Druid is the `queryDruidSql` tool; Trino is the
**`trino-mcp`** connector (a tool whose server name contains `trino`). Before the first Trino statement,
confirm that tool exists (`ToolSearch` for `trino` once if it isn't loaded). If it doesn't, the analysis
cannot start — `chart_config` and `gid_mapping` are prerequisites for every Druid query — so stop and
send the "Connect Trino" message from `brian-master` Step 0: **Settings → Customize → Connectors →
trino-mcp → Connect**, then re-ask (or start a new chat).

A Druid error of the form `Object 'public' not found`, `Object 'play_data' not found` or
`Object 'external_data' not found` means a Trino statement was sent to Druid. It is a routing mistake,
not a moved table — re-send to the Trino tool, never run schema discovery on Druid for it.

## Routing rule

| What you're querying | Engine | Syntax |
|---|---|---|
| Anything with a `chart_XXXX` mapping in the catalog — net/gross revenue, DAU, cohort, spend, predictions, ad monetization, engagement, crashes, notifications | **Druid**, via a `chart_version` resolved from `play_data.chart_config` this conversation | Druid SQL (below) |
| `play_data.chart_config` — the version lookup itself | **Trino** | Trino SQL |
| `play_data.monthly_rev_diff` — long-horizon monthly cohort | **Trino** (no Druid equivalent) | Trino SQL |
| `external_data.sensor_tower_data`, `external_data.st_product_details` — competitor | **Trino** | Trino SQL |
| `play_data.charts_annotations` — chart annotations, the "what changed" layer (no Druid equivalent, no `chart_config` row) | **Trino** | Trino SQL |
| **ULD layer** — user-level tables for questions no chart answers (distinct users, per-user distributions, segment combinations, user-level cross-domain joins, campaign/creative at install, reported revenue by source × country): `derived_tables.dau_splits`, `dm_admon.rev_dau_install_diff_ilrd_v2`, `derived_tables.revenue_reports`, `server_tables.engagement_puzzle_master_cc_col`, `server_tables.sessions_master_cc`, `server_tables.economy_master_cc`, `derived_tables.wallet_dau_install_diff`, `analytics.adjust_installs` | **Trino** — only after confirming no chart answers it; rules in `references/uld.md` | Trino SQL |

That is the complete Trino list, plus `public.gid_mapping` for the name→GID lookup in `ps-entities`, and
the two ULD helper lookups named in `references/uld/*.md` (`analytics.network_mapping`,
`server_tables.test_rid_master_cc`), used only as filters inside ULD queries. Everything else routes to
Druid. **Headline metrics always come from the chart** — the ULD layer answers user-level questions and
is never a substitute when a chart exists. `experiment.users_v2` and `sub_tables.tracking_slice_critical`
are **not** in the ULD layer yet. If a question seems to need a Trino table not named above, the catalog
has a chart for it — find the chart, don't reach for the legacy table name.

**Write table names as `schema.table` — never with a catalog prefix.** The Trino session already sits on
the warehouse catalog, so `play_data.chart_config` is correct and `<catalog>.play_data.chart_config` is
not. Confirmed live (Sep 2026): all five sanctioned Trino tables plus `public.gid_mapping` resolve under
the session catalog — `play_data.chart_config`, `play_data.monthly_rev_diff`,
`play_data.charts_annotations`, `external_data.sensor_tower_data`, `external_data.st_product_details`,
`public.gid_mapping`. Query them by `schema.table` from the first statement of the conversation —
**do not run catalog/schema discovery for them.** Cite them the same way in the response: `schema.table`,
never with the catalog name.

**The one exception:** if a query **run on the Trino tool** against `<schema>.<table>` fails with
schema-or-table-not-found (an environment change, not the routine case), that failure is the trigger for a one-time
`SHOW SCHEMAS` / `SHOW TABLES IN <schema>` discovery — and if the table has genuinely moved, update this
line so the next conversation doesn't re-discover it either.

**Annotations bypass the whole version/variant machinery.** `play_data.charts_annotations` has no
`chart_config` row, no version and no variant suffix — the Step 1–3 lookup below does not apply and must
not be attempted for it. Query it by name. **Two similarly-named tables must not
be queried or fallen back to:** `play_data.charts_annotations_data` is a separate older store with
different columns, and `play_data.annotations_data` holds **0 rows**. The annotation table's own hard rules
— `created_at` as epoch seconds, the three row-inflating duplications, `features` fuzzy-matching, and
the live-coverage probe required before any "outside coverage" claim — live in
`references/annotations.md`, which has its own pre-query checklist.
Annotations are commentary, never a metric: they point a drill-down at a cause; the number still comes from
a chart datasource.

**A warehouse table name not on the list above is retired — don't query it, and don't fall back to it.**
The old per-metric warehouse tables all have Druid replacements in the routing table; where a domain file
names its own retired original, it says so there. They lag the Druid datasources and carry NaN rows the
Druid datasources don't.

## Mandatory version lookup — every chart, every conversation

**Never hardcode a version.** Not `-v20`, not `-v26`, not a version from these reference files, from
memory, or from a past conversation. Versions roll without notice. Every reference in this catalog
writes chart names as `chart_XXXX-vN` precisely so a stale number can't be copied by accident — resolve
`N` from `chart_config` before the chart's first Druid query. One lookup per `chart_id` per
conversation; re-run it if Druid later reports the datasource missing.

**The rule binds per chart, not per batch.** An investigation that widens — a cross-metric sweep, a
cross-check against a sibling family, a denominator from another chart — reaches charts that were not
in the opening batch. **Every one of those needs its own `chart_config` row before its first query.**
Running a second or third lookup mid-analysis is expected and cheap; batch whatever the new stage needs
into one statement. What is never acceptable is inferring a version from a neighbouring chart, from a
version seen earlier in the conversation, or from the shape of another chart's name — different charts
version independently, and a guessed `-vN` either fails loudly or, worse, hits a real but wrong
datasource.

**Step 1 — Look up the chart (Trino). Batch every chart you'll need into one statement:**

```sql
SELECT chart_id, version, chart_version, independent_columns, metrics
FROM play_data.chart_config
WHERE chart_id IN ('chart_579', 'chart_1170', 'chart_1706', 'chart_3730')
ORDER BY chart_id, chart_version
```

`independent_columns` and `metrics` come back as **`array(varchar)`** in Trino — real arrays, not strings.
Read them as arrays; `UNNEST` or `array_join(independent_columns, '-')` if you need them flattened, and
never string-parse them.

**Step 2 — Pick the variant row per metric, and read `independent_columns` correctly.** A chart splits
into one base variant plus reduced variants, each carrying *different* metrics.
**`independent_columns` lists the dimensions that are ABSENT from that variant's datasource** — the
metric is *independent of* them, so they're dropped to keep it from being duplicated across values it
doesn't vary by. Every other chart dimension is present.

- **A metric may only be read from the variant whose `metrics` array lists it** — even if a same-named
  column physically exists in another variant. Reading it elsewhere returns wrong numbers, not just
  redundant ones.
- **A metric cannot be cut or filtered by any dimension in its variant's `independent_columns`** — the
  column does not exist there and the query fails with column-not-found. Say that cut is unavailable
  for that metric (and check the catalog for another table serving it) rather than switching variants
  or guessing. **A column-not-found error is not a Trino-fallback trigger.**
- Metrics spanning variants (e.g. `installs` + `spend`) → one Druid query **per variant**, combined
  client-side. Never join variants inside one query.
- Present dimensions aren't enumerated in `chart_config` — inspect the datasource schema in Druid when
  unsure:
  `SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '<chart_version>'`

**Step 3 — ⚠️ Sort the suffix columns ALPHABETICALLY to build the real Druid name.**

**`chart_config.chart_version` does not always match the actual Druid datasource name.** Druid builds
the suffix by sorting `independent_columns` alphabetically; `chart_config` stores them in arbitrary
order. Confirmed live (Sep 2026):

| `chart_config.chart_version` says | Actual Druid datasource |
|---|---|
| `chart_1706-vN-install_type-dt_flag` | `chart_1706-vN-dt_flag-install_type` |
| `chart_3730-vN-cli-pod-network_name-network_type-country-geo_bucket-accuracy-campaign_type-network_parameter-network_name2` | `chart_3730-vN-accuracy-campaign_type-cli-country-geo_bucket-network_name-network_name2-network_parameter-network_type-pod` |
| `chart_4495-vN-network-time_bucket-ad_type` | `chart_4495-vN-ad_type-network-time_bucket` |
| `chart_4495-vN-time_bucket-network-ad_type` | `chart_4495-vN-ad_type-network-time_bucket` (both config rows collapse to one datasource) |

So: take `chart_id` + `-v` + `version` from config, then append the `independent_columns` **sorted
alphabetically**, hyphen-joined. Querying config's literal string fails with
`Object '<name>' not found`. When two config rows carry the same column set in different orders they
resolve to the same datasource — that is expected, not a duplicate.

**Confirm the name when in doubt** — one cheap listing settles it:

```sql
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'chart_1706%' ORDER BY TABLE_NAME
```

Druid may hold **older and newer versions side by side** (e.g. `chart_1706-v4`, `-v20`, `-v21` all
present while config says 20). **`chart_config` is authoritative for which version to use** — take
config's number even when a higher one exists in Druid; a version present but not yet promoted in
config is not ready for reporting. Use the listing only to fix the *column ordering*, never to pick a
different version.

**There is no Trino fallback for a chart metric.** The ULD tables are not a fallback either — they answer
user-level questions, and their totals do not tie to the charts. Beyond them, Trino serves the five tables above and nothing else —
the per-metric warehouse originals are retired, so when a chart is genuinely unavailable there is no
substitute table to reach for. Two failures are worth re-checking before concluding anything:

1. `chart_config` has **no rows** for the `chart_id` — re-run the Step 1 lookup once.
2. Druid reports the **datasource missing** after you've (a) re-run the Step 1 lookup once and (b)
   confirmed the alphabetical sort — a missing-datasource error is far more often a sort-order mistake
   than a genuinely absent datasource.

If both survive that check, **say the chart is unavailable** and name it in the response. A syntax error,
a column-not-found, or an empty result set is none of the above — fix the query instead.

## Druid SQL syntax

- **Double-quote every identifier**: datasource, columns, `"__time"`. Versioned names contain hyphens
  and fail unquoted.
- Date/partition column is always `"__time"` — always filter it, anchored to calendar periods. Note
  `"__time"` is a timestamp, so `BETWEEN a AND b` covers b's midnight instant only — for a full-day
  inclusive range use `"__time" >= '<START>' AND "__time" < '<END+1 day>'`.
- Aggregate with `SUM("field")`; `GROUP BY 1` positional, or `GROUP BY ()` for a single grand-total row.
- No backticks, no catalog/schema prefix — the datasource is the bare quoted `chart_version` string.
- **Numeric-looking dimensions are often VARCHAR** in Druid (`gid`, `cli`, `diff` are strings on the
  datasources checked). Quote the literal — `"gid" = '22'`, `"diff" = '360'` — rather than passing a
  bare number. **This is the opposite of Trino**, where `gid`, `cli` and `diff` are real `BIGINT`
  columns on `monthly_rev_diff` and `charts_annotations` and must be compared **unquoted** (`gid = 22`).
  Carrying Druid's quoted-literal habit into a Trino statement is a type error, not a no-op.
- **Match case on both sides for `country` (and any other lowercase-coded string dimension).** Country
  is stored as lowercase ISO alpha-2 (`us`, `gb`, `ca`, `au`, …) on every datasource that carries it —
  Druid and Trino alike — even though tier names and prose elsewhere write it uppercase
  (`ps-entities`: Tier-1 = US, GB, CA, AU). Filtering `"country" IN ('US','GB','CA','AU')` is not an
  error — it returns an empty result set, which reads as a missing/unpopulated field rather than a
  case mismatch. Always lowercase the literal: `"country" IN ('us','gb','ca','au')`.
- **`COUNT(DISTINCT x)` is APPROXIMATE by default in Druid** (HLL sketch) and it is wrong at small
  cardinalities. Confirmed live (Aug 2026): `COUNT(DISTINCT TIME_FLOOR("__time",'P1D'))` over July 2026
  on `chart_579-vN` returned **30** for a range that contains **31** days (Jul 1–31 inclusive, verified by
  `GROUP BY` day and counting the rows). **Never use `COUNT(DISTINCT …)` for a day count, a coverage
  denominator, or anything a figure depends on** — an off-by-one day count silently breaks the
  equal-day-count comparison rule. Get exact counts by grouping on the value and counting the returned
  rows client-side (which the consolidation pattern below already gives you for free), or wrap it:
  `SELECT COUNT(*) FROM (SELECT <expr> FROM … GROUP BY 1)`. **`COUNT(DISTINCT …)` in Trino is exact** —
  the workaround is a Druid rule only, and carrying it into Trino just makes the query harder to read.
- Some words are reserved by the Calcite parser and fail as bare aliases — `period` is one
  (`… END AS period` → syntax error near `AS`). Double-quote every alias.
- **Aliases are safe to double-quote, and `TIME_FLOOR("__time", 'P1D')` is the day-bucket expression.**
  Compare `"__time"` against `TIMESTAMP '2026-07-01 00:00:00'` literals.

## Trino SQL syntax

The five sanctioned tables are ordinary ANSI SQL. What differs from the Druid statements above:

- **Name tables `schema.table`.** No catalog prefix, no backticks, no notebook magic (`%sql` is a
  syntax error here — never emit it).
- **Single quotes are string literals; double quotes are identifiers.** A regex or a value written in
  double quotes resolves as a column name and fails. To put a literal single quote inside a string,
  double it: `'''objectsAffected'': \[([^\]]*)\]'`. Backslashes inside a Trino string literal are not
  escape characters, so a regex's `\[` passes through as written.
- **Typed literals for dates and timestamps**: `DATE '2026-08-01'`, `TIMESTAMP '2026-06-28'`. A bare
  string compared against a `date`/`timestamp` column does not implicitly cast —
  `from_unixtime(created_at) >= '2026-06-28'` fails; `>= TIMESTAMP '2026-06-28'` works.
- **Date arithmetic is `date_add(unit, n, date)`**, not `add_months`:
  `date_add('month', diff, install_month)`. `install_month` is already a real `date` column, so
  `to_date()` around it is unnecessary.
- **`array_agg(DISTINCT x)` instead of `collect_set(x)`**, and **`bool_or(x)` instead of `max(x)`
  on a boolean** — `max()` over a boolean is not a valid Trino signature.
- **`regexp_extract(col, pattern, group)` keeps its name**, but returns **NULL** (not an empty string)
  when the pattern doesn't match — so a narrative-category row with no `objectsAffected` list comes back
  `NULL`. Wrap in `coalesce(…, '')` if a blank reads better.
- **Cast before aggregating a string measure.** `external_data.sensor_tower_data.value` is `varchar`:
  `SUM(CAST(value AS DOUBLE))`. Trino will not silently coerce it.
- **`COUNT(DISTINCT …)` is exact**, and `DESCRIBE <schema>.<table>` / `SHOW COLUMNS FROM <schema>.<table>`
  is the schema probe (no `DESCRIBE TABLE`).
- **Reads only.** `INSERT` / `UPDATE` / `DELETE` / `MERGE` and all DDL are blocked on this connection, as
  they should be — this catalog is query-only either way.

## Query consolidation — prefer one statement, split when it gets tricky

**Default to one statement where the merge is obvious; split without hesitation where it isn't.** A wrong
consolidated query costs far more than a saved round-trip, so this is a preference, not a mandate. There is
no target statement count — write as few as are *clearly* correct.

**The obvious merges — do these.** If the only difference between two statements you were about to write is
a **filter value** or a **date range** on the same variant, merge them: move the value into
`WHERE … IN (…)` plus a `GROUP BY` column, or widen the date range and bucket client-side.

| Don't | Do |
|---|---|
| One statement per `gid` | `WHERE "gid" IN ('22','26','39') GROUP BY "gid"` |
| One statement per platform / country / network / ad type | Add that dimension to the `GROUP BY` |
| Current-period statement **+** prior-period statement (adjacent periods — WoW, MoM) | One statement spanning both, grouped by day; bucket client-side |
| A separate `MAX("__time")` freshness probe | Read the max of the day column the trend query already returns |
| A separate rollup probe (`SELECT dim, COUNT(*) … GROUP BY 1`) | Put the dim in the real query's `GROUP BY`; the rollup value arrives as a row, with its measure |
| A trend statement **+** a period-total statement | One day-grained statement; total it client-side |
| A separate day-count / coverage statement | Count the returned day rows |

**Group by day over the span.** One statement then yields the current period, the prior period, the trend
series for the chart, the exact day count per period, and that variant's freshness. Bucket days into
weeks/months **client-side** rather than `TIME_FLOOR`-ing to a month: `"__time"` is UTC, calendar anchoring
is a presentation rule, and keeping day rows is what makes the equal-day-count trim possible.

```sql
-- MoM for two games: both periods, day counts and freshness in one statement
SELECT "gid",
       CASE WHEN "__time" >= TIMESTAMP '2026-07-01 00:00:00' THEN 'cur' ELSE 'prior' END AS "bucket",
       TIME_FLOOR("__time", 'P1D') AS "d",
       SUM("revenue") AS "revenue"
FROM "chart_579-vN"
WHERE "__time" >= TIMESTAMP '2026-06-01 00:00:00'
  AND "__time" <  TIMESTAMP '2026-08-01 00:00:00'
  AND "gid" IN ('22','26')
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
```

Verified live (Aug 2026): this form's July total for gid 22 tied the equivalent single-period single-game
query to 6+ significant figures (3,529,274.3106 both ways — last digits differ by ~4e-6 from float
aggregation order, which is expected and not a discrepancy).

### When to split instead — all legitimate, none a defect

Splitting is the right call whenever merging would need cleverness. Specifically:

- **Non-contiguous periods (YoY).** One `WHERE (rangeA) OR (rangeB)` works and scans only the two ranges —
  but **the `OR` must be parenthesised, with every other filter outside it**. `WHERE A OR B AND "gid"='22'`
  parses as `A OR (B AND gid)` and silently returns the wrong rows. If that makes you uneasy, use two
  statements.
- **Per-slice filters.** One game needs a `source` exclusion another doesn't; one segment needs a different
  `install_bucket`. Expressing that in one statement means conditional aggregation — split.
- **Per-slice rollup pins.** One figure pins `network = 'overall'` while another excludes it, on the same
  variant. Two statements are clearer than `SUM(CASE WHEN …)`.
- **Per-slice windows.** Different maturity-capped dX per cohort month, or a different trimmed window per
  game. Split.
- **Anything needing conditional aggregation, `GROUPING SETS`, or nested `CASE` inside an aggregate** to
  come out in one shot.
- **A result grid whose shape you can't predict before running it**, or one so wide you'd be picking rows
  to ignore.
- **Anything that would cross engines.** Druid and Trino are separate connections — a chart metric and a
  `monthly_rev_diff` or annotation pull are always separate statements, combined client-side. There is no
  join between them.

If you can't state what the single merged statement will return before you run it, that is the signal to
split. Say nothing about it in the response — it isn't a compromise worth narrating.

### Correctness guardrails — these hold either way

1. **Never average daily rates to get a period rate.** Aggregate numerator and denominator over the period
   first, *then* divide. `AVG(daily ROAS)` ≠ period ROAS. Same for Rev/DAU, eCPI, retention, eCPM. A
   day-grained pull makes this mistake easy to make.
2. **Cross-variant ratios are always at least one statement per variant.** Druid cannot join variants, so
   eCPI is two statements (installs variant + spend variant) no matter what.
3. **Merge within a variant only, never across datasources — and never across engines.** Different charts
   are different statements; Druid and Trino are different connections.
4. **Aggregate in the engine; never pull raw rows.** These datasources are enormous — one game-month on
   `chart_579-vN` sits on 515,008 raw rows. Always `SUM()` with a `GROUP BY`.
5. **Keep the returned grid readable.** Group by only the dimensions the answer needs; prefer dropping a
   `GROUP BY` dimension over returning thousands of rows you won't read.
6. **The rollup guard still applies** (next section) — satisfy it by inspecting grouped output where you
   can, by probing where you can't.
7. **A rewritten query re-earns the whole checklist.** Fixing a failure — a version, a sort order, a
   namespace prefix, a column name — means writing a new statement, and mandatory pins, hard filters and
   `WHERE` clauses are silently lost in the rewrite. **This is the highest-frequency way a correct
   analysis produces wrong numbers**, because the retry succeeds: no error, just a denominator that now
   spans a stacked dimension or an unfiltered segment. Diff the rewrite against the original before
   running it, and re-check the pre-query checklist below — the fix is never the only change that
   matters.
8. **Sanity-check every derived rate against its expected magnitude before reporting it** (SR-19). A
   ratio landing near a clean multiple or fraction of the level you expected — roughly 2×, roughly ½× —
   is a denominator defect, not a discovery: an unpinned stacked dimension summing two populations, a
   numerator and denominator at different grains, or a filter that reached only one side. Check the
   pins, then report. A rate outside its definitional range is never reported at all.

```sql
-- daily metric for one game (version resolved from chart_config this conversation)
SELECT "__time", SUM("revenue") AS net_revenue
FROM "chart_579-vN"
WHERE "__time" >= '2026-07-01' AND "__time" < '2026-08-01' AND "gid" = '22'
GROUP BY 1
```

```sql
-- metric from a reduced variant; note the ALPHABETICALLY sorted suffix
SELECT "gid", SUM("spend") AS spend
FROM "chart_1706-vN-dt_flag-install_type"
WHERE "__time" >= '2026-07-01' AND "__time" < '2026-08-01'
GROUP BY 1
```

```sql
-- freshness check
SELECT MIN("__time") AS "min_time", MAX("__time") AS "max_time"
FROM "chart_579-vN"
GROUP BY ()
```

## Rollup guard — read the domain reference; do not probe every chart

Some dimensions carry a rollup value (`'overall'`, `'others'`, `'w/o …'`) alongside their members, or stack
several logical series in one column (`model_type`, `accuracy`, `metric`, `id_type`); a plain `SUM()` across
one then double-counts or mixes segments.

**Which dimensions those are is dataset-specific, and each domain reference declares them up front under
"Rollups & mandatory pins".** That declaration is authoritative and it is positive in both directions — it
names the rollups where they exist and states plainly where there are none.

**So: read it, then act. Do not run a discovery probe on a chart whose reference declares no rollups.**
Probing every datasource for `network = 'overall'` or `id_type` when those columns aren't even present is a
wasted round-trip per chart, and it was the single largest source of dead queries in this catalog. As a
rough map of where to expect them — always confirm in the domain file, never from this list:

| Domain reference | Rollups / mandatory pins |
|---|---|
| `core-and-cohort.md` (`chart_579`, `1170`, `1706`, `monthly_rev_diff`) | **none** (only `geo_bucket` / `country_bucket` on the gross chart) |
| `predictions.md` (`chart_3730`, `1071`) | `model_type`, `accuracy` — pins, not rollup rows |
| `drilldown.md` (`chart_2077`) | `mediation`, `country`, `id_type` |
| `ad-monetization.md` (`chart_2160`, `4495`) | `network`, `country` |
| `engagement.md` (`chart_2524`, `2898`, `2301`, `2917`, `2888`, `2076`) | `id_type`, `category`, `puzzle_type`, `country` |
| `stability-and-notifications.md` | `id_type` |
| `competitor.md`, `annotations.md` | **none** |

**Where a check IS warranted, satisfy it by deriving, not probing** — put the dimension in the real query's
`GROUP BY` and the rollup arrives as a labelled row *with its measure*, which beats a `SELECT dim, COUNT(*)`
probe and costs no extra statement:

```sql
SELECT "model_type", TIME_FLOOR("__time", 'P1D') AS "d", SUM("<metric>") AS "v"
FROM "chart_1071-vN"
WHERE "__time" >= TIMESTAMP '<start>' AND "__time" < TIMESTAMP '<end>'
GROUP BY 1, 2
```

Spend a dedicated probe only when the value must be known *before* the query is written because it goes in
the `WHERE` clause, and the domain file doesn't enumerate it. Never run any of this on a dim listed in that
variant's `independent_columns` — the column doesn't exist there and the query fails.

- A rollup value exists → **pin it for totals**, **exclude it when drilling** members, never sum both.
- The reference declares none → summing across that dimension is the correct total. Proceed.
- Summing across a dimension **no** reference documents at all → that is the one case worth a look.
- An implausibly large figure → re-read the declaration *before* reporting, not after.

## What the Druid migration made obsolete

Two long-standing warehouse workarounds no longer apply, and carrying them over produces wrong
numbers or unnecessary caveats:

- **NaN pre-check on predictions.** `Growth_widget` returned NaN aggregates for whole games (gids 29,
  36, 37, 45 on July 2026), forcing segment isolation and coverage disclosure. `chart_3730-vN-target_bucket`
  returns clean values for all of them. Don't isolate NaN segments or disclose NaN-driven coverage from
  Druid — if a Druid prediction figure comes back NaN, that's a genuine anomaly worth investigating,
  not routine.
- **`MAX()`-collapse on ad monetization.** `dm_admon.metrics2` duplicated most metrics across
  `time_bucket`, requiring a collapse-then-sum subquery. `chart_4495`'s variants drop the duplicating
  dimension structurally — `rev`/`imps`/`users`/`clicks` live on the variant with no `time_bucket`
  column at all, so a plain `SUM()` is correct. Reaching for `MAX()` there now *understates* the figure.

The `no_pred` / coverage rules and the `network = 'overall'` rollup pin are **not** obsolete — they are
dimension-value rules, not storage artifacts, and still apply in Druid.

## Pre-query checklist (charts)

**Run this before the first query and again before every rewritten one** — a retry is a new statement,
and it re-earns every line below.

1. Trino connector confirmed present (else stop with the "Connect Trino" message); engine routed by name; only `chart_config`, `monthly_rev_diff`, the two Sensor Tower tables,
   `charts_annotations`, `gid_mapping` and (for user-level questions only, per `references/uld.md`) the ULD tables sent to Trino; every ULD statement bounded on its partition column; Trino names written as bare `schema.table` with
   no catalog prefix and no `%sql`; no retired legacy table queried; no version/variant lookup attempted
   for the annotation table; neither `charts_annotations_data` nor `annotations_data` touched?
2. `chart_version` resolved from `chart_config` **this conversation**, per metric and **per chart** —
   including any chart the analysis reached after the opening batch — no hardcoded or inferred version
   anywhere?
3. Suffix columns **sorted alphabetically** to build the datasource name, and config's version number
   used even if Druid holds a higher one?
4. Each metric read only from its own variant; no cut or filter attempted on a dim in that variant's
   `independent_columns`; multi-variant needs split and combined client-side?
5. Present dimensions being summed across checked for rollup values before the first `SUM()`; rollups
   pinned for totals / excluded for drills; domain hard filters applied — **and, if this is a rewrite,
   every pin and filter from the previous attempt still present in the new statement**?
6. `"__time"` filtered on every Druid query, calendar-anchored; Druid string dimensions quoted, and
   Trino `BIGINT` columns (`gid`, `cli`, `diff`) left **unquoted** with typed `DATE`/`TIMESTAMP` literals?
7. A chart that survived a lookup retry **and** a sort-order check reported as unavailable — not
   substituted with a retired warehouse table, since Trino has no fallback for chart metrics?
8. Any derived rate this statement feeds checked against its expected magnitude before it reaches the
   answer — a ≈2× or ≈½× miss treated as a denominator defect, not a finding (SR-19)?
9. Nothing about to be reported as absent, empty, or out of coverage on a reference file's authority —
   every such claim carrying a probe run this conversation, with the result quoted (SR-20)?
