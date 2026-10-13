---
name: game-viz-design
description: "House visual-design system for game/app analytics dashboards, KPI cards, and charts, delivered as an inline chat widget (HTML + Chart.js via the Visualizer) — never a saved PNG file unless explicitly requested. Every chart needs an in-widget header (metric name, explicit date range, segment, units, one-line definition) so it stands alone if screenshotted, plus a response-text insight heading (the takeaway, not just a metric label) as the only prose above it — series identification lives in the in-widget dot legend and is never restated as prose, and every multi-series chart uses a shared/index-mode tooltip so one hover reveals all series. Also defines the metric-card grid, delta colors, and chart styling for visual consistency. Use whenever producing a chart, graph, KPI card, or dashboard for game/app metrics — DAU, revenue, Rev/DAU, retention, ROAS, LTV, CPI, spend, network/country breakdowns — especially alongside analyst-game-performance, which calls this to style all its visuals."
---

# Game Analytics Visual Design System

A small, opinionated design system for game/app performance **dashboards, KPI cards, and
charts rendered inline in chat**. It exists so that every visual — whether produced on its
own or by the `analyst-game-performance` skill — shares one coherent look, and so it shows
up the way a dashboard does: live in the conversation, not as an attached image file.

**Default output mechanism: the Visualizer's HTML widget (`visualize:show_widget`), using
Chart.js for any charts.** Do not render dashboards or KPI cards as matplotlib PNGs and do
not present them as image files — that pattern is legacy and only used if the user
explicitly asks to export/download an image (see "Legacy PNG export" at the bottom).

## When this applies

Use this design system for any KPI card, trend line, or cross-segment bar chart of
game/app metrics (DAU, revenue, Rev/DAU, retention, ROAS, LTV, CPI, spend, network/country
breakdowns). If you're working inside `analyst-game-performance`, style **all** its charts
and cards through this module — the analysis skill decides *what* to plot and *what it
means*; this skill decides *how it looks* and *how it's delivered*. This skill does not
change any of the data, metric, or labeling rules in `analyst-game-performance` (units,
net+gross defaults, dual-axis-for-mismatched-scales, mandatory labels) — it implements them
with a consistent visual language, delivered as a live widget instead of a file.

## The fastest path

Optimize for time-to-first-visible-pixel — don't bundle everything into one giant call.

1. Call `visualize:read_me` with `modules: ["chart"]` **only if you haven't already loaded
   the `chart` module earlier in this conversation.** If it's already in context (you or
   `analyst-game-performance` loaded it earlier this session), skip straight to step 2 —
   don't re-fetch it every time.
2. Write your explanatory text (headline numbers, takeaways, what changed) as normal
   response text — never inside the widget.
3. Call `visualize:show_widget` **per section, not once for the whole dashboard**: one call
   for the KPI card grid, one call per chart. See "Composing a dashboard" below. Smaller
   calls render sooner and give the user something to look at while the rest streams in,
   instead of one large call that shows nothing until it's fully generated.
4. Keep the HTML/JS itself lean: no unused Chart.js options, no boilerplate you're not
   using, minimal inline comments. Less to generate and stream is faster end to end.

## Match the native dashboard look

Pin every widget to the board's visual language (the Playsimple in-house analytics board,
Figma "Analytics Mocks": `https://www.figma.com/design/xQ5I24EOMk7rs5lHomRnh6/Analytics-Mocks?node-id=5998-24003`).

- **White "Widget Bar" card.** `background:#fff; border-radius:8px;` with the board's soft
  double shadow: `box-shadow: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02);`. Header
  row `padding:6px 20px 8px; border-bottom:1px solid rgba(0,0,0,0.04);`, body
  `padding:8px 20px 16px;`.
- **Header block** is the board's version of the "Labels, always" three-line header: Title in
  `Archivo 600, 18px, rgba(0,0,0,0.85), line-height 26px`; scope subline in `Nunito Sans 12px
  rgba(0,0,0,0.6)`, segments joined by `|` (e.g. `D-2 | Jun 20 | net revenue, USD`).
- **Load fonts once** per conversation: `<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">`
  (both hosts are on the CDN allowlist).
