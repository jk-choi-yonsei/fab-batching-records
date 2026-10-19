"""Figure 1: the setting, drawn as the author's own figures are: the things themselves, labelled by name.

A source step, the path to a furnace under a queue-time limit tau, lots waiting in front of the furnace
with their residuals (the tightest marked), the next lot on its way with u, the furnace holding an
under-full load, and the two actions. No numbers, no sentences; the explanation is the caption's.

  python figures/fig_setting.py            -> paper/figures/setting.pdf (+ a PNG preview)
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Ellipse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import house_style  # noqa: E402

WIDTH = 5.67                      # text width of the Interact layout, inches
FS = 10.0                         # every text of the figure, near the body's 11 pt (the author, 2026-10-16)
INK = "#1f3b57"                   # the navy outline of the author's figures
GREY = "#8a8f98"
LOT = "#e8e8e8"
LOT_EDGE = "#3a3a3a"
TIGHT = "#f6c9b4"
TIGHT_EDGE = "#c8511b"
FURNACE = "#dbe9f6"
SOURCE = "#e2f0d9"
SLOT_FULL = "#4a7fb5"
SLOT_EMPTY = "#ffffff"
Y0, Y1 = 0.35, 4.55


def box(ax, x0, y0, w, h, fc, ec=INK, lw=1.3, r=0.12, z=3):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={r}", facecolor=fc,
                                edgecolor=ec, lw=lw, zorder=z))


def arrow(ax, p, q, color=INK, lw=1.3, ls="-", ms=11, z=2):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, linestyle=ls,
                                 zorder=z, shrinkA=0, shrinkB=0))


def lot(ax, x, y, s, fc, ec, label=None, label_color=None):
    """A lot drawn as a carrier: a box with two rails, like the cassettes of the author's figures."""
    box(ax, x - s / 2, y - s / 2, s, s, fc, ec=ec, lw=1.2, r=0.06, z=4)
    for dy in (-0.11, 0.11):
        ax.plot([x - s / 2 + 0.06, x + s / 2 - 0.06], [y + dy, y + dy], color=ec, lw=0.7, zorder=5)
    if label:
        ax.text(x, y - s / 2 - 0.1, label, ha="center", va="top", fontsize=FS, color=label_color or ec, zorder=5)


def build():
    house_style.apply(base=FS)
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
                         "mathtext.fontset": "stix"})
    w_in = 0.95 * WIDTH
    fig = plt.figure(figsize=(w_in, w_in * (Y1 - Y0) / 10.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(Y0, Y1)
    ax.axis("off")

    yc = 2.0                                      # the centre line of lots and tools

    # --- the source step: a tool with three baths
    sx, sw, sh = 0.45, 1.75, 1.3
    box(ax, sx, yc - sh / 2, sw, sh, SOURCE)
    for i in range(3):
        bx = sx + 0.22 + i * 0.47
        box(ax, bx, yc - 0.36, 0.36, 0.5, "#c9e3f3", ec=INK, lw=0.9, r=0.03, z=4)
    ax.text(sx + sw / 2, yc + sh / 2 + 0.12, "Source step", ha="center", va="bottom", fontsize=FS, color="black")

    # --- the furnace: a vertical tube holding a boat of B slots, k of them filled
    fx, fw, fh, B, k = 7.05, 1.15, 2.6, 6, 2
    box(ax, fx, yc - fh / 2, fw, fh, FURNACE, r=0.4)
    ax.add_patch(Ellipse((fx + fw / 2, yc + fh / 2), fw, 0.28, facecolor="#c4d8ec", edgecolor=INK, lw=1.1, zorder=4))
    slot_h, gap = 0.22, 0.1
    y_slot = yc - fh / 2 + 0.28
    for i in range(B):
        ax.add_patch(Rectangle((fx + 0.22, y_slot + i * (slot_h + gap)), fw - 0.44, slot_h,
                               facecolor=SLOT_FULL if i < k else SLOT_EMPTY, edgecolor=INK, lw=0.8, zorder=4))
    ax.text(fx + fw / 2, yc + fh / 2 + 0.3, "Furnace", ha="center", va="bottom", fontsize=FS, color="black")
    ax.text(fx + fw + 0.08, yc - fh / 2 + 0.28 + 1.5 * slot_h + gap, r"$k$ of $B$", ha="left", va="center",
            fontsize=FS, color="black")

    # --- the queue-time limit: a bracket from the source step to the furnace
    yb = 3.75
    ax.plot([sx + sw, sx + sw, fx, fx], [yc + sh / 2 + 0.42, yb, yb, yc + fh / 2 + 0.62], color=INK, lw=1.1, zorder=2)
    ax.text((sx + sw + fx) / 2, yb + 0.07, r"Queue-time limit $\tau$", ha="center", va="bottom", fontsize=FS, color="black")

    # --- the path from the source step to the furnace, with the next lot on it
    px0, px1 = sx + sw, fx
    ax.plot([px0, px1], [yc, yc], color=GREY, lw=1.0, zorder=1)
    nx = 3.15
    lot(ax, nx, yc, 0.52, "#ffffff", LOT_EDGE, "Next lot", "black")
    arrow(ax, (nx + 0.3, yc + 0.2), (nx + 0.95, yc + 0.2), color=LOT_EDGE, lw=1.1, ms=9, z=5)
    ax.text(nx + 0.62, yc + 0.3, r"$u$", ha="center", va="bottom", fontsize=FS + 1, color="black")

    # --- the lots waiting in front of the furnace, each with a residual, the tightest marked
    qx = [4.75, 5.4, 6.05]
    for i, x in enumerate(qx):
        tight = i == 1
        lot(ax, x, yc, 0.52, TIGHT if tight else LOT, TIGHT_EDGE if tight else LOT_EDGE,
            r"$m_{\min}$" if tight else r"$m$", TIGHT_EDGE if tight else "black")
    ax.text(sum(qx) / 3, yc + 0.5, "Waiting lots", ha="center", va="bottom", fontsize=FS, color="black")

    # --- the two actions
    ax0 = fx + fw + 0.55
    arrow(ax, (ax0, yc + 0.15), (ax0 + 0.85, yc + 0.85), color=INK, lw=1.3)
    arrow(ax, (ax0, yc - 0.15), (ax0 + 0.85, yc - 0.85), color=INK, lw=1.3)
    ax.text(ax0 + 0.42, yc + 0.95, "Start", ha="left", va="bottom", fontsize=FS, color="black")
    ax.text(ax0 + 0.42, yc - 0.95, "Wait", ha="left", va="top", fontsize=FS, color="black")
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "paper", "figures", "setting.pdf"))
    a = ap.parse_args()
    house_style.save(build(), a.out)


if __name__ == "__main__":
    main()
