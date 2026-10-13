#!/usr/bin/env python3
"""
Chart readability validator for Playsimple branded decks.

`validate.py` proves a .pptx isn't corrupt. This proves its charts can be *read*.
Every defect below produces a perfectly valid file that renders without error, so
nothing signals it except a human noticing the deck looks amateurish:

  1. multi-series chart with no legend
  2. data labels with no number format  -> PowerPoint prints the raw float
  3. cached values carrying > 2 decimal places -> the array was never rounded
  4. category axis labels that are ordinals (1, 2, 3 ...) instead of real names
  5. dual value axes whose tick counts differ -> two crossing sets of gridlines
  6. dual value axes both drawing gridlines
  7. dual axis with an untitled axis
  8. series fill colours outside the brand palette

Usage:
    python3 validate_charts.py deck.pptx [--warn-only]

Exit codes: 0 clean (warnings allowed), 1 one or more failures, 2 bad input.
"""

import re
import sys
import zipfile
import xml.etree.ElementTree as ET

C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

# references/brand-tokens.md — series slots plus the report's structural colours.
PALETTE = {
    "A00FFF", "2A0B35", "FFFFFF",
    "440E6F", "6200B1", "C782FF", "DFB5FF", "F7EBFF",
    "4D0808", "8C0E0E", "FF8787", "FFD1D1", "FFEEEE",
    "4C3255", "A69CED", "ACA0B0", "D4CED7", "F0EDF1",
    "2E7D32",
}

MAX_DECIMALS = 2      # a cached value with more than this was never rounded
ORDINAL_RE = re.compile(r"^\d+$")


class Result:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def fail(self, chart, msg):
        self.failures.append((chart, msg))

    def warn(self, chart, msg):
        self.warnings.append((chart, msg))


def text_of(node):
    return (node.text or "").strip() if node is not None else ""


def series_name(ser):
    tx = ser.find(f"{C}tx")
    if tx is None:
        return None
    for path in (f"{C}strRef/{C}strCache/{C}pt/{C}v", f"{C}v"):
        node = tx.find(path)
        if node is not None and text_of(node):
            return text_of(node)
    return None


def category_labels(ser):
    cat = ser.find(f"{C}cat")
    if cat is None:
        return []
    return [text_of(v) for v in cat.iter(f"{C}v") if text_of(v)]


def cached_values(ser):
    val = ser.find(f"{C}val")
    out = []
    if val is None:
        return out
    for v in val.iter(f"{C}v"):
        raw = text_of(v)
        try:
            out.append((raw, float(raw)))
        except ValueError:
            continue
    return out


def decimals_in(raw):
    if "." not in raw:
        return 0
    return len(raw.split(".", 1)[1].rstrip("0"))


def shows_values(node):
    show = node.find(f"{C}showVal")
    return show is not None and show.get("val") in ("1", "true")


def has_usable_numfmt(node):
    fmt = node.find(f"{C}numFmt")
    if fmt is None:
        return False
    code = fmt.get("formatCode") or ""
    if fmt.get("sourceLinked") in ("1", "true") and not code:
        return False
    return bool(code) and code.lower() != "general"


def axis_intervals(ax):
    """Number of major intervals on a value axis, or None if not pinned."""
    scaling = ax.find(f"{C}scaling")
    if scaling is None:
        return None
    mx = scaling.find(f"{C}max")
    mn = scaling.find(f"{C}min")
    mu = ax.find(f"{C}majorUnit")
    if mx is None or mu is None:
        return None
    try:
        hi = float(mx.get("val"))
        lo = float(mn.get("val")) if mn is not None else 0.0
        unit = float(mu.get("val"))
        if unit <= 0:
            return None
        return round((hi - lo) / unit, 3)
    except (TypeError, ValueError):
        return None


def axis_has_title(ax):
    return ax.find(f"{C}title") is not None


