"""Shared Nature-style matplotlib setup for the DT-SPM summary figures.

Conventions: Arial ~7 pt at print scale, 0.6 pt axes, ticks out, no top/right
spines, Okabe–Ito colourblind-safe palette, bold lowercase panel letters, no
in-figure titles (titles live in captions).
"""
import matplotlib as mpl

# Okabe–Ito
BLUE, ORANGE, GREEN, VERMI, PURPLE, SKY, YELLOW, GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
    "#56B4E9", "#F0E442", "#7F7F7F")
DARK = "#1A1A1A"
LIGHT = dict(blue="#E3EEF7", green="#E2F2ED", purple="#F6E9F1",
             orange="#FBF0DC", grey="#F2F2F2", vermi="#F9E7DE")


def apply():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8.0,
        "axes.labelsize": 8.0,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 7.2,
        "ytick.labelsize": 7.2,
        "legend.fontsize": 7.0,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.0,
        "legend.frameon": False,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
    })


def panel_label(ax, letter, dx=-0.02, dy=1.02):
    """Bold lowercase panel letter at the top-left, Nature convention."""
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=8.5,
            fontweight="bold", va="bottom", ha="right", color=DARK)
