---
name: "game-d0-engagement-bucket-analysis-framework"
description: "Frozen D0-engagement-bucket analysis for any PlaySimple game: splits a metric move into intake (campaign) versus behaviour (game), adjudicates it against network, build, experiment and seasonality controls, and renders a 17-section two-tier report behind a machine gate. Supersedes cohort-decile-attribution."
---

# Game D0-engagement-bucket analysis framework

**method_version: 2.0.0** — stamp this in every report masthead. Changelog at the end of this file.

**Supersedes `cohort-decile-attribution`.** Same engine, same arithmetic, same gate; what changes is
that the report has a **fixed 17-section contract** instead of an author-chosen section set, and the
skill is renamed for what it actually does. Reports produced under `cohort-decile-attribution`
1.0.0–1.3.0 remain valid and remain comparable on their figures; they are not comparable on
structure. Retire the old skill rather than running both — they share one engine and will drift.

Rank every install by how much it played on install day, cut the population on **frozen** thresholds,
then split any metric move into two components that cannot be argued about: how many installs landed
in each bucket (intake — the campaign side) and how each bucket behaved as it aged at constant
install-day quality (the game side).

**Use this when** someone asks whether a metric move was the game or the campaign, wants a
bucket/decile read on engagement, ads, session time or the coin economy, or wants a standing weekly or
monthly attribution for a title. **Distinct from** `game-change-attribution` (single WoW/MoM move, no
frozen buckets), `game-health-check` (eight-metric standing read), `early-journey-review` (D0–D7
funnel) and `older-cohorts-opportunity-assessment` (D30+ LTV levers).

The run has four stages and none is optional: **preflight → engine → adjudication → gated report.**

## Non-negotiables

1. **One report per `cli`.** Android and iOS are never merged. No figure crosses platforms except in
   a labelled divergence table, and never a figure from another game.
2. **Cut-points are frozen.** Computed once on a certified baseline, never recomputed inside a
   version line. Re-ranking each cohort pins every bucket at ~9.1% by construction and destroys the
   method.
3. **Every figure from a live query.** Never from memory, never from a previous run's report.
4. **All 17 sections, every run** (§10). A section with no finding is still rendered and marked; it is
   never dropped, and never swapped for a different topic.
5. **Measure the noise floor before believing any verdict** (§4). Most often skipped, and the clause
   that stops false findings.
6. **The report is not shown to anyone until the gate passes** (§11).

## 1 · Preflight — before building anything

Every miss becomes a BLOCKED candidate with one reason code (`schema-unclear` / `metric-not-found` /
`query-failed` / `resolution` / `not-run`), what was attempted, and the data-eng ask.

| probe | decides |
|---|---|
| `action_type` vocabulary **and which table carries it** | core unit, ranking unit, and the two-table trap below |
| Core-unit ladder `clear → end → start` | which event is the reported engagement metric |
| Atomic move unit (highest-count action) | the ranking-unit candidate |
| **Reproduce the registered cut-points on their own baseline window** | whether the saved baseline is what it claims to be |
| `economy_master_cc` columns, `earn_type` vocab, sign convention | earn/sink/purchase shape |
| Ad mart format labels + intra-day impression timestamp | whether first-impression eCPM is orderable at all |
| rid → network mart existence | whether the network layer is tier 2 or tier 3 |
| Session schema (`tracking_slice_<game>`, pause event, duration field) | session time feasibility or BLOCKED |
| IAP: net % of total revenue; payers per cell; **which mart carries each `cli`** | materiality gate A, resolution gate B |
| `event_exp_users` coverage, arm balance **and allocation window** | whether causal claims are available |
| Build registry freshness | build-boundary tests |
| Maturity guard `installs(diff=N) ÷ installs(diff=0) ≥ 0.98` at N=7,30,90 | the matured windows |
| `cli` materiality (≥5% of installs) | which platforms report |
| Cell counts: bucket × band × cli, then × network | whether deciles, tertiles or nothing is reportable |
| Weekly install series, 6+ months | ramp, plateau or soft launch |
| Game's earliest install date **in the table you will rank on** | whether a year-earlier control exists at all |

**The install-series probe is not optional.** A game mid-ramp, or a platform in soft launch, produces
a ladder that does not order and bands with no population. Finding that after building eight sections
wastes the run.

### The two-table trap — check this before anything else

A game's events can live in **two** marts whose `action_type` vocabularies overlap and whose `actions`
column means different things. Both failures below were found by the reproduction probe, in two
different titles, within one run of each other:

- One title emitted `play` into an aggregated mart *and* a per-event mart that agree to 0.001%. A
  baseline built by summing both was **exactly 2× correct** on all nine cut-points. Doubling is
  monotone, so the partition was unaffected and only the printed thresholds were wrong.