- **Dot legend, not squares.** 8px filled circles, Nunito Sans labels in `rgba(0,0,0,0.6)`,
  series/measure name bold after `|` (e.g. `● Crossword | Revenue`). This is the one place
  the skill overrides the base chart module's square-swatch legend.
- **Board palette, fixed categorical order:** `#3b80f6` blue, `#eb6834` orange, `#1baf7a`
  aqua, `#8b5cf6` violet, `#e87ba4` pink, `#eda100` amber. Accent blue `#3b80f6`; link/active
  blue `#0177ec`. Gridlines: single hairline `#e7e9ee`, horizontal only.

## Rendering engine: Chart.js or Highcharts

Chart.js (from `visualize:read_me`'s `chart` module) stays the default, fast path. Highcharts
is also explicitly allowed — the board itself was built on it, so its stacked areas, stacked
columns, and shared multi-series tooltip (the DOD/WOW/Contribution hover box on the growth
widgets) reproduce the native look with less hand-work. Reach for Highcharts when a widget
genuinely benefits from that; use Chart.js for everything simpler.

The rules are engine-agnostic either way: actual values on every axis (dual y-axis when
scales mismatch — never indexed series), board palette in fixed
order, Widget Bar header + dot legend, rounded numbers, a shared/index-mode tooltip on every
multi-series chart, and the insight heading as the only response text above the widget — none of
that changes based on which library renders the canvas.

**Don't let the engine choice cost render time.** Load exactly one charting library per
widget, from the CDN allowlist — never both Chart.js and Highcharts in the same
`show_widget` call. Keep the config lean (no unused options, no boilerplate). Still split
dashboards across small, per-section `show_widget` calls regardless of engine — see "The
fastest path" and "Composing a dashboard."

A lean Highcharts config for a widget:

```html
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.8/highcharts.js" id="hc-netrev"></script>
<div role="img" aria-label="Net revenue by network, Jun 1-20 2026, USD actual values" style="background:#fff; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02);">
  <!-- Widget Bar header row here, per "Match the native dashboard look" -->
  <div id="chart-container" style="padding:8px 20px 16px;"></div>
</div>
<script>
  // construction is bound to the loader — never top-level; see "Loading the library"
  function drawNetRevChart() {
    if (window.__drawnNetRev) return;
    window.__drawnNetRev = true;
    Highcharts.chart('chart-container', {
    chart: { backgroundColor: 'transparent' },
    title: { text: undefined }, // header lives in the Widget Bar, not the chart
    credits: { enabled: false },
    legend: { enabled: false }, // use the HTML dot legend instead
    yAxis: { gridLineColor: '#e7e9ee', title: { text: undefined } },
    colors: ['#3b80f6', '#eb6834', '#1baf7a', '#8b5cf6', '#e87ba4', '#eda100'],
    plotOptions: { area: { stacking: 'normal' }, column: { stacking: 'normal' } },
    tooltip: { shared: true, useHTML: true, backgroundColor: 'rgba(0,0,0,0.85)', style: { color: '#fff' } },
    series: [ /* ... */ ]
    });
  }
  if (window.Highcharts) drawNetRevChart();
  else document.getElementById('hc-netrev').addEventListener('load', drawNetRevChart);
</script>
```

### Loading the library — the #1 cause of a blank widget

`Uncaught ReferenceError: Chart is not defined` (or `Highcharts is not defined`) means the
inline builder ran **before** the CDN script finished loading. In the widget sandbox the HTML is
injected rather than parsed as a document, so an external `<script src>` does **not** block the
inline `<script>` that follows it — the two race, and the inline one usually wins. This is a
render-order bug, not a data or config bug: re-check this section before touching the chart
config.

Three rules, all mandatory:

**1. Every `show_widget` call that draws a chart includes its own library `<script src>` tag.**
Widgets do not share a JS scope. A library loaded in an earlier call is **not** available in a
later one — that is how this error typically appears halfway down a multi-call dashboard, with
the first chart rendering fine. The library tag is not a "shared helper" (see "Composing a
dashboard"): re-include it in every single widget that draws a chart.

**2. Never call `new Chart(...)` at the top level of the inline script.** Wrap construction in a
named function and bind it to the loader's `load` event, with an already-loaded guard:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" id="cjs-retention"></script>
<canvas id="retention-canvas"></canvas>
<script>
  function drawRetentionChart() {
    if (window.__drawnRetention) return;   // idempotent — never double-draw
    window.__drawnRetention = true;
    new Chart(document.getElementById('retention-canvas'), { /* type, data, options */ });
  }
  if (window.Chart) drawRetentionChart();  // library already present (earlier widget on the page)
  else document.getElementById('cjs-retention').addEventListener('load', drawRetentionChart);
</script>
```

**Name the function and the guard flag after the chart** (`drawRetentionChart`, not `draw`).
Several widgets can coexist on one page, and a generic name silently overwrites a sibling's
function — producing a chart that renders the wrong data instead of erroring.

**3. Same pattern for Highcharts** — swap `window.Chart` for `window.Highcharts` and the CDN
URL. The rule is engine-agnostic.

If a widget comes back blank, check in this order: (a) was the library tag included in *this*
call, (b) is construction inside the `load`-bound function, (c) does the canvas/container `id`
in the script match the one in the HTML.

## Building blocks

### 1. KPI card grid

A CSS grid of board-native KPI cards — one per headline number — each a white Widget Bar
card whose body centers a large value with a comparison row per baseline underneath.

```html
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 1.5rem;">
  <div style="background:#fff; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02); padding:8px 20px 16px; text-align:center;">
    <p style="font-family:'Nunito Sans'; font-size: 13px; color: rgba(0,0,0,0.6); margin: 0 0 4px;">Net revenue</p>
    <p style="font-family:'Nunito Sans'; font-size: 48px; font-weight: 600; margin: 0 0 8px;">$839,399</p>
    <div style="display:flex; align-items:center; justify-content:center; gap:8px;">
      <span style="background:#fdece9; color:#ea4e2b; border-radius:12px; padding:2px 8px; font-size:12px; font-weight:600;">-26.0%</span>
      <span style="font-family:'Nunito Sans'; font-size:12px; color: rgba(0,0,0,0.6);">vs previous day | D-3</span>
      <span style="font-family:'Nunito Sans'; font-size:12px; color: rgba(0,0,0,0.6); margin-left:auto;">-$294,802</span>
    </div>
  </div>
  <!-- repeat per KPI -->
</div>
```

A KPI grid needs a header too, though a lighter one: a single muted line above the grid giving
population · date range · segment · currency (e.g. "Word Bingo · Feb 1–28, 2026 · all
platforms, all countries · USD"), since the cards themselves only carry metric names and
deltas. Spell out what each delta compares against in the descriptor row itself (e.g.
`vs previous day | D-3`).

Delta rule: up is text `#28b76f` on pill `#e5f5ed`; down is text `#ea4e2b` on pill `#fdece9`.
The absolute-change figure is right-aligned in the same row. These pill colors are reserved
for delta direction only — never reuse `#28b76f`/`#ea4e2b` or their pills as series colors.

### 2. Line chart

For trends over time (DAU, revenue, Rev/DAU). Follow the Chart.js or Highcharts rules above:
wrapper `<div>` with explicit `height` and `position: relative`, `role="img"` + `aria-label`
on the canvas/container, the dot legend (8px circles, not the module's default squares), and
the board palette in fixed order — so a game/network keeps the same color across charts
rather than being reassigned when the data is filtered. Lines are 2px, gridlines are the
single hairline `#e7e9ee`, horizontal only.

**ALWAYS plot actual numbers — never index, normalize, or rescale a series.** A chart value
must be readable as the real metric value; "indexed to 100" and any other transformation of
what's measured is banned (it reads as data manipulation and creates confusion against the
query results and dashboards). If two series have mismatched scales (e.g. revenue vs DAU),
use a **dual y-axis**: each axis titled with its series name and units, each series' legend
entry naming its axis ("DAU — left axis · Retained users — right axis"), left/right axis
label colors matching their series. If even a dual axis can't make both readable, use two
separate charts — but the numbers on every axis are always the actual values.

**One set of gridlines, always.** Two axes that pick their own bounds draw two independent
sets of horizontal rules that cross each other — the single thing that makes a dual-axis
chart look broken. Pin both scales explicitly so `(max − min) / stepSize` is identical on
each, and disable the grid on the right-hand scale:

```js
scales: {
  y:  { min: 0, max: 25e6, ticks: { stepSize: 5e6 }, grid: { color: '#e7e9ee' } },
  y1: { position: 'right', min: 0, max: 15e6, ticks: { stepSize: 3e6 }, grid: { display: false } },
}
```

**This rule is the same in an exported deck or PDF, where it is enforced in code.** The
dual-axis policy here is authoritative across all three surfaces — widget, PPTX, PDF — and
`ps-brand-report` implements it via `PS.dualAxis()`, which pins both axes to one tick count
and throws if a chart is built any other way. When editing the policy here, update
`ps-brand-report/references/pptx-report.md` and `pdf-report.md` in the same pass: three
files stating three different dual-axis rules is how a broken chart ships.

### 3. Bar chart

For cross-segment breakdowns (network, country, platform). Bars ≤24px thick, 4px rounded
data-end, value labels via a callback or an adjacent legend — same board palette and dot-
legend conventions as the line chart. Includes stacked columns for part-to-whole views —
Highcharts handles stacked columns and their shared tooltip cleanly (see the growth
widgets in "Rendering engine" above), so prefer it over hand-rolled Chart.js stacking for
these.

**Rate-metric ranking bars carry a contribution % label on every bar.** Whenever bars rank
games (or networks, countries, franchises) by a *rate* — ROAS, retention, Rev/DAU, eCPI,
LTV, stickiness, any ratio — each bar carries a second, smaller label giving that entity's
**share of the portfolio total** for the money behind the rate: spend share for
spend-driven metrics (ROAS, eCPI), revenue share for monetization metrics (Rev/DAU, LTV).
The rate is the bar height; the contribution % sits with it so the two are read together.
Without it, a 184% ROAS bar on 1.6% of spend looks identical to one on 25% of spend — the
chart tells the reader the opposite of the truth. Render the contribution % beneath the
category label (or as a bar-end annotation), muted relative to the value, and name what the
% represents in the header's definition line ("% under each game is its share of July
portfolio UA spend").

Where the bars would otherwise be ordered by the rate alone, keep that order but make the
contribution % legible enough to break the ranking illusion at a glance. A spend-weighted
portfolio average reference line, drawn and legend-labeled like the 100% breakeven line, is
the companion default on any ROAS ranking chart.

```js
scales: {
  x: { grid: { display: false },
       ticks: { callback: function(v, i){ return [this.getLabelForValue(v), share[i] + '% of spend']; },
                font: { family: 'Nunito Sans', size: 11 }, color: 'rgba(0,0,0,0.6)' } }
}
```

### 4. Hover tooltip — one hover shows every series

**A multi-series chart must reveal every series' value in a single hover.** The board's own
widgets do exactly this: hovering any point opens one box carrying the date, then a row per
series with its value and its DoD/WoW/MoM deltas. A tooltip that reports only the series the
cursor happens to be nearest forces the reader to hover twice to compare two lines — on a
chart whose entire purpose is comparison, that is a defect, not a default. It matters more
here than anywhere: because this skill bans indexing, dual-axis charts are the norm, and a
per-series tooltip on a dual-axis chart hides exactly the cross-axis comparison the chart
exists to make.

- **Chart.js:** set `interaction: { mode: 'index', intersect: false }` at the **options root**
  *and* `mode: 'index', intersect: false` under `plugins.tooltip`. Setting it only under
  `plugins.tooltip` leaves hit-testing per-point, so the box still opens one series at a time —
  this is the single most common way this rule gets shipped broken.
- **Highcharts:** `tooltip: { shared: true }` (already in the lean config above).
- **Add an x crosshair** on any time-axis chart so the hovered date is unambiguous:
  `interaction.axis: 'x'` in Chart.js, `xAxis: { crosshair: true }` in Highcharts.
- **Keep the dark box:** `backgroundColor: 'rgba(0,0,0,0.85)'`, white text, the x-value as the
  bolded title row, one row per series beneath it.
- **Format every value to the metric's real units** inside the tooltip — `%`, `$`, `s`,
  `toLocaleString()` for counts. On a dual-axis chart each row carries its own units, since the
  two series are not on the same scale. A raw float in a tooltip is the same defect as a raw
  float in an axis label.
- Carry period deltas (DoD/WoW/MoM) into the hover box where they are **already computed** for
  the response; never compute a new figure just to fill a tooltip.

```js
options: {
  interaction: { mode: 'index', intersect: false, axis: 'x' },
  plugins: {
    legend: { display: false },
    tooltip: { mode: 'index', intersect: false, backgroundColor: 'rgba(0,0,0,0.85)',
               callbacks: { label: c => c.dataset.label + ': ' + c.formattedValue + '%' } }
  }
}
```

### 5. Labels, always

**Every chart carries its own header inside the widget.** This is non-negotiable: a chart
must be identifiable when it is looked at alone — scrolled to out of context, screenshotted,
or pasted into Slack — with no surrounding conversation. A bare bar chart of percentages with
only game names on the x-axis is a defect, not a style choice.

The header is **chart furniture, not prose** — the "no text in the widget" rule bans
explanatory paragraphs, takeaways, and section headings, not a chart's own title and
subtitle. Render it as the first element inside the widget, above the canvas:

```html
<div style="margin-bottom: 0.75rem;">
  <p style="font-size: 15px; font-weight: 500; margin: 0 0 2px;">D1 rolling retention</p>
  <p style="font-size: 12px; color: var(--text-secondary); margin: 0 0 2px;">Top 10 games by UA spend · Jul 1–31, 2026 · all platforms, all countries · % of installs</p>
  <p style="font-size: 12px; color: var(--text-secondary); margin: 0;">Share of new installs who opened the game again the next calendar day, rolling 7-day window. Bars ordered by July UA spend, highest first.</p>
</div>
```

Three lines, in this order, every time:

1. **Metric name** — the exact metric, no abbreviation the reader has to decode.
2. **Scope line** — `population · date range · segment filters · units`, joined by `·`. The
   date range is always an explicit range with the year, never "last month" or "recent."
   Units are always stated (`%`, `USD`, `sessions/DAU`, `players`).
3. **Metric definition** — one plain-language sentence: what is counted, over what window,
   divided by what. Include the sort/ordering rule when bars or rows are ordered by something
   that isn't the plotted metric (a common source of confusion — the reader assumes bars are
   ranked by bar height unless told otherwise). Repeat this line on every chart; do not drop
   it on later charts on the grounds that it appeared once earlier in the conversation.

Give the canvas an `aria-label` carrying the same three facts, so the chart is described for
screen readers and in any context where the HTML is read rather than rendered.

Derive all three lines from the query that produced the data — the metric column, the date
filter, the `WHERE` clauses, and the `ORDER BY`. If you cannot state the definition and
window in one sentence, you do not yet understand the metric well enough to chart it: resolve
it against `ps-data-catalog` first.

**Two more things are mandatory for every chart, on top of the in-widget header — and one
thing that is explicitly banned:**

- **An insight heading in the response text, not just a metric label.** In the prose
  immediately above the `show_widget` call — the in-widget header handles identification, this
  handles meaning — lead with a short bolded line stating what the chart actually shows — the takeaway, not
  just the axis labels. Bad: "Net revenue by day." Good: "**Net revenue dropped 26% MoM,
  driven by the iOS network mix shift.**" The chart's own in-widget header carries the
  metric/period/segment/units — don't repeat them in the heading. If there's genuinely no
  notable takeaway (a flat, unremarkable trend),
  say so plainly ("Net revenue held flat week over week") rather than forcing a dramatic
  claim — the heading must be an accurate read of the data, not a manufactured insight.
- **The in-widget dot legend carries series identification — never restate it as prose.**
  Every legend entry must stand on its own: segment name, then the measure in bold after the
  `|` (`● Tier-1 | D1 retention rate`), **and on a dual-axis chart its axis** (`● DAU | left
  axis`, `● Retained users | right axis`). Because the legend already says which color is
  which and which axis it reads on, a sentence above the chart repeating "Blue is Tier-1, aqua
  is everything else" is redundant restatement and must not be written — it duplicates what the
  reader can see and pads the response. If a legend entry needs a qualifier to be understood,
  **fix the legend entry**; don't add a prose gloss. Anything the legend genuinely cannot carry
  — a population caveat, an exclusion, a thin-sample warning — belongs in the in-widget header's
  definition line. The only response text above the chart is the insight heading.
- **The in-widget legend itself is unskippable on any multi-series chart.** The pattern here
  disables the chart module's built-in legend in favor of the HTML dot legend — which means
  forgetting the dot legend ships a chart with NO legend at all. Hard rule: if the HTML dot
  legend is not rendered for any reason, re-enable the built-in chart legend instead. A
  multi-series widget without a visible legend is a defect, full stop.

## Composing a dashboard

For a "how is [game] performing" view, mirror `analyst-game-performance`'s
visuals-first output, and match the composition order used before: KPI card grid first
(the reader checks the headline numbers before the shape of the trend), then trend
line chart(s), then breakdown bars. Net revenue and gross revenue default to KPI cards
only — don't add a net-vs-gross trend chart unless the user explicitly asks for it (see
Guardrails). Trend charts by default are for whichever other metric the user is actually
asking about (DAU, ROAS, retention, etc.), not an unrequested revenue line. **Split these across separate, small `show_widget`
calls, interleaved with a line or two of text**, rather than one large combined call —
this is the default now, for speed:

