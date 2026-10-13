---
name: "early-journey-review"
description: "Thorough D0–D7 early-journey review for any PS game, ONE report per platform (cli): Health Check → Analyst Deep Dives (route + hypotheses + findings) → Opportunities (with impact calculations) → Prioritization. STRICT per-platform, never blends. Every section is a permanent fully-computed item with charts + findings; the ONLY exclusion is a BLOCKED note (schema-unclear / metric-not-found / query-failed). Maturity metrics on a labeled matured cohort, never deferred. A machine verifier gates delivery: the report is not presented until it passes. The Exploratory Antipattern Analyst seeds candidates from cohort×tenure hunts, cross-reference-game divergence (default reference = PS games >2000 US installs/day, user-overridable), and Android-vs-iOS divergence. Live Databricks. USE to review, health-check, benchmark, or explain a move in early retention, first-week funnel, D1/D7 return, engagement, ad monetization or notifications (Pic Merge, Jigsaw, Word Bingo). Distinct from game-change-attribution."
---

---
name: "early-journey-review"
description: "Thorough D0–D7 early-journey review for any PS game, ONE report per platform (cli): Health Check → Analyst Deep Dives (route + hypotheses + findings) → Opportunities (with impact calculations) → Prioritization. STRICT per-platform, never blends. Every section is a permanent fully-computed item with charts + findings; the ONLY exclusion is a BLOCKED note (schema-unclear / metric-not-found / query-failed). Maturity metrics on a labeled matured cohort, never deferred. A machine verifier gates delivery. Antipattern analyst seeds from cohort×tenure, cross-reference-game divergence (ref = PS games >2000 US installs/day, overridable), and Android-vs-iOS divergence. Live Databricks."
---

# Early Journey Review (D0–D7)

**Pipeline v1.10** — v1.10 upgrades the **Exploratory Antipattern Analyst** with two structured seed generators in addition to the existing cohort×tenure hunt: **(1) cross-reference-game divergence** — the target game's metric pattern vs a reference game set (default = other PS games with **>2000 US installs/day**; a user-supplied reference list at run time overrides the default); **(2) Android-vs-iOS divergence** — the target game's same-metric pattern differences across platforms. Material divergences from (1) and (2) become antipattern candidates fed into the ledger-checked hunt. v1.9 added the MANDATORY PRE-DELIVERY VERIFICATION GATE (verifier below; report not presented until OVERALL PASS). v1.8 NON-NEGOTIABLE REPORT CONTRACT (every §1 component, every §2 analyst route+hypotheses+findings, every §3 opportunity supporting-data+impact-calculation are permanent charted items; no blanks; only exclusion = a rendered BLOCKED note; maturity computed on a labeled matured cohort). v1.7 rollup-first cross-game benchmark + peer availability map. v1.6 one report per platform. v1.5 cross-game benchmark; v1.4 antipattern ledger + 30-day cooldown; v1.3 Notifications + per-analyst sections; v1.2 strict per-`cli` + step-rendering; v1.1 self-serve querying, preflight, TTL cache.

Complete early-lifecycle review for any PS game → prioritized opportunities, as ONE self-contained HTML report per platform. Scope strictly **D0 → D7**. Live Databricks (`hive_metastore`) only. Built on the Picmerge Attribution Methodology (game-change-attribution) ontology.

## NON-NEGOTIABLE REPORT CONTRACT (v1.8) — read first, applies everywhere
The report is INCOMPLETE (fails the gate) if any is missing, blank, or summarized away.

**A · Health Check exhaustive with findings.** Every §1 component (1–8): (i) one-line **highlight**, (ii) **full supporting data — every cut uncovered** (by day, decile, network/source, format, assess vs reference), (iii) **≥1 chart**, (iv) explicit **FINDINGS line**. Thoroughness so nothing is missed; findings in-report for debuggability.

**B · Every analyst presents its own research.** Each §2 analyst renders (i) the **ANALYSIS ROUTE** (path chosen by metric type — see Route Map), (ii) every **HYPOTHESIS TESTED** with a verdict `SUPPORTED/REJECTED/NOT-TESTED` + data + **a chart on the lead hypothesis**, (iii) **FINDINGS** (`bucket · confidence · causal-flag · so-what`). Mandatory even when STABLE. A BLOCKED analyst (metric-not-found) is exempt from hypotheses/chart — it still renders route + BLOCKED note + findings.

