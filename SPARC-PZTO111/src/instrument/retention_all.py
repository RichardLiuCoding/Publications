# -*- coding: utf-8 -*-
"""retention_all.py -- every retention pair, both estimators, one table.

Fourteen raster panels have been re-imaged between 0.4 and 4.8 h after their
writes. Each is measured twice with each estimator: the binned band peak, whose
7.5 deg quantisation is what the retention driver reports live, and the
matched filter, which resolves 0.09 deg.

The point of running both is the panel at (+12,+18), which the binned estimator
says moved 7.5 deg -- one whole bin -- and the matched filter says moved
0.40 deg. Those are the same data.

Every frame is checked against its own header offsets (PITFALLS 21.29).

MEASUREMENT-FREE.
"""
from __future__ import annotations

import io
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A
import scale_tools as ST
from fine_angle import peak_angle, interior

SUPER = (150.0, 500.0)

# label, x, y, age in hours, frame at the write, frame at re-imaging
PAIRS = [
    ('(+12,+12)', 12.0, 12.0, 4.80, 'PZTO_LDART_0048.ibw', 'PZTO_LDART_0080.ibw'),
    ('(-6,-6)', -6.0, -6.0, 4.02, 'PZTO_LDART_0050.ibw', 'PZTO_LDART_0076.ibw'),
    ('(0,-6)', 0.0, -6.0, 3.75, 'PZTO_LDART_0052.ibw', 'PZTO_LDART_0078.ibw'),
    ('(-6,0) re-aim 1', -6.0, 0.0, 2.45, 'PZTO_LDART_0057.ibw', 'PZTO_LDART_0077.ibw'),
    ('(0,+18)', 0.0, 18.0, 1.60, 'PZTO_LDART_0069.ibw', 'PZTO_LDART_0079.ibw'),
    ('(+18,-18)', 18.0, -18.0, 1.31, 'PZTO_LDART_0071.ibw', 'PZTO_LDART_0081.ibw'),
    ('(+12,+18) s343', 12.0, 18.0, 2.87, 'PZTO_LDART_0095.ibw', 'PZTO_LDART_0110.ibw'),
    ('(+6,+12) s178', 6.0, 12.0, 2.58, 'PZTO_LDART_0097.ibw', 'PZTO_LDART_0111.ibw'),
    ('(-6,-12) fast', -6.0, -12.0, 2.30, 'PZTO_LDART_0099.ibw', 'PZTO_LDART_0112.ibw'),
    ('(-12,-6) re-aim 2', -12.0, -6.0, 1.60, 'PZTO_LDART_0102.ibw', 'PZTO_LDART_0113.ibw'),
    ('(+12,+6) fast', 12.0, 6.0, 1.30, 'PZTO_LDART_0104.ibw', 'PZTO_LDART_0114.ibw'),
    ('tile A', -6.8, -18.0, 1.67, 'PZTO_LDART_0107.ibw', 'PZTO_LDART_0119.ibw'),
    ('tile B', -5.2, -18.0, 1.35, 'PZTO_LDART_0109.ibw', 'PZTO_LDART_0120.ibw'),
    ('(+6,-12) re-aim 3', 6.0, -12.0, 0.42, 'PZTO_LDART_0117.ibw', 'PZTO_LDART_0121.ibw'),
]


def measure(g, tag, wx, wy):
    d, h = g('ibw')(tag)
    gx, gy = float(h['XOffset']) * 1e6, float(h['YOffset']) * 1e6
    if abs(gx - wx) > 0.05 or abs(gy - wy) > 0.05:
        raise RuntimeError('%s is at (%+.2f,%+.2f), not (%+.2f,%+.2f)'
                           % (tag, gx, gy, wx, wy))
    S, _, _ = g('signed')(d)
    px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
    I = interior(S, px)
    dd, an, lam, pv = ST.band_peak(I, px, *SUPER, n_perm=300)
    return dd, peak_angle(I, px, dd, lam)[0], an, pv


def main():
    print('=' * 100)
    print('RETENTION, EVERY PANEL, BOTH ESTIMATORS  %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 100)
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__
    rows = []
    print('%-19s %5s %15s %15s %8s %8s %13s'
          % ('panel', 'age h', 'binned then/now', 'fine then/now',
             'd binned', 'd fine', 'aniso then/now'))
    for lab, wx, wy, age, t1, t2 in PAIRS:
        try:
            b1, f1, a1, p1 = measure(g, t1, wx, wy)
            b2, f2, a2, p2 = measure(g, t2, wx, wy)
        except Exception as e:
            print('%-19s  %s' % (lab, e))
            continue
        db = ST.angle_between(b1, b2)
        df = ST.angle_between(f1, f2)
        rows.append((lab, age, db, df, a1, a2, p2))
        print('%-19s %5.2f %7.1f /%6.1f %7.2f /%6.2f %8.1f %8.2f %6.2f /%6.2f'
              % (lab, age, b1, b2, f1, f2, db, df, a1, a2))
    if not rows:
        return
    db = np.array([r[2] for r in rows])
    df = np.array([r[3] for r in rows])
    print('\n' + '-' * 100)
    print('  %d panels, ages %.2f-%.2f h' % (len(rows),
                                             min(r[1] for r in rows),
                                             max(r[1] for r in rows)))
    print('  binned drift : median %.2f, max %.2f deg; %d of %d at or below '
          'one bin (7.5 deg)'
          % (np.median(db), db.max(), int((db <= 7.6).sum()), len(db)))
    print('  fine drift   : median %.2f, max %.2f deg'
          % (np.median(df), df.max()))
    print('  panels where the two estimators disagree by more than 3 deg:')
    for r in rows:
        if abs(r[2] - r[3]) > 3.0:
            print('    %-19s binned %.1f, fine %.2f' % (r[0], r[2], r[3]))
    sig = sum(1 for r in rows if r[6] < 0.01)
    print('  still significant at p < 0.01: %d of %d' % (sig, len(rows)))
    io.open(os.path.join(A.PROJ, 'retall_%s.txt'
                         % time.strftime('%y%m%d_%H%M')), 'w',
            encoding='utf-8').write('\n'.join(
                '%s\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f' % (r[0], r[1], r[2], r[3],
                                                      r[4], r[5])
                for r in rows))


if __name__ == '__main__':
    main()