```
[response text: what this dashboard covers, period, segment]
[show_widget: KPI card grid only — with its own header block naming the period and segment]
[response text: insight heading only — "**Net revenue dropped 26% MoM, driven by iOS.**"]
[show_widget: in-widget header (metric / scope / definition) + dot legend + single trend line chart]
[response text: insight heading for the next chart, plus any breakdown callout]
[show_widget: in-widget header + dot legend + single breakdown bar chart]
```

One line of response text per chart — the insight heading — and nothing else. Series
identification (including the series↔axis mapping on a dual-axis chart) lives in the widget's
own dot legend, so there is no separate legend sentence to place. If you find yourself writing
"blue is X, orange is Y," delete it and check that the dot legend actually names X and Y.

Each call is small and self-contained (one grid, or one canvas + its own `<script>` tag
loading Chart.js and building just that chart). This means:

- Something renders within a few seconds instead of the user waiting for one large
  KPI-grid-plus-two-charts payload to finish streaming before anything is visible.
- Each chart's `<script>` block only needs its own dataset and config — don't re-declare
  shared *helpers* (formatters, legend builders) across calls. **This does NOT apply to the
  charting library itself: every widget that draws a chart re-includes its own
  `<script src>` loader tag** (see "Loading the library"), because widgets share no JS scope
  and an omitted tag is the `Chart is not defined` error. Keep each one minimal and
  self-contained even if that means a few small duplicated lines, since that's still
  faster than one bloated call.

