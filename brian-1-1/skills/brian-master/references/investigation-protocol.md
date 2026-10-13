# Investigation Protocol — binding at depth ≥ D2

The shared machinery for every `investigate-*` skill and any analyst running a "why did X move"
at D2+. Domain playbooks say *what* to cut; this file says *how the investigation argues*.

## Stage zero — lock the metric before drilling

An investigation aimed at the wrong series is worse than no investigation: every downstream cut is
internally consistent and about nothing the user asked. Before L0, settle three things and state them
in one line each.

1. **Which metric family.** Near-synonym names recur across families — the same short label can mean an
   install-cohort metric, a flag-based one, an activity-based one, or a ratio of two of them. The user's
   word choice does not settle it, and neither does the absence of a keyword. **Settle it on the
   evidence: the level they quoted, the shape they describe, and — where two families are plausible and
   both are cheap — by pulling both and seeing which one matches.** Two extra rows in a `GROUP BY` cost
   less than a misaimed investigation.
2. **Which formula.** Name the numerator, the denominator and their sources. A metric family usually
   admits more than one denominator; the one that reproduces the level the user works from is the one
   they mean (SR-17).
3. **Whether the stated move reproduces.** Compare the queried series against the level, direction and
   timing the user described. Agreement → say so and drill. Disagreement → SR-17/SR-18: test the
   adjacent definitions, adopt whichever reconciles, otherwise proceed on the best-grounded series with
   the discrepancy noted in one line. **Disagreement is never a reason to stop, and never converts the
   investigation into questions back to the user.**

State the locked definition in the answer. If the user later says the metric was something else, that is
a cheap correction; a silent mismatch is not.

**"Real vs artifact" (Stage D1) is a data-quality question, not a materiality question — do not blur
them.** Every investigator's Stage D1 asks exactly one thing: is the queried delta a genuine data point,
or a pipeline artifact (delivery lag, an unmatured cohort, an unequal day count, a misaligned ratio)?
That is the entire scope of "artifact." **A delta smaller than the level the user quoted, or one that
sits inside the metric's recent day-to-day/week-to-week variance, is not thereby an artifact — it is a
real, small move, and "real, small" is never a stop condition.** NOISE is a Stage D2+ **attribution
verdict** (one of GAME / CAMPAIGN / EXTERNAL / AD-OPS / NOISE — see "Attribution ontology" below),
reached only after the chain has run and nothing concentrates. It is never a Stage D1 shortcut for "this
doesn't look big enough to matter" or "this is inside normal variance so I won't drill further." A
magnitude mismatch against the user's quoted figure is SR-17/18 territory — test adjacent definitions,
adopt whichever reconciles, note the discrepancy — never grounds, on its own, to render the D1 verdict as
"artifact" and close before reaching the depth the routing assigned. **If Stage D1's data-quality checks
all pass (fresh, matured, aligned), the verdict is REAL, full stop** — continue to the assigned depth
even if the number looks unremarkable; "unremarkable" is exactly what the contributor chain and hypothesis
table exist to test, not pre-empt at D1.

## The drill (L0 → L1 → L2)

1. **L0** — the metric's delta between two anchored periods, from its headline source (SR-5/6/7).
2. **L1** — decompose by franchise/game (or the playbook's first axis). For each segment compute
   **contribution to the delta** (`segment_delta / total_delta`), not just its own % change. Report
   the top contributors covering ~90%+ of the move; name franchise member games.
3. **L2** (depth D3, or D2 where the playbook stages it) — inside the top contributors, cut by every
   available dimension the playbook names. Report cuts that **concentrate** the delta; skip cuts that
   spread it evenly.
4. **Explanatory layer — quantitative first, then annotations.** Check coinciding shifts in the same
   segment (installs, spend, mix), then pull `charts_annotations` for the localized gid/cli/window —
   **not optional on any "why" question.** Widen ±3 days, scope category, read in order of explanatory
   power (Releases rollout % → Experiments ramp delta → Admon opts → Investigation windows → Runtime
   flips). **Query the window before concluding anything about coverage.** If the pull comes back
   empty, establish the table's actual bounds live (`MIN`/`MAX` of the event timestamp) before writing
   that the window is uncovered — documented coverage floors go stale as history is backfilled, and a
   window dismissed on a stale bound hides the evidence layer entirely (SR-20). Distinguish three
   different statements and use the right one: *the window is outside the table's live bounds*,
   *the window is covered and nothing was annotated*, and *annotation coverage is voluntary, so silence
   is not proof nothing changed*. Per SR-14 a quoted figure inside an annotation never enters a KPI table.
5. **Offsetting moves** — if L1 segments move in opposite directions, say so; a flat L0 can hide real
   movement underneath.
6. **Present as a drill path**, every level carrying % + absolute: "Net revenue −8.2% WoW ($5.1M →
   $4.7M) → Anagram franchise −$310K (74% of the drop) → iOS US, rewarded video −$220K."

