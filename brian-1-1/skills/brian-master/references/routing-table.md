# Routing Table — trigger phrases → analyst skill

Match the question's *intent*, not just keywords. First match from the top wins; a "why/investigate"
qualifier overrides a summary phrasing.

| Trigger patterns (examples) | Skill | Depth |
|---|---|---|
| "investigate…", "root cause…", "deep dive on [metric]", "why exactly…" | matching `investigate-*` | D3 |
| "why did [classic] retention drop/spike", "D7 retention fell" | `investigate-retention` | D2 |
| "rolling retention dropped", "D1/D3 rolling moved" | `investigate-rolling-retention` | D2 |
| "why did sessions/time spent/actions per DAU/stickiness drop", "engagement fell" | `investigate-engagement` | D2 |
| "Rev/DAU dropped", "revenue down but DAU flat", "why did rev/dau move" | `investigate-rev-dau` | D2 |
| "why did revenue/DAU/spend/ROAS move" (no single owning investigator) | `analyst-game-performance` runs the investigation protocol at D2 for that metric | D2 |
| "daily healthcheck", "morning scan", "anything broken today?", "portfolio health" | `analyst-daily-healthcheck` | D1 |
| "compare A vs B", "which game is best", "top N games/franchises/countries by [metric]", "rank the portfolio", any ask covering 2+ entities side by side | `analyst-game-performance` | **D1-C** |
| "break CPI into CPM and IPM", "CTR / click-to-install / IPM / CPM for X", "why did CPI move" (UA delivery, creative type, network), CPI decomposition inside a ROAS analysis | `analyst-game-performance` (Procedure D, `chart_2454`) | D2 |
| "how is [game/franchise/portfolio] performing/doing", "KPI summary", "dashboard for X", "ROAS/LTV/spend/eCPI for X", "LiveOps impact" | `analyst-game-performance` | D0 |
| "read experiment X", "A/B results", "how did the test do", "PAB read" | `analyst-experiment-reads` | stub |
| User-level asks with no chart equivalent — "what % of DAU [did X]", "distribution / p50 / p90 of [minutes, clears, revenue, wallet] per user", "how many users [segment A] and [segment B]", "installs / revenue by campaign, adgroup or creative", "reported revenue by source and country" | the analyst that owns the metric family (engagement → `investigate-engagement`, revenue → `investigate-rev-dau`, installs/attribution → `analyst-game-performance`) using the ULD layer (catalog `references/uld.md`) | D0 for a plain lookup; D3 when the ask is "why" |
| "what does [metric] mean", "formula for X", "which table/chart holds X", "values of [dimension]", "define…", quick single-number lookups | `analyst-general-questions` | D0 |
| "[competitor] performance", "vs [rival app]", "market/genre benchmark", "Sensor Tower…" | `analyst-comp-data` | D0; D2 when asked why |
| "make a report/deck/PDF of…", "monthly/quarterly review deck", "export this to slides", "one-pager on…" | primary analyst answers, then `ps-brand-report` formats | **max(inherit, D2-R)** |

**Row order is load-bearing.** The D1-C comparison row sits **above** the D0 "how is X performing" row
because first match from the top wins, and a multi-entity ask phrased as a performance question ("how
are Word Trip and Word Bingo performing") otherwise matches the D0 row first and runs a comparison at
D0. Do not reorder these two.

Tie-breaks:

- A named metric with a named direction ("retention **dropped**") beats a generic summary phrasing.
- "How is X doing **and why is retention down**" → `analyst-game-performance` (primary) at D0, with an
  immediate hand-off of the retention part to `investigate-retention` at D2.
- Anything mentioning a competitor name routes competitor parts to `analyst-comp-data`; internal parts
  stay with the primary analyst — never blended in one series.
- **A deliverable qualifier raises the depth floor, it does not change the analyst.** "How is the
  portfolio doing — as a deck" still routes to `analyst-game-performance`, but at **D2-R**, not D0:
  the deck's Breakdowns and Detail sections need cuts that D0 forbids. See `depth-policy.md` § D2-R.
  Never let the formatting request read as a formatting-only request.

## Same-label metric families — the routing trap

The rows above read as if each metric name maps to one skill. Several do not. **Distinct metric
families share short labels, day-index notation (`D1`, `D7`), and abbreviations, and a user naming one
almost never spells out which family they mean.** Routing these on keyword presence is the single
easiest way to run a flawless investigation on the wrong series.

Known overlaps to treat as ambiguous by default:

| Ambiguous ask | Candidate families | Owning skills |
|---|---|---|
| "retention", "RR", "D1/D7 retention", "retention ratio" | classic install-cohort `dX` · flag-based rolling · activity-based return rates | `investigate-retention` · `investigate-rolling-retention` |
| "engagement", "activity", "usage" | sessions/time-spent · in-game actions · WAU/MAU stickiness | `investigate-engagement` (one skill, but different charts and bands) |
| "revenue per user", "ARPDAU", "RPD" | Rev/DAU on activity grain · cohort LTV on install grain | `investigate-rev-dau` · `analyst-game-performance` |

How to break them — in order, stopping at the first that decides:

1. **The level.** Each family occupies its own band for the same game and window. A level the user
   quotes that sits far outside the family you were about to route to is pointing at a different
   family, a different denominator, or a different segment — treat it as the strongest available signal
   (SR-17).
2. **The shape and the vocabulary around it.** Which direction, over what period, described how.
3. **A cheap dual pull.** Where 1 and 2 leave two candidates, route to the better-supported one and set
   `disambiguate:` in the hand-off; the investigator resolves it in Stage zero by querying both families
   over the same window and adopting whichever reproduces the user's level.

**Never route a same-label ask by the absence of a keyword** ("they didn't say rolling, so it's
classic"). Absence of a qualifier means the user did not think a qualifier was needed — usually because
in their own workflow the label is unambiguous.

Also: a **ratio the user names may not exist in the family they mean** (a `Dx/Dy` ratio where the family
only carries some day indices). Do not silently answer with the other family's ratio. Give the nearest
in-family ratio, name the substitution, and add the sibling family's equivalent alongside it, labeled.
