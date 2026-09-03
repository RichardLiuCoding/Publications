# -*- coding: utf-8 -*-
"""tile_boundary_read.py -- re-image the join between the two written tiles.

MEASUREMENT ONLY. No bias, no litho, no S24 cost.

WHY THIS EXISTS. tile_boundary.py's final readout reported a frame it did not
take. A second process (the retention run) had begun driving the instrument
while the tile script was still finishing, and the frame the tile script read
back -- PZTO_LDART_0110 -- is at (+12,+18), the retention run's first area, not
at (-6,-18). Its two "tile windows" therefore both sampled an area written at
41 deg that sits on member 18, which is exactly why they came out 0.50 deg
apart. Nothing about the tiles was measured.

Every frame is checked against its own header offsets here, and the script
refuses to analyse a frame that is not where it asked to be.

WHAT IS MEASURED. Tile A is an axis-aligned 1.6 um square centred 0.8 um left
of this frame's centre, so a 1.2 um window centred 0.62 um left lies wholly
inside it and clear of the join. That window answers the question the tiling
experiment is for: does tile A still hold its own variant after tile B was
written 1.6 um away?

Tile B cannot be read from this frame. Its square is built ROTATED to the
commanded 60 deg, and no axis-aligned window inside this frame lies wholly
within it. Tile B's own centred frame (PZTO_LDART_0109) is used for that, in
tile_reread.py.
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

X, Y = -6.0, -18.0
SIZE_UM, PX, RATE = 2.5, 512, 2.0
WIN_UM, WIN_X = 1.2, 0.62
SUPER = (150.0, 500.0)
# tile A's own after-frame, for the before/after comparison
A_AFTER = 'PZTO_LDART_0107.ibw'
STAMP = time.strftime('%y%m%d_%H%M')


def window(S, px, cx_um):
    n = S.shape[0]
    h = int(round(WIN_UM * 500.0 / px))
    cx = int(round(n / 2.0 + cx_um * 1000.0 / px))
    c = n // 2
    if cx - h < 0 or cx + h > n:
        raise ValueError('window outside the frame')
    return S[c - h:c + h, cx - h:cx + h]


def check_where(h, want_x, want_y, tag):
    gx = float(h['XOffset']) * 1e6
    gy = float(h['YOffset']) * 1e6
    print('    %s header offset (%+.2f,%+.2f) um' % (tag, gx, gy))
    if abs(gx - want_x) > 0.05 or abs(gy - want_y) > 0.05:
        raise RuntimeError('frame %s is at (%+.2f,%+.2f), not (%+.2f,%+.2f) '
                           '-- refusing to analyse it'
                           % (tag, gx, gy, want_x, want_y))


def main():
    print('=' * 80)
    print('TILE JOIN, RE-IMAGED  %s   (measurement only)'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 80)
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    g('scanner_ok')(X, Y, SIZE_UM)
    _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                             angle_deg=0.0, xoff_um=X, yoff_um=Y, tries=1,
                             verbose=False)
    tag = inf['frame']
    d, h = g('ibw')(tag)
    check_where(h, X, Y, tag)
    S, _, _ = g('signed')(d)
    px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0

    W = window(S, px, -WIN_X)
    dd, an, lam, pv = ST.band_peak(W, px, *SUPER, n_perm=400)
    ok, nper, msg = ST.window_ok(lam, WIN_UM, label='tile A in the join frame')
    print('\n  TILE A, read in this frame, %.1f um window centred %.2f um '
          'left of centre' % (WIN_UM, WIN_X))
    print('    %s' % msg)
    print('    director %.1f deg, Lambda %.0f nm, anisotropy %.2f, p %.4f'
          % (dd, lam, an, pv))

    d2, h2 = g('ibw')(A_AFTER)
    check_where(h2, -6.8, -18.0, A_AFTER)
    S2, _, _ = g('signed')(d2)
    px2 = float(h2['ScanSize']) * 1e6 / S2.shape[0] * 1000.0
    n2 = S2.shape[0]
    hp = int(round(0.60 * 1000.0 / px2))
    c2 = n2 // 2
    I2 = S2[c2 - hp:c2 + hp, c2 - hp:c2 + hp]
    d0, a0, l0, p0 = ST.band_peak(I2, px2, *SUPER, n_perm=400)
    print('\n  TILE A, in its own frame taken BEFORE tile B was written')
    print('    director %.1f deg, Lambda %.0f nm, anisotropy %.2f, p %.4f'
          % (d0, l0, a0, p0))

    print('\n' + '-' * 80)
    drift = ST.angle_between(dd, d0)
    print('  tile A director before tile B: %.1f deg' % d0)
    print('  tile A director after  tile B: %.1f deg   -> change %.1f deg'
          % (dd, drift))
    if pv < 0.01 and drift <= 7.5:
        print('  -> TILE A IS UNDISTURBED. Writing a neighbouring tile at a')
        print('     different commanded axis 1.6 um away does not overwrite')
        print('     it. Tiles are independent, which is what patterning needs.')
    elif pv >= 0.01:
        print('  -> tile A no longer carries a significant direction.')
    else:
        print('  -> tile A moved by %.1f deg; the tiles are NOT independent.'
              % drift)
    print('\n  frame for the figure: %s' % tag)


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
        io.open(os.path.join(A.PROJ, 'tilejoin_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
