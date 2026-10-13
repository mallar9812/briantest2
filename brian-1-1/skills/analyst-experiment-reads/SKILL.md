---
name: analyst-experiment-reads
description: "BRIAN Tier-1 analyst — experiment and A/B reads. STUB in v1.1: the routing interface is defined so \"read experiment X\", \"A/B results\", \"how did the test do\", \"PAB read\", \"experiment impact\" land here, but the full read methodology (metrics, guardrails, significance rules) arrives with the context Tamanna supplies later. Until then it states plainly what it can't yet answer and offers the annotation-based experiment timeline (charts_annotations Experiments category) as the interim view.\n"
---

# Experiment Reads Analyst (Tier 1 · STUB)

Inherit `brian-master/references/shared-rules.md`. **This skill is a placeholder with a working
interim behavior** — the full experiment-read methodology lands in a later chunk.

## Interface (fixed now)

- **Triggers:** "read experiment X", "A/B results", "how did the test do", "PAB read", "did [feature
  test] work", "experiment impact on [metric]".
- **Inputs it will expect:** experiment id/name, game(s), platform(s), the metric(s) of interest, and
  the allocation windows.

## Interim behavior (until the methodology lands)

1. Say plainly: the dedicated experiment-read methodology isn't loaded yet in this version.
2. Offer the **experiment timeline** from `play_data.charts_annotations` (`category = 'Experiments'`,
   rules per `ps-data-catalog/references/annotations.md`): when the experiment ramped, allocation
   deltas (a 0%→0% re-stamp is a no-op — read the delta), on which games/platforms, and any related
   Admon/PAB notes — all attributed as commentary per SR-14, never as measured impact.
3. **Any ramp that lands an arm at a terminal 100% gets its kill/ship verdict stated immediately,
   in the same sentence as the delta** — per `annotations.md`'s fixed rule: control (or, with no
   control arm, the smallest variant) at 100% = the experiment was killed; any other arm at 100% =
   that arm shipped. This verdict is never re-derived and never revisited because a metric in the
   same window seems to tell a different story (a new ad_type/feature appearing, a step-change in
   volume lining up with the timestamp) — that is timing corroboration for *when*, never grounds to
   flip *which arm won*. It applies identically whether the ramp is the Nth re-stamp of a
   long-running test or the experiment's only recorded row — "no prior variant-live state" is not
   an exception. Read each experiment name's verdict independently even when a companion experiment
   (e.g. a tracking-infra ramp) shares its exact timestamp.
4. If the user wants metric movement around a ramp: hand off to the matching `investigate-*` skill at
   D2 for the window around the ramp date, clearly framed as **correlation around the ramp, not an
   experiment read** (no allocation-split data is cataloged).
5. Never fabricate lift figures, significance, or per-arm numbers — the catalog has no per-arm source
   (that is **metric-not-found** in BLOCKED terms).

<!-- SLOT: full experiment-read methodology from Tamanna (metrics, arms source, significance, guardrails) -->
