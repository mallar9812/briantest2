# Annotations — the "what changed" layer

**Table: `play_data.charts_annotations`** — the annotation source. Two similarly-named tables are not
(see "Do not query" at the bottom).

Annotations are dated notes pinned to a metric chart explaining why a line moved: a build rollout, an
experiment allocation ramp, an ad-stack optimisation, a runtime config flip, an open investigation. This
is the **narrative** counterpart to every metric datasource in the catalog — the only place in Playsimple
analytics that records *cause*. Everything else says a number changed; this says what changed alongside it.

**Engine: Trino.** There is no Druid chart for annotations — no `chart_config` row, no version, no
variant suffix — so `references/query-engines.md` Steps 1–3 do not apply and must not be attempted here.
Query it as an ordinary Trino table, named `play_data.charts_annotations` with no catalog prefix. It is
the 4th sanctioned Trino read alongside `chart_config`, `monthly_rev_diff`, and the two Sensor Tower
tables.

**Annotations are commentary, never a metric.** Never count them as an outcome, never present a figure
quoted inside an annotation's text ("BN RPD: +8.77%") as a queried number, and never let an annotation
replace a metric query. An annotation tells you where to point Procedure B; the number still comes from a
chart datasource.

**Coverage bounds are a moving target — read them live, never from this file.** This table is
backfilled and extended, and its earliest row has already moved earlier than previously documented.
**Before writing that any window is outside coverage, run the bounds and quote what came back:**

```sql
SELECT MIN(from_unixtime(created_at)) AS earliest,
       MAX(from_unixtime(created_at)) AS latest,
       COUNT(*) AS n_rows
FROM play_data.charts_annotations
```

(`rows` is reserved in Trino — alias the count `n_rows` or quote it.)

Then say the accurate thing, choosing between three different statements:

- **outside the live bounds** — the probe shows the window predates `earliest` (or postdates `latest`);
  quote the bound.
- **covered, nothing returned** — the window is inside the bounds and the scoped pull came back empty.
- **covered, and coverage is voluntary** — annotations are notes people and deploy scripts chose to
  write, so silence is never proof that nothing changed (see rule 6 under "How to use annotations").

Reporting a window as uncovered on this file's authority instead of the probe's suppresses the entire
evidence layer for that investigation — the most expensive single error available on this table
(SR-20). A "no coverage" claim without a quoted probe is not a finding.

---

## Rollups & mandatory pins

**None.** No dimension here carries an `'overall'`/`'others'` rollup value and there is no mandatory pin —
`category`, `features`, `gid` and `cli` all group normally. What inflates counts on this table is row
duplication, not rollup rows: see "Hard rule 1 — de-duplicate before counting anything" below, which is a
different problem with a different fix.

## Columns

> **Snapshot, not a bound.** The profile line below — row counts, distinct-ID counts, gid count, id
> ranges and date span — was true when this file was written and drifts continuously. Use it to
> recognise the table's shape and rough scale. **Never cite it as a figure, and never let it establish
> that a row, a gid or a date range does not exist** (SR-20): that always takes a live probe.

Live profile (snapshot): ~20k rows, near-1:1 distinct `annotation_id`, ~45 gids, spanning roughly two
and a half years to the present.

