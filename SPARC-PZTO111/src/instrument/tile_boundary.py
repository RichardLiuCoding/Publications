# -*- coding: utf-8 -*-
"""tile_boundary.py -- do two abutting raster squares hold different variants?

Section 3 writes single 1.6 um squares. Section 6 patterns with the point-pulse
lattice, whose mechanism is unresolved. Nothing in the paper shows the
selection rule COMPOSING: that two regions written at different commanded axes
sit side by side, each on its own member, with a boundary between them. That is
the whole of large-area patterning, and section 8 lists it as the main gap.

GEOMETRY. Two 1.6 um squares are written in adjacent scan fields, centred at
X-0.8 and X+0.8, so together they tile x in [X-1.6, X+1.6] with a shared edge
at X. A 2.5 um readout frame centred at X then contains 1.25 um of each,
boundary down the middle.

    |<--------- square A, 1.6 um --------->|<--------- square B --------->|
                        |<====== readout frame, 2.5 um ======>|
                                           ^ boundary

READOUT. Two 1.2 um windows centred at x = -0.62 and +0.62 um, each wholly
inside its own square and clear of the boundary. A 1.2 um window holds 4
periods if Lambda <= 300 nm; the driver refuses otherwise (4-Lambda rule,
scale_tools.window_ok).

WHAT WOULD FALSIFY IT. If the two windows return the same director, the second
write overwrote the first or neither took. If they return directions separated
by something other than a triad spacing, the rule does not compose. If they
return two different members ~60 deg apart, it does.

  TB_X, TB_Y     area centre, um
  TB_ANG_A/B     commanded angles (default 0 and 60)
  TB_PITCH       line pitch um (default 0.06 -> sigma 343)
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
import scale_tools as ST

X = float(os.environ.get('TB_X', '0'))
Y = float(os.environ.get('TB_Y', '0'))
ANG_A = float(os.environ.get('TB_ANG_A', '0'))
ANG_B = float(os.environ.get('TB_ANG_B', '60'))
PITCH = os.environ.get('TB_PITCH', '0.06')
SPEED = os.environ.get('TB_SPEED', '0.5')

SIZE_UM, PX, RATE = 2.5, 512, 2.0
OFFSET = 0.8               # half a square: square centres sit at X -/+ 0.8
WIN_UM = 1.2               # readout window in each tile
WIN_X = 0.62               # window centres, um from the boundary
#
# Geometry check, because getting this wrong is how PITFALLS 20.8 happened:
# each window is 1.2 um wide centred 0.62 um from the frame centre, so it
# spans 0.02 to 1.22 um from the centre. The 2.5 um readout frame reaches
# 1.25 um, so the window fits with 0.03 um to spare; and square A spans
# -1.6 to 0.0 um, so the window at -0.62 lies wholly inside it. The window
# also excludes the boundary itself, starting 0.02 um away from it.
#
# A 1.0 um window would need Lambda <= 250 nm and no screened area is that
# fine; 1.2 um needs Lambda <= 300 nm, which several are.
SUPER = (150.0, 500.0)
LOGDIR = os.environ.get('TEMP', '/tmp')
STAMP = time.strftime('%y%m%d_%H%M')


def window(S, px, cx_um, cy_um=0.0):
    """Square window of WIN_UM centred cx_um from the frame centre."""
    n = S.shape[0]
    h = int(round(WIN_UM * 500.0 / px))          # half-width in pixels
    cx = int(round(n / 2.0 + cx_um * 1000.0 / px))
    cy = int(round(n / 2.0 + cy_um * 1000.0 / px))
    if cx - h < 0 or cx + h > n or cy - h < 0 or cy + h > n:
        raise ValueError('window falls outside the frame')
    return S[cy - h:cy + h, cx - h:cx + h]


def write_square(cx, cy, ang, label):
    env = dict(os.environ)
    env.update(B3_MODE='dc', B3_ANG='%g' % ang, B3_X='%g' % cx,
               B3_Y='%g' % cy, B3_PITCH=PITCH, B3_SPEED=SPEED,
               B3_LABEL=label, B3_BEFORE_L='', B3_BEFORE_V='',
               B3_FORCE='1', PYTHONIOENCODING='utf-8')
    log = os.path.join(LOGDIR, 'tile_%s.log' % label)
    print('  writing %s: raster %.0f deg at (%+.2f,%+.2f)'
          % (label, ang, cx, cy))
    if subprocess.call([sys.executable, '-u', 'instrument_free.py'],
                       cwd=HERE) != 0:
        raise RuntimeError('instrument busy')
    t0 = time.time()
    with io.open(log, 'w', encoding='utf-8') as fh:
        rc = subprocess.call([sys.executable, '-u', 'block3_raster.py'],
                             cwd=HERE, env=env, stdout=fh,
                             stderr=subprocess.STDOUT)
    txt = io.open(log, encoding='utf-8', errors='replace').read()
    key = [L.strip() for L in txt.split('\n') if L.strip().startswith('->')]
    print('    rc=%d in %.1f min | %s'
          % (rc, (time.time() - t0) / 60.0, key[-1][:90] if key else ''))
    return rc


def main():
    print('=' * 80)
    print('TILE BOUNDARY  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 80)
    print('  area (%+.1f,%+.1f); squares at %+.1f and %+.1f; angles %.0f / %.0f'
          % (X, Y, X - OFFSET, X + OFFSET, ANG_A, ANG_B))
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    # Lambda must allow a 1.0 um readout window: 4 periods -> 250 nm.
    g('scanner_ok')(X, Y, SIZE_UM)
    _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                             angle_deg=0.0, xoff_um=X, yoff_um=Y, tries=1,
                             verbose=False)
    d, h = g('ibw')(inf['frame'])
    S, _, _ = g('signed')(d)
    px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
    _dd, _an, lam, _pv = ST.band_peak(S, px, *SUPER, n_perm=200)
    print('  before frame %s, Lambda %.0f nm' % (inf['frame'], lam))
    ok, nper, msg = ST.window_ok(lam, WIN_UM, label='tile readout')
    print('  4-Lambda gate: %s' % msg)
    if not ok:
        print('  REFUSED: Lambda %.0f nm gives only %.2f periods in a %.1f um '
              'window.' % (lam, nper, WIN_UM))
        return

    for cx, ang, lab in ((X - OFFSET, ANG_A, 'tileA'),
                         (X + OFFSET, ANG_B, 'tileB')):
        if write_square(cx, Y, ang, lab) != 0:
            print('  write failed; stopping.')
            return

    print('\n  reading the boundary frame at (%+.1f,%+.1f)' % (X, Y))
    _c, inf2 = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                              angle_deg=0.0, xoff_um=X, yoff_um=Y, tries=1,
                              verbose=False)
    d2, h2 = g('ibw')(inf2['frame'])
    S2, _, _ = g('signed')(d2)
    px2 = float(h2['ScanSize']) * 1e6 / S2.shape[0] * 1000.0
    print('  after frame %s' % inf2['frame'])

    # Both squares cover the whole readout frame, so there is no unwritten
    # region left in it. The control is therefore the SAME two windows in the
    # before-frame, measured identically.
    from fine_angle import peak_angle
    out = []
    for side, cx in (('A (%.0f deg)' % ANG_A, -WIN_X),
                     ('B (%.0f deg)' % ANG_B, +WIN_X)):
        Wb = window(S, px, cx)
        db, ab, pb_, pvb = ST.band_peak(Wb, px, *SUPER, n_perm=400)
        W = window(S2, px2, cx)
        dd, an, per, pv = ST.band_peak(W, px2, *SUPER, n_perm=400)
        try:
            fine = peak_angle(W, px2, dd, per)[0]
        except Exception:
            fine = float('nan')
        out.append((side, dd, an, per, pv, fine))
        print('    %-14s before %6.1f (aniso %5.2f, p %.4f)'
              % (side, db, ab, pvb))
        print('    %-14s after  %6.1f deg (fine %6.2f)  aniso %6.2f  '
              'Lambda %3.0f  p %.4f' % ('', dd, fine, an, per, pv))

    if len(out) == 2:
        f0, f1 = out[0][5], out[1][5]
        if np.isfinite(f0) and np.isfinite(f1):
            print()
            print('  matched-filter landings: %.2f and %.2f deg -> '
                  'separation %.2f' % (f0, f1, ST.angle_between(f0, f1)))
            for lab, f in (('A', f0), ('B', f1)):
                mem = min((18.32, 78.32, 138.32),
                          key=lambda m: ST.angle_between(f, m))
                print('    tile %s lands %.2f deg from the film-wide member '
                      'at %.2f' % (lab, ST.angle_between(f, mem), mem))
        sep = ST.angle_between(out[0][1], out[1][1])
        print('\n  separation between the two tiles: %.1f deg' % sep)
        cmd = ST.angle_between(ANG_A, ANG_B)
        print('  commanded separation: %.1f deg' % cmd)
        if min(out[0][4], out[1][4]) > 0.01:
            print('  -> one or both tiles are not significant; inconclusive.')
        elif abs(sep - 60.0) < 15.0:
            print('  -> TWO DIFFERENT MEMBERS SIDE BY SIDE. The rule composes:')
            print('     abutted squares hold distinct variants.')
        elif sep < 15.0:
            print('  -> the two tiles hold the SAME direction. Either the')
            print('     second write reached across the boundary, or both')
            print('     landed on the same member. Check the commanded angles')
            print('     against the triad before concluding anything.')
        else:
            print('  -> separation %.1f deg matches neither 0 nor 60.' % sep)


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
        io.open(os.path.join(A.PROJ, 'tile_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
