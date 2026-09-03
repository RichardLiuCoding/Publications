# -*- coding: utf-8 -*-
"""triad_all.py -- the single-triad test with every raster write in the campaign.

Section 3.8 established one film-wide triad from six landings. The third
referee report's first point is that six is thin for a claim about the film,
and that round 3's four new areas should be folded in: if they fall in the same
arc the statistic becomes overwhelming, and if they do not the paper must say
the triad drifts.

Each landing is measured with the validated matched filter (M36) on the
after-frame of its own write. Panels re-imaged in the retention run are
averaged over their two independent images; the round 3 panels have one image
each.

Also recomputes, with the full set:
  * the circular range modulo 60 and its p-value
  * whether the per-area as-grown fit predicts the landing
  * whether each write went to the member NEAREST its commanded axis
  * the two re-aim pairs, where the reference cancels

MEASUREMENT-FREE.
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A
import scale_tools as ST
from fine_angle import peak_angle, interior, wrap180, wrap60

SUPER = (150.0, 500.0)

# name, phi0 from the pre-write screen, commanded angle, frames to average
RUNS = [
    ('(+12,+12) 46', 16.5, 46.0, ['PZTO_LDART_0048.ibw', 'PZTO_LDART_0080.ibw']),
    ('(-6,-6) 0', 24.0, 0.0, ['PZTO_LDART_0050.ibw', 'PZTO_LDART_0076.ibw']),
    ('(0,-6) 120', 19.0, 120.0, ['PZTO_LDART_0052.ibw', 'PZTO_LDART_0078.ibw']),
    ('(0,+18) 41', 16.5, 41.0, ['PZTO_LDART_0069.ibw', 'PZTO_LDART_0079.ibw']),
    ('(+18,-18) 41', 16.5, 41.0, ['PZTO_LDART_0071.ibw', 'PZTO_LDART_0081.ibw']),
    ('(-6,0) rw1b 60', 24.0, 60.0, ['PZTO_LDART_0057.ibw', 'PZTO_LDART_0077.ibw']),
    # round 3
    ('(+12,+18) 41 s343', 14.0, 41.0,
     ['PZTO_LDART_0095.ibw', 'PZTO_LDART_0110.ibw']),
    ('(+6,+12) 41 s178', 16.5, 41.0,
     ['PZTO_LDART_0097.ibw', 'PZTO_LDART_0111.ibw']),
    ('(-6,-12) 41 s172 fast', 9.0, 41.0,
     ['PZTO_LDART_0099.ibw', 'PZTO_LDART_0112.ibw']),
    ('(-12,-6) rw2a 0', 19.0, 0.0, ['PZTO_LDART_0101.ibw']),
    ('(-12,-6) rw2b 120', 19.0, 120.0,
     ['PZTO_LDART_0102.ibw', 'PZTO_LDART_0113.ibw']),
    # speed replicate: same triad and command as the sigma 178 write, matched
    # dose, twice the speed. Run because the first speed test landed on an
    # area where 41 deg is nearly equidistant between two members.
    ('(+12,+6) 41 s172 fast', 16.5, 41.0,
     ['PZTO_LDART_0104.ibw', 'PZTO_LDART_0114.ibw']),
]
# the two re-aim pairs: (step1 index, step2 index)
PAIRS = [(5, None), (9, 10)]


def sep(a, b):
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def circ_range(v, C=60.0):
    v = np.sort(np.asarray(v, float) % C)
    g = np.diff(v)
    wrap = v[0] + C - v[-1]
    return C - max(g.max() if g.size else 0.0, wrap)


def main():
    print('=' * 92)
    print('SINGLE TRIAD, ALL RASTER WRITES  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 92)
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__

    rows = []
    for name, phi0, cmd, tags in RUNS:
        pk = []
        for t in tags:
            try:
                d, h = g('ibw')(t)
                # PITFALLS 21.29: a frame is only trustworthy if its own
                # header says where it was taken. Areas are named in the
                # label, so check the header against it.
                import re as _re
                m = _re.match(r'\(([-+]?[\d.]+),([-+]?[\d.]+)\)', name)
                if m:
                    wx, wy = float(m.group(1)), float(m.group(2))
                    gx = float(h['XOffset']) * 1e6
                    gy = float(h['YOffset']) * 1e6
                    if abs(gx - wx) > 0.05 or abs(gy - wy) > 0.05:
                        raise RuntimeError(
                            '%s is at (%+.2f,%+.2f), not %s' % (t, gx, gy, name))
                S, _, _ = g('signed')(d)
                px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
                I = interior(S, px)
                d0, an, lam, pv = ST.band_peak(I, px, *SUPER, n_perm=200)
                pk.append((peak_angle(I, px, d0, lam)[0], an, pv, d0))
            except Exception:
                traceback.print_exc(limit=1)
        if not pk:
            continue
        land = float(np.mean([p[0] for p in pk]))
        rows.append(dict(name=name, phi0=phi0, cmd=cmd, land=land,
                         an=pk[-1][1], pv=pk[-1][2], binned=pk[-1][3],
                         n=len(pk)))
        print('  %-24s cmd %5.1f  landing %7.2f  (binned %5.1f, aniso %6.2f,'
              ' p %.4f)' % (name, cmd, land, pk[-1][3], pk[-1][1], pk[-1][2]))

    lm = np.array([r['land'] % 60.0 for r in rows])
    n = len(rows)
    ang = np.radians(lm * 6.0)
    mu = (np.degrees(np.arctan2(np.sin(ang).mean(),
                                np.cos(ang).mean())) / 6.0) % 60.0
    L = circ_range(lm)
    p = n * (min(L, 60.0) / 60.0) ** (n - 1)
    print('\n' + '-' * 92)
    print('  %d landings, modulo 60 deg:' % n)
    print('    %s' % ', '.join('%.2f' % x for x in np.sort(lm)))
    print('    circular range %.2f deg about a common %.2f deg' % (L, mu))
    print('    P(%d uniform draws inside a %.2f deg arc) = %.2e' % (n, L, p))

    fit = np.array([r['phi0'] % 60.0 for r in rows])
    r = float(np.corrcoef(fit, lm)[0, 1])
    rng = np.random.default_rng(0)
    null = np.array([np.corrcoef(fit, rng.permutation(lm))[0, 1]
                     for _ in range(100000)])
    pp = float(np.mean(np.abs(null) >= abs(r)))
    print('\n  does the pre-write fit predict the landing?')
    print('    r = %+.3f, permutation p = %.3f' % (r, pp))
    print('    r.m.s. of landings about a single common value : %.2f deg'
          % np.sqrt(np.mean(wrapv(lm - mu) ** 2)))
    print('    r.m.s. of landings about their own fits        : %.2f deg'
          % np.sqrt(np.mean(wrapv(lm - fit) ** 2)))

    members = [(mu + 60.0 * k) % 180.0 for k in range(3)]
    print('\n  members of the fitted triad: %s'
          % ', '.join('%.2f' % m for m in members))
    print('  %-24s %8s %9s %9s %8s %s'
          % ('run', 'command', 'landing', 'went to', 'nearest', 'hit'))
    hit = 0
    for rr in rows:
        on = min(members, key=lambda m: sep(rr['land'], m))
        near = min(members, key=lambda m: sep(rr['cmd'], m))
        d1 = sorted(sep(rr['cmd'], m) for m in members)
        ok = abs(on - near) < 1e-6
        hit += ok
        print('  %-24s %8.1f %9.2f %9.2f %8.2f %5s  (margin %.1f deg)'
              % (rr['name'], rr['cmd'], rr['land'], on, near,
                 'yes' if ok else 'NO', d1[1] - d1[0]))
    print('\n  %d of %d went to the member nearest the command; '
          'random choice p = %.2e' % (hit, n, (1.0 / 3.0) ** n))

    print('\n  restricted to runs where "nearest" is unambiguous '
          '(margin >= 8 deg):')
    hh = tt = 0
    for rr in rows:
        d1 = sorted(sep(rr['cmd'], m) for m in members)
        if d1[1] - d1[0] < 8.0:
            print('    EXCLUDED %-22s margin %.1f deg'
                  % (rr['name'], d1[1] - d1[0]))
            continue
        on = min(members, key=lambda m: sep(rr['land'], m))
        near = min(members, key=lambda m: sep(rr['cmd'], m))
        tt += 1
        hh += abs(on - near) < 1e-6
    print('    %d of %d; random choice p = %.2e'
          % (hh, tt, (1.0 / 3.0) ** tt if tt else float('nan')))

    print('\n  re-aim pairs (same area, same session: the reference cancels)')
    for a, b in PAIRS:
        if b is None:
            continue
        s1, s2 = rows[a]['land'], rows[b]['land']
        print('    %-22s step 1 %7.2f, step 2 %7.2f -> separation %6.2f '
              '(%+.2f from 60)'
              % (rows[a]['name'], s1, s2, sep(s1, s2), sep(s1, s2) - 60.0))
    print('    first pair (from S8.4)  step 1   17.98, step 2   75.15 -> '
          'separation  57.17 (-2.83 from 60)')


def wrapv(v):
    return (np.asarray(v, float) + 30.0) % 60.0 - 30.0


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
        io.open(os.path.join(A.PROJ, 'triadall_%s.txt'
                             % time.strftime('%y%m%d_%H%M')), 'w',
                encoding='utf-8').write(buf.getvalue())
