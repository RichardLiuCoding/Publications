# -*- coding: utf-8 -*-
"""screen_areas.py -- pick a working area, TOPOGRAPHY INCLUDED.

MEASUREMENT ONLY. No bias, no litho, no S24 cost.

WHY THIS EXISTS. The campaign's area gates have always been modulation, streak
and Lambda -- all computed from the lateral channel. **Not one of them looks at
the height channel.** On 29 August the operator pointed out that the first area
at a new stage position sat on a large step edge, plainly visible in
topography, which no gate would have caught. The lateral signal on a step edge
is not a domain measurement: the tip's torsion responds to the slope.

Measured on that frame against two areas that worked:

  bad area   plane-removed roughness 3.28 nm, 1-99 % peak-to-peak 19.9 nm
  good areas                        0.39-0.60 nm,                1.8-3.6 nm

so the gate is roughness <= 1.0 nm and peak-to-peak <= 5.0 nm, which separates
them by a factor of three with room to spare.

Bimodality of the height histogram was tried first and does NOT discriminate --
it flags both good and bad frames. Roughness and range do.

  SCR_PTS="0,0 6,0 -6,0 0,6 0,-6 6,6 -6,-6"
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A
import scale_tools as ST

SIZE_UM = 2.5
PX = 256                       # 9.77 nm/px: plenty for topography and Lambda
RATE = 2.0
ROUGH_MAX = 1.0                # nm, plane-removed
P2P_MAX = 5.0                  # nm, 1-99 percentile
MOD_MIN = 0.15
STREAK_MAX = 0.10
LAM_LO, LAM_HI = 150.0, 320.0  # 320 keeps a 1.4 um window above 4 Lambda
STAMP = time.strftime('%y%m%d_%H%M')

_env = os.environ.get('SCR_PTS', '').strip()
PTS = ([tuple(float(v) for v in p.split(',')) for p in _env.split()] if _env
       else [(0., 0.), (6., 0.), (-6., 0.), (0., 6.), (0., -6.),
             (6., 6.), (-6., -6.), (6., -6.), (-6., 6.)])


def topo(d, h):
    """Plane-removed roughness and 1-99 % range of the HEIGHT channel, in nm.

    Channel 0 is Height. The Igor labels are offset by one and the true order
    is 0 Height, 1 Amp1, 2 Amp2, 3 Phase1, 4 Phase2, 5 Freq (FINDINGS M13).
    """
    Z = np.asarray(d[0], float) * 1e9
    Z = np.nan_to_num(Z - np.nanmedian(Z))
    yy, xx = np.mgrid[0:Z.shape[0], 0:Z.shape[1]]
    M = np.c_[xx.ravel(), yy.ravel(), np.ones(Z.size)]
    c, _, _, _ = np.linalg.lstsq(M, Z.ravel(), rcond=None)
    F = Z - (c[0] * xx + c[1] * yy + c[2])
    return float(np.std(F)), float(np.percentile(F, 99) - np.percentile(F, 1))


def main():
    print('=' * 82)
    print('AREA SCREEN  %s   (measurement only)' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 82)
    print('  %d offsets, %.1f um at %d px = %.2f nm/px'
          % (len(PTS), SIZE_UM, PX, SIZE_UM / PX * 1000))
    print('  gates: roughness <= %.1f nm, p2p <= %.1f nm, modulation >= %.2f,'
          % (ROUGH_MAX, P2P_MAX, MOD_MIN))
    print('         streak <= %.2f, Lambda %.0f-%.0f nm'
          % (STREAK_MAX, LAM_LO, LAM_HI))
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    rows = []
    for k, (xo, yo) in enumerate(PTS):
        print('\n--- %d/%d  (%+.1f,%+.1f) ---' % (k + 1, len(PTS), xo, yo))
        try:
            g('scanner_ok')(xo, yo, SIZE_UM)
            _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX,
                                     rate=RATE, angle_deg=0.0, xoff_um=xo,
                                     yoff_um=yo, tries=1, verbose=False)
            tag = inf['frame']
            d, h = g('ibw')(tag)
            S, _, r12 = g('signed')(d)
            px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
            rough, p2p = topo(d, h)
            tri, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
            tri = [float(t) for t in tri]
            dom = float(tri[int(np.argmax(np.asarray(tt['w'], float)))])
            lam = ST.band_period(S, px, dom, 150.0, 500.0)
            sk = g('streak_index')(tag, (0.2, SIZE_UM - 0.2, 0.2, 0.8),
                                   verbose=False)
            ok = (rough <= ROUGH_MAX and p2p <= P2P_MAX
                  and tt['mod'] >= MOD_MIN and sk <= STREAK_MAX
                  and LAM_LO <= lam <= LAM_HI)
            why = []
            if rough > ROUGH_MAX:
                why.append('rough %.2f' % rough)
            if p2p > P2P_MAX:
                why.append('p2p %.1f' % p2p)
            if tt['mod'] < MOD_MIN:
                why.append('mod %.3f' % tt['mod'])
            if sk > STREAK_MAX:
                why.append('streak %.3f' % sk)
            if not (LAM_LO <= lam <= LAM_HI):
                why.append('Lambda %.0f' % lam)
            rows.append(dict(x=xo, y=yo, tag=tag, rough=rough, p2p=p2p,
                             mod=float(tt['mod']), sk=float(sk), lam=lam,
                             dom=dom, tri=tri, ok=ok, r12=r12))
            print('    rough %5.2f nm  p2p %5.2f nm | mod %.3f  streak %.3f |'
                  ' Lambda %.0f nm  dom %.0f  r12 %+.2f  -> %s%s'
                  % (rough, p2p, tt['mod'], sk, lam, dom, r12,
                     'USABLE' if ok else 'no', '' if ok else ' (%s)'
                     % ', '.join(why)))
        except Exception:
            print('    failed:')
            traceback.print_exc(limit=2)

    print('\n' + '=' * 82)
    good = [r for r in rows if r['ok']]
    print('%-14s %8s %8s %7s %8s %8s %6s  %s'
          % ('offset', 'rough', 'p2p', 'mod', 'streak', 'Lambda', 'dom', 'use'))
    for r in sorted(rows, key=lambda q: (-q['ok'], q['rough'])):
        print('(%+5.1f,%+5.1f) %8.2f %8.2f %7.3f %8.3f %8.0f %6.0f  %s'
              % (r['x'], r['y'], r['rough'], r['p2p'], r['mod'], r['sk'],
                 r['lam'], r['dom'], 'YES' if r['ok'] else '-'))
    print('\n  %d of %d areas usable' % (len(good), len(rows)))
    if good:
        print('  usable offsets: %s'
              % ' '.join('%g,%g' % (r['x'], r['y']) for r in good))
        b = min(good, key=lambda q: q['rough'])
        print('  flattest: (%+.1f,%+.1f) roughness %.2f nm, triad %s, '
              'Lambda %.0f nm' % (b['x'], b['y'], b['rough'],
                                  [int(round(t)) for t in b['tri']], b['lam']))
    else:
        print('  NONE. Move the coarse stage again before writing anything.')


if __name__ == '__main__':
    buf = io.StringIO()

    class Tee(object):
        def __init__(self, *s):
            self.s = s

        def write(self, x):
            for t in self.s:
                t.write(x)
                t.flush()

        def flush(self):
            for t in self.s:
                t.flush()

    import contextlib
    try:
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            main()
    except Exception:
        traceback.print_exc()
    finally:
        io.open(os.path.join(A.PROJ, 'screen_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