def check_chart(name, xml, res):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        res.fail(name, f"chart XML will not parse: {exc}")
        return

    plot = root.find(f".//{C}plotArea")
    if plot is None:
        res.fail(name, "no plotArea")
        return

    series = list(plot.iter(f"{C}ser"))
    if not series:
        res.warn(name, "chart carries no series")
        return

    # --- 1. legend -------------------------------------------------------
    legend = root.find(f".//{C}legend")
    if len(series) > 1 and legend is None:
        res.fail(name, f"{len(series)} series and NO legend — the reader cannot tell "
                       f"the series apart (an exported file has no HTML dot legend)")

    # --- series-level checks --------------------------------------------
    for idx, ser in enumerate(series, 1):
        sname = series_name(ser)
        if sname is None and len(series) > 1:
            res.fail(name, f"series {idx} has no name — the name IS the legend entry")

        labels = category_labels(ser)
        if not labels:
            res.fail(name, f"series {idx} ({sname or 'unnamed'}) has no category labels — "
                           f"the axis will read 1, 2, 3 …")
        elif all(ORDINAL_RE.match(l) for l in labels):
            preview = ", ".join(labels[:4])
            res.fail(name, f"series {idx} ({sname or 'unnamed'}) category labels are ordinals "
                           f"({preview}…) — use real names: 'D1','D7','D30' / 'Apr 2025'")

        for raw, _num in cached_values(ser):
            if decimals_in(raw) > MAX_DECIMALS:
                res.fail(name, f"series {idx} ({sname or 'unnamed'}) carries an unrounded value "
                               f"({raw}) — round the array with PS.roundValues() before charting; "
                               f"a format code alone does not survive a Google Slides import")
                break

        for spPr in ser.findall(f"{C}spPr"):
            for clr in spPr.iter(f"{A}srgbClr"):
                val = (clr.get("val") or "").upper()
                if val and val not in PALETTE:
                    res.fail(name, f"series {idx} ({sname or 'unnamed'}) uses off-palette "
                                   f"colour #{val} — see references/brand-tokens.md")

    # --- 2. data label number formats -----------------------------------
    for dlbls in root.iter(f"{C}dLbls"):
        if shows_values(dlbls) and not has_usable_numfmt(dlbls):
            res.fail(name, "data labels are shown with no usable numFmt — PowerPoint falls back "
                           "to the General format and prints the raw float")
            break

    # --- 3. dual axis ----------------------------------------------------
    val_axes = list(plot.findall(f"{C}valAx"))
    if len(val_axes) >= 2:
        intervals = [axis_intervals(ax) for ax in val_axes[:2]]
        if any(i is None for i in intervals):
            res.fail(name, "dual-axis chart without pinned bounds (max/majorUnit) — the two "
                           "scales will choose their own ticks and draw two sets of gridlines. "
                           "Build it with PS.dualAxis()")
        elif intervals[0] != intervals[1]:
            res.fail(name, f"dual-axis tick counts differ ({intervals[0]} vs {intervals[1]}) — "
                           f"gridlines will not coincide. Same tick count on both axes")

        gridded = [ax for ax in val_axes[:2] if ax.find(f"{C}majorGridlines") is not None]
        if len(gridded) > 1:
            res.fail(name, "both value axes draw major gridlines — two crossing sets of "
                           "horizontal rules. Draw them from the primary axis only")

        untitled = [i for i, ax in enumerate(val_axes[:2], 1) if not axis_has_title(ax)]
        if untitled:
            res.fail(name, f"dual-axis chart with untitled axis/axes ({', '.join(map(str, untitled))}) "
                           f"— each axis states its units")

        for ser in series:
            sname = series_name(ser) or ""
            if not re.search(r"left|right", sname, re.I):
                res.fail(name, f"dual-axis series \"{sname or 'unnamed'}\" does not name its axis — "
                               f"e.g. 'UA spend (USD, left axis)'")
                break


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2

    path = argv[1]
    warn_only = "--warn-only" in argv
    res = Result()

    try:
        with zipfile.ZipFile(path) as zf:
            charts = sorted(n for n in zf.namelist()
                            if re.match(r"ppt/charts/chart\d+\.xml$", n))
            if not charts:
                print(f"ps-brand-report chart check: {path}")
                print("  no native charts found — if this deck uses pre-rendered chart images, "
                      "verify them by eye at 100% instead.")
                return 0
            for n in charts:
                check_chart(n.split("/")[-1], zf.read(n), res)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"cannot read {path}: {exc}")
        return 2

    print(f"ps-brand-report chart check: {path}")
    print(f"  {len(charts)} chart(s) inspected\n")

    for chart, msg in res.warnings:
        print(f"  WARN  {chart}: {msg}")
    for chart, msg in res.failures:
        print(f"  FAIL  {chart}: {msg}")

    if not res.failures:
        print("  PASS — legends present, labels named, numbers formatted, axes aligned.")
        return 0

    print(f"\n  {len(res.failures)} failure(s). "
          f"{'Not blocking (--warn-only).' if warn_only else 'Do not deliver this deck.'}")
    return 0 if warn_only else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
