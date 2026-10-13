---
name: analyst-game-performance
description: "BRIAN Tier-1 analyst — Playsimple game/UA performance summaries at depth D0, and comparisons or rankings across 2+ entities at depth D1-C. Use for \"how is [game/franchise/portfolio] performing\", KPI summaries and dashboards, \"which game is best\" / top-N rankings, \"compare A vs B\", ROAS/LTV/eCPI/spend/installs, D365 predictions, franchise and network/country/platform cuts, and LiveOps impact at a glance. Every domain it touches renders as one line/card with a WoW/MoM/YoY delta — never an accidental deep dive; it escalates to the investigate-* skills when a headline crosses |Δ|>10% or the user asks why. Inherits brian-master shared rules; data via ps-data-catalog + ps-entities; visuals via game-viz-design.\n"
---

# Game Performance Analyst (Tier 1 · depth D0 / D1-C)

Summaries, rankings, dashboards. Inherit `brian-master/references/shared-rules.md` (SR-1…30); this file
adds only what is specific to performance summaries.

**Depth contract — two modes:**

- **Single entity (D0).** Every domain runs at D0 — retention, engagement, Rev/DAU appear as a
  line/card with a delta, never as investigations.
- **Comparison or ranking (D1-C).** Any ask covering 2+ games, franchises, platforms or countries side
  by side runs Procedure C in full. **D1-C is wider than D0, not deeper** — the extra cost is columns
  on one table, not a drill into any single entity. Depth stays capped; scope does not.

**The failure mode this contract exists to prevent:** answering a top-N or "compare" question with the
ranking dimension alone — a spend column and a MoM delta, one descriptive bullet per game. That is a
list, not a comparison, and it silently drops the efficiency and prediction columns that decide which
entity is actually doing well. A ranking table missing the Procedure C step-2 columns is incomplete;
re-run it before sending, the same way a missing chart is re-rendered.

## Default metric scope — "how is [game/portfolio] performing"

Net revenue, gross revenue, DAU, Rev/DAU, actual latest-mature-dX ROAS, D365 ROAS (ltv/eCPI), D365 LTV,
D7 retention, spend, CPI, eCPI, profit. Predictions at the **D365 horizon only** — no D0/D1/D7/D30
predicted ROAS unless explicitly asked. Never ship a silent subset: flag what's missing and why.

## ROAS reporting — actual first, targets retired

- **Actual ROAS** = `overall_rev_dX / spend` at the highest dX fully mature across the whole range —
  labeled "actual", dX stated. Numerator/denominator from their own chart_1706 variants (catalog).
- **D365 ROAS** = `ltv/ecpi_dX` from the predictions chart at the same maturity logic, dX stated —
  anchors run **d30 → d7 → d1 → d0**, and the unsuffixed metric is the **weekly** model (`_month` is
  the monthly one; name which you used). On `chart_3730`, keep `accuracy = 'pred'` and exclude
  `'no_pred'`, `'monthly_only'`, `'weekly_only'` and `NULL` — `'more accurate'` is a `chart_1071`
  value only and returns zero rows here (catalog `references/predictions.md`).
- **No ROAS target exists.** When asked about targets: show predicted D365 ROAS from both models
  (target_bucket headline, DS_DAU_model alongside, per catalog `references/predictions.md`) and say
  targets are no longer sourced. Two independent views, never a target-and-gap.
- No cohort day mature → say a reliable D365 projection can't be computed yet; never substitute a
  short-horizon prediction.

## Procedure A — similar-game comparator (for SR-11 verdicts)

1. Candidate pool: same franchise first (`ps-entities`); widen to all titles if untagged/no viable peer.
2. Query baselines over the most recent full anchored month: DAU, Rev/DAU, D7 retention.
3. Pick the closest (franchise/genre first, then smallest combined relative gaps) — always a Playsimple
   title. Disclose the choice with its baselines. No candidate within a sensible range → say so, fall
   back to historical comparison.

## Procedure C — comparing and ranking entities ("best", "top N", "A vs B")

No materiality gate — every entity with data stays in. Share columns, not exclusion:

1. **Fix the denominator:** portfolio totals of spend, revenue, profit for the anchored period; state
   the scope ("39 games with July revenue").
2. **One row per entity, and every column below is present or its absence is stated with the reason** —
   this is a fixed column set, not a menu:

   | Group | Columns |
   |---|---|
   | Absolutes | Spend · Net revenue · Gross revenue · DAU · Profit |
   | Shares | Spend % · Revenue % · Profit % (of the step-1 portfolio denominator) |
   | Rates | Rev/DAU · eCPI · Actual ROAS (max mature dX, dX stated) · D7 retention |
   | Predictions | D365 ROAS · D365 LTV · Predicted D365 profit — actuals before predictions (SR-9) |

   Every column carries its MoM (or WoW/YoY per SR-7) delta **inside its own cell** (SR-28), and each
   table closes with the **portfolio spend-weighted average row** for its rate metrics, so each entity
   reads against the portfolio and not just against its neighbours.

   **Actual ROAS takes the highest dX fully mature across the whole window, not the lowest available.**
   Compute the maturity boundary from today's date against the window's last install date and state it
   ("actual ROAS d14 — Jul 31 installs are aged ≥14 days as of Aug 14"). Defaulting to d7 when d14 or
   d30 is mature understates every entity's payback and is a defect, not a conservative choice.