- Another title's per-event mart carried a *payload* in `actions` averaging 38.6 per row, while the
  aggregated mart carried the event count. The registered baseline ranked on the payload while the
  report called it a count of clears — magnitudes overstated ~36×, and the partition genuinely
  differed (Pearson r 0.98, not 1.0). Worse, the true count **fails the tie test** that the payload
  passes, so the adopted variable was right for a reason the registry stated incorrectly.

Rules that follow: the core unit may exist in only one of the marts (check before assuming it is
missing); **record the source table and column in the baseline registry**, never the unit name alone;
and run the reproduction probe on every registered baseline, not just the one you are using.

### Query pack and cost discipline

One scan per table per run. Tier caps: tier 1 unbounded, tier 2 ≤200 partitions/query, **tier 3 ≤3
partitions/query and ≤9/run.**

| # | query | serves sections |
|---|---|---|
| C0 | preflight probes | 17 |
| C1 | **D0 ranking + cut-points** — persist `rid → bucket` as the bucket map; every downstream query joins it | 1 |
| C2 | cohort spine + survival from `dau_splits` (partition is `dau_date` — bound `install_date .. +180`) | 1, 12 |
| C3 | engagement × bucket × band | 4 |
| C4 | ads per format + first-impression | 6, 7 |
| C5 | economy earn / spend / purchase | 8, 9, 10 |
| C6 | IAP gates | 11 |
| C7 | network × bucket matrix + `campaign_spend` CPI | 2, 3 |
| C8 | session time (tier 3, sampled, matched weekdays) | 5 |
| C9 | change registry: `event_exp_users` + build | 13 |
| C10 | noise-floor series (≥8 periods of C1+C3 at bucket grain) | 1, 12 |
| C11 | peer eCPM benchmark (tier 3) | 13 |
| C12 | year-earlier window on the same frozen cuts | 13 |

Persisting C1's bucket map once is the difference between a ~14-query run and a ~40-query one. Write
it to session state, not the Project. **Never scan a tier-3 slice for tier-2 information.** The
coverage matrix is the acceptance test: every rendered figure maps to one query, and a run fails the
gate if any number is unsourced.

## 2 · The bucket engine

### Choosing the ranking unit — on evidence

The core unit (a completed level/match) is what you *report*. It is often the wrong thing to *rank*
on. Test it:

```
cut_k = percentile(d0_unit | d0_unit > 0, k/10)   for k = 1..9
```

If any two adjacent cut-points are equal, that pair of buckets is a random partition of identical
behaviour — **reject the unit.** Fall back to the atomic move unit, then justify the swap with
Spearman ρ between the two rankings; ρ > 0.95 means nothing is lost and resolution is gained. Record
it as a deliberate, evidenced deviation, **naming the table and column adopted.**

### Buckets

```
d0_unit(rid) = Σ actions WHERE action_type = <unit> AND date_field = install_date
bucket(rid)  = ZERO            if d0_unit = 0
               k               such that cut_(k-1) < d0_unit ≤ cut_k
```

- `actions` is a **count column in the aggregated mart and may be a payload in the per-event mart** —
  §1 decides which. Sum it, never count rows.
- Cut-points over the **positive mass only**, which keeps the zero class out of the ladder.
- **ZERO is a structural class, not bucket 1.** `ntile` would scatter the tie mass at random.
- Zero mass varies hugely by game (33% one title, 8% another). A small zero class means zero-drift is
  *not* that game's dominant signal — look at the top of the ladder instead.

### Validating the ladder — the gate on everything downstream

Validate with instruments **independent of the ranking variable**: D1/D7 retention and ad coverage
from `dau_splits`, never from the engagement table the buckets were built from.

**If the ladder does not order, stop.** One inversion at a narrow adjacent pair is tolerable and must
be named; three inversions, or a zero bucket that *out-retains* the lowest play bucket, is a failed
instrument — report the failure and what would fix it. Narrow cut widths cause adjacent-pair
inversions; collapse to five groups (Z / low / mid / high / top) when you need a ladder that orders
every period.

## 3 · The arithmetic

```
M  = Σ_d share_d × value_d          share_d = den_d ÷ Σden   ← the DENOMINATOR share

ΔM = Σ_d (Δshare_d × value_d,ref)   → MIX          composition moved
   + Σ_d (share_d,ref × Δvalue_d)   → RATE         behaviour moved
   + Σ_d (Δshare_d × Δvalue_d)      → INTERACTION  neither

rate_share = |RATE| ÷ (|MIX| + |RATE|)
   ≥ 65% → GAME     ≤ 35% → CAMPAIGN     else SPLIT
   |ΔM| < 2% of base → NOISE regardless
```

- **The share is the share of the metric's own denominator, not of installs.** Weighting a
  per-active-day metric by install share does not close — it fails by ~1e-1, which is large enough to
  see and small enough to ignore if you are not asserting closure. Assert it.