**C · Opportunities show the math.** Each §3 opportunity: statement; hypotheses (highlight+data); **SUPPORTING DATA behind the impact estimate**; **EXPLICIT IMPACT CALCULATION** (base → delta → reach → selection discount → ad-only compounding → low/mid/high); confidence; causation flag; decisive next step. Never a bare number.

**D · No blanks. One exclusion path only.** The ONLY exclusion is a **rendered `BLOCKED` note** stating one reason — **schema-unclear**, **metric-not-found**, or **query-failed** — + what was attempted (query + table/column) + the data-eng ask. Never a silent skip. **"Maturity", "deferred", "out of scope", "N/A", "pending", "UNAVAILABLE" are NOT valid skip reasons.**

**E · Maturity-aware computation (never defer).** Any metric needing N-day maturity (D2–D7 ladder, per-cohort D7, D0-decile ladder, difficulty curve, first-in-life excess churn) is computed on the most recent **fully-matured cohort** (shift the install window back so every member has ≥N days), with the **matured cohort window explicitly labeled**, vs the equal matured reference. Never blank, never a biased partial, never pushed to another run.

## MANDATORY PRE-DELIVERY VERIFICATION GATE (v1.9) — run before presenting, every time
After building each per-platform report HTML, and BEFORE present_files, **write the verifier below to the working dir and run it**: `python3 verify_early_journey_report.py <report.html> ...`. **Do not present until OVERALL is PASS.** Any FAIL → fix (add the missing chart/route/hypothesis/findings/calc) or convert to a rendered BLOCKED note, then re-run. Report the gate result to the user. Reports must use `<h2>Section 1..4</h2>` headers and CSS classes `block / lab / route / hyp / v / find / calc / blocked` with real `<canvas>`+`getElementById('id')` charts — the structure the gate keys on.

**Machine-checked clauses:** A.1 §1 ≥8 components · A.2 each §1 chart-or-BLOCKED + Findings · B.1 §2 ≥8 analysts · B.2 each Route · B.3 each (non-BLOCKED) ≥1 hypothesis+verdict · B.4 each chart or BLOCKED · B.5 each Findings · C.1 §3 opportunities · C.2 each impact CALCULATION · G.1/G.2 canvas↔chart-code parity · D.1 no silent-skip tokens outside a BLOCKED note · H.1 matured-cohort labelled.

