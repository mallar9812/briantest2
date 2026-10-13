# Investigation Axes — canonical checklist, coverage ledger, priors

Generalized from the team's per-metric investigation sheets (the rolling-retention / install-retention /
session-time / engagement checklists and their historical RCA logs). **Game-agnostic:** every axis is
phrased against a cataloged chart dimension or a documented ULD table, never a per-game event or screen
name. This file does three jobs: (1) the canonical axis list every investigator can draw cuts and
hypotheses from, (2) the **coverage ledger** a D3 close renders so the answer accounts for every
standard axis the way the sheets did, (3) recurring-pattern **priors** from past investigations that
seed hypotheses — never verdicts.

Nothing here changes routing, depth budgets, or the stop gates: an axis whose stage is deeper than the
assigned depth is offered, not run. Raw-event sources (`sub_tables.tracking_slice_critical`,
`experiment.users_v2`) stay out of scope per `ps-data-catalog` — axes that need them are listed below as
BLOCKED so they are declared, not silently skipped.

## The canonical axes

| Axis | The sheets' question, generalized | Source (BRIAN 1.1 cataloged only) | Earliest stage |
|---|---|---|---|
| Platform | Both platforms, or one? | chart `cli` dim | D2 |
| OS version / device | OS-version-specific? Device-specific? | ULD `derived_tables.dau_splits` segments (OS, device, ATT, LAT) | D3 |
| Geo | Geo-specific? Tier/geo mix shift? New geos? | chart `country` dim; tiers via `ps-entities` | D2 |
| Cohorts | Which cohort ages? New vs tenured? Travelling (an install wave aging through buckets) vs accumulated? | chart `cohort` age buckets; `diff` / `actual_diff` on ULD | D2 |
| Install source | Which sources? Are *stable* sources hit too? | chart `install_bucket` → `install_source` (the actionable grain) | D2 |
| Install / cohort mix | Mix vs rate (shift-share)? Volume vs quality? Did CPI move with it? | charts + shift-share; CPI/IPM/CTR side on `chart_2454` (always by `network_name`) | D2–D3 |
| Campaign / creative / bids | Campaign-level? New creatives? Bid changes showing as quality shift? | ULD `analytics.adjust_installs` (deduped `(gid, cli, refid)`) × `dau_splits` return/flags | D3 |
| Build | From a build? Proportional to its rollout ladder? | crash charts by build; `build` on `dau_splits` / ULD engagement; Releases annotations | D2–D3 |
| Stability | Crashes/ANR up? A new error class? | `chart_2856` / `chart_2857` | D2 |
| Player type | Heavy vs light? Payer vs non-payer? | ULD `dau_splits.payer_flag` + user-day joins | D3 |
| Mode / feature | Which mode / action moved? | `puzzle_type` / `action_type` dims; ULD `engagement_puzzle_master_cc_col` | D2–D3 |
| Per-user distribution | Broad move or concentrated? Which percentiles (p50/p90/p99)? Zero-activity share? | ULD `sessions_master_cc`, `rev_dau_install_diff_ilrd_v2`, engagement table | D3 |
| D0 behavior → return | "D0 funnel / FTUE experience" at the activity level: intake vs behavior (below) | ULD activity tables at `diff = 0` × `dau_splits` return flags | D3 |
| Re-engagement | Notification sends/CTR/permissions, PSPN/xpromo changes | `chart_3341`; permission dims on engagement charts | D2–D3 |
| Economy | Earn/spend/sink mix, wallet level by cohort age | ULD `economy_master_cc` (`cash_type` filtered), `wallet_dau_install_diff` | D3 |
| Experiments | Scope exists? Drop ≈ effect × variant share? Two experiments interacting? | annotations (Experiments category) as the evidence layer; allocation table out of scope | evidence only |
| Data sanity | Pipeline delay? Event drop? Definition change? ULD-vs-chart coverage sane? | D1 gate (freshness/maturity/alignment) + the coverage disclosure rule in `uld.md` | D1 |
| Reinstalls | Reinstall share change? | partial — `dau_splits` keeps first attribution; differences vs `adjust_installs` are the only documented signal. Flag, don't quantify | flag |
| UX / screens / dialogs / FTUE steps | Which screen or dialog? | **BLOCKED** (raw client events undocumented) — labeled proxy: view→clear by mode from the ULD engagement table | BLOCKED |
| ASO / keywords | Store listing changes? | **BLOCKED** — no cataloged source | BLOCKED |

