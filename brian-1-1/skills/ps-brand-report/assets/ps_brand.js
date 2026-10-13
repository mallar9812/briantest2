/**
 * Playsimple standard report — pptxgenjs brand module.
 * Brand Playbook v1.0. See references/brand-tokens.md.
 *
 *   const PS = require('<plugin>/skills/ps-brand-report/assets/ps_brand.js');
 *   const pptx = PS.newDeck();
 *   PS.coverSlide(pptx, {...});
 *
 * pptxgenjs hex values carry NO '#' and NO alpha — both corrupt the file.
 */

const pptxgen = require('pptxgenjs');

/* ---------- palette ---------- */

const C = {
  purple: 'A00FFF',
  dark: '2A0B35',
  white: 'FFFFFF',

  p600: '440E6F',
  p500: '6200B1',
  p400: 'A00FFF',
  p300: 'C782FF',
  p200: 'DFB5FF',
  p100: 'F7EBFF',

  burgundy: '4D0808',
  crimson: '8C0E0E',
  coral: 'FF8787',
  blush: 'FFD1D1',
  petal: 'FFEEEE',
  violet: '4C3255',
  lilac: 'A69CED',
  lavender: 'ACA0B0',
  mauve: 'D4CED7',
  mist: 'F0EDF1',

  up: '2E7D32',
  down: '8C0E0E',
  flat: 'ACA0B0',
};

/** Fixed categorical order. Slot 1 is always Playsimple Purple. */
const SERIES = [C.purple, C.violet, C.lilac, C.p500, C.lavender, C.coral, C.p600, C.mauve];

/**
 * Neutrals. These may tint a reference line, a prior-period ghost series, or a
 * "rest of portfolio" remainder — they may NEVER carry the chart's subject metric.
 * A chart whose subject renders in grey while a derived ratio takes the brand colour
 * reads backwards; `assertChartIsReadable` rejects it.
 */
const NEUTRALS = [C.lavender, C.mauve, C.mist];

/* ---------- type ---------- */

/* Three faces, each with one job — see SKILL.md "Fonts".
     HEAD_FACE  MuseoModerno — headings only: cover title, slide titles, section
                dividers, closing headline, wordmark. Never below 18pt.
     TEXT_FACE  Poppins      — all content: body, bullets, tables, captions, KPI labels.
     VIZ_FACE   Zalando Sans — everything numeric or chart-borne: KPI values, deltas,
                axis labels, data labels, legends.
   Inter stays the fallback in the stack for any machine missing the three.
   DISPLAY_FACE is retained as an alias so older callers keep working. */
const HEAD_FACE = 'MuseoModerno';
const TEXT_FACE = 'Poppins';
const VIZ_FACE = 'Zalando Sans';
const DISPLAY_FACE = HEAD_FACE;

const T = {
  // MuseoModerno and Poppins both run wider than Inter — display sizes are stepped
  // down from the old Inter-only scale so titles and KPI values still fit one line.
  coverTitle: { fontFace: HEAD_FACE, fontSize: 36, bold: true, charSpacing: -0.8, lineSpacing: 36 },
  slideTitle: { fontFace: HEAD_FACE, fontSize: 26, bold: true, charSpacing: -0.6, lineSpacing: 26 },
  // Sub-heads sit below MuseoModerno's legibility floor — Poppins SemiBold instead.
  subhead: { fontFace: TEXT_FACE, fontSize: 15, bold: true, charSpacing: -0.3 },
  body: { fontFace: TEXT_FACE, fontSize: 14, charSpacing: -0.1 },
  caption: { fontFace: TEXT_FACE, fontSize: 10 },
  kpiValue: { fontFace: VIZ_FACE, fontSize: 30, bold: true, charSpacing: -0.6 },
  kpiLabel: { fontFace: TEXT_FACE, fontSize: 11 },
};

const RADIUS = 0.06; // rectRadius on ROUNDED_RECTANGLE ≈ 16px at deck scale
const W = 13.333;
const H = 7.5;
const M = 0.65; // side margin

/* ---------- numbers: round before PowerPoint sees them ---------- */

/**
 * Round every value in a series to its display precision.
 *
 * A format code alone is NOT enough. `dataLabelFormatCode` is a PowerPoint
 * instruction, and Google Slides' .pptx importer discards it — at which point the
 * raw float reappears as `31.126578162` on the label. Rounding the array is what
 * survives the round-trip. Do both.
 *
 *   FMT.rate  →  1 decimal   (retention, ROAS, share)
 *   FMT.money →  whole dollars for aggregates ≥ $10k
 *   FMT.count →  whole users
 */