```python
#!/usr/bin/env python3
# Early Journey Review report-contract verifier. Usage: python3 verify_early_journey_report.py r1.html [r2.html ...]
import re, sys
BANNED=["maturity-limited","not available","deferred","out of scope","pending","unavailable","todo","n/a (this run)"]
def strip(s): return re.sub(r"<[^>]+>"," ",s)
def secs(doc):
    h=[(m.start(),int(m.group(1))) for m in re.finditer(r"<h2[^>]*>\s*Section\s+(\d)",doc)]
    return {n:(p, h[i+1][0] if i+1<len(h) else len(doc)) for i,(p,n) in enumerate(h)}
def blocks(chunk):
    idx=[m.start() for m in re.finditer(r'<div class="block"',chunk)]
    return [chunk[s:(idx[i+1] if i+1<len(idx) else len(chunk))] for i,s in enumerate(idx)]
def chart_or_blocked(b): return ("<canvas" in b) or ("BLOCKED" in b)
def findings(b): return ('class="find"' in b) or bool(re.search(r"Findings\s*:",strip(b)))
def check(doc):
    r=[]; S=secs(doc)
    if 1 in S:
        b=blocks(doc[S[1][0]:S[1][1]]); bad=[i+1 for i,x in enumerate(b) if not(chart_or_blocked(x) and findings(x))]
        r+=[("A.1 §1 >=8 components",len(b)>=8,f"{len(b)}"),("A.2 §1 each chart-or-BLOCKED+Findings",not bad,bad or "ok")]
    else: r.append(("A §1 present",False,"missing"))
    if 2 in S:
        b=blocks(doc[S[2][0]:S[2][1]]); rm,hm,cm,fm=[],[],[],[]
        for i,x in enumerate(b):
            bl="BLOCKED" in x
            if 'class="route"' not in x: rm.append(i+1)
            if not bl and not('class="hyp' in x and re.search(r'class="v ',x)): hm.append(i+1)
            if not chart_or_blocked(x): cm.append(i+1)
            if not findings(x): fm.append(i+1)
        r+=[("B.1 §2 >=8 analysts",len(b)>=8,f"{len(b)}"),("B.2 each Route",not rm,rm or "ok"),
            ("B.3 each hypothesis+verdict",not hm,hm or "ok"),("B.4 each chart|BLOCKED",not cm,cm or "ok"),
            ("B.5 each Findings",not fm,fm or "ok")]
    else: r.append(("B §2 present",False,"missing"))
    if 3 in S:
        b=[x for x in blocks(doc[S[3][0]:S[3][1]]) if 'class="mh"' in x]; nc=[i+1 for i,x in enumerate(b) if 'class="calc"' not in x]
        r+=[("C.1 §3 opportunities",len(b)>=1,f"{len(b)}"),("C.2 each impact CALCULATION",not nc,nc or "ok")]
    else: r.append(("C §3 present",False,"missing"))
    cv=set(re.findall(r'<canvas id="([^"]+)"',doc)); ch=set(re.findall(r"getElementById\('([^']+)'\)",doc))
    r+=[("G.1 no orphan canvas",not(cv-ch),sorted(cv-ch) or "ok"),("G.2 no dead chart code",not(ch-cv),sorted(ch-cv) or "ok")]
    low=doc.lower(); NEG=("no ","not ","never","nothing","without","n't","zero "); hits=[]
    for t in BANNED:
        for m in re.finditer(re.escape(t),low):
            w=low[max(0,m.start()-220):m.start()+40]; pre=low[max(0,m.start()-30):m.start()]
            if "blocked" in w or any(n in pre for n in NEG): continue
            hits.append(t)
    r.append(("D.1 no stray skip tokens",not hits,sorted(set(hits)) or "clean"))
    mv=bool(re.search(r"matured cohort|ladder|decile|difficulty",low)); lab=bool(re.search(r"matured .*cohort|matured install cohort|cohort:.*\d{2}-\d{2}",low))
    r.append(("H.1 matured-cohort labelled",(not mv) or lab,"ok" if lab else "no label"))
    return r
def main(a):
    if len(a)<2: print(__doc__); return 2
    bad=0
    for f in a[1:]:
        try: doc=open(f,encoding="utf-8").read()
        except Exception as e: print(f"{f}: CANNOT READ {e}"); bad=1; continue
        res=check(doc); fails=[x for x in res if not x[1]]; print(f"\n### {f} -> {'PASS' if not fails else 'FAIL '+str(len(fails))}")
        for c,ok,d in res: print(f"  [{'PASS' if ok else 'FAIL'}] {c}  {d}")
        bad=bad or bool(fails)
    print(f"\n==== OVERALL: {'PASS — deliverable' if not bad else 'FAIL — do not deliver until fixed'} ====")
    return 1 if bad else 0
if __name__=="__main__": sys.exit(main(sys.argv))
```

## Cross-cutting rules
- **STRICT CLI CUTS.** Every metric per `cli` (0 Android,1 iOS,2 Amazon; ≥5% installs). Never blend platforms. One report per platform. Un-splittable → `BLOCKED — metric-not-found (this cli)`.
- **STEP-RENDERING DISCIPLINE.** Every step = highlight + supporting data + table/chart. Report mirrors §1→§2→§3→§4.
- **EVERY ANALYST A §2 SECTION** — Funnel, Retention, Engagement, Monetization, Lifecycle/Content, UA/Mix, Notifications, Exploratory Antipattern — always, incl. STABLE. Each renders route → hypotheses (verdict+data+chart-on-lead) → findings.
- **Freshness** as-of stamp; fresh or a `BLOCKED` note; stable metrics from TTL cache with staleness stamp.
- **Attribution ontology** GAME/CAMPAIGN/EXTERNAL/AD-OPS/NOISE; **Causation** correlational/causal-on-current-data/needs-experiment.
- **Query hygiene** query-only; true-unique `count(distinct rid)`; `clear` de-dupe on level; read within source/build/network before blending inside a cli; pool < floor; `cc` ordering.
- **Windows** assessment vs same-length prior; label both; D7 ≥7-day-matured (§E); ~2-day trim.

