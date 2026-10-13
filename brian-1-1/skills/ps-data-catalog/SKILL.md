---
name: ps-data-catalog
description: "Playsimple context layer — DATA CATALOG. Routing index for every datasource, metric formula, dimension, filter rule, grain, query template and glossary term. Druid is the default engine: nearly every metric comes from a versioned chart_XXXX datasource resolved from play_data.chart_config (variant suffix sorted alphabetically). Trino serves chart_config, monthly_rev_diff, the Sensor Tower tables, play_data.charts_annotations and the user-level-data (ULD) layer — eight warehouse tables for distinct-user, per-user-distribution, segment-combination and campaign/creative questions no chart answers. Domains: core KPIs, cohorts, predictions, revenue drill-downs, ad monetization, engagement, economy, crashes, notifications, competitors, annotations (what changed / shipped). Load before any Playsimple analytics query, before computing or explaining a metric or dimension, when asked which datasource holds something, or why a chart moved. Companion: ps-entities."
---

# Playsimple Data Catalog

Routing index. **Druid is the default engine — nearly every metric is served by a versioned chart
datasource resolved from `play_data.chart_config`. Trino serves four chart-adjacent things —
`chart_config` itself, `play_data.monthly_rev_diff`, the two Sensor Tower tables, and
`play_data.charts_annotations` — plus the user-level-data (ULD) layer for questions no chart can answer
(`references/uld.md`).** Read
`references/query-engines.md` before the first query of any conversation. Then find the domain below and
read only the reference file it points to. Each reference holds everything for its domain in one place:
which datasource serves which metric, which variant, hard filter rules, grain, formulas, and dimension
value lists. Game/franchise/country mappings live in `ps-entities`.

## Fast path — from question to first query

The full rules live in `references/query-engines.md` and the domain files; this box is the correct
minimal sequence so the first statements of a conversation are right without re-derivation. When
anything here seems insufficient for the question, the reference file wins.

**0. Confirm Trino is connected.** Look for a tool whose server name contains `trino` (e.g.
`mcp__trino-mcp__…`); if none is loaded, `ToolSearch` for `trino` once. Still none → **stop**: send the
"Connect Trino" message from `brian-master` Step 0 (Settings → Customize → Connectors → **trino-mcp** →
Connect, then re-ask or start a new chat) and end the turn. Never route a Trino table through
`queryDruidSql` — Druid's `Object 'public'/'play_data' not found` means wrong connector, not a missing
table — and never ask for GIDs or guess chart versions as a workaround.

**1. Resolve entities** via `ps-entities` (game → GID, franchise members, cli 0/1/2, tiers).

**2. First statement of every conversation — one Trino batch for every chart the answer needs:**

```sql
SELECT chart_id, version, chart_version, independent_columns, metrics
FROM play_data.chart_config
WHERE chart_id IN ('chart_579', 'chart_1706', '...every chart_id the answer needs')
ORDER BY chart_id, chart_version
```

**3. Build each Druid name yourself:** `chart_id` + `-v` + `version` + the variant's
`independent_columns` **sorted alphabetically**, hyphen-joined. Config's `chart_version` string is NOT
reliably sorted — never copy it verbatim, and never hardcode a version from memory or these files.
Read each metric only from the variant whose `metrics` array lists it; a dimension listed in
`independent_columns` does not exist on that variant.

**4. Consolidate before writing SQL:** one statement per (datasource, variant) where the merge is
obvious — games/platforms/countries via `WHERE … IN (…) GROUP BY`, current + prior period in one span
grouped by `TIME_FLOOR("__time",'P1D')`, freshness read off the returned day column. Ratios are one
statement per variant (Druid cannot join variants), totals divided client-side — never average daily
rates into a period rate.

**5. Druid syntax traps:** double-quote every identifier and alias; the datasource is the bare quoted
name (no backticks, no schema prefix); always filter `"__time" >= start AND < end+1day`;
`gid`/`cli`/`diff` are VARCHAR — quote the literals; `COUNT(DISTINCT …)` is approximate — never use it
for day counts (count returned day rows instead). **In Trino the same three columns are `BIGINT` and go
unquoted, dates need typed `DATE`/`TIMESTAMP` literals, tables are `schema.table` with no catalog prefix,
and `%sql` is a syntax error** — full dialect notes in `references/query-engines.md`.