function roundValues(values, decimals = 1) {
  return values.map(v =>
    (v === null || v === undefined || Number.isNaN(Number(v)))
      ? null
      : Number(Number(v).toFixed(decimals)));
}

/** Number format codes by metric family. Pass one as `dataLabelFormatCode`. */
const FMT = {
  rate: '#,##0.0"%"',   // 27.9%
  rate2: '#,##0.00"%"',
  money: '$#,##0',      // $49,371,204
  moneyM: '$#,##0.0,,"M"', // $49.4M
  moneyC: '$#,##0.00',  // $0.16  — small per-user figures
  count: '#,##0',       // 34,632,118
  countM: '#,##0.0,,"M"', // 34.6M
  countK: '#,##0.0,"K"',
};

/**
 * A "nice" axis maximum: rounds up to a clean multiple of the tick count so that
 * `majorUnit` divides evenly and gridlines land on round numbers.
 *
 * The step ladder is deliberately fine-grained. A coarse ladder (1·2·5·10) rounds a
 * 15.2M series up to a 25M axis, which squashes the whole line into the bottom half of
 * the plot — the data ends up occupying 60% of the height it should. Every rung here
 * still divides into readable gridline labels.
 */
const NICE_STEPS = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];

function niceMax(max, ticks = 5) {
  const m = Number(max);
  if (!(m > 0)) return ticks;
  const raw = m / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (NICE_STEPS.find(s => norm <= s + 1e-9) || 10) * mag;
  return step * ticks;
}

/* ---------- deck ---------- */

function newDeck(meta = {}) {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE'; // must be set before any slide is added
  pptx.author = meta.author || 'Playsimple';
  pptx.company = 'Playsimple Games';
  pptx.title = meta.title || 'Playsimple report';
  return pptx;
}

function darkSlide(pptx) {
  const s = pptx.addSlide();
  s.background = { color: C.dark };
  return s;
}

function lightSlide(pptx) {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  return s;
}

/** Lowercase wordmark. Swap for addImage() when a logo asset is supplied. */
function wordmark(slide, { x = M, y = 0.4, color = C.white, size = 16 } = {}) {
  slide.addText('playsimple', {
    x, y, w: 3, h: 0.4, margin: 0,
    fontFace: DISPLAY_FACE, fontSize: size, bold: true, charSpacing: -0.6, color,
  });
}

/* ---------- slide builders ---------- */

/** Cover: white + decorative purple display figure on dark ground. */
function coverSlide(pptx, { title, period, owner, date, figure }) {
  const s = darkSlide(pptx);
  wordmark(s);

  s.addText(title, {
    x: M, y: 2.0, w: W - M * 2 - 1.5, h: 2.2, margin: 0,
    color: C.white, valign: 'bottom', ...T.coverTitle,
  });

  if (figure) {
    // Purple on dark purple — decorative display only, never body text.
    s.addText(figure, {
      x: W - M - 4.6, y: 3.7, w: 4.6, h: 2.4, margin: 0, align: 'right',
      fontFace: VIZ_FACE, fontSize: 66, bold: true, charSpacing: -1.5, color: C.purple,
    });
  }

  const meta = [period, owner, date].filter(Boolean).join('   ·   ');
  s.addText(meta, {
    x: M, y: H - 1.0, w: W - M * 2, h: 0.4, margin: 0,
    color: C.mauve, ...T.caption,
  });
  return s;
}

function sectionDivider(pptx, { number, title, note }) {
  const s = darkSlide(pptx);
  if (number) {
    s.addText(String(number), {
      x: M, y: 2.2, w: 2, h: 0.6, margin: 0,
      fontFace: VIZ_FACE, fontSize: 12, color: C.p300,
    });
  }
  s.addText(title, {
    x: M, y: 2.8, w: W - M * 2 - 2, h: 1.6, margin: 0,
    color: C.white, ...T.slideTitle, fontSize: 31,
  });
  if (note) {
    s.addText(note, {
      x: M, y: 4.5, w: 7.5, h: 1.0, margin: 0, color: C.mauve, ...T.body, fontSize: 13,
    });
  }
  return s;
}