| Column | Type | Notes |
|---|---|---|
| `annotation_id` | BIGINT | Range 86,804–107,048. Near 1:1 with rows — this is **not** an event log; there is no `status`, no update or delete history. Append-only. |
| `category` | STRING | The event type. Eight values, capitalised — see the category table below. This is the primary filter. |
| `features` | STRING | **Plural.** Free-text feature/system. Heavily fuzzy — normalise before grouping (see below). |
| `description` | STRING | The payload for narrative categories, machine-formatted for the rest. **Blank on 7,133 of 12,937 `Runtime` rows** — for those the change is only in `data`. |
| `data` | STRING | **Never blank** — every row has one. Python-repr, *not valid JSON* (single quotes), so `json_parse`/`from_json` fail. Shape: `{'objectsAffected': [...], 'values': {...}, 'action': ''}`. Read as text or regex it. |
| `created_at` | **BIGINT** | **Unix epoch seconds, not a date.** Always wrap: `from_unixtime(created_at)`. This is the event time **and** the business date — there is no separate `annotation_date` here. Only usable ordering column. |
| `created_by` | STRING | Email, or the literal **`Developer`** for machine-generated rows. Unlike some annotation stores, this **is** a real authorship signal — see below. |
| `auto_created` | BOOLEAN | This table's stand-in for a `source` column. `true` on 20,237 rows; **`false` marks the 28 hand-written rows** (18 `Investigation`, 7 `Admon`, 3 `Content`). |
| `gid` | BIGINT | 45 distinct, range 0–60. Standard GID scheme → `ps-entities`. Four values fall outside what `ps-entities` maps — see the entity warning. |
| `cli` | BIGINT | `0` Android (10,195), `1` iOS (7,474), `2` Amazon (1,525), **`3` (728)**, **`5` (343)**. |
| `inserted_at` | TIMESTAMP | ETL load stamp — two near-identical values across the entire table. **Not an event time.** Never order or filter on it. |

No `status`, no `annotation_date`, no `source`, no `updated_at`, no `team`. Do not write queries that
reference them.

---

## Hard rule 1 — de-duplicate before counting anything

Three separate mechanisms inflate row counts. All three are live and all three make a naive
`COUNT(*)` wrong. **Never quote a raw row count as a number of changes.**

**(a) Platform fan-out.** One logical change is written **once per `cli`**. The same `description` and
`created_at` appear on `cli` 0 and 1 with adjacent `annotation_id`s. Counting rows counts platform-rows.
De-duplicate on (`description`, `created_at`, `gid`) — or `array_agg(DISTINCT cli)` to show which
platforms a change hit, which is usually the more interesting answer anyway.

**(b) `Investigation` re-stamps daily while the issue is open.** Confirmed live: `CMP Resurface in EU & UK`
on gid 50 appears **42 rows across 40 distinct days**, 2026-03-12 → 2026-07-25 — and the same subject
recurs independently on gids 35, 36, 37, 41, 42, 45, 48, 49, 50, 51, 52, 55. These are not 42 events.
**Collapse `Investigation` to (`description`, `gid`) and read `MIN`/`MAX` of the timestamp as the window
the issue was open** — that span is the useful output, far more than any count. An investigation whose
window brackets your metric move is a known issue, and it belongs in the answer as such.

**(c) `Releases` re-stamps per rollout step.** Same version, successive percentages — that is signal, not
duplication (see the rollout ladder below). Keep those rows distinct; just don't call them separate builds.

**(d) Same-second near-duplicates.** Genuine repeats exist — two `Admon` rows for gid 26 seconds apart
both reading `Wrong Entry created Ramping down`. Annotation text openly flags its own mistakes
(`Wrong entry created`, `(Ignore)`, `Wrong Runtimes were pushed`). **Read the text before quoting a row**;
never report an annotation the author labelled as an error as if it were a real change.

## Hard rule 2 — `created_at` is epoch seconds

`from_unixtime(created_at)` on every read, filter, and group-by. A bare comparison against a date literal
silently returns nothing or everything. `inserted_at` is not a substitute — it is a load stamp with two
distinct values table-wide.

## Hard rule 3 — normalise `features` before grouping

Free text, and the collisions are large enough to reorder any ranking. Under `Experiments` alone:
`Admon Experimentation` (971) · `Admon Experimentations` (158) · `Admon Experiment` (57) ·
`Admon Experimentaion` (50) · `Admon experimentation` (20) — **1,256 rows of one concept across five
spellings**. Also `gameplay` (86) / `Gameplay` (69) and `content` (129) / `Content` as case-only pairs.

