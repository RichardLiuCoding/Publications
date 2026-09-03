# -*- coding: utf-8 -*-
"""retention_raster.py -- do the RASTER-written directors survive?

MEASUREMENT ONLY. No bias, no litho, no S24 cost.

The manuscript quotes 64-92 % retention over five hours, but those numbers are
for LATTICE-written panels, where the observable is a matched-filter amplitude
at the template wavevector. A raster has no template wavevector: what is
written is a DIRECTION, and the right retention observable is whether the
director stays put and whether the anisotropy holds.

The only raster retention datum in the campaign is 34 minutes (C50). Tonight's
raster panels are 3-5 hours old, and re-imaging them costs nothing.

  RR_AREAS="12,12 -6,-6 0,-6 -6,0 0,18 18,-18"
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

SIZE_UM, PX, RATE = 2.5, 512, 2.0
IN_HALF = 0.60
SUPER = (150.0, 500.0)
STAMP = time.strftime('%y%m%d_%H%M')

# area -> (raster angle, written at, director after the write, anisotropy after)
REF = {
    (12.0, 12.0): (46.0, '19:47', 18.8, 10.85),
    (-6.0, -6.0): (0.0, '20:14', 18.8, 22.74),
    (0.0, -6.0): (120.0, '20:40', 138.8, 9.61),
    (-6.0, 0.0): (60.0, '21:53', 78.8, 5.70),
    (0.0, 18.0): (41.0, '22:54', 18.8, 18.60),
    (18.0, -18.0): (41.0, '23:21', 18.8, 16.86),
    # round 3 and the speed replicate. Re-imaging these costs no write budget
    # and buys two things: a second independent image of each landing, which
    # halves the error on the triad measurement, and retention points at a
    # different age from the first set.
    (12.0, 18.0): (41.0, '01:33', 26.2, 5.67),
    (6.0, 12.0): (41.0, '01:55', 18.8, 18.63),
    (-6.0, -12.0): (41.0, '02:17', 18.8, 35.96),
    (-12.0, -6.0): (120.0, '03:04', 138.8, 4.30),
    (12.0, 6.0): (41.0, '03:27', 18.8, 13.46),
    # the two tiles and the third re-aim. The re-aimed state came back weak
    # (anisotropy 3.64, p 0.035); whether a weak written state survives hours
    # is a different question from whether a strong one does, and it is free
    # to ask.
    (-6.8, -18.0): (0.0, '03:51', 18.8, 19.40),
    (-5.2, -18.0): (60.0, '04:15', 78.8, 36.06),
    (6.0, -12.0): (120.0, '05:16', 138.8, 3.64),
}


def interior(S, px):
    n = S.shape[0]
    hp = int(round(IN_HALF * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def main():
    env = os.environ.get('RR_AREAS', '').split()
    areas = ([tuple(float(v) for v in a.split(',')) for a in env] if env
             else sorted(REF))
    print('=' * 84)
    print('RASTER RETENTION  %s   (measurement only)'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 84)
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    rows = []
    for a in areas:
        ref = REF.get(a)
        if ref is None:
            print('  (%+.1f,%+.1f): no reference; skipping' % a)
            continue
        ang, when, d0, an0 = ref
        print('\n--- (%+.1f,%+.1f)  raster %.0f deg written %s ---'
              % (a[0], a[1], ang, when))
        try:
            g('scanner_ok')(a[0], a[1], SIZE_UM)
            _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX,
                                     rate=RATE, angle_deg=0.0, xoff_um=a[0],
                                     yoff_um=a[1], tries=1, verbose=False)
            tag = inf['frame']
            d, h = g('ibw')(tag)
            S, _, r12 = g('signed')(d)
            px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
            dd, an, per, pv = ST.band_peak(interior(S, px), px, *SUPER,
                                           n_perm=300)
            drift = ST.angle_between(dd, d0)
            rows.append((a, ang, when, d0, an0, dd, an, pv, drift, tag))
            print('    %s  director %.1f -> %.1f deg (drift %.1f), '
                  'anisotropy %.2f -> %.2f, p %.4f'
                  % (tag, d0, dd, drift, an0, an, pv))
        except Exception:
            traceback.print_exc(limit=2)

    if not rows:
        return
    print('\n' + '=' * 84)
    print('%-13s %6s %8s %8s %7s %9s %9s %8s'
          % ('area', 'raster', 'then', 'now', 'drift', 'aniso then',
             'aniso now', 'p now'))
    for a, ang, when, d0, an0, dd, an, pv, drift, tag in rows:
        print('(%+5.1f,%+5.1f) %6.0f %8.1f %8.1f %7.1f %9.2f %9.2f %8.4f'
              % (a[0], a[1], ang, d0, dd, drift, an0, an, pv))
    dr = np.array([r[8] for r in rows])
    keep = np.array([r[6] / max(r[4], 1e-9) for r in rows])
    sig = sum(1 for r in rows if r[7] < 0.01)
    print('\n  director drift: median %.1f deg, max %.1f deg'
          % (np.median(dr), dr.max()))
    print('  anisotropy retained: median %.0f %%, range %.0f-%.0f %%'
          % (100 * np.median(keep), 100 * keep.min(), 100 * keep.max()))
    print('  still significant at p < 0.01: %d of %d' % (sig, len(rows)))
    # PITFALLS 21.31: one verdict per question. Retention of a DIRECTION and
    # significance of a STATE are different things, and ANDing them produced a
    # headline that contradicted the table above it.
    if np.median(dr) <= 10:
        print('  -> DIRECTION: holds. Median drift %.1f deg, max %.1f.'
              % (np.median(dr), dr.max()))
    else:
        print('  -> DIRECTION: does not hold. Median drift %.1f deg.'
              % np.median(dr))
    if sig == len(rows):
        print('  -> SIGNIFICANCE: all %d panels remain at p < 0.01.' % len(rows))
    else:
        print('  -> SIGNIFICANCE: %d of %d at p < 0.01. Check whether the '
              'others were significant WHEN WRITTEN before calling this decay.'
              % (sig, len(rows)))


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
        io.open(os.path.join(A.PROJ, 'retraster_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