/** Standard light content slide with title + optional scope line. */
function contentSlide(pptx, { title, scope }) {
  const s = lightSlide(pptx);
  s.addText(title, {
    x: M, y: 0.5, w: W - M * 2, h: 0.75, margin: 0, color: C.dark, ...T.slideTitle,
  });
  if (scope) {
    s.addText(scope, {
      x: M, y: 1.24, w: W - M * 2, h: 0.3, margin: 0, color: C.violet, ...T.caption,
    });
  }
  s.addShape(pptx.ShapeType.line, {
    x: M, y: 1.62, w: W - M * 2, h: 0,
    line: { color: C.mauve, width: 1 },
  });
  return s;
}

/**
 * KPI card row. kpis: [{label, value, delta, dir: 'up'|'down'|'flat', feature}]
 * Max 5 per row for legibility.
 */
function kpiRow(pptx, slide, kpis, { y = 1.95, h = 1.7 } = {}) {
  const gap = 0.25;
  const n = kpis.length;
  const w = (W - M * 2 - gap * (n - 1)) / n;

  kpis.forEach((k, i) => {
    const x = M + i * (w + gap);
    slide.addShape(pptx.ShapeType.roundRect, {
      x, y, w, h,
      rectRadius: RADIUS,
      fill: { color: k.feature ? C.purple : C.mist },
      line: { color: k.feature ? C.purple : C.mist, width: 0 },
    });
    slide.addText(k.label, {
      x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.3, margin: 0,
      color: k.feature ? C.white : C.violet, ...T.kpiLabel,
    });
    // Step the value down as columns tighten so long values never wrap.
    const vSize = n >= 5 ? 24 : (n === 4 ? 27 : T.kpiValue.fontSize);
    slide.addText(String(k.value), {
      x: x + 0.25, y: y + 0.52, w: w - 0.5, h: 0.62, margin: 0,
      color: k.feature ? C.white : C.dark, ...T.kpiValue, fontSize: vSize,
    });
    if (k.delta) {
      slide.addText(k.delta, {
        x: x + 0.25, y: y + 1.18, w: w - 0.5, h: 0.3, margin: 0,
        fontFace: VIZ_FACE, fontSize: 11, bold: true,
        color: k.feature ? C.white : (C[k.dir || 'flat'] || C.flat),
      });
    }
  });
  return slide;
}

function kpiSlide(pptx, { title, scope, kpis, note }) {
  const s = contentSlide(pptx, { title, scope });
  kpiRow(pptx, s, kpis.slice(0, 5));
  if (kpis.length > 5) kpiRow(pptx, s, kpis.slice(5, 10), { y: 3.85 });
  if (note) {
    s.addText(note, {
      x: M, y: H - 1.1, w: W - M * 2, h: 0.6, margin: 0, color: C.violet, ...T.caption,
    });
  }
  return s;
}

/**
 * Quiet, on-brand chart frame. Merge over the top of your own chart options.
 *
 * Two defaults here are load-bearing and were previously wrong:
 *
 *  - `showLegend` is TRUE. The widget system (`game-viz-design`) turns the chart
 *    legend off because it substitutes an HTML dot legend. A .pptx has no such
 *    substitute, so `showLegend: false` on a multi-series chart ships a chart with
 *    NO legend at all. Single-series callers pass `showLegend: false` explicitly.
 *  - Number formats are always set. With no `dataLabelFormatCode`, PowerPoint falls
 *    back to the General format and prints the raw float (`31.126578162`).
 *    Override per metric with `FMT.*`; also pre-round the array (`roundValues`).
 */
function chartOptions(extra = {}) {
  return {
    chartColors: SERIES,
    showTitle: false,
    showLegend: true,
    legendPos: 'b',
    legendFontFace: VIZ_FACE,
    legendFontSize: 10,
    legendColor: C.violet,
    catAxisLabelColor: C.violet,
    valAxisLabelColor: C.violet,
    catAxisLabelFontFace: VIZ_FACE,
    valAxisLabelFontFace: VIZ_FACE,
    catAxisLabelFontSize: 10,
    valAxisLabelFontSize: 10,
    catAxisLineShow: false,
    valAxisLineShow: false,
    valGridLine: { color: C.mauve, size: 1, style: 'solid' },
    catGridLine: { style: 'none' },
    dataLabelColor: C.dark,
    dataLabelFontFace: VIZ_FACE,
    dataLabelFontSize: 10,
    dataLabelFormatCode: FMT.count,
    valAxisLabelFormatCode: FMT.count,
    ...extra,
  };
}

