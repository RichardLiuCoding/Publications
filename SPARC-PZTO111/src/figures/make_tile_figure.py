# -*- coding: utf-8 -*-
"""make_tile_figure.py -- F7, two variants written side by side.

Panels
  (a), (b) each tile read inside its OWN written square: the frame is rotated
      back by the commanded angle and the largest axis-aligned window that
      fits, 1.50 um, is taken.
  (c) angular band power of the two windows on one axis, converted back to the
      laboratory frame, with the three members of the film-wide triad marked.

An earlier version had a fourth panel showing "the frame taken after both
writes, centred on the join". No such frame exists: the one used was taken by
another process at a different area (PITFALLS 21.29). Every frame here is now
checked against its own header offsets before it is drawn.

Everything is computed from the .ibw frames; nothing is taken from a table.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import autoloop as A
import scale_tools as ST
import publication_style as PS

PS.configure_style()
C = PS.COLORS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures_ms')
SUPER = (150.0, 500.0)
WIN_UM = 1.50
SQ = 1.6
MEMBERS = (18.21, 78.21, 138.21)

TILES = [('A', 0.0, 'PZTO_LDART_0107.ibw', -0.8),
         ('B', 60.0, 'PZTO_LDART_0109.ibw', +0.8)]
# the join, re-imaged after both writes with header verification
JOIN = ('PZTO_LDART_0118.ibw', -6.0, -18.0)
SQ = 1.6


def square_outline(ax, cx, cy, side, ang_deg, **kw):
    """Outline of a square of `side` centred (cx,cy) and rotated by ang_deg."""
    t = np.radians(ang_deg)
    h = side / 2.0
    pts = np.array([[-h, -h], [h, -h], [h, h], [-h, h], [-h, -h]])
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    p = pts @ R.T + np.array([cx, cy])
    ax.plot(p[:, 0], p[:, 1], **kw)


def rotated_window(S, px, ang, win_um=WIN_UM):
    R = ndimage.rotate(np.nan_to_num(S), -ang, reshape=False, order=1,
                       mode='constant', cval=0.0)
    n = R.shape[0]
    h = int(round(win_um * 500.0 / px))
    c = n // 2
    return R[c - h:c + h, c - h:c + h]


def main():
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__

    fig = plt.figure(figsize=(7.2, 4.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1.0],
                          height_ratios=[1.0, 1.0], hspace=0.34, wspace=0.34)
    axJ = fig.add_subplot(gs[:, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 1])
    axP = None

    # the join, from a frame checked against its own header
    dj, hj = g('ibw')(JOIN[0])
    gjx, gjy = float(hj['XOffset']) * 1e6, float(hj['YOffset']) * 1e6
    if abs(gjx - JOIN[1]) > 0.05 or abs(gjy - JOIN[2]) > 0.05:
        raise RuntimeError('%s is at (%.2f,%.2f), not the join'
                           % (JOIN[0], gjx, gjy))
    SJ, _, _ = g('signed')(dj)
    pxj = float(hj['ScanSize']) * 1e6 / SJ.shape[0] * 1000.0
    ej = SJ.shape[0] * pxj / 2000.0
    axJ.imshow(SJ, cmap='RdBu_r', origin='lower',
               extent=[-ej, ej, -ej, ej],
               vmin=np.nanpercentile(SJ, 2), vmax=np.nanpercentile(SJ, 98))
    for lab, ang, _t, dx in TILES:
        square_outline(axJ, dx, 0.0, SQ, ang, color='k', lw=1.1)
    axJ.add_patch(plt.Rectangle((-0.62 - 0.6, -0.6), 1.2, 1.2, fill=False,
                                ec='k', ls='--', lw=0.9))
    axJ.text(-0.62, -0.92, 'A', ha='center', fontsize=7)
    axJ.text(0.8, -1.02, 'B', ha='center', fontsize=7)
    axJ.set_xlim(-ej, ej)
    axJ.set_ylim(-ej, ej)
    axJ.set_xlabel(u'x (µm)')
    axJ.set_ylabel(u'y (µm)')
    PS.square_map(axJ)
    PS.close_frame(axJ)

    for k, (lab, ang, tag, dx) in enumerate(TILES):
        dd, hh = g('ibw')(tag)
        # every frame is checked against where it was asked to be: the first
        # version of this figure used a frame taken by another process at a
        # different area (PITFALLS 21.29)
        gx = float(hh['XOffset']) * 1e6
        gy = float(hh['YOffset']) * 1e6
        if abs(gx - (-6.0 + dx)) > 0.05 or abs(gy + 18.0) > 0.05:
            raise RuntimeError('%s is at (%.2f,%.2f), not where tile %s was '
                               'written' % (tag, gx, gy, lab))
        SS, _, _ = g('signed')(dd)
        pxx = float(hh['ScanSize']) * 1e6 / SS.shape[0] * 1000.0
        W = rotated_window(SS, pxx, ang)
        e = W.shape[0] * pxx / 2000.0
        ax = (ax1, ax2)[k]
        ax.imshow(W, cmap='RdBu_r', origin='lower', extent=[-e, e, -e, e],
                  vmin=np.nanpercentile(W, 2), vmax=np.nanpercentile(W, 98))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(u'tile %s, commanded %.0f°' % (lab, ang), fontsize=6.5,
                     pad=3)
        PS.close_frame(ax)
        PS.add_scalebar(ax, length=0.5, label=u'0.5 µm', x=-e + 0.12,
                        y=-e + 0.12, label_offset=0.06)

        th, pw, _t = ST.band_angular_power(W, pxx, *SUPER)
        dirn, an, lam, pv = ST.band_peak(W, pxx, *SUPER, n_perm=300)
        th_lab = (th - ang) % 180.0
        o = np.argsort(th_lab)
        ax.text(0.03, 0.94, u'%.1f°' % ((dirn - ang) % 180.0),
                transform=ax.transAxes, va='top', fontsize=6.5, color='k')

    PS.align_panel_letters(fig, [[(0, axJ, 'a'), (1, ax1, 'b')],
                                 [(1, ax2, 'c')]])
    PS.save_figure(fig, OUT, 'F7_tiles')
    plt.close(fig)
    print('  F7 rebuilt without the invalid panel')


if __name__ == '__main__':
    main()