## Hypothesis discipline (D2+)

- Branch **~3 candidate hypotheses spanning different causal axes** at the point the playbook calls for
  them — never three variations of the same axis. Most metrics this protocol investigates decompose
  into at least a **rate/yield side** (eCPM, retention rate, fill rate, conversion) and a **count/volume
  side** (impressions, installs, sessions, users), plus a **mix/segment side** (a shift toward a
  different, lower- or higher-value population). A hypothesis set that is three flavors of "which
  segment" — three networks, three countries, three cohorts — has tested one axis three times, not three
  axes, and fails this rule even though it has three rows. Cover as many of the live axes as the
  playbook names before narrowing to the one that shows signal; an axis is dropped from the set only
  after it was actually checked and came back clean, never because a different axis was checked first
  and looked sufficient.
- Test each hypothesis on data queried this conversation. Every tested hypothesis renders with a
  verdict — **SUPPORTED / REJECTED / NOT-TESTED** — plus its supporting numbers; the lead hypothesis gets
  a chart.
- NOT-TESTED requires a reason (out of depth budget, data BLOCKED) — never silence.
- **A rate-side finding and a count-side finding are not substitutes for each other, and neither is a
  mix-side finding.** Where a metric has a cataloged rate/yield formula and a cataloged count/volume
  formula at the same grain (e.g. eCPM and impressions by network; retention rate and cohort size by
  source; fill rate and request volume by placement), both get pulled at that grain before any of the
  three is treated as ruled out. A ranking sorted by one side only surfaces the segments that are big on
  that side — it structurally cannot see a small-share segment with a large move on the *other* side, so
  "the ranking looked clean" is never evidence the other side is fine.

## Attribution ontology

Tag every finding with exactly one bucket:

| Bucket | Meaning |
|---|---|
| **GAME** | Product/content/build behavior — moves across sources together |
| **CAMPAIGN** | UA-driven — scales with one source/network/geo |
| **EXTERNAL** | Market/platform/seasonality — peers move too |
| **AD-OPS** | Ad stack behavior — fill, eCPM, mediation, network mix |
| **NOISE** | Within normal variance / data artifact — say which |

And a causation flag: **correlational** / **causal-on-current-data** / **needs-experiment**. Never
"caused by" from correlation alone; where a rollout ladder exists, test proportionality — a metric
moving on a step but not in proportion is evidence *against* that build.

`Finding = {segment, route/stage, hypotheses[{statement, verdict, data}], attribution_bucket,
confidence, causation_flag, so_what}`.

## Axis coverage ledger (mandatory at a D3 close)

`references/investigation-axes.md` holds the canonical axis checklist generalized from the team's
investigation sheets, game-agnostic and mapped to cataloged sources only. A D3 close renders the
coverage ledger it defines — one row per axis: CHECKED (verdict + one-line evidence), BLOCKED (per the
grammar below), or N/A (why) — so the answer accounts for every standard axis the way the sheets did,
instead of only narrating the branch that paid off. The same file defines the intake-vs-behavior
(D0-bucket) shift-share and the recurring-pattern priors that may seed hypotheses; a prior is commentary
until verified on data queried this conversation.

## BLOCKED-note grammar (the only exclusion path)

A step that cannot be computed renders as:

> **BLOCKED — <schema-unclear | metric-not-found | query-failed | out-of-coverage>**: <what was
> attempted — datasource + field, **and the probe that established it**>. Ask: <the concrete data-eng
> request>.

Never a silent skip; never "N/A". Per the source lock, a metric whose data simply isn't in the catalog
is **metric-not-found** — name the closest cataloged proxy only if one exists, clearly labeled.

**A BLOCKED note is a claim, and every claim needs a query behind it (SR-20).** Before emitting one:

- **`out-of-coverage`** requires the source's live bounds, read this conversation, and the note quotes
  them. A coverage floor, row count or date range copied from a reference file is a snapshot and cannot
  ground the claim — sources get backfilled without the documentation following. **Per SR-20, the
  live-bounds probe is retried once before the note is emitted** — a first empty/short result can be a
  transient serving gap (segment reload, tier rebalance), not real absence; only a confirming second
  probe grounds `out-of-coverage`, and the note names both.
- **`metric-not-found`** requires either the catalog showing no datasource for it, or a live schema
  check on the datasource that would carry it — not an inference from a metric having a different name
  than expected.
- **`query-failed`** requires the failure to survive fixing the obvious causes first (version resolved
  this conversation, suffix sorted alphabetically, pins intact, identifiers quoted). A fixable query
  error is not a blocker.

A BLOCKED note that turns out to be wrong is worse than a missing step: it tells the reader the evidence
does not exist. When one is emitted and later disproved, say so plainly and re-run the step.

## Stop gates & closure

- Respect the depth budget (`depth-policy.md`): early-stop at ≥90% of the delta explained with
  corroborating evidence — where "explained" means localized to the **finest actionable grain** the
  playbook's chain names, per the depth-policy stop-gate rule; at budget end while inconclusive, say
  so and **offer** the next level.
