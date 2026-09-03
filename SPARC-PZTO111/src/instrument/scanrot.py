# -*- coding: utf-8 -*-
"""scanrot.py -- is the written pattern fixed in the SAMPLE or in the SCAN?

MEASUREMENT ONLY. No bias, no litho, no S24 cost.

WHY. M28 concluded that a template commanded to a crystallographically
forbidden direction produces a persistent readout at exactly that direction.
That conclusion rests on the lateral channel reporting a real spatial structure
on the sample. The alternative -- that some part of the contrast is fixed in the
SCAN frame, as the ~75 nm fast-axis artefact demonstrably is (PITFALLS 21.6) --
would change what the result means.

Rotating the scan separates them, and costs nothing:

    real structure on the sample : its measured angle moves WITH the rotation
    anything fixed in the scan   : its measured angle does NOT move

M10 established the sign: rotating the scan by +phi moves measured angles by
+phi. So the difference between the two measurements should be +phi for a real
feature and 0 for a scan-locked one. This script does not assume the sign; it
reports the measured difference and compares it against both predictions.

  SR_AREA="-8,0"      area to re-image
  SR_ANG="0,60"       scan angles, deg
  SR_DIR="56.5"       the direction of interest, in the 0 deg scan frame
  SR_LAM="300"        its period, nm
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
AX, AY = [float(v) for v in os.environ.get('SR_AREA', '-8,0').split(',')]
ANGS = [float(v) for v in os.environ.get('SR_ANG', '0,60').split(',')]
DIRE = float(os.environ.get('SR_DIR', '56.5'))
LAM = float(os.environ.get('SR_LAM', '300'))
STAMP = time.strftime('%y%m%d_%H%M')
SUPER = (150.0, 500.0)


def interior(S, px, h=0.55):
    n = S.shape[0]
    hp = int(round(h * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def main():
    print('=' * 78)
    print('SCAN ROTATION  %s   (measurement only)' % time.strftime('%H:%M'))
    print('=' * 78)
    print('  area (%+.1f,%+.1f), scan angles %s deg' % (AX, AY, ANGS))
    print('  feature of interest: %.1f deg / %.0f nm in the 0 deg scan frame'
          % (DIRE, LAM))
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    g('scanner_ok')(AX, AY, SIZE_UM)

    out = []
    for ang in ANGS:
        print('\n--- scan angle %.0f deg ---' % ang)
        _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                                 angle_deg=ang, xoff_um=AX, yoff_um=AY,
                                 tries=1, verbose=False)
        tag = inf['frame']
        d, h = g('ibw')(tag)
        S, _, r12 = g('signed')(d)
        px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
        Si = interior(S, px)
        dd, an, per, pv = ST.band_peak(Si, px, *SUPER, n_perm=300)
        # the fast-axis artefact, as an internal reference that MUST stay put
        fd, fa, fper, fpv = ST.band_peak(Si, px, 45.0, 90.0, n_perm=300)
        print('    %s  tracked %.0f%%, r12 %+.2f, %.2f nm/px'
              % (tag, 100 * inf['frac'], r12, px))
        print('    super band : %6.1f deg  %6.1f nm  aniso %5.2f  p %.4f'
              % (dd, per, an, pv))
        print('    45-90 band : %6.1f deg  %6.1f nm  aniso %5.2f  p %.4f'
              % (fd, fper, fa, fpv))
        out.append(dict(ang=ang, tag=tag, dir=dd, per=per, p=pv,
                        fdir=fd, fp=fpv))

    if len(out) < 2:
        return
    a0, a1 = out[0], out[1]
    dphi = a1['ang'] - a0['ang']
    dsup = (a1['dir'] - a0['dir'] + 90.0) % 180.0 - 90.0
    dfast = (a1['fdir'] - a0['fdir'] + 90.0) % 180.0 - 90.0
    print('\n' + '=' * 78)
    print('RESULT   scan rotated by %+.0f deg' % dphi)
    print('=' * 78)
    print('  written feature : measured angle moved %+6.1f deg' % dsup)
    print('  45-90 nm band   : measured angle moved %+6.1f deg' % dfast)
    print()
    print('  prediction if the feature is REAL on the sample : %+.0f deg'
          % dphi)
    print('  prediction if it is fixed in the SCAN frame     :   +0 deg')
    print()
    tol = 20.0
    if abs(abs(dsup) - abs(dphi)) < tol:
        print('  -> the written feature ROTATED WITH THE SAMPLE. It is a real')
        print('     spatial structure, and M28 stands.')
    elif abs(dsup) < tol:
        print('  -> the written feature did NOT move: it is fixed in the scan')
        print('     frame, and M28 must be withdrawn.')
    else:
        print('  -> ambiguous: moved %+.1f, neither %+.0f nor 0.' % (dsup, dphi))
    if abs(dfast) < tol:
        print('  -> the 45-90 nm band did NOT move, confirming it is the')
        print('     scan-locked artefact of PITFALLS 21.6. Good internal')
        print('     control: the two bands behave differently in the same')
        print('     frames.')
    print('\n  frames: %s' % ', '.join(o['tag'] for o in out))


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
        io.open(os.path.join(A.PROJ, 'scanrot_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
