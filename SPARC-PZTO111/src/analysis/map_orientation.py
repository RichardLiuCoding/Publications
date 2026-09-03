# -*- coding: utf-8 -*-
"""map_orientation.py -- local director map, far below the FFT window limit.

FREE: analysis only, on frames already taken.

WHY. The FFT population estimator needs >= 4 Lambda, so on a 2 um zoom it can
only report 4 tiles of ~1 um. That is far too coarse to see whether a rewritten
region switched as one block or as merging islands -- the question the pathway
study is actually about.

`orient()` is a structure-tensor estimator: it returns a local director at every
pixel from image gradients, with a smoothing length set in nanometres rather
than in periods. At sg_tens ~ 150 nm that is a director map at roughly half a
lamellar period, ~20x finer than the FFT tiles.

WHAT IT PRODUCES
  * a director map of the zoom frame
  * the fraction of area on each triad member
  * the size distribution of same-member patches -- the island statistic
  * a figure: director map, member map, and patch histogram

WHAT IT CANNOT DO. It reports a stripe orientation mod 180 deg, like every
lateral measurement here, so it cannot see polarisation sense. And a structure
tensor smooths over its own window: features below ~2 x sg_tens are not resolved.
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
ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__
configure_style()


def analyse(tag, label, sg_tens=150.0):
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    L = float(h['ScanSize']) * 1e6
    px = L / S.shape[0] * 1000.0
    triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    triad = [float(t) for t in triad]

    # orient() returns a TUPLE (theta, coherence), not an array. Coercing the
    # tuple and indexing [...,0] silently produced a (2,256) slice and a
    # meaningless map -- same trap as pops() returning a 5-tuple.
    _o = g('orient')(S, px, sg_grad_nm=45.0, sg_tens_nm=sg_tens)
    assert isinstance(_o, tuple) and len(_o) == 2, 'orient() signature changed'
    th = np.mod(np.asarray(_o[0], float), 180.0)
    coh = np.asarray(_o[1], float)
    assert th.shape == S.shape, 'orientation map %s vs image %s' % (th.shape,
                                                                   S.shape)
    # low-coherence pixels have no defined stripe direction; excluding them is
    # not cosmetic, it is the difference between mapping domains and mapping
    # noise
    good = coh >= float(np.nanpercentile(coh, 40))

    dif = np.stack([np.abs((th - t + 90.0) % 180.0 - 90.0) for t in triad])
    member = np.argmin(dif, axis=0)
    off = np.min(dif, axis=0)
    frac = [float(np.mean(member[good] == k)) for k in range(3)]

    # patch statistics on the dominant member: how big are the domains?
    from scipy import ndimage as ndi
    kdom = int(np.argmax(frac))
    lab, n = ndi.label((member == kdom) & good)
    sizes = (np.bincount(lab.ravel())[1:] * (px / 1000.0) ** 2
             if n else np.array([]))
    member = np.where(good, member, -1)
    return dict(tag=tag, label=label, S=S, px=px, L=L, th=th, member=member,
                triad=triad, frac=frac, off=off, sizes=sizes, mod=tt['mod'],
                kdom=kdom)


def report(r):
    print('\n=== %s (%s) ===' % (r['label'], r['tag']))
    print('  %.2f nm/px, modulation %.3f, triad %s'
          % (r['px'], r['mod'], [int(round(t)) for t in r['triad']]))
    print('  area fraction per member: %s'
          % ' '.join('%.0f deg %.0f%%' % (r['triad'][k], 100 * r['frac'][k])
                     for k in range(3)))
    print('  median |offset from nearest member| %.1f deg'
          % float(np.median(r['off'])))
    s = r['sizes']
    if len(s):
        s = np.sort(s)[::-1]
        tot = float(np.sum(s))
        print('  dominant-member patches: %d, largest %.3f um^2 (%.0f%% of the '
              'member area)' % (len(s), s[0], 100 * s[0] / max(tot, 1e-9)))
        print('  patches > 0.05 um^2: %d' % int(np.sum(s > 0.05)))
        if s[0] / max(tot, 1e-9) > 0.8:
            print('  -> ONE connected domain: the member area is a single '
                  'patch, not islands.')
        else:
            print('  -> FRAGMENTED: the dominant member is split across '
                  'patches; islands have not merged.')


def figure(rs, stem='figP_orientation'):
    n = len(rs)
    fig = plt.figure(figsize=(2.45 * n, 5.1))
    gs = fig.add_gridspec(2, n, hspace=0.30, wspace=0.18, left=0.06,
                          right=0.98, top=0.90, bottom=0.09)
    cols = [COLORS['green'], COLORS['red'], COLORS['blue']]
    from matplotlib.colors import ListedColormap
    cm = ListedColormap(cols)
    for j, r in enumerate(rs):
        ext = [0, r['L'], 0, r['L']]
        ax = fig.add_subplot(gs[0, j])
        v = float(np.nanpercentile(np.abs(r['S']), 98))
        ax.imshow(r['S'], origin='lower', extent=ext, cmap='RdBu_r',
                  clim=(-v, v))
        square_map(ax); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(r['label'], loc='left', fontsize=8.0)
        ax = fig.add_subplot(gs[1, j])
        m = np.ma.masked_where(r['member'] < 0, r['member'])
        ax.imshow(m, origin='lower', extent=ext, cmap=cm,
                  clim=(-0.5, 2.5), interpolation='nearest')
        square_map(ax); ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlabel(' '.join('%.0f%%' % (100 * f) for f in r['frac']),
                      fontsize=7.0)
    fig.text(0.06, 0.955, 'in-plane signal (top) and nearest triad member '
                          '(bottom)', fontsize=8.6)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
    fig.legend(hs, ['member 1', 'member 2', 'member 3'], fontsize=7.0,
               loc='lower center', ncol=3, frameon=False)
    save_figure(fig, OUT, stem)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    spec = []
    for a in sys.argv[1:]:
        if ':' in a:
            t, lab = a.split(':', 1)
        else:
            t, lab = a, a
        spec.append((t if t.endswith('.ibw') else t + '.ibw', lab))
    if not spec:
        print('usage: python map_orientation.py TAG:label [TAG:label ...]')
        return
    rs = []
    for t, lab in spec:
        try:
            r = analyse(t, lab)
            report(r)
            rs.append(r)
        except Exception as e:
            print('  %s failed: %s' % (t, e))
    if rs:
        figure(rs)
        print('\nfigure written to %s' % OUT)


if __name__ == '__main__':
    main()
