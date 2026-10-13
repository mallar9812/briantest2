---
name: investigate-rolling-retention
description: "BRIAN Tier-2 investigator — rolling retention (flag-based D1/D3 rolling) drop/spike investigations. Use when rolling retention moved or the user asks why: \"rolling retention dropped\", \"D1 rolling fell\", \"D3 rolling moved for [game]\". Rolling = active ON OR AFTER day X post-install — a different metric from classic dX retention, never blended with it. Staged playbook (D1 definition + equal-cohort-age gate → D2 contributors + classic-retention cross-check + annotations → D3 return-behavior analysis) per the brian-master investigation protocol. Renders its own charts by loading game-viz-design — at D2+ every answer ships at least a rolling-rate trend and a contributor breakdown. Data: chart_2301 (metric dim: D01_rolling / D03_rolling) via ps-data-catalog; at D3 the user-level (ULD) dau_splits (d1_rr_flag / d3_rr_flag) for segment combinations.\n"
---

# Rolling Retention Investigator (Tier 2 · staged D1→D3)

Inherit `brian-master/references/shared-rules.md` + `investigation-protocol.md`; depth per hand-off.
Source: `chart_2301` (`retained_users` by the `metric` dimension — `D01_rolling` / `D03_rolling`,
**populations overlap, never sum across both**); rate denominator = `chart_2076` dau per the catalog's
fixed cross-dataset ratio rule; both pins `id_type='rid'`.

## Stage D1 — definition + is it real?

1. **Definition gate, stated in the answer:** rolling = active **on or after** day X (flag-based).
   Never compare against or blend with classic dX retention in one series; if the user actually means
   classic → hand to `investigate-retention`. **Settle which family on the data, not the wording** —
   the word "rolling" being absent from the ask is not evidence the user means classic, and the two
   families sit in visibly different bands. Where the user quotes a baseline, compute this family's
   rate for their window and compare; if it is materially off, pull the classic series over the same
   window before concluding, and adopt whichever reproduces their level (SR-17, protocol Stage zero).
   **Verify the denominator before judging the fit** — a rate landing near a clean multiple or fraction
   of the quoted level is an unpinned or wrong-grain denominator, not a different metric family
   (SR-19); confirm the mandatory pins survived before deciding the family is wrong.
   **Only day indices the flag dimension actually carries exist here.** A ratio the user names across
   other day indices is not available in this family: give the nearest in-family ratio, name the
   substitution, and add the classic-family equivalent alongside it, labeled — never present one
   family's ratio as the other's.
2. **Equal cohort age:** rolling flags keep updating as cohorts age, so recent cohorts are structurally
   understated. Compare cohorts only at equal age; label the matured window (SR-6).
3. Freshness both charts; anchored equal windows; which window moved (D01, D03, or both).
4. Verdict: real vs artifact. *Stop gate per protocol.* **A small delta, or one smaller than the level the user quoted, is not an artifact — only delivery lag/maturity/day-count issues are. A magnitude mismatch is SR-17/18 (test adjacent definitions), never grounds to call it not-real. Full rule: `investigation-protocol.md` § Stage zero.**

## Stage D2 — localize + cross-check + evidence

5. **Contributors — run the FULL chain before the stop gate:** `cli` → `country` → `install_bucket`
   → `install_source`, contribution-to-delta at each level. A bucket-level localization ("paid
   Android") is not closure — `install_source` (which network) is the actionable grain, and the
   stage's stop gate is evaluated only after the chain reaches it. Never offer a remaining chain
   level as a "next question".
6. **Classic-retention cross-check, same window/segment:** rolling moving while classic D1/D7 is flat
   usually means **return behavior** changed (users still come back eventually, or stopped coming back
   late) rather than onboarding — that's the fork that decides Stage D3's direction. Both moving
   together → the cause likely lives in `investigate-retention` territory; say so in the hand-off note.
7. **Annotations** on the localized window — **notification/PSPN and xpromo changes are the prime
   category** for rolling moves; then Releases/Experiments per protocol order.
8. ~3 hypotheses with verdicts.

*Stop gate (only after the full contributor chain): ≥90% explained at the actionable grain → close;
else offer D3.* **Pre-close gate: confirm `install_source` was actually queried this conversation, not
just `country`/`install_bucket` — a diffuse coarser cut is a reason to go deeper, never a reason to
close. Full checklist: `investigation-protocol.md` § Pre-close checklist.**

## Stage D3 — return-behavior analysis

9. **Re-engagement channels, same window/segment:** notification sends/CTR/permissions (`chart_3341`,
   `chart_2076` permission_givers, `notif_permission` dim on the engagement charts) — a send-volume or
   permission-mix change moves rolling retention with no product change.
10. **Returning-user engagement:** sessions/actions for later `cohort` age buckets (D02-D07, D08-D14) —
    did the users who return do less, or did fewer return at all?
11. **Mix shift:** source mix toward low-return networks/geos, quantified mix-vs-rate.
12. **Segment combinations (ULD — catalog `references/uld.md`):** `derived_tables.dau_splits`
    `d1_rr_flag` / `d3_rr_flag` (active on `dau_date`+1 / +3 — final only at ≤ today−5) for cuts no
    `chart_2301` variant carries — OS version, device, build, LAT, payer, notification permission, or
    any cross of them; campaign / adgroup / creative cohorts via `analytics.adjust_installs` (deduped
    on `(gid, cli, refid)`) joined to those flags; returning users' sessions/clears from the ULD
    activity tables; and, when step 6's fork points at new-cohort quality, the **intake-vs-behavior
    D0-bucket shift-share** (`brian-master/references/investigation-axes.md`) on the return flags.
    Disclose `dau_splits` coverage vs the chart base; label ULD figures; the headline stays on
    `chart_2301`.
13. Evidence timeline; **axis coverage ledger** (`investigation-axes.md`) + finding table + drill path
    + decisive next step per protocol closure.

## Visuals — this skill renders its own (mandatory from D2)

**Load `game-viz-design` and render.** Charting is this skill's job; naming the skill in prose ships
nothing. Minimum set per SR-22:

- **D2 — both, always:** (a) the rolling-retention rate over the window, **`D01_rolling` and
  `D03_rolling` as separate series — never summed, never stacked** (the populations overlap);
  (b) a contributor bar of contribution-to-delta at the actionable grain the chain reached.
- **D3 — add:** the return-behavior view (re-engagement volume against the rate), the mix-vs-rate
  shift-share, and an evidence timeline marking annotation dates against the inflection.

**The classic-retention cross-check is the one chart most likely to mislead here.** Rolling and classic
are different metrics on different denominators and sit in different bands — plotting them as two plain
lines invites the reader to compare levels that are not comparable. Use two charts, or one chart with a
labeled dual axis where each series' legend entry names its axis *and* its definition. Never blend them
into a single series, and never let a shared axis imply one is "higher" than the other.

**Known limits (BLOCKED):** no per-user return-path sequences in the cataloged sources —
metric-not-found when a hypothesis needs them.
