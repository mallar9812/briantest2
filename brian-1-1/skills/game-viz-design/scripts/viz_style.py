"""
viz_style.py — Playsimple game-analytics chart design system (matplotlib).

Drop-in styling so every static chart / KPI card looks like it came from the
same dashboard. Inspired by the internal metrics dashboard: clean white cards,
big numbers, red/green delta pills with trend arrows, restrained line charts,
dual axes for mismatched scales.

Usage
-----
    from viz_style import apply_theme, PALETTE, kpi_card, line_chart, save
    apply_theme()
    fig, ax = line_chart(dates, {"Android": a_vals, "iOS": i_vals},
                         title="Rev/DAU — Tier 1", subtitle="Jun 27–Jul 05 '26",
                         ylabel="Rev per DAU ($)")
    save(fig, "rev_per_dau.png")

Everything here is a starting point, not a straitjacket — override colors,
add annotations, or drop a helper if a specific chart calls for it.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
import numpy as np

# --- Palette -----------------------------------------------------------------
# Cool, calm base with two clear series colors and semantic red/green for deltas.
PALETTE = {
    "ink":        "#1A1D26",   # near-black text / big numbers
    "muted":      "#6B7280",   # secondary text, subtitles, labels
    "grid":       "#E7E9EE",   # hairline gridlines
    "card_bg":    "#FFFFFF",   # card background
    "page_bg":    "#F6F7F9",   # canvas behind cards
    "tooltip_bg": "#12131A",   # dark hover-style annotation box
    # Series (extend as needed; these read well together and in colorblind view)
    "android":    "#4C7DF0",   # blue  (primary series)
    "ios":        "#D6486E",   # rose  (secondary series)
    "series3":    "#2FB48A",   # green
    "series4":    "#E0912F",   # amber
    "series5":    "#8B5CF6",   # violet
    # Semantic (deltas)
    "up":         "#137A4C",   # positive delta text
    "up_bg":      "#E4F4EC",   # positive delta pill
    "down":       "#C43D3D",   # negative delta text
    "down_bg":    "#FCEBEA",   # negative delta pill
}

SERIES_CYCLE = [PALETTE[k] for k in
                ("android", "ios", "series3", "series4", "series5")]


def _pick_font():
    """Prefer a clean sans; fall back gracefully so this never crashes."""
    for name in ("Inter", "Helvetica Neue", "Arial", "DejaVu Sans"):
        if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
            return name
    return "DejaVu Sans"


FONT = _pick_font()


def apply_theme():
    """Apply global rcParams. Call once before making figures."""
    plt.rcParams.update({
        "font.family": FONT,
        "figure.facecolor": PALETTE["page_bg"],
        "axes.facecolor": PALETTE["card_bg"],
        "axes.edgecolor": PALETTE["grid"],
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlecolor": PALETTE["ink"],
        "axes.labelsize": 10.5,
        "axes.labelcolor": PALETTE["muted"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": PALETTE["page_bg"],
    })


# --- Formatting helpers ------------------------------------------------------
def fmt_compact(x, _pos=None):
    """1_240_512 -> '1.24M', 2860 -> '2.86K'. For axis tick formatting."""
    ax = abs(x)
    if ax >= 1e9:
        return f"{x/1e9:.2f}B".rstrip("0").rstrip(".") + "B" if False else f"{x/1e9:.2f}B"
    if ax >= 1e6:
        return f"{x/1e6:.2f}M"
    if ax >= 1e3:
        return f"{x/1e3:.2f}K"
    return f"{x:.0f}"


def fmt_money(x, decimals=2):
    """Currency with commas. Large aggregates (>=10k) show 0 decimals."""
    if abs(x) >= 10_000:
        return f"${x:,.0f}"
    return f"${x:,.{decimals}f}"


def _delta_style(value):
    up = value >= 0
    arrow = "↗" if up else "↘"
    return {
        "arrow": arrow,
        "txt": PALETTE["up"] if up else PALETTE["down"],
        "bg":  PALETTE["up_bg"] if up else PALETTE["down_bg"],
    }


# --- KPI card ----------------------------------------------------------------
def kpi_card(title, value, deltas=None, period=None,
             figsize=(3.4, 2.6), value_color=None):
    """
    A single KPI card: title, optional period, a big value, and up to a couple
    of delta pills (e.g. 'vs previous day', 'vs last week').

    deltas: list of dicts like
        {"pct": -1.497, "abs": "-43.633", "label": "vs previous day"}
    'pct' drives arrow + red/green; 'abs' is shown right-aligned; both optional.
    """
    fig = plt.figure(figsize=figsize, facecolor=PALETTE["page_bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    # rounded white card
    card = FancyBboxPatch((0.03, 0.03), 0.94, 0.94,
                          boxstyle="round,pad=0.01,rounding_size=0.05",
                          linewidth=1, edgecolor=PALETTE["grid"],
                          facecolor=PALETTE["card_bg"], mutation_aspect=figsize[0]/figsize[1])
    ax.add_patch(card)

    ax.text(0.10, 0.86, title, color=PALETTE["ink"], fontsize=13,
            fontweight="bold", va="top")
    if period:
        ax.text(0.10, 0.75, period, color=PALETTE["muted"], fontsize=8.5, va="top")

    ax.text(0.10, 0.50, str(value), color=value_color or PALETTE["ink"],
            fontsize=30, fontweight="bold", va="center")

    y = 0.26
    for d in (deltas or [])[:2]:
        st = _delta_style(d.get("pct", 0))
        pill = f" {st['arrow']} {abs(d.get('pct', 0)):.3f}% "
        ax.text(0.10, y, pill, color=st["txt"], fontsize=9, fontweight="bold",
                va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc=st["bg"], ec="none"))
        if d.get("label"):
            ax.text(0.42, y, d["label"], color=PALETTE["muted"], fontsize=8.5, va="center")
        if d.get("abs") is not None:
            ax.text(0.90, y, str(d["abs"]), color=st["txt"], fontsize=9,
                    va="center", ha="right")
        y -= 0.15
    return fig, ax


# --- Line chart --------------------------------------------------------------
def line_chart(x, series, title=None, subtitle=None, ylabel=None,
               y2=None, y2label=None, figsize=(8, 4.2), money=False,
               compact_y=False, marker=True):
    """
    Multi-series line chart with the house style.

    series: dict {label: y_values}. Colors auto-assigned from SERIES_CYCLE.
    y2:     optional dict {label: y_values} plotted on a secondary right axis
            (use for mismatched scales, e.g. revenue vs DAU). Its series
            continue the color cycle after the primary ones.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ci = 0
    for label, ys in series.items():
        ax.plot(x, ys, color=SERIES_CYCLE[ci % len(SERIES_CYCLE)], linewidth=2.4,
                marker="o" if marker else None, markersize=4.5,
                markerfacecolor="white", markeredgewidth=1.6, label=label,
                solid_capstyle="round")
        ci += 1

    ax2 = None
    if y2:
        ax2 = ax.twinx()
        ax2.grid(False)
        ax2.spines["top"].set_visible(False)
        for label, ys in y2.items():
            ax2.plot(x, ys, color=SERIES_CYCLE[ci % len(SERIES_CYCLE)], linewidth=2.4,
                     linestyle="--", marker="s" if marker else None, markersize=4,
                     markerfacecolor="white", markeredgewidth=1.6, label=label)
            ci += 1
        if y2label:
            ax2.set_ylabel(y2label, color=PALETTE["muted"])

    if money:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: fmt_money(v)))
    elif compact_y:
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_compact))

    if title:
        ax.set_title(title, loc="left", pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                color=PALETTE["muted"], fontsize=9.5, va="bottom")
    if ylabel:
        ax.set_ylabel(ylabel)

    # merge legends from both axes
    handles, labels = ax.get_legend_handles_labels()
    if ax2:
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2; labels += l2
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=min(len(labels), 4))
    fig.tight_layout()
    return fig, ax