- **Report two decompositions for every rate metric.** Per-install (install-weighted) isolates pure
  intake; per-active-day (activity-weighted) isolates intensity but blends intake with retention,
  because a bucket's share of active-days falls both when fewer installs land there and when they
  retain worse. Name which one each verdict rests on.
- **Print INTERACTION, never fold it.** Folding it is how a 50/50 split silently becomes 70/30.
- **Assert closure.** MIX + RATE + INTERACTION must reproduce `cur − base` to six decimals. A run that
  does not close has a bug — find it before writing prose.
- Ratios are always `Σnumerator ÷ Σdenominator` over the window — never a mean of means.
- Per-bucket MIX terms are **not individually interpretable** (shares sum to 1). Print totals only.

## 4 · The noise floor — measure per game, never borrow

Before reporting any verdict, build the null: pairs of (reference, current) windows **of the same
shape and the same displacement** as the real comparison, drawn from a stretch where nothing notable
happened, on the same frozen cut-points and the same arithmetic.

| | state |
|---|---|
| null mean, sd, max for MIX and RATE | the band inside which nothing is a finding |
| observed term and its z against the null | signal-to-noise |
| **share of quiet pairs exceeding the observed term** | the honest non-parametric version |
| null distribution of `rate_share` | how often a quiet pair would be chipped GAME or CAMPAIGN |

**Displacement matters as much as shape.** A null built from *adjacent* blocks understates the bar for
a comparison made ten weeks apart. In production the adjacent null had mean −0.071 and the
displacement-matched null −0.334 on the same series: a third of the observed move was drift the series
was already carrying. Build the null at the displacement you are actually using.

Rules that follow:
- If more than ~20% of quiet pairs exceed the observed RATE, **it is not a behaviour finding.**
- Widening the window helps only if the series has no trend. If a wider block cuts the sd far less
  than √n predicts — or shifts the mean instead — the series is trending and the trend is being
  absorbed as signal. Say "persistent drift", not "step change".
- Single-week windows are unusable on small titles: 60% of quiet week-pairs chipped GAME on one game
  with nothing happening. Print the figure and let it justify the window length you chose.
- Bonferroni (`|z| > 3.1718` at 11 buckets × 3 bands = 33 tests, α = 0.05/33) protects individual
  cells and says nothing about the headline. Both are required.
- The floor is measured per band. Reading one band's floor across to another is an assumption —
  label it, and open a ledger row to measure the others.

## 5 · The adjudication gate — a mix effect is not automatically a campaign effect

The most important discriminator in the method. It regularly **overturns the raw chip.**

A product change that shortens or breaks the first session moves players *across* bucket boundaries.
That changes composition by construction, so it lands in MIX looking identical to an intake change —
while players who still clear the top threshold behave exactly as before, so RATE stays flat.

**Hold network constant and re-cut, then hold geography constant and re-cut again:**

| pattern | verdict |
|---|---|
| Drift concentrated in one or two bought networks | CAMPAIGN |
| Drift common across most networks, **especially organic** | **GAME** — nobody buys organic, so no media decision can move it |
| Drift survives holding country constant inside every network | GAME, and report the sign test |
| Zero-share flat while the top of the ladder erodes | first-session depth change, not an install-quality break |

A consistent sign across independent strata is stronger evidence than the headline statistic. Drift
rising in 5 of 5 geo-controlled network strata is p = 0.031 under a coin-flip null, which can carry a
finding whose aggregate sits at the edge of the noise floor. Say exactly that when it happens.

Then find the mechanism, cheapest first:

1. **Build boundary — within a single install week, and within each network.** A raw build cut is
   confounded: users on older builds are a different population, not a treated one. One run's raw cut
   showed 61.7% vs 34.2% non-players between two builds and looked damning; the older build's
   population was 50.3% one low-quality source against the newer build's 14.0%. Re-cut inside each
   network, the newer build was **equal or better everywhere** — no regression at all.
2. **Server or config change** not behind an arm.
3. **Randomised arm** — difference-in-differences against control. Check the allocation window first:
   an arm live in *both* windows cannot explain a difference *between* them, and an arm that stopped
   allocating explains nothing. An arm that began between the windows is the only one with the right
   timing.
4. **Season** (§13 Test 1). A 364-day shift preserves weekday alignment. It can make a move *worse*:
   one title's non-player share improved 3.0pp over the same summer weeks a year earlier while the
   current year worsened 7.9pp, making the season-adjusted move +10.9pp rather than +7.9pp.

## 6 · Tenure bands and matured windows

Bands **D1–D7, D8–D30, D31–D90** (add D91–D180 when the partition budget allows a second cohort
universe). Each band is measured on the newest install cohort that has *fully* aged that far, so the
bands are different cohorts weeks or months apart.

