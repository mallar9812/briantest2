---
name: investigate-retention
description: "BRIAN Tier-2 investigator — classic retention (D1/D7/D30… dX) drop/spike investigations. Use when classic retention moved or the user asks why: \"D7 retention dropped\", \"retention fell for [game]\", \"investigate retention\", \"why is D1 retention up\". Runs a staged playbook (D1 is-it-real gate → D2 decomposition + annotations → D3 mix-shift + cross-metric sweep) with stop gates, hypothesis verdicts, and attribution buckets per the brian-master investigation protocol. Renders its own charts by loading game-viz-design — at D2+ every answer ships at least a retention trend and a contributor breakdown. NOT for rolling retention (flag-based D1/D3 rolling) — that is investigate-rolling-retention. Data: chart_1706 via ps-data-catalog; at D3 the user-level (ULD) dau_splits and adjust_installs for campaign/creative cohorts and segment combinations.\n"
---

# Retention Investigator (Tier 2 · staged D1→D3)

Inherit `brian-master/references/shared-rules.md` + `investigation-protocol.md`; depth per the hand-off
(`depth-policy.md`). Metric: classic retention = `dX_retained / installs` on the cohort chart
(`ps-data-catalog/references/core-and-cohort.md` — install-date-cohort grain).

**Definition gate on entry — resolve on the data, not on the wording.** Run protocol Stage zero before
Stage D1. "Rolling" anywhere in the ask → hand to `investigate-rolling-retention`. But **the absence of
that word settles nothing**: classic and rolling are routinely both called "retention" or "RR", and
they sit in visibly different bands for the same game and window.

- **Check the level first.** Where the user quotes a baseline, compute classic `dX_retained / installs`
  for their window and compare. Materially off their number → pull the rolling series over the same
  window before concluding anything (SR-17). Whichever family reproduces their level is the one they
  mean; adopt it, say so in one line, and hand off if it isn't this skill's.
- **A requested ratio may not exist here.** Report the nearest available in-family `Dx/Dy`, name the
  substitution, and give the sibling family's equivalent alongside it, labeled — never silently swap
  one family's ratio for the other's.
- **State the locked definition in the answer** — numerator, denominator, grain, and which family.
- A mismatch that survives all of this is a footnote, not a stop: proceed at the assigned depth on the
  best-grounded series with the discrepancy noted in one line (SR-18).

## Stage D1 — is the move real?

1. **Maturity before anything:** the affected dX computed only over install dates aged ≥ X days
   (SR-6); label the matured cohort window. A "drop" concentrated in unaged cohorts is a maturity
   artifact — close as NOISE.
2. **Delivery lag:** installs (denominator) and the retained field on their own freshness; trailing-day
   artifacts excluded and disclosed.
3. **Equal windows:** anchored periods, equal day counts, same dX both sides.
4. Verdict: real move vs data artifact. Artifact → report and stop. **A small delta, or one smaller than the level the user quoted, is not an artifact — only delivery lag/maturity/day-count issues are. A magnitude mismatch is SR-17/18 (test adjacent definitions), never grounds to call it not-real. Full rule: `investigation-protocol.md` § Stage zero.**

*Stop gate: real move + depth budget D1 → report the verdict and offer D2.*

## Stage D2 — localize + evidence

5. **Cohort vs calendar first:** did specific install cohorts worsen (install-date pattern — points at
   acquisition/onboarding), or did a calendar event cut across all cohort ages at once (points at a
   live change — check engagement/DAU by `cohort` age bucket for the same dates)?
6. **Ladder & cuts with contribution-to-delta — run the FULL chain before the stop gate:** `cli` →
   `country` → `install_bucket` → `install_source` (catalog dims). Bucket-level ("paid") is not
   closure — `install_source` is the actionable grain; the stop gate is evaluated only after the
   chain reaches it. Common across sources = GAME; scaling with one source = CAMPAIGN.
