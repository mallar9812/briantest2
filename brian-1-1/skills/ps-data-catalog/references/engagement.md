# Sessions, Engagement, Economy, WAU/MAU, DAU Reconciliation

Extended catalog. Same discipline as everywhere else: query-only, verify the live schema before claiming a
field is unavailable, and never mix these decomposition tables into an L0 headline figure.

## Rollups & mandatory pins

- **`id_type` — always pin `'rid'`, on the charts that have the column.** Not every chart in this family
  carries it, so the pin is mandatory where present and a query error where absent — **check the table
  below before writing the filter**, rather than adding it everywhere and discovering the gap through a
  column-not-found:

  | Chart | Carries `id_type`? | Pin |
  |---|---|---|
  | `chart_2524-vN` sessions | yes | `id_type = 'rid'` |
  | `chart_2898-vN` actions | yes | `id_type = 'rid'` |
  | `chart_2917-vN` economy | **no** — absent on `chart_2917-v11` (verified Oct 2026); filtering on it fails | none |
  | `chart_2888-vN` WAU/MAU | yes | `id_type = 'rid'` |
  | `chart_2076-vN` DAU | yes — **and it is the one chart where the value matters** | `id_type = 'rid'` |
  | `chart_2301-vN` rolling retention | **no** — the column does not exist; filtering on it fails | none |

  **`chart_2076` stacks two independent populations in this column** (`rid` internal and `adjust`
  network-reported). Summing across them roughly doubles DAU, and because it fails silently it lands in
  every per-DAU ratio built on this chart as an inexplicably halved rate. **A per-DAU rate coming back
  near half its expected level is this pin, missing** — check it before questioning the metric (SR-19).
  The pin is at its most fragile when a query is rewritten to fix something unrelated; re-verify it
  survived (query-engines guardrail 7).
- **`category = 'overall'` on the economy chart (`chart_2917-vN`)** — a grand-total rollup row stacked in the
  same column as real sub-categories. Pin for totals, exclude when drilling.