## L0 CONFIG (only per-game layer)
```yaml
game: {name, gid, schema, franchise_peer_gids}
shared_spine: {dau: derived_tables.dau_splits, ads: dm_admon.rev_dau_install_diff_ilrd_v2, iap: server_tables.dollar_purchase_master_cc, campaign: dm_adjust.adjust_all_data, xgame_ecpm: chart_2077-vN (Druid — resolve vN from play_data.chart_config; __time date col, lowercase country), benchmark_rollup: <ps.early_journey_benchmark_rollup>, raw_slice: sub_tables.tracking_slice_<schema>, engagement: <schema>.<engagement_table>}   # all under hive_metastore except xgame_ecpm (Druid chart datasource)
event_map:
  app_open:{k:dialog,o:loading} puzzle_view:{k:puzzle,o:view}
  level_clear:{k:puzzle,o:clear, level:"split(p,'_')[0]", clear_time:"split(f,'_')[0]", moves:"split(f,'_')[1]"}
  ftue:{k:dialog,o:piece_move_ftue} ftue_hint:{k:dialog,o:hint_ftue} ftue_undo:{k:dialog,o:undo_ftue}
  economy_coins:{k:cash,o:coins, level:"f"}
  ad_banner:{k:game_ad_tracking,o:banner} ad_interstitial:{k:game_ad_tracking,o:interstitial, level:"g"} ad_rewarded:{k:growth_ilrd_max,g:w2e} ecpm_ilrd:{k:growth_ilrd_max, value:"s", format:"g"}
  notif_permission_android:{k:dialog,o:notif_permission, action:"f"}  notif_send_android:{k:local,p:sent}  notif_click_android:{k:local,p:click}
  notif_ios:{k:runtime,o:notif,c:visible}   # iOS heartbeat only; funnel = BLOCKED(metric-not-found)
  feature_unlocks:{daily_quest:{k:dialog,o:dq_ftue}, daily_puzzle:{k:dialog,o:daily_puzzle}, collections:{k:dialog,o:collections}}
  EXCLUDE:{ad_health:{k:ad_tracking_max,p:health}}
ordering_key: cc
split_by: cli
platforms: {0:Android,1:iOS,2:Amazon}
reference_games:                       # v1.10 — antipattern cross-game seed
  mode: auto                           # 'auto' = resolve default; a user list at run time overrides -> mode:override
  default_rule: "PS gids with US installs/day > 2000 over the assessment window"
  resolver_sql: |
    SELECT gid FROM hive_metastore.dm_adjust.adjust_all_data
    WHERE metric='installs' AND country='us'           -- NOTE country codes are lowercase
      AND date_field BETWEEN :win_start AND :win_end
    GROUP BY gid HAVING sum(value)/:win_days > 2000
  override: <user-supplied list of gids at run time; when present, replaces the default set>
  as_of_2026-08_default: [26,22,9,43,39,8,11,42,37,17]   # cached example resolution (~last 7d)
benchmark_cohort: reference_games (above) for pattern divergence; chart_2077 for eCPM percentile; franchise_peer_gids for notif
benchmark_pass_percentile: 90
benchmark_rollup_ttl_days: 1
knobs: {monetization_model, liveops_density, acquisition_model}
windows: {assessment:{len_days:7}, reference: same_length_prior, maturity_trim_days:2}
gates: {install_source_min_share:0.05, noise_band_sigma:2, volume_floor:{installs:100,dau:200}}
divergence_gates:                      # v1.10 — what makes a seed 'material'
  vs_reference: "target metric outside [p10,p90] of the reference-game set, OR robust |z|>2 (median/MAD), AND target volume>=floor"
  vs_platform:  "|Android - iOS| relative gap >= 20% (or > 2sigma of the metric's historical A-iOS gap), AND both cli installs>=100"
run_controls: {analyst_query_budget:5, cache_ttl_days:{stable_metrics:7, deviation_metrics:0}, antipattern_cooldown_days:30}
protected_metrics: [ad_rev_per_dau_d0, notif_opt_in_rate, d7_retention, total_dau]
```
**Pic Merge (48, `picmerge`):** peers [8 Crossword, 9 Word Trip, 20 Word Bingo, 24 Jigsaw, 26 Tile]; ad_only; cli 0 & 1 material; activation 5 D0 clears; clear `f`=`seconds_moves`; interstitial=`game_ad_tracking o='interstitial'`, rewarded=`growth_ilrd_max g='w2e'`; ad_tracking_max*=health→exclude. Notif: Android full funnel; iOS = BLOCKED(metric-not-found). Cross-game (Android): eCPM ~$1.80 rank ~6–7/35 p82–85. **Word Bingo (20, `wordbingo`):** PvP turn-based (funnel/engagement via `game/start`,`game/end`); no level construct → difficulty BLOCKED(schema-unclear); notif not instrumented → BLOCKED(metric-not-found); iap_plus_ad. **Neither Pic Merge (48) nor Word Bingo (20) is in the default reference set** (both < 2000 US installs/day), so both are measured against it.

