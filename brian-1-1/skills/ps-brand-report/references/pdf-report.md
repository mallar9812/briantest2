# Building the PDF report

Path: one self-contained HTML file → headless Chromium → PDF. Chromium is the only
renderer used here; it honours `@page`, `print-color-adjust`, CSS grid, and installed
web fonts. wkhtmltopdf silently drops all four — never substitute it.

## 1. Set up

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/setup_fonts.sh
```

## 2. Write the HTML

Link the brand stylesheet by absolute path (Chromium loads it over `file://`):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Word Bingo — Monthly performance review</title>
  <link rel="stylesheet" href="/abs/path/to/skills/ps-brand-report/assets/brand.css">
</head>
<body>
  ...
</body>
</html>
```

If the PDF must survive being moved around before rendering, inline the CSS inside a
`<style>` tag instead — the output is identical.

Use the stylesheet's classes; do not hand-roll inline styles, and never introduce a hex
value that is not in `brand-tokens.md`.

## 3. Section patterns

**Cover** (dark ground, decorative purple display figure is optional):

```html
<div class="cover">
  <p class="wordmark">playsimple</p>
  <p class="eyebrow">Monthly performance review</p>
  <h1>Word Bingo</h1>
  <p class="display-figure">+25%</p>
  <p class="meta">
    <strong>Period</strong> Jul 1 – Jul 31, 2026<br>
    <strong>Owner</strong> Growth Analytics<br>
    <strong>Produced</strong> Aug 7, 2026
  </p>
</div>
```

**Executive summary** — `.lead` paragraph, then `.callout` for the verdict.

**KPI grid** — `.kpi-grid` (add `.cols-3` / `.cols-2` for fewer cards). Feature the
single most important metric with `.kpi.feature` (purple ground) — at most one per grid.

```html
<div class="kpi-grid">
  <div class="kpi feature">
    <p class="kpi-label">Net revenue</p>
    <p class="kpi-value">$839,399</p>
    <p class="delta">-26.0% MoM</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">DAU (avg)</p>
    <p class="kpi-value">412,880</p>
    <p class="delta up">+4.1% MoM</p>
  </div>
</div>
```

**Figure** — every chart sits in a `.figure` with the three-line header. This is not
optional: the chart must be identifiable when screenshotted out of context.

```html
<div class="figure">
  <div class="figure-header">
    <p class="title">Net revenue by day</p>
    <p class="scope">Word Bingo · Jul 1–31, 2026 · all platforms, all countries · USD</p>
    <p class="definition">Gross IAP + ad revenue less store commission, booked on the
      transaction date. Bars ordered chronologically.</p>
  </div>
  <img src="charts/net-revenue.png" alt="Net revenue by day, Jul 1–31 2026, USD">
</div>
```

Scope-line slots that don't apply are **omitted, not filled with a placeholder**. A
retention figure's scope ends at `% of cohort` — never `% of cohort, USD n/a`.

**Table** — `.table`, `.num` on numeric cells, `tr.total` for the summary row.

**Appendix** — wrap in `.appendix`; put metric definitions, query notes, and caveats there.

Force a new page with `<div class="page-break"></div>`.

## 4. Charts

Two options, both fine:

- **Pre-rendered PNG at 3× / ≥300 DPI** (matplotlib, Chart.js in a scratch page, or the
  Visualizer output saved out) referenced with `<img>`. Simplest and most predictable.
  **3× is the floor, not 2×** — a figure block spans ~170mm on A4, and a 2× raster is
  visibly soft at print size and worse once the PDF is screenshotted into Slack.
- **Chart.js drawn in the page.** Load Chart.js, draw into a `<canvas>` inside the
  `.figure`, set `devicePixelRatio: 3` in the chart config, and set
  `window.__reportReady = true` in the final chart's `animation.onComplete`. Disable
  animation (`options.animation = false`) so it settles fast, and raise `--wait-ms` to 3000.

Chart colours come from `SERIES` in `brand-tokens.md`: slot 1 is always Playsimple
Purple, and an entity keeps its slot across every chart in the report. Gridlines Mauve
`#D4CED7`, axis labels Violet `#4C3255`, no chart junk.

### Rules every figure owes, whichever path

These match the deck's rules in `pptx-report.md` — one policy across both formats, so a
PDF and a deck of the same report say the same thing the same way.

- **Round the values, don't just format the labels.** Rates and percentages 1 decimal
  (`27.9%`), money ≥ $10k whole with separators (`$49.4M`), per-user money 2 decimals
  (`$0.16`), counts whole (`34.6M`). A data label carrying a raw float
  (`31.126578162`) is a defect. Drop labels entirely if they collide at final size.
- **Category labels are real names, never ordinals.** `D1 · D7 · D30`,
  `Apr 2025 … Jun 2026` — never `1 2 3 … 15`. Over ~12 categories, thin or rotate them.
- **Every multi-series figure carries a visible legend**, and each entry names its metric
  and units — "UA spend (USD, left axis)", not "spend".
- **The subject metric takes Playsimple Purple.** Mauve and Lavender are neutrals for
  reference lines and remainders; they never carry the chart's subject.

### Dual axis — allowed, with one set of gridlines

Mismatched scales (revenue vs DAU, spend vs installs) get **either** a properly-built dual
y-axis **or** two stacked figures. Never index, normalize or rescale a series to force it
onto one axis — that changes what is measured (SR-8) and reads as manipulated numbers.

A dual-axis figure is legal only when all five hold:

1. **One set of gridlines.** Both axes pinned to the same tick count so their major units
   coincide; gridlines drawn from the left axis only. Two crossing sets of horizontal rules
   is the defect this rule exists to prevent.
2. Both axes titled with their units.
3. Each legend entry names its axis.
4. Axis label colour matches its series colour.
5. The subject metric is in Playsimple Purple.

In Chart.js that means setting `min`, `max` and `ticks.stepSize` explicitly on both scales
so `(max − min) / stepSize` is identical, and `grid: { display: false }` on the right-hand
scale:

```js
scales: {
  y:  { min: 0, max: 25e6, ticks: { stepSize: 5e6 }, grid: { color: '#D4CED7' },
        title: { display: true, text: 'UA spend (USD)' } },
  y1: { min: 0, max: 15e6, ticks: { stepSize: 3e6 }, grid: { display: false },
        position: 'right', title: { display: true, text: 'Installs (users)' } },
}
```

Both scales here have five intervals, so one set of rules serves both.

## 5. Render

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/html_to_pdf.py \
  report.html report.pdf --wait-ms 2000
```

## 6. Check before delivering

- Open the PDF and confirm: cover is dark purple, headings are MuseoModerno Bold with
  the short M / W / w, body is Poppins, figures and chart labels are Zalando Sans (or MTG
  Display), no Times New Roman anywhere — a serif means the font install failed.
- No orphaned figure headers (a header on one page, chart on the next). `.figure` and
  `.kpi` already set `page-break-inside: avoid`; if a block still splits, move it behind
  a `.page-break`.
- **Zoom every figure to 100% and read it**: real category labels, ≤1 decimal on data
  labels, one set of gridlines, a legend on anything multi-series, no soft/blurry raster.
- Every chart has all three header lines.
- Every delta names its comparison basis.
- Colour count: purple family dominates; extended palette appears only inside charts.
