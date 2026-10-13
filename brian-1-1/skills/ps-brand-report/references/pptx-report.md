# Building the PPTX report deck

Generated with `pptxgenjs` on top of `assets/ps_brand.js`, which carries the palette,
type scale, and slide builders. Read the `pptx` skill's gotcha list first — it is
authoritative on the library's footguns. The most load-bearing ones here:

- Hex values carry **no `#` and no alpha** — `'A00FFF'`. Either corrupts the file.
- `pptx.layout = 'LAYOUT_WIDE'` must be set **before** the first slide (`newDeck()` does it).
- pptxgenjs mutates options objects in place — never share one across two `add*` calls.
- `rectRadius` works on `ROUNDED_RECTANGLE` only.
- `charSpacing`, not `letterSpacing`.
- On stacked bars, `dataLabelPosition` must be `ctr` / `inEnd` / `inBase` — `outEnd` corrupts.

## Generator skeleton

```js
const PS = require('/abs/path/to/skills/ps-brand-report/assets/ps_brand.js');

const pptx = PS.newDeck({ title: 'Word Bingo — July 2026 review', author: 'Growth Analytics' });

PS.coverSlide(pptx, {
  title: 'Word Bingo\nJuly performance review',
  period: 'Jul 1 – Jul 31, 2026',
  owner: 'Growth Analytics',
  date: 'Aug 7, 2026',
  figure: '+25%',            // optional decorative display figure
});

PS.sectionDivider(pptx, { number: '01', title: 'Where we landed', note: 'Headline KPIs and the verdict.' });

PS.kpiSlide(pptx, {
  title: 'July at a glance',
  scope: 'Word Bingo · Jul 1–31, 2026 · all platforms, all countries · USD',
  kpis: [
    { label: 'Net revenue', value: '$839,399', delta: '-26.0% MoM', dir: 'down', feature: true },
    { label: 'DAU (avg)',   value: '412,880',  delta: '+4.1% MoM',  dir: 'up' },
    { label: 'Rev / DAU',   value: '$0.065',   delta: '-28.9% MoM', dir: 'down' },
    { label: 'D1 retention',value: '38.4%',    delta: '+0.6pp MoM', dir: 'up' },
  ],
  note: 'Deltas compare July 2026 with June 2026. Revenue is net of store commission.',
});

PS.chartSlide(pptx, {
  title: 'Net revenue by day',
  scope: 'Word Bingo · Jul 1–31, 2026 · all platforms · USD',
  definition: 'Gross IAP + ad revenue less store commission, booked on the transaction date.',
  chart: {
    type: pptx.ChartType.line,
    data: [{ name: 'Net revenue (USD)', labels: dayLabels, values: PS.roundValues(revenue, 0) }],
    options: { lineDataSymbol: 'none', lineSize: 2, showLegend: false,
               dataLabelFormatCode: PS.FMT.money, valAxisLabelFormatCode: PS.FMT.moneyM },
  },
  insight: 'Revenue fell through the second week as iOS spend was cut; DAU held, so the drop is monetisation, not audience.',
});

PS.tableSlide(pptx, {
  title: 'Network breakdown',
  scope: 'Word Bingo · Jul 1–31, 2026 · UA networks · USD',
  rows: [
    ['Network', 'Spend', 'Installs', 'eCPI', 'D7 ROAS'],
    ['Meta', '$180,400', '92,100', '$1.96', '14.2%'],
    ['Google', '$121,900', '70,400', '$1.73', '11.8%'],
    ['Total', '$302,300', '162,500', '$1.86', '13.3%'],
  ],
  colW: [3.4, 2.1, 2.1, 2.1, 2.3],
  totalRow: true,
});

PS.closingSlide(pptx, {
  headline: 'Next steps',
  lines: ['Reinstate iOS spend at 60% of June level — Growth, w/c Aug 10',
          'Rerun the D7 ROAS check after two weeks — Analytics'],
});

pptx.writeFile({ fileName: 'word-bingo-july-2026.pptx' });
```

Then always, both of these:

```bash
python /mnt/skills/public/pptx/scripts/office/validate.py word-bingo-july-2026.pptx
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ps-brand-report/scripts/validate_charts.py word-bingo-july-2026.pptx
```

`validate.py` checks the file isn't corrupt. `validate_charts.py` checks the charts are
*readable* — ordinal axes, missing legends, unformatted floats and misaligned dual axes all
produce a valid file. A non-zero exit from either is blocking.

## Slide grammar

| Slide | Ground | Builder |
|---|---|---|
| Cover | Dark Purple | `coverSlide` |
| Section divider | Dark Purple | `sectionDivider` |
| KPI overview | White | `kpiSlide` |
| Chart (native) | White | `chartSlide` |
| Chart (pre-rendered image) | White | `chartImageSlide` |
| Table | White | `tableSlide` |
| Narrative / recommendations | White | `contentSlide` + your own text boxes |
| Closing | Dark Purple | `closingSlide` |

