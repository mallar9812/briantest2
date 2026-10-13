---
name: "tracking-event-dictionary"
description: "Generate a rigorously-verified, paste-into-Google-Sheets event and field data dictionary for a PlaySimple game's raw tracking table (sub_tables.tracking_slice_GAME in Databricks), given a game name and its Tracking Mapping Google Sheet. Use this whenever the user asks to document, describe, or build a data dictionary for a game's tracking/event table, tracking slice, or asks \"what do the columns/events mean\" for any PlaySimple game -- even if they only name the game and not the exact table. Produces a single paste-ready tab-separated block (Category, Event k, p, c, o, f, g, s, What it means, Example query filter) with every field claim backed by live queries across multiple dates, cross-referenced against the standing DAG node queries catalog for production usage, and including a direct tracking_slice query pattern per row -- never a single-day guess and never dependent on derived/investigation tables."
---

## What this skill produces

A single tab-separated block, ready to paste straight into Google Sheets, that documents every event kind (`k` value) in one game's raw tracking table: what each of the generic payload columns (`p c o f g s`) holds for that event, grouped into business/product categories, with every claim checked against live data across multiple dates, cross-referenced against the standing DAG node queries catalog wherever production already consumes that event, and a direct `tracking_slice` query filter attached to every row so the sheet can answer "how do I query this metric" on its own -- not just "what does this field mean".

This is high-stakes documentation -- other people and other Claude sessions will run queries based on it. A wrong "this field is always empty" claim, or a query pattern that only works through a derived table nobody can find, silently breaks someone's downstream work later. Verify before asserting, always, and keep every query pattern runnable directly against `sub_tables.tracking_slice_*` so it never depends on a derived/investigation table the reader may not have access to.

## Inputs this skill expects

- A game name (fuzzy is fine, e.g. "word search" or "crossword" -- resolve it in Step 0).
- Optionally, a link to that franchise's Tracking Mapping Google Sheet (Step 4). If not given, ask for it or proceed without it and say so.
- The DAG node queries catalog is a standing resource for every run of this skill, not something the user needs to re-share each time: **https://docs.google.com/spreadsheets/d/1LslKsZszKHb11k0xgc-eo0njcwyDFnNs2E2XSy3DgLo/edit?gid=361045103** (sheet name `dag_node_queries`, columns `dagName, dagId, nodeId, prodConfig_data, stagingConfig_data, InsertQuery`). Always check it in Step 4.5.

## Step 0 -- Resolve the game and its table

Every PlaySimple game has a `gid` in `public.gid_mapping` and (usually) its own slice table in the `sub_tables` schema, `tracking_slice_<gamename>`, holding that game's full raw event stream. There's also `sub_tables.tracking_slice_critical`, a cross-game slice spanning ~20 business-critical titles (all their events, not a filtered event list) -- useful for the same treatment but note in the output that it spans multiple `gid` values instead of one. Watch for a franchise pooling more than one `gid` into a single analysis cohort (a production query for "wordsearch" filtering `gid IN (22,43)` means the second gid is very likely a companion/variant title, such as a Solitaire spin-off, deliberately analyzed together) -- confirm via `gid_mapping` rather than assuming a single gid covers the whole franchise.

1. Look up the game: `SELECT gid, game_name FROM public.gid_mapping WHERE game_name ILIKE '%name%'`. This is very likely to return several similar entries (e.g. searching "crossword" returns Crossword, Crossword Frenzy, Tiny Crossword, Crossword Search, Crossword Go, Crossword Jam 2, 1v1 Crossword Go -- all real, distinct games). Never just take the first row. If the user's phrasing doesn't clearly pick one, ask them to confirm the exact game name before continuing -- a wrong table means the whole rest of the output describes the wrong game.
2. Find its slice table: `SHOW TABLES IN sub_tables` and match on the game name (allowing for naming variants -- e.g. "Word Search Solitaire" maps to `tracking_slice_wordsolitaire`, "Crossword Search" maps to `tracking_slice_crossword_search`). If nothing matches cleanly, say so rather than guessing a table name.
3. Confirm the schema with `DESCRIBE TABLE sub_tables.tracking_slice_<gamename>`. Every one of these tables shares the same 17-column shape: `date_field, gid, cli, inserted_at, k, rid, p, c, o, f, g, s, b, cc, cs, cc_local, sync_id`. If a table doesn't match this shape, don't force the rest of this skill onto it -- flag the difference to the user instead.

