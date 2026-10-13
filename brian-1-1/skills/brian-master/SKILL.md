---
name: brian-master
description: "BRIAN v1.1 master router — the entry point for EVERY Playsimple analytics question. Classifies intent, hands off to exactly ONE analyst skill, and attaches a depth level (D0 mention · D1 check · D2 diagnose · D3 full investigation) so a broad \"how is X doing\" never turns into an accidental deep dive and a \"why did X drop\" never stays shallow. Owns the shared rulebook every analyst inherits (query-only, D-2 freshness, calendar anchoring, verdict grounding, formatting), the investigation protocol, and the escalation policy. Load FIRST for any Playsimple game/portfolio/metric question: performance, KPIs, healthcheck, retention, engagement, revenue, Rev/DAU, ROAS, spend, experiments, competitors, definitions, or any \"why did X move\" — then follow its routing to the right analyst.\n"
---

# BRIAN Master — route the question, assign the depth

Thin router. **Run the connection preflight (Step 0) first**, then do three things and get out of the way:
**classify intent → pick exactly one analyst → attach a depth level**. Never answer the data question from this skill.

## Step 0 — Connection preflight (before routing, before any query)

BRIAN runs on **two separate connectors**: Druid (the `queryDruidSql` tool — every `chart_XXXX` metric)
and **Trino** (the `trino-mcp` connector — `play_data.chart_config`, `public.gid_mapping`,
`monthly_rev_diff`, Sensor Tower, annotations, and the user-level-data (ULD) tables). **Every** analysis needs Trino first: the GID lookup
and the chart-version lookup both live there, so no Druid query can be written correctly without it.

