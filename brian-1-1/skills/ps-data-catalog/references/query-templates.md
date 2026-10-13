# Query Templates — Trino only

⚠️ **Trino now serves exactly four things.** Everything else routes to Druid — versioned
datasource from `play_data.chart_config`, alphabetically-sorted variant suffix, Druid SQL, rollup guard
and unavailability rules all in `references/query-engines.md`. Do not use this file's syntax for a chart.

The four Trino jobs:

1. **`play_data.chart_config`** — the version lookup. Runs on every conversation that touches a chart.
2. **`play_data.monthly_rev_diff`** — long-horizon monthly cohort; the one core table with no Druid
   equivalent.
3. **`external_data.sensor_tower_data`** + **`external_data.st_product_details`** — competitor data.
4. **`play_data.charts_annotations`** — chart annotations, the "what changed"
   layer. **No `chart_config` row, no version, no variant**, so nothing in `query-engines.md` Steps 1–3
   applies; its own hard rules, query shapes and checklist live in `references/annotations.md`. Do **not**
   query or fall back to `play_data.charts_annotations_data` (a separate older store) or
   `play_data.annotations_data` (empty).

`public.gid_mapping` is the fifth Trino read — the name→GID lookup, owned by `ps-entities`.

These show **structure and syntax only**. No filter *value* below is a default — apply a filter only when
the question calls for it or a hard rule requires it, and omit an unscoped filter entirely rather than
blanking it. If unsure whether a source exclusion applies, ask the user rather than carrying one over.

## Trino SQL form

```sql
SELECT gid, cli, SUM(rev) AS rev
FROM play_data.monthly_rev_diff
WHERE install_month >= DATE '2026-01-01' AND gid = 9 AND cli = 0
GROUP BY 1, 2
```

- **`schema.table`, never a catalog prefix**, no backticks, and **no `%sql`** — it is a syntax error
  in Trino.
- Single quotes are strings, double quotes are identifiers. Typed literals for dates and timestamps:
  `DATE '2026-08-01'`, `TIMESTAMP '2026-06-28'` — a bare string will not implicitly cast.
- `gid`, `cli` and `diff` are real `BIGINT` columns here — compare them **unquoted** (`gid = 22`). The
  quoted-literal rule is a Druid rule and does not carry over.
- Group by raw column positions matching the selected dimensions; aggregate last.
- Date columns: `date_field` (a real `date`) on the Sensor Tower tables. `play_data.monthly_rev_diff`
  has **no date column** in the daily sense — scope it by `install_month`, itself a `date`.
- Full dialect notes — `date_add` vs `add_months`, `array_agg` vs `collect_set`, `bool_or`, regex
  quoting, casting `value` — are in `references/query-engines.md` under "Trino SQL syntax".

## 1. Chart version lookup

Batch every chart the conversation needs into one statement, then build each Druid datasource name by
appending the variant's `independent_columns` **sorted alphabetically**:

```sql
SELECT chart_id, version, chart_version, independent_columns, metrics
FROM play_data.chart_config
WHERE chart_id IN ('chart_579', 'chart_1170', 'chart_1706', 'chart_3730')
ORDER BY chart_id, chart_version
```

`independent_columns` and `metrics` are `array(varchar)` in Trino — real arrays. Read them as arrays;
`array_join(independent_columns, '-')` flattens one if you want the suffix inline. Never string-parse them.

## 2. Long-horizon monthly cohort

`spend` repeats on every `diff` row of a cohort — **always `MAX()`, never `SUM()`**, or the figure
inflates by the row count (confirmed: one cohort carried the identical value on 104 rows).

```sql
-- per-month cohort revenue
SELECT gid, cli, install_month, diff,
       date_add('month', diff, install_month) AS dau_month, rev
FROM play_data.monthly_rev_diff
WHERE gid = <GID> AND cli = <CLI>
ORDER BY install_month, diff
```

```sql
-- cohort spend, deduplicated
SELECT gid, cli, install_month, MAX(spend) AS spend
FROM play_data.monthly_rev_diff
WHERE gid = <GID> AND cli = <CLI>
GROUP BY 1, 2, 3
```

`install_month` is already a `date` — no `to_date()` wrapper, and the month step is
`date_add('month', diff, install_month)`, not `add_months`.

