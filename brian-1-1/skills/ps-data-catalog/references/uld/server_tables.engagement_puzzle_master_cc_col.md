# `server_tables.engagement_puzzle_master_cc_col`: per-user daily puzzle actions (all games)

> **Engine:** Trino. Write `server_tables.engagement_puzzle_master_cc_col` (no `delta.` prefix). **Category:** Engagement
> **Grain:** one row per user (`rid`) × `gid` × `cli` × `date_field` × `action_type` × `puzzle_type` × `build`, with `actions` = event count. **Partition / mandatory date filter:** `date_field` (DATE).

> **Used by (BRIAN):** `investigate-engagement` D3 (per-user actions, breadth vs depth). Read `references/uld.md` first for the layer-wide rules.

## What it is
The portfolio-wide user-level engagement table: for every user who fired a puzzle/gameplay event, how many times each `action_type` happened in each puzzle mode (`puzzle_type`) on each app build that day. It is a plain union of per-game source tables with no cross-game normalisation, so **`action_type` and `puzzle_type` vocabularies are whatever each game emits** (only OPM, gid 38, is remapped: `puzzle_type` = mini-game name). Population = users with ≥1 engagement event; it is not a DAU table (most, not all, DAU appear) and is not filtered for reject or test traffic.

## When to use it — and when not to
- **Use for:** distinct users who did X (cleared ≥1 puzzle, used a hint, played the daily puzzle); per-user distributions (clears/user percentiles, heavy-player buckets); D0/Dn engagement of install cohorts; engagement by any `derived_tables.dau_splits` segment (install_bucket, country, cohort, payer); build-level checks; game-specific action funnels (view → clear, fail, hint use).
- **Don't use for:** headline actions, actions-per-DAU or puzzle-mode trends — use Druid `chart_2898-vN`, which is built from this table. ULD sums won't tie exactly: the chart keeps only a fixed action_type set (view, fail, clear, use_hint, start, play, chat, burst_hint, disc_burst_hint, w_clear, frenzy_clear, w_made), adds `eoc` rows from another source, and uses its own `w/o puzzle_type` rollup. Sessions / time spent → `server_tables.sessions_master_cc` or `chart_2524-vN`.

## Grain, keys & freshness
| Item | Value |
|---|---|
| Unique key | (`date_field`, `gid`, `cli`, `rid`, `action_type`, `build`, `puzzle_type`). A user can be on 2+ builds in a day, so re-aggregate to (date_field, gid, cli, rid) before joining per user. |
| Partition column | `date_field` — **always filter on it**; unfiltered scans time out. |
| Freshness / lag | Loads shortly after 00:00 UTC and **rewrites a rolling ~5-day window**; D-1 is incomplete. Use ≤ D-2 as the latest complete day and expect D-1…D-5 to change between runs. `date_field` is inherited from each game's source; treat as UTC. |
| Types | `gid`, `cli`, `actions` INTEGER (cast SUM to BIGINT for large sums); `build` VARCHAR (numeric strings); `date_field` DATE; `inserted_at` TIMESTAMP(3) WITH TIME ZONE; everything else VARCHAR. |

