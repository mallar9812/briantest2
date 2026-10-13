# Stability (Crashes / ANR) & Notifications

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`.

## Rollups & mandatory pins

**`id_type` — pin `'rid'`** on the charts here that carry it. No `'overall'` rollup on any dimension of
`chart_2856`, `chart_2857` or `chart_3341`; the build, device, permission and `install_bucket` dimensions sum
normally.

The retired warehouse originals — the unnamed Firebase stability table,
`external_data.playstore_crashes_app_version`, and the unnamed notifications table — are **retired; do
not query them.**

## `chart_2856-vN` — Firebase Crashlytics stability

The daily stability feed. Single variant, `independent_columns` empty, so every dimension is present.
Pin `id_type = 'rid'`.

Metrics (confirmed live in `chart_config`): `firebase_fatal_users`, `firebase_fatal_crashes`
(deduplicated upstream via a constructed `event_id` of issue title + timestamp), `firebase_non_fatal_users`,
`firebase_non_fatal_crashes`, `firebase_anr_users`, `firebase_anr` — all raw counts.

Rates are computed against DAU **from the core DAU chart** (`chart_579-vN-source-source_category`) at the
matching grain — `crashes / dau`, `crash_free_users = 1 - fatal_users / dau` — and must be labeled as
such. Two queries, combined client-side; there is no `dau` column on this datasource.

| Name | Type | Formula |
|---|---|---|
| Fatal crashes / users | Normal | `firebase_fatal_crashes` / `firebase_fatal_users` |
| Non-fatal crashes / users | Normal | `firebase_non_fatal_crashes` / `firebase_non_fatal_users` |
| ANR count / users | Normal | `firebase_anr` / `firebase_anr_users` |
| Crash rate | Custom | `firebase_fatal_crashes / dau` — cross-chart |
| Crash-free users | Custom | `1 - firebase_fatal_users / dau` — cross-chart |
| ANR rate | Custom | `firebase_anr / dau` — cross-chart |

- **ANR is Android-specific** ("App Not Responding") and a **separate error class** from fatal/non-fatal —
  not a subset. Never fold ANR counts into a crash total without saying so.
- `os_version_bucket` encodes version **plus** an installed/updated flag on Android, and dotted point
  releases on iOS — **not** a clean one-value-per-version axis.
- `stable_flag` (stable / non_stable / NA) is a pass-through flag — don't infer a definition for it.
- `payer_flag` runs roughly 9% payers, useful as a sanity check on segment sizes.

Dimensions (confirmed live via `INFORMATION_SCHEMA.COLUMNS`): `gid`, `cli`, `country`, `cohort`,
`dau_build`, `device_type`, `id_type`, `install_bucket`, `install_type`, `lat_flag`, `notif_permission`,
`os_version_bucket`, `payer_flag`, `stable_flag`, `att_status`.

`att_status` (iOS App Tracking Transparency): NA, local_denied, global_denied, authorized, restricted,
not_determined, blank. The local vs global denial distinction (app-level vs OS-level) is unconfirmed —
don't assert it. Only populated for `cli = '1'`.

## `chart_2857-vN` — Play Store crashes / ANR

Daily Play Store Console crash and ANR counts by game and app build version. Single variant, all
dimensions present.

Metrics: `playstore_crashes`, `playstore_anr` — raw counts; rates against DAU from the core DAU chart at
the matching grain. Dimensions (confirmed live): `gid`, `cli`, `dau_build` — that's the complete set
besides `__time`, so **no country, cohort, or acquisition cut exists here.** Say so rather than
substituting another chart.

- **Despite any "reviews" naming upstream, this datasource contains no review text and no star ratings.**
- Filtered upstream to **even-numbered builds only** (`MOD(app_version, 2) = 0`) — a deliberate
  build-selection rule, not a data artifact. Never present it as full build coverage.

## `chart_3341-vN` — Notifications performance

Who got sent a notification, who received it, who clicked. **Two variants:**

| Variant | Absent dims | Metrics |
|---|---|---|
| `chart_3341-vN-action_type` | `action_type` | `click_actions`, `click_users`, `sent_actions`, `sent_users` |
| `chart_3341-vN-action_type-notif_category-notif_type` | `action_type`, `notif_category`, `notif_type` | `all_users`, `dau` |

Note the consequence: **the send/click metrics cannot be cut by `action_type`** (it's absent from their
variant) — the metric names already encode the action, so that cut would be redundant. `notif_type` and
`notif_category` *are* available on the send/click variant, and absent from the `all_users`/`dau` one.

⚠️ **`chart_1168` is NOT the notifications chart.** It carries only `users` and `dau`, over `category` /
`connect_source` / `cohort` / `device_type` / `install_source` — no notification metrics at all. If a doc
or instruction points at `chart_1168` for notifications, it's wrong. `chart_1301-vN` is a lighter sibling
of `chart_3341` carrying the same four send/click metrics but **without `notif_category`** — use
`chart_3341` unless you specifically need 1301's history.

### Metric formulas

| Name | Type | Formula | Variant |
|---|---|---|---|
| sent_actions / sent_users | Normal | raw counts | `-action_type` |
| click_actions / click_users | Normal | raw counts | `-action_type` |
| all_users | Normal | union of users with a notification record and DAU-split users | `-action_type-notif_category-notif_type` |
| dau | Normal | `dau` | `-action_type-notif_category-notif_type` |
| CTR (users) | Custom | `click_users / sent_users` | `-action_type` |
| CTR (actions) | Custom | `click_actions / sent_actions` | `-action_type` |
| Users per DAU | Custom | `sent_users / dau` | cross-variant |
| Actions per DAU | Custom | `sent_actions / dau` | cross-variant |
| Users per all_users | Custom | `sent_users / all_users` | cross-variant |

### Dimensions and traps

- **`action_type` contains a misspelled duplicate:** both `alarm_received` and `alarm_recieved` exist as
  separate raw values — sum both when counting alarms. Other values: sent, click, receive, permission,
  no_permission, game_blocked, NA. Present only on the `all_users`/`dau` variant's *sibling* dimensions —
  absent from both documented variants, so treat it as an upstream concept rather than a queryable cut
  here, and verify against `INFORMATION_SCHEMA.COLUMNS` before claiming a cut on it.
- `notif_type`: l_type / c_type / others / NA.
- `notif_category` is bucketed (bonus_db, daily_puzzle, jigsaw, leaderboard, daily_challenge,
  weekly_challenge, daily_reward, dbc, quest, welcome, dc_streak, vip, digit, co_op, generic,
  letter_hunt, message, others), with a special rule stripping numeric suffixes for **gid = 37**;
  unbucketed raw values also pass through.
- **Country is pre-tiered:** allow-listed LOC games keep raw country codes; otherwise au/ca/gb collapse
  to `'Tier 1 (Non-US)'` and everything else to `'others'`. Don't expect raw ISO codes.