- **`puzzle_type = 'w/o puzzle_type'` on `chart_2898-vN`** — a rollup/sentinel beside the named modes.
- **`country = 'others'`** — long-tail rollup; exclude from country-level sums.

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`.

## Which chart answers which question — decide here, don't scan the file

| Question is about | Chart | Metrics it carries |
|---|---|---|
| Sessions, time spent, sessions per DAU | `chart_2524-vN` | sessions, session_users, time_spent |
| Engagement / in-game actions, actions per DAU, puzzle-mode (`puzzle_type`) or action-type cuts | `chart_2898-vN` | actions, users |
| Rolling retention (D1/D3 rolling flags) | `chart_2301-vN` | retained_users |
| In-game economy / virtual currency (earn, spend, purchase) | `chart_2917-vN` | total_cash, users |
| WAU, MAU, stickiness | `chart_2888-vN` | wau, mau |
| DAU reconciliation (rid vs Adjust), permission givers, per-DAU ratio denominator | `chart_2076-vN` | dau, lat_users, permission_givers |

Every name here is written `chart_XXXX-vN` deliberately: `N` is resolved from `chart_config` this
conversation, per chart, including charts reached mid-analysis. Never carry a version across charts.

**There is no `chart_2971`.** It has no rows in `play_data.chart_config` — the engagement/actions table is
`chart_2898` (config-verified metrics: `actions`, `users`). If an older doc or memory says 2971, it is stale.

## Dimensions shared across this family

These dimensions recur on most tables below with the same meaning. Per-chart sections list only the
dimensions unique to that chart and any behavior that deviates.

| Dimension | Description |
|---|---|
| `"__time"` | Calendar date of the activity (the DAU/event date, **not** the install date). |
| `gid` | Numeric game ID — resolve names via `ps-entities`. |
| `cli` | Numeric platform/client ID: 0 = Android, 1 = iOS, 2 = Amazon. Some tables here also carry 5 (meaning unconfirmed — flag if encountered). |
| `country` | Lowercase ISO alpha-2 code (us, gb, ca, au, de…) plus an `others` long-tail rollup — exclude `others` when summing to a named-countries total. |
| `cohort` | Retention-age bucket **as of `time`** (age since install, not a calendar axis): D00, D01, D02-D07, D08-D14, D15-D30, D31-D60, D61-D120, D121-D180, D181-D240, D241-D360, D361-D720, D720+. Raw LD-prefixed codes are normalized to D-buckets upstream. |
| `install_bucket` | High-level acquisition bucket: organic, organic (google play), organic (w/o google play), organic (dt_t1), paid, paid (preloads), paid (preloads dt_t1), xpromo, p2e, reject, untagged. **Exclude `reject` (invalid traffic) from real-user totals by default and state the exclusion.** |
| `install_source` | Granular UA network/attribution source (100+ values: organic, applovin, unity, facebook, adwords (search)/(others), apple_search, ironsource, quest_center / quest_center (high) [xpromo hub tiers], mistplay, untrusted, deeplink, invite…). Finer than `install_bucket`; one bucket maps to several sources. |
| `lat_flag` | lat / non-lat — Limit-Ad-Tracking / ATT opt-out. NULL appears where the flag doesn't apply or wasn't captured — **don't treat NULL as non-lat**. |
| `payer_flag` | payer / non_payer — ever made an IAP as of that cohort age. |
| `device_type` | Hardware form factor: phone, tablet, tv, pc, console, ipod (phone dominates; the rest are low-volume edge categories). |
| `dau_build` | Integer app build/version the user was on for that day's activity (sourced from the DAU table). High cardinality — build-level cuts only. |
| `install_type` | only_install (fresh first-time install) / reinstall. |
| `session_bucket` | That day's session-count bucket: S00 (0 sessions), S01, S02, S03-S05, S06-S10, S10+. Users with no session-count row fall through to S10+. |
| `os_version_bucket` | Bucketed OS version: numeric majors (13–19, 26, 27), minors (17.1–18.7, 27.0/27.2), boundary buckets <13/<14, Android state suffixes ("13 installed" vs "13 updated"), plus others. |
| `notif_permission` | `given` if the user had a recorded notification-permission grant on or before that day's DAU date, else `not_given`. **Not present on `chart_2524-vN`** (confirmed live Aug 2026) — check the per-chart section before using it. |
| `att_status` | iOS App-Tracking-Transparency status: authorized, restricted, not_determined, global_denied, local_denied, or empty. Only populated for `cli = 1` (iOS) — NULL elsewhere; don't filter on it for Android cuts. **Not present on `chart_2524-vN`** (confirmed live Aug 2026) — check the per-chart section before using it. |
| `stable_flag` | stable / non_stable — derivation unconfirmed; per the data owner it carries no reliable business meaning. Ignore it, don't filter or group by it. |
| `device_lang` | Device language (en, es, fr, de, pt, it…); `N/A` = missing/unset (the most common value — treat as unknown, not a locale); `others` = outside the tracked list. |
| `id_type` | Identifier grain — **always pin `'rid'`** where the column exists; see the presence table under "Rollups & mandatory pins" for which charts have it (`chart_2301-vN` does not). Only `chart_2076-vN` meaningfully carries a second value (`adjust`), and leaving it unpinned there roughly doubles the DAU denominator. |
| `inserted_at` | ETL load timestamp — freshness checks only, never a business dimension. |

## `chart_2524-vN` — Sessions / time spent

DAU, sessions, and time spent by acquisition channel, cohort, geography, and device — an engagement
segmentation table, not a revenue table. **Always pin `id_type = 'rid'`.**

| Name | Type | Definition |
|---|---|---|
| Sessions | Normal | Count of qualifying session events per rid, summed. **gid 20:** has no `start` rows — counted on `app_pause`. **gid 10:** live `chart_2524` counts `start` + `app_pause` (≈25–28 sessions/DAU; experiment DAGs count `start`/`resume` only, ≈6 — state which). **All other gids:** counted on `start` or `resume` (verified against `server_tables.sessions_master_cc`, Oct 2026 — `references/uld/server_tables.sessions_master_cc.md`). Session length is capped before counting — out-of-cap sessions are dropped entirely, not truncated. |
| Session Users | Normal | Distinct rid with at least one counted session that day, within the same dimension slice. |
| Time Spent | Normal | Total in-session seconds that day. **gid 20:** only sessions between 0 and 7,200 seconds (2 hrs). **All other gids:** sessions between 0 and 100,000 seconds. |
| Sessions per DAU | Custom | `sessions / dau` — dau from `chart_2076`, per the cross-dataset ratio rule below. |

Dimensions — **this exact closed list, not the whole shared set**: `id_type`, `time`, `gid`,
`cli` [0/1/2 only], `country`, `cohort`, `install_bucket`, `install_source`, `lat_flag` [includes
NULL here], `payer_flag`, `device_type`, `dau_build`, `install_type`, `session_bucket`,
`inserted_at`.

⚠️ **`att_status` and `notif_permission` do NOT exist on this datasource.** Confirmed live
(Aug 2026, `chart_2524-v11`): both return
`Column 'att_status' not found in any table` / `Column 'notif_permission' not found in any table`.
They appear in the shared-dimension table above because other charts in this family carry them —
that table describes the family, **not** every chart in it. So an ATT-opt-in or
notification-permission cut of sessions / time spent / sessions-per-DAU **is not available**: say
the cut can't be made from this datasource rather than reaching for a proxy, and don't spend a
column-not-found round trip discovering it. (A column-not-found here is not an engine-fallback
trigger and not a version/variant sort error — it is a genuine absence.)

## `chart_2898-vN` — Engagement / actions

Daily engagement and action counts by game, client, and user segment, joining puzzle / eoc ("end of
chapter") / dialog activity to DAU-day install and device attributes — it is **not** puzzle-only.
(Formerly misdocumented as `chart_2971` — that ID does not exist in `chart_config`.)

| Name | Type | Definition |
|---|---|---|
| Users | Normal | Distinct engaging users (rid) for the day/dimension slice. |
| Actions | Normal | Sum of the actions field from the underlying engagement/dialog tables. |
| Actions per DAU | Custom | `actions / dau` — dau from `chart_2076`, per the cross-dataset ratio rule below. |

Dimensions beyond the shared set:

| Dimension | Description |
|---|---|
| `puzzle_type` | Game-mode/puzzle segment: named modes (Main/main, Puzzle/puzzle, daily_puzzle, daily_mini, daily_challenge, crossword_go, word_ladder, pack, archive, bonus_archive, vip_puzzle, p2e, dp, LLP-Big/Midi/Mini/small, others) **plus a `w/o puzzle_type` rollup — pin to either the named-mode rows or the rollup, never sum both.** |
| `action_type` | Specific in-game action: clear, w_clear, frenzy_clear, view, play, pass, fail, use_hint, use_bomb, use_hammer, timer, chat, store, submit, reveal_letter, cashout, eoc. |

Notes: `gid` shows 37 distinct values (4, 8, 9, 10, 11, 14, 15, 17, 20, 22, 24–55 with gaps); `cli`
includes value 5 here (unconfirmed — flag it); `att_status` populated only for `cli = 1`.

## `chart_2301-vN` — Rolling retention

Daily rolling-retention user counts by game, client, and user segment, sourced entirely from the DAU
table's rolling-retention flags — no event/action table involved.

| Name | Type | Definition |
|---|---|---|
| Retained Users | Normal | Distinct rid flagged rolling-retained for the date/dimension/`metric` combination — still active as of the D1 or D3 rolling window. |
| Rolling retention rate | Custom | `retained_users / dau` — dau from `chart_2076`, per the cross-dataset rule below. |

Dimension beyond the shared set:

| Dimension | Description |
|---|---|
| `metric` | Which rolling window the row belongs to: `D01_rolling` (`d1_rr_flag = 'Y'`) or `D03_rolling` (`d3_rr_flag = 'Y'`). Only these 2 values — the key dimension to filter/group by. **The populations overlap; never sum across both.** |

## `chart_2917-vN` — In-game economy (virtual currency)

Daily virtual-currency flows by game, client, and user segment, split by how the cash moved (`earn_type`)
and which in-game feature generated it (`category`).

| Name | Type | Definition |
|---|---|---|
| Total Cash | Normal | Sum of virtual-currency movement — a **signed net** amount: positive for earn/purchase, negative (or zero) for spend. Not an absolute volume — a small net can hide large gross flows in both directions; group by `earn_type` to see them. |
| Users | Normal | Distinct rid with at least one qualifying cash-movement row for the slice. |

Dimensions beyond the shared set:

| Dimension | Description |
|---|---|
| `category` | Economy sub-category — two structurally different kinds of value in one column: the literal `'overall'` (a grand-total rollup row) and named categories (puzzle_solved, w2e, normal_hint, quest_center, daily_reward, hint, spin, bonus_words, others…). **Never sum `'overall'` together with the named rows — it already is their sum.** |
| `earn_type` | How the cash moved: earn (positive — gameplay), purchase (positive — bought with real money), spend (negative/zero — spent in-game). 3 values. |

Notes: `cli` includes 5 (unconfirmed); `stable_flag` carries no real meaning here — ignore it.
**`total_cash` mixes units:** the chart is `server_tables.economy_master_cc` inner-joined to `dau_splits` with **no `cash_type` filter**, so coins (`cash`) are summed together with item counts (spin, hints, lives, inventory). Treat cross-category totals as directional; for coin-only flows use the ULD table with `cash_type = 'cash'` (`references/uld/server_tables.economy_master_cc.md`).

## `chart_2888-vN` — WAU / MAU

Daily trailing-window active-user counts. **WAU** = distinct rid active in the trailing 7-day window
(`time` − 6 through `time`, inclusive); **MAU** = trailing 30-day window. MAU ≥ WAU for the same row.
Pin `id_type = 'rid'`. Stickiness = `dau / mau` where a DAU figure at the same grain is available
(dau from `chart_2076`, per the cross-dataset rule). If the user says "WAU/MAU stickiness", note that
`wau / mau` is a different ratio computable from this table alone — state which one you're reporting.

**Caveat:** each row's dimension values (country, install_source, install_bucket, lat_flag, device_type)
reflect the segment the user was in on the specific day they were active within the trailing window — not
necessarily their segment as of `time`.

Dimensions: shared set, with `time` meaning the "as of" reporting date the trailing windows end on. No
cohort/payer/build/OS dimensions here — the confirmed set is `id_type`, `time`, `gid`, `cli`, `country`,
`install_source`, `install_bucket`, `lat_flag`, `device_type`, `install_type`, `inserted_at`.

## `chart_2076-vN` — DAU (internal rid vs Adjust)

Two structurally different sources stacked in one table via `id_type`: internal rid-level DAU (with
session/permission/OS/device detail) and external Adjust-reported network DAU (aggregate, no user-level
join). Use it for reconciliation. **Never sum rid and adjust rows together; default `id_type = 'rid'`.**

| Name | Type | Definition |
|---|---|---|
| DAU | Normal | Daily active users for the date/dimension/id_type combination — for `id_type = 'rid'`, distinct rid at the row's grain. |
| Permission Givers | Normal | Distinct rid with a recorded notification-permission grant on or before that day. Only meaningful for `id_type = 'rid'` — always 0 for adjust rows. |
| Lat Users | Normal | Distinct rid with `lat_flag = 'lat'` (config-verified metric; rid branch only). |

- Adjust rows have most segment dimensions hardcoded to "NA" (cohort, lat_flag, payer_flag, install_type,
  os_version_bucket, notif_permission) and `dau_build` hardcoded to 0.
- `session_bucket` fall-through: users with no session-count row land in S10+.

### Cross-dataset ratio rule

`chart_2076-vN.dau` is the denominator for per-DAU ratios against this **fixed** list only:
`chart_2077-vN`, `chart_2524-vN`, `chart_2898-vN`, `chart_2857-vN`, `chart_2856-vN`, `chart_3341-vN`,
`chart_2301-vN`, `chart_2888-vN`. (Older docs also listed `chart_2971` — stale; that ID doesn't exist.
Its entry in the list *was* `chart_2898`.) **Do not extend this pattern to any other dataset.** Method:
query each table separately, **pin `id_type = 'rid'` on every side that has the column** (the presence
table above says which do), aggregate both sides to the shared grain, then divide — never force a
row-level join. A filter that exists on only one side applies only where the column exists: simply
ignore it on the other side — don't drop the metric and don't error.

**The denominator is where these ratios go wrong.** Every rate on this list is built across two charts,
so the pin has to hold on the `chart_2076-vN` side independently of whatever the numerator chart needs —
and it is routinely lost when a query is rewritten for an unrelated reason. **Before reporting any rate
from this family, check its magnitude** (SR-19): a result near half the expected level is the unpinned
DAU denominator carrying both `rid` and `adjust` populations, not a real move. Confirm the pin, then
report.

## Auxiliary source tables (not queried directly by default)

`derived_tables.dau_splits` (DAU fact at user-day grain with install cohort, source/bucket, retention flags,
payer status, device, ATT status, language), `server_tables.notifs_master_cc_new`, `rid_info`,
`public.country_language_mapping`.
