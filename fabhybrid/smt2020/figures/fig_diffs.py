"""Figure 5: the gain of each fitted table in completed lots per day, paired by seed, both scenarios.

Rows, in two groups: the table fitted from a rule's own records over that rule, and the fitted tables over the
remaining-time threshold tuned in the simulator (the last row, the table of the full-batch records with random
starts). A row shows the per-seed differences (small dots; the vertical offset is a fixed function of the seed's position, so a seed sits at the
same height in every row), their mean with its 95% interval, and at the right the number of seeds
on which the difference is positive, out of the untied seeds.

Everything is read from the results file of confirm_report.py (comparisons[...]: mean, lo, hi, wins,
losses, per_seed; policies[...]: label), so the same call serves the development record and the block.

  python figures/fig_diffs.py --results ../../experiments/smt2020/final/confirm/results.json \
      --out ../../paper/figures/diffs.pdf

  --variant v1   two panels (HVLM, LVHM), per-seed differences shown        (default)
  --variant v2   two panels, means and intervals only
  --variant v3   one panel, the two scenarios as two colours and markers in each row
  --strip        v1 with the per-seed differences in a strip under the mean, not around it
  --no-dots      drop the per-seed differences from v1 or v3
  --params       row labels with the rule's parameter (q = 3, T = 1 h, h = 1.5 h)
  --png FILE     where the PNG preview goes (default: paper/build/preview, as house_style.save)
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import house_style  # noqa: E402
from confirm_tables import SHORT_LABEL  # noqa: E402    the policies' names, the same as in the tables

EXP = os.path.join(HERE, "..", "..", "..", "experiments", "smt2020")
FABS = ["HVLM", "LVHM"]
WIDTH = 5.67                      # text width of the Interact layout, inches
FS = 10.0                         # every text of the figure, near the body's 11 pt (the author, 2026-10-16)

# (heading, [(comparison key, policy whose label names the row), ...]); a group of one row is
# labelled by its heading alone. A row is named by the rule whose records the table was fitted from.
GROUPS = [
    ("Gain over the rule that made the records",
     [("tbl_timeout-timeout", "timeout"), ("tbl_mbs-mbs", "mbs"), ("tbl_nach-nach", "nach")]),
    ("Gain over the remaining-time threshold tuned in the simulator",
     [("tbl_timeout-clock", "timeout"), ("tbl_mbs-clock", "mbs"), ("tbl_nach-clock", "nach"),
      ("learner-clock", "logging")]),
]

INK = "#111111"
MEAN = "#1f4e79"                  # the mean and its interval: the blue of the tables figure
DOT = "#8ea6bf"                   # per-seed differences: the lighter step of the same hue
ZERO = "#4d4d4d"
GRID = "#e3e3e3"
SCEN = {"HVLM": ("#2a78d6", "o"), "LVHM": ("#eb6834", "s")}   # v3: two hues that stay apart under protan/deutan vision

# inches
PAD = 0.02
INDENT = 0.11                     # rows under a heading
GAP_L = 0.07                      # labels to the panel
GAP_P = 0.13                      # between the two panels (after the first panel's counts)
HEAD = 0.17                       # a heading line
SPACE = 0.07                      # above a heading line or a one-row group
XTICK = 0.16                      # the tick labels under the last band
XLAB = 0.17
K = FS / 8.0                      # the sizes above were set for 8 pt type: those that hold text scale with it
INDENT, GAP_L, GAP_P, HEAD, SPACE, XTICK, XLAB = (x * K for x in (INDENT, GAP_L, GAP_P, HEAD, SPACE, XTICK, XLAB))


def text_width(fig, s, **kw):
    t = fig.text(0, 0, s, **kw)
    w = t.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi
    t.remove()
    return w


def jitter(n):
    """a fixed low-discrepancy offset in [-0.5, 0.5) for the i-th seed"""
    return (np.arange(n) * 0.6180339887498949) % 1.0 - 0.5


def row_name(res, fab, policy, params):
    label = res[fab]["policies"][policy]["label"]
    if params:
        return label
    return SHORT_LABEL.get(policy) or label.split(",")[0]


def wins_text(c):
    if not c or not c.get("n"):
        return "–"
    return f"{c['wins']}/{c['wins'] + c['losses']}"


def x_limits(res, fabs, dots):
    lo, hi = 0.0, 0.0
    for fab in fabs:
        for _, rows in GROUPS:
            for key, *_ in rows:
                c = res[fab]["comparisons"].get(key)
                if not c or not c.get("n"):
                    continue
                v = [x for x in (c["mean"], c["lo"], c["hi"]) if x is not None]   # one seed: no interval
                if dots:
                    v += [x for x in c["per_seed"] if x is not None]
                lo, hi = min(lo, min(v)), max(hi, max(v))
    if hi - lo < 1e-9:                                   # nothing to show yet
        lo, hi = -1.0, 1.0
    pad = 0.045 * (hi - lo)
    return lo - pad, hi + pad


def draw_row(ax, c, y, dots, colour, marker, amp, dot_colour, y_dots=None):
    """the mean and its interval at height y; the per-seed differences around y_dots (default: y)"""
    if not c or not c.get("n"):
        return
    if dots:
        d = np.array([np.nan if x is None else x for x in c["per_seed"]], float)
        ok = ~np.isnan(d)
        ax.scatter(d[ok], (y if y_dots is None else y_dots) + amp * jitter(len(d))[ok], s=3.6,
                   color=dot_colour, alpha=0.45, linewidths=0, zorder=2, clip_on=False)
    xerr = None if c["lo"] is None else [[c["mean"] - c["lo"]], [c["hi"] - c["mean"]]]
    if dots and xerr:                          # a white edge keeps the interval readable over the dots
        ax.errorbar(c["mean"], y, xerr=xerr, fmt="none", ecolor="white", elinewidth=2.8, capsize=2.6,
                    capthick=2.4, zorder=3)
    ax.errorbar(c["mean"], y, xerr=xerr, fmt=marker, ms=3.6 if marker == "o" else 3.3, color=colour,
                mfc=colour, mec="white", mew=0.5, elinewidth=1.2, capsize=2.0, capthick=0.9, zorder=4)


def build(res, layout, dots, params, strip=False):
    house_style.apply(base=FS)
    house_style.serif()
    plt.rcParams.update({"axes.titlesize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                         "legend.fontsize": FS})
    single = layout == "single"
    panels = [FABS] if single else [[f] for f in FABS]          # the scenarios drawn in each panel
    row_h = K * ((0.30 if dots else 0.25) if single else ((0.22 if strip else 0.19) if dots else 0.17))
    top = 2 * HEAD if single else HEAD + 0.02                     # the title line(s)

    # ---- vertical layout, top down: (kind, height, payload)
    blocks = [("title", top, None)]
    for gi, (head, rows) in enumerate(GROUPS):
        one = len(rows) == 1
        if gi > 0:
            blocks.append(("space", SPACE, None))
        if not one:
            blocks.append(("head", HEAD, head))
        blocks.append(("band", len(rows) * row_h, gi))
    blocks.append(("axis", XTICK + XLAB, None))
    height = PAD + sum(h for _, h, _ in blocks) + PAD

    fig = plt.figure(figsize=(WIDTH, height))
    fx, fy = (lambda x: x / WIDTH), (lambda y: y / height)

    # ---- horizontal layout
    names = {}                                           # a group of one row is named by its heading
    for gi, (head, rows) in enumerate(GROUPS):
        for ri, (_, pol) in enumerate(rows):
            name = row_name(res, FABS[0], pol, params)
            names[(gi, ri)] = name if len(rows) > 1 else head
    label_w = max(text_width(fig, names[(gi, ri)], fontsize=FS) + (INDENT if len(rows) > 1 else 0.0)
                  for gi, (_, rows) in enumerate(GROUPS) for ri in range(len(rows)))
    if single:
        count_w = max(text_width(fig, "32/32", fontsize=FS) + 0.10,
                      max(text_width(fig, f, fontsize=FS) for f in FABS) + 0.16)
        n_counts = len(FABS)
    else:
        count_w = max(text_width(fig, "32/32", fontsize=FS), text_width(fig, "Wins", fontsize=FS)) + 0.06
        n_counts = 1
    x0 = PAD + label_w + GAP_L
    n_pan = len(panels)
    panel_w = (WIDTH - PAD - x0 - n_pan * n_counts * count_w - (n_pan - 1) * GAP_P) / n_pan
    px = [x0 + p * (panel_w + n_counts * count_w + GAP_P) for p in range(n_pan)]

    xlim = x_limits(res, FABS, dots)
    step = 1.0 if xlim[1] - xlim[0] <= 9 else 2.0

    # ---- draw, block by block
    y = height - PAD
    first_head = None                                    # every heading has its own line below the titles
    last_band = max(i for i, b in enumerate(blocks) if b[0] == "band")
    for bi, (kind, h, payload) in enumerate(blocks):
        y -= h
        if kind == "title":
            yc = y + HEAD / 2                                    # the line just above the first band
            if first_head:
                fig.text(fx(PAD), fy(yc), first_head, ha="left", va="center", fontsize=FS, color=INK)
            for p, fabs in enumerate(panels):
                if single:
                    for k, fab in enumerate(fabs):               # the legend heads the count columns
                        col, mrk = SCEN[fab]
                        xr = px[p] + panel_w + (k + 1) * count_w
                        tw = text_width(fig, fab, fontsize=FS)
                        fig.text(fx(xr), fy(yc), fab, ha="right", va="center", fontsize=FS, color=INK)
                        fig.add_artist(Line2D([fx(xr - tw - 0.075)], [fy(yc)], marker=mrk, ms=4.2, color=col,
                                              mec="white", mew=0.5, lw=0, transform=fig.transFigure))
                    xm = px[p] + panel_w + count_w * len(fabs) / 2 + 0.04
                    fig.text(fx(xm), fy(yc + HEAD), "Wins", ha="center", va="center", fontsize=FS, color=INK)
                else:
                    fig.text(fx(px[p] + panel_w / 2), fy(yc), fabs[0], ha="center", va="center",
                             fontsize=FS, color=INK)
                    fig.text(fx(px[p] + panel_w + count_w), fy(yc), "Wins", ha="right", va="center",
                             fontsize=FS, color=INK)
        elif kind == "head":
            fig.text(fx(PAD), fy(y + HEAD / 2 - 0.01), payload, ha="left", va="center", fontsize=FS, color=INK)
        elif kind == "band":
            head, rows = GROUPS[payload]
            one = len(rows) == 1
            for ri in range(len(rows)):
                yc = y + h - (ri + 0.5) * row_h
                fig.text(fx(PAD + (0 if one else INDENT)), fy(yc), names[(payload, ri)],
                         ha="left", va="center", fontsize=FS, color=INK)
            for p, fabs in enumerate(panels):
                ax = fig.add_axes([fx(px[p]), fy(y), fx(panel_w), fy(h)])
                ax.set_xlim(*xlim)
                ax.set_ylim(len(rows) - 0.5, -0.5)
                ax.xaxis.set_major_locator(MultipleLocator(step))
                ax.set_axisbelow(True)
                ax.grid(axis="x", color=GRID, lw=0.6)
                ax.axvline(0.0, color=ZERO, lw=0.8, zorder=1)
                ax.set_yticks([])
                for s in ("left", "right", "top"):
                    ax.spines[s].set_visible(False)
                ax.set_facecolor("none")
                if bi == last_band:
                    ax.tick_params(axis="x", length=3, pad=2)
                else:
                    ax.spines["bottom"].set_visible(False)
                    ax.tick_params(axis="x", length=0, labelbottom=False)
                for ri, (key, *_) in enumerate(rows):
                    yc = y + h - (ri + 0.5) * row_h
                    for k, fab in enumerate(fabs):
                        c = res[fab]["comparisons"].get(key)
                        if single:
                            col, mrk = SCEN[fab]
                            draw_row(ax, c, ri + (k - 0.5) * 0.42, dots, col, mrk, 0.24, col)
                        elif strip and dots:
                            draw_row(ax, c, ri - 0.22, dots, MEAN, "o", 0.30, DOT, y_dots=ri + 0.13)
                        else:
                            draw_row(ax, c, ri, dots, MEAN, "o", 0.52, DOT)
                        fig.text(fx(px[p] + panel_w + (k + 1) * count_w), fy(yc), wins_text(c),
                                 ha="right", va="center", fontsize=FS, color=INK)
        elif kind == "axis":
            xm = (px[0] + px[-1] + panel_w) / 2
            fig.text(fx(xm), fy(y + XLAB / 2 - 0.01), "gain in completed lots per day",
                     ha="center", va="center", fontsize=FS, color=INK)
    return fig


def save(fig, out, png):
    if png is None:
        house_style.save(fig, out)
        return
    out, png = os.path.abspath(out), os.path.abspath(png)
    for p in (out, png):
        os.makedirs(os.path.dirname(p), exist_ok=True)
    fig.savefig(out)
    fig.savefig(png, dpi=200)
    print("wrote", out, "and", png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(EXP, "final", "confirm", "results.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "paper", "figures", "diffs.pdf"))
    ap.add_argument("--png", default=None, help="PNG preview (default: paper/build/preview/<name>.png)")
    ap.add_argument("--variant", choices=("v1", "v2", "v3"), default="v1")
    ap.add_argument("--no-dots", action="store_true", help="means and intervals only")
    ap.add_argument("--params", action="store_true", help="row labels with the rule's parameter")
    ap.add_argument("--strip", action="store_true",
                    help="v1: the per-seed differences in a strip under the mean, not around it")
    a = ap.parse_args()
    res = json.load(open(a.results, encoding="utf-8"))
    layout = "single" if a.variant == "v3" else "panels"
    dots = a.variant != "v2" and not a.no_dots
    fig = build(res, layout, dots, a.params, a.strip)
    save(fig, a.out, a.png)
    for fab in FABS:
        for _, rows in GROUPS:
            for key, *_ in rows:
                c = res[fab]["comparisons"].get(key)
                if c and c.get("n"):
                    ci = "[no interval]" if c["lo"] is None else f"[{c['lo']:.2f}, {c['hi']:.2f}]"
                    print(f"  {fab} {key:22s} n {c['n']:2d}  {c['mean']:+.2f} {ci}  wins {wins_text(c)}")
                else:
                    print(f"  {fab} {key:22s} no paired seeds")


if __name__ == "__main__":
    main()