- **A stage closes only when every step the playbook assigns to it has run, is BLOCKED, or is
  explicitly inapplicable (say which).** Work the current stage still owes is executed, never offered.
- **The suggested next question / escalation offer may only contain work OUTSIDE the current depth
  budget** — a deeper stage, or a different metric family belonging to another skill. Turning an
  in-scope step into a question back to the user is a protocol violation.
- **An assigned depth is a commitment to deliver at that depth.** Uncertainty about definitions,
  a premise that doesn't reconcile, a stale-looking reference, or a partly-blocked step all get
  resolved or flagged inside the answer — none of them downgrades the run. An investigation assigned
  D3 that returns clarifying questions instead of D3 findings has failed, however well-founded the
  questions were: ask at most one alongside the delivered analysis (SR-21), never in place of it.
- Close with: the drill path, the finding table (bucket + confidence + causation), what was ruled out,
  the single decisive next step (a check, a segment to watch, or an experiment), **and the visuals the
  depth requires (SR-22)** — load `game-viz-design` and render them. At D2+ that is never zero charts:
  the moved metric across both periods and the contributor breakdown at minimum, plus the mix-shift
  chart and evidence timeline at D3. **The lead hypothesis always gets a chart** (see Hypothesis
  discipline). An investigation whose entire output is prose and tables has not closed — the drill path
  is the argument, the chart is the evidence the reader can check at a glance.


## Pre-close checklist — run before writing ANY closing verdict (NOISE, SUPPORTED, or a stage close)

This is the gate a real routing incident (Aug 2026) exists to prevent: a coarse cut (e.g. `country`)
came back diffuse and got written up as NOISE without the chain ever reaching `install_source` — the
actionable grain the playbook actually named. **A closing verdict may not render unless every item below
is true.** Check them in this order; if any is false, the correct output is "continue the chain" or
"offer the next depth" — never a close.

1. **The playbook's named finest grain was actually queried this conversation** — not inferred, not
   skipped because a coarser level looked diffuse. For the engagement / retention / rolling-retention
   chains that is `install_source`; for rev/DAU it is the named ad network or mediation layer; for other
   playbooks it is whatever Stage D2/D3 names as actionable. **A diffuse result at a coarser grain
   (`country`, `install_bucket`, format-level) is a reason to go one level deeper, never a reason to
   stop** — "the chain looked flat so far" is evidence the wrong axis was cut so far, not evidence of
   NOISE.
2. **The annotations pull for the localized gid/cli/window actually ran** (protocol step 4) — not
   assumed empty, not skipped because the earlier levels looked inconclusive.
3. **Every hypothesis in the ~3-hypothesis set carries a verdict** (SUPPORTED / REJECTED / NOT-TESTED)
   with its evidence. **NOISE is itself a hypothesis and needs the same evidence bar as any other
   verdict** — it is never the default fallback for "nothing else was found" before the chain finished.
4. **The visuals and prose the depth requires actually rendered** (SR-22 / SR-23) — restated here because
   a closing verdict is exactly where skipping them is most tempting.
5. **At D3, the axis coverage ledger rendered** (`investigation-axes.md`) — every canonical axis
   accounted for as CHECKED / BLOCKED / N/A, none silently absent.
6. **Both sides of every rate/count pairing the playbook names were actually queried at the matching
   grain — not just whichever side happened to be checked first.** If the metric under investigation has
   a cataloged rate-or-yield formula (eCPM, retention rate, fill rate, CTR, conversion) and a cataloged
   count-or-volume formula (impressions, installs, sessions, users, requests) at the same segment grain,
   a closing verdict requires both to have been pulled this conversation — one clean-looking side is
   never grounds to skip the other, and "the volume ranking already told a concentrated story" is not a
   reason to leave the price/rate side unchecked (or the reverse). This is what caught the miss it
   exists to prevent: a network at ~1% of impression volume carried a real, ongoing eCPM decline that a
   volume-sorted contributor ranking never surfaced, because a ranking sorted by one side of a pairing
   is blind to a move concentrated on the other side of a small segment.

**A verdict that fails this checklist is not a defensible close — it is a premature stop wearing a
verdict's clothing.** If item 1 hasn't happened, the correct output is the next chain level's query, not
a rendered NOISE table. This checklist is unconditional at D2+, and it is satisfied only by the query
having actually run this conversation — stating the intent to check it is not sufficient.

**A closing verdict is a mechanism, not a location.** "The move is concentrated in segment X" names
where; it is not yet an explanation. A defensible close also names **which side of the pairing carried
it** — the rate/yield side, the count/volume side, or a mix shift between segments — with the number that
shows it, in the same sentence as the location. "Segment X drove the drop because its eCPM fell 19% while
its volume held" is a full verdict; "segment X drove the drop" alone is half of one, however confidently
it's stated, and does not satisfy this checklist even when every other item above is true.
