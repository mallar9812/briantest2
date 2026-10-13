---
name: ps-entities
description: "Playsimple context layer — ENTITIES. Canonical mappings for resolving names to IDs in Playsimple analytics: game name → GID via a live lookup against `public.gid_mapping`, never hardcoded; platform (`cli`) as a fixed convention (0/1/2), not from that table; franchise → member games, keyed by GID (PVP, Anagram, Crossword, Search Studios, Organic Growth, plus Others/untagged); and country tier mapping (Tier-1 = US, GB, CA, AU), matched case-insensitively. Load whenever a question names a game, franchise, platform, or country tier, or asks which games belong to a franchise or what a GID refers to. Companion: ps-data-catalog (table routing, filter rules, formulas, dimensions).\n"
---

# Playsimple Entities

Resolve names to IDs from the tables below. Competitor apps are not here — resolve those via
`external_data.st_product_details` (`product_id`), never through the GID mapping.

**Resolution rule — count the candidates, then act.** People refer to titles by a fragment, a nickname
or a shortened form far more often than by the full catalog name. Match case-insensitively on
substrings and word fragments across the resolved game list below, then:

- **Exactly one candidate → resolve it and say so** in the period & segment line ("resolved to <full
  title> (GID N)"). Do not ask. A single-candidate match is not a guess, and holding the analysis to
  confirm one costs the user a round trip for something the answer already states plainly and they can
  correct in a word.
- **Two or more candidates → ask once**, listing them. This is the case the confirmation rule exists
  for.
- **Zero candidates → say so plainly** and offer the nearest names in the table, rather than forcing
  the closest one.

**Never let entity resolution block the analysis.** Where a single candidate exists, resolve and
proceed at the assigned depth (SR-21); a stated resolution the user can correct beats a question they
have to answer before any work starts.

## Game → GID — live lookup, never hardcoded

Do not memorize a fixed game/GID list — titles launch, retire, and get re-tagged, and a stale list
silently mis-resolves. Resolve every game name and its GID by querying `public.gid_mapping` fresh, once
per conversation, and reuse that result set for the rest of the conversation:

```sql
SELECT gid, game_name
FROM public.gid_mapping
```

**Run this on the Trino tool (`trino-mcp`), never through `queryDruidSql`** — Druid answers
`Object 'public' not found`. No Trino tool connected → stop and send the "Connect Trino" message from
`brian-master` Step 0 (Settings → Customize → Connectors → trino-mcp); don't ask the user for GIDs instead.

Confirmed table shape (`public.gid_mapping`, Trino — no catalog prefix): `gid` (int), `game_name` (string),
`inserted_at` (timestamp — a row-insert timestamp, not useful for resolution).

Apply the standard resolution rule above to the returned `game_name` values: match case-insensitively on
substrings and fragments, then resolve on exactly one candidate, ask once on two or more, and say so
plainly on zero.

## Franchise → member games

Franchise structure is maintained on a separate internal tracking sheet, not a queryable table. Names
below are the short/internal names as they appear on that sheet, which may differ from the marketing
title `public.gid_mapping` or other tables use (e.g. "Wars" vs "Word Wars") — resolve via the standard
fragment-matching rule above, and when in doubt confirm by GID rather than by string.

| Franchise | Games |
|---|---|
| **Anagram_franchise** | Jam, Trip, Bliss, Planet, Word Trip Zen, Word Connect Association, Word Tour, Hexa Tap Away, Jam 2 |
| **PvP_franchise** | Wars, Roll/Bingo, Jigsaw Puzzle HD, Pic Merge, Cryptogram, Tile Empire, Mahjong Empire, Zen Connect/Tile Match, Tile Travels, Destination Solitaire, Solitaire |
| **Crossword_franchise** | DTC, 2248, Crossword Go, Crossword Search, OPM, Sudoku Go, XP, Pawzzle |
| **Search_franchise** | Word Trip Search, Word Search Solitaire, Word Search, Color Block Crush, Solitaire Word Association |
| **Organic_Growth_franchise** | PlayRova (P2E), Netflix: Word Trails, Netflix: Trails Search, Arcade: Crossword Jam +, Arcade: XP+, Serenity Word - Relaxing Puzzles, Word Explorer - DT store (onestore), YouTube: Word Search Explorer, Word Trek |
| **Others (untagged)** | Any GID-mapped game not listed in a franchise above — includes Play Mint, which no longer appears on the franchise sheet |

**Franchise rules**

- **Always name the member games** when reporting on a franchise — never present a franchise figure without
  stating exactly which games it covers. Put it in the period & segment line or immediately beside the first
  franchise figure: "Anagram franchise (Jam, Trip, Bliss, Planet, Word Trip Zen, Word Connect Association,
  Word Tour, Hexa Tap Away, Jam 2)".
- Games mapped to no franchise are **"Others (untagged)"** — never silently fold them into a named franchise,
  and label them that way in any franchise-level comparison.
- A franchise game that doesn't resolve to a GID via the live `public.gid_mapping` lookup → flag it
  explicitly rather than dropping it silently. "YouTube: Word Search Explorer" has no GID on the source
  sheet — flag it if referenced.
- **Tile_franchise and Central_franchise no longer exist as separate groups.** Tile Empire, Mahjong Empire,
  and the Tile Match variants are now under PvP_franchise; Play Mint (formerly Central_franchise) is
  untagged until confirmed otherwise.
- Franchise questions follow every rule that game questions do — metric scope, net+gross, ROAS vs target. A
  franchise is a game grouping, not a different kind of analysis: resolve to member GIDs and aggregate.

## Platform codes (`cli`)

Not resolved from `public.gid_mapping` — that table has no `cli`/platform column. Platform is a fixed
convention, read directly off the `cli` column on each metric table itself: 0 = Android, 1 = iOS,
2 = Amazon. Some extended tables also carry `cli = 5` — meaning unconfirmed; flag it if encountered
rather than assigning it a platform.

## Country tiers

**Tier-1 = US, GB, CA, AU.** Everything else — including `ZZ` (Unknown) — is Non Tier 1.

**Match case-insensitively, always — never rely on remembering or verifying the stored case.**
Underlying tables are inconsistent about it (most store lowercase ISO alpha-2 codes, but not
guaranteed on every table), and a plain literal comparison like `country IN ('US','GB','CA','AU')` can
silently return **zero rows** against a lowercase-stored field — no error, just an empty geo cut that
looks like the field is unpopulated. Wrap both sides in `LOWER()` (or `UPPER()`) so the filter is
correct regardless of storage case, on every table with a `country` dimension:

```sql
LOWER(country) IN ('us','gb','ca','au')
```

This makes the stored case a non-issue — there's no need to probe a table's convention with
`SELECT DISTINCT country` first; the case-insensitive filter is correct either way.

Watch for pre-aggregated country fields: the notifications table pre-tiers country itself (au/ca/gb →
'Tier 1 (Non-US)', rest → 'others', except allow-listed LOC games); `country = 'others'` in drill-down tables
is a long-tail rollup, not a real country; `geo_bucket` (gross revenue) and `country_bucket` (core KPIs —
ignore it) are rollups, not countries.
