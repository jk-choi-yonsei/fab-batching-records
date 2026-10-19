"""Figure: the fitted tables side by side, both scenarios.

One row of maps per scenario and one column per set of records: the timeout rule, the minimum-batch-size
rule and NACH as they stand, and the full-batch rule with a share of its free decisions started at random.
A map is the table over (tightest residual, downwards) x (time to the next arrival, across); a cell
starts the load (dark) or waits (light), and a cell whose entry is not its own estimate, but the entry
of the residual-only table, is marked. (The share of the free decisions at which a table takes the
learner's action is in the records table, not under the map.)

Everything is read from the results file of confirm_report.py (records[...]: fire, own, margin, edges,
agree_with_learner; policies[...]: label). The tables do not depend on the evaluation seeds.

  python figures/fig_tables.py --results ../../experiments/smt2020/final/confirm/results.json \
      --out ../../paper/figures/tables.pdf

  --variant v1      binary maps                                                  (default)
  --variant v2      the learner's map coloured by Q(start) - Q(wait), as the archived fig_table.py did; the
                    other maps binary in the two hues of that scale
  --mark hatch|dot  how a cell that takes the residual-only entry is marked      (default hatch)
  --learner-line    the boundary of the learner's start region drawn on every map
  --yranges         the residual bins labelled as bins (0-0.25, ..., >=4), not by their edges; the
                    arrival bins keep their edges, for which alone there is room under a map
  --png FILE        where the PNG preview goes (default: paper/build/preview, as house_style.save)
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import house_style  # noqa: E402
from confirm_tables import SHORT_LABEL  # noqa: E402    the policies' names, the same as in the tables

EXP = os.path.join(HERE, "..", "..", "..", "experiments", "smt2020")
FABS = ["HVLM", "LVHM"]
COLS = ["timeout", "mbs", "nach", "default"]      # records[...] keys; "default": the full-batch rule, random starts
WIDTH = 5.67                      # text width of the Interact layout, inches
FS = 10.0                         # every text of the figure, near the body's 11 pt (the author, 2026-10-16)
INK = "#111111"

# start, wait, and the mark on each for a cell that takes the residual-only entry
MONO = {"start": "#1f4e79", "wait": "#dbe3ec", "mark_start": "#ffffff", "mark_wait": "#6f8399"}
CMAP = plt.get_cmap("RdBu_r")
RDBU = {"start": CMAP(0.80), "wait": CMAP(0.36), "mark_start": "#5a0f1a", "mark_wait": "#1d4f7c"}
LINE = "#eb6834"                  # the learner's boundary on a binary map (--learner-line)

# inches
PAD = 0.02
YLAB = 0.17                       # the rotated axis label
YTICK = 0.30                      # the tick labels of the first column: bin edges
YTICK_RANGES = 0.52               # the same as bins (--yranges)
STRIP = 0.17                      # the scenario name at the right
GAP = 0.10                        # between maps
CELL_H = 0.16
HEADER = 0.16                     # "Table fitted from the records of"
TITLE = 0.13                      # one line of a column title
XTICK = 0.15
NOTE = 0.0                        # no line under a map: the agreement is in the records table
ROWGAP = 0.10
XLAB = 0.17
LEGEND = 0.22
CBAR = 0.27                       # v2: the line of the colour bar under the legend
K = FS / 8.0                      # the sizes above were set for 8 pt type: those that hold text scale with it
YLAB, YTICK, YTICK_RANGES, STRIP, GAP = (x * K for x in (YLAB, YTICK, YTICK_RANGES, STRIP, GAP))
HEADER, TITLE, XTICK, ROWGAP, XLAB, LEGEND, CBAR = (x * K for x in (HEADER, TITLE, XTICK, ROWGAP, XLAB, LEGEND, CBAR))
CELL_H = CELL_H * (1 + (K - 1) / 2)


def text_width(fig, s, **kw):
    t = fig.text(0, 0, s, **kw)
    w = t.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi
    t.remove()
    return w


def edge_ticks(edges):
    """ticks on the cell boundaries, labelled with the bin edges; the last bin is open"""
    return np.arange(len(edges) - 1) - 0.5, [f"{e:g}" for e in edges[:-1]]


def range_ticks(edges):
    """ticks at the cell centres, labelled with the bin as fig_table.py did (0–0.25, ..., >=4)"""
    e = edges
    return np.arange(len(e) - 1), [f"{e[j]:g}–{e[j + 1]:g}" if e[j + 1] < 24 else f"$\\geq${e[j]:g}"
                                   for j in range(len(e) - 1)]


def boundary(ax, fire, **kw):
    """the edges between neighbouring cells of different action"""
    nT, nN = fire.shape
    for i in range(nT):
        for j in range(nN):
            if j + 1 < nN and fire[i, j] != fire[i, j + 1]:
                ax.plot([j + 0.5, j + 0.5], [i - 0.5, i + 0.5], **kw)
            if i + 1 < nT and fire[i, j] != fire[i + 1, j]:
                ax.plot([j - 0.5, j + 0.5], [i + 0.5, i + 0.5], **kw)


def draw_map(ax, T, colours, mark, margin_norm=None):
    fire, own = np.array(T["fire"], int), np.array(T["own"], int)
    nT, nN = fire.shape
    m = np.array(T["margin"], float) if margin_norm is not None else None
    inset = 0.06                 # the top row stops a hair below the frame: in some viewers a dark cell flush
    for i in range(nT):          # with the frame's line covers it and looks as if it stuck out above
        for j in range(nN):
            a = "start" if fire[i, j] else "wait"
            face = CMAP(margin_norm(m[i, j])) if m is not None else colours[a]
            y0 = i - 0.5 + (inset if i == 0 else 0.0)
            ax.add_patch(Rectangle((j - 0.5, y0), 1, i + 0.5 - y0, facecolor=face, edgecolor="white", lw=0.7))
            if own[i, j]:
                continue
            if m is not None:                         # on the colour scale: dark ink, light where the cell is dark
                mc = "#ffffff" if abs(margin_norm(m[i, j]) - 0.5) > 0.33 else "#333333"
            else:
                mc = colours["mark_" + a]
            if mark == "dot":
                ax.plot(j, i, "o", ms=2.6, color=mc, mec="none", zorder=3)
            else:
                ax.add_patch(Rectangle((j - 0.46, i - 0.46), 0.92, 0.92, fill=False, hatch="/////",
                                       edgecolor=mc, lw=0, zorder=3))
    ax.set_xlim(-0.5, nN - 0.5)
    ax.set_ylim(nT - 0.5, -0.5)
    for s in ax.spines.values():
        s.set_linewidth(0.6)
        s.set_color("#333333")


def column_title(res, key):
    rules = {res[fab]["records"][key]["rule"] for fab in FABS}
    rule = rules.pop()
    label = SHORT_LABEL.get(rule) or res[FABS[0]]["policies"][rule]["label"].split(",")[0]
    return label.replace(", ", ",\n", 1)


def note(T, key):
    if key == "default":
        return "random starts"
    a = T.get("agree_with_learner")
    return "–" if a is None else f"same action: {100 * a:.1f}%"


def build(res, variant, mark, learner_line, yranges=False):
    house_style.apply(base=FS)
    house_style.serif()
    plt.rcParams.update({"axes.titlesize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                         "legend.fontsize": FS, "hatch.linewidth": 0.55})
    colours = RDBU if variant == "v2" else MONO
    T0 = res[FABS[0]]["records"][COLS[0]]
    nT, nN = np.array(T0["fire"]).shape
    map_h = nT * CELL_H
    n_title = max(column_title(res, k).count("\n") + 1 for k in COLS)
    top = HEADER + n_title * TITLE + 0.04
    row_h = map_h + XTICK + NOTE
    legend_h = LEGEND + (CBAR if variant == "v2" else 0.0)
    height = PAD + top + len(FABS) * row_h + (len(FABS) - 1) * ROWGAP + XLAB + legend_h + PAD
    left = PAD + YLAB + (YTICK_RANGES if yranges else YTICK)
    map_w = (WIDTH - left - STRIP - PAD - (len(COLS) - 1) * GAP) / len(COLS)

    fig = plt.figure(figsize=(WIDTH, height))
    fx, fy = (lambda x: x / WIDTH), (lambda y: y / height)
    xs = [left + c * (map_w + GAP) for c in range(len(COLS))]

    norm = None
    if variant == "v2":                                # one scale for the learner's two maps
        v = max(np.abs(np.array(res[fab]["records"]["default"]["margin"], float)).max() for fab in FABS)
        norm = TwoSlopeNorm(0.0, -v, v)

    # header and column titles
    y = height - PAD
    fig.text(fx((xs[0] + xs[-1] + map_w) / 2), fy(y - HEADER / 2), "Table fitted from the records of",
             ha="center", va="center", fontsize=FS, color=INK)
    y -= top
    for c, key in enumerate(COLS):
        fig.text(fx(xs[c] + map_w / 2), fy(y + 0.035), column_title(res, key), ha="center", va="bottom",
                 fontsize=FS, color=INK, linespacing=1.15)

    y_maps_top = y
    for r, fab in enumerate(FABS):
        y -= map_h
        y_maps_bottom = y
        learner = np.array(res[fab]["records"]["default"]["fire"], int)
        for c, key in enumerate(COLS):
            T = res[fab]["records"][key]
            ax = fig.add_axes([fx(xs[c]), fy(y), fx(map_w), fy(map_h)])
            first = variant == "v2" and key == "default"
            draw_map(ax, T, colours, mark, norm if first else None)
            if first:
                boundary(ax, learner, color="black", lw=1.6, solid_capstyle="projecting", zorder=4)
            elif learner_line:
                boundary(ax, learner, color=LINE, lw=1.3, solid_capstyle="projecting", zorder=4)
            xt, xl = edge_ticks(T["edges"]["nxt"])
            yt, yl = (range_ticks if yranges else edge_ticks)(T["edges"]["tightest"])
            ax.set_xticks(xt); ax.set_xticklabels(xl)
            ax.set_yticks(yt); ax.set_yticklabels(yl if c == 0 else [])
            ax.tick_params(axis="x", length=2.5, pad=1.5, width=0.6)
            ax.tick_params(axis="y", length=2.5 if c == 0 and not yranges else 0, pad=2.5 if yranges else 1.5,
                           width=0.6)
        fig.text(fx(WIDTH - PAD - STRIP / 2 + 0.02), fy(y + map_h / 2), fab, rotation=270, ha="center",
                 va="center", fontsize=FS, color=INK)
        y -= XTICK + NOTE + (ROWGAP if r + 1 < len(FABS) else 0)
    # one label for both rows of maps, as the label of the time to the next arrival is one for all columns
    fig.text(fx(PAD + YLAB / 2), fy((y_maps_top + y_maps_bottom) / 2), "tightest residual $m_{\\min}$ (h)",
             rotation=90, ha="center", va="center", fontsize=FS, color=INK)

    y -= XLAB
    fig.text(fx((xs[0] + xs[-1] + map_w) / 2), fy(y + XLAB / 2), "time to the next arrival $u$ (h)",
             ha="center", va="center", fontsize=FS, color=INK)

    # one legend for all maps
    y -= LEGEND
    xm = (xs[0] + xs[-1] + map_w) / 2
    handles = [Patch(facecolor=colours["start"], edgecolor="none", label="start"),
               Patch(facecolor=colours["wait"], edgecolor="none", label="wait")]
    if mark == "dot":
        handles.append(Line2D([], [], marker="o", ms=2.6, color="#555555", mec="none", lw=0,
                              label="entry of the residual-only table"))
    else:
        handles.append(Patch(facecolor="white", edgecolor="#555555", hatch="/////", lw=0.5,
                             label="entry of the residual-only table"))
    if learner_line and variant != "v2":
        handles.append(Line2D([], [], color=LINE, lw=1.3, label="start region of the table in the last column"))
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(fx(xm), fy(y + LEGEND / 2)), ncol=len(handles),
               frameon=False, fontsize=FS, handlelength=1.3, handleheight=0.9, columnspacing=1.6,
               handletextpad=0.5, borderaxespad=0.0)
    if variant == "v2":                                # the scale of the learner's maps and their line
        y -= CBAR
        t1 = "learner: $Q(\\mathrm{start}) - Q(\\mathrm{wait})$ (lots)"
        t2 = "boundary of its start region"
        cw, lw_ = 1.0, 0.24
        w1, w2 = text_width(fig, t1, fontsize=FS), text_width(fig, t2, fontsize=FS)
        x = xm - (cw + 0.07 + w1 + 0.24 + lw_ + 0.06 + w2) / 2
        yb = y + CBAR - 0.085                          # the centre of the bar
        cax = fig.add_axes([fx(x), fy(yb - 0.032), fx(cw), fy(0.064)])
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=CMAP), cax=cax, orientation="horizontal")
        cb.outline.set_linewidth(0.5)
        t = np.floor(v * 10) / 10 if v >= 0.1 else np.floor(v * 100) / 100
        cb.set_ticks([-t, 0.0, t] if t > 0 else [0.0])
        cb.ax.tick_params(labelsize=FS, length=2, pad=1, width=0.6)
        x += cw + 0.07
        fig.text(fx(x), fy(yb), t1, ha="left", va="center", fontsize=FS, color=INK)
        x += w1 + 0.24
        fig.add_artist(Line2D([fx(x), fx(x + lw_)], [fy(yb), fy(yb)], color="black", lw=1.6,
                              transform=fig.transFigure))
        fig.text(fx(x + lw_ + 0.06), fy(yb), t2, ha="left", va="center", fontsize=FS, color=INK)
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
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "paper", "figures", "tables.pdf"))
    ap.add_argument("--png", default=None, help="PNG preview (default: paper/build/preview/<name>.png)")
    ap.add_argument("--variant", choices=("v1", "v2"), default="v1")
    ap.add_argument("--mark", choices=("hatch", "dot"), default="hatch")
    ap.add_argument("--learner-line", action="store_true",
                    help="the boundary of the learner's start region on every map")
    ap.add_argument("--yranges", action="store_true",
                    help="label the residual bins as fig_table.py did (0-0.25, ..., >=4) instead of their edges")
    a = ap.parse_args()
    res = json.load(open(a.results, encoding="utf-8"))
    fig = build(res, a.variant, a.mark, a.learner_line, a.yranges)
    save(fig, a.out, a.png)
    for fab in FABS:
        for key in COLS:
            T = res[fab]["records"][key]
            rows = "|".join("".join(str(int(x)) for x in row) for row in T["fire"])
            own = int(np.array(T["own"]).sum())
            ag = T.get("agree_with_learner")
            print(f"  {fab} {key:8s} start {rows}  own {own:2d}/{np.array(T['own']).size}  "
                  f"same as the learner {'--' if ag is None else format(100 * ag, '.1f') + '%'}  ({T.get('artefact')})")


if __name__ == "__main__":
    main()