Always lowercase + trim + fuzzy-match before any group-by, and say you did. Treat `default` (39), `na`,
`others`, `misc`, `event`, `home` and empty string as **unspecified**, not as features.

Real values worth recognising: `Admon Stack Opts`, `Ads`, `Ads Optimisations`, `PSPN Adwall`,
`PSPN Quests`, `Backup Xpromo`, `Aggressive Xpromo`, `LPM Rotation`, `Content Infra`,
`Content Personalization`, `Leaderboard`, `Iap`, `Open Quest`, `Word Master`, `Word Duel`, `Outro`,
`DT Compliance`, `Mid Level Gratification V2`, `W2e Coin Jar`, `Daily Challenge`, `Hidden Temple`,
`Rule Toggle`, `Skill Logic`, `Quest Center`, `Daily Goals`.

## Hard rule 4 — `created_by` and `auto_created` split machine from human

Unlike other annotation stores in the warehouse, authorship here is meaningful:

- **`created_by = 'Developer'`** (1,335 rows) is the machine marker, and it covers essentially all of
  `Releases` and `Investigation`. Never name it as an author.
- **Real engineer emails** author `Runtime`, `Experiments` and `Admon`: `pravasbehera@` (1,765),
  `dikshitbhandary@` (1,230), `zorawarsingh@` (1,143), `aashishkalra@` (1,138), `atishayjain@` (607),
  `abhisheksingh@` (584), `kushagramishra@` (575) …
- **`auto_created = false`** isolates the **28 deliberately hand-written rows** (18 `Investigation`,
  7 `Admon`, 3 `Content`). These are the highest-signal rows in the table — a human chose to write them.

## Hard rule 5 — unmapped entities get raw codes, not guesses

`gid` present: 0, 4, 8, 9, 10, 11, 14, 15, 17, 20, 21, 22, 24, 26, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37,
38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 57, 58, 60.

**Four fall outside the GID range `ps-entities` documents (4–55): `0`, `57`, `58`, `60`.** And `cli`
carries **`3`** and **`5`** beyond the documented 0/1/2. Report an unmapped `gid` as "gid NN (unmapped)"
and an unknown `cli` by its raw code. Never invent a game name or a platform for them, and never silently
drop those rows — 1,071 `cli` 3+5 rows is real activity.

---

## Categories

> **The Rows and gids columns are a snapshot** — relative scale, not current counts, and they grow with
> every backfill. Use them to judge which categories are dense and which are rare. Never quote one, and
> never conclude from a low count that a category is unlikely to hold anything for your window (SR-20).

| Category | Rows | gids | `description` format | Explanatory value |
|---|---|---|---|---|
| `Runtime` | 12,937 | 39 | `<config_key> [<param>: <old> to <new>],[…]` — e.g. `i2 [interstitialCooldown: 180-180 to 180-150],[interstitialCooldownAfterRV: 165 to 30]`. **55% blank** → payload in `data`; 6,773 rows carry `segmentGroup`, meaning the change was scoped to a segment, not global. | High volume, low signal per row. Filter it out unless the question is about a specific config or nothing else explains the move. |
| `Experiments` | 5,166 | 36 | `<exp_name>:\n[control: <old>% to <new>%],:[var<N>: <old>% to <new>%]` — an **allocation ramp**. e.g. `pawzzle_theme:\n[control: 0% to 50%],:[var1: 0% to 50%]` | **Strong.** Read the *delta* in allocation: 0%→50% is a real exposure change; 0%→0% is a no-op that shouldn't move anything. **A terminal 100% is a verdict, not just exposure** — see the interpretation rule below. |
| `Releases` | 1,099 | 37 | `<major>.<build>.<patch>:<rollout %>` — **`1.282.0:100%` means build 282 at 100% rollout.** The `%` is any staged value (`20%`, `50%`, `100%` all live). Bare `1.4.0` with no `%` also occurs. | **Strongest single signal.** See the rollout ladder below. |
| `Admon` | 718 | 22 | Free-text human narrative, `\|`-separated updates, often carrying claimed PAB reads. e.g. `Started Stack Opts \| Re-opts + Native placement fix done on 23 July \| Ramped up \| BN RPD: +8.77%` | **Strong and quotable** — the closest thing to an analyst's own write-up. Attribute it; never treat its numbers as data. |
| `Investigation` | 254 | 32 | Short subject line, **re-stamped daily while open**. e.g. `CMP Resurface in EU & UK` | **Strong once collapsed** — the min/max span is the issue window. A move inside that window has a known candidate cause. |
| `Server-Build` | 70 | 1 | Deploy marker. | Low — single gid. |
| `JSON Publisher` | 18 | 4 | Config publish event; real `data` payload. | Situational. |
| `Content` | 3 | 1 | The only category where **all** rows are `auto_created = false`. | Low volume, hand-written. |

