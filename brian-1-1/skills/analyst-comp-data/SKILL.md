---
name: analyst-comp-data
description: "BRIAN Tier-1 analyst — competitor and market benchmarking from Sensor Tower estimates. Use when the user names a competitor or rival app, asks for market/genre benchmarks, category rankings, or \"[competitor] vs us\". Strictly opt-in (never pulls competitor data uninvited), every figure labeled \"Sensor Tower estimate\", never blended with internal numbers in one series; cross-comparisons pull the Playsimple side from internal charts labeled \"Playsimple — internal\". Competitor-only answers close by offering matching Playsimple numbers. Inherits brian-master shared rules; sources via ps-data-catalog references/competitor.md.\n"
---

# Comp Data Analyst (Tier 1 · depth D0; D2 on a "why")

Inherit `brian-master/references/shared-rules.md`. Sources: `external_data.sensor_tower_data` +
`external_data.st_product_details` (Trino) — rules, fields and query shapes in
`ps-data-catalog/references/competitor.md`. Read it before the first competitor query.

## Hard rules

1. **Opt-in only.** Query Sensor Tower only when the user explicitly asks about a competitor, rival
   app, or market/genre benchmark. Never enrich an internal answer with competitor data uninvited.
2. **Resolve competitor names via `st_product_details`** (product_id) — never through the GID mapping.
   Ambiguous name → ask, don't guess.
3. **Label everything** "Sensor Tower estimate" — in chart legends, table headers, and prose. These are
   modeled estimates; treat directionally, and say so when magnitudes matter.
4. **Never blend.** Internal and Sensor Tower figures never share a series or a summed total. For
   cross-comparisons, query Playsimple's side from its internal charts and label each row/series
   **"Playsimple — internal"** vs **"[Competitor] — Sensor Tower estimate"**.
5. **PoP per SR-7 applies to competitor figures too** — WoW/MoM/YoY with % and absolute.
6. **The closing offer:** a competitor-only response ends by offering matching Playsimple numbers. On
   yes: pick the closest Playsimple title (Procedure A in `analyst-game-performance`, or ask), query
   internally, present side by side. Skip the offer if a comparison is already present or was declined.
7. Verdicts per SR-11/12 — a competitor "outperforming us" claim needs the comparison shown, and the
   estimate caveat attached.

## Depth

- D0: benchmark tables/charts with deltas.
- D2 (user asks why a competitor/market moved): the investigation protocol applies, but the evidence
  layer is limited — no internal annotations exist for competitors; say plainly that causes outside
  Sensor Tower's estimates (their LiveOps, their UA) are not observable, and tag findings EXTERNAL
  with causation "correlational".

## Visuals — this skill renders its own (per SR-22)

**Load `game-viz-design` and render**; naming the skill in prose ships nothing. A benchmark is a
comparison, and a comparison is the case a chart serves best — D2 always ships at least one.

**The labeling rules are stricter here than anywhere else.** Estimated and internal figures may never
share a series, and where both appear on one chart each series' legend entry carries its provenance
("Sensor Tower estimate" / "Playsimple — internal") and the in-widget header says the chart mixes
sources. If that can't be made unambiguous at a glance, use two charts. An unlabeled competitor series
sitting beside an internal one reads as a like-for-like measurement, which it is not.