/**
 * Dual-axis config with ONE set of gridlines.
 *
 * The defect this exists to prevent: two value axes with independently chosen
 * bounds draw two independent sets of horizontal rules, which cross each other and
 * make the chart unreadable. Both axes are pinned to the same tick count here, so
 * their major units land on the same rules — and only the primary axis draws them.
 *
 * Returns the `valAxes` / `catAxes` pair to spread into the chart's GLOBAL options.
 * PowerPoint discards a secondary-axis chart unless `catAxes` also has two entries.
 *
 *   const axes = PS.dualAxis({
 *     leftMax:  Math.max(...spend),  leftTitle:  'UA spend (USD)',  leftFormat: PS.FMT.moneyM,
 *     rightMax: Math.max(...installs), rightTitle: 'Installs (users)', rightFormat: PS.FMT.countM,
 *   });
 */
function dualAxis({
  leftMax, rightMax,
  leftTitle, rightTitle,
  ticks = 5,
  leftFormat = FMT.count, rightFormat = FMT.count,
  leftColor = SERIES[0], rightColor = SERIES[1],
} = {}) {
  const lMax = niceMax(leftMax, ticks);
  const rMax = niceMax(rightMax, ticks);
  return {
    valAxes: [
      {
        showValAxisTitle: !!leftTitle,
        valAxisTitle: leftTitle,
        valAxisTitleColor: leftColor,
        valAxisTitleFontFace: TEXT_FACE,
        valAxisTitleFontSize: 10,
        valAxisMinVal: 0,
        valAxisMaxVal: lMax,
        valAxisMajorUnit: lMax / ticks,
        valAxisLabelFormatCode: leftFormat,
        valAxisLabelColor: leftColor,
        valAxisLabelFontFace: VIZ_FACE,
        valAxisLabelFontSize: 10,
        valAxisLineShow: false,
        valGridLine: { color: C.mauve, size: 1, style: 'solid' },
      },
      {
        showValAxisTitle: !!rightTitle,
        valAxisTitle: rightTitle,
        valAxisTitleColor: rightColor,
        valAxisTitleFontFace: TEXT_FACE,
        valAxisTitleFontSize: 10,
        valAxisMinVal: 0,
        valAxisMaxVal: rMax,
        valAxisMajorUnit: rMax / ticks,
        valAxisLabelFormatCode: rightFormat,
        valAxisLabelColor: rightColor,
        valAxisLabelFontFace: VIZ_FACE,
        valAxisLabelFontSize: 10,
        valAxisLineShow: false,
        valGridLine: { style: 'none' }, // one set of rules only — see above
      },
    ],
    catAxes: [
      {
        catAxisLabelColor: C.violet,
        catAxisLabelFontFace: VIZ_FACE,
        catAxisLabelFontSize: 10,
        catAxisLineShow: false,
      },
      { catAxisHidden: true },
    ],
  };
}

/**
 * Pre-flight gate. Throws rather than shipping an unreadable chart, because every
 * failure below is silent: the deck builds, validates, and looks plausible in a
 * thumbnail. Cheaper to fail here than in a review.
 */