7. **Annotations** on the localized gid/cli/window (protocol step 4): releases stepping rollout %,
   experiment ramps, open Investigation windows.
8. Branch ~3 hypotheses (e.g. "one network's mix shifted", "build X hurt onboarding", "seasonal dip vs
   last 4 same-weekdays"), verdict each.

*Stop gate (only after the full contributor chain): ≥90% of the delta localized at the actionable
grain with corroborating evidence → close. Else offer D3.* **Pre-close gate: confirm `install_source`
was actually queried this conversation, not just `country`/`install_bucket` — a diffuse coarser cut is a
reason to go deeper, never a reason to close. Full checklist: `investigation-protocol.md` § Pre-close
checklist.**

## Stage D3 — mix shift + cross-metric sweep

9. **Install-mix shift-share:** did blended retention move because source mix moved (low-retaining
   networks/geos growing) with per-source retention flat? Quantify: mix effect vs rate effect.
10. **Cross-metric sweep, same window/segment:** D1 vs D7 (which broke first?), engagement
    (`chart_2524` sessions, `chart_2898` clears by `cohort` D00/D01/D02-D07), crashes/ANR by build
    (`chart_2856`/`2857`), notification sends/CTR (`chart_3341`). What else moved — and what
    conspicuously didn't — bounds the cause.
11. **Evidence timeline:** metric inflection vs annotation dates, proportionality against rollout
    ladders.
12. **Below-chart cuts (ULD — catalog `references/uld.md`):** (a) when the shift-share points at a
    source — `analytics.adjust_installs` (deduped on `(gid, cli, refid)`) for campaign / adgroup /
    creative cohorts, joined to `derived_tables.dau_splits` for their return on `actual_diff`;
    (b) segment combinations no `chart_1706` variant carries — OS version, device, build, LAT, ATT,
    payer, or any cross of them, from the `dau_splits` segments; (c) **intake vs behavior — the
    D0-bucket shift-share** (`brian-master/references/investigation-axes.md`): bucket the windows'
    installs by install-day activity (D0 sessions/clears per user from the ULD activity tables joined
    at `diff = 0`, buckets game-relative) and split the delta into bucket-mix shift (intake → CAMPAIGN)
    vs within-bucket retention change (GAME). Disclose `dau_splits` coverage vs chart installs before
    trusting any of these cuts; label every figure ULD; the headline rate stays on `chart_1706`.
13. Full finding table + **axis coverage ledger** (`investigation-axes.md`) + drill path + the one
    decisive next step, per protocol closure.

## Visuals — this skill renders its own (mandatory from D2)

**Load `game-viz-design` and render.** Charting is this skill's job, not something the router or another
analyst does afterwards; naming the skill in prose ships nothing. Minimum set per SR-22:

- **D2 — both, always:** (a) the affected `dX` retention rate by install-date cohort across the current
  and comparison windows, one line per period or one continuous series with the periods marked;
  (b) a contributor bar of contribution-to-delta at the actionable grain the chain reached.
- **D3 — add:** the mix-vs-rate shift-share (what moved because the install mix moved vs because
  per-segment rates moved), the D1-vs-D7 (or shorter-vs-longer `dX`) comparison showing which horizon
  broke first, and an evidence timeline marking annotation dates against the metric inflection.

Retention rates and install counts are different units — never force them onto one axis; use a labeled
dual axis or two charts, always actual values (SR-8). Cohort maturity cuts the series short: end the
plotted line at the last fully-matured install date and say so in the in-widget header rather than
letting an immature tail render as a cliff.

**Known limits (BLOCKED per protocol):** no FTUE **screen-level** funnel and no per-screen/dialog
events in the cataloged sources — name it metric-not-found when a hypothesis needs it, and offer the
activity-level proxy, labeled as a proxy. D0 **activity-level** conditioning is NOT blocked — it is step
12's ULD cut (sessions/clears on install day vs return).
