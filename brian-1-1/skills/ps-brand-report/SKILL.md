---
name: ps-brand-report
description: "Produces standard Playsimple-branded reports as PPTX decks and PDF documents, following the Playsimple Brand Playbook exactly — Playsimple Purple #A00FFF, MTG Dark Purple #2A0B35, the purple 100–600 ramp, the extended infographic palette, the three-face type system (MuseoModerno headings / Poppins content / Zalando Sans figures), 16px rounded cards, and the standard cover → summary → KPI → chart → detail → appendix structure. Defaults to an analytics performance report driven by analyst-game-performance at depth D2-R and styled per game-viz-design, but also produces general business reports (strategy memos, reviews, post-mortems, updates). Use whenever the user asks for a report, deck, deliverable, monthly/weekly/quarterly review, business review, or wrap-up in PPTX or PDF form, or says 'standard report', 'branded report', 'brand format', 'on-brand', 'Playsimple format', 'company template', 'same font and colors', or asks to export an analysis to slides or a document."
---

# Playsimple standard report

Builds the house report — one look, one palette, one type scale — in two output
formats: **PPTX deck** and **PDF document**. Both are generated from the same brand
token set, so a deck and a PDF of the same report look like siblings.

This skill owns *how the report looks and is assembled*. It does not source data.
For analytics content, route through `brian-master` to `analyst-game-performance`, which
decides what the numbers are and what they mean; `game-viz-design` governs inline chat
visuals. This skill is what turns that into a shareable file.

## Step 0 — Decide format and mode, then set up

**Format.** If the user named one ("deck", "slides", "PPTX" → deck; "doc",
"document", "PDF", "one-pager", "write-up" → PDF), use it. If they just said
"report", ask which — do not guess, the layouts differ substantially.

**Mode.**

- **Analytics mode (default)** — the report is about game/UA performance. Pull every
  number through `analyst-game-performance` (which loads `ps-data-catalog` /
  `ps-entities` and runs live queries), routed via `brian-master` so the depth contract
  applies. Never write a metric into a report that did not come from a query executed in
  this session.
- **General mode** — strategy memo, review, post-mortem, org update. Same brand shell,
  content comes from the conversation or the user's source material.

**Depth — a report never runs at D0.** `brian-master/references/depth-policy.md` sets the
floor at **D2-R** for any file deliverable: max(inherited depth, D2-R). The spine below has
sections a chat answer does not — Breakdowns, Detail, Recommendations — and D0 is defined as
"no cuts, no evidence layer", so a deck assembled at inherited D0 depth is asked for
sections its depth forbids it to produce. What ships is a thin deck of correct headline
KPIs followed by charts that restate them, and the failure is silent. At D2-R every headline
the report carries also brings its L1 contributor decomposition and the annotations scan
over the reporting window. **The SR-23 prose ceiling does not apply to a report** — the
density limits in the format references govern length instead.

**Setup.** Run once per session before generating anything:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/setup_fonts.sh
```

It installs MuseoModerno, Poppins and Zalando Sans (plus Inter as a fallback). If it
fails, stop and fix it — do not generate a report in a substitute font.

## Fonts — three faces, one job each

| Face | Job | Where |
|---|---|---|
| **MuseoModerno** | Headings | Cover title, slide/section titles, section dividers, closing headline, wordmark |
| **Poppins** | Content | Body, bullets, sub-heads, table text, captions, scope lines, KPI labels |
| **Zalando Sans** | Visualizations | KPI values, deltas, chart axis labels, data labels, legends, numeric table cells |
| Inter | Fallback only | Never chosen deliberately — last entry in the stack if a primary face is missing |

The split is functional, not decorative. MuseoModerno carries personality at title size
and none of it survives small, so it never runs below 18pt — sub-heads drop to Poppins
SemiBold. Poppins reads well in running text but is wide, so display sizes step down
from the old Inter scale. Zalando Sans owns everything numeric so a figure looks the
same whether it sits in a KPI card, a chart axis, or a table cell.

**MuseoModerno uses the short M / W / w.** Stock MuseoModerno defaults to decorative
wide-arch forms — the "ᙏ"-style M is unreadable in a report title. The family ships
short conventional alternates (`M.ss02`, `W.ss01`, `w.ss01`) and `setup_fonts.sh`
swaps them into the default slots via `scripts/build_museomoderno.py`. Lowercase `m` is
already short in the default set and is left alone. PowerPoint cannot apply stylistic
sets from a .pptx, so this has to happen in the font file — do not try to set `ss02` in
generator code, it will silently do nothing.

Sizes and tracking per level live in `references/brand-tokens.md`. Hierarchy comes from
face + weight + size together. Sentence case for headlines; all-caps belongs to the MTG
masterbrand and never appears in a Playsimple report.

**A .pptx does not carry its fonts.** It stores font *names*; if the recipient lacks
MuseoModerno, Poppins and Zalando Sans, PowerPoint silently substitutes one default face
for all three and the type system collapses. When a deck goes to anyone outside the
team, either send the PDF (fonts embed on export) or ship the .ttf files alongside it.
Say which you did in the delivery message.

Never substitute Montserrat, Futura, Helvetica, Arial or any other "close enough" face
when one of the three is missing — install it instead.

## The brand system, in short

Full values, ramps, and usage rules: **`references/brand-tokens.md`** — read it before
writing any styling code, and use the hex values verbatim.

The short version:

| Role | Value |
|---|---|
| Primary brand | Playsimple Purple `#A00FFF` |
| Dark ground / headings | MTG Dark Purple `#2A0B35` |
| Light ground | White `#FFFFFF`, panels `#F0EDF1` (Mist) |
| Purple ramp | 600 `#440E6F` · 500 `#6200B1` · 400 `#A00FFF` · 300 `#C782FF` · 200 `#DFB5FF` · 100 `#F7EBFF` |
| Extended (charts only) | Violet `#4C3255`, Lilac `#A69CED`, Lavender `#ACA0B0`, Mauve `#D4CED7`, Coral `#FF8787`, Crimson `#8C0E0E` |
| Corner radius | 16px cards / 0.16" on slides; pills fully rounded |
| Type | MuseoModerno headings (short M/W/w) · Poppins content · Zalando Sans figures and charts · Inter fallback |