## Rollups, mandatory pins & gotchas
- **`puzzle_type = 'overall'` is a rollup row for gid 10 (Word Wars) and gid 20 (Word Bingo) only** — it equals the sum of their other puzzle_types. Exclude it when summing across modes (or pin it for totals). For other gids there is no `'overall'`; sum the modes yourself.
- **Never sum `actions` across action_types.** Units differ: most are event counts, but some are durations or high-frequency taps (gid 24 `clear_time` is a duration, likely seconds; gid 26 `tile_select` dwarfs clears). Always filter or pivot by `action_type`.
- **"Clear" is not universal.** `clear` = puzzle/level completed for most gids, but gids 10 and 20 have no `clear` (they use `play` / `start` / `end`; team convention treats gid 20 `play` as clears), gid 16 uses `solved`, and gid 38 has hundreds of free-form types (`click_grid_x_y`, `click_submit_…`). `w_clear` = a word solved inside a puzzle, not a puzzle clear; gids 39/45 split it into `w_clear_player` / `w_clear_bot`.
- **`puzzle_type` case varies by game** (`Main` vs `main` vs `puzzle` vs `Puzzle`). Use `LOWER()` when comparing; there is no portfolio-wide "main mode" value.
- **gid 39 / 45 junk puzzle_types:** numeric strings `'0'`–`'23'` and `'trackBlock'` carry only `milestone`; `puzzle_type = ''` covers nearly every user and is mostly NULL action_type. Exclude these for mode analyses.
- **NULL `action_type`** (almost all gid 39, plus gids 45 and 27): meaning unknown — exclude.
- **`actions = 0` rows exist** (no negatives): hint-type actions on gids 9/14/34/40 (`use_hint`, `burst_hint`, `disc_burst_hint`), 42/55 (`category_hint`), 51 (`use_bomb`, `use_hammer`, `use_extra_move`), and gid 27 NULL rows. For "users who did X" require `actions > 0`.
- **Don't filter builds with `CAST(build AS INT) < 1000`** — gid 10 uses 5-digit builds and would vanish. Use `try_cast(build AS INT)`.
- **Reject users are included.** Join `derived_tables.dau_splits` and filter `install_bucket <> 'reject'`.
- **cli 2 (Amazon)** exists only for gids 8, 9, 10, 11, 17, 22.

## Columns
| Column | Type | Role | Description |
|---|---|---|---|
| date_field | DATE | Date (partition) | Activity date. Always filter. |
| gid | INTEGER | Key | Game id (`public.gid_mapping`). |
| cli | INTEGER | Key | Platform: 0 Android, 1 iOS, 2 Amazon. |
| rid | VARCHAR | Key | Playsimple user id (= `refid` in `analytics.adjust_installs`); join key to all ULD siblings. |
| action_type | VARCHAR | Dimension | Gameplay event name; vocabulary per game (see matrix below). NULL rows — exclude. |
| build | VARCHAR | Dimension | App build (numeric string); `try_cast(build AS INT)`. gid 10 builds are 5-digit. |
| actions | INTEGER | Metric | Count of that action (for some types a duration/value). Additive **within one action_type** only. |
| puzzle_type | VARCHAR | Dimension | Game mode. `'overall'` = rollup for gids 10/20; gid 38 = mini-game name; `''` on gids 39/45/47. |
| inserted_at | TIMESTAMP(3) WITH TIME ZONE | Meta | Load time; freshness checks only. |

> **Examples only.** New games and new action / puzzle types keep appearing, and names can change across builds — the valid set depends on the date range. Before filtering on a name, confirm it exists for that gid and window: `SELECT action_type, puzzle_type, SUM(actions) FROM server_tables.engagement_puzzle_master_cc_col WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid} GROUP BY 1, 2`.

**puzzle_type by gid** (`*` = rollup): 8: main, mini, tp, pack, bonus_archive, mc, archive, pc, ep, b_mini, mini_events (+ junk `13`, `g1`, `_9`) · 9: Main, daily_puzzle, vip_puzzle · 10: overall*, bots, real, solo_series, dwp · 11: puzzle, daily_puzzle, word_ladder · 14: Main, daily_puzzle · 15: puzzle, daily_puzzle · 16: classic_1, thoughtful_1, move_1, time_1, dc_* … · 17: LLP-Big, LLP-Mini, daily_mini, LLP-Midi, pc, word_ladder · 20: overall*, instant_bot, real, dbh, solo_series, multi_bot · 22: puzzle, daily_challenge · 24: Puzzle, Daily Puzzle, Collections · 26/33/53: Main, bonus_level, dp · 27/42/55: Main, daily_challenge · 29: um, ma · 31/41/48: puzzle, daily_puzzle (+ word_ladder on 41) · 34/36/40/51: Main, daily_puzzle · 35/60: main, dc · 37: puzzle, daily_challenge, weekly_puzzle, story_puzzle, secret_level · 38: crossword, password, wordsearch, wordtrails, numbermerge, grid_reset · 39: main, '', dp, trackBlock, pack, bdp, sm, wordpix, packArchive, wl, dpArchive, '0'–'23' · 43: puzzle, daily_challenge · 49: Main · 50/52: puzzle · 58: puzzle, daily_challenge, secret_level.

