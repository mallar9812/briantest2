# Revenue Drill-Down — `chart_2077-vN`

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`.

## Rollups & mandatory pins

Three on `chart_2077-vN`, all live:
- **`mediation = 'overall'`** — rollup. Pin for totals, exclude when drilling named mediation layers.
- **`country = 'others'`** — long-tail rollup. Exclude from country-level sums.
- **`id_type` — default-pin `'rid'` where the column exists** (the data-dictionary sheet says it may be
  absent here; verify before relying on it).

`ad_network`, `rev_type`, cohort-age, LAT, payer, `install_type` and `device_language` carry no rollup value
and sum normally.

Segment-level decomposition table for "why did X move?" — the cuts the core tables lack: ad network and
mediation, `rev_type`, install cohort age, LAT/payer/install-type/device-language splits.

**Date column in Druid is `"__time"`.** (The retired warehouse original used `time` — irrelevant now.)

## Hard filter rules

| Metric(s) | Rules |
|---|---|
| revenue, impressions, users by network, mediation, rev_type, cohort, country, install source, and more | **Revenue here is NOT ad-only** — `rev_type` includes an `IAP` value, so IAP and ad revenue share the `revenue` column. Always filter or group by `rev_type` before treating a `revenue` sum as ad revenue. The data is also multiplied across mediation × ad_network rollups: **default to `mediation = 'overall'` AND `ad_network = 'overall'` AND `id_type = 'rid'`** — pin all three unless the user explicitly asks about a specific network or mediation platform. When drilling exactly one of `mediation` / `ad_network`, pin the other to `'overall'`. Never sum without these pins. |

*Schema note to verify:* the data-dictionary sheet says `chart_2077` has **no `id_type` column** — that
pin belongs to the sessions-style tables (`chart_2524`). This is a Druid datasource, so check it with
`SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'chart_2077-vN'`; apply
the pin only where the column exists.

## Interpretation rules

- **Exclude invalid traffic by default.** `install_bucket = 'reject'` and `install_source = 'untrusted'`
  are invalid-traffic buckets — exclude unless the user is specifically analyzing fraud, and state the
  exclusion when you make it.
- **`cohort` is retention-age, not a calendar date.** Values run `D00, D01, D02-D07, D08-D14, D15-D30,
  D31-D60, D61-D120, D121-D180, D181-D240, D241-D360, D361-D720, D720+` — age-since-install as of `time`.
  A `D720+` row on a recent `time` is an old cohort still active, not a data error. Never join or filter
  `cohort` against `time` as if they share an axis.
- **`country = 'others'` is a long-tail rollup** — don't treat it as a real country when summing or
  grouping by country.
- **`device_lang = 'N/A'`** means unknown, not a locale — exclude or flag it rather than treating it as a
  language segment.
- **`lat_flag = 'lat'`** (Limit Ad Tracking) users generally can't be network-attributed — expect
  `install_source` to skew organic/unknown for those rows; never read that skew as an organic gain.
- **Freshness guard:** on first use in a conversation, check `max(time)`; if it trails today by **2 or
  more days**, flag it and don't treat the tail as signal. (Was >3 days — the ordinary D-2 gap slipped
  through unflagged.)
- **Delivery-lag guard — the D-2 default:** revenue and spend post on a ~2-day lag, so treat data as
  complete only through **D-2** unless the freshness check proves otherwise. Never present the trailing
  1–2 days as a real move. A trailing-day `0` is undelivered data, not a decline.
- **Cross-source rule:** headline (L0) numbers come from the core/cohort/prediction tables; this table is
  for decomposition only. Never mix sources within a single metric's headline figure, and note when
  drill-level sums won't exactly tie to the L0 source.

## Metric formulas

| Name | Type | Formula | Description |
|---|---|---|---|
| impressions | Normal | `impressions` | Ad impressions served at the row's grain. |
| revenue | Normal | `revenue` | Revenue at the row's grain — **not ad-only**; filter by `rev_type` first, since IAP is mixed in. |
| users | Normal | `users` | Distinct users contributing to the row that day. |
| eCPM | Custom | `revenue / impressions * 1000` | Revenue per 1,000 impressions — the standard ad-yield comparison. Filter `rev_type` to ad formats (excluding IAP) when the intent is ad yield. |
| Rev/User | Custom | `revenue / users` | Average revenue per user at the row's grain. |

These are the only metrics carried at this grain — do not invent additional base fields.

## Dimensions

- `time` — DATE, the event/reporting date (**not** the install date).
- `gid` (INT), `cli` (0/1/2).
- `country` — 135 values plus `"others"` (long-tail rollup — exclude from country-level sums).
- `ad_network` — 44 networks (applovin, admob, inmobi, unity, vungle, fan, aps, fyber, bidmachine, ironsource, moloco, pubnative, mintegral, reklamup…) plus the `"overall"` rollup, **default-pinned**.
- `mediation` — ironsource, admob, fairbid, max, prebid, postbid, odeeo, bright, plus `"overall"` rollup and `"NA"` (no mediation layer). Same default-pin rule as `ad_network`.
- `rev_type` — interstitial, banner, rewarded video, offerwall, app_open, audio, w2e [likely watch-to-earn, unconfirmed], btob_w2e, ad_on_inactivity, screen_transition, mid_interstitial, others, **and `IAP`**. Revenue is mixed — always filter or group by this before treating `revenue` as ad-only.
- `install_source` — 108 values (applovin, facebook, apple_search, unity, quest_center [xpromo hub], adwords (search), adwords (others), organic variants, `untrusted`…).
- `install_bucket` — organic, paid, xpromo, p2e [likely play-to-earn, unconfirmed], untagged, `reject`, plus organic/preload splits. **Exclude `reject` from "real users" totals by default.**
- `cohort` — retention-age bucket as of `time`: D00, D01, D02-D07, D08-D14, D15-D30, D31-D60, D61-D120, D121-D180, D181-D240, D241-D360, D361-D720, D720+. Age-since-install, **not** a calendar axis.
- `lat_flag` — lat / non-lat (Limit Ad Tracking); `lat` rows skew organic/unknown on `install_source`.
- `payer_flag` — payer / non_payer (≥1 IAP as of that cohort age).
- `install_type` — only_install / reinstall.
- `device_lang` — 42 locales plus `"N/A"` (unknown — treat as missing, not a segment).
- `id_type` — identifier grain; **default-pin `'rid'`** where the column exists (the sheet says it may not exist on this table — verify).
- `inserted_at` — ETL load timestamp; freshness checks only, never a business dimension.