1. **Check that a Trino tool is available** — any tool whose server name contains `trino` (e.g.
   `mcp__trino-mcp__…`). If it isn't in the loaded tool list, run `ToolSearch` with query `trino` once
   (connectors can still be connecting at session start, and deferred tools don't show until searched).
2. **Trino tool found → proceed** to routing. Send `schema.table` Trino statements only to that tool.
3. **No Trino tool after the search → stop and send the "Connect Trino" message below. Do nothing
   else.** Specifically, do NOT:
   - send `play_data.*`, `public.*` or `external_data.*` statements through `queryDruidSql` — Druid
     cannot see them and answers `Object 'public' not found` / `Object 'play_data' not found`;
   - hunt Druid for game names, list `INFORMATION_SCHEMA.TABLES` to guess a chart version, or ask the
     user for GIDs as a workaround — chart versions still need `chart_config`, so the numbers would be
     wrong even with correct GIDs;
   - describe the problem in engine/tool jargon ("Trino-only tables", "queryDruidSql").

**Wrong-engine signal.** If a Druid call ever returns `Object 'public' not found`,
`Object 'play_data' not found` or `Object 'external_data' not found`, the statement went to the wrong
connector — it is not a missing table and not a trigger for schema discovery. Re-run it on the Trino
tool; if there is no Trino tool, send the message below.

**"Connect Trino" message** — send as-is (fill in nothing else, add no workaround options):

> **Trino isn't connected in this chat, so I can't run this yet.** BRIAN uses Trino to look up game
> IDs and the current chart versions before pulling any numbers — without it the results would be
> wrong, so I've stopped rather than guess.
>
> **To connect it:**
> 1. Go to **Settings → Customize → Connectors**.
> 2. Find **trino-mcp** and click **Connect** (sign in if asked).
> 3. Come back and send your question again. If Trino still isn't picked up, start a new chat — new
>    connectors load when a chat starts.
>
> If trino-mcp isn't listed under Connectors, ask your workspace admin to add it for you.

After sending it, end the turn. When the user returns with Trino connected, re-run this preflight and
continue with the original question — don't make them re-explain it.

## Hand-off contract

Every routing decision produces this, stated internally before any query:

```
{analyst: <skill>, depth: D0–D3, entities: <games/franchise/platforms/tiers via ps-entities>,
 window: <resolved calendar period>, segment: <filters>, visuals: <the SR-22 floor for this depth>}
```

The analyst may not exceed its assigned depth (see `references/depth-policy.md`); it may offer the
next level when its budget ends inconclusive. **It may not fall below the depth's visual floor
either** — `visuals` is part of the contract, not an optional extra (SR-22).

## Routing

Full trigger-phrase table: `references/routing-table.md`. The short version:

| Question shape | Analyst skill | Default depth |
|---|---|---|
| "How is [game/franchise/portfolio] doing/performing", KPI summary, dashboard, ROAS/LTV/spend/eCPI | `analyst-game-performance` | D0 per domain touched |
| CPI decomposition — CPM, IPM, CTR, Click-to-Install by network / creative type; "why did CPI/IPM move" | `analyst-game-performance` (Procedure D) | D2 |
| "Compare A vs B", "top N by [metric]", "which game is best" — any ranking across 2+ entities | `analyst-game-performance` | **D1-C** (full Procedure C column set) |
| "Daily healthcheck", "anything broken?", morning scan (also scheduled) | `analyst-daily-healthcheck` | D1 per cell |
| "Read experiment X", A/B results, PAB read | `analyst-experiment-reads` (stub) | — |
| Metric definition, formula, "which table/chart holds X", dimension values, glossary, quick single number | `analyst-general-questions` | D0 |
| Competitor, rival app, market/genre benchmark (Sensor Tower) | `analyst-comp-data` | D0/D2 per ask |
| "[classic] retention dropped/spiked/why" | `investigate-retention` | D2 (D3 on "investigate/root cause") |
| Engagement / sessions / time spent / actions/DAU / stickiness moved | `investigate-engagement` | D2 (D3 likewise) |
| Rev/DAU moved; revenue moved with flat DAU (or vice versa) | `investigate-rev-dau` | D2 (D3 likewise) |
| Rolling retention (D1/D3 rolling) moved | `investigate-rolling-retention` | D2 (D3 likewise) |

Rules:

- **One analyst per question.** A multi-part question is answered by the primary analyst, which may
  hand off follow-ups. Never load two analysts side by side for one ask.
- **Direct deep-dive asks skip Tier 1** — "why did D7 retention drop?" routes straight to
  `investigate-retention` at D2.
- **Escalation is a depth upgrade, not a re-ask.** When a Tier-1 answer trips the Notable-Change
  threshold (|Δ| > 10%) or the user asks "why", hand the already-resolved
  {entities, window, segment} to the matching investigator at D2 — the investigator never re-asks
  what's known.
- **Metric families that share a label are separated on evidence, not on keywords.** Several families
  carry near-identical short names and abbreviations, and a user naming one of them rarely spells out
  which they mean. **Absence of a family's keyword is not evidence for the other family** — people
  abbreviate the metric they look at every day. Route on the stronger signals: the *level* the user
  quotes (each family sits in its own band), the *shape* they describe, and the surface they work from.
  Where two families stay plausible, route to the better-supported one and carry
  `disambiguate: <family A vs family B>` in the hand-off so the investigator settles it in Stage zero
  by pulling both — that is two extra rows in a `GROUP BY`, not a second investigation.
- **Route on the user's intent, then let the analyst correct the metric.** A hand-off names the best
  current guess; discovering mid-run that a sibling family fits better is a metric correction inside
  the same run at the same depth (`depth-policy.md`), not a reason to stop and re-ask.
- Vague question → settle what defaults and a cheap query can settle, then route. Ask at most **one**
  clarifying question, and only where no reasonable default exists and the answer changes the analysis
  (SR-21) — never hold a routable question to confirm a single-candidate entity match, a calendar
  window the anchoring rules already fix, or a metric family a query would resolve. Outside Playsimple
  analytics → say so plainly.

## User-level data (ULD) — the drill layer under the charts

Eight Trino warehouse tables at user (`rid`) grain (`ps-data-catalog` → `references/uld.md`). They answer
what no chart can: distinct users, per-user distributions, segment combinations no variant carries,
user-level joins across revenue / sessions / engagement / economy, Adjust campaign/creative at install,
reported revenue by source × country. Routing never changes because of them — the question still goes
to its one analyst; ULD is a tool that analyst picks up at the stage its skill names:

| Depth | ULD allowed? |
|---|---|
| D0 · D1 · D1-C | **No** — charts only. Exception: a direct ask that only ULD can answer ("what % of DAU spent coins", "installs by creative") — the owning analyst answers it at D0 from the table file's template, labeled ULD |
| D2 | Only `revenue_reports` for a feed-lag / source × country check, and `analyst-general-questions` table lookups (no query) |
| D3 | Yes — the per-user / breadth-vs-depth / campaign-cohort step each investigator lists |

Rules: the headline number always comes from the chart; ULD figures are labeled "user-level (ULD)" with
their population filter and never share a ratio or series with a chart figure (SR-13a). `experiment.users_v2` and `sub_tables.tracking_slice_critical` are out of scope until documented.

## What every analyst inherits

- `references/shared-rules.md` — the common rulebook (query-only, D-2 + date alignment, calendar
  anchoring, net+gross, PoP deltas on every metric, formatting, verdict grounding + weighting,
  actuals-before-predictions, presentation format, and the length/table discipline SR-23…SR-28:
  prose budget per depth, each number once, assert-don't-argue, conditional sections, comparisons as
  group claims, and table construction). Analysts state domain-specific rules only.
- `references/depth-policy.md` — the D0–D3 depth contract and stop gates.
- `references/investigation-protocol.md` — the shared drill (L0→L1→L2), hypothesis-verdict
  discipline, attribution ontology, annotations evidence layer, BLOCKED-note grammar. Binding at
  depth ≥ D2.
- `references/investigation-axes.md` — the canonical axis checklist (generalized from the team's
  investigation sheets, game-agnostic), the D3 axis coverage ledger, the intake-vs-behavior
  (D0-bucket) shift-share, and recurring-pattern priors for hypothesis seeding.
- Data & context only via `ps-data-catalog` (start at its **Fast path** box) and `ps-entities`.
  No analyst hardcodes a datasource or a chart version.
- **`game-viz-design` — LOAD it, don't just cite it.** Every analyst and investigator renders its own
  visuals by invoking this skill; the widget mechanism and chart patterns live inside it, so naming it
  in prose produces nothing. **Each skill owns its charts** — routing to a single analyst never routes
  the charting elsewhere, and no skill may assume another one will draw the picture. The per-depth
  minimum is SR-22: **D2 and deeper always ship at least one chart.** Branded PPTX/PDF exports via
  `ps-brand-report`.
