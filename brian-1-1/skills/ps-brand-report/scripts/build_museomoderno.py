#!/usr/bin/env python3
"""Build the Playsimple cut of MuseoModerno.

Stock MuseoModerno defaults to decorative wide-arch forms for M, W and w — the
"ᙏ" style M in particular is unreadable in a report title. The family ships short,
conventional alternates for exactly these: M.ss02, W.ss01, w.ss01. Lowercase m is
already the short form in the default set and is left alone.

This swaps the short glyphs into the default slots and writes static Regular and
Bold instances (PowerPoint handles variable fonts badly — its bold button does
nothing on a variable-only install).

Usage: build_museomoderno.py <MuseoModerno[wght].ttf> <outdir>
"""
import sys, os
from fontTools import ttLib
from fontTools.varLib import instancer

# default slot <- short alternate. m is already short in the default set.
SHORT_FORMS = [("M", "M.ss02"), ("W", "W.ss01"), ("w", "w.ss01")]

def build(src, outdir, weight, style):
    f = instancer.instantiateVariableFont(ttLib.TTFont(src), {"wght": weight}, inplace=False)
    order = f.getGlyphOrder()
    for base, alt in SHORT_FORMS:
        if alt not in order:
            print(f"  warn: {alt} missing, leaving {base} as-is", file=sys.stderr)
            continue
        f["glyf"][base] = f["glyf"][alt]
        f["hmtx"][base] = f["hmtx"][alt]
    n = f["name"]
    for nid, val in [(1, "MuseoModerno"), (2, style), (4, f"MuseoModerno {style}"),
                     (6, f"MuseoModerno-{style}"), (16, "MuseoModerno"), (17, style)]:
        for rec in list(n.names):
            if rec.nameID == nid:
                n.setName(val, nid, rec.platformID, rec.platEncID, rec.langID)
        n.setName(val, nid, 3, 1, 0x409)
    os2 = f["OS/2"]
    os2.usWeightClass = weight
    if style == "Bold":
        os2.fsSelection = (os2.fsSelection & ~0x40) | 0x20
        f["head"].macStyle |= 1
    else:
        os2.fsSelection = (os2.fsSelection & ~0x20) | 0x40
        f["head"].macStyle &= ~1
    out = os.path.join(outdir, f"MuseoModerno-{style}.ttf")
    f.save(out)
    print(f"  built {out}")

if __name__ == "__main__":
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    build(src, outdir, 400, "Regular")
    build(src, outdir, 700, "Bold")
