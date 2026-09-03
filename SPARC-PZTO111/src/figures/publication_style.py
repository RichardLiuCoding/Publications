"""Reusable Matplotlib helpers for compact publication figures.

Windows-adapted copy of the bundled helper from the make-publication-figures
skill. The only change is the font search: Arial / Cambria live in
C:\\Windows\\Fonts on this machine rather than the macOS Office bundles.
Cambria Math is not installed here, so the documented Cambria fallback is used
for scale-bar text.

Import this module from a standalone script or notebook. The defaults provide
an Arial-based, closed-frame, compact colorbar/legend style for high-impact
materials-science figures while remaining dataset-agnostic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.patches import FancyBboxPatch


FONT = {
    "base": 8.8,
    "axis": 9.0,
    "tick": 8.2,
    "legend": 8.1,
    "panel": 11.0,
    "colorbar_label": 8.1,
    "colorbar_tick": 7.8,
    "small": 7.4,
}

COLORS = {
    "blue": "#4477AA",
    "red": "#C93612",
    "orange": "#EE7733",
    "green": "#2A9D8F",
    "purple": "#AA3377",
    "cyan": "#33BBEE",
    "yellow": "#CCBB44",
    "grey": "#7A7A7A",
    "light_grey": "#D0D0D0",
    "black": "#111111",
    "model": "royalblue",
}

WIN = Path("C:/Windows/Fonts")


def _first_existing(paths: Iterable[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def register_fonts() -> dict[str, FontProperties]:
    """Register local Arial/Cambria fonts and return useful font properties."""

    arial = _first_existing([
        WIN / "arial.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ])
    arial_bold = _first_existing([
        WIN / "arialbd.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ])
    cambria_math = _first_existing([
        WIN / "cambria math.ttf",
        WIN / "CambriaMath.ttf",
        Path.home() / "Library/Fonts/Cambria Math.ttf",
        Path("/Library/Fonts/Cambria Math.ttf"),
    ])
    cambria = _first_existing([
        WIN / "cambria.ttc",
        Path.home() / "Library/Fonts/Cambria.ttf",
    ])

    for path in (arial, arial_bold, cambria_math, cambria):
        if path is not None:
            try:
                fontManager.addfont(str(path))
            except (OSError, RuntimeError):
                pass

    sans = FontProperties(fname=str(arial)) if arial else FontProperties(family="Arial")
    sans_bold = (FontProperties(fname=str(arial_bold)) if arial_bold
                 else FontProperties(family="Arial", weight="bold"))
    if cambria_math:
        math = FontProperties(fname=str(cambria_math))
    elif cambria:
        math = FontProperties(fname=str(cambria))
    else:
        math = FontProperties(family="STIX Two Math")
    return {"sans": sans, "sans_bold": sans_bold, "math": math}


FONTS = register_fonts()


def configure_style(*, closed_frames: bool = True) -> None:
    """Apply the default final-size publication style."""

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": FONT["base"],
        "axes.labelsize": FONT["axis"],
        "xtick.labelsize": FONT["tick"],
        "ytick.labelsize": FONT["tick"],
        "legend.fontsize": FONT["legend"],
        "axes.linewidth": 0.75,
        "axes.spines.top": closed_frames,
        "axes.spines.right": closed_frames,
        "axes.titlesize": FONT["base"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.major.pad": 2.0,
        "ytick.major.pad": 2.0,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "axes.grid": False,
    })


def close_frame(ax: mpl.axes.Axes, *, linewidth: float = 0.75) -> None:
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(linewidth)


def square_map(ax: mpl.axes.Axes) -> None:
    ax.set_box_aspect(1)
    close_frame(ax)


def top_colorbar(fig, ax, mappable, label, *, ticks=None, width: float = 0.68,
                 y: float = 1.10, height: float = 0.048,
                 ticks_position: str = "bottom"):
    """Add a compact horizontal colorbar above an axis and outside its frame."""

    cax = ax.inset_axes([(1.0 - width) / 2.0, y, width, height])
    cb = fig.colorbar(mappable, cax=cax, orientation="horizontal", ticks=ticks)
    cb.ax.xaxis.set_label_position("top")
    cb.set_label(label, fontsize=FONT["colorbar_label"], labelpad=1.5)
    if ticks_position == "top":
        cb.ax.xaxis.set_ticks_position("top")
        cb.ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False,
                          labelsize=FONT["colorbar_tick"], pad=1.0, length=2.2, width=0.6)
    else:
        cb.ax.xaxis.set_ticks_position("bottom")
        cb.ax.tick_params(top=False, bottom=True, labeltop=False, labelbottom=True,
                          labelsize=FONT["colorbar_tick"], pad=1.2, length=2.2, width=0.6)
    cb.outline.set_linewidth(0.7)
    return cb


def boxed_legend(ax: mpl.axes.Axes, **kwargs):
    """Create a square-corner black-bordered legend."""

    kwargs.setdefault("frameon", True)
    kwargs.setdefault("fancybox", False)
    kwargs.setdefault("borderpad", 0.3)
    kwargs.setdefault("handlelength", 1.4)
    kwargs.setdefault("handletextpad", 0.4)
    legend = ax.legend(**kwargs)
    frame = legend.get_frame()
    frame.set_edgecolor("black")
    frame.set_linewidth(0.7)
    frame.set_facecolor("white")
    frame.set_alpha(0.92)
    return legend


def add_scalebar(ax, *, length: float, label: str, x: float, y: float,
                 label_offset: float, line_color: str = "white",
                 box_color: str = "#102E55", box_alpha: float = 0.68,
                 box_pad_x: float = 0.04, box_pad_y: float = 0.035,
                 linewidth: float = 2.0, fontsize: float = 8.2,
                 use_math_font: bool = True) -> None:
    """Draw a horizontal data-coordinate scale bar with a contrast pad."""

    xlim = ax.get_xlim(); ylim = ax.get_ylim()
    dx = abs(xlim[1] - xlim[0]); dy = abs(ylim[1] - ylim[0])
    ax.plot([x, x + length], [y, y], color=line_color, linewidth=linewidth,
            solid_capstyle="butt", zorder=6)
    txt = ax.text(x + length / 2, y + label_offset, label, ha="center",
                  va="bottom", color=line_color, fontsize=fontsize,
                  fontproperties=FONTS["math"] if use_math_font
                  else FONTS["sans"], zorder=6)
    # measure the label instead of guessing its height from the padding, which
    # let a larger fontsize print outside the box it was meant to sit on
    fig = ax.figure
    fig.canvas.draw()
    bb = txt.get_window_extent(renderer=fig.canvas.get_renderer())
    th = abs(np.ptp(ax.transData.inverted().transform(
        [(0, bb.y0), (0, bb.y1)])[:, 1]))
    tw = abs(np.ptp(ax.transData.inverted().transform(
        [(bb.x0, 0), (bb.x1, 0)])[:, 0]))
    bw = max(length, tw) + 2 * box_pad_x * dx
    box = FancyBboxPatch(
        (x + length / 2 - bw / 2, y - box_pad_y * dy), bw,
        label_offset + th + 1.7 * box_pad_y * dy,
        boxstyle="square,pad=0", linewidth=0, facecolor=box_color,
        alpha=box_alpha, clip_on=False, zorder=5)
    ax.add_patch(box)


def align_panel_letters(fig, rows, *, x_offset: float = 0.028,
                        y_offset: float = 0.014) -> None:
    """Align panel letters to shared row baselines and column positions."""

    fig.canvas.draw()
    column_x: dict[int, float] = {}
    for row in rows:
        for column, ax, _ in row:
            column_x[column] = min(column_x.get(column, 1.0),
                                   ax.get_position().x0 - x_offset)
    for row in rows:
        y = max(ax.get_position().y1 for _, ax, _ in row) + y_offset
        for column, _ax, label in row:
            fig.text(column_x[column], y, label, ha="left", va="bottom",
                     fontsize=FONT["panel"], fontproperties=FONTS["sans_bold"])


def align_xlabels(fig, axes) -> None:
    fig.align_xlabels(list(axes))


def save_figure(fig, output_dir, stem, *, pad_inches: float = 0.04,
                formats: Sequence[str] = ("png", "pdf", "svg", "tiff"),
                dpi_raster: int = 600):
    """Export a figure in inspection, vector, and submission formats."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    saved = []
    for extension in formats:
        path = output / f"{stem}.{extension}"
        kwargs = {"dpi": dpi_raster} if extension in {"png", "tiff"} else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=pad_inches,
                    facecolor="white", **kwargs)
        saved.append(path)
    return saved
