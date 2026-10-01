"""Reusable toolkit for professional workflow and neural-network figures.

Encodes the design rules distilled from Nature Machine Intelligence / CVPR / NeurIPS
figure practice (see .claude/skills/workflow-nn-figures/SKILL.md):
  - 5-7 components per view; one abstraction level per view
  - light rounded "zone" backgrounds group stages; consistent left-to-right flow
  - every block has explicit in/out arrows; tensor SHAPES annotate the edges
  - layer-type colour code (conv / pool / dense / recurrent / physics / output)
  - concrete example data thumbnails, not placeholder boxes
  - Arial, ~7-8 pt, colour never the sole encoder (shape + label too)

Usage:
    d = Diagram(fig)                       # 0-1 background canvas
    d.zone(0.02, 0.1, 0.30, 0.9, 'physics', 'Physics model')
    d.layer(0.16, 0.6, 0.12, 0.05, 'Conv1d 2→16  k7', 'conv')
    d.arrow((0.16, 0.55), (0.16, 0.50), shape='(B,16,128)')
    ax = d.thumb(0.05, 0.05, 0.27, 0.22)   # inset axes for an example plot
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---- Okabe–Ito core + soft tints ------------------------------------------
DARK = "#1A1A1A"
INK = "#333740"
C = dict(conv="#0072B2", pool="#56B4E9", dense="#CC79A7", recur="#E69F00",
         physics="#009E73", output="#D55E00", io="#7F7F7F", grey="#9AA0A8")
TINT = dict(physics="#E6F2EC", encoder="#F7EAF1", scanner="#E5F0F8",
            correction="#FBF0DC", output="#FBE7DC", neutral="#F2F3F5",
            conv="#E0EEF6", pool="#E7F4FB", dense="#F6E9F1", recur="#FBF0DC")
LAYER_FC = dict(conv=TINT["conv"], pool=TINT["pool"], dense=TINT["dense"],
                recur=TINT["recur"], physics=TINT["physics"], output=TINT["output"],
                io="white")
LAYER_EC = dict(conv=C["conv"], pool=C["pool"], dense=C["dense"], recur=C["recur"],
                physics=C["physics"], output=C["output"], io=C["io"])


def apply_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8.0, "axes.linewidth": 0.6,
        "savefig.dpi": 300, "figure.facecolor": "white",
    })


class Diagram:
    def __init__(self, fig, rect=(0, 0, 1, 1)):
        self.fig = fig
        self.ax = fig.add_axes(rect)
        self.ax.axis("off"); self.ax.set_xlim(0, 1); self.ax.set_ylim(0, 1)

    # -- grouping zone with optional header ---------------------------------
    def zone(self, x0, y0, x1, y1, tint="neutral", title=None, color=None,
             r=0.022, alpha=0.6, lw=0):
        fc = TINT.get(tint, tint)
        self.ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                          boxstyle=f"round,pad=0.004,rounding_size={r}", fc=fc,
                          ec="none", lw=lw, alpha=alpha, zorder=0,
                          transform=self.ax.transAxes, mutation_aspect=0.6))
        if title:
            self.ax.text((x0 + x1) / 2, y1 - 0.012, title, ha="center", va="top",
                         fontsize=8.4, fontweight="bold", color=color or DARK, zorder=7)

    def step_badge(self, x, y, num, color=DARK):
        self.ax.add_patch(plt.Circle((x, y), 0.0135, color=color, zorder=8,
                          transform=self.ax.transAxes))
        self.ax.text(x, y, str(num), ha="center", va="center", fontsize=6.6,
                     color="white", fontweight="bold", zorder=9)

    # -- a labelled node (rounded rect with title + optional sub) -----------
    def node(self, x0, y0, x1, y1, title, sub=None, fc="white", ec=DARK, lw=1.1,
             tcol=None, fs=8.4, r=0.014, z=3):
        self.ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                          boxstyle=f"round,pad=0.003,rounding_size={r}", fc=fc, ec=ec,
                          lw=lw, zorder=z, transform=self.ax.transAxes, mutation_aspect=0.55))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if sub:
            self.ax.text(cx, cy + (y1 - y0) * 0.16, title, ha="center", va="center",
                         fontsize=fs, fontweight="bold", color=tcol or DARK, zorder=z + 1)
            self.ax.text(cx, cy - (y1 - y0) * 0.22, sub, ha="center", va="center",
                         fontsize=fs - 0.8, color=INK, zorder=z + 1)
        else:
            self.ax.text(cx, cy, title, ha="center", va="center", fontsize=fs,
                         color=tcol or DARK, zorder=z + 1)

    # -- a colour-coded NN layer block --------------------------------------
    def layer(self, cx, cy, w, h, label, kind="conv", fs=7.8):
        self.ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                          boxstyle="round,pad=0.002,rounding_size=0.008",
                          fc=LAYER_FC.get(kind, "white"), ec=LAYER_EC.get(kind, DARK),
                          lw=1.0, zorder=4, transform=self.ax.transAxes, mutation_aspect=0.5))
        self.ax.text(cx, cy, label, ha="center", va="center", fontsize=fs, color=DARK, zorder=5)

    def vstack(self, cx, ytop, ybot, items, w=0.17, gap=0.012, fs=7.8):
        """Stack layer blocks top->bottom; items=[(label,kind),...]. Returns y-centres."""
        n = len(items); h = (ytop - ybot - (n - 1) * gap) / n
        ys = []
        for i, (lab, kind) in enumerate(items):
            cy = ytop - h / 2 - i * (h + gap)
            self.layer(cx, cy, w, h, lab, kind, fs=fs); ys.append(cy)
        return ys, h

    # -- arrows, with optional tensor-shape pill on the edge ----------------
    def arrow(self, p0, p1, shape=None, color=DARK, lw=1.8, ms=13, shape_fs=6.4,
              shape_side="right", z=6):
        a = FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                            color=color, lw=lw, zorder=z, transform=self.ax.transAxes,
                            shrinkA=0, shrinkB=0, capstyle="round", joinstyle="round")
        self.ax.add_patch(a)
        if shape:
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            dx = 0.012 if shape_side == "right" else -0.012
            ha = "left" if shape_side == "right" else "right"
            self.ax.text(mx + dx, my, shape, ha=ha, va="center", fontsize=shape_fs,
                         color=INK, style="italic", zorder=z + 1,
                         bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.4))

    def label(self, x, y, text, **kw):
        kw.setdefault("fontsize", 7.6); kw.setdefault("color", DARK)
        kw.setdefault("ha", "center"); kw.setdefault("va", "center")
        return self.ax.text(x, y, text, zorder=7, transform=self.ax.transAxes, **kw)

    # -- inset axes for an example-data thumbnail ---------------------------
    def thumb(self, x0, y0, x1, y1, frame=True):
        ax = self.fig.add_axes([x0, y0, x1 - x0, y1 - y0])
        if frame:
            for s in ax.spines.values():
                s.set_linewidth(0.5); s.set_color(C["grey"])
        ax.set_xticks([]); ax.set_yticks([])
        return ax

    def panel_letter(self, x, y, letter):
        self.ax.text(x, y, letter, fontsize=11, fontweight="bold", color=DARK,
                     va="top", ha="left", zorder=10, transform=self.ax.transAxes)


def legend_chips(diagram, x, y, items, dx=0.165, sw=0.022, fs=6.6):
    """items=[(label, kind_or_color), ...] drawn as a horizontal colour key."""
    cx = x
    for lab, kind in items:
        ec = LAYER_EC.get(kind, kind); fc = LAYER_FC.get(kind, kind)
        diagram.ax.add_patch(FancyBboxPatch((cx, y - 0.013), sw, 0.026,
                             boxstyle="round,pad=0.001,rounding_size=0.006", fc=fc, ec=ec,
                             lw=0.8, zorder=7, transform=diagram.ax.transAxes, mutation_aspect=0.5))
        diagram.ax.text(cx + sw + 0.006, y, lab, va="center", ha="left", fontsize=fs,
                        color=DARK, zorder=7, transform=diagram.ax.transAxes)
        cx += dx