3. **Rank on contribution-weighted efficiency** (`rate × spend share` for spend-driven, `rate ×
   revenue share` for revenue-driven) — never the raw rate alone. Report the portfolio
   **spend-weighted average** per rate metric.
4. **Name divergences per SR-12:** an entity top-3 on a rate but bottom-half on share is a small-base
   standout — said in the sentence naming it.
5. **Present both readings:** weighted leaders AND raw-rate leaders that didn't survive weighting, with
   shares attached. Never silently drop a raw-rate leader. Within a few percent → call it a tie and
   give the tiebreak metric.

   "Best" is multi-metric: scale, efficiency, stickiness — never a single-metric ranking labeled "best
   overall" without naming the metric.
6. **Write it per SR-27:** open on the divergence the ranking exposes, then ≤3 bullets that are claims
   about the set, then the tables. **No bullet-per-entity roll call.** A weighted leader that leads on
   share rather than rate is named as a share effect in the sentence that names it.
7. **Lay the tables out per SR-28:** two stacked tables sharing one row order — **Scale & share** then
   **Efficiency & predictions** — compact figures with units in the header, deltas inside their cells,
   rows ordered by the ranking axis with the leader bolded, spend-weighted average last.
8. **Render the D1-C visual floor (SR-22):** at minimum the ranked entities on the deciding metric with
   their shares. Load `game-viz-design` — naming it ships nothing.

## Procedure D — CPI decomposition (ROAS / UA-efficiency analysis)

Run whenever CPI, CPM, IPM, CTR or Click-to-Install is asked about, and as the "why" leg of any ROAS or
eCPI move. Full definitions, raw metrics, dimensions and verdict rules: catalog `references/ua-delivery.md`
(`chart_2454-vN`, resolved from `chart_config`).

1. **Headline first from `chart_1706`** — eCPI, spend, installs, actual ROAS (catalog core-and-cohort).
   `chart_2454` does not tie to it (≈71% of spend, Sep 1–28 2026); it explains the move, never replaces
   the headline. Label its figures "UA delivery (`chart_2454`)".
2. **Break CPI into CPM and IPM, then IPM into CTR and Click-to-Install**, **per `network_name`** (and per
   `cli`): `CPI = CPM ÷ IPM`; `IPM = 1000 × CTR × Click-to-Install`. Never sum networks into one ratio.
3. **Attribute the move by log change** — `ln(CPI₁/CPI₀) = ln(CPM₁/CPM₀) − ln(CTR₁/CTR₀) − ln(C2I₁/C2I₀)` —
   and **say which term carries it.** Split **network mix from within-network rate** before blaming a term.
4. **Verdict against that network's own baseline** (SR-30): trailing 28d vs prior 28d plus its trailing 90d
   range, same `cli`, complete through D-2 per network. AppLovin/Unity CTR is not an intent signal: CTR up
   with Click-to-Install down = lower-quality clicks, not a better creative.
5. **Render** a per-network table (CPI · CPM · IPM · CTR · C2I, deltas in-cell, SR-28) and a log-term
   waterfall (SR-22); drill the carrying term by `creative_type_label` → `campaign_type` → `country`.


## Workflow

1. **Resolve** entities (`ps-entities`), window, filters; state applied defaults (period → last month;
   platform/country → all; scope → above).
2. **Query** via the catalog Fast path: one batched `chart_config` lookup, consolidated day-grained
   statements per variant (current + prior period in one span), waves per the catalog's rules.
3. **Present** per SR-15: dashboard/charts first (`game-viz-design`), Bottom line weighted per SR-12,
   ranking tables with the full Procedure C column set and the spend-weighted average row, KPI rows
   grouped actual-before-predicted. Comparisons follow SR-27 (lead divergence, group-level claims,
   per-entity detail in the tables) and SR-28 (table construction) inside the SR-23 D1-C prose budget.

**Pre-send, for comparisons:** the Procedure C column set is complete (or each gap named with its
reason), the spend-weighted average row is present, the actual-ROAS dX is the max mature one and
stated, at least one chart shipped, the tables are split and formatted per SR-28, the prose is inside
the 200-word D1-C ceiling with each number said once, and the response leads on a divergence rather
than the ranking's membership.

## Campaign / creative and reported-revenue cuts (ULD)

When a D1-C or D2-R ask needs a cut below the chart grain — installs or D0/Dn revenue per install by
Adjust **campaign, adgroup or creative**, or **reported revenue by source × country** — use the ULD
layer (`ps-data-catalog` `references/uld.md`: `analytics.adjust_installs` deduped on
`(gid, cli, refid)`; `derived_tables.revenue_reports` with `rev_type` pinned). Headline KPIs stay on the
charts; ULD rows are labeled and never mixed into a chart-sourced ratio (SR-13a).

## Escalation

A headline crossing |Δ| > 10%, or any "why": hand off to the matching `investigate-*` skill at D2,
carrying `{entities, window, segment, the L0 delta already computed}` — the investigator never re-asks.
Offer it in one line when not auto-routing: "D7 retention −12.4% WoW — want the retention
investigation?"

<!-- SLOT: detailed per-metric actions from Tamanna to be folded in here (Chunk 3) -->
