# UA Delivery — Creative-Type CPI Decomposition (`chart_2454`)

Extended catalog. Same discipline as everywhere else: query-only, resolve the version and variant from
`play_data.chart_config` this conversation (`references/query-engines.md`), verify the live schema before
claiming a field is unavailable.

> **Always group by or pin `network_name` before computing CTR, CPM, IPM or CPI.** These ratios are not
> comparable across networks, and summing across networks silently blends them.

**What it is for.** Creative-type-level UA delivery per install/spend date: impressions, clicks, installs,
spend, D1/D7 retained and recovery, plus campaign budget and bid where the network feed supplies them. Use
it to decompose CPI into CPM and IPM, and IPM into CTR and Click-to-Install. **It is not the headline eCPI
source — that is `chart_1706`** (see Verdict rule 4).

## Rollups & mandatory pins

**None.** No rollup rows to exclude. The mandatory discipline is analytic, not a filter: **always group by
`network_name`; never sum networks into one ratio.** `budget` and `bid` repeat across rows and are never
summed (see Raw metrics).

> **Engine & versions:** Druid — resolve `chart_2454-vN` and its variant per `references/query-engines.md`.
> Build every ratio client-side from summed raw columns (`SUM(spend)`, `SUM(impressions)`, …) over the
> period, **per network** — never average daily ratios (query-engines guardrail on ratios).

## Metrics

### CPI decomposition (derived)

| Metric_type | Name | Formula | Description |
|---|---|---|---|
| Custom | CPI | `{spend}/{installs}` | Spend per install for the slice. Equals `{CPM}/{IPM}`. **Per-network figure, not the portfolio headline eCPI.** |
| Custom | CPM | `{spend}/{impressions}*1000` | Cost per 1,000 impressions: the price of reach on that network. |
| Custom | IPM | `{installs}/{impressions}*1000` | Installs per 1,000 impressions: the efficiency half of CPI. `IPM = 1000 × {CTR} × {Click to Install}`. |
| Custom | CTR | `{clicks}/{impressions}` | Impression → click. **Only comparable within one network:** applovin and unity run roughly 47–85% (no close button on their ad formats); facebook and google roughly 1–4%. |
| Custom | Click to Install | `{installs}/{clicks}` | Click → install, store step included. Click-to-store-page and store-page-to-install are **not separable** in this chart. |

### Raw metrics (inputs to the formulas above)

| Metric_type | Name | Formula | Description |
|---|---|---|---|
| Normal | spend | `spend` | Network-reported ad spend for the row. |
| Normal | impressions | `impressions` | Ad impressions for the row. |
| Normal | clicks | `clicks` | Ad clicks as reported by the network; **definition differs by network — never compare across networks.** |
| Normal | installs | `installs` | Installs from the creative feed. **Does not tie to `chart_1706`** (see Datasource relationship). |
| Normal | d1_retained | `d1_retained` | Users counted as retained at D1 for the install date. Mid-Sep 2026 it is about 0.86 × installs — too high for a cohort retention rate — so **do not present `{d1_retained}/{installs}` as D1 retention without checking its population.** |
| Normal | d7_retained | `d7_retained` | Same family at D7; about 0.40 × installs in mid-Sep 2026, same caveat. |
| Normal | d1_recovery | `d1_recovery` | Sum of 0.67 × IAP rev + banner + interstitial + W2E + offerwall revenue at day 1 after install, per the `ltv_master_cc` join in the source SQL. |
| Normal | d7_recovery | `d7_recovery` | Same revenue definition at day 7 after install. |
| Normal | budget | `budget` | Campaign-day budget from the network feed. **Repeats on every country and creative row of the campaign: never SUM — take MAX per campaign-day.** |
| Normal | bid | `bid` | Campaign-day bid or target from the network feed. **Never SUM.** Unit depends on the feed (the adwords branch multiplies target ROAS by 100); applovin and unity units not confirmed. |

## Dimensions

