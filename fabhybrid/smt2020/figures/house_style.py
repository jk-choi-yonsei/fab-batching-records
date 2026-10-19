"""One place for the figure typography, so every figure in the paper matches.

Read off the group's published T-SM figures rather than guessed: in
"Drift-Aware Offline Reinforcement Learning for Run-to-Run Control in CMP",
the body text and captions are Times (NimbusRomNo9L), but the text INSIDE the
figures is sans (NimbusSanL / Helvetica) and it is set at about the size of the
body text -- the sub-panel labels are 10 pt against a 10 pt body. Figure text
that is smaller than the caption reads as an afterthought in print.

So: Arial (the Helvetica the machine has), 9 pt base, nothing below 8 pt, and
mathtext in the matching sans face.

    from house_style import apply
    apply()                      # single-column figure
    apply(scale=1.0)             # or pass a scale for a wide one
"""
import matplotlib
import matplotlib.pyplot as plt

SANS = ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]


def apply(base=9.0, scale=1.0):
    """base is the size of ordinary labels in points; everything keys off it."""
    b = base * scale
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": SANS,
        "mathtext.fontset": "stixsans",
        "font.size": b,
        "axes.labelsize": b,
        "axes.titlesize": b + 0.5,
        "xtick.labelsize": b - 0.5,
        "ytick.labelsize": b - 0.5,
        "legend.fontsize": b - 0.5,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "lines.linewidth": 1.1,
        "patch.linewidth": 0.9,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,          # embed as TrueType, not Type 3: IEEE Xplore requires it
        "ps.fonttype": 42,
    })
    return b


def serif():
    """The face of the author's own figures (2026-10-15): the body's Times inside the figure too, with STIX
    for the mathematics. Figures 1 and 3 were drawn this way and accepted; the data figures follow."""
    plt.rcParams.update({"font.family": "serif",
                         "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
                         "mathtext.fontset": "stix"})


def small(b, delta=1.0):
    """a secondary size that still prints: never below 8 pt."""
    return max(8.0, b - delta)


def save(fig, out, dpi=200):
    """The PDF goes where asked (the paper's figures/); a PNG preview of it goes to
    paper/build/preview/, which is not tracked, so the figures directory holds only
    what the paper includes."""
    import os
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    prev = os.path.join(os.path.dirname(out), "..", "build", "preview")
    os.makedirs(prev, exist_ok=True)
    png = os.path.join(prev, os.path.splitext(os.path.basename(out))[0] + ".png")
    fig.savefig(png, dpi=dpi)
    print("wrote", out, "and", os.path.normpath(png))