Grounds alternate deliberately — dark at the seams (cover, dividers, close), white for
content. Do not scatter dark and light content slides at random, and do not use a purple
ground for a full content slide; Playsimple Purple on a whole slide is a hero moment, not
a working surface.

## Charts in the deck

Series colours come from `PS.SERIES` in fixed order. Every chart slide states `title`,
`scope`, and `definition`. `insight` is optional but strongly preferred — it is the
takeaway, not a restatement of the axis labels, and it is **one claim with its number,
≤35 words**. Longer argument belongs on a narrative slide.

`ps_brand.js` enforces most of what follows at build time: `chartSlide` runs
`assertChartIsReadable` and **throws** rather than shipping a chart that breaks these
rules. If a build fails with a `ps_brand [chart]:` error, fix the chart — do not bypass
the assertion.

### Native chart or pre-rendered image — decide by destination

**Google Slides rasterises native charts.** Google's .pptx importer converts every
`addChart` object into a static bitmap at screen resolution, so a technically-correct
native chart arrives soft and blurry — the single most common complaint about these decks.

- **Deck stays in PowerPoint / Keynote** → keep charts **native** (`chartSlide`). They
  stay vector, and the recipient can click into the data.
- **Deck will be opened in Google Slides** (the default at Playsimple) → render each chart
  yourself at **3× / ≥300 DPI** (Chart.js in headless Chromium, or matplotlib via
  `game-viz-design/scripts/viz_style.py`) and place it with `chartImageSlide`. You control
  the raster instead of Google's importer.
- Say which path was used in the delivery message, and never mix the two in one deck.

A pre-rendered chart still owes everything below — the raster is a delivery choice, not a
licence to skip the labels.

### Number formatting — round the array, not just the label

**Every value passed into a chart is pre-rounded to its display precision, AND carries a
format code.** Format codes alone are not enough: Google Slides' importer discards
`dataLabelFormatCode`, and the raw float reappears (`31.126578162` on a retention label).
`PS.roundValues(values, decimals)` is the belt to the format code's braces.

| Metric family | Decimals | Format code |
|---|---|---|
| Rates, percentages, retention, ROAS, share | **1** (`27.9%`) | `PS.FMT.rate` |
| Money, aggregates ≥ $10k | 0, thousands separators (`$49,371,204` / `$49.4M`) | `PS.FMT.money` / `PS.FMT.moneyM` |
| Money, per-user (Rev/DAU, eCPI, CPI) | 2 (`$0.16`) | `PS.FMT.moneyC` |
| Counts (DAU, installs, sessions) | 0 (`34,632,118` / `34.6M`) | `PS.FMT.count` / `PS.FMT.countM` |

**A data label with more than one decimal place is a defect.** So is an axis label with a
raw float. If SR-10 and this table disagree for a chart label, this table wins — SR-10
governs prose.

**Turn data labels off when they collide.** Three series × three categories overlapped
illegibly in a retention chart. If labels touch at final size, drop `showValue` and let
the axis carry the values; the reader has the table for exact figures.

### Category labels are real names, never ordinals

`labels: ['D1','D7','D30']`, `labels: ['Apr 2025', …, 'Jun 2026']` — never `[1,2,3]`,
never omitted, and **on a combo chart every series carries its own identical `labels`
array** or pptxgenjs falls back to ordinal indices. An axis reading `1 2 3 … 15` forces
the reader to map positions to the definition line by hand; treat it as unshippable.

Over ~12 categories, thin the labels with `catAxisLabelFrequency` or rotate to 45°
(`catAxisLabelRotate: -45`) — never shrink below 10pt.

### Legends are mandatory on anything multi-series

`chartOptions()` now defaults `showLegend: true`. **Single-series** charts pass
`showLegend: false` explicitly; multi-series charts never do. The widget system
(`game-viz-design`) switches the chart legend off because it substitutes an HTML dot
legend — a .pptx has no such substitute, so copying that setting here ships a chart with
no legend at all.

**Series names are the legend, so they carry the metric and its units** — `'UA spend
(USD, left axis)'`, not `'Series 1'` and not `'spend'`. The scope line above the chart is
not a substitute: a screenshot of the plot area has to stand alone.

### Dual axis — legal only with one set of gridlines

Two value axes with independently chosen bounds draw two independent sets of horizontal
rules that cross each other. That is what makes a dual-axis chart look broken, and it is
avoidable: pin both axes to the same tick count so their major units coincide, and draw
gridlines from the primary axis only.

Build it with `PS.dualAxis()`, which does exactly that and returns the `valAxes`/`catAxes`
pair for the chart's **global** options:

