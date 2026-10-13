---
name: investigate-rev-dau
description: "BRIAN Tier-2 investigator — Rev/DAU drop/spike investigations, and revenue-vs-DAU divergences (\"revenue down but DAU flat\"). Use when Rev/DAU moved or the user asks why: \"rev/dau dropped\", \"ARPDAU fell\", \"monetization per user is down\", \"revenue fell but users didn't\". Staged playbook (D1 is-it-real on both sides of the ratio → D2 numerator-vs-denominator + ad-vs-IAP + contributors + admon annotations → D3 eCPM × imps/DAU chain + ad-funnel + segment quality cuts) per the brian-master investigation protocol. Renders its own charts by loading game-viz-design — at D2+ every answer ships at least a numerator-vs-denominator chart and a contributor breakdown. Data: chart_579/2077/4495/2160 via ps-data-catalog; user-level (ULD) rev_dau_install_diff_ilrd_v2 at D3 and revenue_reports for source × country / feed-lag checks.\n"
---

# Rev/DAU Investigator (Tier 2 · staged D1→D3)

Inherit `brian-master/references/shared-rules.md` + `investigation-protocol.md`; depth per hand-off.
Headline Rev/DAU = `chart_579` revenue ÷ its DAU variant (catalog `core-and-cohort.md`); decomposition
via `chart_2077` (pins: `mediation='overall'`, `ad_network='overall'`, filter `rev_type` — IAP is mixed
in), `chart_4495` (`network='overall'` pin), funnel via `chart_2160`. Ratio hygiene per SR-6: both
sides date-aligned, period totals then divide — never averaged daily ratios.

## Stage D1 — is the move real?

1. Freshness on BOTH variants (revenue and DAU deliver independently); known feed lags (xpromo ~10d,
   Apple Arcade ~4d) excluded and disclosed.
2. Anchored equal windows; rate metric so day-count trims are safe — but say them.
3. Verdict: real vs artifact. *Stop gate per protocol.* **A small delta, or one smaller than the level the user quoted, is not an artifact — only delivery lag/maturity/day-count issues are. A magnitude mismatch is SR-17/18 (test adjacent definitions), never grounds to call it not-real. Full rule: `investigation-protocol.md` § Stage zero.**

## Stage D2 — decompose the ratio, then the revenue

4. **Numerator vs denominator first — never investigate the ratio directly:** which actually moved?
   DAU-driven → the DAU side (source mix, new-vs-tenured via `cohort` buckets) and consider a hand-off
   note toward retention/engagement causes. Revenue-driven → continue here.
5. **Ad vs IAP split** (`chart_579` source_category, cross-checked `chart_2077` rev_type) —
   contribution-to-delta each.
6. **Format & network contributors — run the FULL chain before the stop gate** (`chart_2077`, one pin
   released at a time per catalog): rev_type (interstitial / rewarded / banner / app_open / IAP) →
   `ad_network` or `mediation` — concentrated or broad? The named network/mediation layer is the
   actionable grain; a format-level localization alone is not closure.
   **Price and volume, together, every time.** At that same network/mediation grain, pull **both**
   the volume side (impressions, requests, loads, users) **and** the yield side (eCPM =
   revenue/impressions) in the same pass — never volume alone, and never eCPM alone. Mediation
   waterfalls reorder by yield, so price and volume move together almost by construction; ranking
   contributors by volume-of-change only surfaces the segments with the biggest *counts*, which
   structurally cannot catch a real, concentrated price break on a small-share network (a network at
   ~1% of impression volume with a 20%+ eCPM drop is invisible to a volume-sorted ranking, and would
   have to be reported as a live finding, not filed away as noise for being small). The reverse gap is
   just as real: an eCPM-sorted view weighted by revenue share can miss a volume problem sitting on a
   large, flat-price network. Run both cuts on the same network list before asking whether the story is
   closed — one clean-looking axis is never grounds to skip the other.
7. **Admon annotations** on the localized window — stack opts quote their own expected impact: attribute
   ("the annotation claims +8.77% BN RPD"), verify against the metric, never paste the quoted % as data
   (SR-14).
