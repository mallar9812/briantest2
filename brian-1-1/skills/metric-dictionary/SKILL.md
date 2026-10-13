---
name: "metric-dictionary"
description: "Generates a metric-and-dimension data dictionary for a Databricks table, rendered as a tab-separated, gsheet-paste-ready block (usage note + \"WHAT'D YOU USE IT FOR\" ref line, then Metric_type / Name / Formula / Description METRICS rows, plus separate DIMENSIONS, DATASOURCES, and GLOSSARY sections). Give it a table name and/or the SQL that defines the table/chart, and it queries Databricks to inspect real columns, sample data, and distinct dimension values, then reads the SQL to classify each column as Normal (raw) or Custom (derived formula) and write grounded descriptions. Use whenever the user pastes a Databricks table name and/or SQL query and asks to document it, describe its metrics/dimensions, build a data dictionary, list what a table/chart contains, or explain query fields — even without saying \"skill\" or \"dictionary\". Trigger on \"describe this table\", \"what metrics does X have\", \"document this query\", \"data dictionary for X\", or a table name + query pasted together."
---

# Metric Dictionary Builder

You are documenting a Databricks table for other analysts and for downstream
agents (like the game-performance-verdict skill) that will query it without
any other context. A vague or guessed entry causes wrong numbers downstream —
so every row must be grounded in something you actually saw, either in the SQL
or in the live data.

## Inputs

The user will typically give you one or both of:
- **Table name** — a Databricks table (e.g. `play_data.Revenue_dataset`) you can query directly via the Databricks connector.
- **Query** — the SQL that defines the table or the chart built on top of it (grain, joins, filters, derived columns).

If only a table name is given, query it yourself (`DESCRIBE`, `LIMIT` samples, `DISTINCT` on likely dimension columns) before writing anything — don't guess a schema from the name alone. If only a query is given with no live table access, document strictly from the SQL and mark anything you'd normally verify against live data as unconfirmed. If both are given, use the query to explain *why* a column looks the way it does, and use the live data to confirm actual values, cardinality, and edge cases (nulls, unexpected categories) the SQL alone doesn't show.

## Step 1 — Investigate before writing anything

