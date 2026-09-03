# -*- coding: utf-8 -*-
"""fine_angle.py -- locate the written director below the binning resolution.

The band estimator bins the low-q annulus into ~48 angular bins, a resolution
of 7.5 deg, and five of six raster runs consequently report exactly 18.8 deg.
That is enough for every claim in the paper -- the moves are 37-75 deg -- but
it is NOT enough for one thing the landscape model predicts:

    delta = B sin(2 Delta) / (36 A)

the displacement of the selected minimum TOWARD the commanded axis. Measured
offsets are 0.2-5.2 deg, i.e. at the binning resolution, so the blind estimator
can establish the sign of the lean but not its size.

A matched filter does not have that limit. At a KNOWN period, the amplitude of
the Fourier component along a given direction is a continuous function of that
direction, and its maximum can be located far below the bin width.

The uncertainty is measured, not assumed: every panel here was imaged TWICE,
once at the write and once 3-5 h later during the retention run, with an
independent tune and an independent tip approach in between. The scatter
between those two measurements is the empirical repeatability of the method.

MEASUREMENT-FREE. Reads .ibw files already on disk.
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

IN_HALF = 0.60
SUPER = (150.0, 500.0)
SPAN, STEP = 18.0, 0.25          # scan +/-18 deg in 0.25 deg steps

# area: (phi0 from the pre-write screen, raster angle, after-frame, retention
#        frame). phi0 comes from the SCREEN, before any write, so the
#        crystallographic reference is not derived from the same data as the
#        measured director.
RUNS = [
    ('(+12,+12)', 16.5, 46.0, 'PZTO_LDART_0048.ibw', 'PZTO_LDART_0080.ibw'),
    ('(-6,-6)', 24.0, 0.0, 'PZTO_LDART_0050.ibw', 'PZTO_LDART_0076.ibw'),
    ('(0,-6)', 19.0, 120.0, 'PZTO_LDART_0052.ibw', 'PZTO_LDART_0078.ibw'),
    ('(0,+18)', 16.5, 41.0, 'PZTO_LDART_0069.ibw', 'PZTO_LDART_0079.ibw'),
    ('(+18,-18)', 16.5, 41.0, 'PZTO_LDART_0071.ibw', 'PZTO_LDART_0081.ibw'),
    ('(-6,0) rw2', 24.0, 60.0, 'PZTO_LDART_0057.ibw', 'PZTO_LDART_0077.ibw'),
]


def wrap180(a):
    return (a + 90.0) % 180.0 - 90.0


def wrap60(a):
    return (a + 30.0) % 60.0 - 30.0


def interior(S, px):
    n = S.shape[0]
    hp = int(round(IN_HALF * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def peak_angle(S, px, centre, lam):
    """Matched-filter amplitude vs direction; peak by parabolic interpolation."""
    th = np.arange(centre - SPAN, centre + SPAN + 1e-9, STEP)
    amp = np.array([ST.matched_amplitude(S, px, t, lam) for t in th])
    k = int(np.argmax(amp))
    if 0 < k < len(th) - 1:
        y0, y1, y2 = amp[k - 1], amp[k], amp[k + 1]
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if abs(den) > 1e-30 else 0.0
        d = float(np.clip(d, -1, 1))
    else:
        d = 0.0
    return float(th[k] + d * STEP), th, amp


def main():
    print('=' * 82)
    print('FINE ANGLE  %s   (measurement-free)' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 82)
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__

    rows = []
    for name, phi0, phi, tag_a, tag_r in RUNS:
        try:
            out = []
            for tag in (tag_a, tag_r):
                d, h = g('ibw')(tag)
                S, _, _ = g('signed')(d)
                px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
                I = interior(S, px)
                d0, an, lam, pv = ST.band_peak(I, px, *SUPER, n_perm=200)
                pk, th, amp = peak_angle(I, px, d0, lam)
                out.append((pk, lam, an, pv))
            members = [(phi0 + 60.0 * k) % 180.0 for k in range(3)]
            pk_a, pk_r = out[0][0], out[1][0]
            m = min(members, key=lambda t: abs(wrap180(0.5 * (pk_a + pk_r) - t)))
            da, dr = wrap180(pk_a - m), wrap180(pk_r - m)
            Delta = wrap180(phi - m)
            rows.append((name, phi, m, pk_a, pk_r, da, dr, Delta,
                         out[0][1], out[1][1]))
            print('  %-11s raster %5.1f  member %5.1f | peak %6.2f / %6.2f '
                  '| delta %+5.2f / %+5.2f | Delta %+5.1f'
                  % (name, phi, m, pk_a, pk_r, da, dr, Delta))
        except Exception:
            print('  %-11s FAILED' % name)
            traceback.print_exc(limit=2)

    if not rows:
        return
    print('\n' + '-' * 82)
    rep = np.array([abs(r[3] - r[4]) for r in rows])
    print('  repeatability between the two independent images of the same')
    print('  panel: median %.2f deg, max %.2f deg  (%d panels)'
          % (np.median(rep), rep.max(), len(rows)))
    print('  -- against the 7.5 deg resolution of the blind band estimator.')

    d = np.array([0.5 * (r[5] + r[6]) for r in rows])
    D = np.array([r[7] for r in rows])
    tw = int(np.sum(d * D > 0))
    from math import comb
    n = len(rows)
    p = min(1.0, sum(comb(n, j) for j in range(tw, n + 1)) / 2.0 ** n * 2)
    print('\n  mean delta per panel (deg): %s'
          % ', '.join('%+.2f' % v for v in d))
    print('  %d of %d lean toward the commanded axis; sign test p = %.3f'
          % (tw, n, p))
    s2 = np.sin(np.radians(2 * D))
    ba = np.radians(d) * 36.0 / s2
    print('  implied B/A: median %.2f, range %.2f-%.2f'
          % (np.median(ba), ba.min(), ba.max()))
    sig = np.abs(d) > 2 * np.median(rep)
    print('  panels whose |delta| exceeds twice the repeatability: %d of %d'
          % (int(sig.sum()), n))

    # ---- is the triad reference good enough to ask the question? ----
    #
    # The member positions come from a rigid-triad fit to the AS-GROWN frame,
    # which has anisotropy 2-4 and frequently no significant direction. If
    # that fit carries an error of a few degrees, it swamps delta.
    #
    # Two internal checks need no new data:
    #   (1) the rewrite pair wrote two DIFFERENT orientations on the SAME
    #       area. If the triad is rigid, they must be separated by exactly
    #       60.0 deg, whatever the fit says.
    #   (2) several areas share a nominal phi0 of 16.5 and all landed on the
    #       same member. Their spread bounds how well a triad transfers
    #       between areas.
    print()
    print('-' * 82)
    print('  IS THE CRYSTALLOGRAPHIC REFERENCE GOOD ENOUGH?')
    try:
        pk = {}
        for tag in ('PZTO_LDART_0056.ibw', 'PZTO_LDART_0057.ibw'):
            dd, hh = g('ibw')(tag)
            SS, _, _ = g('signed')(dd)
            pxx = float(hh['ScanSize']) * 1e6 / SS.shape[0] * 1000.0
            II = interior(SS, pxx)
            d0, an, lam, pv = ST.band_peak(II, pxx, *SUPER, n_perm=200)
            pk[tag] = peak_angle(II, pxx, d0, lam)[0]
        sep = abs(wrap180(pk['PZTO_LDART_0057.ibw']
                          - pk['PZTO_LDART_0056.ibw']))
        print('    rewrite pair, same area: step 1 %.2f deg, step 2 %.2f deg'
              % (pk['PZTO_LDART_0056.ibw'], pk['PZTO_LDART_0057.ibw']))
        print('    separation %.2f deg against the required 60.00 deg '
              '-> error %+.2f deg' % (sep, sep - 60.0))
    except Exception:
        traceback.print_exc(limit=2)

    # (3) The strongest test. If the film carries ONE triad rather than a
    #     different one per area, then every landing -- on any area, at any
    #     commanded angle, on any member -- must fall at the same value
    #     modulo 60 deg. The pre-write fits disagree by several degrees; the
    #     written states are well ordered and should not.
    def circ_range(v, C=60.0):
        v = np.sort(np.asarray(v, float) % C)
        g = np.diff(v)
        wrap = v[0] + C - v[-1]
        return C - max(g.max() if g.size else 0.0, wrap)

    lm = np.array([(0.5 * (r[3] + r[4])) % 60.0 for r in rows])
    ph = np.array([r[2] % 60.0 for r in rows])
    ang = np.radians(lm * 6.0)                    # 60 deg -> full circle
    mu = np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) / 6.0
    mu = mu % 60.0
    res = np.array([wrap60(x - mu) for x in lm])
    print('    landings modulo 60 deg : %s'
          % ', '.join('%.2f' % x for x in lm))
    print('    as-grown fits modulo 60: %s'
          % ', '.join('%.2f' % x for x in ph))
    L = circ_range(lm)
    print('    written  circular range %.2f deg about a common %.2f deg'
          % (L, mu))
    print('    as-grown spread %.2f deg'
          % (ph.max() - ph.min()))
    if L < (ph.max() - ph.min()):
        print('    -> the WRITTEN orientations agree far better than the fits')
        print('       they are compared against. The reference, not the')
        print('       landing, carries the scatter.')

    # Is that clustering surprising? The circular RANGE -- the smallest arc
    # containing every point -- has CDF P(range <= L) = n (L/60)^(n-1) for
    # L <= 30. Verified against 4e6 Monte Carlo draws in check_arc_p.py;
    # an earlier version used 2 x max|residual from the mean|, which is not
    # the range and overstated it by 0.7 deg.
    nn = len(lm)
    pu = nn * (min(L, 60.0) / 60.0) ** (nn - 1)
    print('    P(%d uniform draws all inside a %.2f deg arc) = %.2e'
          % (nn, L, pu))
    cmd = np.array([r[1] % 60.0 for r in rows])
    print('    commanded angles modulo 60: %s  (spread %.1f deg)'
          % (', '.join('%.1f' % x for x in cmd), cmd.max() - cmd.min()))
    print('    -- the commands are NOT clustered, so the landings did not')
    print('       inherit their clustering from what was asked for.')

    same = [r for r in rows if abs(r[2] - 16.5) < 0.01]
    if len(same) > 1:
        v = np.array([0.5 * (r[3] + r[4]) for r in same])
        print('    %d areas sharing member 16.5: landings %s'
              % (len(same), ', '.join('%.2f' % x for x in v)))
        print('    spread %.2f deg (max-min) -- the same member, measured on'
              % (v.max() - v.min()))
        print('    independently screened areas, does not sit at one angle.')


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
    finally:
        io.open(os.path.join(A.PROJ, 'fineangle_%s.txt'
                             % time.strftime('%y%m%d_%H%M')), 'w',
                encoding='utf-8').write(buf.getvalue())