| Dimension | Description |
|---|---|
| `__time` | Row date (`date_field` in the source SQL). Filter with a half-open range and aggregate to day first. |
| `gid` | Game id, **VARCHAR — quote literals.** |
| `cli` | Platform, VARCHAR. Seen: `0` and `1` on every network; `2` and `-1` only on facebook (since 2026-01-01); NULL on 11 facebook rows, 2025-08-25 to 2025-09-04. |
| `network_name` | Lowercased. Seen: applovin, facebook, google, ironsource (last row 2025-12-31), tiktok (first row 2026-01-01), unity. **Google is stored as `'google'`, not `'adwords'`.** |
| `country` | Lowercased 2-letter code. |
| `campaign_name` | Campaign name truncated at `' ('` for most networks. Google joins on the full trimmed name in the source SQL. |
| `creative_type` | Raw network value, differs by network (applovin: Playable/IEC/Video; facebook: others/Static/Video/Short Video/Carousel; google: TEXT/YOUTUBE_VIDEO/IMAGE/MEDIA_BUNDLE/untagged; unity: video/video+playable/playable/untagged; tiktok: Video/others). |
| `creative_type_label` | CASE relabel of `creative_type`: video and YOUTUBE_VIDEO → Video, IEC → Video + IEC, MEDIA_BUNDLE → Playable, IMAGE → Static, else unchanged. **Unity `playable` / `video+playable` stay lowercase while applovin `Playable` is capitalised — filter case-sensitively per network.** |
| `campaign_type` | From `dm_growth.campaign_tagging`. Seen: roas, event, install, creative, untagged, unknown, NULL. **NULL for 100% of google rows.** |
| `network_parameter` | Optimisation-target label from `campaign_tagging` (e.g. D28 BLD ROAS, D28 AD ROAS, D28_combo_roas, AAA, CBO, Engagement Event). **NULL for 100% of google rows.** |

## Datasource relationship — what ties to what

**`chart_2454` does not tie to `chart_1706`** (about 71% of spend, Sep 1–28 2026). Headline eCPI, spend and
installs come from `chart_1706` (`references/core-and-cohort.md`); `chart_2454` only **explains the move**.
Never put a `chart_2454` CPI beside a `chart_1706` eCPI as if they were the same metric, and never reconcile
one to the other by scaling — state that they are different feeds.

## CPI decomposition — procedure

**Identity:** `CPI = CPM / IPM`, and `IPM = 1000 × CTR × Click-to-Install`.

**Attribute a CPI move by log change (per network, period 1 vs period 0):**

```
ln(CPI1/CPI0) = ln(CPM1/CPM0) − ln(CTR1/CTR0) − ln(C2I1/C2I0)
```

The three terms sum exactly to the CPI move. **Say which term carries the move** (largest absolute term),
with its share of the total log change. A CPM rise is a price-of-reach move; a CTR or Click-to-Install fall
is an efficiency move (creative / store-step quality).

1. **Resolve** `chart_2454-vN` from `chart_config`; pull `SUM(spend, impressions, clicks, installs)` per
   `network_name` (× `cli`, × `creative_type_label` when drilling) per period — one statement, day-grained.
2. **Compute per network** CPM, IPM, CTR, C2I, CPI from the summed raws; run the log attribution.
3. **Portfolio-level CPI/CPM moves are partly network mix.** Split **mix from rate** first — hold each
   network's period-0 spend share fixed, recompute, and report the share of the move that is mix versus
   within-network rate — before blaming any single term (Verdict rule 3).
4. **Drill** the carrying term: `creative_type_label` → `campaign_type` / `network_parameter` → `country`.
5. **Present** a per-network table (CPI, CPM, IPM, CTR, C2I with deltas in-cell) and a waterfall of the
   log terms; label every figure "UA delivery (`chart_2454`)" and keep the `chart_1706` eCPI as the headline.

## Verdict rules

1. **Judge CPM, CTR, IPM, Click-to-Install and CPI against the SAME network's own history, same `cli`:**
   trailing 28 days vs the prior 28 days, plus that network's trailing 90-day range. Calendar-anchored and
   complete through D-2 **per network** (each network's own freshness, SR-6). This trailing-window basis is
   explicit for this chart and overrides the generic month-anchored default (SR-5) for these ratios.
2. **AppLovin and Unity CTR (~47–85%) is not an intent signal** — their ad formats have no close button. A
   CTR rise there with falling Click-to-Install means **lower-quality clicks, not a better creative.**
   Facebook, Google and TikTok CTR is a genuine intent signal.
3. **Portfolio CPI/CPM moves are partly network mix.** Split mix from rate before blaming a single term.
4. **`chart_2454` does not tie to `chart_1706`.** Headline eCPI comes from `chart_1706`; `chart_2454` only
   explains the move.

## Glossary

| Term | Meaning |
|---|---|
| IPM | Installs per mille: installs per 1,000 impressions. |
| IEC | Creative type labelled "Video + IEC"; expansion not stated in the source SQL. |