**Main action_types by gid:**
| gid | action_types |
|---|---|
| 8 Crossword | view, w_clear, frenzy_clear, clear, stars_clear, use_hint, w_made, wrong_w_made |
| 9 Word Trip / 14 / 34 / 40 | view, w_clear, clear, word_streak, extra_word, use_hint, special_word, free_normal_hint, shuffle, spin, burst_hint, disc_burst_hint (40 adds fail) |
| 11 WordJam / 15 / 31 / 41 | view, w_clear, clear, extra_word, use_hint, shuffle, star, use_hint_burst, use_hint_target, bonus_words |
| 17 Explorer | view, w_clear, frenzy_clear, use_hint, clear, stars_clear |
| 10 Word Wars | view, play, start, end, powerup_use, powerup_tap, word_tap, chat (no clear) |
| 20 Word Bingo | start, view, end, play, swap, recall, shuffle, back, more, bingo (no clear) |
| 22 Word Search / 43 / 27 | view, w_form, clear, w_fail, normal_hint, w_bonus, w_bonus_already_form, rotate, w_already_form, wind_hint, *_out, w_tap, burst_hint |
| 24 Jigsaw | view, move, rack_scroll, fix, snap, clear, clear_time, zoom_*, preview_*, hint_click, hint_use |
| 26 Tile Match / 33 / 49 / 53 | load_start, algo_version, zoom, matches_on_top variants, level_easing, view, hard_level_tag, load_end, tile_select, set_clear, gratif, player_idle, quartile_complete, match_ready, clear, fail, pu_click … |
| 37 Cryptogram / 58 Codegram | view, letter_key_input, letter_fill, cursor_select, scroll, clear, mistake, fail, revive, hint, hint_cancel, burst_hint |
| 39 Crossword Go / 45 | letter_view, view, letter_fill, submit(_bot), w_clear_player, w_clear_bot, empty_handed_bonus_*, bot_surpass, clear, incorrect_fill, use_hint, reveal_letter, pass, milestone |
| 42 WCA / 55 | view, row_clear, icon_clear, clear, use_hint, category_hint, col_clear |
| 36 / 52 (solitaire-likes) | 36: view, tableau_select, submit, draw_card, clear, wild_card…; 52: view, draw_pile_drag, tableau_drag, card_submit, clear, joker… |
| 50 / 51 / 60 / 29 / 47 | 50: block_tap/move/clear, clear, fail, boosters · 51: tile_clear, clear, fail, use_bomb/hammer · 60: cell_*, clear, fail, use_hint · 29: w_clear, clear, use_hint_*_gem_sink/_w2e/_free · 47: number_fill, row/column_clear, clear |

## Common metrics built from this table
| Metric | Formula (`{field}` notation) | Notes |
|---|---|---|
| Clears | `SUM({actions})` WHERE `{action_type}='clear'` | Not defined for gids 10/20 (use `play` for 20 per team convention); exclude `'overall'` rows. |
| Clearing users | `COUNT(DISTINCT {rid})` WHERE `{action_type}='clear' AND {actions}>0` | Distinct per (gid, cli); don't sum across days for multi-day uniques. |
| Clears per DAU | clears / `COUNT(DISTINCT dau_splits.{rid})` | Denominator from `derived_tables.dau_splits` (reject excluded), not users in this table. |
| Actions per DAU (by action_type) | `SUM({actions})` WHERE `{action_type}=X` / DAU | One action_type at a time — never sum across types. |
| View → clear rate | clear actions / view actions | Same gid and puzzle_type; meaning of `view` varies by game. |
| Hint usage rate | users with a hint action `> 0` / DAU | Hint action names vary (use_hint, normal_hint, hint, category_hint, …). |

## Join recipes
**Key:** `e.date_field = t.<date column> AND e.gid = t.gid AND e.cli = t.cli AND e.rid = t.rid` (INTEGER / INTEGER / VARCHAR — no casts). Aggregate this table to (date_field, gid, cli, rid) first; drive per-DAU rates from `dau_splits` with a LEFT JOIN.