function assertChartIsReadable(specs, opts, ctx = 'chart') {
  const allSeries = specs.reduce((acc, s) => acc.concat(s.data || []), []);
  const first = allSeries[0];

  if (!first) throw new Error(`ps_brand [${ctx}]: chart has no series data.`);

  const labels = first.labels;
  if (!labels || !labels.length) {
    throw new Error(
      `ps_brand [${ctx}]: no category labels. pptxgenjs falls back to ordinals (1,2,3…). ` +
      `Pass real names: labels: ['D1','D7','D30'] or ['Apr 2025',…,'Jun 2026'].`);
  }
  if (labels.every(l => /^\d+$/.test(String(l).trim()))) {
    throw new Error(
      `ps_brand [${ctx}]: category labels are ordinals (${labels.slice(0, 4).join(', ')}…). ` +
      `An axis reading 1 2 3 forces the reader to map positions to the definition line by hand.`);
  }
  allSeries.forEach(ser => {
    if (!ser.labels || ser.labels.length !== labels.length) {
      throw new Error(
        `ps_brand [${ctx}]: series "${ser.name || '(unnamed)'}" is missing its own labels array ` +
        `(or its length differs). On a combo chart EVERY series carries the identical labels array, ` +
        `or pptxgenjs falls back to ordinal indices.`);
    }
    if (!ser.name) {
      throw new Error(`ps_brand [${ctx}]: every series needs a name — it is the legend entry.`);
    }
  });

  if (allSeries.length > 1 && opts.showLegend === false) {
    throw new Error(
      `ps_brand [${ctx}]: multi-series chart with showLegend:false. A report has no HTML dot ` +
      `legend to fall back on, so this ships a chart with no legend at all.`);
  }

  // A dual-axis chart must name its axes and its units in the legend entries.
  if (opts.valAxes && opts.valAxes.length === 2) {
    const titled = opts.valAxes.every(a => a.valAxisTitle);
    if (!titled) {
      throw new Error(`ps_brand [${ctx}]: dual-axis chart with an untitled axis — each axis states its units.`);
    }
    const aligned = opts.valAxes.every(a =>
      a.valAxisMaxVal !== undefined && a.valAxisMajorUnit !== undefined);
    if (!aligned) {
      throw new Error(
        `ps_brand [${ctx}]: dual-axis chart without pinned bounds. Build it with PS.dualAxis() so ` +
        `both axes share a tick count and produce ONE set of gridlines.`);
    }
    const intervals = opts.valAxes.map(a =>
      Math.round((a.valAxisMaxVal - (a.valAxisMinVal || 0)) / a.valAxisMajorUnit));
    if (intervals[0] !== intervals[1]) {
      throw new Error(
        `ps_brand [${ctx}]: axes have ${intervals[0]} and ${intervals[1]} intervals — their gridlines ` +
        `will not coincide. Same tick count on both.`);
    }
    const named = allSeries.every(s => /left|right/i.test(s.name));
    if (!named) {
      throw new Error(
        `ps_brand [${ctx}]: on a dual-axis chart every series name states its axis, e.g. ` +
        `"UA spend (USD, left axis)". The scope line is not a substitute for the legend.`);
    }
  }

  // The subject metric takes Playsimple Purple; neutrals never carry it.
  const colors = opts.chartColors || SERIES;
  if (NEUTRALS.includes(colors[0])) {
    throw new Error(
      `ps_brand [${ctx}]: series slot 1 is a neutral (${colors[0]}). The chart's subject metric ` +
      `takes Playsimple Purple; Mauve/Lavender are for reference lines and remainders.`);
  }
}

/**
 * One chart per slide. `definition` is mandatory — every chart states what it counts.
 * chart: { type, data, options } (or an array for combos).
 *
 * `axes` is the PS.dualAxis() result, spread into the chart's global options.
 */
function chartSlide(pptx, { title, scope, definition, chart, axes, insight, options }) {
  const s = contentSlide(pptx, { title, scope });
  if (definition) {
    s.addText(definition, {
      x: M, y: 1.72, w: W - M * 2, h: 0.3, margin: 0, color: C.violet, ...T.caption,
    });
  }
  const specs = Array.isArray(chart) ? chart : [chart];
  const area = { x: M, y: 2.15, w: insight ? W - M * 2 - 3.6 : W - M * 2, h: 4.5 };

  if (specs.length === 1) {
    const opts = chartOptions({ ...(axes || {}), ...(specs[0].options || {}), ...(options || {}) });
    assertChartIsReadable(specs, opts, title || 'chart');
    s.addChart(specs[0].type, specs[0].data, { ...area, ...opts });
  } else {
    // Combo. The brand frame belongs in the GLOBAL options object — a previous version
    // passed only the plot area here, which silently dropped the palette, the fonts,
    // the gridlines, the number formats AND the legend on every combo chart in the deck.
    // Per-series options carry only chart-type specifics (secondaryValAxis, lineSize…).
    const opts = chartOptions({ ...(axes || {}), ...(options || {}) });
    assertChartIsReadable(specs, opts, title || 'chart');
    s.addChart(
      specs.map(c => ({ type: c.type, data: c.data, options: { ...(c.options || {}) } })),
      { ...area, ...opts });
  }

  if (insight) {
    s.addShape(pptx.ShapeType.roundRect, {
      x: W - M - 3.3, y: 2.15, w: 3.3, h: 4.5,
      rectRadius: RADIUS, fill: { color: C.p100 }, line: { color: C.p100, width: 0 },
    });
    // One claim with its number. ≤35 words — longer argument goes on a narrative slide.
    s.addText(insight, {
      x: W - M - 3.05, y: 2.4, w: 2.8, h: 4.0, margin: 0,
      color: C.dark, ...T.body, fontSize: 13, valign: 'top',
    });
  }
  return s;
}

