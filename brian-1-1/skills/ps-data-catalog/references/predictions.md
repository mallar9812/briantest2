# Predictions — Growth_widget (chart_3730) & DS_DAU_model (chart_1071)

⚠️ **Every value on these datasources is a model prediction — including `installs` and `spend`. There are
no actuals here.** Never present one as observed. Always show the actual observed ROAS beside — and
before — any predicted figure.

⚠️ **`chart_3730` carries TWO independent D365 models: weekly and monthly.** An unsuffixed metric name
(`ltv/ecpi_d7`) is always the **weekly** model; the monthly model is reached only via the explicit
`_month` suffix. Name which model a reported figure came from. *(Verified live Sept 2026 against
`chart_3730` and the chart's own custom-metric definitions — this supersedes every earlier doc that
described a single `d365_recovery_dX` family.)*

> **Engine & versions:** Druid — resolve names per `references/query-engines.md`.

## Live shape of `chart_3730`

**Source lineage:** `UNION ALL` of `dm_growth.d365_pred_lg` / `_ng` / `_loc` for a single `install_date`,
aggregated to the dimension grain, `LEFT JOIN dm_growth.franchise_tagging` for `franchise`, and
`FULL OUTER JOIN dm_growth.budget_roas_goals` for the (unused) targets. `pod` doubles as the source-table
tag: `Localization` → `_loc` (the bulk of rows), `New Games` → `_ng`, `Android`/`iOS` → `_lg`.

**Grain:** one row per `install_date` × `gid` × `cli` × `pod` × `network_name2` × `network_type` ×
`country` × `accuracy` × `campaign_type` × `network_parameter`. Install-date (cohort) grain, never
activity date.

| Datasource | `independent_columns` (ABSENT there) | Use |
|---|---|---|
| `chart_3730-vN-target_bucket` | `target_bucket` | **The only variant to query.** Carries every prediction metric and every other chart dimension, including `franchise`. |
| `chart_3730-vN-accuracy-campaign_type-cli-country-geo_bucket-network_name-network_name2-network_parameter-network_type-pod` | all of those | Targets only (`spend_target`, `recovery_target`) — **out of scope, do not query** (see "Targets" below). |
| `chart_3730-vN` | — | Exists in Druid but has **no `chart_config` row**, so no `metrics` array governs it. Never use it for reported figures. |

## Rollups & mandatory pins

**Two mandatory pins — both are large-multiple errors if missed, not rollup rows:**
- **`model_type` on `chart_1071-vN` — always pin `'DS_DAU_model'`.** Five model families share the column;
  summing across them multiplies every figure by five.
- **`accuracy` — the value set DIFFERS BY CHART. Pin per chart; never copy one chart's pin to the other.**

| Datasource | `accuracy` values | Pin |
|---|---|---|
| `chart_3730-vN-target_bucket` | `'pred'` · `'no_pred'` · `'monthly_only'` · `'weekly_only'` · `NULL` | **keep `'pred'` only.** `'more accurate'` does not exist here and returns zero rows. |
| `chart_1071-vN` | `'more accurate'` · `'no_pred'` | pin `'more accurate'` (which also drops `'no_pred'`) |

**`'monthly_only'` / `'weekly_only'` are not scored rows.** They mean only *one* of the two models
produced a projection; on the un-scored side the `d365` column silently falls back to the raw
`dX_recovery` (actual-to-date), so including them blends a projection with a non-projection in the same
sum. Excluding them is not optional. **`NULL` marks the FULL-OUTER-JOIN target-only rows**, where `cli`, `pod`,
`network_type` and **every metric** are NULL — they inflate `COUNT(*)`, distort `AVG()` and overstate
`COUNT(DISTINCT gid)`.

Dropped-row coverage is always disclosed. No `'overall'` rollup and no `id_type` on either prediction
chart. `country`, `geo_bucket`, `network_name`, `campaign_type` and `franchise` sum normally once the
pins above are applied — but see `network_name2` and `geo_bucket` under Dimensions before grouping.