Three hard rules carried from the playbook:

1. **Playsimple Purple stays the leading expression.** The extended palette exists for
   data-rich visuals; it never becomes the report's dominant color.
2. **Purple on Dark Purple is decorative only** — large display numbers and hero
   headlines. Never body text, never table text, never in CMYK print output.
3. **Only three colored grounds:** Dark Purple on White, White on Dark Purple, White on
   Purple. Anything else is off-system.

## Report structure

Both formats follow the same spine. Drop sections that don't apply; never reorder.

1. **Cover** — report title, period (explicit dates with year), owner, date produced.
2. **Executive summary** — 3–5 sentences or bullets. The takeaways, not a table of
   contents. In analytics mode this is the verdict: what moved, why, what to do.
3. **Headline KPIs** — the metric-card grid. Label, value, delta with comparison basis.
4. **Trends** — one chart per question. Every chart carries its own title, scope line
   (`population · date range · segment · units`) and one-sentence definition.
5. **Breakdowns** — cross-segment bars or tables (network, country, platform, game).
   In analytics mode this is the D2-R L1 decomposition, not a restatement of section 3.
6. **Detail / narrative** — the argument, per section. In analytics mode the annotations
   scan lives here: what shipped or changed in the window, as observation not causation.
7. **Recommendations / next steps** — owner + action, where applicable.
8. **Appendix** — methodology, metric definitions, query notes, caveats, depth run.

**A report with an empty Breakdowns section has run below its depth** — same class of
defect as a missing chart. Check it before packaging.

### Content rules that survive both formats

- **Every number is labeled with its units and period.** No bare "24.5" anywhere.
- **Every delta states its basis** — `+12.4% WoW`, `-26.0% MoM`. Never a naked arrow.
- **Deltas use `#2E7D32` (up) and `#8C0E0E` (down)**, as plain colored text. Green and
  red appear nowhere else in the report — not as series colors, not as highlights.
- **Explicit date ranges with the year.** Never "last month", "MTD", "recent".
- **Scope-line slots that don't apply are omitted, not filled.** A retention chart's
  scope ends at `% of cohort` — never `% of cohort, USD n/a`.
- **Say when ordering isn't by the plotted metric** (bars ranked by spend but showing
  retention, for example) in the definition line.
- **Charts use the categorical order in `references/brand-tokens.md`** — slot 1 is
  always Playsimple Purple, and an entity keeps its color across every chart in the
  report. **Mauve and Lavender are neutrals** for reference lines and remainders; they
  never carry the chart's subject metric.
- **No invented data.** Unmatured cohorts and missing days are plotted as gaps, or
  omitted with a note.

#### Chart rules — one policy, both formats

These are the same in a deck and in a PDF. Full mechanics in `references/pptx-report.md`
and `references/pdf-report.md`; `assets/ps_brand.js` enforces most of them at build time
and throws rather than shipping a chart that breaks them.

- **Round the values, don't just format the labels.** Rates 1 decimal (`27.9%`), money
  ≥ $10k whole (`$49.4M`), per-user money 2 decimals (`$0.16`), counts whole (`34.6M`).
  A format code alone does not survive a Google Slides import — the raw float comes back.
  **A data label with more than one decimal place is a defect.** Drop labels entirely if
  they collide at final size.
- **Category labels are real names, never ordinals.** `D1 · D7 · D30`,
  `Apr 2025 … Jun 2026` — never `1 2 3 … 15`.
- **Every multi-series chart carries a visible legend**, each entry naming its metric and
  units. The widget system substitutes an HTML dot legend for the chart legend; an exported
  file has no such substitute, so copying that setting here ships no legend at all.
- **Dual axis is allowed, with one set of gridlines.** Mismatched scales get a properly
  built dual y-axis or two stacked charts — never an indexed or rescaled series (SR-8).
  Legal only when all five hold: one set of gridlines (both axes pinned to the same tick
  count, rules drawn from the primary only), both axes titled with units, each legend entry
  naming its axis, axis label color matching its series color, and the subject metric in
  Playsimple Purple. Build it with `PS.dualAxis()`.