- **Never compare one band's level to another's.** Each panel carries its own cohort stamp.
- Derive windows from the cohort cutoff: every install in the week needs `install_date + N ≤ cutoff`.
- **Choose the reference window on volume, not convenience.** A reference block sitting inside a spend
  spike imports a composition shift into every downstream verdict. Prefer a volume-matched block and
  record the choice as a deviation.
- Cap confidence on any band whose windows sit inside a ramp or spike, and say why.
- A band with no population is BLOCKED for absence of installs — not a maturity limit.

## 7 · Metric contracts

| metric | the rule that matters |
|---|---|
| Engagement | Three instruments — volume (core unit/active-day), intensity (atomic unit/active-day), efficiency (atomic per core). Gating on volume alone is the classic false positive: volume down with efficiency up is efficient mastery, the standing default, and it takes evidence to overturn. |
| **Active-day denominator** | From `dau_splits`, **never** the engagement table — an engagement row exists only when the player acted, so using it drops idle days and inflates every rate. Define "active-day" in words in the report; it is the most misread term on the page. |
| Win rate | Only where a `fail`-equivalent exists: `clears ÷ (clears + fails)`. Win rate per attempt holding while volume falls means pacing, not difficulty. |
| Session time | Bound the duration column hard (e.g. 1..7200s) — epoch-contaminated in every title checked. Report the median, never an untrimmed mean. Fire a structural-break detector when sessions and length move in opposite directions by >25% while the product holds. |
| Ad revenue | `rev/AD ≡ eCPM × imps/AD ÷ 1000`. **Two factors, two buckets, two verdicts** — never one blended chip. eCPM **per format**; banner impressions can outnumber interstitials 30:1 at 1/200th the price, so a blended figure goes wherever banner volume takes it. |
| **First-impression eCPM** | Confounded by impressions-per-day in *both* directions. Rising eCPM alongside falling impressions/AD is **waterfall depth, not price** — and the test is whether revenue/AD moved with it. Flat revenue means depth; revenue up 30% on volume down 9% is too much to come from trimming a cheap tail, and is a real yield change. Treat the raw figure as a measure of waterfall depth, never of user value. |
| **Peer control on any price move** | Run the same comparison across other titles on the same platform over the identical calendar weeks before booking a price change as yours. One run's −9.8% was an *outperformance* against a −14.6% peer median; another's +43% was real because the peer median was −6.0%. |
| Economy | Split `earn` / `spend` / `purchase` natively from the schema, never inferred. Purchased coins belong to IAP, not the faucet. Report sink concentration as a level every run — a stable-but-fragile monoculture never trips a change gate, which is exactly why it must be stated. |
| Coin surplus | `free_earn ÷ sink`. A **rising** surplus is the leading indicator of a coin-demand collapse IAP cannot yet detect; a falling one means sink demand is outgrowing the faucets. Crossing 1.0 is a reportable event. Direction matters more than magnitude. |
| IAP | Gate A materiality: net IAP ≥ 2% of total revenue. Gate B resolution: ≥500 payers and ≥$10k per 30 days per cell. Run a resolution ladder (bucket×band → bucket-group×band → bucket pooled → aggregate) and **print the level reached**. Below gate A, report as below-threshold, not LIMITED. Check which mart carries each platform — one title's IAP mart held zero rows for iOS while gross bookings sat in another table. |
| Network × CPI | CPI is a **network-level column attribute, not a cell value** — spend buys installs, not buckets. To make the matrix a decision: `EV(net) = Σ_d share_d(net) × value_d(baseline)`, `CPQ = CPI ÷ EV`. A cheap weak network can beat an expensive strong one — state the crossover point. |

## 8 · Verdict vocabulary

`GAME` (behaviour / first-session, product owns) · `CAMPAIGN` (composition, UA owns) · `SPLIT` (both,
neither team alone) · `EXTERNAL` (market moved, nobody here caused it) · `AD-OPS` (yield or waterfall
change inside our own ad stack) · `NOISE` (under 2% of base or inside the measured floor) · `BLOCKED`
(uncomputable, with reason and ask).

**Never collapse a per-band verdict into one chip.** A metric that is composition-driven in week one
and behaviour-driven by month two genuinely has two answers. Emit chips from **one helper used by both
the summary board and the section body** — see clause W in §11.

**A price verdict is never GAME.** The arithmetic will chip a rising eCPM as rate-dominated, but rate
here means price, which the product does not set. Route every price verdict through §7's peer control
and land it on EXTERNAL or AD-OPS.

Verdict chips are **L2 furniture**, not L1. A leader reads the metric move and the insight; the chip is
how an analyst checks the attribution.

## 9 · Versioning controls

Three things version independently. **Two reports are comparable only when all three match.**

### 9.1 `method_version`

