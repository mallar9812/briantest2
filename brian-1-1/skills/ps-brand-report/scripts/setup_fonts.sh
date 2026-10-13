#!/usr/bin/env bash
# Playsimple report fonts — MuseoModerno (headings), Poppins (content),
# Zalando Sans (visualizations), Inter (fallback only).
# Safe to re-run. Exits non-zero if any of the three primary faces is missing.
#
# MuseoModerno is installed as the Playsimple cut: short M / W / w forms swapped
# in from the family's own stylistic alternates. See build_museomoderno.py.

set -u

DEST="${HOME}/.local/share/fonts/psreport"
GF="https://raw.githubusercontent.com/google/fonts/main/ofl"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

have() { fc-list : family 2>/dev/null | tr ',' '\n' | grep -qiFx "$1"; }

if have "MuseoModerno" && have "Poppins" && have "Zalando Sans" && have "Inter"; then
  echo "Report fonts: MuseoModerno, Poppins, Zalando Sans, Inter all present — ready."
  exit 0
fi

mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Poppins: static instances ship upstream, take them directly -------------
if ! have "Poppins"; then
  echo "Poppins: installing..."
  for w in Regular Medium SemiBold Bold; do
    curl -fsSL -o "${DEST}/Poppins-${w}.ttf" "${GF}/poppins/Poppins-${w}.ttf" \
      || echo "  warn: Poppins-${w} failed" >&2
  done
fi

# --- Zalando Sans: variable upstream, pin to static Regular + Bold -----------
if ! have "Zalando Sans"; then
  echo "Zalando Sans: installing..."
  if curl -fsSL -o "${TMP}/ZalandoSans.ttf" "${GF}/zalandosans/ZalandoSans%5Bwdth,wght%5D.ttf"; then
    python3 - "$TMP/ZalandoSans.ttf" "$DEST" <<'PY'
import sys, os
from fontTools import ttLib
from fontTools.varLib import instancer
src, dest = sys.argv[1], sys.argv[2]
for wght, style in ((400, "Regular"), (700, "Bold")):
    f = instancer.instantiateVariableFont(ttLib.TTFont(src), {"wght": wght, "wdth": 100}, inplace=False)
    n = f["name"]
    for nid, val in [(1,"Zalando Sans"),(2,style),(4,f"Zalando Sans {style}"),
                     (6,f"ZalandoSans-{style}"),(16,"Zalando Sans"),(17,style)]:
        for rec in list(n.names):
            if rec.nameID == nid: n.setName(val, nid, rec.platformID, rec.platEncID, rec.langID)
        n.setName(val, nid, 3, 1, 0x409)
    o = f["OS/2"]; o.usWeightClass = wght
    if style == "Bold":
        o.fsSelection = (o.fsSelection & ~0x40) | 0x20; f["head"].macStyle |= 1
    else:
        o.fsSelection = (o.fsSelection & ~0x20) | 0x40; f["head"].macStyle &= ~1
    f.save(os.path.join(dest, f"ZalandoSans-{style}.ttf"))
PY
  fi
fi

# --- MuseoModerno: Playsimple cut, short M / W / w --------------------------
if ! have "MuseoModerno"; then
  echo "MuseoModerno: installing Playsimple cut (short M / W / w)..."
  if curl -fsSL -o "${TMP}/MuseoModerno.ttf" "${GF}/museomoderno/MuseoModerno%5Bwght%5D.ttf"; then
    python3 "${SCRIPT_DIR}/build_museomoderno.py" "${TMP}/MuseoModerno.ttf" "$DEST" \
      || echo "  warn: MuseoModerno build failed" >&2
  fi
fi

# --- Inter: fallback only, but keep it present ------------------------------
if ! have "Inter"; then
  echo "Inter (fallback): installing..."
  apt-get install -y fonts-inter >/dev/null 2>&1 || {
    if curl -fsSL -o "${TMP}/inter.zip" \
        "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"; then
      unzip -qo "${TMP}/inter.zip" -d "${TMP}/inter" 2>/dev/null || true
      find "${TMP}/inter" \( -name "Inter*.otf" -o -name "Inter*.ttf" \) 2>/dev/null \
        | while read -r f; do cp -f "$f" "$DEST/"; done
    fi
  }
fi

fc-cache -f "$DEST" >/dev/null 2>&1

MISSING=""
for fam in "MuseoModerno" "Poppins" "Zalando Sans"; do
  have "$fam" || MISSING="${MISSING} ${fam};"
done

if [ -n "$MISSING" ]; then
  cat >&2 <<MSG
Report fonts: FAILED — missing:${MISSING}
Do NOT fall back to Montserrat, Futura, Helvetica, Arial or any lookalike.
Fix this first: retry with network access, or drop the .ttf files into
${DEST}/ and re-run this script.
MSG
  exit 1
fi

echo "Report fonts ready: MuseoModerno (headings), Poppins (content), Zalando Sans (viz)."
have "Inter" || echo "  note: Inter fallback absent — fine unless a primary face fails to load."
exit 0
