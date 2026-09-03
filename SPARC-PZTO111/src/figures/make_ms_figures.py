# -*- coding: utf-8 -*-
"""Manuscript figures for Agent_Paper_v8.

Ten figures at 6.90 in wide, the exact insertion width, so every label is at
final size. Schematics use few shapes and 9 to 10 pt text. Data panels come
from the raw .ibw frames in 260813/PZTO and 260820/PZTO, the trajectory files
in output/, and the audited numbers in aug_numbers.json, paper_llm/
paper_numbers.json and paper_llm/phase2.json.

Style follows the make-publication-figures skill: Arial, closed frames,
outward ticks, colorbars outside the data, boxed legends off the data, aligned
panel letters, PNG plus PDF plus SVG.
"""

import io
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Circle, FancyArrowPatch, Polygon,
                                Rectangle)

PROJ = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJ.parent.parent / "Styles"))
import publication_style as ps                      # noqa: E402
import aug_toolkit as T                             # noqa: E402
import flow_nodes as FN                             # noqa: E402
import quote_panels as QP                           # noqa: E402
import utk_geom as UG                               # noqa: E402
import utk_maps as UM                               # noqa: E402
import utk_orient as UO                             # noqa: E402
import aug_toolkit2 as T2                           # noqa: E402

ps.configure_style()
C = ps.COLORS
F = ps.FONT
SB = ps.FONTS["sans_bold"]

OUT = PROJ / "ms_v7" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

A6 = json.loads((PROJ / "aug_numbers.json").read_text())
NP = json.loads((PROJ / "paper_llm" / "paper_numbers.json").read_text())
P2 = json.loads((PROJ / "paper_llm" / "phase2.json").read_text())
NS = T.load_toolkit()
ibw, signed, angular_power = NS["ibw"], NS["signed"], NS["angular_power"]

W = 6.90                                            # insertion width, inches
KEEP_OPEN = False        # set by check_overlaps so it can measure the axes
LAST = {}                # the last figure built, when KEEP_OPEN
FR = dict(base="PZTO_LDART_0034.ibw", afterA="PZTO_LDART_0035.ibw",
          afterB="PZTO_LDART_0036.ibw")
OPC, AIC = C["red"], C["blue"]                      # operator, agent


# ------------------------------------------------------------------ helpers
def sites(fn):
    a = np.loadtxt(PROJ / "output" / fn)
    x, y, v = a[:, 0] * 1e6, a[:, 1] * 1e6, a[:, 2]
    live = np.abs(v) > 1e-9
    out, i, n = [], 0, len(v)
    while i < n:
        if not live[i]:
            i += 1
            continue
        j = i
        while (j + 1 < n and live[j + 1] and abs(x[j + 1] - x[i]) < 1e-6
               and abs(y[j + 1] - y[i]) < 1e-6):
            j += 1
        out.append((x[i], y[i], v[i]))
        i = j + 1
    return np.array(out)


def crop(tag, x0, x1, y0, y1):
    d, h = ibw(tag)
    L = float(h["ScanSize"]) * 1e6
    S, _, _ = signed(d)
    n = S.shape[0]
    return S[int(y0 / L * n):int(y1 / L * n), int(x0 / L * n):int(x1 / L * n)]


def spectrum(tag, x0, x1, y0, y1, step=5.0):
    """Angular power spectrum of one crop, in percent, on `step` degree bins."""
    d, h = ibw(tag)
    L = float(h["ScanSize"]) * 1e6
    n = d[0].shape[0]
    S = crop(tag, x0, x1, y0, y1)
    m = min(S.shape)
    Z = S[:m, :m] - S[:m, :m].mean()
    Z = Z * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    P = np.abs(np.fft.fftshift(np.fft.fft2(Z))) ** 2
    yy, xx = np.indices(P.shape)
    dy, dx = yy - m // 2, xx - m // 2
    px = L / n * 1000.0
    q = np.hypot(dy, dx) / (m * px / 1000.0)
    ang = np.mod(np.rad2deg(np.arctan2(dy, dx)) + 90.0, 180.0)
    sel = (q >= 1.5) & (q <= 14.0)
    e = np.arange(0.0, 180.0 + step, step)
    ctr = e[:-1] + step / 2
    hh = np.array([P[sel & (ang >= e[i]) & (ang < e[i + 1])].sum()
                   for i in range(len(ctr))])
    return ctr, hh / hh.sum() * 100.0


def blank(ax):
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def letters(fig, items, size=None):
    """items: (x, y, 'a') in figure coordinates."""
    for x, y, t in items:
        fig.text(x, y, t, fontsize=size or F["panel"], fontproperties=SB,
                 ha="left", va="bottom")


def inlabel(ax, t, col="#111111"):
    """Panel letter inside the top left corner of an image panel.

    Placed inside because these figures carry colorbars above the axes, and a
    letter outside the frame lands on the colorbar label.
    """
    ax.text(0.035, 0.965, t, transform=ax.transAxes, ha="left", va="top",
            fontsize=F["panel"], fontproperties=SB, color=col, zorder=8,
            bbox=dict(facecolor="#FFFFFFDD", edgecolor="none",
                      boxstyle="square,pad=0.16"))

def box(ax, x, y, w, h, face, edge, lw=1.1, z=2):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=edge,
                           linewidth=lw, zorder=z))


def arrow(ax, p0, p1, color, lw=1.4, ms=11, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, linestyle=ls,
                                 shrinkA=0, shrinkB=0, zorder=4))


# ================================ Figure 1: material, state and readout
# the two slab tints of a laminate, and the nano domain fill
SLAB = ("#B9A7D6", "#CFE0E8")
NANO = "#F3E4C8"