**Preflight (per cli, per peer/reference):** probe every registry metric × cli source (`count(*)>0`); empty/unclear/error → record reason for a `BLOCKED` note, never a blank. Resolve the **reference_games** set (override list if provided, else run `resolver_sql`) and record it in the header. For the benchmark, emit a **peer availability map** (not-instrumented = N/A). Fix, per maturity metric, the **matured cohort window** (§E).

## SECTION 1 — HEALTH CHECK (one per cli; contract A per component)
1 **Early funnel** · 2 **Retention** (D1 clean; D2–D7 ladder on matured cohort §E; conditional D1 by D0 state; by network; DAU new/returning/reactivated) · 3 **Engagement** (clears/games by recency; D1–D7 by D0-decile on matured cohort §E; sessions) · 4 **Monetization** (Rev/DAU = eCPM × imps/DAU; eCPM vs peers = EXTERNAL gate; fill = AD-OPS; first-eCPM decile; IAP if iap_plus_ad) · 5 **Lifecycle & content** (first-in-life excess churn vs level baseline; difficulty curve — matured §E; BLOCKED if no level construct) · 6 **Acquisition mix** (source share ≥5%; mix-vs-rate) · 7 **Notifications** (permission funnel; Send % = distinct sent ÷ cohort by cohort-day; CTR by day — Android; iOS BLOCKED) · **8 Cross-game benchmark** (rollup-first percentile vs the reference set; below top decile → seed §2 Antipattern).

Deviation gate within cli: material = `|assess−ref| > noise_band_sigma·σ` AND volume ≥ floor.

## QUERY PACK (always `AND cli=:cli`)
funnel-by-build; conditional-return by cohort×source; ladder by network (matured); DAU new/returning/reactivated; engagement by recency×source; clears/games by decile×day (matured); first-eCPM decile; Rev/DAU+eCPM+fill by format (+IAP); first-event excess vs level baseline (matured); clear-time by level (matured); source shift-share; notif opt-in/surfacing + Send%/CTR by cli×day; cross-game eCPM by gid (chart_2077); **reference-set resolver (`reference_games.resolver_sql`); per-metric reference-set distribution (target vs ref p10/p50/p90 + robust z); Android-vs-iOS same-metric divergence table**; rollup-writer. Empty/unclear/error → `BLOCKED` note.

## SECTION 2 — ANALYST DEEP DIVE (per cli; one section per analyst; contract B)
Each analyst renders **ROUTE → HYPOTHESES (verdict+data+chart-on-lead) → FINDINGS**.

**Analysis Route Map (route chosen by metric type):**
- **Funnel/Activation** → step-decompose → depth-among-clearers vs marginal-user → mix check. flat depth + falling activation ⇒ CAMPAIGN; depth falls across sources ⇒ GAME.
- **Retention** → ladder by network → common-vs-one-source → conditional-by-D0-state. common=GAME; one-source-scaling=CAMPAIGN.
- **Engagement** → intensity vs frequency → decile depth (matured) → survivorship check.
- **Monetization** → Rev/DAU = eCPM × imps/DAU → eCPM vs peers (EXTERNAL) → fill (AD-OPS) → residual impressions (GAME).
- **Lifecycle/Content** → index first-events to level → excess churn = instant − level-baseline hazard → content-vs-event triage.
- **UA/Mix** → shift-share → mix-vs-rate → dominant-source distribution.
- **Notifications** → permission funnel → Send% → CTR by cohort-day → peer compare. Gaps = BLOCKED(metric-not-found).
- **Exploratory Antipattern** → runs the three-seed generator below, ledger-checked.

**Exploratory Antipattern Analyst (v1.10) — three seed generators → one ledger-checked hunt.**
Every run first assembles antipattern CANDIDATES from three sources, then de-dupes and runs the hunt:
- **Seed S1 · Cohort × tenure hunt** — find cohorts (by D0-engagement decile × tenure) behaving against expectation (e.g. per-active depth decay, decile inversions).
- **Seed S2 · Cross-reference-game divergence** — for each §1 metric (retention D1/D7, funnel/activation, engagement depth, Rev/DAU, eCPM, notif opt-in/CTR, mix quality), compare the target game's value/pattern to the **reference-game set** (default = PS games >2000 US installs/day via `reference_games.resolver_sql`; a user-supplied reference list at run time overrides the default). A metric where the target is a **material outlier** per `divergence_gates.vs_reference` (outside ref p10–p90, or robust |z|>2, with volume≥floor) becomes a candidate. This generalizes the §1.8 eCPM/notif benchmark to ALL metrics under a single reference definition.
- **Seed S3 · Android-vs-iOS divergence** — for each metric, compare the target game's **Android vs iOS** value/pattern; a gap beyond `divergence_gates.vs_platform` becomes a candidate. (Reports stay strict per-cli; this cross-platform contrast is an explicit candidate-generation step, computed per cli then diffed — record which platform is the outlier.)