**6. Rollup pins at a glance** — confirm in the domain file before the first `SUM()`, never probe a
chart whose file declares none:

| Charts | Pins / rollups |
|---|---|
| 579 / 1170 / 1706 / monthly_rev_diff | none (gross chart: ignore `geo_bucket`, `country_bucket`) |
| 3730 (predictions, primary) | `accuracy` has FIVE values — `'pred'` · `'no_pred'` · `'monthly_only'` · `'weekly_only'` · `NULL`. **Keep `'pred'` only**; **never** `'more accurate'` here (zero rows). Two D365 models: unsuffixed metrics = weekly, `_month` = monthly |
| 1071 (predictions, fallback) | pin `model_type='DS_DAU_model'`; `accuracy = 'more accurate'`; exclude `no_pred` |
| 2077 (drill-down) | pin `mediation='overall'`, `ad_network='overall'`, `id_type='rid'`; filter `rev_type` (IAP is mixed in) |
| 2160 / 4495 (ad mon) | `network='overall'` is an exact rollup — pin it; exclude `country='others'` |
| 2524 / 2898 / 2301 / 2917 / 2888 / 2076 (engagement) | pin `id_type='rid'` (column absent on 2301 and 2917 — no pin there); `category='overall'` and `puzzle_type='w/o puzzle_type'` are rollups |
| 2454 (UA delivery by network / creative type) | none — but **always group by `network_name`**; never sum networks into one CTR/CPM/IPM/CPI |
| stability / notifications | pin `id_type='rid'` |
| ULD tables (Trino) | always bound the partition column (`dau_date` / `date_field` / `report_date` / `installed_date`); exclude `install_bucket='reject'` via `dau_splits`; `revenue_reports` filter `rev_type`; `economy_master_cc` filter `cash_type`; dedupe `adjust_installs` on `(gid, cli, refid)` — `references/uld.md` |

**7. Universal defaults that survive every question:** data complete only through **D-2**, freshness
per **variant** (both sides of every ratio); calendar-anchored periods (week = Mon, month = 1st);
net AND gross revenue, Rev/DAU whenever both appear; actuals before predictions, never mixed in one
ratio; `MAX(spend)` on `monthly_rev_diff`; annotations are commentary — never a queried number.

Then read the domain reference below for hard filter rules and formulas before finalizing SQL.

## Routing