def _hollow(ax, p0, p1, col="#FFFFFF", ec="#3A3A3A", w=0.075, lw=0.7,
            z=6, hl=0.16, hw=0.155):
    """A hollow block arrow, the micro level marker of the reference figure."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    L = np.hypot(*v)
    if L < 1e-9:
        return
    u = v / L
    n = np.array([-u[1], u[0]])
    b = p1 - u * hl
    pts = [p0 + n * w, b + n * w, b + n * hw, p1, b - n * hw, b - n * w,
           p0 - n * w]
    ax.add_patch(Polygon(pts, closed=True, facecolor=col, edgecolor=ec,
                         lw=lw, zorder=z, joinstyle="miter"))


def _nanocell(ax, R, cx, cy, wc, hc, shear, face, ec="#8A7A5C", lw=0.35, z=2):
    """One sheared nano domain cell, in the block frame."""
    q = np.array([[-wc / 2 + shear, -hc / 2], [wc / 2 + shear, -hc / 2],
                  [wc / 2 - shear, hc / 2], [-wc / 2 - shear, hc / 2]])
    pts = (R @ q.T).T + np.array([cx, cy])
    ax.add_patch(Polygon(pts, closed=True, facecolor=face, edgecolor=ec,
                         lw=lw, zorder=z))
    return pts


def _hierarchy(ax, cx, cy, ang, wblk, hblk, pol_deg, nslab=4, ncell=4):
    """One superdomain drawn at all three levels.

    `ang` is the fitted stripe director, so the lamellae run along it and the
    laminate average sits normal to the walls. Each lamella is resolved into
    nano cells carrying the two polarization variants, every lamella gets a
    hollow micro arrow for its own average, and the block gets one global
    arrow.
    """
    th = np.deg2rad(ang - 90.0)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    ctr = np.array([cx, cy])

    def to_frame(pts):
        return (R @ np.asarray(pts, float).T).T + ctr

    sw = wblk / nslab                       # slab width, across the walls
    ch = hblk / ncell                       # nano cell height, along a wall
    for a in range(nslab):
        x0 = -wblk / 2 + a * sw
        xc = x0 + sw / 2
        # the slab, tinted so the alternation is visible at a glance
        quad = to_frame([[x0, -hblk / 2], [x0 + sw, -hblk / 2],
                         [x0 + sw, hblk / 2], [x0, hblk / 2]])
        ax.add_patch(Polygon(quad, closed=True, facecolor=SLAB[a % 2],
                             edgecolor="none", zorder=1))
        pd = np.deg2rad(pol_deg[a % 2])
        ncol = "#111111" if a % 2 == 0 else C["green"]
        for b in range(ncell):
            yc = -hblk / 2 + (b + 0.5) * ch
            _nanocell(ax, R, *to_frame([[xc, yc]])[0], sw * 0.84, ch * 0.86,
                      sw * 0.15, SLAB[a % 2], ec="#7C7364", lw=0.45)
            base = to_frame([[xc, yc]])[0]
            u = np.array([np.cos(pd), np.sin(pd)]) * min(sw, ch) * 0.42
            ax.add_patch(FancyArrowPatch(base - u, base + u,
                                         arrowstyle="-|>", mutation_scale=6.0,
                                         lw=1.05, color=ncol, shrinkA=0,
                                         shrinkB=0, zorder=4))
    # the block outline last, so no slab edge sits on top of it
    out = to_frame([[-wblk / 2, -hblk / 2], [wblk / 2, -hblk / 2],
                    [wblk / 2, hblk / 2], [-wblk / 2, hblk / 2]])
    ax.add_patch(Polygon(out, closed=True, facecolor="none",
                         edgecolor="#4A4335", lw=1.1, zorder=5))
    return R, ctr


def _blend(hexcol, a, bg=(1.0, 1.0, 1.0)):
    """Flatten a translucent fill against the page, so vector export is clean."""
    import matplotlib.colors as mc
    r, g, b = mc.to_rgb(hexcol)
    return mc.to_hex(tuple(a * c + (1 - a) * d for c, d in zip((r, g, b), bg)))


def _laminate(ax, cx, cy, ang, wblk, hblk, pol_deg, label, col, nstripe=26):
    """A compact superdomain: nano walls as thin lines, one global arrow.

    Used for the three orientation blocks, where the point is the direction
    rather than the internal hierarchy.
    """
    th = np.deg2rad(ang - 90.0)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])

    def to_frame(pts):
        return (R @ np.asarray(pts, float).T).T + np.array([cx, cy])

    out = to_frame([[-wblk / 2, -hblk / 2], [wblk / 2, -hblk / 2],
                    [wblk / 2, hblk / 2], [-wblk / 2, hblk / 2]])
    ax.add_patch(Polygon(out, closed=True, facecolor=_blend(col, 0.55),
                         edgecolor="none", zorder=1))
    for k in range(1, nstripe):
        x0 = -wblk / 2 + k * wblk / nstripe
        seg = to_frame([[x0, -hblk / 2], [x0, hblk / 2]])
        ax.plot(seg[:, 0], seg[:, 1], lw=0.55, color="#6E6250", zorder=2,
                solid_capstyle="butt")
    ax.add_patch(Polygon(out, closed=True, facecolor="none",
                         edgecolor="#4A4335", lw=1.0, zorder=3))
    v = np.array([np.cos(th), np.sin(th)]) * (wblk * 0.60)
    ax.add_patch(FancyArrowPatch(np.array([cx, cy]) - v / 2,
                                 np.array([cx, cy]) + v / 2,
                                 arrowstyle="-|>", mutation_scale=13, lw=2.6,
                                 color=C["red"], shrinkA=0, shrinkB=0,
                                 zorder=6))
    ax.text(cx, cy - hblk * 0.80, label, ha="center", va="top", fontsize=9.4,
            color=C["red"])


def fig1():
    tri = A6["R6"]["triad"]
    w0 = A6["R6"]["panels"]["P1"]["w"][0]
    lam = A6["R6"]["lam_nm"]

    fig = plt.figure(figsize=(W, 4.20))
    gs = fig.add_gridspec(2, 1, left=0.072, right=0.986, bottom=0.075,
                          top=0.935, height_ratios=[1.00, 0.92], hspace=0.26)
    gtop = gs[0].subgridspec(1, 3, width_ratios=[1.16, 1.60, 0.86],
                             wspace=0.05)
    gbot = gs[1].subgridspec(1, 3, width_ratios=[1.0, 1.30, 0.72],
                             wspace=0.42)

    # ---- (a1) the hierarchy: nano, micro, global
    ax = fig.add_subplot(gtop[0, 0])
    ax.set_xlim(-0.20, 2.60)
    ax.set_ylim(-0.74, 2.76)
    ax.set_aspect("equal")
    blank(ax)
    ax.text(1.20, 2.74, "one superdomain", ha="center", va="top",
            fontsize=9.2, fontproperties=SB)
    HANG = 64.0
    pol0 = (HANG - 30.0, HANG - 150.0)
    Rh, ch = _hierarchy(ax, 1.16, 1.50, HANG, 1.44, 1.44, pol0,
                        nslab=4, ncell=3)
    # the two lamella averages, and the sum that defines the superdomain,
    # drawn once each from a common origin below the block
    thh = np.deg2rad(HANG - 90.0)
    gv = np.array([np.cos(thh), np.sin(thh)])
    org = np.array([0.58, 0.02])
    for pdg in pol0:
        u = np.array([np.cos(np.deg2rad(pdg)), np.sin(np.deg2rad(pdg))])
        _hollow(ax, org, org + u * 0.46, w=0.052, hl=0.115, hw=0.115, lw=0.7)
    ax.add_patch(FancyArrowPatch(org, org + gv * 0.60, arrowstyle="-|>",
                                 mutation_scale=14, lw=2.8, color=C["red"],
                                 shrinkA=0, shrinkB=0, zorder=7))
    # the three level key
    for yk, lab, kind in ((0.56, "nano", "n"), (0.22, "micro", "m"),
                          (-0.10, "global", "g")):
        xk = 1.82
        if kind == "n":
            ax.add_patch(FancyArrowPatch((xk, yk), (xk + 0.19, yk),
                                         arrowstyle="-|>", mutation_scale=5.5,
                                         lw=1.0, color="#111111", shrinkA=0,
                                         shrinkB=0))
            ax.add_patch(FancyArrowPatch((xk, yk - 0.085),
                                         (xk + 0.19, yk - 0.085),
                                         arrowstyle="-|>", mutation_scale=5.5,
                                         lw=1.0, color=C["green"], shrinkA=0,
                                         shrinkB=0))
        elif kind == "m":
            _hollow(ax, (xk, yk), (xk + 0.21, yk), w=0.045, hl=0.09,
                    hw=0.095, lw=0.6, z=4)
        else:
            ax.add_patch(FancyArrowPatch((xk, yk), (xk + 0.23, yk),
                                         arrowstyle="-|>", mutation_scale=11,
                                         lw=2.4, color=C["red"], shrinkA=0,
                                         shrinkB=0))
        ax.text(xk + 0.30, yk - (0.042 if kind == "n" else 0.0), lab,
                ha="left", va="center", fontsize=8.2)

    # ---- (a2) the three allowed orientations
    ax = fig.add_subplot(gtop[0, 1])
    ax.set_xlim(0, 5.05)
    ax.set_ylim(-0.62, 1.82)
    ax.set_aspect("equal")
    blank(ax)
    # the two in-plane projections that build a laminate sit 120 degrees
    # apart, so their average bisects them and lands on the wall normal
    pol = [(t - 30.0, t - 150.0) for t in tri]
    fills = ["#B9A7D6", "#AFC9D8", "#E7C3B4"]
    for k, (t, pl, fc) in enumerate(zip(tri, pol, fills)):
        _laminate(ax, 0.86 + k * 1.62, 0.52, t, 1.02, 1.02, pl,
                  f"$d_{k + 1}$  {t:.0f}$\\degree$", fc)
    ax.text(2.50, 1.74, "three allowed superdomain directions in (111) PZT",
            ha="center", va="center", fontsize=9.2)

    # ---- (a3) crystal axes
    ax = fig.add_subplot(gtop[0, 2])
    ax.set_xlim(-1.30, 1.42)
    ax.set_ylim(-1.96, 1.80)
    ax.set_aspect("equal")
    blank(ax)
    for t, col in zip(tri, (C["blue"], C["green"], C["red"])):
        r = np.deg2rad(t)
        ax.plot([-np.cos(r), np.cos(r)], [-np.sin(r), np.sin(r)], lw=3.0,
                color=col, solid_capstyle="round", zorder=3)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec=C["light_grey"], lw=0.9))
    for t, col, nm in zip(tri, (C["blue"], C["green"], C["red"]),
                          ("$d_1$", "$d_2$", "$d_3$")):
        r = np.deg2rad(t)
        ax.text(1.22 * np.cos(r), 1.22 * np.sin(r), nm, ha="center",
                va="center", fontsize=9.4, color=col)
    # the axis marker sits below the circle, not inside it
    axo, ayo = -1.16, -1.50
    ax.plot([axo, axo + 0.40], [ayo, ayo], lw=1.0, color=C["black"])
    ax.plot([axo, axo], [ayo, ayo + 0.40], lw=1.0, color=C["black"])
    ax.text(axo + 0.46, ayo, "[1$\\overline{1}$0]", ha="left", va="center",
            fontsize=8.2)
    ax.text(axo, ayo + 0.46, "[11$\\overline{2}$]", ha="left", va="center",
            fontsize=8.2)
    ax.text(axo, ayo, "$\\odot$", ha="center", va="center", fontsize=9.0)
    ax.text(axo, ayo - 0.34, "[111] out of plane", ha="left", va="top",
            fontsize=8.2)
    ax.text(0, 1.52, "60$\\degree$ apart", ha="center", va="bottom",
            fontsize=9.2)

    # ---- (b) a real virgin frame
    ax = fig.add_subplot(gbot[0, 0])
    S = crop(FR["base"], 0.6, 2.6, 3.0, 5.0)
    v = float(np.percentile(np.abs(S), 98))
    im = ax.imshow(S, cmap="RdBu_r", vmin=-v, vmax=v, origin="lower",
                   extent=[0, 2, 0, 2], interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    ps.square_map(ax)
    ps.top_colorbar(fig, ax, im, "Signed lateral response (pm)",
                    ticks=[-int(v // 10 * 10), 0, int(v // 10 * 10)],
                    width=1.00, y=1.10, height=0.055)
    ps.add_scalebar(ax, length=0.5, label="500 nm", x=0.11, y=0.14,
                    label_offset=0.10, fontsize=8.4)

    # ---- (c) the measured spectrum with the scoring wedges
    ax = fig.add_subplot(gbot[0, 1])
    c, h = spectrum(FR["base"], 0.6, 2.6, 3.0, 5.0)
    for t, col in zip(tri, (C["blue"], C["green"], C["red"])):
        ax.axvspan(t - 15, t + 15, color=_blend(col, 0.13), lw=0)
    ax.plot(c, h, lw=1.7, color=C["black"])
    for t, col, nm in zip(tri, (C["blue"], C["green"], C["red"]),
                          ("$d_1$", "$d_2$", "$d_3$")):
        ax.axvline(t, color=col, lw=0.9, ls=":")
        ax.text(t, 9.0, nm, ha="center", va="bottom", fontsize=8.8, color=col)
    ax.set_xlim(0, 180); ax.set_xticks([0, 60, 120, 180])
    ax.set_xlabel("stripe director (deg)")
    ax.set_ylabel("angular power (%)")
    ax.set_ylim(0, 10.4)
    ax.set_yticks([0, 4, 8])
    ps.close_frame(ax)

    # ---- (d) the state vector
    ax = fig.add_subplot(gbot[0, 2])
    ax.bar(np.arange(3), w0, 0.60,
           color=[C["blue"], C["green"], C["red"]], edgecolor="none")
    ax.axhline(1 / 3, color=C["grey"], lw=0.9, ls="--")
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(["$d_1$", "$d_2$", "$d_3$"], fontsize=9.0)
    ax.set_xlim(-0.60, 2.60)
    ax.set_ylim(0, 0.66)
    ax.set_yticks([0, 1 / 3, 0.5])
    ax.set_yticklabels(["0", "1/3", "0.5"])
    ax.set_ylabel("population $w$")
    ps.close_frame(ax)

    fig.canvas.draw()
    letters(fig, [(0.006, 0.944, "a"), (0.006, 0.452, "b"),
                  (0.330, 0.452, "c"), (0.775, 0.452, "d")])
    ps.save_figure(fig, OUT, "fig1_material_state_readout",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig1"




# ============================ Figure 2: how the project actually evolved
LANES = [("H", "operator input", "#C93612"),
         ("A", "agent construction", "#4477AA"),
         ("E", "experiment", "#6E7A86"),
         ("T", "understanding", "#2A9D8F")]
LX = {k: 0.04 + i * 1.55 for i, (k, _, _) in enumerate(LANES)}
BW, BH = 1.46, 0.46
ROWP, DECH = 0.500, 0.245


def fig2():
    rows = FN.ROWS
    # y for each row, walking down and inserting space for decision bars
    C2 = getattr(FN, "CAMPAIGN2_ROW", None)
    BOUNDH = 0.64                     # the campaign break gets its own band
    ytop, ys, dy, ybound = 0.0, [], {}, None
    for i, (_, _, dec) in enumerate(rows):
        if i == C2:
            ybound = ytop - BOUNDH * 0.50
            ytop -= BOUNDH
        ys.append(ytop)
        ytop -= ROWP
        if dec:
            dy[i] = ytop - 0.02
            ytop -= DECH
    ybot = ytop

    # the figure grows with the number of rows, so a box never shrinks below
    # the two lines of 28 characters its label was written for
    HFIG = 0.545 * (0.86 - (ybot - 0.10)) + 0.62
    fig = plt.figure(figsize=(W, HFIG))
    ax = fig.add_axes([0.008, 0.006, 0.984, 1.0 - 0.62 / HFIG])
    ax.set_xlim(-1.06, 6.24)
    ax.set_ylim(ybot - 0.10, 0.86)
    blank(ax)

    # lane bands, spines and headers
    for k, name, col in LANES:
        ax.add_patch(Rectangle((LX[k] - 0.055, ybot - 0.06), BW + 0.11,
                               0.60 - ybot, facecolor=_blend(col, 0.05),
                               edgecolor="none", zorder=0))
        ax.plot([LX[k] + BW / 2, LX[k] + BW / 2], [0.40, ybot + 0.02],
                lw=0.8, color=_blend(col, 0.35), zorder=1)
        ax.text(LX[k] + BW / 2, 0.50, name, ha="center", va="bottom",
                fontsize=8.8, color=col, fontproperties=SB)
    # the time axis, with the two campaigns marked instead of dates
    ax.annotate("", xy=(-0.94, ybot + 0.06), xytext=(-0.94, 0.24),
                arrowprops=dict(arrowstyle="-|>", lw=1.0, color=C["grey"],
                                shrinkA=0, shrinkB=0))
    ax.text(-0.94, 0.30, "time", ha="center", va="bottom", fontsize=8.4,
            color=C["grey"])
    if ybound is not None:
        xL, xR = -0.66, LX["T"] + BW + 0.075
        # campaign 2 sits on its own tinted band, so the change of regime is
        # visible before any label is read
        ax.add_patch(Rectangle((xL, ybot - 0.06), xR - xL,
                               ybound - (ybot - 0.06), facecolor="#F1EEE6",
                               edgecolor="none", zorder=0))
        # the boundary itself is a rule across the whole chart, in its own gap
        ax.plot([xL, xR], [ybound, ybound], lw=1.7, color="#8A7A5C",
                zorder=6, solid_capstyle="butt")
        ax.text(xL + 0.05, ybound + 0.045, "campaign 1 ends. Eleven days, "
                "813 min at the instrument, no command issued by the agent",
                ha="left", va="bottom", fontsize=7.2, color="#8A7A5C",
                zorder=6)
        ax.text(xL + 0.05, ybound - 0.050, "campaign 2 begins. A new session, "
                "a new area, and a theory of its own to test",
                ha="left", va="top", fontsize=7.2, color="#8A7A5C", zorder=6)
        ax.text(xR, ybound + 0.045, "campaign 2", ha="right", va="bottom",
                fontsize=9.0, fontproperties=SB, color="#6F6144", zorder=6)
        for lab, y0, y1 in (("campaign 1", 0.10, ybound),
                            ("campaign 2", ybound, ybot + 0.06)):
            ax.plot([-0.80, -0.80], [y0, y1], lw=3.0, color="#B9AF98",
                    solid_capstyle="butt", zorder=1)
            ax.text(-0.86, (y0 + y1) / 2, lab, ha="center", va="center",
                    fontsize=8.2, fontproperties=SB, color="#7A6A4C",
                    rotation=90)

    # rows
    ctr = {}
    for i, (date, boxes, dec) in enumerate(rows):
        y = ys[i]
        cites = [(k, v[1]) for k, v in boxes.items() if v[1]]
        if cites:
            lk, ct = cites[0]
            ax.text(-0.10, y - BH / 2, ct, ha="right", va="center",
                    fontsize=7.6,
                    color=dict((a, c) for a, _, c in LANES)[lk])
        for k, (text, cite) in boxes.items():
            col = dict((a, c) for a, _, c in LANES)[k]
            ax.add_patch(Rectangle((LX[k], y - BH), BW, BH, facecolor="white",
                                   edgecolor=col, lw=1.05, zorder=3))
            ax.text(LX[k] + 0.06, y - 0.055, text, ha="left", va="top",
                    fontsize=7.4, linespacing=1.36, zorder=4)
            ctr[(i, k)] = (LX[k], LX[k] + BW, y - BH / 2)
        if dec:
            yd = dy[i]
            ax.add_patch(Rectangle((LX["H"], yd - DECH + 0.06),
                                   LX["T"] + BW - LX["H"], DECH - 0.10,
                                   facecolor="#FDF0DC", edgecolor="#E8890C",
                                   lw=1.0, zorder=3))
            cx = LX["H"] + 0.14
            ax.add_patch(Polygon([[cx, yd - DECH / 2 + 0.01],
                                  [cx + 0.085, yd - DECH / 2 + 0.10],
                                  [cx + 0.17, yd - DECH / 2 + 0.01],
                                  [cx + 0.085, yd - DECH / 2 - 0.08]],
                                 closed=True, facecolor="#E8890C",
                                 edgecolor="white", lw=0.8, zorder=5))
            ax.text(cx + 0.26, yd - DECH / 2 + 0.01, dec, ha="left",
                    va="center", fontsize=8.2, color="#A96200", zorder=5)

    # in row links
    for i, src, dst in FN.LINKS:
        if (i, src) not in ctr or (i, dst) not in ctr:
            continue
        x0, x1, y = ctr[(i, src)][1], ctr[(i, dst)][0], ctr[(i, src)][2]
        col = "#AA3377" if src == "H" and dst == "A" else C["light_grey"]
        lw = 1.3 if col != C["light_grey"] else 1.1
        if x1 - x0 > 0.30:                       # skips a lane, step around
            ym = y - BH / 2 - 0.045
            ax.plot([x0 + 0.02, (x0 + x1) / 2], [y, y], lw=lw, color=col, zorder=2)
            ax.plot([(x0 + x1) / 2, (x0 + x1) / 2], [y, ym], lw=lw, color=col, zorder=2)
            ax.plot([(x0 + x1) / 2, x1 - 0.10], [ym, ym], lw=lw, color=col, zorder=2)
            arrow(ax, (x1 - 0.10, ym), (x1 - 0.015, y), col, lw=lw, ms=8)
        else:
            arrow(ax, (x0 + 0.02, y), (x1 - 0.015, y), col, lw=lw, ms=8)

    # legend, two rows so nothing collides
    row1 = [("operator input", "#C93612"), ("agent construction", "#4477AA"),
            ("experiment", "#6E7A86"), ("understanding", "#2A9D8F")]
    x = 0.012
    for name, col in row1:
        fig.patches.append(plt.Rectangle((x, 0.9775), 0.016, 0.0115,
                           transform=fig.transFigure, facecolor="white",
                           edgecolor=col, lw=1.05, clip_on=False))
        fig.text(x + 0.022, 0.9832, name, ha="left", va="center",
                 fontsize=8.0, color=C["black"])
        x += 0.022 + 0.0086 * len(name) + 0.020
    x = 0.012
    fig.lines.append(plt.Line2D([x, x + 0.016], [0.9585, 0.9585],
                     transform=fig.transFigure, color="#AA3377", lw=1.5,
                     clip_on=False))
    fig.text(x + 0.022, 0.9585, "a question that changed the method",
             ha="left", va="center", fontsize=8.0, color="#AA3377")
    x += 0.022 + 0.0086 * 34 + 0.020
    fig.patches.append(plt.Polygon([[x, 0.9585], [x + 0.008, 0.9668],
                                    [x + 0.016, 0.9585], [x + 0.008, 0.9502]],
                       transform=fig.transFigure, facecolor="#E8890C",
                       edgecolor="white", lw=0.7, clip_on=False))
    fig.text(x + 0.022, 0.9585, "campaign level decision", ha="left",
             va="center", fontsize=8.0, color="#A96200")
    ps.save_figure(fig, OUT, "fig2_project_flow",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig2"




# ================== Figure 3: what the agent produced, in its own words
def fig3():
    AGC, OPC2, ERR = "#4477AA", "#C93612", "#AA3377"

    import textwrap as _tw

    # measure first, so the legend always has room
    LEG = 0.62
    tot = 0.0
    for pan in QP.PANELS:
        tot += 0.30 * len(_tw.wrap(pan["claim"], 104)) + 0.14
        tot += 0.285 * len(_tw.wrap(pan["quote"], 100)) + 0.52 + 0.16
        if pan["after"]:
            tot += 0.285 * len(_tw.wrap(pan["after"], 100)) + 0.52 + 0.16
        tot += 0.30
    top = tot + LEG + 0.18

    fig = plt.figure(figsize=(W, 0.492 * top))
    ax = fig.add_axes([0.006, 0.006, 0.988, 0.976])
    ax.set_xlim(0, 10.0)
    ax.set_ylim(0, top)
    blank(ax)

    y = top - 0.18
    for pan in QP.PANELS:
        # claim line, in the agent colour
        cl = _tw.wrap(pan["claim"], 104)
        nclaim = len(cl)
        ax.text(0.44, y, "\n".join(cl), ha="left", va="top", fontsize=8.8,
                color=C["black"], linespacing=1.42, zorder=4)
        y -= 0.30 * nclaim + 0.14
        ax.text(0.10, y + 0.30 * nclaim + 0.14, pan["tag"], ha="left",
                va="top", fontsize=F["panel"], fontproperties=SB)

        # the verbatim quote, in a tinted box with a rule on the left
        lines = _tw.wrap(pan["quote"], 100)
        # the extra 0.22 keeps a clear strip for the provenance label, so a
        # long last line can never run into it
        h = 0.285 * len(lines) + 0.52
        ax.add_patch(Rectangle((0.44, y - h), 9.34, h, facecolor="#F2F6FA",
                               edgecolor="#CBD9E6", lw=0.8, zorder=1))
        ax.add_patch(Rectangle((0.44, y - h), 0.055, h, facecolor=AGC,
                               edgecolor="none", zorder=2))
        ax.text(0.66, y - 0.15, "\n".join(lines), ha="left", va="top",
                fontsize=8.2, linespacing=1.46, color="#12293F", zorder=3)
        ax.text(9.72, y - h + 0.09, f"agent output, {pan['when']}",
                ha="right", va="bottom", fontsize=7.4, color=AGC, zorder=3)
        y -= h + 0.16

        if pan["after"]:
            lines2 = _tw.wrap(pan["after"], 100)
            h2 = 0.285 * len(lines2) + 0.52
            ax.add_patch(Rectangle((0.44, y - h2), 9.34, h2,
                                   facecolor="#FBF0F4", edgecolor="#E6C9D6",
                                   lw=0.8, zorder=1))
            ax.add_patch(Rectangle((0.44, y - h2), 0.055, h2, facecolor=ERR,
                                   edgecolor="none", zorder=2))
            ax.text(0.66, y - 0.15, "\n".join(lines2), ha="left", va="top",
                    fontsize=8.2, linespacing=1.46, color="#12293F", zorder=3)
            ax.text(9.72, y - h2 + 0.09, pan["after_label"], ha="right",
                    va="bottom", fontsize=7.4, color=ERR, zorder=3)
            y -= h2 + 0.16
        y -= 0.30

    # legend
    ly = 0.22
    ax.add_patch(Rectangle((0.44, ly), 0.20, 0.20, facecolor="#F2F6FA",
                           edgecolor="#CBD9E6", lw=0.8))
    ax.add_patch(Rectangle((0.44, ly), 0.045, 0.20, facecolor=AGC,
                           edgecolor="none"))
    ax.text(0.74, ly + 0.10, "verbatim agent output", ha="left", va="center",
            fontsize=8.2, color=AGC)
    ax.add_patch(Rectangle((3.30, ly), 0.20, 0.20, facecolor="#FBF0F4",
                           edgecolor="#E6C9D6", lw=0.8))
    ax.add_patch(Rectangle((3.30, ly), 0.045, 0.20, facecolor=ERR,
                           edgecolor="none"))
    ax.text(3.60, ly + 0.10, "a claim made in the same turn that later proved "
            "wrong", ha="left", va="center", fontsize=8.2, color=ERR)

    ps.save_figure(fig, OUT, "fig3_agent_in_its_own_words",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig3"


# ============================ Figure 4: program and selectivity
def fig4():
    R5 = A6["R5"]
    tp, cp = R5["panels"]["test"], R5["panels"]["ctrl"]
    DZ = json.loads((PROJ / "paper_llm" / "dose_fixed.json").read_text())

    fig = plt.figure(figsize=(W, 2.52))
    gs = fig.add_gridspec(1, 3, left=0.078, right=0.988, bottom=0.215,
                          top=0.845, width_ratios=[0.80, 1.34, 0.86],
                          wspace=0.44)

    # ---- (a) on triad versus off triad, dose matched at 144 sites
    ax = fig.add_subplot(gs[0, 0])
    it = tp["angles"].index(R5["cmd_test"])
    ic = cp["angles"].index(R5["cmd_ctrl"])
    d = [cp["after"][ic] - cp["before"][ic], tp["after"][it] - tp["before"][it]]
    ax.bar([0, 1], d, 0.56, color=[C["blue"], C["light_grey"]], edgecolor="none")
    for x, v in zip([0, 1], d):
        ax.text(x, v + 0.016, f"+{v:.3f}", ha="center", fontsize=8.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["on triad", "26$\\degree$ off"], fontsize=8.8)
    ax.set_ylabel("gain at the command")
    ax.set_ylim(0, 0.48)
    ax.set_yticks([0, 0.2, 0.4])
    ps.close_frame(ax)

    # ---- (b) the two write programs, read back from the files sent out
    ax = fig.add_subplot(gs[0, 1])
    ax.set_xlim(-0.20, 4.90)
    ax.set_ylim(-0.90, 2.68)
    ax.set_aspect("equal")
    blank(ax)
    prog = [("260814_R6_writeA.txt", [(1.6, 4.0), (6.4, 4.0)], 4.0,
             C["red"], "write A"),
            ("260814_R6_writeB.txt", [(1.6, 4.0), (4.0, 4.0)], 124.0,
             C["blue"], "write B")]
    for k, (fn, cens, ang, col, lab) in enumerate(prog):
        S = sites(fn)
        ctr = cens[0]
        dall = np.stack([np.hypot(S[:, 0] - c[0], S[:, 1] - c[1])
                         for c in cens])
        sel = np.argmin(dall, axis=0) == 0
        x0 = k * 2.50
        box(ax, x0, 0.16, 2.00, 2.00, "white", C["black"], lw=1.0, z=1)
        xs = (S[sel, 0] - ctr[0]) / 2.0 * 2.00 + x0 + 1.00
        ys = (S[sel, 1] - ctr[1]) / 2.0 * 2.00 + 1.16
        pos = S[sel, 2] > 0
        ax.plot(xs[pos], ys[pos], ls="none", marker="o", ms=2.5,
                mfc=C["red"], mec="none", zorder=3)
        ax.plot(xs[~pos], ys[~pos], ls="none", marker="o", ms=2.5,
                mfc=C["blue"], mec="none", zorder=3)
        ax.text(x0 + 1.00, 2.30, f"{lab}, {ang:.0f}$\\degree$", ha="center",
                va="bottom", fontsize=9.2, color=col)
        ax.text(x0 + 1.00, -0.16, f"{int(sel.sum())} sites",
                ha="center", va="center", fontsize=9.6, color=col,
                fontproperties=SB)
    ax.plot(0.10, -0.62, marker="o", ms=3.4, mfc=C["red"], mec="none")
    ax.text(0.24, -0.62, "+10 V", ha="left", va="center", fontsize=8.2,
            color=C["red"])
    ax.plot(1.20, -0.62, marker="o", ms=3.4, mfc=C["blue"], mec="none")
    ax.text(1.34, -0.62, "$-$10 V", ha="left", va="center", fontsize=8.2,
            color=C["blue"])
    ax.text(2.55, -0.62, "each site held 1.0 s", ha="left", va="center",
            fontsize=8.2, color=C["grey"])

    # ---- (c) the outcome splits on site count
    ax = fig.add_subplot(gs[0, 2])
    y196, y144 = DZ["p196_fft"], DZ["p144_fft"]
    ax.axhspan(min(y196), max(y196), color=_blend(C["red"], 0.10), lw=0)
    ax.axhspan(min(y144), max(y144), color=_blend(C["blue"], 0.10), lw=0)
    ax.scatter(np.linspace(-.09, .09, len(y196)), y196, s=32, color=C["red"],
               zorder=3)
    ax.scatter(1 + np.linspace(-.15, .15, len(y144)), y144, s=32,
               color=C["blue"], marker="s", zorder=3)
    ax.set_xlim(-0.42, 1.42)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([str(DZ["n196"]), str(DZ["n144"])], fontsize=8.8)
    ax.set_xlabel("sites delivered")
    ax.set_ylabel("power at the command")
    ax.set_ylim(0.19, 0.85)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ps.close_frame(ax)

    letters(fig, [(0.008, 0.885, "a"), (0.290, 0.885, "b"),
                  (0.720, 0.885, "c")])
    ps.save_figure(fig, OUT, "fig4_program_and_selectivity",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig4"


# ================================== Figure 4: reconfiguring a written region
def fig5():
    R6 = A6["R6"]
    tri, A, B, fl = R6["triad"], R6["A"], R6["B"], R6["floor_max"]
    P = R6["panels"]
    FRM = [FR["base"], FR["afterA"], FR["afterB"]]

    # four maps: P1 through all three stages, plus P3 in the final frame
    boxes = [("P1", 1.6, 0), ("P1", 1.6, 1), ("P1", 1.6, 2), ("P3", 6.4, 2)]
    imgs = [crop(FRM[j], cx - 1.0, cx + 1.0, 3.0, 5.0) for _, cx, j in boxes]
    v = float(np.percentile(np.abs(np.concatenate([i.ravel() for i in imgs])), 98))

    fig = plt.figure(figsize=(W, 3.98))
    gs = fig.add_gridspec(2, 1, left=0.077, right=0.988, bottom=0.075,
                          top=0.855, height_ratios=[1.0, 1.06], hspace=0.36)
    gm = gs[0].subgridspec(1, 4, wspace=0.075)
    gp = gs[1].subgridspec(1, 3, width_ratios=[1.0, 1.06, 1.14],
                           wspace=0.56)

    hdr = ["virgin", f"after A ({A:.0f}$\\degree$)",
           f"after B ({B:.0f}$\\degree$)", f"control, no B"]
    axm = []
    for k, (nm, cx, j) in enumerate(boxes):
        ax = fig.add_subplot(gm[0, k])
        im = ax.imshow(imgs[k], cmap="RdBu_r", vmin=-v, vmax=v, origin="lower",
                       extent=[0, 2, 0, 2], interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        ps.square_map(ax)
        ax.text(0.5, 1.045, hdr[k], transform=ax.transAxes, ha="center",
                va="bottom", fontsize=9.0)
        ax.text(0.035, 0.955, nm, transform=ax.transAxes, ha="left", va="top",
                fontsize=9.4, fontproperties=SB,
                color=C["black"] if k < 3 else C["grey"])
        axm.append((ax, im))
    ps.top_colorbar(fig, axm[1][0], axm[1][1],
                    "Signed lateral piezoresponse (pm)",
                    ticks=[-int(v // 10 * 10), 0, int(v // 10 * 10)],
                    width=1.90, y=1.30, height=0.062)
    ps.add_scalebar(axm[0][0], length=0.5, label="500 nm", x=0.11, y=0.14,
                    label_offset=0.10, fontsize=8.6)

    # ---- (e) angular spectra of P1
    ax = fig.add_subplot(gp[0, 0])
    for f, lab, col in zip(FRM, ("virgin", "after A", "after B"),
                           (C["grey"], C["blue"], C["red"])):
        c, h = spectrum(f, 0.6, 2.6, 3.0, 5.0)
        ax.plot(c, h, lw=1.5, color=col, label=lab)
    for t in tri:
        ax.axvline(t, color=C["light_grey"], lw=0.8, ls=":")
    ax.set_xlim(0, 180); ax.set_xticks([0, 60, 120, 180])
    ax.set_xlabel("stripe director (deg)")
    ax.set_ylabel("angular power (%)")
    ax.set_ylim(0, 30)
    ps.boxed_legend(ax, loc="upper right", fontsize=7.6, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ps.close_frame(ax)

    # ---- (f) power at A and at B in P1
    ax = fig.add_subplot(gp[0, 1])
    x = np.arange(3)
    ax.plot(x, P["P1"]["powA"], "o-", ms=5.0, lw=1.6, color=C["blue"],
            label=f"at {A:.0f}$\\degree$")
    ax.plot(x, P["P1"]["powB"], "s-", ms=5.0, lw=1.6, color=C["red"],
            label=f"at {B:.0f}$\\degree$")
    ax.axhline(1 / 6, color=C["grey"], lw=0.8, ls="--")
    ax.text(-0.06, 1 / 6 + 0.016, "uniform", ha="left", va="bottom",
            fontsize=7.6, color=C["grey"])
    ax.set_xticks(x); ax.set_xticklabels(["virgin", "+A", "+B"], fontsize=8.6)
    ax.set_ylim(0, 0.66); ax.set_yticks([0, 0.2, 0.4, 0.6])
    ax.set_ylabel("power at target")
    ps.boxed_legend(ax, loc="upper left", fontsize=7.6, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ps.close_frame(ax)

    # ---- (g) the six contrasts against the floor
    ax = fig.add_subplot(gp[0, 2])
    items = [("A on P1", P["P1"]["powA"][1] - P["P1"]["powA"][0], C["blue"]),
             ("A on P3", P["P3"]["powA"][1] - P["P3"]["powA"][0], C["blue"]),
             ("none on P2", P["P2"]["powA"][1] - P["P2"]["powA"][0], C["grey"]),
             ("B on P1", P["P1"]["powB"][2] - P["P1"]["powB"][1], C["red"]),
             ("B on P2", P["P2"]["powB"][2] - P["P2"]["powB"][1], C["red"]),
             ("P3 held", P["P3"]["powA"][2] - P["P3"]["powA"][1],
              C["orange"])]
    y = np.arange(len(items))[::-1]
    ax.axvspan(-fl, fl, color=_blend(C["light_grey"], 0.55), lw=0)
    ax.barh(y, [i[1] for i in items], 0.62,
            color=[i[2] for i in items], edgecolor="none")
    ax.axvline(0, color="black", lw=0.8)
    for yy, (_, val, _) in zip(y, items):
        ax.text(val + (0.022 if val >= 0 else -0.022), yy,
                f"{val:+.3f}", va="center", fontsize=7.6,
                ha="left" if val >= 0 else "right")
    ax.set_yticks(y); ax.set_yticklabels([i[0] for i in items], fontsize=8.0)
    ax.set_ylabel("write, panel")
    ax.set_xlabel("change at the command")
    ax.set_xlim(-0.40, 0.78); ax.set_xticks([-0.2, 0, 0.2, 0.4, 0.6])
    ps.close_frame(ax)

    fig.align_xlabels([a for a in fig.axes[-3:]])
    fig.canvas.draw()
    bb = axm[0][0].get_position()
    fig.text(0.008, bb.y1 + 0.012, "a", fontsize=F["panel"], fontproperties=SB,
             ha="left", va="bottom")
    letters(fig, [(0.008, 0.442, "b"), (0.352, 0.442, "c"),
                  (0.700, 0.442, "d")])
    ps.save_figure(fig, OUT, "fig5_reconfiguration",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig5"





# ============================ Figure 5: measurement validity and robustness
def fig6():
    RS, RR, AD, PF = NP["race_synth"], NP["race_real"], NP["abs_disagree"], NP["peak_frag"]
    CO = NP["contrasts"]

    fig = plt.figure(figsize=(W, 4.30))
    gs = fig.add_gridspec(2, 2, left=0.105, right=0.985, bottom=0.085,
                          top=0.905, wspace=0.42, hspace=0.56)

    # ---- (a) the synthetic race
    ax = fig.add_subplot(gs[0, 0])
    names = ["Fourier", "Canny", "structure\ntensor"]
    bias = [RS["bias"]["fft"], RS["bias"]["canny"], RS["bias"]["tensor"]]
    var = [RS["per_real"]["fft"], RS["per_real"]["canny"], RS["per_real"]["tensor"]]
    x = np.arange(3); w = 0.34
    ax.bar(x - w / 2, bias, w, color=C["light_grey"], edgecolor="none",
           label="bias")
    ax.bar(x + w / 2, var, w, color=C["green"], edgecolor="none",
           label="scatter")
    for xx, b, v in zip(x, bias, var):
        ax.text(xx - w - 0.02, b + 0.004, f"{b:.3f}", ha="center", fontsize=7.8)
        ax.text(xx + w + 0.02, v + 0.004, f"{v:.3f}", ha="center", fontsize=7.8)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8.6)
    ax.set_ylabel("error against\nknown truth")
    ax.set_xlim(-0.62, 2.62); ax.set_ylim(0, 0.215)
    ax.set_yticks([0, 0.1, 0.2])
    ps.boxed_legend(ax, loc="upper center", fontsize=7.8, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ps.close_frame(ax)

    # ---- (b) the transfer test
    ax = fig.add_subplot(gs[0, 1])
    x = np.arange(2); w = 0.34
    syn = [RS["per_real"]["fft"], RS["per_real"]["tensor"]]
    real = [RR["fft_mean"], RR["tensor_mean"]]
    ax.bar(x - w / 2, syn, w, color=C["green"], edgecolor="none",
           label="synthetic")
    ax.bar(x + w / 2, real, w, color=C["orange"], edgecolor="none",
           label="real frames")
    for xx, a, b in zip(x, syn, real):
        ax.text(xx - w / 2, a + 0.008, f"{a:.3f}", ha="center", fontsize=7.8)
        ax.text(xx + w / 2, b + 0.008, f"{b:.3f}", ha="center", fontsize=7.8)
    ax.set_xticks(x); ax.set_xticklabels(["Fourier", "structure\ntensor"],
                                        fontsize=8.6)
    ax.set_ylabel("change on an\nunchanged state")
    ax.set_xlim(-0.62, 1.62); ax.set_ylim(0, 0.215)
    ax.set_yticks([0, 0.1, 0.2])
    ps.boxed_legend(ax, loc="upper center", fontsize=7.8, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ps.close_frame(ax)

    # ---- (c) the six contrasts under both estimators
    ax = fig.add_subplot(gs[1, 0])
    lab = ["A on P1", "A on P3", "none on P2",
           "B on P1", "B on P2", "P3 held"]
    y = np.arange(len(CO))[::-1]
    for yy, (_, a, b) in zip(y, CO):
        ax.plot([a, b], [yy, yy], "-", lw=1.0, color=C["light_grey"], zorder=1)
    ax.scatter([c[1] for c in CO], y, s=30, color=C["grey"], zorder=3,
               label="Fourier")
    ax.scatter([c[2] for c in CO], y, s=30, color=C["purple"], marker="s",
               zorder=3, label="tensor")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.2)
    ax.set_xlabel("change at the command")
    ax.set_xlim(-0.22, 1.22); ax.set_xticks([0, 0.5, 1.0])
    ps.boxed_legend(ax, loc="lower right", fontsize=7.8, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ps.close_frame(ax)

    # ---- (d) the peak statistic under two bin widths
    ax = fig.add_subplot(gs[1, 1])
    st = ["virgin", "after A", "after B"]
    b5 = [PF["virgin"][0], PF["afterA"][0], PF["afterB"][0]]
    b25 = [PF["virgin"][1], PF["afterA"][1], PF["afterB"][1]]
    x = np.arange(3); w = 0.34
    ax.bar(x - w / 2, b5, w, color=C["light_grey"], edgecolor="none",
           label="5$\degree$ bins")
    ax.bar(x + w / 2, b25, w, color=C["red"], edgecolor="none",
           label="2.5$\degree$ bins")
    for xx, a, b in zip(x, b5, b25):
        ax.text(xx - w / 2, a + 5, f"{a:.0f}", ha="center", fontsize=7.8)
        ax.text(xx + w / 2, b + 5, f"{b:.0f}", ha="center", fontsize=7.8)
    ax.set_xticks(x); ax.set_xticklabels(st, fontsize=8.6)
    ax.set_ylabel("dominant director\n(deg)")
    ax.set_xlim(-0.60, 3.02); ax.set_ylim(0, 182); ax.set_yticks([0, 60, 120, 180])
    ps.boxed_legend(ax, loc="upper left", fontsize=7.8, labelspacing=0.24,
                    handlelength=1.0, borderpad=0.28)
    ax.annotate("", xy=(2.46, b25[2]), xytext=(2.46, b5[2]),
                arrowprops=dict(arrowstyle="<->", lw=1.0, color=C["red"],
                                shrinkA=0, shrinkB=0))
    ax.text(2.56, (b5[2] + b25[2]) / 2, "116$\degree$", ha="left",
            va="center", fontsize=8.2, color=C["red"])
    ps.close_frame(ax)

    fig.align_xlabels(fig.axes[2:4])
    letters(fig, [(0.008, 0.930, "a"), (0.520, 0.930, "b"),
                  (0.008, 0.455, "c"), (0.520, 0.455, "d")])
    ps.save_figure(fig, OUT, "fig6_measurement_validity",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig6"






# ============================== Figure 7: the loop that ran without a human
def fig7():
    """One message: the agent was given the actuator, and what stopped it.

    Laid out in inches on a single full-figure axes, because the two panels
    have to agree on a text baseline grid and a gridspec cannot promise that.
    """
    H = P2["halts"]
    HF = 3.88                                       # figure height, inches
    fig = plt.figure(figsize=(W, HF))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, W)
    ax.set_ylim(0, HF)
    blank(ax)

    # ---- (a) the cycle, two columns of four
    STEPS = [("propose", "hypothesis, prediction and\ntwo named outcomes", AIC),
             ("preflight", "29 coded checks, with the\ndeferred ones named", C["orange"]),
             ("place", "a fresh area that can\nsupport the measurement", C["orange"]),
             ("write", "trajectory sent, area\nlogged the same second", C["red"]),
             ("read", "population over the triad,\ninside the same frame", AIC),
             ("refine", "the one constant the\ntheory turns on", C["green"]),
             ("log", "notebook cell, findings\nentry, console file", C["green"]),
             ("decide", "carry on, or halt and\nraise a strike", C["orange"])]
    ax.text(0.27, HF - 0.13, "the agent runs every step", ha="left",
            va="center", fontsize=8.8, fontproperties=SB, color=AIC)
    BW, BH, GX, GY = 1.24, 0.53, 0.46, 0.10
    x0, ytop = 0.10, HF - 0.34

    def place(k):
        """Boustrophedon: column one top down, column two bottom up, so the
        eight steps form a ring with no crossing connector."""
        col, r = k // 4, k % 4
        row = r if col == 0 else 3 - r
        return x0 + col * (BW + GX), ytop - row * (BH + GY) - BH

    for k, (nm, sub, col) in enumerate(STEPS):
        cx, cy = place(k)
        box(ax, cx, cy, BW, BH, "#FFFFFF", col, lw=1.1)
        ax.add_patch(Rectangle((cx, cy), 0.055, BH, facecolor=col,
                               edgecolor="none", zorder=3))
        ax.text(cx + 0.15, cy + BH - 0.115, "%d  %s" % (k + 1, nm), ha="left",
                va="center", fontsize=8.4, fontproperties=SB, color=col)
        ax.text(cx + 0.15, cy + 0.145, sub, ha="left", va="center",
                fontsize=6.6, color=C["black"], linespacing=1.32)

    STEPC = "#7B8794"
    # the seven step to step arrows, each one short and unambiguous
    for k in range(7):
        ax0, ay0 = place(k)
        ax1, ay1 = place(k + 1)
        if ax0 == ax1:                                   # same column
            down = ay1 < ay0
            y_from = ay0 if down else ay0 + BH
            y_to = ay1 + BH if down else ay1
            arrow(ax, (ax0 + BW / 2, y_from), (ax0 + BW / 2, y_to), STEPC,
                  lw=1.5, ms=8)
        else:                                            # the bottom crossing
            arrow(ax, (ax0 + BW, ay0 + BH / 2), (ax1, ay1 + BH / 2), STEPC,
                  lw=1.5, ms=8)

    # the loop closes along the top, from decide back to propose
    lx0, ly0 = place(7)
    lx1, ly1 = place(0)
    ymid = ly0 + BH / 2
    arrow(ax, (lx0, ymid), (lx1 + BW, ymid), C["orange"], lw=1.5, ms=8)
    ax.text((lx0 + lx1 + BW) / 2, ymid + 0.07, "carry on", ha="center",
            va="bottom", fontsize=6.6, color=C["orange"])
    ax.text((lx0 + lx1 + BW) / 2, ymid - 0.07, "or halt", ha="center",
            va="top", fontsize=6.6, color=C["red"])

    # the cost line, under the cycle
    ax.add_patch(Rectangle((x0, 0.10), 2 * BW + GX, 0.62,
                           facecolor="#F4F6F8", edgecolor="#D8DEE4", lw=0.8))
    ax.text(x0 + 0.13, 0.41, "campaign 2: nine driver runs\n%.0f min at the "
            "instrument, %.0f of it writing\nno write left its declared area"
            % (P2["census"]["loop_instr_min"], P2["census"]["write_min"]),
            ha="left", va="center", fontsize=7.4, color=C["black"],
            linespacing=1.50)

    # ---- (b) every halt, with the gate that caused it
    KIND = {"tooling": C["red"], "geometry": C["orange"],
            "area gate": AIC, "static audit": C["green"],
            "physics guard": C["purple"] if "purple" in C else C["green"],
            "footprint S9": C["yellow"]}
    xb = 3.22
    ax.text(xb + 0.17, HF - 0.13, "and every time it stopped itself, in order",
            ha="left",
            va="center", fontsize=8.8, fontproperties=SB, color=C["black"])
    yh = HF - 0.42
    for when, it, kind, why in H:
        col = KIND.get(kind, C["grey"])
        ax.add_patch(Rectangle((xb, yh - 0.115), 0.05, 0.235, facecolor=col,
                               edgecolor="none"))
        ax.text(xb + 0.11, yh + 0.075, "%s" % when, ha="left",
                va="center", fontsize=7.2, fontproperties=SB, color=col)
        ax.text(xb + 0.63, yh + 0.075, "iteration %s" % it, ha="left",
                va="center", fontsize=7.0, color=C["grey"])
        ax.text(xb + 0.11, yh - 0.085, why, ha="left", va="center",
                fontsize=6.7, color=C["black"])
        yh -= 0.325
    seen, hs = [], []
    for _, _, kind, _ in H:
        if kind not in seen:
            seen.append(kind)
            hs.append(kind)
    for i, kind in enumerate(hs):
        cx = xb + (i % 3) * 1.18
        cy = 0.40 - (i // 3) * 0.20
        ax.add_patch(Rectangle((cx, cy), 0.09, 0.09,
                               facecolor=KIND.get(kind, C["grey"]),
                               edgecolor="none"))
        ax.text(cx + 0.14, cy + 0.045, kind, ha="left", va="center",
                fontsize=6.8, color=C["black"])

    letters(fig, [(0.012, (HF - 0.21) / HF, "a"),
                  (xb / W + 0.004, (HF - 0.21) / HF, "b")])
    ps.save_figure(fig, OUT, "fig7_autonomous_loop",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig7"


# ============ Figure 8: what the loop found, and what it overturned
def fig8():
    """One message: the loop falsified three of its own rules in one night."""
    SL = P2["sigma_ladder"]
    PS = P2["period_series"]
    UT = P2["uniform_test"]
    RA = P2["raster"]
    I9 = P2["it9"]

    fig = plt.figure(figsize=(W, 3.34))
    gs = fig.add_gridspec(2, 3, left=0.078, right=0.988, bottom=0.098,
                          top=0.905, wspace=0.44, hspace=0.62)

    # ---- (a) period is irrelevant: two runs disagree on the ordering
    ax = fig.add_subplot(gs[0, 0])
    for run, mk, col, lab in (("IT2", "s", C["light_grey"], "run 1"),
                              ("IT3", "o", AIC, "run 2")):
        pv = [float(r[0][:-1]) for r in PS[run]]
        xv = [r[3] for r in PS[run]]
        ax.plot(pv, xv, marker=mk, ms=5.0, lw=1.4, color=col, label=lab,
                mec="none")
    ax.axhline(1.0, ls=(0, (3, 2)), lw=0.9, color=C["red"])
    ax.text(2.9, 1.06, "detection limit", ha="left", va="bottom",
            fontsize=6.6, color=C["red"])
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8])
    ax.set_xticklabels(["$\\Lambda$", "2$\\Lambda$", "4$\\Lambda$",
                        "8$\\Lambda$"])
    ax.set_ylim(0, 3.6); ax.set_yticks([0, 1, 2, 3])
    ax.set_xlabel("template period")
    ax.set_ylabel("selection,\nmultiples of the null")
    ps.boxed_legend(ax, loc="upper right", fontsize=7.0, labelspacing=0.20,
                    handlelength=1.1, borderpad=0.24)
    ps.close_frame(ax)

    # ---- (b) but the sign has to alternate
    ax = fig.add_subplot(gs[0, 1])
    keys = [("A_balanced", "alternating", AIC), ("UP", "all $+$V", C["grey"]),
            ("UM", "all $-$V", C["light_grey"])]
    x = np.arange(3)
    ax.bar(x, [UT[k][1] for k, _, _ in keys], 0.62,
           color=[c for _, _, c in keys], edgecolor="none")
    ax.axhline(UT["threshold"] / 2.0 * 0 + 0.0, lw=0.8, color=C["black"])
    ax.axhspan(-0.0995, 0.0995, color=_blend(C["red"], 0.13), lw=0)
    ax.text(2.42, 0.104, "null band", ha="right", va="bottom", fontsize=6.6,
            color=C["red"])
    for i, (k, _, _) in enumerate(keys):
        v = UT[k][1]
        ax.text(i, v + (0.014 if v >= 0 else -0.014), "%+.3f" % v,
                ha="center", va="bottom" if v >= 0 else "top", fontsize=6.8,
                color=C["black"])
    ax.set_xticks(x)
    ax.set_xticklabels([l for _, l, _ in keys], fontsize=7.4)
    ax.set_ylim(-0.09, 0.26); ax.set_yticks([-0.05, 0, 0.1, 0.2])
    ax.set_ylabel("change at the\ncommanded director")
    ax.set_xlabel("sign pattern, same $\\sigma$")
    ps.close_frame(ax)

    # ---- (c) no threshold, and a fixed point
    ax = fig.add_subplot(gs[0, 2])
    sg = [r[1] for r in SL["rungs"]]
    w0 = [r[3] for r in SL["rungs"]]
    w1 = [r[4] for r in SL["rungs"]]
    ax.plot(sg, SL["law_pred"], ls=(0, (3, 2)), lw=1.2, color=C["red"])
    ax.plot(sg, w0, marker="o", ms=4.6, lw=0, color=C["light_grey"], mec="none")
    ax.plot(sg, w1, marker="o", ms=5.2, lw=1.4, color=AIC, mec="none")
    ax.axhline(SL["fixed_point"], lw=0.8, color=C["green"])
    ax.axvline(302, lw=0.8, ls=(0, (1, 2)), color=C["grey"])
    # labelled on the curves rather than in a box, which was covering the data
    ax.text(492, SL["law_pred"][-1] + 0.022, "the fitted law", ha="right",
            va="bottom", fontsize=6.6, color=C["red"])
    ax.text(126, SL["fixed_point"] + 0.022, "settles at 0.47", ha="left",
            va="bottom", fontsize=6.6, color=C["green"])
    ax.text(sg[-1], w1[-1] - 0.050, "after", ha="center", va="top",
            fontsize=6.6, color=AIC, fontproperties=SB)
    ax.text(sg[0] - 22, w0[0], "before", ha="right", va="center",
            fontsize=6.6, color=C["grey"])
    ax.text(296, 0.712, "the supposed threshold", ha="right", va="top",
            fontsize=6.2, color=C["grey"])
    ax.set_xlim(120, 500); ax.set_xticks([200, 300, 400, 500])
    ax.set_ylim(0, 0.72); ax.set_yticks([0, 0.2, 0.4, 0.6])
    ax.set_xlabel("$\\sigma$ (V.s/$\\mu$m$^2$)")
    ax.set_ylabel("w at the command")
    ps.close_frame(ax)

    # ---- (d) the raster: enhanced, where the agent had predicted depletion
    ax = fig.add_subplot(gs[1, 0])
    tri = [2, 62, 122]
    x = np.arange(3)
    ax.bar(x - 0.19, RA["before"], 0.36, color=C["light_grey"],
           edgecolor="none", label="before")
    ax.bar(x + 0.19, RA["after"], 0.36,
           color=[C["red"] if t == RA["dir"] else AIC for t in tri],
           edgecolor="none", label="after")
    ax.annotate("", xy=(1.19, RA["after"][1] + 0.055),
                xytext=(1.19, RA["after"][1] + 0.150),
                arrowprops=dict(arrowstyle="-|>", lw=1.1, color=C["red"],
                                shrinkA=0, shrinkB=0))
    ax.text(2.46, 1.00, "the scan direction,\nand it rose by %+.3f"
            % (RA["after"][1] - RA["before"][1]), ha="right", va="top",
            fontsize=6.6, color=C["red"], linespacing=1.32)
    ax.set_xticks(x)
    ax.set_xticklabels(["2$\\degree$", "62$\\degree$", "122$\\degree$"],
                       fontsize=7.6)
    ax.set_ylim(0, 1.02); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("population w")
    ax.set_xlabel("triad member")
    ps.boxed_legend(ax, loc="upper left", fontsize=6.8, labelspacing=0.18,
                    handlelength=0.9, borderpad=0.22)
    ps.close_frame(ax)

    # ---- (e) set, reset, and hold
    ax = fig.add_subplot(gs[1, 1])
    H, R = I9["HOLD"], I9["RW_s1"]
    ax.plot([0, 1, 2], [0.20, H[3], I9["HOLD_ret"][0]], marker="o", ms=5.0,
            lw=1.6, color=AIC, label="hold at 64$\\degree$", mec="none")
    ax.plot([0, 1, 2], [0.20, R[3], I9["RW_s2"][1]], marker="s", ms=5.0,
            lw=1.6, color=C["orange"], label="drive, then reverse", mec="none")
    for xx, yy, tt, dy2, va in ((1, H[3], "7.7x", 0.045, "bottom"),
                               (1, R[3], "3.4x", -0.045, "top"),
                               (2, I9["HOLD_ret"][0], "5.9x", -0.045, "top"),
                               (2, I9["RW_s2"][1], "3.8x", 0.045, "bottom")):
        ax.text(xx, yy + dy2, tt, ha="center", va=va, fontsize=6.8,
                color=C["grey"])
    ax.set_xlim(-0.25, 2.55); ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["start", "write 1", "write 2\nor 34 min"],
                       fontsize=7.0)
    ax.set_ylim(0, 0.92); ax.set_yticks([0, 0.25, 0.5, 0.75])
    ax.set_ylabel("w at the\npanel's own target")
    ps.boxed_legend(ax, loc="lower right", fontsize=6.8, labelspacing=0.18,
                    handlelength=1.1, borderpad=0.22)
    ps.close_frame(ax)

    # ---- (f) the three rules the loop overturned
    ax = fig.add_subplot(gs[1, 2])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    blank(ax)
    rows = [("commensuration is required", 0.72,
             "a 2$\\Lambda$ template is not, and works", "a"),
            ("charge has a threshold", 0.61,
             "0.70 $\\sigma_c$ selects at 3.5 times the null", "c"),
            ("the raster depletes", 0.52,
             "on virgin film it aligns instead", "d")]
    ax.text(0.0, 1.04, "three of its own rules, overturned in one night",
            ha="left", va="top", fontsize=7.6, fontproperties=SB,
            color=C["black"])
    yy = 0.80
    for old, rw, new, pan in rows:
        ax.text(0.0, yy, old, ha="left", va="top", fontsize=7.4,
                fontproperties=SB, color=C["red"])
        ax.plot([0.0, rw], [yy - 0.050, yy - 0.050], lw=0.9, color=C["red"])
        ax.text(0.0, yy - 0.115, new, ha="left", va="top", fontsize=7.0,
                color=C["black"])
        ax.text(1.0, yy - 0.055, pan, ha="right", va="center", fontsize=6.6,
                color=C["grey"])
        yy -= 0.295

    letters(fig, [(0.006, 0.928, "a"), (0.330, 0.928, "b"),
                  (0.664, 0.928, "c"), (0.006, 0.452, "d"),
                  (0.330, 0.452, "e"), (0.664, 0.452, "f")])
    ps.save_figure(fig, OUT, "fig8_loop_findings",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig8"


# ================================ Figure 9: a word written in orientation
def fig9():
    """One message: an arbitrary shape can be written into the director.

    Raw signed response on the top row, because a referee should see the
    stripes break along the strokes before being shown a derived population
    map. Quantification underneath.
    """
    U = P2["utk"]
    M = UM.build()
    xs, ys = M["xs"], M["ys"]
    ext = [xs[0] - 0.15, xs[-1] + 0.15, ys[0] - 0.15, ys[-1] + 0.15]
    lines = UG.stroke_lines()

    NS2 = T2.load_toolkit()
    import contextlib as _cx
    RAW = {}
    with _cx.redirect_stdout(io.StringIO()):
        for k, tag in (("b", UG.BEFORE), ("a", UG.AFTER)):
            d, h = NS2["ibw"](tag)
            RAW[k] = (NS2["signed"](d)[0], float(h["ScanSize"]) * 1e6)

    fig = plt.figure(figsize=(W, 4.60))
    gs = fig.add_gridspec(2, 4, left=0.066, right=0.988, bottom=0.072,
                          top=0.912, height_ratios=[1.26, 1.00],
                          width_ratios=[1, 1, 1, 1.12], wspace=0.34,
                          hspace=0.40)

    def overlay(ax, col, lw=1.0):
        for a, b in lines:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=lw,
                    solid_capstyle="round", zorder=5)

    # ---- (a) and (b) the raw signed response, full frame
    gtop = gs[0, :].subgridspec(1, 3, width_ratios=[1, 1, 1.02], wspace=0.30)
    KC = np.array([7.69, 9.18])                 # the letter K, scan frame um
    KH = 2.25                                   # half a 4.5 um window
    for k, (key, ttl) in enumerate((("b", "before the letters"),
                                    ("a", "after the letters"))):
        ax = fig.add_subplot(gtop[0, k])
        S, L = RAW[key]
        v = float(np.percentile(np.abs(S), 98))
        im = ax.imshow(S, cmap="RdBu_r", vmin=-v, vmax=v, origin="lower",
                       extent=[0, L, 0, L], interpolation="nearest")
        overlay(ax, "#111111", 0.9)
        ax.set_xlim(0, L); ax.set_ylim(0, L)
        ax.set_xticks([0, 4, 8, 12]); ax.set_yticks([0, 4, 8, 12])
        ax.set_xlabel("x (\u00b5m)")
        if k == 0:
            ax.set_ylabel("y (\u00b5m)")
            ps.top_colorbar(fig, ax, im, "signed lateral response (pm)",
                            ticks=[-100, 0, 100], width=0.92, y=1.10,
                            height=0.040)
        else:
            # mark where panel c is taken from
            ax.add_patch(Rectangle(KC - KH, 2 * KH, 2 * KH, facecolor="none",
                                   edgecolor="#111111", lw=1.2,
                                   ls=(0, (3, 2)), zorder=7))
            ax.text(KC[0] + KH - 0.14, KC[1] + KH - 0.14, "c", ha="right",
                    va="top", fontsize=F["panel"], fontproperties=SB,
                    color="#111111", zorder=8,
                    bbox=dict(facecolor="#FFFFFFDD", edgecolor="none",
                              boxstyle="square,pad=0.16"))
        ax.text(0.5, 0.025, ttl, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=8.4, color="#111111", zorder=6,
                bbox=dict(facecolor="#FFFFFFDD", edgecolor="none",
                          boxstyle="square,pad=0.24"))
        inlabel(ax, "ab"[k])
        ps.square_map(ax)

    # ---- (c) the letter K, zoomed, from the same frame as b
    ax = fig.add_subplot(gtop[0, 2])
    S, L = RAW["a"]
    v = float(np.percentile(np.abs(S), 98))
    ax.imshow(S, cmap="RdBu_r", vmin=-v, vmax=v, origin="lower",
              extent=[0, L, 0, L], interpolation="bilinear", zorder=1)
    for a_, b_ in lines:                        # only the strokes in view
        if (min(a_[0], b_[0]) < KC[0] + KH and max(a_[0], b_[0]) > KC[0] - KH
                and min(a_[1], b_[1]) < KC[1] + KH
                and max(a_[1], b_[1]) > KC[1] - KH):
            ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="#111111", lw=1.3,
                    solid_capstyle="round", zorder=5)
    ax.set_xlim(KC[0] - KH, KC[0] + KH)
    ax.set_ylim(KC[1] - KH, KC[1] + KH)
    ax.set_xticks([6, 8, 10]); ax.set_yticks([8, 10])
    ax.set_xlabel("x (\u00b5m)")
    inlabel(ax, "c")
    ps.square_map(ax)

    # ---- (d) to (f) the population maps
    for k, (key, ttl) in enumerate((("W0", "before"), ("W1", "after"))):
        ax = fig.add_subplot(gs[1, k])
        im = ax.imshow(M[key], origin="lower", extent=ext, cmap="magma",
                       vmin=0.0, vmax=0.75, interpolation="nearest")
        overlay(ax, "#FFFFFF", 0.9)
        ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
        ax.set_xticks([2, 6, 10]); ax.set_yticks([2, 6, 10])
        ax.set_xlabel("x (\u00b5m)")
        if k == 0:
            ax.set_ylabel("y (\u00b5m)")
            ps.top_colorbar(fig, ax, im, "w at the commanded 2$\\degree$",
                            ticks=[0.0, 0.25, 0.50, 0.75], width=0.92,
                            y=1.14, height=0.048)
        ax.text(0.5, 0.035, ttl, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=8.2, color="#111111", zorder=6,
                bbox=dict(facecolor="#FFFFFFDD", edgecolor="none",
                          boxstyle="square,pad=0.20"))
        inlabel(ax, "de"[k])
        ps.square_map(ax)

    ax = fig.add_subplot(gs[1, 2])
    D = M["W1"] - M["W0"]
    im = ax.imshow(D, origin="lower", extent=ext, cmap="RdBu_r",
                   vmin=-0.6, vmax=0.6, interpolation="nearest")
    overlay(ax, "#111111", 0.9)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([2, 6, 10]); ax.set_yticks([2, 6, 10])
    ax.set_xlabel("x (\u00b5m)")
    ps.top_colorbar(fig, ax, im, "change in w", ticks=[-0.5, 0.0, 0.5],
                    width=0.92, y=1.14, height=0.048)
    ax.text(0.5, 0.035, "difference", transform=ax.transAxes, ha="center",
            va="bottom", fontsize=8.2, color="#111111", zorder=6,
            bbox=dict(facecolor="#FFFFFFDD", edgecolor="none",
                      boxstyle="square,pad=0.20"))
    inlabel(ax, "f")
    ps.square_map(ax)

    # ---- (g) per letter
    ax = fig.add_subplot(gs[1, 3])
    L = U["letters"]
    order = ["U", "T", "K"]
    x = np.arange(3)
    b0 = [L[k][0] for k in order]
    b1 = [L[k][1] for k in order]
    ax.bar(x - 0.19, b0, 0.36, color=C["light_grey"], edgecolor="none",
           label="before")
    ax.bar(x + 0.19, b1, 0.36, color=AIC, edgecolor="none", label="after")
    for i2, (v0, v1) in enumerate(zip(b0, b1)):
        ax.text(i2 + 0.19, v1 + 0.018, "+%.2f" % (v1 - v0), ha="center",
                fontsize=7.6, color=AIC)
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=10.0)
    ax.set_ylim(0, 0.70); ax.set_yticks([0, 0.2, 0.4, 0.6])
    ax.set_ylabel("w at 2$\\degree$")
    ps.boxed_legend(ax, loc="upper left", fontsize=7.4, labelspacing=0.20,
                    handlelength=0.9, borderpad=0.24)
    ps.close_frame(ax)

    letters(fig, [(0.742, 0.352, "g")])
    ps.save_figure(fig, OUT, "fig9_writing_a_word",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig9"


# ============================= Figure 10: the two phases, side by side
def fig10():
    """One message: what changed between the two phases, and what did not.

    Three bar panels on top, and the failure summary as a full width band
    underneath. Everything is a point or two larger than before, and the
    labels that used to sit inside the bars in white are gone, since at
    insertion size they were unreadable.
    """
    FL = json.loads((PROJ / "aug_process_numbers.json").read_text())["floors_own_target"]
    G = json.loads((PROJ / "paper_llm" / "guards.json").read_text())
    CS, C1 = P2["census"], P2["phase1"]
    CF, TL = NP["findings"], P2["tooling"]
    CN = P2["conclusions"]
    P1C, P2C = C["light_grey"], AIC

    fig = plt.figure(figsize=(W, 3.62))
    gs = fig.add_gridspec(2, 3, left=0.076, right=0.988, bottom=0.052,
                          top=0.912, height_ratios=[1.00, 0.42],
                          width_ratios=[1.06, 0.94, 1.22], wspace=0.44,
                          hspace=0.74)

    def pair(ax, labels, v1, v2, ylab, fmt="%d", ymax=None, rot=0):
        x = np.arange(len(labels))
        ax.bar(x - 0.19, v1, 0.36, color=P1C, edgecolor="none",
               label="campaign 1")
        ax.bar(x + 0.19, v2, 0.36, color=P2C, edgecolor="none",
               label="campaign 2")
        hi = ymax or max(max(v1), max(v2)) * 1.30
        for i, (a, b) in enumerate(zip(v1, v2)):
            ax.text(i - 0.19, a + hi * 0.025, fmt % a, ha="center",
                    fontsize=8.0, color=C["grey"])
            ax.text(i + 0.19, b + hi * 0.025, fmt % b, ha="center",
                    fontsize=8.0, color=P2C)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.6, rotation=rot,
                           ha="right" if rot else "center",
                           rotation_mode="anchor" if rot else None)
        ax.set_ylim(0, hi)
        ax.set_ylabel(ylab, fontsize=9.2)
        ax.tick_params(labelsize=8.6)
        ps.close_frame(ax)

    # ---- (a) instrument time, and who spent it
    ax = fig.add_subplot(gs[0, 0])
    ax.bar([0], [C1["active_instr_min"]], 0.64, color=P1C, edgecolor="none")
    ax.bar([1], [CS["loop_instr_min"] - CS["write_min"]], 0.64, color=P2C,
           edgecolor="none", label="imaging, tuning")
    ax.bar([1], [CS["write_min"]], 0.64,
           bottom=[CS["loop_instr_min"] - CS["write_min"]], color=C["red"],
           edgecolor="none", label="writing")
    ax.text(0, C1["active_instr_min"] + 42, "%d" % C1["active_instr_min"],
            ha="center", fontsize=8.4, color=C["grey"])
    ax.text(1, CS["loop_instr_min"] + 42, "%d" % CS["loop_instr_min"],
            ha="center", fontsize=8.4, color=P2C)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["campaign 1\noperator", "campaign 2\nagent"],
                       fontsize=8.6, linespacing=1.28)
    ax.set_ylim(0, 1420); ax.set_yticks([0, 300, 600, 900])
    ax.set_ylabel("active instrument\ntime (min)", fontsize=9.2)
    ax.tick_params(labelsize=8.6)
    ps.boxed_legend(ax, loc="upper center", fontsize=7.6, labelspacing=0.18,
                    handlelength=0.9, borderpad=0.24)
    ps.close_frame(ax)

    # ---- (b) what the agent did with the actuator
    ax = fig.add_subplot(gs[0, 1])
    pair(ax, ["writes it\nissued", "runs it\nhalted", "areas it\nchose"],
         [0, 0, 0], [CS["driver_runs"], CS["halts"], CS["areas"]],
         "count", ymax=13.5)
    ps.boxed_legend(ax, loc="upper left", fontsize=7.6, labelspacing=0.18,
                    handlelength=0.9, borderpad=0.24)

    # ---- (c) the record it kept
    ax = fig.add_subplot(gs[0, 2])
    pair(ax, ["graded", "withdrawn", "overturned"],
         [CN["phase1_total"], CF["superseded"], 0],
         [CN["phase2_total"], CN["withdrawn"], CN["overturned_own"]],
         "count", ymax=76)

    # ---- (d) what did not improve, as a full width band
    ax = fig.add_subplot(gs[1, :])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    blank(ax)
    ax.add_patch(Rectangle((-0.012, -0.10), 1.024, 0.98, facecolor="#FDF3F1",
                           edgecolor="#EBD3CD", lw=0.9, zorder=0))
    ax.text(0.0, 1.20, "what did not improve", ha="left", va="top",
            fontsize=9.4, fontproperties=SB, color=C["red"], zorder=2)
    items = [("%d of %d launches" % (TL["launch_faults"], TL["launches"]),
              "died on faults a parser\nwould have caught"),
             ("%d of %d overnight faults" % (TL["overnight_in_tooling"],
                                             TL["overnight_faults"]),
              "were in its own tooling,\nnone in the physics"),
             ("the central guard", "encoded all 29 checks and\nhad never "
              "once been called")]
    for k, (hd, bd) in enumerate(items):
        x0 = 0.018 + k * 0.334
        ax.text(x0, 0.70, hd, ha="left", va="center", fontsize=8.8,
                fontproperties=SB, color=C["black"], zorder=2)
        ax.text(x0, 0.24, bd, ha="left", va="center", fontsize=8.0,
                color=C["black"], linespacing=1.32, zorder=2)

    letters(fig, [(0.006, 0.920, "a"), (0.352, 0.920, "b"),
                  (0.646, 0.920, "c"), (0.006, 0.272, "d")])
    ps.save_figure(fig, OUT, "fig10_two_phases",
                   formats=("png", "pdf", "svg"), pad_inches=0.03)
    LAST['fig'] = fig
    if not KEEP_OPEN:
        plt.close(fig)
    return "fig10"


if __name__ == "__main__":

    import sys as _s
    only = set(_s.argv[1:])
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10):
        if only and f.__name__ not in only:
            continue
        print(" ", f())