**MAJOR** any change to arithmetic, thresholds or verdict vocabulary — **or to the fixed-section
contract, or a rename that supersedes a prior skill** · **MINOR** a new metric or gate clause inside an
existing section · **PATCH** wording, layout, chart or accessibility fixes. Append to the changelog
**in the same edit** as the change.

### 9.2 `baseline_id` — the frozen cut-points, per game × platform

```
B<n>·<gid>·<cli>·<unit>·<YYYY-MM-DD→YYYY-MM-DD>·<hash8>
hash8 = sha1( sorted cut-point vector | unit | window )[:8]
```

- Computed **once**. Never recomputed inside a version line.
- The registry row **must name the source table and column**, not the unit name alone. Two of two
  baselines audited were unreproducible from their recorded definition because the unit name was
  ambiguous across two marts.
- **Re-baselining is a breaking event.** It increments `<n>`, and reports across the boundary are not
  comparable — the masthead must say so. A **record correction that leaves the partition unchanged is
  not a re-baseline**: keep `B<n>`, reissue the hash against the corrected vector, and state it.
- **Stability audit every cycle**, run on two windows: the current window (drift — the early warning)
  and **the baseline's own window (reproduction — the defect check)**. One query each.
- Maintain a registry including baselines marked **UNCERTIFIED** (ladder failed) and **MISLABELLED**
  (partition sound, variable misnamed) so nobody publishes against them unknowingly.

### 9.3 `run_id` and the two ledgers

```
run_id = <gid>·<cli>·<as_of>·<method_version>·<baseline hash8>
```

**Run log** per run: the resolution table, the windows used, every deviation from this skill with the
evidence that forced it, self-corrections made during the run, the headline, and what was not run with
its reason and cost. **Record wrong calls as well as right ones** — a run log containing only real
catches is not a useful record.

**Hypothesis ledger** per game, carried run to run: `id, statement, state, why_picked_up,
discriminating_test, priority, opened_run_id, last_touched_run_id`. States `live` / `validated` /
`rejected` / `watch` / `closed`. **Never delete a row** — change its state. A rejected hypothesis often
leaves a shippable side-finding; record it as its own row.

The ledger and each section's L2 "hypotheses checked" part are the same record at two grains. Reconcile
them at the end of every run.

### 9.4 Correction propagation

When a later section overturns an earlier one, or a defect is found in a shipped report: mark the
section `CORRECTED BY §N` with a precedence rule (the section body supersedes the board, the act-now
box and the caveats); remove all pre-correction language elsewhere; state which questions the
correction closed; re-issue under a PATCH bump and note it in the run log. Never edit a shipped figure
silently.

## 10 · Report structure — 17 fixed sections, two tiers each

One self-contained HTML per `cli`, `CohortAttribution_<Game>_<PLATFORM>_<as_of>.html`.

### Fixed-section discipline

The 17 sections below are canonical. **Every one appears, in this order, in every run, for every
platform**, so two platforms read side by side and two months read against each other.

- **Section has a finding** → render it normally: L1 then L2.
- **Section has no material finding** (metric stable, inside the noise floor) → still render it, and
  say so in the L1 insight. "Nothing moved here" is an answer.
- **Section is uncomputable** → render it with a BLOCKED chip, the reason code, what was attempted and
  the ask. Never fabricate a chart or a number to fill the slot, and never swap in another topic.

### The 17 sections

| # | section | the question it answers | L1 callout | L2 core table |
|---|---|---|---|---|
| 1 | The bucket itself | can you trust the instrument? | bottom→top retention spread; measured drift band | bucket × D0 range × share × D1/D7/D30 retention × active-days/install |
| 2 | Share drift and its adjudication | did intake quality move, and whose is it? | non-player share, ref → cur | network × zero-share × install share × direction; then MIX/RATE per metric |
| 3 | Acquisition network share × CPI | are we paying for quality or for volume? | cost per expected unit, best vs worst network | bucket × network install share (month / week / latest day); then network × EV × CPI × CPQ |
| 4 | Engagement progression | do the players who stay still play as much? | core unit per active-day, per band | band × bucket × volume × intensity × efficiency × Bonferroni z |
| 5 | Session time | are sessions shorter, or fewer? | median minutes per active-day | band × bucket × min/AD × median × segments/user × break test |
| 6 | Ad revenue per active-day | did ad money move, and which half moved it? | revenue per active-day, split into price and volume | band × bucket × rev/AD × eCPM × imps/AD × rev per 1k core units |
| 7 | First-impression eCPM | is the price signal usable at all? | coverage, days to first | bucket × coverage × days-to-first × first-day eCPM × usability |
| 8 | Game sink | is the game still absorbing coins? | sink per active-day | band × bucket × sink/AD × by-source breakdown |
| 9 | Game earn | is the faucet running faster? | free earn per active-day | band × bucket × earn/AD × by-source breakdown |
| 10 | Net coin flow and surplus | will coin demand hold? | surplus (earn ÷ sink) against the 1.0 line | band × bucket × surplus × net flow × state |
| 11 | IAP | is anyone paying, and can we see it? | payer rate, USD per install, resolution level reached | band × bucket-group × payers × payer rate × USD/install × ARPPU |
| 12 | Survival, exposure and multiple testing | is the panel comparing like with like? | active-days per install; survivorship exposure | band × bucket × exposure × retention; then panel × right-edge N × matured week × reference window |
| 13 | Causal tests | season, experiment or market? | season-adjusted move; peer median | seasonality DiD; experiment allocation registry; arm DiD; peer eCPM |
| 14 | Guardrail check | did we break something while fixing something? | worst protected metric | protected metric × reference × latest × Δ × veto rule |
| 15 | Hypotheses, ranked | what do we do next, in what order? | number live, top priority | # × hypothesis × discriminating test × what it is worth × priority |
| 16 | Dependency map | which findings rest on which? | count of findings resting on a single instrument | directed list: finding → the section it depends on → what breaks if that section is wrong |
| 17 | Caveats and BLOCKED register | what could we not measure? | items blocked, data-eng asks | item × reason code × what was attempted × what would unblock it |