## Table routing and hard filter rules

| Metric(s) | Datasource | Hard filter rules |
|---|---|---|
| **PRIMARY prediction source** — `installs`, `spend`, `d0/d1/d7/d30_recovery`, `weekly_` and `monthly_d365_recovery_d0/_d1/_d7/_d30`, `d1/d7/d30_retained_users`, `d1/d7/d30_payers`, and every derived ROAS / LTV / CPI / retention / payer% | `chart_3730-vN-target_bucket` | **The entire datasource is model prediction.** `target_bucket` does not exist on this variant; every other chart dimension does — `gid`, `cli`, `pod`, `country`, `geo_bucket`, `network_name`, `network_name2`, `network_type`, `campaign_type`, `network_parameter`, `franchise`, `accuracy`. **Pin `accuracy = 'pred'`**, excluding `'no_pred'`, `'monthly_only'`, `'weekly_only'` and `NULL` from every side of every ratio. |
| **FALLBACK ONLY** — predicted recovery/LTV/ROAS at horizon `diff` | `chart_1071-vN` | Use **only** when `chart_3730` has no rows for the game/segment. Use `"diff" = '360'` to match the D365 basis. **Always pin `model_type = 'DS_DAU_model'`** and **`accuracy = 'more accurate'`**, excluding `no_pred`, from every side of every ratio. State install coverage. **Name this source in the output.** |

**Retired — do not query.** `play_data.Growth_widget` and `Actual_vs_Pred_dataset` are superseded by the
two datasources above. `chart_1701` does not exist in `chart_config` — if a doc or memory says otherwise,
it's wrong; the DS model is `chart_1071`.

## Targets — out of scope, ignore

**`spend_target` and `recovery_target` are not reportable metrics and are not documented as such.**
`play_data.Growth_widget_target` is retired with no replacement. The two target columns do survive on the
targets variant above, but they repeat across every `install_date` at (`gid`, `target_bucket`) grain, so any
multi-day sum double-counts them — and the underlying numbers proved unreliable. The
variant also strips `cli`, `country`, network and `pod`, and its `target_bucket` (`Android` / `iOS` /
`Localization` / `NULL`) mirrors `pod` rather than any prediction-quality flag, and covers far fewer
gids than have predictions.

**When someone asks about targets, do not report a target number.** Show the predicted D365 ROAS from
both models instead — `chart_3730` weekly as the headline, monthly alongside, and `chart_1071`
(DS_DAU_model) if a second opinion is wanted — and say plainly that ROAS targets are no longer sourced
from the catalog. Present them as independent views on the same horizon, not as a target and a gap:
there is no gap to state.

## Coverage pre-check

The **NaN pre-check is obsolete on Druid.** `Growth_widget` in the retired warehouse original returned NaN aggregates that
poisoned whole games, forcing segment isolation and coverage disclosure. `chart_3730-vN-target_bucket`
returns clean values for those games. Don't isolate NaN
segments or disclose NaN-driven coverage from Druid. If a Druid prediction figure *does* come back NaN,
that's a genuine anomaly to investigate and flag — not routine.

Three checks still apply:

**(a) Unscored and half-scored rows — present on BOTH charts, with different value sets.**
- `chart_3730-vN-target_bucket` → the scored value is **`accuracy = 'pred'`**. Everything else is
  excluded. On `'no_pred'` rows the d365 columns are **not zero** — they equal the raw `dX_recovery`
  exactly (actual-to-date carried forward, no projection), so including them *understates* ROAS/LTV
  rather than zeroing it. Excluding all non-`'pred'` rows drops a meaningful block of installs but very
  little spend — almost entirely organic/unspent segments, so the ROAS denominator barely moves while
  the LTV denominator does.  Measure the actual drop per query rather than assuming a fixed share. `'more accurate'` is not a value here — pinning it returns zero rows.