### Reading an `Experiments` allocation ramp — 100% is a verdict, not just exposure

Any arm landing at **100%** collapses the experiment to a single group — but *which* arm reads
opposite verdicts, so never report a terminal 100% row as a plain "experiment ended":

- **If a `control` arm exists in the ramp:**
  - `control` ramped to **100%** → the experiment was **taken out of the game** — traffic sent back
    to control because the treatment(s) didn't perform as expected.
  - **Any non-control variant** ramped to **100%** → that variant **won and fully shipped** and is
    now serving all users.
- **If no `control` arm exists** (only numbered variants, e.g. `var1`, `var2`, `var3`):
  - The **smallest variant** ramped to **100%** → reads the same as control @ 100% — the experiment
    was **killed / rolled back**, it underperformed.
  - **Any variant other than the smallest** ramped to **100%** → that variant **won and fully
    shipped**.

Put another way: a genuine full rollout to 100% of users is only signalled by a *non-control* arm
(when control exists) or by any arm *except the smallest* (when it doesn't) — control, or the
smallest variant, sitting at 100% always reads as a rollback, never a ship. Get this backwards and
a kill reads as a ship (or vice versa) in every downstream "what changed" answer.

**This is a fixed decision rule — never re-derived, never overridden by other evidence.** The two
bullet cases above are exhaustive; there is no third case where the label is "probably a naming
quirk" and something else gets to decide instead. Two specific failure modes have actually
occurred and both are prohibited:

- **"It's the experiment's only/first annotation row, so there's no prior live-variant state to
  roll back from."** Not a reason to read control-at-100% (or smallest-variant-at-100%, with no
  control) as anything but a kill. The rule reads the **arm name and the terminal percentage**,
  not the row's position in a longer history. An experiment whose *only* recorded row jumps
  straight from non-existent to `control: 0%→100%` is still a kill by this rule — do not wait for
  a second row that never comes, and do not treat "no earlier row exists" as evidence the ramp
  must mean something else.
- **"The production data in the same window looks like a launch (or a rollback), so the label
  must be backwards here."** A metric's shape in the correlated window — a new `ad_type` or
  feature appearing at zero and ramping to plateau, a step-change lining up with the annotation's
  timestamp, matching timestamps across two related experiments — is corroborating evidence for
  **when** something happened. It is **never** grounds to flip **which arm the rule says won**.
  If the metric data seems to contradict the arm-based verdict, the correct conclusion is that the
  observed metric behavior belongs to whichever arm the rule names as the winner — never that the
  rule has an exception here. Do not reason backward from a time-series shape (0 → ramp → plateau,
  or the reverse) to relabel which of the annotation's arms actually won.

Apply the rule to each experiment name independently, even when two experiments ramp at the exact
same `created_at` (e.g. a feature experiment and its companion tracking-infra experiment shipping
together) — a shared timestamp is never license to borrow one experiment's data-driven story to
reinterpret the other's verdict.