| Question is about | Datasource(s) | Engine | Read |
|---|---|---|---|
| Net revenue, Rev/DAU, DAU | `chart_579-vN` (revenue), `chart_579-vN-source-source_category` (dau) | Druid | `references/core-and-cohort.md` |
| Gross revenue | `chart_1170-vN` (+ `-source-source_category` for its dau) | Druid | `references/core-and-cohort.md` |
| Installs, retention dX, cohort revenue/LTV, LTDays, actual ROAS | `chart_1706-vN` | Druid | `references/core-and-cohort.md` |
| Spend, eCPI | `chart_1706-vN-dt_flag-install_type` | Druid | `references/core-and-cohort.md` |
| Long-horizon cohort revenue/ROAS past the day-grain dX caps (monthly `diff` 0–103) | `play_data.monthly_rev_diff` | **Trino** | `references/core-and-cohort.md` |
| Predicted D365 ROAS (`ltv/ecpi_dX`), `Pred_LTV`, recovery, CPI, predicted retention/payers | `chart_3730-vN-target_bucket` | Druid | `references/predictions.md` |
| DS_DAU_model fallback predictions | `chart_1071-vN` | Druid | `references/predictions.md` |
| "Why did revenue move" — ad network, mediation, rev_type, cohort age, payer/LAT/device splits, eCPM, Rev/User | `chart_2077-vN` | Druid | `references/drilldown.md` |
| Ad funnel (request→load→view→click→grant), fill rate | `chart_2160-vN` | Druid | `references/ad-monetization.md` |
| Ad revenue/eCPM by ad network or ad type, ad time & time-between-ads buckets, ad-type retention/churn | `chart_4495-vN` | Druid | `references/ad-monetization.md` |
| **CPI decomposition / UA delivery** — CPM, IPM, CTR, Click-to-Install, impressions, clicks, creative-type & network cuts of CPI; budget/bid | `chart_2454-vN` | Druid | `references/ua-delivery.md` — **group by `network_name`**; explains the CPI move, is **not** the headline eCPI (that is `chart_1706`) |
| Sessions, time spent, sessions/DAU | `chart_2524-vN` | Druid | `references/engagement.md` |
| Engagement / in-game actions, actions per DAU, puzzle-mode or action-type cuts | `chart_2898-vN` | Druid | `references/engagement.md` |
| Rolling retention (D1/D3 rolling) | `chart_2301-vN` | Druid | `references/engagement.md` |
| In-game economy, virtual currency earn/spend/purchase | `chart_2917-vN` | Druid | `references/engagement.md` |
| WAU, MAU, stickiness | `chart_2888-vN` | Druid | `references/engagement.md` |
| DAU reconciliation (rid vs Adjust), permission givers | `chart_2076-vN` | Druid | `references/engagement.md` |
| Crashes, ANR, stability (Firebase) | `chart_2856-vN` | Druid | `references/stability-and-notifications.md` |
| Play Store crashes / ANR by build | `chart_2857-vN` | Druid | `references/stability-and-notifications.md` |
| Notification sends/clicks/CTR, permissions | `chart_3341-vN` | Druid | `references/stability-and-notifications.md` |
| Competitors, rival apps, market/genre benchmarking | `external_data.sensor_tower_data`, `external_data.st_product_details` | **Trino** | `references/competitor.md` |
| **What changed / what shipped / why a chart moved** — annotations: releases & build rollout %, experiment allocation ramps, admon stack opts, runtime config flips, open investigations | `play_data.charts_annotations` (coverage bounds read live, never assumed) | **Trino** | `references/annotations.md` |
| **User-level questions no chart answers** — distinct users, per-user distributions (p50/p90, whales, zero-session DAU), segment combinations no variant carries, user-level joins across revenue / sessions / engagement / economy, wallet balances, Adjust campaign / adgroup / creative at install, reported revenue by source × country | ULD tables: `derived_tables.dau_splits`, `dm_admon.rev_dau_install_diff_ilrd_v2`, `derived_tables.revenue_reports`, `server_tables.engagement_puzzle_master_cc_col`, `server_tables.sessions_master_cc`, `server_tables.economy_master_cc`, `derived_tables.wallet_dau_install_diff`, `analytics.adjust_installs` | **Trino** | `references/uld.md` first (decision rule, routing, layer-wide rules, canonical join), then only the one `references/uld/<table>.md` it points to. **Headline numbers stay on the charts** |
| Which engine runs a query, version lookup, variant/metric selection, alphabetical name building, Druid and Trino SQL syntax, unavailability rules | `play_data.chart_config` | **Trino** | `references/query-engines.md` |

## Rules that apply to every datasource

**What belongs on this page.** Only rules that hold for **every** datasource: engine/version resolution,
ratio construction, the D-2 freshness default, filter discipline, verification triggers. **Anything true of
one datasource — a rollup value, a mandatory pin, a feed-specific lag, a column quirk, a dimension value
list — belongs in that domain's `references/` file, never here.** The test: would this rule cause a check on
a chart that doesn't have the column? If yes, it isn't universal. Every domain reference opens with a
`Rollups & mandatory pins` section stating its rollups **or "none"** — keep that true of any domain added
later, since it is what lets the analyst skip a discovery probe.

**Engine, version and variant resolution is owned by `references/query-engines.md`** — read it before
the first query of any conversation. In one line: only `play_data.chart_config`,
`play_data.monthly_rev_diff`, the two Sensor Tower tables and `play_data.charts_annotations` run in
Trino; everything else is a Druid chart whose name you build from a `chart_config` row resolved this
conversation, with the variant suffix sorted alphabetically, reading each metric only from the variant
that lists it. Every chart name in this catalog is written `chart_XXXX-vN` on purpose so a stale version
can't be copied. Don't re-derive those rules from this page.