Then: **check `Antipattern_Ledger.csv` and skip any candidate whose next_eligible_date (=date_logged+30d) is in the future**; pick the highest-signal remaining candidate; **decompose → branch ~3 hypotheses → check each on current data → narrow cause → directional impact → append to ledger** (+30d cooldown). Record, in the analyst section, which seed(s) surfaced the chosen antipattern and the divergence evidence (target vs reference distribution, or Android vs iOS). Feeds §3.

`Finding = {cli, analyst, route, seed_source, hypotheses[{statement, verdict, supporting_data, chart?}], attribution_bucket, confidence, correlation_or_causal, so_what, data_request}`. Lead-Analyst reconciliation per cli → ranked root-cause map. Recurring data-requests promote into §1.

## SECTION 3 — OPPORTUNITIES (per cli; contract C)
PM × Game-Design over the root-cause map; current-data validation only. Each opportunity: statement; hypotheses (highlight+data); **supporting data behind the impact estimate**; **explicit impact calculation** (base → delta → reach → selection discount → ad-only compounding → low/mid/high); confidence; causation flag; decisive next step. `Opportunity = {cli, statement, hypotheses[...], data_requests[], validation_result, impact_estimate{inputs{base,delta,reach,selection_discount,compounding}, scenarios{low,mid,high}, calc_shown:true}, confidence, causation_flag, decisive_next_step}`.

## SECTION 4 — PRIORITIZATION (per cli)
`Priority=(Impact×Confidence×Reach)/Effort` (1–5); row = highlight + scoring table. Guardrail veto: never damage a protected_metric; rollout-risky levers A/B-gate against D7 & DAU.

## OUTPUT — ONE consolidated report per platform
Single self-contained HTML per cli (`EarlyJourney_<Game>_<PLATFORM>_<window>.html`) with `<h2>Section 1..4</h2>` + classes `block/lab/route/hyp/v/find/calc/blocked` + real `<canvas>`+`getElementById` charts. §1 (components 1–8, each with findings) → §2 (one section per analyst with route+hypotheses+chart-on-lead+findings, incl. Antipattern with its seed_source) → §3 (each opportunity with supporting data + impact calculation) → §4. No separate benchmark/antipattern files. Never merge platforms. Header: game, GID, cli, config, windows + labeled matured-cohort range(s), **resolved reference-game set (+ note if user-overridden)**, availability map (+ BLOCKED items), version. Footer: version + "run independently per platform; not merged" + "numbers from live queries, not memory". End with a short per-platform summary.

## Verification (per cli) — the GATE is mandatory
Sum-check cohort splits; re-run a key delta on an adjacent window. Then **run `verify_early_journey_report.py` and require OVERALL PASS before present_files.** Any FAIL → fix or convert to a rendered BLOCKED note, re-run. Also: cross-game a §1 component with no "pending"; Lifecycle + decile + D2–D7 ladder on labeled matured cohorts; no blended numbers; antipattern hunt fresh & ledger-checked & appended, with its seed_source (S1/S2/S3) and divergence evidence recorded.

## Guardrails (attribution v1.13 + report contract v1.8 + gate v1.9 + antipattern seeds v1.10)
Query-only; true-unique rid; clear de-duped; strict per-cli never blended; five-bucket attribution; confidence+causation on every claim; no unmeasured labels; pool thin cells; `cc` ordering; SDK ad-health excluded; no silently-stale numbers; every step highlight+data+table/chart; **every §1 component computed with findings; every analyst renders route+hypotheses+a rendered chart+findings; every opportunity shows supporting data + impact calculation; NO blank/"not available" sections — only a rendered BLOCKED note (schema-unclear/metric-not-found/query-failed); maturity metrics on a labeled matured cohort; the report is NOT delivered until the verifier returns OVERALL PASS**; the Antipattern Analyst seeds from cohort×tenure + cross-reference-game divergence (ref = PS games >2000 US installs/day, user-overridable) + Android-vs-iOS divergence, then runs a fresh ledger-checked hunt; one report per platform; benchmark rollup-first with a peer availability map.

