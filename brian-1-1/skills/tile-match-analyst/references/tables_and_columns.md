# Tile Match (zenconnect) — raw tables & column semantics

This is the **event-level / feature-level** layer for Tile Match (GID 26, codename `zenconnect`,
internal client folder/table prefix `play_zenconnect`). It sits underneath the Druid `chart_XXXX`
KPI layer documented in `ps-data-catalog` — use this layer when a question needs a specific
in-game action, a specific dialog/popup, a specific live-ops event, or a funnel/behavioral cut that
no `chart_XXXX` datasource carries a dimension for. See `SKILL.md` for when to use which layer.

All 19 source queries this reference was built from were written in **Trino/Presto SQL**, run against
Delta-lake tables. If you execute them through the Databricks SQL plugin, several functions need
translating — see "SQL dialect" at the end of this file.

## The core event stream: `k`/`p`/`c`/`o`/`f`/`g`/`s`

The main raw event table is **`sub_tables.tracking_slice_zenconnect_trino`** (a related, possibly
US-scoped slice appears as **`zenconnect.puzzle_master_cc_us`** in a few older queries — confirm row
counts/date coverage before assuming it's the full population; when in doubt use
`tracking_slice_zenconnect_trino`). Analysts also spin up **`adhoc_analysis.<username>_<timestamp>`**
scratch tables with the same schema for one-off pulls — treat those literal table names as
non-reproducible; rebuild the equivalent query against `tracking_slice_zenconnect_trino` yourself.

Every row is one client/server tracking call. Columns:

