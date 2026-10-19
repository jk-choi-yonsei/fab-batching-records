"""Figure: the optimal decision of the isolated station over (tightest residual, time to the next
announced arrival), read from the instances already solved by theory/announced_station.py.

Nothing is computed here. experiments/smt2020/theory/announced.json holds, for each of its 540
instances (kappa in {0.25, 0.5, 1}; the manuscript's 720 add the 180 at kappa = 0.1 of
announced_kappa0p1_*.json, as theory/announced_summary.py prints), the optimal action at the
under-full decisions by (u, m) (the field actions_by_u): start in every state of the cell, wait in
every state, or start in some and wait in others, by the rest of the state (the other residuals, the
number of waiting lots, the later announcements). The map has the orientation of fig_tables.py:
the residual downwards, the time to the next arrival across. The line bounds the cells with
m <= min(u, L + 1), in which Proposition 1 proves that starting is optimal.

  python figures/fig_station.py --out ../../paper/figures/station.pdf

  --variant v1      one instance (default: the centre of the solved grid), drawn at 0.6 of the text
                    width: \\includegraphics[width=0.6\\textwidth] keeps its text at 8 pt
  --variant v2      the same instance at several costs of waiting (--etas), side by side at the
                    text width
  --instance ...    B=3,R=8,L=4,p=0.25,kappa=0.5,eta=0.05
  --png FILE        where the PNG preview goes (default: paper/build/preview, as house_style.save)
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import house_style  # noqa: E402

EXP = os.path.join(HERE, "..", "..", "..", "experiments", "smt2020")
WIDTH = 5.67                      # text width of the Interact layout, inches
ONE_FRAC = 0.6                    # v1 is drawn at this share of the text width
FS = 10.0                         # every text of the figure, near the body's 11 pt (the author, 2026-10-16)
INK = "#111111"

# one hue, three steps: start in every state of the cell, in some, in none (as fig_tables.py, v1)
FACE = {"F": "#1f4e79", "?": "#8ea6bf", "W": "#dbe3ec", "T": "#8ea6bf", ".": "#ffffff"}
NAME = {"F": "start", "?": "start or wait, by the\nrest of the state", "W": "wait",
        "T": "start or wait\n(equal value)"}
LINE = "#111111"                  # black, with a white edge: not the hue of fig_tables.py's line

# inches
PAD = 0.02
YLAB = 0.17
YTICK = 0.16
CELL_H = 0.19
XTICK = 0.15
XLAB = 0.17
TITLE = 0.18
K = FS / 8.0                      # the sizes above were set for 8 pt type: those that hold text scale with it
YLAB, YTICK, XTICK, XLAB, TITLE = (x * K for x in (YLAB, YTICK, XTICK, XLAB, TITLE))
CELL_H = CELL_H * (1 + (K - 1) / 2)


def pick(grid, spec):
    want = {"gamma": 0.99}
    for item in spec.split(","):
        k, v = item.split("=")
        want[{"eta": "c"}.get(k.strip(), k.strip())] = float(v)
    hit = [g for g in grid if all(abs(float(g[k]) - v) < 1e-9 for k, v in want.items())]
    if len(hit) != 1:
        raise SystemExit(f"{len(hit)} solved instances match {spec}")
    return hit[0]


def draw(ax, inst, first):
    rows = inst["actions_by_u"]                           # u -> string over m = 1..R
    cols = list(rows)                                     # "1", ..., "L", "none"
    R, L = int(inst["R"]), int(inst["L"])
    for j, u in enumerate(cols):
        for i, a in enumerate(rows[u]):
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=FACE[a], edgecolor="white", lw=0.7,
                                   hatch="/////" if a == "T" else None))
    # the cells with m <= min(u, L + 1): a staircase under them
    xs, ys = [], []
    for j, u in enumerate(cols):
        k = min(L + 1 if u == "none" else int(u), L + 1, R)
        xs += [j - 0.5, j + 0.5]
        ys += [k - 0.5, k - 0.5]
    ax.plot(xs, ys, color="white", lw=2.6, solid_capstyle="butt", zorder=3)
    ax.plot(xs, ys, color=LINE, lw=1.4, solid_capstyle="butt", zorder=4)
    ax.set_xlim(-0.5, len(cols) - 0.5)
    ax.set_ylim(R - 0.5, -0.5)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(range(R))
    ax.set_yticklabels([str(m) for m in range(1, R + 1)] if first else [])
    ax.tick_params(axis="x", length=0, pad=2.5)
    ax.tick_params(axis="y", length=0, pad=2.5)
    for s in ax.spines.values():
        s.set_linewidth(0.6)
        s.set_color("#333333")
    return {a for u in cols for a in rows[u]}


def handles(present, wrap):
    out = [Patch(facecolor=FACE[a], edgecolor="white" if a == "T" else "none", lw=0,
                 hatch="/////" if a == "T" else None, label=NAME[a] if wrap else NAME[a].replace("\n", " "))
           for a in ("F", "?", "T", "W") if a in present]
    out.append(Line2D([], [], color=LINE, lw=1.4, label="$m \\leq \\min(u, L+1)$"))
    return out


def build(insts, titles):
    house_style.apply(base=FS)
    house_style.serif()
    plt.rcParams.update({"axes.titlesize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                         "legend.fontsize": FS, "hatch.linewidth": 0.55})
    one = len(insts) == 1
    R = int(insts[0]["R"])
    ncol = len(insts[0]["actions_by_u"])
    map_h = R * CELL_H
    left = PAD + YLAB + YTICK
    xlabel = "time to the next announced arrival $u$ (periods)"
    if one:                                               # the map with its legend at the right
        map_w, gap = ncol * 0.32, 0.0
        width = ONE_FRAC * WIDTH                          # \includegraphics[width=0.6\textwidth] keeps 8 pt
        xlabel = xlabel.replace("announced ", "announced\n")   # one line is wider than the map
        xlab = XLAB + 0.13
        height = PAD + 0.04 + map_h + XTICK + xlab + PAD
        top = PAD + 0.04
    else:                                                 # maps side by side at the text width, legend under them
        gap, width, xlab = 0.14, WIDTH, XLAB
        map_w = (width - left - PAD - (len(insts) - 1) * gap) / len(insts)
        height = PAD + TITLE + map_h + XTICK + xlab + 0.24 + PAD
        top = PAD + TITLE
    fig = plt.figure(figsize=(width, height))
    fx, fy = (lambda x: x / width), (lambda y: y / height)
    y = height - top - map_h
    present = set()
    for c, inst in enumerate(insts):
        x = left + c * (map_w + gap)
        ax = fig.add_axes([fx(x), fy(y), fx(map_w), fy(map_h)])
        present |= draw(ax, inst, c == 0)
        if not one:
            fig.text(fx(x + map_w / 2), fy(y + map_h + TITLE / 2), titles[c], ha="center", va="center",
                     fontsize=FS, color=INK)
    fig.text(fx(PAD + YLAB / 2), fy(y + map_h / 2), "tightest residual $m$ (periods)", rotation=90,
             ha="center", va="center", fontsize=FS, color=INK)
    xm = left + (len(insts) * map_w + (len(insts) - 1) * gap) / 2
    fig.text(fx(xm), fy(y - XTICK - xlab / 2), xlabel, ha="center", va="center", fontsize=FS, color=INK,
             linespacing=1.15)
    if one:
        fig.legend(handles=handles(present, True), loc="upper left",
                   bbox_to_anchor=(fx(left + map_w + 0.12), fy(y + map_h + 0.02)), frameon=False, fontsize=FS,
                   handlelength=1.3, handleheight=0.9, labelspacing=0.75, handletextpad=0.5, borderaxespad=0.0)
    else:
        fig.legend(handles=handles(present, False), loc="center",
                   bbox_to_anchor=(fx(xm), fy(y - XTICK - xlab - 0.12)), ncol=4, frameon=False, fontsize=FS,
                   handlelength=1.3, handleheight=0.9, columnspacing=1.5, handletextpad=0.5, borderaxespad=0.0)
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
    ap.add_argument("--results", default=os.path.join(EXP, "theory", "announced.json"),
                    help="the solved grid written by theory/announced_station.py --grid")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "paper", "figures", "station.pdf"))
    ap.add_argument("--png", default=None, help="PNG preview (default: paper/build/preview/<name>.png)")
    ap.add_argument("--variant", choices=("v1", "v2"), default="v1")
    ap.add_argument("--instance", default="B=3,R=8,L=4,p=0.25,kappa=0.5,eta=0.05",
                    help="the instance of the grid (eta is the cost of a period of waiting, c in the file)")
    ap.add_argument("--etas", default="0,0.05,0.2", help="v2: the waiting costs shown side by side")
    a = ap.parse_args()
    grid = json.load(open(a.results, encoding="utf-8"))
    if a.variant == "v1":
        insts, titles = [pick(grid, a.instance)], [""]
    else:
        base = ",".join(x for x in a.instance.split(",") if not x.strip().startswith("eta"))
        etas = [float(x) for x in a.etas.split(",")]
        insts = [pick(grid, f"{base},eta={e}") for e in etas]
        titles = [f"waiting cost $\\eta = {e:g}$" for e in etas]
    fig = build(insts, titles)
    save(fig, a.out, a.png)
    for g in insts:
        cells, mixed = g["um_cells"], g["um_mixed"]
        print(f"  B {g['B']}  R {g['R']}  L {g['L']}  p {g['p']}  kappa {g['kappa']}  eta {g['c']}  gamma {g['gamma']}: "
              f"the rest of the state decides in {mixed} of {cells} cells")
        for u, row in g["actions_by_u"].items():
            print(f"      u = {u:>4s}   m = 1..{g['R']}: {row}")


if __name__ == "__main__":
    main()