Only combine KPI cards + a chart into a single call when the dashboard is small enough
(e.g. 2-3 KPIs + one chart) that splitting wouldn't meaningfully speed anything up — use
judgment, but default to splitting for anything larger. What you should never do is go
back to saving each card/chart as its own PNG file.

## Design rules baked into this system

- **Native board frame.** White Widget Bar card, soft double shadow, `#e7e9ee` horizontal
  gridlines only, no chart-junk. Data is the loudest thing on the chart.
- **Restrained, fixed-order categorical palette.** Use the board palette in order — never
  cycle colors like a rainbow, never reassign an entity's color when the data is filtered.
- **Self-labeling.** Widget Bar header (Archivo title + Nunito Sans scope subline) and dot
  legend inside the widget; insight heading — and only the insight heading — in the response
  text above it. Never restate the legend as prose. Full spec under "Labels, always." Also a
  hard rule in the analyst skills.
- **One hover, every series.** Multi-series tooltips are shared/index mode — the reader
  compares series in a single hover, never two. Full spec under "Hover tooltip."
- **Whole numbers for counts, money to the dashboard's rounding.** Use compact formatting
  (`1.24M`, `2.86K`) for large counts and standard currency formatting for money; round
  every number that reaches the screen (`toFixed`/`toLocaleString`) — don't let raw float
  math leak into a label.