## Step 1 -- Understand the shared column schema

These columns mean the same thing across every tracking slice table:

- `date_field` -- partition date. **Always filter on this.** These tables are large enough that an unfiltered `GROUP BY` or `COUNT(DISTINCT ...)` will time out -- this isn't a style preference, it's a hard practical constraint you'll hit on the first unfiltered query.
- `gid` -- game id (fixed to one value for a single-game slice table; varies across games for `tracking_slice_critical`).
- `cli` -- client platform, 0=Android/1=iOS (a 3rd value occasionally appears, e.g. Amazon -- don't assume the coding scheme is only 0/1 without checking `DISTINCT cli`).
- `inserted_at` -- warehouse ingestion timestamp (ETL landing time), separate from `cc`.
- `k` -- the event kind / event name. This is the main thing you're cataloging.
- `rid` -- groups multiple event rows together (same `rid` recurs across different `k` values for what looks like the same user/session) -- it is not a unique per-row event id, even though its cardinality is huge. `rid` is the join key for any user-level, funnel, or retention query -- see Step 6's query patterns.
- `p, c, o, f, g, s` -- six generic payload columns whose business meaning is entirely set by the value of `k`. Internally these are nicknamed after the biological taxonomy ranks -- check the Tracking Mapping sheet's own column headers for the exact convention used, since this is a real internal naming convention confirmed by direct inspection, not a joke -- don't take any specific letter-to-rank mapping as gospel without confirming it against the sheet if one is available for this game.
- `b` -- app build/version number.
- `cc` -- unix epoch timestamp of the event (client-side).
- `cs` -- a secondary timestamp, often close to `cc` but sometimes hours later -- consistent with client-side batching/offline queueing rather than a clean derived field.
- `cc_local` -- unix epoch timestamp in the user's local timezone (confirm this by checking the `cc` vs `cc_local` gap is a plausible timezone offset, not just assuming).
- `sync_id` -- has been observed unpopulated across every table checked so far; verify rather than assume for a new game.

## Step 2 -- Reconnaissance: what event kinds exist

Get the distinct `k` values and volumes for ONE recent, complete date first -- this is fast and gives you the shape of the catalog before you commit to the expensive multi-date pass:

```sql
SELECT k, count(*) c FROM sub_tables.tracking_slice_<gamename>
WHERE date_field = '<one date>'
GROUP BY k ORDER BY c DESC LIMIT 150
```

Then pull a handful of sample rows per `k` (grouped, not just a flat LIMIT) so you can see the actual shape of `p/c/o/f/g/s` for each event kind:

```sql
SELECT k,p,c,o,f,g,s FROM (
  SELECT k,p,c,o,f,g,s, ROW_NUMBER() OVER (PARTITION BY k ORDER BY rid) rn
  FROM sub_tables.tracking_slice_<gamename>
  WHERE date_field = '<same date>'
) WHERE rn <= 6 ORDER BY k, rn
```

Two things to watch for at this stage, both confirmed to actually happen, not hypothetical edge cases: near-duplicate event names from a rename or refactor that both still fire (e.g. `race_event` and `raceEvent` coexisting as genuinely different `k` values with different field shapes -- don't assume one is a typo for the other, catalog both), and a blank/empty-string `k` value showing up in the results (a real, if usually small, slice of rows -- worth a one-line callout rather than silently dropping it).

If you're delegating this raw-extraction step to a subagent because the result is large, keep its instructions purely mechanical ("group these rows by k and reproduce the values verbatim, do not interpret or describe") -- asking a subagent to also interpret meaning while parsing a large blob invites it to pattern-match a plausible-sounding but invented explanation instead of reading the actual data. Spot-check a couple of its claims against the raw values yourself before trusting the rest.

## Step 3 -- The mandatory verification pass (do not skip this)

A 6-row sample from one day is not enough to claim a field is "always empty" or "fixed" -- it's only enough to form a hypothesis. On a past run of this exact skill, a single-day sample produced over a dozen wrong "always empty"/"fixed" claims (fields that were actually populated 30-90% of the time, just not in that day's small sample) -- all caught by rerunning the same check across a wider date spread. Treat every "empty" or "fixed" read from Step 2 as provisional until this step confirms it.

Pick 4 dates spread across the available history (e.g. one from each quarter, not four consecutive days), and compute population rate per field per event kind:

```sql
SELECT k,
  count(*) n,
  round(100.0*sum(case when p is not null and p<>'' then 1 else 0 end)/count(*),1) p_pct,
  round(100.0*sum(case when c is not null and c<>'' then 1 else 0 end)/count(*),1) c_pct,
  round(100.0*sum(case when o is not null and o<>'' then 1 else 0 end)/count(*),1) o_pct,
  round(100.0*sum(case when f is not null and f<>'' then 1 else 0 end)/count(*),1) f_pct,
  round(100.0*sum(case when g is not null and g<>'' then 1 else 0 end)/count(*),1) g_pct,
  round(100.0*sum(case when s is not null and s<>'' then 1 else 0 end)/count(*),1) s_pct
FROM sub_tables.tracking_slice_<gamename>
WHERE date_field IN ('<date1>','<date2>','<date3>','<date4>')
GROUP BY k ORDER BY k
```

These percentages are the source of truth for every "empty"/"populated" claim in the final output -- they are measured population rates from this exact query, never placeholders and never guesses:

- 0.0% -> genuinely always empty, safe to say so ("always empty (confirmed)").
- 95-100% -> safe to describe as consistently populated (small gaps are normal, not worth a caveat).
- Anywhere meaningfully in between -> state the real percentage in the cell instead of a flat "empty" or "populated" claim, e.g. "only ~41% populated, not a fixed constant" -- and keep the percentage visible in the delivered sheet (don't strip it out later), since it tells the next person whether they can safely filter on that field or must handle it being blank on many rows.

This same pass will also surface event kinds that didn't appear in your Step 2 single-day sample at all -- new or date-specific variants. Fold these in with a note that they weren't seen on the original reconnaissance date.

If a literal placeholder string like "nan" or "null" shows up as a value, that's a populated field with a sentinel value, not an empty one -- call it out by name rather than lumping it in with genuinely blank fields.

## Step 4 -- Cross-check against the Tracking Mapping sheet, if available

If the user has shared (or you can find) a Tracking Mapping Google Sheet for this franchise, it's the team's own authored source for what k/p/c/o/f/g/s mean per event -- treat it as higher authority than your own inference where the two overlap; treat your live-data verification as the check on staleness (the sheet may be years out of date on some rows) and as the source for anything the sheet doesn't cover.

Large Google Sheets often don't return usable cell data through a Drive/Docs read tool (you may only get sheet names and column ranges, no values) -- if that happens, open the sheet in a browser at its specific gid URL, resize the viewport wide (e.g. 1600x1000) so more columns render, and read cell values from screenshots or the page's accessibility tree instead of assuming the sheet is inaccessible. Match tabs to games by content (a tab like "Trip-Search" may cover a shared franchise schema across several similarly-built games, not just the literally-named one), not just by tab name.

## Step 4.5 -- Cross-reference the DAG node queries catalog (always check this, it's the strongest grounding available)

Sampling and population-rate checks tell you what a field *looks like*. A production query that already reads that exact `k`/`o`/`c`/`f` combination and gives it a named business metric tells you what it definitely *means*, because an analyst already built and shipped an investigation or dashboard on that assumption. Treat this as a step above Step 3, not a replacement for it.

Open the standing catalog at **https://docs.google.com/spreadsheets/d/1LslKsZszKHb11k0xgc-eo0njcwyDFnNs2E2XSy3DgLo** (sheet `dag_node_queries`; same browser-viewing caveats as Step 4 -- it's wide, so widen the viewport). Its columns are `dagName, dagId, nodeId, prodConfig_data, stagingConfig_data, InsertQuery`. The `InsertQuery` column holds the literal SQL that builds each derived/aggregate table in the warehouse, and that SQL frequently reads straight from `sub_tables.tracking_slice_critical` or a game's own slice table with a specific `k`/`o`/`c`/`f` filter. Search it by table name, by game name, or by a `k` value to "backtrack" from a raw event to its production consumer (or the reverse: from a named business metric back to the raw event that produces it).

If the user separately pastes or references a standing investigation/health-check query (e.g. a D1/retention investigation query), mine it the same way: every `CASE WHEN k=... AND o=... AND c=... THEN ... END AS some_named_metric` is a confirmed, human-authored mapping from raw fields to business meaning -- pull these out explicitly.

What to do with a match: fold a short "production usage" note into that event's "What it means" cell -- e.g. "`k='puzzle', o='view', c='1'` is aggregated downstream as `puzzle1_viewers`" -- and use the named metric to sharpen the description (if the production query treats `c` as a puzzle-level index 1-30, that settles what `c` means far better than a guess from 6 sample rows). Flag, rather than silently resolve, any inconsistency you find between two logging paths for what looks like the same feature (e.g. a `type='quest_center'` field on a processed table existing alongside a raw `k='dialog', o='quest_centre'` event with different spelling), and flag any abbreviation in production code with no obvious expansion (e.g. an `'ooc'` substring with no comment) as needing an SME check rather than guessing.

Do NOT carry the derived/aggregate table names themselves (`wordsearch.D1_investigation_table`, `derived_tables.dau_splits`, `server_tables.*`, `dm_admon.*`, etc.) into the final query-pattern column -- those tables may not exist for every game and the reader may not have access to them. Use what they reveal about field meaning, then translate every example query back into a direct filter on `sub_tables.tracking_slice_<gamename>` (or `tracking_slice_critical` for cross-game).

## Step 5 -- Group events into categories

Sort every `k` into a business/product category -- this is what turns a column dump into something a human can actually navigate. Categories won't be identical game to game, but a useful starting set: Core Gameplay & Content, Daily/Live Features, Competitive & Social, UI/Dialogs, Session & App Lifecycle, Ad Monetization (usually the largest cluster -- trace the pipeline from "ad slot shown" through mediation lifecycle through the parallel revenue-postback events, since several k values will turn out to be network-specific variants of the same step, e.g. an admob-specific and a MAX-specific version of the same eligibility check), Economy & IAP, Cross-Promo & Attribution, Notifications, Onboarding/Identity/Compliance, Diagnostics/Infra, Experiments. Add or drop categories as the actual event list demands rather than forcing a fit.

## Step 6 -- Output format

Deliver ONE tab-separated block in a single code fence (so it has a copy affordance and pastes cleanly into Sheets), by default straight in chat -- only save it as a file if the user asks. Structure:

1. A short legend block first, giving the generic query shapes so the per-row "Example query filter" column can stay short:
   - User/action count: `SELECT COUNT(DISTINCT rid) n FROM sub_tables.tracking_slice_<gamename> WHERE date_field='<date>' AND <filter>`
   - Funnel across a level/tier (`c`): same, drop the `c` constraint, add `GROUP BY CAST(c AS INT) ORDER BY 1`
   - Revenue/value sum: `SELECT SUM(CAST(<value field> AS DOUBLE)) rev FROM ... WHERE <filter>`
   - Dx retention/return funnel: self-join `k='install'` rid+date_field against later date_fields for the same rid, bounded to the window needed
   - Cross-game/franchise pooling: swap the table for `tracking_slice_critical` and add `AND CAST(gid AS INT) IN (<gid list>)`
2. The main table, header row exactly: `Category	Event (k)	p	c	o	f	g	s	What it means	Example query filter`. One row per event kind. Field cells describe what the field holds in plain language with a real example value, and carry the population-rate percentage inline whenever it's below ~95% (per Step 3) rather than in a separate footnote. Fold in any Step 4.5 production cross-reference into the "What it means" cell. The last column is a short WHERE-clause fragment meant to be dropped into whichever legend pattern fits (never a full derived-table query).

## A note on trust

Every specific claim in the output -- "always empty", "fixed value", "X% populated", "this is what production calls it" -- should trace to something actually queried or read in this session, not to a plausible-sounding pattern. If you're unsure whether a claim is grounded or inferred, say so in the cell rather than presenting it with false confidence. Being asked to cross-check your own prior output and finding real errors is a normal and expected part of this workflow, not a failure -- run the multi-date verification pass and the DAG catalog cross-reference up front so they happen before the user has to catch a gap.