**Annotations are commentary, never a metric.** `play_data.charts_annotations` records what a human or a
deploy said changed — the only source of *cause* in this catalog, and evidence rather than data. Never
count annotations as an outcome, never let a figure quoted inside an annotation's text ("BN RPD +8.77%")
enter a KPI table or a delta as if it were queried, and never let an annotation replace a metric query.
Use one to decide where to point a drill-down, then query the chart datasource for the number.
**Its coverage bounds move as history is backfilled — read them live (`MIN`/`MAX` on the event
timestamp) before ever calling a window uncovered, and quote the probe** (SR-20); "outside the live
bounds", "covered but nothing returned" and "covered, but annotation coverage is voluntary" are three
different statements and only a probe distinguishes them. Full rules — epoch `created_at`, the three
row-inflating duplications, `features` fuzzy-matching, and the two similarly-named tables that must not
be queried: `references/annotations.md`.

**Rollups and mandatory pins are dataset-specific — read them, don't probe for them.** Some dimensions
carry a rollup value alongside its members, or stack several logical series in one column; summing across
one silently double-counts. **Which dimensions those are differs per datasource, and each domain reference
declares them up front under "Rollups & mandatory pins".** Pin the rollup for totals, exclude it when
drilling, never sum both.

**Never mix actual and predicted in one figure.** `installs` and `spend` exist as actuals (`chart_1706`)
**and** as model predictions (`chart_3730`, `chart_1071`). Default to the cohort actuals for observed
installs/spend/eCPI. Use the prediction charts only for the model's own view, or for a
prediction-derived ratio needing internally consistent inputs. Never put an actual numerator over a
predicted denominator, and never sum or compare the two without labeling which is which.

**Compute ratios client-side.** Query each base metric separately from its own correct variant, then
apply the formula. Never combine metrics from different variants or charts in one query. Align numerator
and denominator to matching available dates only — if a date's numerator is 0/NULL/unmatured, drop that
date's denominator too, and disclose the exclusion.

**Headline vs decomposition.** Headline (L0) figures come from the core, cohort, and prediction charts.
Drill-down and extended charts decompose a move; never mix sources inside one metric's headline figure,
and note when drill-level sums won't tie exactly back to the L0 source.

**Freshness, delivery lag, and the D-2 default.** **Assume data is complete only through D-2 (two days
before today) unless a freshness check proves otherwise.** Revenue and spend both post on a ~2-day lag,
so the last 1–2 days of any window are structurally incomplete — partial, not declining. Three rules
follow, none of them optional:

- **Establish freshness per datasource AND per variant, on first use in a conversation.** Variants of
  the same chart deliver independently — confirmed live (Aug 2026): the base `chart_1706-vN` carried
  `installs` a full day later than `chart_1706-vN-dt_flag-install_type` carried `spend`, same chart, same
  version. Checking the base chart and assuming the spend variant matches produces a silently wrong
  eCPI/ROAS on the trailing day. A ratio's numerator and denominator each need their own freshness check.
  **Get it from the day-grained query you are already running against that variant — the max of the
  returned day column is the answer, so this costs no extra statement.** A standalone `MAX("__time")` is
  needed only for a variant you touch with no date grain at all. See "Query consolidation" in
  `references/query-engines.md`.
- **Flag any datasource trailing today by 2+ days — not 3+.** The old >3-day threshold let the ordinary
  D-2 gap pass unflagged, which is the most common way an incomplete tail reaches a reader as a real
  move. Trailing 2 days is expected and gets stated; trailing 3+ escalates as a pipeline concern.
- **A trailing-day `0` or NULL on a spend, revenue, or cohort field is expected delivery lag, not an
  anomaly.** Never report it as a collapse, never chase it as a data-quality incident, and never let it
  into a ratio (see date alignment above). This is the one carve-out to "any impossible result triggers a
  re-check": confirm the date sits inside the lag window, state the exclusion, move on.

