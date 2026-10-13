# Ad Monetization — funnel & performance

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`.

## Rollups & mandatory pins

- **`network = 'overall'` on `chart_4495-vN` is an EXACT rollup** — it equals the sum of the named-network
  rows to the cent, so summing it with its members double-counts exactly 2x. **Default-pin `'overall'`**;
  drill named networks *instead of* the rollup, never alongside.
- **`country = 'others'`** — long-tail rollup; exclude from country-level sums.
- **No `'overall'` rollup on `ad_type` or `time_bucket`** — sum those normally.

## `chart_2160-vN` — Ad monetization funnel

End-to-end in-app ad lifecycle: request → load → view → click → close → grant (reward), plus failure and
error variants at each stage, plus a matching `*_users` distinct-user count for each stage.

**Four variants — the metric decides which one you query:**

| Variant | Absent dims (`independent_columns`) | Metrics |
|---|---|---|
| `chart_2160-vN` | none | all funnel stage counts and their `*_users` counterparts, plus `action`, `users` |
| `chart_2160-vN-ad_type-ad_unit_type-network` | `ad_type`, `ad_unit_type`, `network` | `dau` |
| `chart_2160-vN-ad_type-ad_unit_type-country-network` | `ad_type`, `ad_unit_type`, `country`, `network` | `us_dau` |
| `chart_2160-vN-country` | `country` | `us_action` |

This variant split is what enforces the old "don't slice `dau` by `ad_type` / `ad_unit_type` / `network`"
rule — those columns simply don't exist on the `dau` variant, so the mistake now fails loudly instead of
silently. A per-DAU funnel ratio therefore needs **one statement per variant** — each covering every period and segment the answer needs, never one slice per period (stage count from the base variant, `dau`
from its own variant), aggregated to the shared grain and divided client-side.

- `ad_type` values are normalized upstream: `banner_init` → banner, `interstitial_init` → interstitial,
  `rewarded_video_init` → **w2e**, `app_open_init` → app_open; offerwall/survey/screen_transition/debug
  pass through. `ad_unit_type` values containing "AO" collapse to AO; BN/BN1/BN2, IT0–IT8, RV0–RV5, VI
  pass through.
- `network` includes the literal string `"null"`, distinct from SQL NULL.
- **Unreliable metric names** — `grant_approved_per_dau` actually divides by `view`, not `dau`; flag the
  mismatch when using it. `Anchit` = `(view + view_fail) / view_request` and `dd` =
  `(load + load_fail) / dau` are ad-hoc, creator-named metrics — confirm intent before reusing either.

### Funnel metric formulas

Stage counts (each with a matching `*_users` distinct-user metric): request, load, view, click, close,
grant, grant_approved, available, not_available, retry, success, hidden, video_completed, load_fail,
load_status, view_fail, view_error, view_request, ad_type_init, sdk_init_callback_success,
price_ceiling_set, view_caching_cpm, puzzle_clear, action, users. Plus `dau`, `us_dau`, `us_action` on
their own variants.

| Name | Type | Formula |
|---|---|---|
| Fill Rate | Custom | `load / request` |
| Fill rate excl. retries | Custom | `load / (request - retry)` |
| `<stage>_per_dau` | Custom | `stage / dau` — **cross-variant**, two queries |
| Users per DAU | Custom | `users / dau` — cross-variant |
| Action per DAU | Custom | `action / dau` — cross-variant |
| US Action per DAU | Custom | `us_action / us_dau` — cross-variant, both from their own variants |
| view_to_viewRequest | Custom | `view / view_request` |
| view_to_load | Custom | `view / load` |
| click_to_view | Custom | `click / view` |
| close_to_view | Custom | `close / view` |
| grant to view ratio | Custom | `grant / view` |
| grant_approved_to_view | Custom | `grant_approved / view` |
| video_completed_to_view | Custom | `video_completed / view` |
| load failure rate | Custom | `load_fail / request`, or `(load + load_fail) / request` |

### Funnel dimensions

- `ad_type` (normalized) — banner, interstitial, **w2e**, app_open, offerwall, survey,
  screen_transition, debug. Absent from the `dau` and `us_dau` variants.
- `ad_unit_type` — AO-collapsed values; BN, BN1, BN2, IT, IT0–IT8, RV0–RV5, VI pass through.
- `network` — 34 confirmed plus `"others"` and the literal string `"null"`.
- `country` — absent from the `us_action` and `us_dau` variants.

## `chart_4495-vN` — Ad monetization performance & ad time

Daily ad monetization by game, client, country, cohort and acquisition segment, broken out by `network` /
`ad_type` / `time_bucket`. The only source with ad-*type*-level engagement and user-quality signals:
time-between-ads buckets, ad-served user counts, clicks, and D1 rolling retention / D1-D3-D7 churn
attributed to a specific ad type.

**The `time_bucket` duplication is handled structurally — do NOT `MAX()`-collapse.** In the retired
warehouse original,
`dm_admon.metrics2` carried `rev`/`imps`/`users`/`clicks`/etc. duplicated identically across all 8–9
`time_bucket` rows, requiring a collapse-then-sum subquery. **The Druid variants drop the duplicating
dimension instead**, so a plain `SUM()` on the right variant is correct — and reaching for `MAX()` there
now *understates* the figure.

| Variant | Absent dims | Metrics | Aggregate with |
|---|---|---|---|
| `chart_4495-vN` | none | `ad_time_imps`, `ad_users`, `total_time` | plain `SUM()` — these are genuinely `time_bucket`-grained |
| `chart_4495-vN-time_bucket` | `time_bucket` | `rev`, `imps`, `users`, `clicks`, `retained_users`, `d1_churn_users`, `d3_churn_users`, `d7_churn_users` | plain `SUM()` |
| `chart_4495-vN-ad_type-network-time_bucket` | `ad_type`, `network`, `time_bucket` | `dau`, `rr_retained_users`, `rr_users` | plain `SUM()` |

⚠️ `chart_config` lists the third variant's suffix in two different column orders
(`-network-time_bucket-ad_type` and `-time_bucket-network-ad_type`); **both resolve to the single
alphabetically-sorted Druid datasource `-ad_type-network-time_bucket`.** That is expected, not a
duplicate.

The segment-level repetition rules also become structural: `dau`, `rr_users` and `rr_retained_users`
repeated across `ad_type` *and* `network` in the retired warehouse original — on Druid they live on the
variant that has
neither column, so a segment with 5 ad types can no longer count its DAU 5x.

**Rules that still apply** — these are dimension-value rules, not storage artifacts:

- **`network = 'overall'` is an exact rollup.** The `'overall'` row equals the sum of the named-network
  rows to the cent. **Default-pin `network = 'overall'`** unless the user explicitly asks about a
  specific ad network; when they do, drill the named network(s) *instead of* the rollup. Never sum the
  rollup with its members — that double-counts exactly 2x. **There is no `'overall'` value for `ad_type`
  or `time_bucket`** — those axes collapse by aggregating.
- **`users`, `retained_users` and the churn counts are distinct-user counts** — never additive across
  `ad_type` or `network`. A user who saw an interstitial and a w2e ad appears in both rows.
- Revenue and the other ad metrics are **NULL for segments with no matching ad event** — don't read NULL
  as zero. Filter `"ad_type" IS NOT NULL` for any ad-metric aggregate.
- **Never present this chart's `dau` as the headline DAU** — it runs **2–16% below** the core DAU
  datasource. Headline DAU and Rev/DAU come from `chart_579-vN-source-source_category`; this `dau` is
  only a within-chart denominator, and say so when you use it.
- `rev` is restricted upstream to ad types mid_interstitial, interstitial, w2e, ad_on_inactivity,
  screen_transition — so revenue here **is** ad-only, unlike `chart_2077`; no IAP to guard against.
- `total_time` = seconds between impressions, capped 0–120, excluding sentinels −1 ("No Next ad") and −2
  ("No close") — so it is **0 on the `120+`, `No Next ad`, `No close` and NULL buckets by construction**.
  Any average built on it must be restricted to the five 0–120s buckets: 28.96s restricted vs 22.83s
  unrestricted on the same week, a 21% understatement.
- `install_bucket = 'reject'` rows force `rr_users` / `rr_retained_users` to NULL, so D1 rolling
  retention can't be computed for that bucket. **`retained_users` is *not* NULL there** — don't assume
  the same exclusion applies to the ad-type retention field.

### Metric formulas & grain

The **Variant** column says which datasource each field lives on — that *is* the grain statement now.

| Name | Type | Formula | Variant | Description |
|---|---|---|---|---|
| DAU | Normal | `dau` | `-ad_type-network-time_bucket` | Base population — distinct active rid for the segment that day. **Not the headline DAU** — runs 2–16% under the core DAU chart. |
| Revenue | Normal | `rev` | `-time_bucket` | Ad revenue, restricted upstream to five ad types — **is** ad-only, no IAP mixed in. NULL when no ad event matched. |
| Impressions | Normal | `imps` | `-time_bucket` | Ad network impressions. Same NULL behaviour. |
| Users | Normal | `users` | `-time_bucket` | Distinct users served ≥1 ad in that network/ad type — a **subset of `dau`**. Not additive across `ad_type`/`network`. |
| Clicks | Normal | `clicks` | `-time_bucket` | Ad clicks. |
| Ad users | Normal | `ad_users` | base | Distinct ad-exposed users at the bucket grain. |
| Rev/DAU | Custom | `rev / dau` | cross-variant | Ad revenue per active user. **In-chart only** — headline Rev/DAU comes from the core charts. Guard against `dau = 0`. |
| eCPM | Custom | `rev / imps * 1000` | `-time_bucket` | Ad revenue per 1,000 impressions. |
| CTR | Custom | `clicks / imps` | `-time_bucket` | Click-through rate on served impressions. |
| Impressions per user | Custom | `imps / users` | `-time_bucket` | Ad load delivered per ad-served user — denominator is `users`, **not** `dau`. |
| Total ad time | Normal | `total_time` | base | Seconds between impressions, capped 0–120, excluding sentinels. **0 on the `120+` and sentinel buckets by construction.** |
| Ad time impressions | Normal | `ad_time_imps` | base | Impressions bucketed by the time gap between ads — used to compare ad pacing. |
| Avg time between ads | Custom | `SUM(total_time) / SUM(ad_time_imps)`, **restricted to `time_bucket IN ('0 to 15','15 to 30','30 to 45','45 to 60','60 to 120')`** | base | Mean seconds between ad impressions. The restriction is mandatory. State it; report in seconds unless asked to convert. |
| Ad time impressions share | Custom | `SUM(ad_time_imps) / imps` | cross-variant | **Coverage check on ad-time instrumentation, not a performance metric.** Expect ≈1.0 — a network materially below 1.0 has missing ad-time tracking; flag as instrumentation coverage, not behaviour. |
| Rolling D1 base / retained users | Normal | `rr_users` / `rr_retained_users` | `-ad_type-network-time_bucket` | D1 rolling-retention denominator and numerator. **NULL for `install_bucket = 'reject'`.** `rr_users` is identical to `dau` on every non-reject row. |
| D1 rolling retention rate | Custom | `rr_retained_users / rr_users` | `-ad_type-network-time_bucket` | Excludes rejected installs by construction. |
| Ad-type rolling retained users | Normal | `retained_users` | `-time_bucket` | Retained users at the ad-type grain — the field for "does this ad type cost us retention". **Populated for `reject`**, unlike the `rr_*` fields. |
| Ad-type D1 retention rate | Custom | `retained_users / users` | `-time_bucket` | D1 retention of users actually exposed to that network/ad type. |
| D1 / D3 / D7 churn users | Normal | `d1_churn_users` / `d3_churn_users` / `d7_churn_users` | `-time_bucket` | Distinct users lapsed by day 1 / 3 / 7 after exposure to that ad type. Not additive across `ad_type`/`network`. |
| D1 / D3 / D7 churn rate | Custom | `dX_churn_users / users` | `-time_bucket` | Share of ad-exposed users in that network/ad type who churned by day X. |

### Dimensions

Date column is `"__time"` — the "as of" reporting date, **not** the install date. ~41 games present.

- `network` — **34 named networks plus the exact rollup `'overall'`**: applovin, admob, unity, inmobi,
  fan, moloco, fyber, vungle, mintegral, pangle, bidmachine, appbroda, bigo, reklamup, **verve**
  (remapped from pubnative), jungle, **aps** (remapped from amazon), ironsource, ogury, chartboost,
  smaato, hyprmx, adx, thetradedesk, mobilefuse, indexexchange, pubmatic, line, medianet, magnite,
  algorix, playdigo, plus a small `others`. Default-pin `'overall'`; never sum it with its members.
- `ad_type` — interstitial, w2e, ad_on_inactivity, mid_interstitial, screen_transition. **No `'overall'`
  rollup.** NULL where the segment had no ad event.
- `time_bucket` — "0 to 15", "15 to 30", "30 to 45", "45 to 60", "60 to 120", "120+", plus sentinels
  "No Next ad" (raw −1) and "No close" (raw −2). **No `'overall'` rollup.** Only the five 0–120s buckets
  carry `total_time`.
- `cohort` — D00, D01, D02-D07, D08-D14, D15-D30, D31-D60, D61-D120, **D121-D360**, **D360+**. The last
  two are rollups, **coarser than `chart_2077`'s buckets** — the two charts are not joinable
  bucket-for-bucket.
- `install_bucket` — organic, organic (google play), organic (w/o google play), organic (dt_t1), paid,
  paid (preloads), paid (preloads dt_t1), xpromo, p2e, untagged, `reject`. Exclude `reject` by default.
- `install_source` — ~94 values, higher cardinality than `install_bucket`.
- `country` — 135 lowercase ISO codes **plus the `'others'` long-tail rollup**; exclude `'others'` from
  country-level sums.
- `lat_flag` — lat / non-lat, plus a few NULLs where consent wasn't resolved.
- `payer_flag` — payer / non_payer. `cli` — 0/1/2.
- **Absent here:** no `spend`, `mediation`, `rev_type`, `install_type`, `device_lang` or `id_type`.
