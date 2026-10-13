# Design Tokens

Exact values behind `viz_style.py`. Use these when building a chart type the helpers don't
cover (scatter, heatmap, stacked bars, a composed multi-panel canvas) so it still reads as
part of the same system.

## Color palette

| Token | Hex | Use |
|---|---|---|
| ink | `#1A1D26` | Primary text, big KPI numbers, chart titles |
| muted | `#6B7280` | Subtitles, axis labels, tick labels, period lines |
| grid | `#E7E9EE` | Hairline horizontal gridlines, card/axis borders |
| card_bg | `#FFFFFF` | Card and plot-area background |
| page_bg | `#F6F7F9` | Canvas behind cards/figures |
| tooltip_bg | `#12131A` | Dark hover-style annotation boxes |

### Series colors (assign in this order)

| Order | Token | Hex | Typical |
|---|---|---|---|
| 1 | android | `#4C7DF0` | blue — primary / Android |
| 2 | ios | `#D6486E` | rose — secondary / iOS |
| 3 | series3 | `#2FB48A` | green |
| 4 | series4 | `#E0912F` | amber |
| 5 | series5 | `#8B5CF6` | violet |

### Semantic delta colors (deltas only — never series)

| Token | Hex | Use |
|---|---|---|
| up | `#137A4C` | positive delta text + ↗ arrow |
| up_bg | `#E4F4EC` | positive delta pill background |
| down | `#C43D3D` | negative delta text + ↘ arrow |
| down_bg | `#FCEBEA` | negative delta pill background |

Keep red/green exclusively for direction-of-change. A series drawn in `down` red must not
sit next to a red delta pill — it creates a false "this line is bad" read.

## Typography

- Font resolution order (first installed wins): **Inter → Helvetica Neue → Arial → DejaVu Sans**.
  DejaVu Sans always exists in the container, so charts never fail to render.
- Sizes: chart title ~15pt bold; axis labels ~10.5pt; ticks ~9.5pt; legend ~10pt.
- KPI card: title 13pt bold, period 8.5pt muted, value ~30pt bold, delta pill 9pt bold.
- Titles are **left-aligned**, not centered — the eye starts top-left.

## Layout & spacing

- Line/bar figures: default `figsize=(8, 4.2)` / `(7, 4)`; render at `savefig.dpi=200`.
- KPI card: `figsize=(3.4, 2.6)`, rounded rectangle inset ~3% from the figure edge,
  corner rounding ~0.05.
- Spines: top and right removed on every chart; only a faint left/bottom frame remains.
- Gridlines: horizontal (y) only, `#E7E9EE`, 1px. No vertical gridlines — they compete with
  the data.
- Line width 2.4px, round caps, white-filled circle markers (~4.5px) so points read on top
  of the line. Secondary-axis series use a dashed line + square markers to distinguish scale.
- Legend sits **below** the plot, centered, frameless, up to 4 columns.

## Number formatting

- Counts (DAU, installs, retained users): whole numbers with thousands separators — use
  `fmt_compact` (`1.24M`, `2.86K`) on axes, full integers in labels.
- Currency: `fmt_money` — 2 decimals under $10k, 0 decimals at/above $10k, always a `$` and
  commas.
- Percentages / ratios: 2–3 decimals as the metric warrants; don't rescale the metric to
  tidy the axis — adjust axis bounds/ticks instead.

## Dashboard composition order

KPI cards (headline numbers) → trend line charts → breakdown bar charts. Cards first because
readers check the number before the shape. On a single composed figure, keep the same
palette, `apply_theme()`, and formatters across every panel.