Cumulative ROAS through month N = `SUM(rev WHERE diff <= N) / MAX(spend)`. Only `gid` and `cli` exist as
dimensions — no country/network/source cut is possible here; say so rather than switching charts
mid-answer.

## 3. Sensor Tower pivot

`sensor_tower_data` is long/pivoted — one `metric` + `value` row per product/platform/country/date. Pivot
only the metrics the question needs and join `st_product_details` for readable names. Available metrics:
revenue, downloads, active_users, d1, d7, d14, d30, session_count, total_session_count, session_duration,
time_spent, total_time_spent.

```sql
SELECT
  a.date_field AS "time",
  b.product_name AS game_name,
  a.platform AS os,
  b.publisher_name,
  b.game_class AS category,
  a.product_id,
  upper(a.country) AS country,
  SUM(CASE WHEN a.metric = 'revenue'      THEN CAST(a.value AS DOUBLE) END) AS revenue,
  SUM(CASE WHEN a.metric = 'downloads'    THEN CAST(a.value AS DOUBLE) END) AS downloads,
  SUM(CASE WHEN a.metric = 'active_users' THEN CAST(a.value AS DOUBLE) END) AS active_users,
  SUM(CASE WHEN a.metric = 'd1'           THEN CAST(a.value AS DOUBLE) END) AS d1_retention,
  SUM(CASE WHEN a.metric = 'd7'           THEN CAST(a.value AS DOUBLE) END) AS d7_retention
FROM external_data.sensor_tower_data a
LEFT JOIN external_data.st_product_details b ON a.product_id = b.product_id
WHERE a.date_field BETWEEN DATE '<START>' AND DATE '<END>'
  AND a.product_id IN (<PRODUCT_ID(S)>)
GROUP BY 1, 2, 3, 4, 5, 6, 7
```

- `date_field` is a real `date` at daily grain — anchor ranges to calendar periods and use typed `DATE`
  literals. For a single-day snapshot replace the `BETWEEN` clause with `a.date_field = DATE '<DATE>'`.
- Resolve `product_id` via `st_product_details` first; **`value` is `varchar`, so
  `CAST(value AS DOUBLE)` before any aggregation** — Trino will not coerce it for you.

## Custom / ratio metrics

Query each base metric separately from its correct datasource, then apply the formula client-side. Never
combine metrics from different tables or variants in one query, and never across engines. Align numerator
and denominator to matching available dates only.

## Schema verification

Not a default step — trust the catalog for documented tables and query them directly. Run this only on a
trigger: (1) before reporting that a metric, dX, or dimension isn't available; (2) after a schema error,
**and only once you've confirmed the alphabetical sort** on a Druid name; (3) for a table with no catalog
entry. At most once per table per conversation.

```sql
DESCRIBE <schema>.<table>
```

`SHOW COLUMNS FROM <schema>.<table>` is equivalent. There is no `DESCRIBE TABLE` in Trino.

For Druid chart datasources use `INFORMATION_SCHEMA.COLUMNS` / `INFORMATION_SCHEMA.TABLES` instead — see
`references/query-engines.md`. Use the live schema for the query, and on any disagreement with these
references, update the relevant reference file (or state the exact correction if the files aren't
editable).

## Consolidate first, then batch into waves

**Consolidation comes before batching** — see "Query consolidation" in `references/query-engines.md`. Prefer
one statement per (datasource, variant): where two statements would differ only by a filter value or an
adjacent date range, merge them into a `GROUP BY`. So **an adjacent current + prior period is normally one
statement**, and a freshness check is read off that statement rather than fired separately.

**Split when merging would need cleverness** — per-slice filters, per-slice rollup pins, per-slice windows,
non-contiguous ranges, conditional aggregation. That is a normal outcome, not a compromise. Also always
separate: each side of a cross-variant ratio (Druid cannot join variants), each distinct datasource, and
**anything that would cross engines** — Druid and Trino are separate connections with no join between them.

Batch what remains into waves of ~5 submitted and polled together; **a wave may mix Trino and Druid**.
Sequential only for true dependencies: `chart_config` resolution before that chart's first Druid query,
drill-down L1 before L2, maturity-dependent dX choices. ~5 per wave matches engine concurrency; larger
waves just queue server-side.