| Column | Meaning |
|---|---|
| `date_field` | Calendar date (IST) the event was attributed to. Primary date filter/grain. |
| `cc_local` | Epoch seconds, used to derive `date_field` client-side in some queries (see IST gotcha below). |
| `cc` | A **monotonically increasing per-event sequence number**, not a timestamp. This is the backbone of every funnel/ordering query in this codebase — `LEAD(cc)`/`LAG(cc)` and `BETWEEN cc AND next_cc` windows are how "what happened between two views" gets computed. Don't treat it as time; treat it as "happened-before/after" ordering only. |
| `rid` | User id (matches `rid` on `derived_tables.dau_splits` and elsewhere). |
| `cli` | Platform: 0 = Android, 1 = iOS (2 = Amazon exists platform-wide per `ps-entities`, not seen used in this game's queries). |
| `gid` | Game id — Tile Match is **26**. Always filter/cast `gid`, it's stored as string in places (`CAST(gid AS INT) = 26`). |
| `b` | Build number as a string — queries defensively check `regexp_like(b, '^[0-9]+$')` before casting to INT, implying it's sometimes non-numeric/blank. |
| **`k` `p` `c` `o` `f` `g` `s`** | The seven taxonomy fields — **kingdom, phylum, class, order, family, genus, species**, in that column order. This is the event taxonomy from `Tracking mapping Tile Match.xlsx`. |

### The taxonomy fields are NOT fixed-meaning columns — always look them up

`k` is close to a stable "feature/category" tag (`puzzle`, `dialog`, `home`, `cash`, `session`,
`golden_tile`, `quest_centre`, `store`, `ad_tracking`, `login_streak`, …), and `o` is usually the
specific action/sub-event within that kingdom (`clear`, `view`, `set_clear`, `matches_available`,
`w2e`, `dlr`, …). **Everything past that (`p`, `c`, `f`, `g`, `s`) is heavily overloaded** — the same
column holds a pack/level id for one event and a wallet total, a reward amount, or a free-text status
for another, depending entirely on which `k`+`o` combination the row belongs to.

**Before writing a filter or a `split_part(x, '_', n)` extraction on `p`/`c`/`f`/`g`/`s`, look the
exact event up** in `references/event_taxonomy_full.csv` (filter by kingdom/order, or by `Feature`)
or start from the curated `references/event_feature_index.md`. Never assume a field's meaning
carries over from one event row to the next, even within the same `k`.

**Trust the mapping, but verify on a trigger.** The mapping sheet itself flags known gaps — the
`Comment` column on ~90 of the 731 documented rows says `verified` or `checked`; others say things
like `g field is incorrect`, `this is not coming`, `issue here`, `need to add time here`, or note a
build number where the field changed. Read the comment for any row you're about to depend on, and if
a field looks empty/wrong in a live query where the mapping says it should be populated, that's a
known-tracking-bug candidate, not necessarily your query being wrong — flag it rather than silently
working around it.

## Supporting tables

| Table | Grain | Key columns | Notes |
|---|---|---|---|
| `derived_tables.dau_splits` | one row per (rid, dau_date, gid, cli) | `install_date`, `dau_date`, `country`, `cohort`, `install_source`, `install_bucket`, `install_type`, `actual_diff`, `build`, `dau_build` | The DAU/cohort attribute table. `cohort` needs normalizing (`LIKE 'LD%'` → `'LD120+'`); `install_source`/`install_bucket` need the network-bucketing `CASE` in `query_patterns.md`. Standard hygiene filters: `install_bucket <> 'reject'`, `LOWER(country) <> 'in'` (India is routinely excluded in this game's ad-hoc analyses — confirm with the requester before assuming it should be for a new one), a specific test `rid` (`'yAnDg-jwOk'`) excluded in at least one query. |
| `server_tables.experiments_master_cc_alldata` | one row per (rid, cli, experiment, version, allocation event) | `rid`, `cli`, `gid`, `experiment`, `version`, `variant`, `date_field`, `cs` | Experiment allocation log. **Always dedupe**: `ROW_NUMBER() OVER (PARTITION BY rid[, cli] ORDER BY date_field ASC, cs DESC)`, keep `rn = 1`. `cs` is an undocumented tie-break/priority column — treat it only as the documented sort key, not as a business field. Cast `experiment`/`version` to `VARCHAR` before comparing (both are typed loosely upstream). Android and iOS builds of the same experiment often carry **different `version` values** — the base query template unions an Android branch (`cli IN (0)`, `version_And`) and an iOS branch (`cli IN (1)`, `version_iOS`). |
| `server_tables.dau_master_by_build_cc` | one row per (rid, date_field, cli, gid) | `build` | Used to gate a cohort to a minimum build: `MAX(CAST(build AS INT)) HAVING >= min_build`. |
| `play_zenconnect.content_seeds` | one row per (level, seed, content version) | `level`, `seeds`, `json` (content-set tag, e.g. `'15.1'`, `'15.3'`), `cid`, `cli` | Content catalog — maps levels to the seed(s) live under a given content-set/JSON version. Join this in when an engagement/seed-performance question needs to be scoped to "levels actually live in version X", not just any level id that ever existed. |
| `play_zenconnect.<exp_name>` / `delta.play_zenconnect.<exp_name>[_1/_local/_cc_bucket/_eng/_t/_base/_based]` | scratch, per-analysis | varies | **Not permanent tables.** Every analysis in this codebase starts with `DROP TABLE IF EXISTS ... ; CREATE TABLE ... AS SELECT ...` to materialize a cohort/experiment base population named after the experiment (`${exp_name}$`), then layers suffixed scratch tables on top: `_1`/`_local` = an alternate/ad-hoc-scoped version of the base cohort, `_cc_bucket` = precomputed `cc` windows for a funnel, `_eng` = the wide engagement rollup, `_t` = an intermediate "trigger event" table (e.g. every "0 matches" moment), `_base`/`_based` = streak/day-in-cycle calculations. Follow this convention for a new analysis rather than inventing a different scratch-table shape. |

## SQL dialect — Trino/Presto, not Spark SQL

If you run these patterns through the Databricks MCP tools (`mcp__Databricks__execute_sql*`), the
underlying warehouse is Spark SQL, and the following Trino/Presto-isms need translating — check the
error message against this list before assuming the query itself is wrong:

| Trino/Presto (source queries) | Spark SQL equivalent |
|---|---|
| `split_part(x, '_', n)` | `split(x, '_')[n-1]` (0-indexed) |
| `regexp_like(x, pattern)` | `x RLIKE pattern` |
| `dow(date)` (1=Mon..7=Sun in these queries) | `dayofweek(date)` (Spark: 1=Sun..7=Sat — **offsets differ, don't copy the CASE mapping verbatim**) |
| `date_add('day', n, date)` | `date_add(date, n)` (argument order is reversed) |
| `date_diff('day', d1, d2)` | `datediff(d2, d1)` (argument order is reversed) |
| `from_unixtime(epoch)` | same name, generally compatible |
| `TRY_CAST(x AS type)` | `TRY_CAST` is supported in recent Spark; `CAST` + null-on-error otherwise |
| `row_number() / lead() / lag() OVER (...)` | same — window functions are portable |

## A gotcha worth double-checking before reuse: the IST offset

Several queries derive the calendar date from an epoch column with
`DATE(FROM_UNIXTIME(cc_local - 19800))`. IST is UTC+5:30 (+19800 seconds), so converting a UTC epoch
to an IST calendar date should normally **add** 19800 seconds, not subtract it. This pattern is
copied across several files verbatim, so it may be intentional (e.g. `cc_local` might already be
stored pre-shifted), but it's exactly the kind of off-by-11-hours bug that silently shifts a date by
one day for events near midnight IST. If a query's `date_field` (already correct, computed
server-side) and a `DATE(FROM_UNIXTIME(cc_local - 19800))` recomputation ever disagree, trust
`date_field` and flag the discrepancy rather than assuming the epoch math is right.

## Template placeholder convention

Every query in this library is parametrized with dollar-terminated placeholders, resolved before
running: `${exp_name}$`, `${start_date}$`, `${end_date}$`, `${expt_start_date}$`, `${cli}$`, `${gid}$`
(almost always `26`), `${min_build}$`, `${build}$`, `${version}$` / `${version_And}$` /
`${version_iOS}$`, `${variant_name}$`, `${country}$`, `${cid}$`, `${diff}$`. Keep this convention when
adapting a template so the query stays diffable against the original.
