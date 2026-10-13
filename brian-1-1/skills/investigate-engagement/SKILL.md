---
name: investigate-engagement
description: "BRIAN Tier-2 investigator — engagement drop/spike investigations: sessions, time spent, sessions/DAU, actions per DAU, clears, WAU/MAU stickiness. Use when engagement moved or the user asks why: \"engagement dropped\", \"sessions fell\", \"time spent down\", \"why did actions per DAU move\", \"stickiness declined\". Staged playbook (D1 is-it-real → D2 surface-vs-depth split + contributors + annotations → D3 mode/action cuts + notification & crash cross-checks) per the brian-master investigation protocol. Renders its own charts by loading game-viz-design — at D2+ every answer ships at least a surface-vs-depth component chart and a contributor breakdown. Data: chart_2524/2898/2888/2076 via ps-data-catalog; at D3 the user-level (ULD) tables sessions_master_cc, engagement_puzzle_master_cc_col, economy_master_cc and wallet_dau_install_diff for breadth-vs-depth and per-user distributions. NOT for retention metrics — those have their own investigators.\n"
---

# Engagement Investigator (Tier 2 · staged D1→D3)

Inherit `brian-master/references/shared-rules.md` + `investigation-protocol.md`; depth per hand-off.
Sources: `ps-data-catalog/references/engagement.md` — pin `id_type='rid'` everywhere it exists;
sessions/time from `chart_2524`, actions from `chart_2898` (mind the `puzzle_type` rollup), WAU/MAU
from `chart_2888`, the per-DAU denominator from `chart_2076` per the catalog's fixed cross-dataset
ratio rule.

## Stage D1 — is the move real?

1. Freshness per variant; anchored equal windows; ratio dates aligned (SR-6).
2. **Definition check:** sessions counting rules differ by gid (start/resume vs app_pause; time caps —
   catalog); a metric-definition boundary crossing is an artifact, not a move.
3. Verdict: real vs artifact. *Stop gate as per protocol.* **A small delta, or one smaller than the level the user quoted, is not an artifact — only delivery lag/maturity/day-count issues are. A magnitude mismatch is SR-17/18 (test adjacent definitions), never grounds to call it not-real. Full rule: `investigation-protocol.md` § Stage zero.**

## Stage D2 — split, localize, evidence

4. **Surface vs depth first — never investigate the blended number:** DAU-driven (fewer users, per-user
   flat) vs per-user-driven (same users doing less). Compute DAU, sessions/DAU, time/session,
   actions/DAU separately and name which component moved.
5. **Recency cut:** by `cohort` age bucket (D00 / D01 / D02-D07 / …) — new-user engagement breaking
   points at onboarding/UA; tenured-user decline points at a live change or fatigue.
6. **Contributors — run the FULL chain before the stop gate:** `cli` → `country` → `install_bucket`
   → `install_source`, contribution-to-delta at each level; `install_source` is the actionable grain
   and the stop gate is evaluated only after the chain reaches it.
7. **Annotations** on the localized window — `Runtime` config flips matter more here than anywhere
   else; still read Releases/Experiments first per protocol order.
8. ~3 hypotheses with verdicts.

*Stop gate (only after the full contributor chain): ≥90% explained at the actionable grain → close;
else offer D3.* **Pre-close gate: confirm `install_source` was actually queried this conversation, not
just `country`/`install_bucket` — a diffuse coarser cut is a reason to go deeper, never a reason to
close. Full checklist: `investigation-protocol.md` § Pre-close checklist.**

## Stage D3 — which behavior, and what else

9. **Mode/action cuts:** `puzzle_type` (named modes vs the `w/o puzzle_type` rollup — never both) and
   `action_type` (clear, view, play, fail, use_hint…) — WHICH behavior moved; clears-vs-fails shifts
   hint at difficulty/content.
10. **Cross-checks, same window/segment:** notifications (`chart_3341` sends/CTR — a send-volume change
    is a classic engagement mover), crashes/ANR by build (`chart_2856`/`2857`), session-bucket mix
    (S01 vs S03-S05 — frequency vs intensity), economy flows (`chart_2917`, category-pinned) when the
    move looks reward-loop shaped.
11. **Survivorship check:** stickiness (dau/mau) can rise while DAU falls because casual users left —
    test before celebrating a "quality improvement".
12. **User-level cut (ULD — catalog `references/uld.md`):** breadth vs depth — did fewer users play,
    or did the same users play less? From `server_tables.sessions_master_cc` and
    `server_tables.engagement_puzzle_master_cc_col` (aggregated to the user-day, LEFT JOINed onto
    `derived_tables.dau_splits`): zero-session DAU share, p50/p90 minutes and clears per user, heavy-player
    bucket shift, current vs prior window. When the move looks reward-loop shaped, add
    `server_tables.economy_master_cc` (`cash_type='cash'`: % of DAU spending, sink mix) and
    `derived_tables.wallet_dau_install_diff` (median wallet by cohort age). Cut any of these by the
    `dau_splits` segments the charts don't carry (OS version, device, build, payer, LAT). For a new-user
    move, the **intake-vs-behavior D0-bucket shift-share**
    (`brian-master/references/investigation-axes.md`) separates install quality from a game change.
    Screen/dialog-level funnels are not in the cataloged sources — the labeled proxy is view→clear
    conversion by `puzzle_type`/`action_type` from the engagement table. Disclose `dau_splits` coverage;
    label ULD figures; the headline stays on `chart_2524`/`chart_2898`.
13. Finding table + **axis coverage ledger** (`investigation-axes.md`) + drill path + decisive next
    step per protocol closure.

## Visuals — this skill renders its own (mandatory from D2)

**Load `game-viz-design` and render.** Charting is this skill's job; naming the skill in prose ships
nothing. Minimum set per SR-22:

- **D2 — both, always:** (a) the **surface-vs-depth decomposition** — DAU, sessions/DAU and
  time/session (or actions/DAU) as separate series so the reader sees which component moved, since the
  blended number is exactly what this stage refuses to investigate; (b) a contributor bar of
  contribution-to-delta at the actionable grain the chain reached.
- **D3 — add:** the mode/action breakdown (`puzzle_type` or `action_type` — named modes **or** the
  rollup, never both in one chart), the cohort-age cut, and an evidence timeline against annotations.

A user count and a per-user rate never share an axis — labeled dual axis or separate charts, actual
values only (SR-8). When a cross-check metric is plotted beside the engagement series to show
coincidence, label it as a cross-check **inside its own legend entry** (`● Crashes/DAU | cross-check,
not a driver`) so it isn't read as a driver — not in a prose line above the chart.

**Known limits (BLOCKED):** no screen/dialog-level funnels and no per-level difficulty curves in the
cataloged sources — metric-not-found when a hypothesis needs them (view→clear by mode is the labeled
proxy). D0-engagement buckets are NOT blocked — they are constructible from the ULD activity tables
(step 12, `investigation-axes.md`).