- `chart_1071-vN` → the scored value is **`accuracy = 'more accurate'`**. At `diff = 360`, `no_pred` is a
  large share of rows — often exceeding the scored rows — and this matters most for recently-launched
  titles.

Excluding a single unscored row is still an exclusion: state it (SR-4 / Rule 1) rather than dropping it
silently.

**(b) `model_type` is NOT a constant — pin it or 5x your numbers.** On `chart_1071-vN` at `diff = '360'`, five model families coexist —
`DS_DAU_model`, `DS_DAU_model_low_seasonality`,
`DS_DAU_model_weekly`, `Growth_daily`, `crr_poly`. **Always pin `model_type = 'DS_DAU_model'`** unless
the user explicitly asks to compare models. (Older docs called this column a constant — that is wrong.)

**(c) Always disclose coverage** whenever rows were excluded under (a): the share of installs (or spend)
carrying a valid scored value — "D365 figure rests on 33% install coverage vs 97%+ for the other games."
Low coverage is reduced confidence and a likely model-input gap worth raising with the DS team. If
coverage is effectively zero in both sources, say the prediction isn't available rather than reporting a
number neither model produced.

Any impossible or counter-intuitive result — a ROAS that *drops* over a longer horizon, a NaN, a value
contradicting a known constraint — triggers these checks *before* reporting.

## Metric formulas

### `chart_3730-vN-target_bucket` (primary)

Names and formulas below are the chart's own custom-metric definitions — use these names verbatim in
output rather than inventing synonyms.

**⚠️ Scale is not uniform.** The `ltv/ecpi_*` family and every `X/Y` ratio are **plain ratios**
(1.0 = payback); `D0–D30 Roas`, all Retention and all payer% metrics are **×100 percentages**.
Never put the two on one axis.

**D365 prediction — the headline family (weekly is the default model)**

| Name | Type | Formula | Description |
|---|---|---|---|
| `ltv/ecpi_d0` | Custom | `{weekly_d365_recovery_d0}/{spend}` | Predicted D365 return on spend, weekly model, anchored on day-0 revenue. Ratio, not a percentage. |
| `ltv/ecpi_d1` | Custom | `{weekly_d365_recovery_d1}/{spend}` | Same, day-1 anchor. |
| `ltv/ecpi_d7` | Custom | `{weekly_d365_recovery_d7}/{spend}` | Same, day-7 anchor. **The default reported prediction once d7 is mature.** |
| `ltv/ecpi_d30` | Custom | `{weekly_d365_recovery_d30}/{spend}` | Same, day-30 anchor. Highest-confidence anchor; only on cohorts 30+ days old. |
| `ltv/ecpi_d0_month` / `_d1_month` / `_d7_month` / `_d30_month` | Custom | `{monthly_d365_recovery_dX}/{spend}` | Monthly-model counterparts. The `_month` suffix is the **only** thing distinguishing the two models. |
| `Pred_LTV` | Custom | `{weekly_d365_recovery_d7}/{installs}` | Predicted D365 revenue per install. **Hardcoded to the weekly model at the d7 anchor** — the one official predicted-LTV metric; there is no d0/d1/d30 or monthly variant. |
| `D365_to_D0 multiplier` | Custom | `{weekly_d365_recovery_d0}/{d0_recovery}` | How many times day-0 revenue the model expects back by day 365. Sanity check on the projection itself. |

**Short-horizon ROAS / LTV — actual-to-date within the cohort, not projections**

| Name | Type | Formula | Description |
|---|---|---|---|
| `D0 ROAS` / `D1 Roas` / `D7 Roas` / `D30 Roas` | Custom | `{dX_recovery}*100/{spend}` | Percent of spend recovered through day X. **×100.** |
| `D7/D1 ROAS` | Custom | `{d7_recovery}/{d1_recovery}` | Revenue multiple between day 1 and day 7. |
| `D7/D0 LTV` | Custom | `{d7_recovery}/{d0_recovery}` | Revenue multiple between day 0 and day 7. |
| `D0_LTV` / `D1 LTV` / `D7 LTV` | Custom | `{dX_recovery}/{installs}` | Revenue-to-date per install at day X. **"LTV" here is not projected** — only `Pred_LTV` is. |
| `cpi` | Custom | `{spend}/{installs}` | Cost per install. The chart has no separate eCPI metric. |

