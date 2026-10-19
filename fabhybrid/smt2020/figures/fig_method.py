"""Figure 3: the proposed method, drawn as the author's own figures are: the things themselves, named.

The records of a tool family as a strip of decisions in time, with one transition bracketed between
two consecutive decisions; value iteration at the price beta; the table over (tightest residual,
time to the next arrival), with the form of the paper's HVLM table; and the furnace whose dispatcher
reads it. No sentences in the artwork; the explanation is the caption's.

  python figures/fig_method.py            -> paper/figures/method.pdf (+ a PNG preview)
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import house_style  # noqa: E402

WIDTH = 5.67                      # text width of the Interact layout, inches
FS = 10.0                         # every text of the figure, near the body's 11 pt (the author, 2026-10-16)
INK = "#1f3b57"                   # the navy outline of the author's figures
GREY = "#8a8f98"
RECORD = "#ebebeb"
RECORD_EDGE = "#3a3a3a"
PAIR = "#c9e3f3"                  # the two decisions of the bracketed transition
START, WAIT = "#1f4e79", "#dbe3ec"   # the colours of the tables figure
FURNACE = "#dbe9f6"
SLOT_FULL = "#4a7fb5"
SLOT_EMPTY = "#ffffff"
FIRE = ["1111", "0111", "0111", "0011", "0000", "0000"]   # the HVLM table of the paper, rows = residual bins

X1, Y1 = 10.0, 3.1                # the drawing's coordinates; the figure is X1 : Y1


def box(ax, x0, y0, w, h, fc, ec=INK, lw=1.3, r=0.12, z=3):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={r}", facecolor=fc,
                                edgecolor=ec, lw=lw, zorder=z))


def arrow(ax, p, q, color=INK, lw=1.3, ms=11, z=2):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, zorder=z,
                                 shrinkA=0, shrinkB=0))


def build():
    house_style.apply(base=FS)
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
                         "mathtext.fontset": "stix"})
    fig = plt.figure(figsize=(WIDTH, WIDTH * Y1 / X1))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, X1)
    ax.set_ylim(0, Y1)
    ax.axis("off")
    yc = 1.62                                     # the centre line of the flow

    # --- the records of a tool family: a strip of decisions in time, two of them one transition
    n, cw, ch = 8, 0.28, 0.46
    x0 = 0.2
    for i in range(n):
        pair = i in (3, 4)
        box(ax, x0 + i * cw + 0.02, yc - ch / 2, cw - 0.04, ch, PAIR if pair else RECORD,
            ec=INK if pair else RECORD_EDGE, lw=1.3 if pair else 0.9, r=0.03, z=5 if pair else 4)
    xe = x0 + n * cw
    ax.text((x0 + xe) / 2, yc + ch / 2 + 0.62, "Records of a tool family", ha="center", va="bottom",
            fontsize=FS, color="black")
    bx0, bx1, by = x0 + 3 * cw + 0.02, x0 + 5 * cw - 0.02, yc + ch / 2 + 0.07
    ax.plot([bx0, bx0, bx1, bx1], [by, by + 0.1, by + 0.1, by], color=INK, lw=1.0, zorder=5)
    ax.text((bx0 + bx1) / 2, by + 0.15, r"$c_n, a_n \rightarrow r_n, \Delta t_n, c_{n+1}$", ha="center",
            va="bottom", fontsize=FS, color="black")
    ty = yc - ch / 2 - 0.2
    arrow(ax, (x0, ty), (xe, ty), color=GREY, lw=1.0, ms=9)
    ax.text((x0 + xe) / 2, ty - 0.08, "time", ha="center", va="top", fontsize=FS, color="black")

    # --- value iteration, with the price as its one input from outside the records
    vx0, vw, vh = 2.85, 1.75, 0.72
    box(ax, vx0, yc - vh / 2, vw, vh, "#ffffff", r=0.08)
    ax.text(vx0 + vw / 2, yc, "Value iteration", ha="center", va="center", fontsize=FS, color="black")
    arrow(ax, (xe + 0.08, yc), (vx0 - 0.04, yc))
    arrow(ax, (vx0 + vw / 2, yc + vh / 2 + 0.62), (vx0 + vw / 2, yc + vh / 2 + 0.04))
    ax.text(vx0 + vw / 2 + 0.1, yc + vh / 2 + 0.36, r"$\beta$", ha="left", va="center", fontsize=FS + 1,
            color="black")

    # --- the table over (tightest residual, time to the next arrival)
    tx0, tw, th = 5.2, 0.38, 0.27
    nT, nN = len(FIRE), len(FIRE[0])
    ttop = yc + nT * th / 2
    for i, row in enumerate(FIRE):
        for j, a in enumerate(row):
            ax.add_patch(Rectangle((tx0 + j * tw, ttop - (i + 1) * th), tw, th, facecolor=START if a == "1" else WAIT,
                                   edgecolor="white", lw=0.8, zorder=4))
    ax.add_patch(Rectangle((tx0, ttop - nT * th), nN * tw, nT * th, fill=False, edgecolor=INK, lw=1.1, zorder=5))
    ax.text(tx0 + nN * tw / 2, ttop + 0.12, "Table", ha="center", va="bottom", fontsize=FS, color="black")
    ax.text(tx0 - 0.1, yc + 0.42, r"$m_{\min}$", rotation=90, ha="right", va="center", fontsize=FS, color="black")
    ax.text(tx0 + nN * tw / 2, ttop - nT * th - 0.1, r"$u$", ha="center", va="top", fontsize=FS, color="black")
    arrow(ax, (vx0 + vw + 0.06, yc - 0.1), (tx0 - 0.05, yc - 0.1))

    # --- the furnace whose dispatcher reads the table, and its two actions
    fx, fw, fh, B, k = 7.6, 0.8, 1.9, 6, 2
    box(ax, fx, yc - fh / 2, fw, fh, FURNACE, r=0.3)
    ax.add_patch(Ellipse((fx + fw / 2, yc + fh / 2), fw, 0.2, facecolor="#c4d8ec", edgecolor=INK, lw=1.1, zorder=4))
    slot_h, gap = 0.16, 0.08
    y_slot = yc - fh / 2 + 0.2
    for i in range(B):
        ax.add_patch(Rectangle((fx + 0.16, y_slot + i * (slot_h + gap)), fw - 0.32, slot_h,
                               facecolor=SLOT_FULL if i < k else SLOT_EMPTY, edgecolor=INK, lw=0.8, zorder=4))
    ax.text(fx + fw / 2, yc + fh / 2 + 0.22, "Furnace", ha="center", va="bottom", fontsize=FS, color="black")
    arrow(ax, (tx0 + nN * tw + 0.08, yc), (fx - 0.05, yc))
    ax0 = fx + fw + 0.22
    arrow(ax, (ax0, yc + 0.12), (ax0 + 0.62, yc + 0.62))
    arrow(ax, (ax0, yc - 0.12), (ax0 + 0.62, yc - 0.62))
    ax.text(ax0 + 0.32, yc + 0.7, "Start", ha="left", va="bottom", fontsize=FS, color="black")
    ax.text(ax0 + 0.32, yc - 0.7, "Wait", ha="left", va="top", fontsize=FS, color="black")
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "paper", "figures", "method.pdf"))
    a = ap.parse_args()
    house_style.save(build(), a.out)


if __name__ == "__main__":
    main()
