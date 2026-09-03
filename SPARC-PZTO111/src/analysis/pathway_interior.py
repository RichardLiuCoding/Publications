# -*- coding: utf-8 -*-
"""pathway_interior.py -- re-analyse the zoom frames INSIDE the written panel.

WHY THIS EXISTS. M22 classified each 2 um zoom as UNIFORM or MIXED from four
1.12 um FFT tiles. The written panel is only 1.2-1.4 um across and sits in the
middle of a 2.0 um frame, so **every one of those tiles overhangs the panel
edge** by 0.3-0.4 um and samples unwritten film. "Three tiles agree, one
differs" is then exactly what an edge overhang produces, with or without any
coexistence inside the panel. The same objection applies to the structure-tensor
patch statistics, which were computed over the whole frame.

WHAT THIS DOES INSTEAD. Two regions of the same frame, same estimator:

  INTERIOR   central 1.0 um -- entirely inside even the smallest (1.2 um) panel
  SURROUND   the outer border of the frame -- entirely outside even the
             largest (1.4 um) panel

The structure tensor is used rather than the FFT because it needs a smoothing
length (150 nm), not four periods, so a 1.0 um window is legitimate for it and
is not for the FFT.

WHAT IT CAN SETTLE. If the interior is single-orientation and the surround is
not, the rewrite is complete inside the panel and confined to it. If the
interior itself is fragmented, that is real coexistence and the nucleation
reading survives. If interior and surround agree, the panel did not take.

FREE: no instrument time, no write budget. Frames already on disk.
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
from publication_style import configure_style, square_map, save_figure, COLORS

OUT = os.path.join(HERE, 'figures_pathway')
INTERIOR_UM = 1.0        # inside the smallest panel (1.2 um) with 0.1 um margin
SURROUND_UM = 1.5        # outside the largest panel (1.4 um): border beyond this
SG_TENS_NM = 150.0

ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__
configure_style()

# zoom frame -> (label, the CSV run/panel it images, dose)
# every entry traced to the zoom_*.txt log that produced the frame and to
# results_templates.csv for the dose actually delivered
FRAMES = [
    ('PZTO_LDART_0247.ibw', 52,  '260829_0028 P1', 'area (0,+16)'),
    ('PZTO_LDART_0248.ibw', 67,  '260829_0020 P1', 'area (+16,0)'),
    ('PZTO_LDART_0251.ibw', 111, '260829_0228 P1', 'area (+24,-24)'),
    ('PZTO_LDART_0246.ibw', 117, '260829_0220 P1', 'area (0,-24)'),
    ('PZTO_LDART_0250.ibw', 120, '260829_0220 P2', 'area (0,-24)'),
    ('PZTO_LDART_0249.ibw', 306, '260828_2158 P1', 'area (0,0)'),
]


def director_map(S, px):
    """Per-pixel stripe orientation and coherence. orient() returns a TUPLE."""
    o = g('orient')(S, px, sg_grad_nm=45.0, sg_tens_nm=SG_TENS_NM)
    assert isinstance(o, tuple) and len(o) == 2, 'orient() signature changed'
    th = np.mod(np.asarray(o[0], float), 180.0)
    coh = np.asarray(o[1], float)
    assert th.shape == S.shape
    return th, coh


def stats(member, good, px):
    """Member fractions and connected-patch sizes over a masked region."""
    from scipy import ndimage as ndi
    if good.sum() < 50:
        return None
    frac = [float(np.mean(member[good] == k)) for k in range(3)]
    kdom = int(np.argmax(frac))
    lab, n = ndi.label((member == kdom) & good)
    if not n:
        return dict(frac=frac, kdom=kdom, biggest=0.0, npatch=0, area=0.0)
    sz = np.bincount(lab.ravel())[1:] * (px / 1000.0) ** 2
    sz = np.sort(sz)[::-1]
    return dict(frac=frac, kdom=kdom, biggest=float(sz[0]),
                npatch=int(np.sum(sz > 0.02)), area=float(sz.sum()))


def analyse(tag, sigma, prov, area):
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    L = float(h['ScanSize']) * 1e6
    px = L / S.shape[0] * 1000.0
    triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    triad = [float(t) for t in triad]

    th, coh = director_map(S, px)
    dif = np.stack([np.abs((th - t + 90.0) % 180.0 - 90.0) for t in triad])
    member = np.argmin(dif, axis=0)
    good = coh >= float(np.nanpercentile(coh, 40))

    n = S.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    r_um = np.maximum(np.abs(xx - c), np.abs(yy - c)) * px / 1000.0 * 2.0
    m_in = (r_um <= INTERIOR_UM) & good
    m_out = (r_um >= SURROUND_UM) & good

    si = stats(member, m_in, px)
    so = stats(member, m_out, px)
    return dict(tag=tag, sigma=sigma, prov=prov, area=area, S=S, px=px, L=L,
                member=member, good=good, triad=triad, mod=tt['mod'],
                inside=si, outside=so, m_in=m_in, m_out=m_out)


def report(r):
    print('\n=== sigma %-4d %s  (%s, %s) ===' % (r['sigma'], r['tag'],
                                                 r['prov'], r['area']))
    print('   %.2f nm/px, modulation %.3f, triad %s'
          % (r['px'], r['mod'], [int(round(t)) for t in r['triad']]))
    for nm, s in (('INTERIOR (%.1f um)' % INTERIOR_UM, r['inside']),
                  ('SURROUND (> %.1f um)' % SURROUND_UM, r['outside'])):
        if s is None:
            print('   %-22s too few coherent pixels' % nm)
            continue
        print('   %-22s members %s | dominant %.0f deg holds %.0f %%, '
              'largest patch %.3f um^2 = %.0f %% of it, %d patches'
              % (nm, ' '.join('%.0f%%' % (100 * f) for f in s['frac']),
                 r['triad'][s['kdom']], 100 * s['frac'][s['kdom']],
                 s['biggest'],
                 100 * s['biggest'] / max(s['area'], 1e-9), s['npatch']))
    si, so = r['inside'], r['outside']
    if si and so:
        same = si['kdom'] == so['kdom']
        print('   -> interior and surround are on %s member'
              % ('the SAME' if same else 'DIFFERENT'))
        if si['frac'][si['kdom']] > 0.80:
            print('   -> interior is SINGLE-ORIENTATION (%.0f %%)'
                  % (100 * si['frac'][si['kdom']]))
        elif si['frac'][si['kdom']] > 0.55:
            print('   -> interior is MAJORITY but not uniform (%.0f %%): '
                  'coexistence inside the panel' % (100 * si['frac'][si['kdom']]))
        else:
            print('   -> interior has NO clear majority')


def figure(rs):
    n = len(rs)
    # height chosen so a square panel FILLS its grid cell: six panels across
    # 7.25 in leaves ~1.09 in per column, so two rows plus labels and the
    # legend need ~3.15 in. A taller figure would put white bands around the
    # squares (the "small panel in an oversized cell" defect).
    fig = plt.figure(figsize=(7.25, 3.15))
    gs = fig.add_gridspec(2, n, left=0.055, right=0.985, bottom=0.185,
                          top=0.88, hspace=0.16, wspace=0.09)
    from matplotlib.colors import ListedColormap
    cols = [COLORS['red'], COLORS['blue'], COLORS['green']]
    cm = ListedColormap(cols)
    axes_top, axes_bot = [], []
    for j, r in enumerate(rs):
        ext = [0, r['L'], 0, r['L']]
        ax = fig.add_subplot(gs[0, j])
        v = float(np.nanpercentile(np.abs(r['S']), 98))
        ax.imshow(r['S'], origin='lower', extent=ext, cmap='RdBu_r',
                  clim=(-v, v))
        ax.set_xticks([]); ax.set_yticks([]); square_map(ax)
        # mark the region actually analysed
        h = INTERIOR_UM / 2.0
        ax.add_patch(plt.Rectangle((r['L'] / 2 - h, r['L'] / 2 - h),
                                   2 * h, 2 * h, fill=False, lw=0.9,
                                   ec='black', ls='--'))
        axes_top.append(ax)

        ax = fig.add_subplot(gs[1, j])
        m = np.where(r['good'], r['member'], -1).astype(float)
        m = np.ma.masked_where(m < 0, m)
        ax.imshow(m, origin='lower', extent=ext, cmap=cm, clim=(-0.5, 2.5),
                  interpolation='nearest')
        ax.set_xticks([]); ax.set_yticks([]); square_map(ax)
        ax.add_patch(plt.Rectangle((r['L'] / 2 - h, r['L'] / 2 - h),
                                   2 * h, 2 * h, fill=False, lw=0.9,
                                   ec='black', ls='--'))
        si = r['inside']
        ax.set_xlabel('%d\n%.0f %%' % (r['sigma'],
                                       100 * si['frac'][si['kdom']]),
                      fontsize=7.6, linespacing=1.25)
        axes_bot.append(ax)

    fig.text(0.5, 0.018, u'areal dose σ (V·s/µm$^2$), and the fraction of the '
             u'boxed interior on its dominant member', ha='center',
             fontsize=8.4)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
    fig.legend(hs, ['member 1', 'member 2', 'member 3'], fontsize=7.8,
               loc='upper center', bbox_to_anchor=(0.5, 1.005), ncol=3,
               frameon=False)
    fig.canvas.draw()
    for ax, lab in ((axes_top[0], 'a'), (axes_bot[0], 'b')):
        p = ax.get_position()
        fig.text(p.x0 - 0.042, p.y1 - 0.004, lab, fontsize=11.0,
                 fontweight='bold', va='bottom')
    save_figure(fig, OUT, 'figP_interior')
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    print('=' * 78)
    print('PATHWAY, RE-ANALYSED INSIDE THE PANEL')
    print('=' * 78)
    print('  interior %.1f um (inside every panel); surround beyond %.1f um'
          % (INTERIOR_UM, SURROUND_UM))
    print('  estimator: structure tensor, %.0f nm smoothing (no 4-Lambda need)'
          % SG_TENS_NM)
    rs = []
    for tag, sig, prov, area in FRAMES:
        try:
            r = analyse(tag, sig, prov, area)
            report(r)
            rs.append(r)
        except Exception as e:
            print('  %s failed: %s' % (tag, e))
    if not rs:
        return
    print('\n' + '=' * 78)
    print('DOSE ORDERING OF THE INTERIOR')
    print('=' * 78)
    print('  %-6s %-22s %-10s %s' % ('sigma', 'frame', 'interior', 'verdict'))
    for r in sorted(rs, key=lambda r: r['sigma']):
        si = r['inside']
        f = si['frac'][si['kdom']]
        print('  %-6d %-22s %-10s %s'
              % (r['sigma'], r['tag'], '%.0f %%' % (100 * f),
                 'single-orientation' if f > 0.80 else
                 ('coexistence' if f > 0.55 else 'no majority')))
    fr = [r['inside']['frac'][r['inside']['kdom']] for r in rs]
    sg = [r['sigma'] for r in rs]
    cc = float(np.corrcoef(np.log(sg), fr)[0, 1])
    print('\n  correlation of interior uniformity with log(dose): r = %.3f '
          'on n = %d' % (cc, len(rs)))
    print('  (a nucleation-and-growth pathway predicts r > 0 and a rise '
          'towards 1;')
    print('   no correlation means the panels are all past completion, or that')
    print('   dose is not the variable that sets uniformity.)')
    figure(sorted(rs, key=lambda r: r['sigma']))
    print('\n  figure written to %s' % OUT)


if __name__ == '__main__':
    main()