Distinguish **delivery lag** (the ETL hasn't shipped that date yet — affects every metric, resolves in
days) from **cohort maturity** (the cohort exists but hasn't aged X days — affects only `dX` fields,
resolves as the cohort ages). Both produce a low or zero trailing figure; they are different problems and
must never be described interchangeably. Cohort maturity detail: `references/core-and-cohort.md`.

**Feed-specific delivery gaps live with their datasource.** Some individual revenue feeds arrive on their
own lag on top of the D-2 default (xpromo and Apple Arcade on the core revenue charts are the known cases —
see `references/core-and-cohort.md`). These are per-datasource facts, not global ones: read the domain file
rather than assuming every chart has an undelivered tail beyond D-2.

**Filters are never defaults.** No filter value in any template or example is a default. Apply a filter
only when the question calls for it or a hard rule requires it, and omit unscoped filters entirely
rather than blanking them. Exclusion lists in reference queries are case-specific — if unsure whether
one applies, ask the user rather than carrying it over.

**Trust these references for routing; verify live on a trigger.** Metric-to-variant mappings, dX
ranges, and dimension lists here are a snapshot. For any documented chart, resolve the version and query
it directly with no preemptive schema check. Verify (`INFORMATION_SCHEMA.COLUMNS` in Druid,
`DESCRIBE <schema>.<table>` in Trino, or a bounds/count probe for availability) only when: (1) about to tell a
user that a metric, field, dimension, **time period, or row set** "isn't available", or reaching for a
proxy; (2) a query fails with a schema error **after** you've confirmed the alphabetical sort; (3) the
chart has no entry here. At most once per datasource per conversation. Live wins — and when a mismatch
is found, update the relevant reference file (or state the exact correction if the files aren't
editable) so future runs can skip the same check. `chart_config` version resolution is engine routing,
not schema verification — it always runs.

**Volatile facts in these references are snapshots and can never ground a negative claim.** Coverage
windows, date ranges, row counts, distinct-value counts, ID ranges, "live profile" lines and version
numbers were all true at authoring time and drift without the documentation following — sources get
backfilled, extended, and re-versioned. They are sound for **recognising shape and routing**, and
unsound as evidence that something **does not exist**. Any statement that a period is uncovered, a table
is empty, a metric is unavailable, or a value doesn't occur requires a probe run this conversation, with
the result quoted (SR-20). **Trigger (1) above is the one verification that is never rationed** — the
once-per-datasource budget applies to exploratory schema checks, not to a check standing between the
reader and a false "this data doesn't exist".

## Formula conventions

- **Normal** = a raw field. **Always aggregate it at date level first** — `SUM(...)` grouped by the date
  column — then collapse across dates, never in one blanket `SUM()` over the whole window. The date-level
  rows are what a trend chart, a period comparison and a day count all need anyway, so this costs nothing.
- **Collapsing date-level rows to a window figure: sum additive metrics, average level metrics.**
  - **Sum** — revenue, gross revenue, spend, installs, impressions, clicks, sessions, ad requests/views,
    notification sends: each day's value is a fresh quantity, so they add.
  - **Average** — DAU, and any other per-day distinct-user or point-in-time level (WAU, MAU). **Summing DAU
    across dates gives user-days, not users** — a 30-day "DAU" that is 30× too large. Report average DAU
    over the window and say so.
  - A metric you can't classify with confidence → report it at date level rather than guessing which way
    it collapses.
- **Custom** = derived. Query each base metric separately from its own correct variant, aggregate each to
  date level, collapse each per the rule above, and only then apply the formula — align numerator and
  denominator to matching available dates first. **Never average a daily ratio to get a window ratio**
  (`AVG(daily Rev/DAU)` ≠ window Rev/DAU): collapse numerator and denominator separately, then divide.
- **Never change a metric's unit or definition for readability.** rev/DAU means rev/DAU — not
  rev/1,000-DAU, not indexed, not rescaled.
