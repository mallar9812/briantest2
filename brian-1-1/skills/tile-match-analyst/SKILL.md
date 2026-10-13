---
name: tile-match-analyst
description: "Feature/event-level analyst for Tile Match (zenconnect, GID 26) — below the Druid chart_XXXX KPI layer. Use for funnels between screens/actions, \"what does a player do after 0 matches / an outro / a paywall\", DLR/Daily Victory streak-day analysis, Golden Tile / Sky Sprint / Picnic Rush / Stamps / Streak Event / Quest Center / Daily Challenge engagement, w2e or IAP/OOC purchase funnels, powerup usage, level/seed difficulty, experiment cohorts, or any query on tracking_slice_zenconnect_trino / puzzle_master_cc_us / play_zenconnect.* tables. Also load to interpret the k/p/c/o/f/g/s (kingdom/phylum/class/order/family/genus/species) tracking taxonomy, including a ground-truthed field guide to the puzzle/dp/bonus_level kingdoms (level progression, difficulty/DDA, powerups, content-version). Companions: ps-entities (GID/franchise lookup), ps-data-catalog (KPI layer), game-performance- analyst, game-viz-design.\n"
---

# Tile Match (zenconnect) — feature & event analyst

Act as the analyst for **Tile Match's** in-game feature instrumentation — the raw event stream
behind every dialog, powerup, live-ops event, and monetization touchpoint, not the aggregated
KPI charts. This skill packages a Tile Match analyst's tracking-mapping workbook (731 documented
event rows across 164 features) and 19 of their SQL analyses into a reusable reference so a new
funnel, retention cut, or "what happened next" question doesn't have to re-derive the schema or
the query shapes from scratch.