Axis questions are hypothesis-generating, not a mandate to query everything: the playbook's chain and
the depth budget still decide what runs. What the ledger (next) forbids is leaving a standard axis
*unaccounted for*.

## The coverage ledger — mandatory at a D3 close

The sheets tracked every axis with a Status and a Comment; a BRIAN D3 close does the same. Render one
compact table (one line per axis, SR-28 applies):

| Axis | Status | Evidence / reason |
|---|---|---|

- **CHECKED — <verdict>**: the axis was queried this conversation; one line of evidence (the number).
- **BLOCKED — <type>**: per the protocol's BLOCKED-note grammar, probe included.
- **N/A — <why>**: the axis doesn't apply to this metric/segment (say why), or sits beyond the assigned
  depth (then it belongs in the escalation offer instead).

A CHECKED row requires the query to have actually run this conversation (SR-20) — the ledger is an
account of work done, never a plan. At D2 the ledger is optional; when omitted, the pre-close checklist
still governs what must have run. The ledger never expands the depth budget — it makes the budget's
spending visible.

## Intake vs behavior — the D0-bucket shift-share (D3 technique)

The sheets' recurring fork — "is it install quality (intake) or did the game change (behavior)?" — made
rigorous, on documented ULD tables only:

1. **Bucket installs by install-day activity.** For each install cohort in both windows, compute D0
   activity per user (sessions from `sessions_master_cc` and/or clears from
   `engagement_puzzle_master_cc_col`, aggregated to the user-day, joined to `dau_splits` at
   `diff = 0`, `install_bucket <> 'reject'`). Buckets are game-relative — quartiles (or 0 / low / mid /
   high splits) of the *baseline* window's distribution — never fixed counts, so the same recipe works
   for every game.
2. **Split the delta.** Between baseline and current cohorts, decompose the retention/return/engagement
   move into **bucket-mix shift** (more installs landing in low-activity buckets at unchanged
   within-bucket rates → intake: CAMPAIGN, cross-check `adjust_installs` campaign/creative mix and
   `chart_2454` CPI side) vs **within-bucket rate change** (the same-activity users now return/do less →
   GAME: cross-check builds, annotations, stability). Return = `d1_rr_flag`/`d3_rr_flag` or presence at
   `actual_diff = X`, per the metric under investigation.
3. **Report both components** with contribution-to-delta, mirrored on the chart headline. All figures
   labeled user-level (ULD) with the population filter and the `dau_splits` coverage disclosure; the
   headline number stays on the chart.

This is the cataloged-table equivalent of a D0-engagement-bucket analysis — it needs nothing outside
the eight ULD tables.

## Recurring patterns — priors from past investigations (never data)

Hypothesis seeds distilled from the historical RCA logs. A prior earns a verdict only from data queried
this conversation (SR-14/SR-20); quote none of these as findings.

- **OS-rollout cohorts:** installs on a brand-new major OS version retain/behave worse until parity
  (often weeks); blended metrics move while same-OS metrics are flat. Cut by OS version (ULD).
- **Travelling cohorts:** one unusual install wave ages through D-bucket windows, moving "D60+"-style
  metrics months later with nothing live changing. Check install-date origin of the moved buckets.
- **Mix overtaking rate:** a higher- or lower-retaining segment's *share* grows (OS upgrade waves,
  network ramps, preload deals) and the blend moves with per-segment rates flat — always run shift-share
  before blaming the product.
- **Auth/login dependency breakage:** third-party login or similar external-dependency failure moves
  retention with no build release; shows as a platform- or OS-specific step with clean stability charts.
- **Staged-rollout build damage:** a metric stepping with a Releases annotation's rollout % — test
  proportionality; moving on a step but *not* in proportion is evidence against that build.
- **Ad-experience shifts:** network/mediation mix or time-per-ad changes (interstitial, rewarded/W2E)
  move rolling retention and session time without any game change — AD-OPS; check admon annotations.
- **Feature ramp arithmetic:** an experiment or feature at X% allocation moves the blend by roughly
  effect × X%; a blended step that matches an annotation's ramp share is attribution, pending the
  variant read.
- **External/seasonal:** the move is visible across games and year-on-year with internal metrics
  (engagement, economy, stability) flat — EXTERNAL; compare peers before drilling deeper.
- **Feed lag masquerading as a drop:** a trailing-window revenue/return dip inside a known delivery lag
  — the D1 gate, not a finding.