- **Actual vs predicted are different metrics.** Anything from `chart_3730` or `chart_1071` is a model
  projection, including its `installs` and `spend`. Label observed figures "actual"; identify
  predictions by their D365/D360 horizon naming. Never mix the two in one ratio.
- **Don't invent formulas.** If a needed derived metric isn't here, say the underlying field isn't
  available rather than approximating one — and verify against the live schema before declaring it
  missing.

## Glossary

- **Annotation** — a dated note pinned to a metric chart explaining a movement (release, experiment ramp, config flip, open investigation). `play_data.charts_annotations` is the store behind that chart feature; `references/annotations.md` owns the rules.
- **PSPN** — Playsimple Player Network: the cross-game notification/xpromo network, and an annotation category for notification-driven changes.
- **Admon** — ad monetization; also an annotation category for ad-side changes and stack optimisations.
- **Server-Build** — auto-generated annotation marking a server build/deploy. 70 rows on a single gid, so rarely the explanation for a portfolio move.
- **Investigation** (annotation category) — an open issue, **re-stamped daily while it stays open**; collapse to (description, gid) and read the min/max span as the window the issue was live.
- **Releases** (annotation category) — a build rollout marker; `1.282.0:100%` means build **282** at **100%** rollout. The same version reappears at `:50%` then `:100%`, giving both edges of a staged rollout.
- **Runtime** (annotation category) — a live config flip, written `<config_key> [<param>: <old> to <new>]`.
- **W2E** — Watch-to-Earn (rewarded video); appears in annotation text and `feature` values like `w2e on grid`.
- **PAB** — post-A/B read: the measurement taken after an experiment is ramped down, quoted inside Admon annotation text.
- **Xpromo** — cross-promotion: ads run inside one Playsimple game for another Playsimple game.
- **p2e** — play-to-earn acquisition channel/source. **dt_t1** — Digital Turbine tier-1 preload partnership channel.
- **Net revenue** — after the store/platform cut. **Gross revenue** — before the cut; a separate chart, never derived from net.
- **Cohort** — users who installed on the same date. Cohort `dX` fields describe that cohort X days later; cohort *buckets* (D00, D02-D07 …) are age-since-install, not calendar dates.
- **Recovery** — model-predicted revenue recouped against UA spend.
- **no_pred** — an `accuracy` value meaning the model produced no prediction for that segment. On `chart_3730` the d365 columns then hold the raw `dX_recovery` carried forward, **not zero**. Always exclude. **Its scored sibling differs by chart:** `'pred'` on `chart_3730`, `'more accurate'` on `chart_1071`.
- **monthly_only / weekly_only** — `chart_3730` `accuracy` values meaning only one of the two D365 models scored that segment; the other model's column falls back to actual-to-date. Exclude alongside `no_pred`.
- **Coverage** — the share of installs or spend carrying a valid scored prediction. Always disclose it; low coverage means reduced confidence.
- **Rolling retention (D1/D3)** — flag-based: active on or after day X post-install. Distinct from classic retention (active on day X).
- **ANR** — Android "App Not Responding"; a separate error class from fatal and non-fatal crashes.
- **rid** — internal user-identifier grain, as opposed to `adjust` (network-attributed) rows.
- **eCPM** — revenue per 1,000 impressions. **eCPI** — spend per install. **ROAS** — revenue ÷ spend. **LTV** — cumulative revenue per install. **LTDays** — active days per install.
- **IPM** — installs per 1,000 impressions (`chart_2454`); `CPI = CPM ÷ IPM`, `IPM = 1000 × CTR × Click-to-Install`. **IEC** — creative type labelled 'Video + IEC'; expansion not stated in the source SQL. **Click to Install** — installs ÷ clicks, store step included.
- **ULD** — user-level data: the Trino warehouse tables at user (`rid`) grain, keyed `(date, gid, cli, rid)`; a drill layer under the charts — `references/uld.md`.
- **ILRD** — impression-level revenue data: per-impression ad revenue from mediation, rolled up to the user-day in `dm_admon.rev_dau_install_diff_ilrd_v2`.
- **`independent_columns`** — the dimensions **absent** from a variant's datasource, and the suffix in its name (sorted alphabetically by Druid).