- **Match the raster to the destination.** Google Slides rasterises native PowerPoint
  charts at screen resolution, so a native chart arrives blurry there. Deck staying in
  PowerPoint → native charts. Deck going to Google Slides → render at 3× / ≥300 DPI and
  place the image yourself. PDF figures are 3× minimum either way.

## Building a PDF report

Read **`references/pdf-report.md`** for the full recipe.

Path: write a single self-contained HTML file that links
`assets/brand.css`, then render with headless Chromium.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/html_to_pdf.py report.html report.pdf
```

`assets/brand.css` already implements the whole system — page setup (A4, 18mm margins,
running footer with page numbers), cover page, type scale, KPI card grid, tables,
callouts, chart figure blocks. Use its classes rather than writing inline styles:
`.cover`, `.section`, `.kpi-grid` / `.kpi`, `.delta.up` / `.delta.down`, `.table`,
`.callout`, `.figure` (with `.figure-header`), `.appendix`.

Charts: render each chart to an inline SVG or a PNG at 3× and place it inside a
`.figure`. Chart.js in headless Chromium works — see the reference for the wait
handling and the `devicePixelRatio` setting.

## Building a PPTX deck

Read **`references/pptx-report.md`** for the full recipe, and follow the `pptx`
skill's pptxgenjs gotchas (no `#` in hex, `LAYOUT_WIDE` set before slides, fresh
options objects, `validate.py` after writing).

`assets/ps_brand.js` exports the palette, type scale, slide-master helpers, and
ready-made builders (`coverSlide`, `sectionDivider`, `kpiSlide`, `chartSlide`,
`chartImageSlide`, `tableSlide`, `closingSlide`) plus the chart correctness helpers
(`roundValues`, `FMT`, `dualAxis`, `assertChartIsReadable`). Require it from the
generator script rather than re-deriving colors or hand-rolling axes.

Slide sizing is `LAYOUT_WIDE` (13.3" × 7.5"). Grounds alternate deliberately: dark
cover, white content, dark section dividers, dark closing — never a random mix.

Always finish with both:

```bash
python /mnt/skills/public/pptx/scripts/office/validate.py deck.pptx
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/validate_charts.py deck.pptx
```

`validate.py` proves the file isn't corrupt. `validate_charts.py` proves the charts are
*readable* — an ordinal axis, a missing legend, an unformatted float and a misaligned dual
axis all produce a perfectly valid file. Both must exit clean before delivery.

## Delivery

Save outputs to the working directory, then deliver with `SendUserFile`. One-line
caption; do not restate the report's contents in chat — but do state the source and
period, whether charts are native or rasterised, and in analytics mode flag any metric
whose query returned partial data.

If the report will be revisited (a recurring monthly review, a live status page), also
offer an HTML version that can be persisted as an artifact.

## Guardrails

- **Never ship a report in a face outside the three.** MuseoModerno headings, Poppins
  content, Zalando Sans figures. If the font install failed, fix it before generating —
  no Helvetica/Arial/Montserrat fallback, no exceptions.
- **Never set MuseoModerno below 18pt**, and never in a table, caption, or chart label.
- **Never ship a .pptx to an outside recipient without the fonts or a PDF alongside it** —
  unresolved font names collapse the whole type system to one substituted face.
- **Never use a color outside `references/brand-tokens.md`.** No default matplotlib
  cycle, no default Chart.js palette, no Office theme colors.
- **Never let a neutral (Mauve, Lavender) carry a chart's subject metric.** The subject
  takes Playsimple Purple; a chart whose subject is grey while a derived ratio is purple
  reads backwards.
- **Never ship a multi-series chart without a visible legend.** There is no HTML dot
  legend in an exported file to fall back on.
- **Never ship a data label with more than one decimal place**, and never rely on a format
  code alone — pre-round the values.
- **Never ship a category axis reading `1 2 3`.** Real names, on every series.
- **Never ship a dual-axis chart with two sets of gridlines**, untitled axes, or legend
  entries that don't name their axis. If it can't meet all five conditions, use two charts.
- **Never index, normalize or rescale a series** to force two scales onto one axis (SR-8).
- **Never build a report at D0.** The floor is D2-R; an empty Breakdowns section means the
  depth was downgraded.
- **Never put body copy in Playsimple Purple on Dark Purple** — decorative display only.
- **Never use all-caps for Playsimple headlines** — sentence case; all-caps belongs to MTG.
- **Never let the extended palette outweigh Playsimple Purple** across the report.
- **Never invent, extrapolate, or round-trip a number** that no query produced.
- **Never ship a chart without title, scope line, and definition.**
- **Never deliver a deck without both validators exiting clean.**
- **Never reorder the report spine** — sections may be omitted, not shuffled.
- Do not restyle the logo, stretch it, or place it on a busy image area; clear space is
  1× the wordmark's stem thickness on all sides.