Sections 1, 12, 14, 16 and 17 rarely carry a "finding" and are not supposed to. They carry
**assurance**, and a run that drops them is a run that has quietly stopped checking itself.

### Order the page by the argument

The numbering above is also the reading order: *can you trust this → the intake side → the behaviour
side → the money → is the comparison fair → what caused it → did we break anything → what to do →
what we could not see.* A section that is *evidence for* another must not be presented as its peer.

Open with a **three-tile executive strip**: the one finding, the one action, how confident. A leader
should not pass a masthead, a glossary and a board before reaching an answer.

### L1 — four fixed elements, in this order

1. **Metric callout.** Stat tiles: metric name, reference → current, delta, direction-coded. One
   glance answers *what moved and by how much*.
2. **Insight.** One or two sentences of plain language with **zero method vocabulary** — what it
   means, never how we know. Enforced by clause L1-3.
3. **Action.** One instruction with a named owner, or the explicit words *No action*, which is an
   answer rather than an omission. Say what **not** to do where that is the risk ("do not book the
   price rise as a gain") — a warning is an action.
4. **L1 visual.** One picture whose only job is to make the insight obvious — and usually **not** the
   analytical chart. A detection band with the observed move marked answers "is this big enough";
   paired bars answer "did these move"; opposing factor bars with the flat product between them answer
   "why is the total flat when a factor jumped"; a status strip answers "what shape is the gap".

### L2 — five fixed parts behind one `<details>`

1. **Methodology** — what was held constant and what that lets you conclude.
2. **Formulae** — the arithmetic in mono, with a gloss on each named term.
3. **Definitions** — the terms *this section* uses. Per-section definitions replace the central
   glossary, so an L1 reader never needs one.
4. **Hypotheses checked** — what was tested and the verdict on each, *including the rejected ones and
   the ones that cannot be tested*. This is where an analyst decides whether to trust the section.
5. **Supporting / disproving data** — the full shift-share tables and the analytical charts.

### Mechanics

- Native `<details>`/`<summary>`. **No JavaScript** — the gate bans `<script>`, and native disclosure
  is keyboard-accessible and survives print-to-PDF. Add `@media print{details{display:block}
  summary{display:none}}`.
- Label the control for what it contains: *"More detail — methodology, formulae, definitions,
  hypotheses and the supporting data"*, not "Show more".
- Order categorical bars by segment size and print the size in the label. A 156-install channel should
  not be the most prominent bar on the page.
- Give the L1 chart a caption that names the conclusion, not the axes.

## 11 · The gate — run it before anyone sees the report

Text clauses first, then the rendered audit. **Do not present the report until every clause passes**,
and print the clause set plus the PASS line in the report itself. When a defect escapes, add a clause
for its *class* — not a patch for the instance — and negative-test it.

### Fixed sections (F1–F3)

`F1` all 17 canonical sections present, in order · `F2` every section resolves to exactly one state —
finding, no-material-finding, or BLOCKED with a reason code · `F3` section order and section set are
identical across platforms of the same run.

### Structure and sourcing (A–S)

Every section carries a confidence **and** a causation flag (`correlational` /
`causal-on-current-data` / `needs-experiment` / `quasi-experimental`); decomposed metrics render one
bucket per factor; cross-sectional panels carry a rendered MIX-DIAGNOSTIC label with no verdict word
inside; every contested verdict names its discriminating test; identity is consistent between
masthead, footer and filename; no banned skip token outside a BLOCKED note; ≥1 sized number and,
where a GAME verdict exists, ≥2.

### Versioning (V1–V6)

`V1` method_version stamped as semver · `V2` baseline_id stamped · `V3` run_id stamped · `V4` exactly
one baseline_id appears in the document · `V5` the comparability rule is stated in the footer · `V6`
method_version agrees between masthead and footer.

### Verdict consistency (W)

Where a verdict appears in more than one place, emit both from **one helper**, then assert they match
by comparing the rendered chip sets. Two independent rules once produced disagreement on **7 of 22
rows**, so a reader got different answers depending on where they looked. If a metric genuinely has
several answers, **render all of them rather than collapsing.**

### Comprehension (Y1–Y5)

`Y1` every term defined in the section that uses it · `Y2` the active-day denominator defined in words
· `Y3` window legend naming reference and current per band · `Y4` executive strip with exactly three
tiles · `Y5` the L2 control is labelled for what it contains.

### L1 / L2 contract (L1-1 … L2-1)

`L1-1` every section has exactly one L1 block and exactly one L2 block · `L1-2` every L1 block has all
four elements — callout row, insight, action, visual · **`L1-3` zero method-lexicon terms in any L1
insight**, machine-checked against the lexicon (MIX, RATE, rate_share, frozen, cut-point, decile,
percentile, Spearman, Bonferroni, z, null, noise floor, active-day, tenure, denominator, adjudicate,
DiD, control arm, survivorship, matured, waterfall, eCPM, confound, and the table names) · `L1-4` every
action names an owner or says *No action* · `L2-1` every L2 block has at least four headed parts.

Two notes on L1-3. Match `DiD` case-sensitively or it fires on the word "did". Permit a term where the
insight exists to warn the reader off it — "the eCPM figure is **not a win**" is the sentence doing its
job — and encode that exception rather than weakening the clause.

### Inert encoding (C11) — measured, not reasoned

A family base plus a modifier token (`sd neg`, `chip c-game`) is meant to encode direction or verdict.
If two different modifiers in one family resolve to an **identical computed rendering**, the encoding
is inert: the page still passes contrast, layout and clipping while telling the reader nothing.

Measure it on the rendered page rather than reasoning from the stylesheet — a modifier can exist as a
standalone rule elsewhere and *look* defined while the compound selector that was meant to style it
does not exist, the two single-class rules then tying on specificity with source order deciding.
Measuring also avoids false alarms on a deliberately shared colour vocabulary used across several
bases. Flag any two distinct modifiers in a family that render identically.

### Rendered-output audit (Z)

Static checks on HTML source cannot see contrast, wrapping or overflow. Three defect classes shipped
through a 40-clause text verifier while making content unreadable: ~93 table cells at contrast 1.13, a
table clipping every long cell, and verdict chips at 2.19.

Render in headless Chromium and, for **every text node**, compute the effective foreground against the
nearest opaque ancestor background and take the WCAG ratio. Sweep **light and dark × at least three
viewport widths** (1440 / 1140 / 760). Fail on:

| finding | test |
|---|---|
| `INVISIBLE` | contrast < 2.2 |
| `CRITICAL` | contrast < 3.0 |
| `CLIPPED` | `scrollWidth > clientWidth + 3` with `overflow-x: visible` |
| `COLLAPSED` | a chart, board, section or table rendering under 4px in either dimension |
| `HIDDEN` | `display:none` / `visibility:hidden` / `opacity:0` on an element carrying text |

Report `LOW` (< 4.5) without failing, and fix it anyway for anything carrying numbers.

**The audit must open every `<details>` before it runs** — collapsed L2 content is `display:none`,
which would flag as HIDDEN and would otherwise silently stop contrast- and clip-checking most of a
17-section report. Open them all, then report how many were opened.

Implementation notes: walk **up** the ancestor chain for the background (treat alpha < 0.85 as
transparent and keep walking); audit `svg text` separately against its chart container; aggregate by
selector + ratio or one bad token yields hundreds of lines; exit non-zero and print failing selectors
with both colours.

### Negative-testing the gate — required

A clause nobody has seen fail is not known to work. Each cycle, break and restore at least: L1-3
(inject a method term into an insight), L1-4 (delete an action), F1 (delete a section), V4 (inject a
second baseline_id), W (desynchronise two chips), C11 (make two modifiers render identically), Z
(reintroduce a known-bad colour). Confirm each fails, restore, confirm the suite passes.

When a negative test does *not* fire, the clause is wrong, not the file. One C11 draft passed a
mutation because the real rule was more specific than the injected one — the clause was tightened
until the mutation failed.

### Authoring rules that make Z pass

**No literal colour inside a component rule.** Define the token in bare `:root`, override the token per
theme, style only through the token. This one rule prevents the whole dark-mode defect class.

- Tokenise **all three** parts of every semantic family — foreground, background *and* border.
  Overriding only the background for dark leaves dark text on a dark ground.
- Declare all three theme states: bare `:root` (complete light palette), `@media
  (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and
  `:root[data-theme="dark"]`. The default "system" setting stamps nothing.
- Give `body` an explicit token background — a transparent body borrows the host's ground.
- Tokenise row highlights, callout backgrounds, action-box grounds, L1 stat tiles and chart
  grid/axis/label ink. These are the forgotten ones.
- **Table wrapping is opt-in:** `td { white-space: normal }`, with `td.num, td.rl, th { white-space:
  nowrap }` and prose cells capped at `max-width: 46ch`. Blanket nowrap is right for a numeric bucket
  grid and catastrophic for any table holding sentences.
- Wide content scrolls in its own `overflow-x: auto` wrapper, never the page body.
- Missing values need a **visible** mark — use the tertiary ink token, not a near-invisible grey.

### Chart rules

| rule | why |
|---|---|
| No negative axis label on a non-negative series | a percentage with a `-6.41` tick is a padding artifact; clamp the floor to 0 |
| Two series on one axis must share a unit | a count and a percentage on one scale compare nothing. **Index both to a common base** and say so, or use small multiples |
| Any co-movement claim carries a statistic | print the correlation rather than asserting it visually |
| Value labels never overlap row labels | on a long bar, print the value **inside** the bar in the inverse colour |
| Every axis label names a value the chart reaches | no ticks beyond the data |
| Chart text takes theme tokens | a hardcoded `fill` is invisible in one theme |

The F, W, Y, L1/L2, C11 and Z clauses are builder-agnostic — they audit a rendered page, not the code
that made it — so they lift into any other HTML report builder unchanged.

## 12 · Failure modes seen in production

- A narrative that contradicted its own table (a cost-per-quality ranking inverted the conclusion).
  **Read your own tables before writing the prose.**
- Weighting a per-active-day metric by install share, so the identity failed to close by ~1e-1.
- A noise floor built on adjacent blocks for a comparison made ten weeks apart.
- A raw build cut that looked like a regression and was a network-composition artifact.
- A hypothesis naming an experiment that had stopped allocating three months earlier.
- A registered baseline that was 2× its true value; another that ranked on a payload while the report
  called it a count, overstating every magnitude ~36×.
- Quoting one game's figures inside another game's report.
- Treating a rising eCPM as an ad win when impressions per active-day had fallen.
- Publishing a platform whose ladder had three inversions and a zero bucket out-retaining bucket 1.
- Writing the summary line for an analyst and the explanation for a leader, so the summary was the
  harder of the two to read.
- **Diagnosing a defect from a screenshot without probing computed styles, "fixing" it, and recording
  a catch that never existed.** Measure before claiming.

## Changelog

- **2.0.0** — Renamed from `cohort-decile-attribution`, which this supersedes. Report contract becomes
  **17 fixed sections** (§10) with fixed-section discipline — every section rendered every run, marked
  no-material-finding or BLOCKED rather than dropped — each carrying the L1/L2 two-tier treatment.
  Restores network × CPI, session time, first-impression eCPM, survival and multiple testing, the
  guardrail check and the dependency map as canonical rather than optional. New gate clauses F1–F3
  (fixed sections) and C11 (inert encoding, measured on the rendered page); negative-testing promoted
  to a required per-cycle step with a named clause list. §3 now specifies denominator shares and the
  two-decomposition rule; §4 requires a displacement-matched null; §5 adds the geo control, the sign
  test and the confounded-build-cut warning; §9.2 requires source table and column in the registry and
  a reproduction probe on every baseline. AD-OPS added to the verdict vocabulary with the rule that a
  price verdict is never GAME. MAJOR because the section contract and the skill identity both change.
- **1.3.0** — Two-tier report contract: L1 always visible with callout, insight, action and its own
  conclusion-stating visual; L2 collapsed behind one native `<details>` control. Added clauses
  L1-1 … L2-1 including the machine-checked ban on method vocabulary in L1 insights. Clause Z opens
  collapsed blocks before auditing. Verdict chips declared L2 furniture.
- **1.2.0** — Noise floor promoted to a non-negotiable, required per game and never borrowed.
  Adjudication gate given the organic tell and the build-boundary mechanism hunt. Per-band chips from
  one helper (clause W). Comprehension clauses (Y) and the rendered-output audit (Z) folded in.
  Versioning controls formalised with V1–V6 and a baseline registry.
- **1.1.0** — Causal layer: seasonality control on a 364-day shift, randomised-arm
  difference-in-differences, peer eCPM benchmark for EXTERNAL discrimination.
- **1.0.0** — Frozen-bucket engine, shift-share arithmetic, tenure bands, metric contracts, first
  verifier-gated report.