- **Actual numbers on every axis.** Never index, normalize, or rescale a series — mismatched
  scales get a dual y-axis (each axis titled + color-matched to its series, series↔axis
  mapping named in the in-widget legend entries) or two separate charts.

See `references/design-tokens.md` for the legacy static-image token values (only relevant if
you're doing the PNG-export fallback below) and the Visualizer's own `chart` module (loaded
via `visualize:read_me`) for the authoritative HTML/Chart.js conventions — CSS variables,
canvas sizing, categorical hex values, accessibility requirements.

## Guardrails

- **Don't plot net revenue and gross revenue as a trend line chart by default.** They belong
  in the KPI card grid as two headline numbers, nothing more. Only add a net-vs-gross trend
  chart if the user explicitly asks to see it over time (e.g. "chart net vs gross revenue",
  "show me the revenue trend") — a request for "a dashboard" or "how is [game] performing"
  is not, by itself, a request for that specific chart.
- **Never present a dashboard, KPI card, or chart as a saved PNG/image file by default** —
  only on explicit request to download/export/save.
- **Never carry `legend: { display: false }` into a PPTX or PDF chart.** That setting is
  correct *here* only because the HTML dot legend replaces it. An exported file has no dot
  legend, so the same setting ships a chart with no legend at all — which is exactly how an
  unreadable deck chart gets built. Exports are `ps-brand-report`'s surface and its
  `chartOptions()` defaults the legend ON; single-series charts opt out explicitly.
- **Never ship a chart without its header block, its in-widget dot legend (multi-series), or
  the insight heading in the response text above it.** Spec: "Labels, always." A bar chart with
  only category names on the x-axis is broken, not minimal.
- **Never restate the legend as prose above the chart.** "Blue is iOS, aqua is Android" is
  redundant with the dot legend the reader is already looking at. Fix an unclear legend entry
  in the widget; don't gloss it in the response text.
- **Never ship a multi-series chart whose tooltip reports only the hovered series.** Shared /
  index-mode tooltips are mandatory — spec: "Hover tooltip." Setting `mode: 'index'` under
  `plugins.tooltip` alone does not satisfy this; the root `interaction` block must match.
- **Never call `new Chart(...)` / `Highcharts.chart(...)` at the top level of a widget's inline
  script, and never assume a library loaded by an earlier `show_widget` call is still available.**
  Both produce `Chart is not defined` and a blank widget. Every chart widget carries its own
  `<script src>` loader tag and binds construction to its `load` event — spec: "Loading the
  library.
- Don't put explanatory prose, takeaways, or section headings inside the widget HTML — only
  the header block belongs there; everything else is response text.
- Don't use relative date language ("last month", "MTD") in a header scope line — always an
  explicit range with the year.
- Don't order bars or rows by something other than the plotted metric without saying so in
  the definition line — readers assume rank follows bar height.
- **Never ship a rate-metric ranking chart (ROAS, retention, Rev/DAU, eCPI, LTV, any ratio)
  without a contribution % label on every bar** and the definition line naming what that %
  is a share of. Spec: "Bar chart." A ROAS ranking whose bars carry only game names lets a
  1.6%-of-spend title read as the portfolio's best performer — that is a defect, not a
  simplification.
- **Never index/rescale/normalize what's measured — plot actual values.** "Indexed to 100"
  charts are banned: they contradict the query results the reader just saw and read as
  manipulated numbers. Mismatched scales → dual y-axis (properly labeled) or two charts.
- Don't repurpose `--text-success`/`--text-danger` as series colors — reserved for deltas.
- Don't invent data to fill a chart — plot only available dates (e.g. unmatured cohorts).
- **Never plot an undelivered trailing day as a data point.** Data is complete only through D-2 by default
  (SR-6, the D-2 completeness rule in `brian-master/references/shared-rules.md`), so a trailing date whose value hasn't posted must be omitted from
  the series — not drawn as a zero or a downward hook, which is the single most misleading mark a trend
  chart can carry. When a date is excluded, say so in the header's definition line ("Aug 9 excluded: spend
  for that date has not posted yet"), so the shortened axis is explained rather than looking like the
  window was chosen arbitrarily.
- This skill styles and delivers visuals only; it never overrides the data-sourcing,
  metric-definition, or net/gross rules in `analyst-game-performance`.

## Legacy PNG export (only if the user explicitly wants a downloadable image)

`scripts/viz_style.py` and `references/design-tokens.md` hold the old matplotlib-based
system (KPI card figures, line/bar charts, dark tooltip callouts) that renders to PNG files
under `/mnt/user-data/outputs/`. Use this path only when the user specifically asks to
"save," "download," or "export" a chart as an image file — otherwise always use the inline
widget path above.
