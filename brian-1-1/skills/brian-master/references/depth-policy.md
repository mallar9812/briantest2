# Depth Policy — D0 to D3

"How is Portugal doing?" and "retention has dropped" both touch retention — but the first deserves one
line with a delta and the second a staged investigation. Depth is a decision made at routing time,
never improvised per answer. Every hand-off carries a depth; every answer states the depth it ran at.

## The levels

| Level | Name | What it includes | Used by |
|---|---|---|---|
| **D0** | Mention | Metric + period delta (% and absolute) as one line/card inside a broader answer. No cuts, no evidence layer. | `analyst-game-performance` for each domain in a summary; `analyst-general-questions` lookups |
| **D1** | Check | D0 + the **is-it-real gate only**: delivery lag (D-2), cohort maturity, day-count alignment. Verdict: real move vs data artifact. | `analyst-daily-healthcheck` per cell; stage 1 of every investigation |
| **D1-C** | Compare | D0 on each entity **side by side**: the full Procedure C column set for every entity in scope, contribution shares, the weighted ranking and the spend-weighted average row. **Wider than D0, not deeper** — no drill into any single entity. | `analyst-game-performance` for any ask covering 2+ entities |
| **D2** | Diagnose | D1 + L1 decomposition to top contributors (~90% of the delta) + annotations scan on the localized window + the playbook's cross-metric sanity checks. | Default for "[metric] dropped/spiked" |
| **D2-R** | Report | **Floor for any PPTX/PDF deliverable** — see below. D2's decomposition and annotations scan applied to every headline the report carries, plus a chart per report section. | `ps-brand-report` in analytics mode |
| **D3** | Full investigation | D2 + every L2 cut, full cross-metric sweep (what else moved in the same window/segment), mix-shift analysis, evidence timeline, hypothesis table. | Explicit "investigate / root cause / deep dive", or a D2 that ends inconclusive |

## D2-R — a report is never built at D0

**Any request whose deliverable is a file — PPTX deck, PDF document, "export this to slides" — runs at
minimum D2, whatever depth the same question would have taken in chat.** Take the maximum of the
inherited depth and D2-R; never the inherited depth alone.

The reason is structural. `ps-brand-report`'s spine has sections a conversational answer does not:
**Breakdowns** (cross-segment bars or tables), **Detail / narrative**, and **Recommendations**. D0 is
defined above as "no cuts, no evidence layer" — so a report assembled at inherited D0 depth is asked
for sections its depth forbids it to produce. What ships is a thin deck: correct headline KPIs
followed by charts that restate them. **That failure is silent** — the deck builds, validates, and
looks plausible.

At D2-R, deliver for every headline metric the report carries:

- The **L1 contributor decomposition** (which games / platforms / countries / networks carry the move),
  with each contributor's share of the delta — this is what fills the Breakdowns section.
- The **annotations scan** over the reporting window (`ps-data-catalog/references/annotations.md`) —
  this is what fills the Detail / narrative section with what changed rather than only what moved.
- **At least one chart per report section**, per SR-22.
- Where a headline crosses |Δ| > 10%, the matching `investigate-*` playbook at D2 for that metric.

**The SR-23 prose budget and the SR-28 table rules do not cap a report deliverable.** SR-23 caps *chat*
prose; a 60-word ceiling on a D0 answer is right in conversation and wrong for a fifteen-slide deck, and
SR-28's ~8-column split is a chat-table rule that `ps-brand-report`'s own density limits supersede (one
idea per slide, ~40 words of body copy, ≤35 words in an insight panel, ~8 rows per slide). SR-24 (say
each number once), SR-25 (assert, don't argue) and SR-27 (claims about the group, not a bullet per
entity) all still apply — they are quality rules, not length rules.

Escalate a report to D3 only on an explicit ask ("full deep dive deck", "post-mortem").

## Intent → depth mapping

- Broad performance question ("how is X doing") → route `analyst-game-performance`; every domain it
  touches runs at **D0**.
- Comparison or ranking across 2+ games/franchises/platforms/countries ("compare A vs B", "top 5 by
  spend", "which game is best") → `analyst-game-performance` at **D1-C**. The extra cost is columns on
  one table, never a drill-down — depth stays capped, scope does not. **A top-N answered with the
  ranking dimension alone (a spend column, a MoM delta, one bullet per game) has run at D0 while
  claiming D1-C.**
- **Deliverable is a deck or a document** ("make a report/deck/PDF of…", "export this to slides",
  "monthly review deck") → the primary analyst answers at **max(inherited depth, D2-R)**, then
  `ps-brand-report` formats. A report request never runs below D2.
- Healthcheck → **D1** on every cell; a red cell upgrades to **D2** (never straight to D3).
- "[metric] dropped/spiked" → matching investigator at **D2**.
- "Why…", "investigate", "root cause", "deep dive" → investigator at **D3**.
- **User override always wins:** "just give me the number" forces D0; "go deeper" upgrades exactly one
  level. An explicit "quick one-pager, headlines only" overrides the D2-R floor — but say that the
  breakdowns were skipped on request.

## Stop gates — what keeps depth honest

1. A stage may not start unless the assigned depth allows it.
2. **Early stop:** if a stage already explains ≥90% of the delta with corroborating evidence, report
   and stop — even with budget remaining. **But "explained" means localized to the finest actionable
   grain the playbook's chain names** (e.g. `install_source`, not just `install_bucket`; a named
   ad network, not just "ad revenue"). A coarse cut crossing 90% licenses *finishing the chain within
   the stage cheaply* — it never licenses skipping the chain's remaining levels. The early stop
   applies BETWEEN steps only when the remaining steps are a different axis, never mid-chain on the
   same axis.
3. **Escalation offer, never silent deepening:** an investigation that hits its budget while
   inconclusive says so and offers the next level ("D2 couldn't localize this — want the full D3
   sweep?").
4. **State the depth** in the answer's period & segment line (e.g. "· depth D2") so the reader knows
   what was and wasn't checked. A report states it in the appendix's methodology note.
5. **Depth is never silently downgraded.** The assigned depth is what the answer must contain. Ambiguity
   in the ask, a user-quoted figure that doesn't reconcile, a definition needing a judgment call, or a
   reference that looks stale are all handled *within* the run — resolve on the evidence, take the most
   reasonable reading, and flag the assumption in one line (SR-17, SR-18, SR-21). **Clarifying questions
   never substitute for assigned work**: an answer that replaces a D2/D3 analysis with questions has run
   at D0 while claiming the higher depth. If a question is genuinely needed, it rides alongside the
   delivered analysis, not instead of it.
6. **Depth survives a mid-run metric correction.** Discovering partway through that the wrong metric,
   denominator or family was queried resets the *series*, not the *budget* — re-run the stages on the
   corrected series at the depth originally assigned, and say which correction was made. A correction is
   not a fresh, shallower question.
7. **A report with an empty Breakdowns section has run below its depth.** Same class of defect as a
   missing chart (SR-22): the deliverable looks complete, so nothing signals it. Before packaging a
   deck or PDF, confirm every section of the spine that applies is carrying analysis rather than a
   restatement of the KPI grid.
