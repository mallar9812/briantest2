# The `puzzle` / `dp` / `bonus_level` kingdoms — a ground-truthed decode

These three kingdoms (`k='puzzle'` = the main level screen, `k='dp'` = Daily Challenge/Daily
Puzzle, `k='bonus_level'` = bonus levels) share an identical `c` field layout and mostly-identical
`o` vocabulary — a large chunk of `event_taxonomy_full.csv`'s rows are documented once under a
combined kingdom tag (`puzzle/dp/bonus_level`, `puzzle/ dp`, and two typo'd variants
`puuzle/dp/bonus_level` / `puzle/dp/bonus_level`) because the field meanings are the same
regardless of which of the three screens the event actually fired on. **When looking up an event
for one of these three kingdoms, grep the CSV for all of these kingdom-tag spellings, not just the
literal one you're querying** — `o='wand'` (the magic wand powerup), for example, only appears
under the combined-kingdom rows, not under a `k='puzzle'`-only row, even though it fires with
`k='puzzle'` in the live data.

This file is the ground-truthed version of that decode — confirmed against how the fields actually
behave, not just the CSV's generic placeholder labels, by an analyst on this game.

## `p` — differs by kingdom, don't reuse across them

| Kingdom | `p` format | Meaning |
|---|---|---|
| `puzzle` | `<pack_id>_<puzzle_id>` | `puzzle_id` (after the `_`) is the real progression number — validated as a genuine sequential counter (a fresh installer's first three clears carried `p = 1_1`, `1_2`, `1_3`). `pack_id` (before the `_`) just buckets levels into groups; `pack_id` and `puzzle_id` rise together, so treat `pack_id` as a derived grouping, not an independent axis. |
| `dp` | `<week_number>_<day_number>` | A calendar position within the Daily Challenge cycle, not a level number. |
| `bonus_level` | `<challenge_number>` | A single value, not two parts. |

Do not apply the `puzzle_id`-as-progression reading to `dp` or `bonus_level` rows — only `k='puzzle'`
gives a level-progression number from `p`.

## `c` — identical across all three kingdoms

`c = <seed_id>_<attempt_number>_<content_set>_<json_version>_<diff_preset>`

| Part | What it is | Reading notes |
|---|---|---|
| `seed_id` | An **RNG seed** used to procedurally generate the level's board/content | Not a content identifier — it's a randomization input, and it's *expected* to be reused across many unrelated levels (one seed observed mapped to 51,000 different `content_seeds.level` rows). **`play_zenconnect.content_seeds` is a seed-reuse/board-design catalog, not a level-lookup or progression table — don't join it expecting a 1:1 level mapping.** |
| `attempt_number` | The attempt count on this specific level instance, **1-indexed** | `attempt_number = 1` is the first real try; it increments per retry. **A value of `0` means the field wasn't populated for that row / the row doesn't cover an important action — treat `0` as missing data, not as "try zero."** Filter it out before using this as a struggle/frustration signal. |
| `content_set` (content id) | The content set/track a level is provided from | **Not permanently fixed by design** — it can change, it's just usually not changed often in practice. Don't assume it's a hard-static tag for a given seed/level without checking. |
| `json_version` (`x.y` format) | **The real live content-version indicator** | Increments whenever any content update ships. This is the field to use for "was new content live for this user" — not `content_seeds.json`, which is a coarser/separately-maintained catalog value that does not reconcile with this live per-event version (confirmed: same seed showed `json_version=13.36` in a live event but `content_seeds.json='14.9'` for that seed). |
| `diff_preset` | A predetermined difficulty preset | **Not ordinal in raw numeric order.** True easy→hard order is **5 < 0 < 1 < 2 < 3 < 4** (preset `5` is the easiest, `4` the hardest). Remap through this order before treating it as a difficulty scale — the raw digit is not usable directly. |

## A dedicated content-version event exists — use this instead of decoding `c` for version questions

**`k='content_version'`** fires once per session start: `p='session_start'` (a fixed tag), `c=<player
geo>`, and — unusually for this taxonomy — **the content version itself is the value of `o`** (not a
fixed action name), with `f=<json version>`. This is the correct source for a user-date →
content-version mapping (e.g. for a content-drought test: did this user's content version ever
change during their observed window), rather than parsing it out of every `puzzle`/`dp`/`bonus_level`
event's `c` field.

## Every `o` (action) value encountered under `puzzle`/`dp`/`bonus_level`, grouped by function

61 distinct `o` values across the literal `puzzle`/`dp`/`bonus_level` rows and the combined-kingdom
rows, after merging build-updated duplicates. Grouped here by what they're useful for, not by the
CSV's declaration order.

### Level lifecycle
`load_start`, `first_level`, `view`, `clear`, `fail`, `quit`, `retry`, `replay`, `settings`

- The richest field in the whole kingdom is `s` on the current-build `view` event: `<no. of
  tiles>_<no. of layers>_<tiles on top>_<distinct symbols>_<matches on first visible layer>_<duplets
  on first visible layer>_<matches on top-2 visible layers>_<duplets on top-2 visible layers>_<9-value
  symbol distribution array>` — a full solvability/difficulty snapshot at the moment a level starts,
  independent of `diff_preset`.
- `clear`'s `f` = how many times this level has been cleared (replay count); `s` = powerup usage
  (`undos_wands_shuffle_revives`, or the `extra_slot`-variant equivalent).
- `fail`'s `s` = tiles remaining on the board — a near-miss / closeness-to-clearing measure.

### Powerups
`undo`, `shuffle`, `revive`, `revive_time` (dp/bonus_level timed variant), `wand`, `extra_slot`,
`<powerup_name>` (the IAP/out-of-powerup popup), `pu_prompt`, `pu_board_view`, `pu_board_click`
(Picnic Rush)

- `f`=click/success/fail, `g`=click type + symbol/reason-for-fail, `s`=rack/board tile counts at the
  moment of use, for each of the five core powerups.
- `<powerup_name>` fires specifically when a player taps a powerup with **zero inventory**
  (`g='oop'`, out-of-powerups) — a monetization-friction event distinct from normal usage.
- `pu_prompt` (proactive "try this powerup" nudge, start/close pair) carries shown/skip/cycle
  counters in `s` — a powerup-prompt-fatigue signal.

### Difficulty / DDA (dynamic difficulty adjustment)
`level_easing`, `level_easing/algo_version`, `dda` (3 build/version variants), `hard_level_tag` (3
variants), `matches_on_top`, `matches_on_top2`, `matches_available` (3 variants incl. a QMT one),
`no_matches`, `no_match_tile_highlight`, `no_match_undo_highlight`, `no_match_toaster`, `challenge`,
`zoom`

- The DDA events matter most here: the game **actively eases levels for strugglers**
  (`level_easing`/`dda` guardrail variants) but can also **actively harden levels for high-skill
  players** (`dda`'s `first_try_high_diff` variant, DDA v2) — `g`=`difficulty_preset` assigned in
  either direction. Any pace/progression-linked engagement finding should be cross-checked against
  this — a fast, skilled player showing a steeper engagement decline could be partly explained by
  the DDA system assigning them objectively harder content, not just fatigue.
- `matches_available`'s `g` = the player's live powerup/coin inventory at that exact solvability
  check — ties difficulty and economy together in one row.
- One `matches_available` variant has a flagged tracking bug in the source mapping (`f' field needs
  to be updated`) — don't trust that field on that variant without checking.

### Hints / assistance
`hint_view`, `hint_tap` (NACTA feature + updated "Hint System Opts" variant, 2 rows each),
`how_to_play`, `player_idle` (bubble-pop feature), `rack_pulsate`, `rack_highlight`, `tile_highlight`,
`tile_rack_tap` (2 variants), `locked_tile`

- `s` on `hint_view`/`hint_tap` = seconds of inactivity before the hint triggered — a genuine
  idle/stuck timer, not just a binary "hint shown" flag.
- `player_idle`'s `f` = time since last move — the same idea via a different feature.

### Obstacles
`hidden_tile_reveal`, `hidden_tile_dig` — only relevant on levels using the hidden-tile mechanic.

### Board interaction / telemetry
`tile_move` (marked **"removed"** in the source mapping — may no longer fire), `gameboard` (also
marked **"removed"**), `tile_select` (current version, merged from `tile_move`+`tile_rack`),
`tile_rack` (superseded by `tile_select`), `set_clear`, `match_ready`, `gratif`, `quartile_complete`,
`screen_tap_load`, `tutorial_screen_tap`

- `gratif`'s `f` (`match_streak`/`close_call`/`rack_clear`/`slow_match`/`board_clear`/`match_ready`)
  is a positive-reinforcement-moment tracker; `g`=streak_length for the streak variant.
- `quartile_complete` fires at 25/50/75% of a level (by sets, not tiles) — gives partial-completion
  granularity that binary clear/fail/quit can't (e.g. quitting right after 75% reads very differently
  from quitting immediately).

### Economy / social / live-ops
`store_page`, `zen_points`, `star_wallet`, `streak` (**3 distinct meanings** — core Puzzle Streak
System, Picnic Rush, and Leaderboard — heavily overloaded, disambiguate by feature/live-ops context,
not by `o` alone), `quest_centre`, `qmt_allocate`, `qmt_reveal`, `w2e`, `oopc`, `not_oopc`

- `store_page`'s `s` = total wallet at that moment — a currency-consciousness snapshot.
- `quest_centre`'s `f` = all 9 quest statuses at once (incomplete/complete/collected) plus
  watering-can count.

### Other / low signal for lapse-style hypotheses
`notif_perm_similar_tap` (an **in-app** notification pre-prompt tap — distinct from the OS-level
permission check tracked in `server_tables.notifs_master_cc_new`), `write_to_us` (rare
feedback-channel tap).