State the verdict (killed vs. shipped) in the same sentence as the allocation delta every time a
terminal 100% appears — never present the raw percentages alone and leave the reader to infer it,
and never soften it to "may have been a launch" once the arm and percentage are read.

### The `Releases` rollout ladder

The most useful pattern in the table. The same version reappears at successive percentages days apart
(`:20%` → `:50%` → `:100%` — live: `1.282.0:20%` on gid 22, 2026-07-10), giving every edge of a staged
rollout. When a metric moves, check whether a build stepped up inside the window — and **read the step
size**: a 20%→50% ramp should move a metric roughly 2.5× harder than that build's earlier 0%→20% step. A
metric that jumps on a rollout step but not in proportion to it is evidence *against* the build being the
cause. That test is cheap and it kills a lot of false attributions.

### Reading `data` when `description` is blank

`Runtime` and `Experiments` carry the real change in `data`; the shape is
`{'objectsAffected': ['<key>'], 'values': {…}, 'action': ''}`. For `Releases`, `Admon`, `Investigation`,
`Server-Build` and `Content`, `data` is a shell (`objectsAffected: None, values: None, action: ''`) and
`description` is the whole payload — so never go looking in `data` for those. Because `data` is
single-quoted Python repr, extract with string ops:

```sql
regexp_extract(data, '''objectsAffected'': \[([^\]]*)\]', 1) AS objects_affected
```

**The pattern is a single-quoted Trino string literal** — the regex's own single quotes are doubled
(`''`), and backslashes pass through literally because Trino string literals don't process escapes. Writing
it in double quotes makes Trino read it as an identifier and the query fails.

Verified live (Sep 2026): returns the changed config key **with its surrounding single quotes** (`'iobdl'`,
`'22$prr1_i'`, `'psgid_i'`) — strip them if you're displaying it. On the narrative categories
`objectsAffected` is `None` rather than a list, so the same expression returns **NULL** (Trino), not an
empty string — `coalesce(…, '')` if a blank reads better. Either way that is the expected result there,
not a parse failure. Don't attempt `from_json` / `json_parse` — it fails on every row.

---

## Query shape

```sql
-- ops timeline for one game, platform fan-out collapsed
SELECT MIN(from_unixtime(created_at))         AS event_ts,
       category,
       lower(trim(coalesce(features,'')))     AS feature_norm,
       description,
       array_agg(DISTINCT cli ORDER BY cli)   AS platforms,
       bool_or(auto_created)                  AS auto_created
FROM play_data.charts_annotations
WHERE gid = 22
  AND from_unixtime(created_at) >= TIMESTAMP '2026-06-28'   -- window widened ±3 days
  AND from_unixtime(created_at) <  TIMESTAMP '2026-08-04'
  AND category IN ('Releases','Experiments','Admon')   -- Runtime excluded: high volume, low signal
GROUP BY category, lower(trim(coalesce(features,''))), description
ORDER BY event_ts
```

```sql
-- open-investigation windows (collapse the daily re-stamps)
SELECT gid, description,
       MIN(date(from_unixtime(created_at))) AS opened,
       MAX(date(from_unixtime(created_at))) AS last_seen,
       COUNT(DISTINCT date(from_unixtime(created_at))) AS days_open
FROM play_data.charts_annotations
WHERE category = 'Investigation' AND gid = 50
GROUP BY gid, description
ORDER BY opened
```

Three Trino details in those shapes, all verified live (Sep 2026): **timestamp comparisons need a typed
`TIMESTAMP '…'` literal** (a bare string does not cast), **`bool_or()` replaces `max()` over a boolean**
(`max(boolean)` is not a valid Trino signature), and **`COUNT(DISTINCT …)` is exact here** — the Druid
approximation warning in `query-engines.md` does not apply to this table. `gid` and `cli` are `BIGINT`:
compare them unquoted.

Filter `category` whenever the question is scoped — pulling all of `Runtime` for a busy game returns
thousands of config flips and buries the release and experiment events that actually explain a move.

