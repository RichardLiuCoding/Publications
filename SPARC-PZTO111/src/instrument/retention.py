# -*- coding: utf-8 -*-
"""retention.py -- does the written modulation survive, or does it decay?

MEASUREMENT ONLY. No bias, no litho, no S24 cost.

THE QUESTION THIS SETTLES. M27 showed that the modulation appearing at the
template wavevector after a write is largely an IMPRINT of the alternating
bias: it follows the template's period even when that period is nothing the
film would choose, and the off-triad test put the readout on a commanded
direction the crystal does not allow.

An imprint and a domain reorganisation differ in one respect that costs
nothing to measure: **an imprinted charge or polarisation pattern relaxes, a
reorganised ferroelastic domain structure does not.** Every panel written this
morning has a matched-filter amplitude recorded within minutes of writing. Re-
imaging them hours later, at identical settings, turns that into a decay curve.

  decayed toward the corner null  -> imprint
  unchanged                       -> the film really did reorganise
  partly decayed                  -> both, and the residue is the real part

The corners of each frame carry the same measurement on film that was never
written, so drift in the readout is subtracted rather than assumed.

  RET_AREAS="0,0 4,0 0,-4"
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
PX = 512
RATE = 2.0
STAMP = time.strftime('%y%m%d_%H%M')

# area -> (commanded deg, template Lambda nm, sigma, written-at, the amplitudes
#          measured on the after-frames immediately following the write)
REF = {
    (0.0, 0.0): dict(want=16.5, lam=219.0, sigma=133, at='10:55',
                     L=150.27, V=122.28),
    (4.0, 0.0): dict(want=4.0, lam=225.0, sigma=122, at='11:15',
                     L=124.96, V=179.26),
    (0.0, -4.0): dict(want=16.5, lam=251.0, sigma=263, at='12:15',
                      L=208.94, V=202.62),
}


def load(g, tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0, r12


def interior(S, px, h=0.5):
    n = S.shape[0]
    hp = int(round(h * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def corners(S, px, size=0.62):
    n = S.shape[0]
    k = int(round(size * 1000.0 / px))
    return [S[0:k, 0:k], S[0:k, n - k:n], S[n - k:n, 0:k], S[n - k:n, n - k:n]]


def main():
    env = os.environ.get('RET_AREAS', '0,0 4,0 0,-4').split()
    areas = [tuple(float(v) for v in a.split(',')) for a in env]
    print('=' * 78)
    print('RETENTION  %s   (measurement only)' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    rows = []
    for (ax, ay) in areas:
        ref = REF.get((ax, ay))
        if ref is None:
            print('  (%+.1f,%+.1f) has no reference amplitude; skipping'
                  % (ax, ay))
            continue
        print('\n--- (%+.1f,%+.1f)  written %s at sigma %d, commanded %.1f deg,'
              ' template %.0f nm ---' % (ax, ay, ref['at'], ref['sigma'],
                                         ref['want'], ref['lam']))
        g('scanner_ok')(ax, ay, SIZE_UM)
        got = {}
        for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
            _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                     angle_deg=0.0, xoff_um=ax, yoff_um=ay,
                                     tries=1, verbose=False)
            tag = inf['frame']
            S, px, r12 = load(g, tag)
            amp, z, p, sd = ST.matched_test(interior(S, px), px, ref['want'],
                                            ref['lam'])
            cor = np.mean([ST.matched_amplitude(c, px, ref['want'], ref['lam'])
                           for c in corners(S, px)])
            got[slot] = (tag, amp, z, p, cor, r12)
            was = ref[slot]
            print('    %s %s  interior %7.2f pm (was %7.2f right after the '
                  'write, %+.0f %%)  z %+.1f  p %.4f | corners %6.2f'
                  % (mode.upper(), tag, amp, was, 100 * (amp - was) / was,
                     z, p, cor))
        rows.append(((ax, ay), ref, got))

    print('\n' + '=' * 78)
    print('DECAY')
    print('=' * 78)
    print('  %-11s %-7s %10s %10s %9s  %s'
          % ('area', 'chan', 'then (pm)', 'now (pm)', 'retained', 'reading'))
    frac = []
    for (a, ref, got) in rows:
        for slot, ch in (('L', 'LDART'), ('V', 'VDART')):
            if slot not in got:
                continue
            was, now = ref[slot], got[slot][1]
            r = now / max(was, 1e-9)
            frac.append(r)
            note = ('persists' if r > 0.7 else
                    ('partly decayed' if r > 0.3 else 'DECAYED'))
            print('  (%+5.1f,%+5.1f) %-7s %10.2f %10.2f %8.0f %%  %s'
                  % (a[0], a[1], ch, was, now, 100 * r, note))
    if frac:
        f = np.asarray(frac)
        print('\n  retained fraction: median %.0f %%, range %.0f-%.0f %%'
              % (100 * np.median(f), 100 * f.min(), 100 * f.max()))
        if np.median(f) > 0.7:
            print('  -> THE MODULATION PERSISTS. It is not a relaxing surface')
            print('     charge; something structural was written.')
        elif np.median(f) < 0.3:
            print('  -> THE MODULATION DECAYED. It was an imprint, and the')
            print('     campaign readout has been measuring it.')
        else:
            print('  -> PARTIAL DECAY. Part of the signal relaxes and part')
            print('     does not; the residue is the structural component and')
            print('     its size is the number that matters.')


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
        io.open(os.path.join(A.PROJ, 'retention_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