**GID 26, platform codes 0=Android/1=iOS** (resolve any other game/franchise/platform name via
`ps-entities`, don't hardcode from memory here).

## Two layers — pick the right one before you query

| Question shape | Layer | Skill to load |
|---|---|---|
| "How is Tile Match performing" — DAU, revenue, Rev/DAU, retention, ROAS, spend, ad revenue, crashes, competitor benchmarking, WoW/MoM trend | Aggregated **Druid `chart_XXXX`** KPI dashboards | `game-performance-analyst` + `ps-data-catalog` (does **not** need this skill) |
| A specific screen, popup, powerup, live-ops event, funnel step, or "why do users drop after X" — anything needing a `k`/`o` event filter | **This skill** — raw `tracking_slice_zenconnect_trino` event stream | this skill (`references/*`) |
| Both — e.g. "DAU dropped, and I suspect it's the new Daily Challenge flow" | Start with the KPI layer to size/confirm the movement, then drop into this layer to find the specific event-level cause | both, in that order |

If a question could plausibly be answered from a `chart_XXXX` datasource (sessions, actions/DAU,
in-game economy totals, retention curves) check `ps-data-catalog/references/engagement.md` first —
it's pre-aggregated and far cheaper to query than rebuilding the same rollup from raw events here.
Come to this layer when the KPI layer doesn't have the dimension you need (a specific dialog, a
specific powerup, a specific live-ops event's own funnel).

## Load order for a new question

1. **`references/tables_and_columns.md`** — the raw tables (`tracking_slice_zenconnect_trino` and
   friends), what `k/p/c/o/f/g/s` mean, the SQL-dialect gotchas (Trino vs. Spark SQL), and the
   scratch-table naming convention. Read this before writing any query against these tables.
2. **`references/event_feature_index.md`** — a one-row-per-feature index of all 164 tracked
   features (session/install, puzzle core loop, progression, DLR/streak retention mechanics,
   live-ops events, leaderboard/social, monetization, ads, notifications, compliance, settings,
   experiments/debug — see the domain groups below) with row counts and how many rows the analyst
   flagged with a comment. Use it to find which feature owns the event you need.
3. **`references/event_taxonomy_full.csv`** — the full 731-row taxonomy (every `k/p/c/o/f/g/s`
   combination, its description, and the analyst's verification comment). Grep/filter this for the
   exact field layout of the event you're about to query — never guess a `p`/`c`/`f`/`g`/`s`
   meaning from a similar-looking event. **When the kingdom is `puzzle`, `dp`, or `bonus_level`,
   also grep the combined-kingdom spellings** (`puzzle/dp/bonus_level`, `puzzle/ dp`, and the
   typo'd `puuzle/dp/bonus_level` / `puzle/dp/bonus_level`) — many events for these three screens
   are documented once under a combined tag rather than under each kingdom separately, so a
   literal-kingdom-only grep will silently miss real `o` values (e.g. `wand`).
4. **`references/puzzle_dp_bonus_level_guide.md`** — load this whenever the question touches
   `k='puzzle'`, `'dp'`, or `'bonus_level'` specifically (core level loop, powerups, difficulty/DDA,
   hints, progression/level-frontier questions). It's the ground-truthed decode of `p`/`c` for these
   three kingdoms (confirmed against real data, not just the CSV's placeholder labels — including
   two corrections to the raw taxonomy: `attempt_number` is 1-indexed with `0` meaning missing data,
   and `content_set` can change over time, it's just rare), a note on the separate `k='content_version'`
   event (the real user-date → content-version source — don't decode it out of `c` when this exists),
   and every `o` value seen under these kingdoms grouped by function with the important `f`/`g`/`s`
   nuances called out (e.g. `diff_preset`'s true easy→hard order is `5 < 0 < 1 < 2 < 3 < 4`, not raw
   numeric order; `content_seeds` is a seed-reuse catalog, not a level lookup — don't join it
   expecting one row per level).
5. **`references/query_patterns.md`** — the nine reusable query shapes (cohort/experiment base
   table, network bucketing, `cc`-window funnels, "what happened next", retention via paired
   actions, DLR/streak-day calculation, the engagement-rollup `UNION ALL` pattern, unassisted-clear
   filtering, and the monetization/ads event shapes). Start a new query from the matching pattern
   rather than from a blank editor.

## Feature domains (full list: `references/event_feature_index.md`)

| Domain | Representative features |
|---|---|
| Core loop & session | `session`, `DAU`, `install`, `Puzzle`, `NACTA` (hint/no-action-timeout), `no_matches available`, `matches available`, `Hidden Tile Obstacle`, `bubble pop`, `Tutorial`, `How to Play` |
| Progression & content | `Progression`, `Outro`, `Level CTA on Outro`, `Chapter Complete Flow`, `Dynamic Difficulty v1`/`DDA v2`, `Hard Level Tagging`, `Symbol Unlock`, `Event Unlock`, `Zen Tree` |
| Retention mechanics | `DLR`, `DLR Revamp`, `DLR_w2e`, `Daily Victory`, `Daily Challenge` (+ `DLC`, `DC optimizations`), `Streak System`, `Streak Event` (Lily's Adventure) |
| Live-ops timed events | `Golden Tile`, `Sky Sprint`, `Picnic Rush`, `Bonus Levels`, `Stamps`, `Lighting strike`, `quest center` |
| Leaderboard & social | `Leaderboard`, `bots_lb`, `FB connect`, `fb login`, `apple login`, `Profile`, `Wisdom score` |
| Monetization & economy | `Econ`, `OOC Flow`, `IAP popup`, `No Ads Pack`, `New Conversion Deals`, `Powerup IAP`, `Powerup prompts`, `w2e_store`, `extra_slot` |
| Ads | `w2e`, `ad logic`, `dt_interstitial_exp`, `ads on inactivity`, `audio ads`, `Online vs Offline`, `w2e Cap` |
| Notifications | `Notif`, `Notif Opts v1`, `notif pre prompt`, `Notify me`, `DT auto update` |
| Compliance & platform | `GDPR`/`GDPR v2`, `CCPA`, `ATT`, `Android 13 Compliance`, `Force Update` |
| Settings, account & UX | `Settings`, `Localization`, `Home Screen`, `Rate Us`, `Quit flow`, `Play On`, `RUX` |
| Experiments, QA & debug | `Experiment`, `player bucketing`, `it_tunings`, `Viewers investigation`, `wand debug`, `QMT` |

## Running queries

Use the Databricks plugin (`mcp__Databricks__execute_sql_read_only` for exploration,
`mcp__Databricks__execute_sql` only when you actually need to materialize a scratch table per the
`play_zenconnect.<exp_name>` convention) to run against these tables. **The source queries are
written in Trino/Presto SQL** — translate per the dialect table in `tables_and_columns.md` before
running through a Spark SQL warehouse, and sanity-check results rather than assuming a straight
copy-paste runs correctly.

Standard hygiene filters used throughout this game's analyses (state which ones you applied, don't
apply silently): `CAST(gid AS INT) = 26`, `CAST(cli AS INT) IN (0, 1)`, `install_bucket <>
'reject'`, `LOWER(country) <> 'in'` (confirm intent with the requester before carrying this India
exclusion into a new analysis — it's a recurring convention in this game's queries, not a documented
hard rule), and a minimum-build gate via `server_tables.dau_master_by_build_cc` when the question is
scoped to a specific release.

## What this skill does NOT cover — tell the user rather than guessing

- **Anything answerable from a `chart_XXXX` Druid datasource** — use `ps-data-catalog` /
  `game-performance-analyst` instead; don't rebuild a KPI from raw events when a chart already
  serves it.
- **Client-side game design/balancing logic** (how difficulty presets are actually tuned, how the
  matching algorithm decides "0 matches available") — this skill documents what's *tracked*, not
  the game logic that produces the tracked values.
- **Anything not in the tracking mapping.** If a question needs an event that isn't in
  `event_taxonomy_full.csv`, say so plainly and ask the analyst/data-eng team rather than inventing
  a plausible-looking `k`/`o` combination.
