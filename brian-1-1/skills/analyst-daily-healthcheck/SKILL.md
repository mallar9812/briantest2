---
name: analyst-daily-healthcheck
description: "BRIAN Tier-1 analyst — the daily portfolio healthcheck at depth D1. Use for \"daily healthcheck\", \"morning scan\", \"anything broken today?\", \"portfolio health\", or as a scheduled task. Scans all games × core KPIs for the latest complete day (D-2) against a weekday-matched 4-week baseline, renders ONE traffic-light board (green/amber/red per game × metric) via game-viz-design, reports only flagged cells as bullets, and routes every red cell to the matching investigate-* skill at D2. \"All green\" is reported explicitly. Inherits brian-master shared rules; data via ps-data-catalog + ps-entities.\n"
---

# Daily Healthcheck Analyst (Tier 1 · depth D1 per cell)

Inherit `brian-master/references/shared-rules.md`. **Depth contract: every cell runs at D1** — metric +
delta + the is-it-real gate only. A red cell upgrades to **D2** (auto-suggest by default; auto-run only
if the user/schedule says so). Never straight to D3.

## Window & baseline

- **Assessment day:** D-2 (latest complete day per SR-6), stated explicitly.
- **Baseline:** same weekday over the prior 4 weeks — **median** (weekday-aware: Monday never compares
  to Sunday). Both windows named in the header.
- Where a metric is cohort-based (D1/D7 retention), compute on the matured cohort per SR-6 and label
  the cohort window.

## Scan set (all games with volume, × cli where material)

Per game: DAU · net revenue · gross revenue · Rev/DAU · spend · eCPI · installs · D1 retention ·
D7 retention (matured) · crash rate (fatal/DAU) · notification CTR. All from cataloged charts —
consolidate to one statement per variant across ALL games (catalog Fast path), never per-game
statements.

## Flag logic (per cell)

- **Green** — within noise: |Δ vs baseline| ≤ 10% (or within 2σ of that weekday's 4-week spread when
  computable from the returned day rows).
- **Amber** — 10% < |Δ| ≤ 20%, or a data-quality caveat (freshness trailing 2+ days, partial feed).
- **Red** — |Δ| > 20%, or a protected metric breaching 10%: D7 retention, Rev/DAU, total DAU, crash rate.
- **The D1 gate runs before any flag:** a trailing-day zero from delivery lag, an unmatured dX, an
  unequal-day artifact → the cell is marked "lag/maturity", never red. Known feed lags (xpromo ~10d,
  Apple Arcade ~4d per catalog) are annotated, not flagged.

## Output (SR-15 order)

1. Period & segment line: assessment day, baseline window, games in scope, "· depth D1".
2. **The traffic-light board** — one `game-viz-design` widget, games × metrics grid, deltas in-cell.
3. Bottom line: ≤3 bullets — the worst red with its delta and suspected axis, the best notable
   improvement, and the overall count ("3 red / 5 amber / 412 green cells").
4. **Flagged cells only** as bullets: game · metric · Δ (% + absolute) · is-it-real verdict · the
   matching `investigate-*` skill offered (or auto-run result).
5. **All green → say it explicitly** ("all 420 cells green — no action needed"); flat is a finding,
   never silence.

## Scheduling

When invoked by a scheduled task: unattended mode — state assumptions, auto-run D2 for red cells,
deliver the board + findings without waiting for answers.

<!-- SLOT: detailed actions from Tamanna (metric set adjustments, thresholds, auto-run policy) -->
