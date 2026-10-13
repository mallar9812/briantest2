# Competitor / Market Intelligence — Sensor Tower (opt-in only)

## Rollups & mandatory pins

**None.** Neither Sensor Tower table carries a rollup value. The pivoted `metric` column on
`sensor_tower_data` is not a rollup — it is a long format holding several different metrics, so **always
filter to the one metric you want** rather than summing across `metric`. `value` is STRING: cast before
aggregating.

| Table | Purpose and rules |
|---|---|
| `external_data.sensor_tower_data` | Third-party Sensor Tower **estimates** for non-Playsimple apps: revenue, downloads, active_users, d1/d7/d14/d30 retention, session counts and duration, time spent. **Long/pivoted format** — one row per `product_id` + `platform` + `country` + `date_field` + `metric`, with the number in `value`. `value` is STRING: cast before aggregating. Date column `date_field` (daily grain). |
| `external_data.st_product_details` | Competitor app lookup. Join on `product_id` for `product_name`, `publisher_name`, `game_class` / `game_genre`, `platform`, content rating, release date, and monetization flags. |

## Rules

- **Opt-in only.** Query these tables **only** when the user explicitly asks about a competitor, rival
  app, or market/genre benchmark. Never surface them as a default add-on to a portfolio KPI answer.
- **Third-party estimate, never ground truth.** Always label figures "Sensor Tower estimate". Never use
  them in place of, or blended into, Playsimple's own internal figures.
- **Cross-comparison:** pull Playsimple's number from its normal internal table and the competitor's from
  Sensor Tower, labeling each side explicitly ("Playsimple — internal" vs "[Competitor] — Sensor Tower
  estimate").
- **Resolve `product_id` first.** If the user hasn't given one, query `st_product_details` filtered on
  `product_name` / `publisher_name` (fuzzy match) before running the metric query. Multiple plausible
  matches (same game on several platforms, similarly-named apps) → list them and confirm rather than
  guessing.
- **Never route a competitor through the Playsimple GID mapping** — competitor apps have no GID.
- **No drill-down exists** for third-party data: no franchise, cohort, payer, or network cuts.
- **No spend/cost data exists.** Never approximate a competitor ROAS or any spend-derived metric — say the
  underlying field isn't available. If a question needs a derived competitor metric not listed below, say
  the underlying field isn't available rather than approximating one.
- **Units:** all session/time metrics come out of the source in **seconds**. Convert only if the user asks,
  and state the conversion explicitly — never silently rescale.

## Metric formulas

| Metric | Type | Field / Formula |
|---|---|---|
| revenue | Raw (pivoted) | `metric = 'revenue'` |
| downloads | Raw (pivoted) | `metric = 'downloads'` |
| active_users | Raw (pivoted) | `metric = 'active_users'` |
| D1 / D7 / D14 / D30 retention | Raw (pivoted) | `metric = 'd1' / 'd7' / 'd14' / 'd30'` — % of D0 users still active on that day (confirmed with the data owner, not derived) |
| total_session_count | Raw (pivoted) | `metric = 'total_session_count'` — total number of sessions |
| session_count | Raw (pivoted) | `metric = 'session_count'` — a distinct raw field from `total_session_count`; do **not** assume it equals sessions per user unless the user confirms |
| session_duration | Raw (pivoted) | `metric = 'session_duration'` — average duration per session, **in seconds** |
| total_time_spent | Custom | `session_duration * total_session_count` (confirmed formula), **in seconds** |
| time_spent | Custom | `session_duration / active_users` (confirmed formula, per the data owner), **in seconds** |

## Dimensions

`product_id` (competitor app identifier — no GID; resolve via `st_product_details`), `platform` (android,
ios), `country`, `date_field` (daily), `metric` / `value` (long format — pivot). Joined descriptive fields
(from `st_product_details`): `product_name`, `publisher_name`, `unified_publisher_name`, `game_class`
(Sports & Racing, Casino, Action & Strategy, Lifestyle & Puzzle, None), `game_genre`, `game_sub_genre`,
`game_product_model`, `content_rating`, `release_date`, and monetization flags (`has_iap`, `has_video_ads`,
`has_banner_ads`, `has_image_ads`, `has_playables`, `has_w2e`).

Query template: `references/query-templates.md`.