| Table | Date column | Notes |
|---|---|---|
| `derived_tables.dau_splits` | `dau_date` | One row per user-day; denominator and segments. Nearly all engaged users match for core word games (gid 39 noticeably fewer). `dau_build` is INTEGER vs `build` VARCHAR here. |
| `server_tables.sessions_master_cc`, `server_tables.economy_master_cc` | `date_field` | Multi-row per user-day — pre-aggregate both sides. |
| `dm_admon.rev_dau_install_diff_ilrd_v2` | `dau_date` | Pre-aggregate to the user-day. |
| `derived_tables.wallet_dau_install_diff` | `dau_date` | Dedupe with `MAX(cash)` per user-day first. |
| `analytics.adjust_installs` | `installed_date` | `a.refid = e.rid`; D0 = `date_field = installed_date`, Dn = `installed_date + n`. Dedupe adjust per `(gid, cli, refid)` first. |
| `derived_tables.revenue_reports` | — | **No user-level join** (no `rid`); compare only as aggregates on date / gid / cli / lowercase country. |

## Query templates (all executed successfully)

**1. Per-DAU action rates for one game (clears, views, hints per DAU by platform)**
```sql
WITH dau AS (
  SELECT dau_date, gid, cli, rid FROM derived_tables.dau_splits
  WHERE dau_date BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid} AND install_bucket <> 'reject'
), eng AS (
  SELECT date_field, gid, cli, rid,
         SUM(CASE WHEN action_type = 'clear'    THEN actions ELSE 0 END) AS clears,
         SUM(CASE WHEN action_type = 'view'     THEN actions ELSE 0 END) AS views,
         SUM(CASE WHEN action_type = 'use_hint' THEN actions ELSE 0 END) AS hints
  FROM server_tables.engagement_puzzle_master_cc_col
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND puzzle_type <> 'overall'
  GROUP BY 1,2,3,4
)
SELECT d.dau_date, d.cli, COUNT(DISTINCT d.rid) AS dau, COUNT(DISTINCT e.rid) AS engaged_users,
       SUM(COALESCE(e.clears,0)) AS clears,
       ROUND(1e0 *SUM(COALESCE(e.clears,0))/COUNT(DISTINCT d.rid),2) AS clears_per_dau,
       ROUND(1e0 *SUM(COALESCE(e.views,0))/COUNT(DISTINCT d.rid),2)  AS views_per_dau,
       ROUND(1e0 *SUM(COALESCE(e.hints,0))/COUNT(DISTINCT d.rid),2)  AS hints_per_dau
FROM dau d LEFT JOIN eng e
  ON e.date_field = d.dau_date AND e.gid = d.gid AND e.cli = d.cli AND e.rid = d.rid
GROUP BY 1,2 ORDER BY 1,2
```
Hint action names are per game — gid 22 has no `use_hint` (it logs `normal_hint`, `wind_hint`, `burst_hint`), so `hints_per_dau` returns 0 there; pick names from the action matrix above.

**2. Per-user clears distribution**
```sql
WITH u AS (
  SELECT date_field, cli, rid, SUM(actions) AS clears
  FROM server_tables.engagement_puzzle_master_cc_col
  WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
    AND action_type = 'clear' AND actions > 0
  GROUP BY 1,2,3
)
SELECT date_field, COUNT(DISTINCT rid) AS clearing_users,
       approx_percentile(clears, ARRAY[0.25,0.5,0.75,0.9,0.99]) AS p25_p50_p75_p90_p99,
       ROUND(AVG(clears),2) AS avg_clears,
       SUM(CASE WHEN clears >= 20 THEN 1 ELSE 0 END) AS users_20plus
FROM u GROUP BY 1 ORDER BY 1
```

**3. Puzzle-mode mix for one game (rollup and junk modes excluded)**
```sql
SELECT date_field, puzzle_type,
       COUNT(DISTINCT rid) AS users,
       SUM(CASE WHEN action_type = 'view'  THEN actions ELSE 0 END) AS views,
       SUM(CASE WHEN action_type = 'clear' THEN actions ELSE 0 END) AS clears   -- use 'play'/'end' for gid 10/20
FROM server_tables.engagement_puzzle_master_cc_col
WHERE date_field BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND gid = {gid}
  AND puzzle_type <> 'overall'
  AND puzzle_type <> '' AND NOT regexp_like(puzzle_type, '^[0-9]+$') AND puzzle_type <> 'trackBlock'
  AND action_type IS NOT NULL
GROUP BY 1,2 ORDER BY 1, users DESC
```
