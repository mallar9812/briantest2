# Playsimple brand tokens

Source: Playsimple Brand Playbook v1.0 (2026). Use these values verbatim — do not
approximate, re-derive, or "improve" them.

## Primary colours

| Name | HEX | RGB | CMYK | PMS |
|---|---|---|---|---|
| Playsimple Purple | `#A00FFF` | 160, 15, 255 | 70, 85, 0, 0 | 266 C |
| White | `#FFFFFF` | 255, 255, 255 | 0, 0, 0, 0 | White |
| MTG Dark Purple | `#2A0B35` | 42, 11, 53 | 75, 100, 15, 50 | 2695 C |

MTG Dark Purple connects to the MTG family. Playsimple Purple is the district's own
voice and must remain the leading expression in every report.

## Secondary ramp

Built on Playsimple Purple. Adds depth without competing with the core colour.

| Token | HEX | RGB |
|---|---|---|
| Purple 600 | `#440E6F` | 68, 14, 111 |
| Purple 500 | `#6200B1` | 98, 0, 177 |
| Purple 400 | `#A00FFF` | 160, 15, 255 | *(= Playsimple Primary Purple)* |
| Purple 300 | `#C782FF` | 199, 130, 255 |
| Purple 200 | `#DFB5FF` | 223, 181, 255 |
| Purple 100 | `#F7EBFF` | 247, 235, 255 |

Use 100/200 for table zebra striping and soft panel fills, 300 for secondary chart
series, 500/600 for dark accents on light grounds.

## Extended palette

Drawn from the MTG masterbrand. **Only** for complex infographics, UI, and data-rich
visuals — never as a report's dominant colour.

| Name | HEX | RGB |
|---|---|---|
| Burgundy | `#4D0808` | 77, 8, 8 |
| Crimson | `#8C0E0E` | 140, 14, 14 |
| Coral | `#FF8787` | 255, 135, 135 |
| Blush | `#FFD1D1` | 255, 209, 209 |
| Petal | `#FFEEEE` | 255, 238, 238 |
| Violet | `#4C3255` | 76, 50, 85 |
| Lilac | `#A69CED` | 166, 156, 237 |
| Lavender | `#ACA0B0` | 172, 160, 176 |
| Mauve | `#D4CED7` | 212, 206, 215 |
| Mist | `#F0EDF1` | 240, 237, 241 |

Mist is the standard light panel/surface fill for cards and sidebars.

## Colour pairings

**Approved grounds — these three only:**

1. Dark Purple text on White
2. White text on Dark Purple
3. White text on Playsimple Purple

**Restricted:**

- Purple on Dark Purple — decorative text and large display headlines only. Avoid
  entirely in CMYK print output; contrast does not reproduce.
- Purple text on White — permitted for CTAs, links, and highlight text.

## Delta / status colours (report-specific extension)

The playbook has no semantic status pair, so the report system fixes these:

| Meaning | HEX |
|---|---|
| Positive delta | `#2E7D32` |
| Negative delta | `#8C0E0E` (Crimson) |
| Neutral / flat | `#ACA0B0` (Lavender) |

Rendered as plain coloured text under the metric value — no pill, no background.
These colours are reserved: they never appear as chart series colours or decoration.

## Categorical chart order

Fixed order. Slot 1 is always Playsimple Purple. An entity keeps its slot across every
chart in the same report — never reassign when filtering.

1. `#A00FFF` Playsimple Purple
2. `#4C3255` Violet
3. `#A69CED` Lilac
4. `#6200B1` Purple 500
5. `#ACA0B0` Lavender
6. `#FF8787` Coral
7. `#440E6F` Purple 600
8. `#D4CED7` Mauve

Sequential/intensity scales use the purple ramp 100 → 600. Diverging scales use
Crimson `#8C0E0E` → Mist `#F0EDF1` → Purple 500 `#6200B1`.

## Typography