---

## How to use annotations in an analysis

Annotations attach to the **explanatory layer of any drill-down** (the analyst layer's "why did X move"
procedure). Once a
drill-down has localised a move to a segment and a window, pull the annotations for that `gid`/`cli`/window
and see what changed there. Order of explanatory power: **`Releases`** (build stepped up) →
**`Experiments`** (allocation ramp, read the delta) → **`Admon`** (stack opts) → **`Investigation`**
(already-known issue, check the window) → **`Runtime`** (config flip) → **`Server-Build`**.

1. **Widen the window by ±3 days.** Effects land with a lag and a rollout takes days to propagate; an
   exact-window filter misses the cause more often than it finds it.
2. **Correlation, never causation** — the same standard as every other analytical observation.
   "Build 1.282.0 stepped from 20% to 50% on Jul 14, two days before
   the eCPM step-down" — never "caused by". Where a rollout ladder is available, test proportionality
   before asserting even a correlation.
3. **Quote it, attribute it, keep it out of the metric rows.** Annotation text is evidence about cause; it
   is never a figure in a KPI table, a delta, or a chart series.
4. **Check the text for self-flagged errors** before quoting — `Wrong entry created`, `(Ignore)`,
   `Wrong Runtimes were pushed` all appear, and reporting one as a real change is worse than reporting
   nothing.
5. **Say when there are none — and say why, with the probe behind it.** "No annotations for this
   gid/window" is a real finding *once the window is confirmed inside the live bounds*. Outside them,
   the honest statement names the bound the probe returned. Never assert either from this file's
   documented span — check first (SR-20).
6. **Coverage is never complete.** These are notes people and deploy scripts chose to write. Absence of an
   annotation is not evidence that nothing changed — state that when an explanation comes up empty.

## Do not query

- **`play_data.charts_annotations_data`** — a separate, older human-note store (1,092 rows, 2021→). Not
  this table, not a superset, and **not the annotation source for this catalog**. It has different columns
  (`aid`, `status`, `annotation_date`, `feature` singular, `source`, `updated_at`/`updated_by`) and none of
  the rules above apply to it. Do not query it, do not join it, and do not fall back to it — including for
  windows that fall outside the sanctioned table's live bounds, where the correct answer is the bound the
  probe returned, not a substitute source.
- **`play_data.annotations_data`** — **empty, 0 rows**, despite the richest schema (adds `team` and an
  `updated_time` TIMESTAMP). Never query, never cite.

Both names are one suffix away from the real table. Re-read the table name before running any annotation
query.

## Pre-query checklist (annotations)

1. Neither other annotation table touched?
2. No `chart_config` / version / variant lookup attempted; no reference to `status`, `annotation_date`,
   `source` or `updated_at` (they don't exist here)?
3. `created_at` wrapped in `from_unixtime()` everywhere; `inserted_at` used for nothing?
4. Window widened ±3 days around the metric move, and `category` scoped (Runtime excluded unless
   specifically relevant)?
5. Platform fan-out collapsed, `Investigation` reduced to (description, gid) windows, and no raw row count
   quoted as a number of changes?
6. `features` lowercased, trimmed, fuzzy-matched, with `default`/`na`/`others`/`misc`/blank treated as
   unspecified?
7. Self-flagged error rows (`Wrong entry created`, `(Ignore)`) read and excluded before quoting?
8. `created_by = 'Developer'` never named as an author; `auto_created = false` rows recognised as the
   hand-written high-signal set?
9. Unmapped `gid` (0, 57, 58, 60) and unknown `cli` (3, 5) reported as raw codes — not guessed, not
   dropped?
10. Live coverage bounds probed **before** any "outside coverage" claim, and the probe's result quoted —
    never this file's documented span used as the authority (SR-20)?
11. Every annotation presented as attributed commentary — correlation not causation, no quoted figure
    passed off as queried data?