/** rows[0] is the header. Set opts.totalRow to purple-fill the last row. */
function tableSlide(pptx, { title, scope, rows, colW, totalRow = false, note }) {
  const s = contentSlide(pptx, { title, scope });
  const body = rows.map((row, r) => row.map(cell => {
    const isHead = r === 0;
    const isTotal = totalRow && r === rows.length - 1;
    return {
      text: String(cell),
      options: {
        // Numeric cells take the viz face so figures align with the charts.
        fontFace: (!isHead && /^[$+\-(]?[\d.,]/.test(String(cell))) ? VIZ_FACE : TEXT_FACE,
        fontSize: isHead ? 12 : 11,
        bold: isHead || isTotal,
        color: isTotal ? C.white : C.dark,
        fill: { color: isTotal ? C.purple : (isHead ? C.white : (r % 2 === 0 ? C.p100 : C.white)) },
        align: r === 0 ? 'left' : (typeof cell === 'number' ? 'right' : 'left'),
        margin: 6,
      },
    };
  }));

  s.addTable(body, {
    x: M, y: 2.0, w: W - M * 2, colW,
    border: { type: 'solid', color: C.mauve, pt: 0.5 },
    autoPage: false,
  });
  if (note) {
    s.addText(note, {
      x: M, y: H - 1.0, w: W - M * 2, h: 0.5, margin: 0, color: C.violet, ...T.caption,
    });
  }
  return s;
}

/**
 * Chart placed as a pre-rendered image, at the same figure geometry as chartSlide.
 *
 * Use this when the deck is destined for Google Slides: Google's .pptx importer
 * rasterises native `addChart` objects at screen resolution, so a correct native
 * chart arrives blurry. Rendering it yourself at 3× and placing the PNG puts the
 * resolution under your control. See references/pptx-report.md § Charts in the deck.
 */
function chartImageSlide(pptx, { title, scope, definition, image, insight }) {
  const s = contentSlide(pptx, { title, scope });
  if (definition) {
    s.addText(definition, {
      x: M, y: 1.72, w: W - M * 2, h: 0.3, margin: 0, color: C.violet, ...T.caption,
    });
  }
  s.addImage({
    path: image,
    x: M, y: 2.15, w: insight ? W - M * 2 - 3.6 : W - M * 2, h: 4.5,
    sizing: { type: 'contain', w: insight ? W - M * 2 - 3.6 : W - M * 2, h: 4.5 },
  });
  if (insight) {
    s.addShape(pptx.ShapeType.roundRect, {
      x: W - M - 3.3, y: 2.15, w: 3.3, h: 4.5,
      rectRadius: RADIUS, fill: { color: C.p100 }, line: { color: C.p100, width: 0 },
    });
    s.addText(insight, {
      x: W - M - 3.05, y: 2.4, w: 2.8, h: 4.0, margin: 0,
      color: C.dark, ...T.body, fontSize: 13, valign: 'top',
    });
  }
  return s;
}

function closingSlide(pptx, { headline = 'Thank you', lines = [] } = {}) {
  const s = darkSlide(pptx);
  s.addText(headline, {
    x: M, y: 2.6, w: W - M * 2, h: 1.2, margin: 0, color: C.white, ...T.slideTitle, fontSize: 31,
  });
  if (lines.length) {
    s.addText(lines.join('\n'), {
      x: M, y: 4.0, w: 7, h: 1.6, margin: 0, color: C.mauve, ...T.body, fontSize: 13,
    });
  }
  wordmark(s, { y: H - 1.0 });
  return s;
}

module.exports = {
  C, SERIES, NEUTRALS, T, FMT, HEAD_FACE, TEXT_FACE, VIZ_FACE, DISPLAY_FACE, RADIUS, W, H, M,
  roundValues, niceMax, dualAxis, assertChartIsReadable,
  newDeck, darkSlide, lightSlide, wordmark,
  coverSlide, sectionDivider, contentSlide,
  kpiRow, kpiSlide, chartOptions, chartSlide, chartImageSlide, tableSlide, closingSlide,
};
