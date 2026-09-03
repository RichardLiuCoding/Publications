# -*- coding: utf-8 -*-
"""What was actually sent to the instrument, for the three write types.

Patterns are produced by the SAME generators the campaign drove the tip with:
`template_lib.parallel` for the point-pulse lattice, and the serpentine and
sign-arrangement logic of `block3_raster.py` for the DC and AC rasters. Nothing
here is redrawn by hand.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

import publication_style as ps
import template_lib as T

OUT = Path('figures_ms')
HALF, PITCH, STEP, V, ANG = 0.80, 0.03, 0.02, 10.0, 0.0
LAM = 0.29                                   # measured period, um
POS, NEG = '#C0392B', '#2B6CB0'


def raster_lines(centre, half, pitch, ang):
    """Serpentine endpoints, copied from block3_raster.raster_lines."""
    cx, cy = centre
    a = np.deg2rad(ang)
    u = np.array([np.cos(a), np.sin(a)])
    n = np.array([-np.sin(a), np.cos(a)])
    out = []
    for k, t in enumerate(np.arange(-half, half + 1e-9, pitch)):
        o = np.array([cx, cy]) + t * n
        p, q = o - half * u, o + half * u
        out.append((p, q) if k % 2 == 0 else (q, p))
    return out


def ac_segments(lines, acn=2):
    """Per-point sign flipping every `acn` points, as block3_raster builds it."""
    segs = []
    for (p, q) in lines:
        L = float(np.hypot(*(q - p)))
        u = (q - p) / max(L, 1e-12)
        nfull = int(np.floor(L / STEP))
        nch = (nfull // acn) // 2 * 2
        if nch < 2:
            continue
        npts = nch * acn
        pts = p[None, :] + (np.arange(npts) * STEP)[:, None] * u[None, :]
        sgn = np.where((np.arange(npts) // acn) % 2 == 0, 1.0, -1.0)
        segs.append((pts, sgn))
    return segs


def box(ax, cx, cy, half, lw=1.0):
    ax.add_patch(plt.Rectangle((cx - half, cy - half), 2 * half, 2 * half,
                               fill=False, ec='#333333', lw=lw, zorder=5))


def panel(ax, letter, title, sub):
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(0.0, 1.105, letter, transform=ax.transAxes, fontsize=9.6,
            fontweight='bold', va='bottom')
    ax.text(0.075, 1.105, title, transform=ax.transAxes, ha='left',
            va='bottom', fontsize=9.0, fontweight='bold')
    ax.text(0.075, 1.018, sub, transform=ax.transAxes, ha='left', va='bottom',
            fontsize=7.2, color='#5E6873')


def note(ax, text, y=-0.055):
    ax.text(0.055, y, text, transform=ax.transAxes, ha='left', va='top',
            fontsize=7.4, color='#333333', linespacing=1.38)


def main():
    fig, ax2 = plt.subplots(2, 2, figsize=(6.9, 4.72))
    axes = [ax2[0, 0], ax2[0, 1], ax2[1, 0], ax2[1, 1]]
    lines = raster_lines((0.0, 0.0), HALF, PITCH, ANG)
    show = lines[::2]                     # thinned for legibility only

    # (a) the stationary pulse: the zero-motion limit of the same family
    ax = axes[0]
    panel(ax, 'a', 'Stationary DC pulse', 'one site, no motion')
    ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 0.92)
    for r, al in ((0.30, 0.34), (0.45, 0.20), (0.60, 0.10)):
        ax.add_patch(plt.Circle((0.0, 0.14), r, fill=False, ec=POS, lw=0.9,
                                alpha=al, ls='--', zorder=2))
    ax.plot(0.0, 0.14, ls='none', marker='o', ms=5.6, mfc=POS, mec='none',
            zorder=4)
    ax.annotate('', xy=(0.60, 0.14), xytext=(0.0, 0.14),
                arrowprops=dict(arrowstyle='-|>', lw=1.0, color='#333333'))
    ax.text(0.66, 0.14, '0.6 $\\mu$m', ha='left', va='center',
            fontsize=7.0, color='#333333')
    note(ax, 'Dose is bias times dwell alone.\n'
             'Rotates its own patch above 40 V\u00b7s.', y=-0.045)

    # (b) DC raster: the two polarities are separated in TIME, so the square
    #     is drawn twice, once per pass
    ax = axes[1]
    panel(ax, 'b', 'Charge-balanced raster', 'bias plus motion')
    ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 0.92)
    for k, (dx, col, lab) in enumerate(((-0.50, POS, 'all +10 V'),
                                        (+0.50, NEG, 'all -10 V'))):
        for (p_, q_) in show:
            ax.plot([p_[0] * 0.42 + dx, q_[0] * 0.42 + dx],
                    [p_[1] * 0.42 + 0.14, q_[1] * 0.42 + 0.14],
                    color=col, lw=0.75, zorder=3)
        box(ax, dx, 0.14, HALF * 0.42)
        ax.text(dx, 0.14 - HALF * 0.42 - 0.055, lab, ha='center', va='top',
                fontsize=7.2, color=col)
    ax.annotate('', xy=(0.155, 0.14), xytext=(-0.155, 0.14),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color='#333333'))
    ax.text(0.0, 0.20, 'then', ha='center', va='bottom', fontsize=7.4,
            color='#333333')
    note(ax, 'One sign covers the whole square at a time.\n'
             'Net charge zero. 30 nm line pitch.', y=-0.045)

    # (b) AC raster: identical path and dose, both signs present at once
    ax = axes[2]
    panel(ax, 'c', 'AC raster', 'the sign-uniformity control')
    ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 0.92)
    for pts, sgn in ac_segments(lines[::6]):
        for sgv, col in ((+1, POS), (-1, NEG)):
            m = sgn == sgv
            ax.plot(pts[m, 0] * 0.86, pts[m, 1] * 0.86 + 0.14, ls='none',
                    marker='s', ms=2.0, mfc=col, mec='none', zorder=3)
    box(ax, 0.0, 0.14, HALF * 0.86)
    note(ax, 'Same path, same dose, same geometry.\n'
             'Both signs present in the square at once.', y=-0.045)

    # (c) the point-pulse lattice, from the campaign's own generator
    ax = axes[3]
    sites = np.asarray(T.parallel((0.0, 0.0), HALF, LAM, ANG, V))
    xs, ys, vs = sites[:, 0], sites[:, 1], sites[:, 2]
    panel(ax, 'd', 'Point-pulse lattice', 'a grid of stationary pulses')
    ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 0.92)
    for sgv, col in ((+1, POS), (-1, NEG)):
        m = np.sign(vs) == sgv
        ax.plot(xs[m] * 0.86, ys[m] * 0.86 + 0.14, ls='none', marker='o',
                ms=2.4, mfc=col, mec='none', zorder=3)
    box(ax, 0.0, 0.14, HALF * 0.86)
    note(ax, '%d discrete dwells, rows alternating\n'
             'every %d nm, charge balanced to zero.'
             % (len(sites), int(LAM * 500)), y=-0.045)

    fig.subplots_adjust(left=0.012, right=0.988, top=0.905, bottom=0.055,
                        wspace=0.06, hspace=0.42)
    ps.save_figure(fig, OUT, 'F1_control_space',
                   formats=('png', 'pdf', 'svg'), pad_inches=0.02)
    print('lattice sites %d, raster lines %d (every 2nd drawn)'
          % (len(sites), len(lines)))


if __name__ == '__main__':
    main()