8. **~3 hypotheses spanning different causal axes — never three flavors of the same axis.** A set like
   "network A concentration", "network B concentration", "network C concentration" is one axis
   (mix/volume) tested three ways and fails this step even with three rows. Cover price (eCPM
   compression, on a specific network or broad), volume (impression/request/fill decline, ad_ops or
   engagement-driven), and mix/segment (IAP lapse, install-source or geo mix shift toward low-yield
   segments) as distinct candidates — drop whichever axis step 6 already ruled out, but only after it
   was actually checked, not because it wasn't the first one found.

*Stop gate (only after the full contributor chain — volume AND price, per step 6): ≥90% explained at the
actionable grain → close; else offer D3.* **Pre-close gate: confirm (a) the named ad network/mediation
layer was actually queried this conversation, not just the format (`rev_type`) level, and (b) both the
volume-side and price-side cuts ran at that grain — a diffuse or clean-looking result on only one of the
two is a reason to go deeper, never a reason to close. Full checklist: `investigation-protocol.md` §
Pre-close checklist.**
**A closing verdict names the mechanism, not just the location.** "Concentrated in network X" is a
location. "Network X's revenue fell because its eCPM dropped 19% while its impression volume held" (or
"...because its impression volume collapsed while its eCPM held") is a verdict — state which side (price
or volume) carried the move, with the number that shows it, before calling anything closed. A verdict
that names where without naming why-price-or-volume is half a verdict and does not satisfy the stop gate.

## Stage D3 — the mechanical chain + quality cuts

9. **Ad Rev/DAU = eCPM × imps/DAU — split it:** eCPM by rev_type/network (`chart_2077`, `chart_4495`)
   vs impressions per DAU (`chart_4495` imps; its own in-chart dau only as denominator, per catalog).
   Price problem vs volume problem — different owners (AD-OPS vs GAME).
10. **Ad funnel** (`chart_2160`): request → fill (load/request) → view drops localize stack issues
    (AD-OPS) vs user-behavior drops (GAME). Fill-rate moves are AD-OPS by default.
11. **Segment quality cuts:** `payer_flag`, `lat_flag`, `cohort` age, country tier — a mix shift toward
    low-yield segments is CAMPAIGN/EXTERNAL, not a monetization break.
12. **Cross-checks:** sessions/time (`chart_2524` — fewer minutes = fewer ad slots), ad-type retention/
    churn (`chart_4495`) if aggressive pacing is hypothesized.
13. **User-level concentration (ULD — catalog `references/uld.md`):** from
    `dm_admon.rev_dau_install_diff_ilrd_v2` joined to `derived_tables.dau_splits`: did the broad base or
    the whales move? Per-user ad-revenue p50/p90/p99, top-1% share, payer vs non-payer rev/DAU,
    impressions per user by format. Cross any of these by the `dau_splits` segments the charts don't
    carry (OS version, device, build, install_source × payer). Remember `total_rev` = ad + 0.7 × IAP,
    xpromo excluded — it will not tie to `chart_579`. For a trailing dip, check `derived_tables.revenue_reports` by `rev_source` for a
    late feed (APS, Apple Arcade, xpromo lag ~9 days) before calling it real.
14. Finding table + **axis coverage ledger** (`brian-master/references/investigation-axes.md`) +
    drill path + decisive next step per protocol closure.

## Visuals — this skill renders its own (mandatory from D2)

**Load `game-viz-design` and render.** Charting is this skill's job; naming the skill in prose ships
nothing. Minimum set per SR-22:

- **D2 — both, always:** (a) the **numerator-vs-denominator chart** — revenue and DAU plotted together
  with Rev/DAU, so the reader sees which side moved rather than only the ratio; (b) a
  contribution-to-delta bar for the ad-vs-IAP split and the format/network contributors the chain
  reached.
- **D3 — add:** the mechanical split (eCPM against impressions per DAU — price problem vs volume
  problem, the chart that assigns the owner), the ad funnel as stage-to-stage conversion, and an
  evidence timeline against admon annotations.

**Currency, user counts and a per-user rate are three different units** — this is the investigator most
prone to an unreadable single-axis chart. Use a labeled dual axis (each axis titled with its series and
units, each legend entry naming its axis) or split into separate charts; never index or rescale to make
them fit (SR-8). Where an annotation quotes its own claimed impact, it may be marked on the timeline as
an annotation, never plotted as a data series (SR-14).

**Known limits (BLOCKED):** no impression-level ILRD and no first-eCPM decile in the cataloged sources
— metric-not-found when a hypothesis needs them.