1. **Run `DESCRIBE TABLE <table>`** (or read the SELECT list of the given query) to get every output column.
2. **Sample the data**: `SELECT * FROM <table> LIMIT 50` (or run the given query with a `LIMIT`) to see real values — this is how you catch things like a dimension being 0/1/2 coded rather than a string, or a metric that's actually always null for a given segment.
3. **For each column that looks categorical** (low-cardinality string/int, used in GROUP BY or as a filter key), run `SELECT DISTINCT <col> FROM <table> LIMIT 50` to see its actual value set — don't describe a dimension's possible values from assumption.
4. **Read the SQL logic** (if given) for: GROUP BY / grain, every JOIN (and whether it's 1:1 or fans out), every WHERE/HAVING filter, and which SELECT expressions are raw columns vs computed (division, window function, CASE, aggregation of another aggregation).
5. **Classify every measure as Normal or Custom**:
   - **Normal** — a raw column, or a straight `SUM`/`COUNT` of one field with no combination of other fields.
   - **Custom** — anything derived: a ratio, a percentage, a `CASE WHEN`, a window function, a formula combining two or more other fields.
6. **Check for schema-evolution artifacts**: when a column looks like it should never be NULL per the current SQL (a `CASE` with no null-producing branch, a hardcoded literal, a `COALESCE`/`NVL` default) but `DISTINCT`/live data shows NULL anyway, quantify it — run a `COUNT(*)` / `SUM(CASE WHEN col IS NULL ...)` share across the whole table. This is usually a sign the column was added or the logic changed partway through the table's history, and older rows predate it. That share (e.g. "NULL on ~46% of rows") is exactly the kind of thing that silently breaks a downstream agent's query if left undocumented.

Do this investigation silently — don't narrate it to the user. Only the final block matters.

## Step 2 — Classify columns into Metrics vs Dimensions

- **Metric**: a numeric measure someone would aggregate, chart, or set a target against (revenue, installs, retention rate, ROAS, spend).
- **Dimension**: anything used to slice, filter, or group metrics — platform, country, source, date, IDs, categorical codes. Dates and IDs count as dimensions even though they may look technical.

If a column is genuinely ambiguous (e.g. a count that's sometimes used as a slicer), put it wherever it's used in the given query and note the ambiguity in its description rather than silently picking one.

## Step 3 — Write the usage note + "WHAT'D YOU USE IT FOR" ref line

Before the metrics table, write two things, in this order:

1. A single-line usage note in the form: `Note: always use <default filter/assumption> unless explicitly asked` — the one most important default a query-writer needs before touching this table. This is often: a hardcoded literal column (e.g. `install_type = 'NA'`), a dimension that should default to an aggregate/rollup value (e.g. `adnetwork = 'overall'`), or the single biggest gotcha you found in Step 1.6. Ground it in something you actually saw — never invent a plausible-sounding default. Skip this line entirely if nothing in the table/query warrants a default-usage instruction.
2. A `WHAT'D YOU USE IT FOR` header, then a `ref:` row (tab-separated: literal text `ref:` in the first cell, the description in the second) — 2-4 sentences on what the table/chart is for, its grain (what one row represents), and its base population, in the voice of a human-written team reference doc, not a schema dump.

## Step 4 — Write the Metrics rows

Group metrics into sections the way a human reference doc would when there are enough of them to warrant it — by metric family (e.g. "CORE METRICS", "LTV", "RETENTION", "ROAS", "RAW METRICS / inputs to the above"). Write each family name as its own plain line (no markdown `##`, just the label) directly above the rows it covers. Skip grouping entirely for a small/single-metric table — one flat list under `METRICS` is fine.

Exact column order and header, tab-separated:

```
Metric_type	Name	Formula	Description
```

- **Metric_type**: `Normal` or `Custom` (Step 1.5).
- **Name**: the human-facing metric name (e.g. `D7 LTV`), not the raw SQL alias, unless they're the same.
- **Formula**: for Normal metrics, just the column/field name (e.g. `revenue`). For Custom metrics, the formula using `{field}` placeholders for every input, e.g. `{overall_rev_d7}/{installs}` — never inline a raw SQL fragment here, keep it in the clean placeholder notation.
- **Description**: one tight sentence — what it measures, over what population/window, in business language. Include a caveat only when it's specific and non-obvious (e.g. "ignore this filter when querying DAU — the column doesn't exist in that table"); don't pad a clean metric with a manufactured caveat.

If any Custom metric formula references a raw field that isn't itself documented as its own Metric row, add a final `RAW METRICS (inputs to the above formulas)` family listing those raw fields — a Custom formula is unusable to a downstream agent if `{overall_rev_d7}` is never itself defined.

## Step 5 — Write the Dimensions rows

Under a `DIMENSIONS` header, tab-separated:

```
Dimension name	Description
```

Each description should state: what it identifies, its coding scheme if not self-evident (e.g. "android=0, iOS=1, Amazon=2" — confirmed via `DISTINCT`, not assumed), and any warning a query-writer needs — a bucket/rollup value that must be pinned before summing, a column that should be ignored, a value that only exists in some source tables and not others, a legacy/schema-evolution null share found in Step 1.6. If you queried `DISTINCT` values, use what you actually saw to write the coding scheme — don't guess numeric codes.

## Step 6 — Write the Datasources rows

Under a `DATASOURCES` header, tab-separated. This section doubles as the catch-all for any gotcha that doesn't fit cleanly in a single Description cell — not just literal cross-table sourcing:

```
Metric/Dimension	Datasource or Issue	Notes
```

Always include a row for: a same-named field that behaves differently or doesn't exist across related tables/queries, a hardcoded literal that overrides historical values, a column with a meaningful legacy-null share (name the approximate percentage), an output column whose name doesn't match what it actually holds (e.g. "this `build` column is the experiment's minimum qualifying build, not the user's own device build"), and how this table relates to sibling tables that share its lineage (e.g. "this is the diff=0 slice of the same source as X"). This section is the single highest-value thing for preventing a downstream agent from writing a broken query — don't skip it even if it feels repetitive with a Description cell above.

## Step 7 — Glossary (only if needed)

If the query or data uses an internal/domain-specific term that isn't self-explanatory (e.g. "Xpromo" for cross-promotion, "LAT" for Limited Ad Tracking), add a `GLOSSARY` header with tab-separated `Term	Meaning` rows. Skip this section entirely if there's no jargon to define — don't manufacture entries.

## Grounding rules (non-negotiable)

- Every claim traces to something you actually queried or read in the SQL. If you can't confirm something (e.g. no live table access and the SQL doesn't settle it), say so in the Description rather than guessing — "coding scheme not confirmed, only seen as {values} in the SQL" beats inventing a clean answer.
- Never state a dimension's value set from assumption when you have query access — go run the `DISTINCT`.
- Don't manufacture a caveat, a Glossary entry, or a Datasources row just to fill the section — empty/short sections are fine when there's genuinely nothing to flag.
- No banned filler: avoid "this table contains", "various metrics", "useful for analysis", "provides insights", "key performance indicators" — describe what the number/dimension actually is and where it comes from.
- Keep Formula cells in clean `{field}` placeholder notation, not raw SQL — that's what makes the table usable as a lookup reference, not a code dump.

## Output

Render the entire result as **one tab-separated block inside a single code fence** — never as markdown tables (`| col | col |`). Tabs, not pipes, are what makes a straight copy-paste land cleanly in Google Sheets cells. Structure, top to bottom, with a blank line between sections:

1. The usage `Note:` line (Step 3.1), if there is one.
2. `WHAT'D YOU USE IT FOR` header, then the `ref:` row (Step 3.2).
3. `METRICS` header, then family labels (if grouped) and `Metric_type / Name / Formula / Description` rows (Step 4).
4. `DIMENSIONS` header, then rows (Step 5).
5. `DATASOURCES` header, then rows (Step 6) — include whenever there's a real gotcha, which is nearly always.
6. `GLOSSARY` header, then rows (Step 7) — only if needed.

Default to showing this block inline in chat first so the user can sanity-check it. If they want it saved, offer a `.tsv`/`.csv` file or to drop it straight into a spreadsheet — but don't create a file unprompted.

## Check before returning

1. Every column from the table/query schema is accounted for in either Metrics or Dimensions — none silently dropped.
2. Every Custom metric's formula only references fields that are themselves documented (in Metrics or the Raw Metrics family).
3. Every dimension with a numeric/coded value set has that scheme confirmed via `DISTINCT`, not assumed.
4. Datasources section flags every case where a same-named field behaves differently or doesn't exist across tables, every hardcoded literal, and every meaningful legacy-null share found in Step 1.6.
5. No banned filler phrases anywhere; no description just restates its own column name.
6. Output is plain tab-separated text in one code fence — no markdown pipe tables anywhere in the response.