**Retention and payers**

| Name | Type | Formula | Description |
|---|---|---|---|
| `D1 Retention` / `D7 Retention` / `D30 Retention` | Custom | `{dX_retained_users}*100/{installs}` | Percent of the cohort active on day X. **×100.** Prefer cohort actuals from `chart_1706` for any reported retention number; use these only for a model-internal view. |
| `D7/D1 Retention` | Custom | `{d7_retained_users}/{d1_retained_users}` | Share of day-1 retained users still active at day 7. |
| `D1 payer%` / `D7 payer%` / `D30 payer%` | Custom | `{dX_payers}*100/{installs}` | Percent of the cohort that has paid by day X. **×100.** |

**There is no predicted-profit metric on this chart.** Profit existed only against the retired targets —
do not compute `d365 − spend` and call it a chart metric; if profit is asked for, say it is derived,
show the inputs, and name the anchor and model used.

**RAW METRICS (inputs to the above formulas)**

| Name | Type | Description |
|---|---|---|
| `spend` | Normal | Predicted UA spend for the cohort-day segment. |
| `installs` | Normal | Predicted installs for the cohort-day segment. |
| `d0_recovery` / `d1_recovery` / `d7_recovery` / `d30_recovery` | Normal | Cumulative revenue (IAP + ads) through day X. |
| `weekly_d365_recovery_d0` / `_d1` / `_d7` / `_d30` | Normal | Weekly model's D365 projection, per anchor. |
| `monthly_d365_recovery_d0` / `_d1` / `_d7` / `_d30` | Normal | Monthly model's D365 projection, per anchor. |
| `d1_retained_users` / `d7_retained_users` / `d30_retained_users` | Normal | Users active on day X post-install. |
| `d1_payers` / `d7_payers` / `d30_payers` | Normal | Paying users by day X. |

### `chart_1071-vN` (fallback only)

Pin `model_type = 'DS_DAU_model'`, `accuracy = 'more accurate'`, `"diff" = '360'`. State install
coverage and name this source in the output.

| Name | Type | Formula | Description |
|---|---|---|---|
| installs | Normal | `installs` | Installs in the scored segment. |
| recovery | Normal | `recovery` | Predicted revenue accrued at the given horizon. |
| recovery_ads | Normal | `recovery_ads` | Predicted revenue from ads only. |
| spend | Normal | `spend` | Spend — a dedicated column here. |
| D360 ROAS | Custom | `recovery / spend` | Predicted ROAS at `diff = '360'`. |
| D360 LTV | Custom | `recovery / installs` | Predicted revenue per install at d360. |
| eCPI | Custom | `spend / installs` | Cost per install. |
| LTDays | Custom | `active_dau_days / installs` | Average active days per install. |
| rev_per_install | Custom | `recovery / active_dau_days` | Predicted revenue per active day. |
| Ilrd_ROAS | Custom | `recovery_ads / spend` | Ad-revenue-only ROAS. |
| LTV_ads | Custom | `recovery_ads / installs` | Ad-revenue LTV. |
| ltv/cpi_incl_rt_spend | Custom | `recovery / spend_incl_rt` | ROAS including retargeting spend. |
| LTV_Error% | Custom | `delta_recovery * 100 / actual_recovery` | Model error on revenue vs actuals. |
| LTDays_Error% | Custom | `delta_active_dau_days * 100 / actual_active_dau_days` | Model error on active days vs actuals. |

Also present, meanings unconfirmed: `recovery_weighted_wmape`, `active_dau_days_weighted_wmape`.
`actual_recovery` and `actual_active_dau_days` are confirmed columns on the datasource.

## Maturity