**Reports use three faces, each with one job.** MuseoModerno for headings, Poppins for
content, Zalando Sans for anything numeric or chart-borne. Inter remains in the stack as
a fallback only. The playbook's MTG Display pairing is for brand-led marketing work and
does not apply here — MTG Display is licensed and absent wherever reports are opened.

Sentence case throughout; uppercase is reserved for the MTG masterbrand.

| Level | Face | Leading | Tracking |
|---|---|---|---|
| Cover / slide / section title | MuseoModerno Bold | 95% | -2% |
| Sub-headline | Poppins SemiBold | 110% | -2% |
| Body | Poppins Regular | 120% | -0.75% |
| Button / label | Poppins Medium | — | 0% |
| KPI value, delta | Zalando Sans Bold | 95% | -2% |
| Chart axis / data label | Zalando Sans Regular | — | 0% |
| Numeric table cell | Zalando Sans Regular | — | 0% |

**MuseoModerno is cut short.** M, W and w are replaced with the family's short
alternates (`M.ss02`, `W.ss01`, `w.ss01`); lowercase m is already short by default.
`scripts/setup_fonts.sh` builds and installs this cut. Stock MuseoModerno will render
the decorative wide-arch forms instead — visibly wrong, and worth checking on any
machine that had the font before.

**MuseoModerno has an 18pt floor.** Below that it stops being legible and starts being
texture. Sub-heads, captions, tables and chart labels never use it.

Report size scale (PDF, A4):

| Element | Size |
|---|---|
| Cover title | 40pt (MuseoModerno) |
| Section title | 24pt (MuseoModerno) |
| Sub-headline | 15pt (Poppins) |
| Body | 10.5pt (Poppins) |
| Caption / scope line | 8.5pt (Poppins) |
| KPI value | 26pt (Zalando Sans) |
| KPI label | 9pt (Poppins) |

Deck scale (PPTX, 13.3" × 7.5"):

| Element | Size |
|---|---|
| Cover title | 36pt (MuseoModerno) |
| Slide title | 26pt (MuseoModerno) |
| Section divider title | 31pt (MuseoModerno) |
| Sub-headline | 15pt (Poppins) |
| Body / bullet | 14pt (Poppins) |
| Caption | 10pt (Poppins) |
| KPI value | 30pt (Zalando Sans), 27pt at 4-up, 24pt at 5-up |
| KPI label | 11pt (Poppins) |

MuseoModerno Bold is for cover, section and slide titles only. Zalando Sans Bold is for
large display numbers. Everything else is Poppins Regular/SemiBold/Medium.

Never substitute Montserrat, Futura, Helvetica, Arial, or any other lookalike when one
of the three is missing — install it instead.

## Shape and layout

- **Corner radius 16px** on cards, panels, and image containers (0.16" on slides).
  Buttons and pills are fully rounded.
- Infographics use soft, curved forms — rounded bar ends (4px), no hard corners on
  data marks.
- Generous whitespace; the playbook's functional text-heavy layout is two columns of
  small Poppins body copy under one large MuseoModerno headline.
- Grid: 12-column on slides, 2-column on PDF detail pages, single column for narrative.

## Logo usage

- Wordmark: lowercase `playsimple`. Studio lock-up adds the PS grid symbol to its left.
- Colourways: Dark Purple on White · White on Dark Purple · White on Purple · Purple on
  White. Nothing else.
- Clear space on all sides = 1X, where X is the stem thickness of the wordmark.
- Placement in reports: small, top-left of the cover, or bottom-left of the closing
  slide. Never stretched, recoloured, rotated, or placed over busy imagery.

## Imagery and iconography

- Photography: documentary tone, authentic, small joyous everyday moments. Categories
  are people, product, and game illustrations.
- Illustration: simplified rounded geometric shapes, depth from grain rather than
  realistic lighting or hard shadows. Friendly, playful, modern — never corporate,
  sharp, or photoreal.
- Icons: line style, rounded joins, drawn from game motifs (dice, key, puzzle, gem,
  rocket, trophy), in Dark Purple.
- Reports are usually image-light. Use one hero illustration on the cover at most; do
  not decorate data pages.