def bar_chart(categories, values, title=None, subtitle=None, ylabel=None,
              figsize=(7, 4), money=False, compact_y=False, color=None):
    """Simple vertical bar chart for cross-segment breakdowns (network, country)."""
    fig, ax = plt.subplots(figsize=figsize)
    colors = color or [SERIES_CYCLE[i % len(SERIES_CYCLE)] for i in range(len(categories))]
    bars = ax.bar(categories, values, color=colors, width=0.62, zorder=3)
    ax.grid(axis="y", zorder=0)
    for b, v in zip(bars, values):
        lbl = fmt_money(v) if money else (fmt_compact(v) if compact_y else f"{v:,.0f}")
        ax.text(b.get_x() + b.get_width()/2, v, lbl, ha="center", va="bottom",
                fontsize=9, color=PALETTE["ink"], fontweight="bold")
    if money:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: fmt_money(v)))
    elif compact_y:
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_compact))
    if title:
        ax.set_title(title, loc="left", pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                color=PALETTE["muted"], fontsize=9.5, va="bottom")
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig, ax


def annotate_point(ax, x, y, lines, color=PALETTE["tooltip_bg"]):
    """Dark tooltip-style callout at (x, y). `lines` is a list of strings."""
    txt = "\n".join(lines)
    ax.annotate(txt, xy=(x, y), xytext=(12, 12), textcoords="offset points",
                fontsize=9, color="white", fontweight="medium",
                bbox=dict(boxstyle="round,pad=0.5", fc=color, ec="none"),
                zorder=6)


def save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=PALETTE["page_bg"])
    plt.close(fig)
    return path


if __name__ == "__main__":
    # Smoke test — renders one of each so the module can be verified quickly.
    apply_theme()
    x = ["Jun 27", "Jun 28", "Jun 29", "Jun 30", "Jul 01", "Jul 02", "Jul 03"]
    f, a = line_chart(
        x,
        {"Android": [0.335, 0.335, 0.30, 0.27, 0.267, 0.271, 0.276],
         "iOS":     [0.29, 0.29, 0.28, 0.254, 0.282, 0.273, 0.278]},
        title="Rev/DAU — Tier 1", subtitle="Jun 27 – Jul 03 '26",
        ylabel="Rev per DAU ($)")
    save(f, "/tmp/_smoke_line.png")

    f, a = kpi_card("Android — Revenue", "$2.86K", period="D-2 | Jul 05 '26",
                    deltas=[{"pct": -1.497, "abs": "-43.633", "label": "vs previous day"},
                            {"pct": -21.996, "abs": "-809.314", "label": "vs last week"}])
    save(f, "/tmp/_smoke_card.png")

    f, a = bar_chart(["Unity", "AppLovin", "Meta", "Google"],
                     [42000, 31000, 28500, 19000],
                     title="Net Revenue by Network", subtitle="Last month",
                     money=True)
    save(f, "/tmp/_smoke_bar.png")
    print("OK")