```js
const spend = PS.roundValues(spendRaw, 0);
const installs = PS.roundValues(installRaw, 0);

PS.chartSlide(pptx, {
  title: 'Spend held while installs fell',
  scope: 'Playsimple portfolio — internal · Apr 2025 – Jun 2026 · monthly',
  definition: 'Bars: marketing spend booked on the install date. Line: cohort installs on the same date.',
  axes: PS.dualAxis({
    leftMax:  Math.max(...spend),    leftTitle:  'UA spend (USD)',    leftFormat:  PS.FMT.moneyM,
    rightMax: Math.max(...installs), rightTitle: 'Installs (users)',  rightFormat: PS.FMT.countM,
    ticks: 5,
  }),
  chart: [
    { type: pptx.ChartType.bar,
      data: [{ name: 'UA spend (USD, left axis)', labels: months, values: spend }] },
    { type: pptx.ChartType.line,
      data: [{ name: 'Installs (users, right axis)', labels: months, values: installs }],
      options: { secondaryValAxis: true, secondaryCatAxis: true, lineDataSymbol: 'none', lineSize: 2 } },
  ],
});
```

Five conditions, all enforced by `assertChartIsReadable`:

1. **One set of gridlines** — same tick count on both axes, `valGridLine: { style: 'none' }`
   on the secondary. Two crossing sets of rules is a defect, not a style.
2. **Both axes titled with units** — "UA spend (USD)" left, "Installs (users)" right.
3. **Each series name states its axis** — "…(USD, left axis)" / "…(users, right axis)".
4. **Axis label colour matches its series colour**, so scale maps to mark without reading.
5. **The subject metric takes Playsimple Purple** (`SERIES[0]`). Mauve and Lavender are
   neutrals for reference lines and remainders — they never carry the subject. A chart
   whose subject (DAU) renders in grey while a derived ratio (Rev/DAU) takes the brand
   colour reads backwards.

If a chart can't meet all five, **use two stacked charts** — never index or rescale a
series to force it onto one axis (SR-8). Two clear charts beat one clever one.

A combo series on a secondary axis needs **both** `valAxes` and `catAxes` declared with two
entries each, or PowerPoint discards the chart and calls the file corrupt. `PS.dualAxis()`
returns both.

**The brand frame belongs in the global options object on a combo chart.** Per-series
options carry only chart-type specifics (`secondaryValAxis`, `lineSize`, `barDir`).
`chartSlide` handles this; if you call `addChart` directly with an array of specs and pass
only the plot area as the second argument, you silently lose the palette, fonts,
gridlines, number formats and legend on that chart.

### Scope-line slots

Slots that don't apply are **omitted, not filled with a placeholder**. A retention chart's
scope ends at `% of cohort` — never `% of cohort, USD n/a`.

## Density

- One idea per slide. If a slide needs more than ~40 words of body copy, split it.
- Insight panel: one claim with its number, ≤35 words.
- Max 5 KPI cards per row, 10 per slide.
- Max ~8 table rows per slide; continue on a second slide rather than shrinking type.
- Body text never smaller than 12pt; captions never smaller than 10pt.

## Fonts

`ps_brand.js` exports three faces and assigns each a job. Use the constants, never a
literal font name:

- `HEAD_FACE` — **MuseoModerno**. Cover title, slide titles, section dividers, closing
  headline, wordmark. Nothing below 18pt.
- `TEXT_FACE` — **Poppins**. Body, bullets, sub-heads, table text, captions, KPI labels.
- `VIZ_FACE` — **Zalando Sans**. KPI values, deltas, chart axis and data labels,
  legends, and numeric table cells (`tableSlide` routes these automatically by matching
  cells that start with a digit, currency symbol or sign).

MuseoModerno ships as the Playsimple cut with short M / W / w — see SKILL.md. Stylistic
sets cannot be applied from a .pptx, so the swap lives in the installed font file. If
titles render with wide decorative arches, the wrong MuseoModerno is installed: re-run
`setup_fonts.sh` after removing the stock family.

Both MuseoModerno and Poppins run wider than Inter, so the display scale is stepped down
(cover 36pt, slide title 26pt, KPI value 30pt) and `kpiRow` drops the value to 27pt at
four cards and 24pt at five. If you add a longer value string, check the thumbnail grid
rather than assuming it fits.

**Shipping caveat.** A .pptx stores font names, not fonts. A recipient without these
three sees one substituted face everywhere. Send the PDF, or ship the .ttf files with
the deck, and say which in the delivery message.

## Check before delivering

- `validate.py` clean.
- `validate_charts.py` clean — no ordinal axes, no unformatted data labels, no
  multi-series chart without a legend, no misaligned dual axes, no off-palette hex.
- Open the thumbnail grid (`python /mnt/skills/public/pptx/scripts/thumbnail.py deck.pptx ps-report-thumbs`)
  and read it **at 100%**, not as thumbnails:
  - every x-axis label is a real name, not `1 2 3`
  - every data label ≤1 decimal place
  - one set of gridlines per chart
  - every multi-series chart has a legend naming units and axis
  - no text overflowing a card, no chart bleeding off the canvas, grounds alternating
- Every chart has title, scope, definition.
- Deltas coloured only with `#2E7D32` / `#8C0E0E`, nowhere else in the deck.