`dX_recovery` and the `d365_recovery` anchors are only complete once every install in the window has
passed day X. Pick the `ltv/ecpi` anchor from the **highest fully-mature dX (d30 → d7 → d1 → d0)** and
state which one and why — d30 is now available and is the highest-confidence anchor, so stopping at d7
on a mature cohort leaves accuracy on the table. Apply date alignment to every ratio. If not even d0 is
mature, say a reliable D365 projection can't be computed yet — never substitute a short-horizon
prediction and call it D365.

## Dimensions

**`chart_3730-vN-target_bucket`** (verified live, Sept 2026 — value sets are stable, row counts are not,
so re-measure any volume before quoting it):

| Dimension | Values / notes |
|---|---|
| `gid` | Only a subset of portfolio gids carry predictions. `COALESCE(a.gid, d.gid)`, so target-only rows add further gids with no metrics. |
| `cli` | `'0'` Android · `'1'` iOS · `'2'` Amazon · `'-1'` (rare) · `NULL` (target-only rows). |
| `pod` | `Localization` (the bulk of rows) · `Android` · `New Games` · `iOS` · `NULL`. Identifies the source table, not just an owning team. |
| `network_name` | Cleaned network — `applovin%` collapsed to `applovin`, `unity%` to `unity`, `adwords_enww` to `adwords_uac`. **Use this one for network reporting.** |
| `network_name2` | Raw lowercased network before that collapse. Grouping on it splits `applovin` into `applovin` + `applovind28` and `adwords_uac` into `adwords_uac` + `adwords_enww`. **Never use for reported network totals.** |
| `network_type` | organic · platform · video · xpromo · preload · untrusted · dsp · incent · retarget · affiliate · p2e · untagged · **empty string** (a real bucket, not a null) · `NULL`. |
| `country` | Lowercase ISO-2 (`us`, `gb`, `ca`, `mx`…). Sourced from the upstream column literally named `geo_bucket`, renamed to `country`. |
| `geo_bucket` | Language/region rollup derived from `country`: `us` · `non_us_tier1` (gb/ca/au) · `German` · `Spanish` · `Portuguese` · `French` · `Rest of Europe` · `Asian` · `Russian` · `others`. **`others` is a large catch-all bucket, not a total.** |
| `campaign_type` | install · roas · event · preload · untagged · incent · unknown · creative · retargeting · **`NULL` (one of the largest buckets)**. A `NOT NULL` filter silently drops a large share of rows. |
| `network_parameter` | Sub-network / placement parameter. |
| `franchise` | From `franchise_tagging`: `Anagram` · `Crossword` · `Search` · `Tile` · `PvP` · `Central` · `NULL`. **Note `Tile` and `Central`** — this is not the franchise set in `ps-entities`; reconcile before mixing. |
| `accuracy` | `pred` · `no_pred` · `monthly_only` · `weekly_only` · `NULL`. Upstream column is `ratio_coverage`. Pin `'pred'`. |
| `target_bucket` | **Absent** from this variant (it is the variant's `independent_columns`). On the targets variant it is `Android` / `iOS` / `Localization` / `NULL` — a budget slice mirroring `pod`, and out of scope anyway. |

**`chart_1071-vN`** (confirmed live via `INFORMATION_SCHEMA.COLUMNS`): `gid`, `cli`, `country`,
`bucket` (organic, paid, NULL, paid (preloads), xpromo, SAN+Organic), `install_source`,
`diff` — **VARCHAR**, prediction horizon in days (use `'360'`), `dn` (D2, D7),
`model_type` — **5 values, must be pinned** (see above), `accuracy` ('more accurate' / 'no_pred' — pin to
'more accurate'), `reattribution_flag` (installs, reattributions).

A reduced variant `chart_1071-vN-accuracy-dn-model_type` also exists in Druid — it drops exactly the
three dimensions you most need to pin, so **do not use it for reported figures**; check its `metrics`
array in `chart_config` before touching it.
