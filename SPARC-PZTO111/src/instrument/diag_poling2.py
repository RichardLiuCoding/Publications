# -*- coding: utf-8 -*-
"""diag_poling.py -- does the tip deliver bias to the sample at all?

WHY THIS EXISTS
---------------
Two IT12 iterations on 28 Aug wrote 512-site lattices at 10 V and ~15 V.s per
site -- roughly a third of the sites at -10 V -- and both came back VOID. The
first was explained by a collapsed readout (M12) and the second was not: its
after-frames were the STABLEST part of the iteration (after-vs-after floor
0.145, 0 % flips) and the panels still moved no more than the untouched tiles
did (excess 0.008 and 0.017).

The decisive observation is out-of-plane. Both iterations ended with:

    VDART: up 93.7-96.0 %,  ONE CLASS ONLY,  minority in patches >=25 px: 0 %

A -10 V pulse at 15 V.s on a ferroelectric film should leave an unmistakable
out-of-plane domain. Two areas, two writes, zero switched patches anywhere in
either frame. That is hard to explain with dose or readout and easy to explain
with an open electrical path -- a fresh probe was installed today.

WHAT THIS DOES
--------------
The cheapest experiment that separates "the film resists the in-plane rewrite"
from "no bias is reaching the sample":

  1. VDART image of a fresh 5 um area                       (the BEFORE state)
  2. two solid poled squares side by side, +10 V and -10 V  (~2 min of writing)
  3. VDART image of the same area                           (the AFTER state)

Two polarities because the film reads 94-96 % "up": whatever the starting state,
one of the two squares is writing AGAINST it and must switch if bias arrives.
Writing both also keeps the net injected charge near zero.

HOW TO READ IT
--------------
  A square appears in VDART phase   -> the tip writes. The in-plane VOIDs are
                                       then real physics about the IP director,
                                       and the dose question is open again.
  No square, both polarities        -> no bias is reaching the sample. Every
                                       void tonight has one cause, and it is
                                       not something to fix in software. Stop
                                       writing and tell the operator.

This is a DIAGNOSTIC, not an iteration: it does not touch campaign_state.json,
does not consume the iteration counter, and its area is deliberately one that
the pathway experiments would not want anyway.

Per-site dose is ~1-2 V.s, well under C21's 40 V.s, because a raster spreads
charge along a line instead of concentrating it on a point.
"""
import io
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A

SIZE_UM = 5.0
PX_V = 128                 # VDART pixels; the square is 1.2 um = ~31 px
RATE = A.TIP_SPEED_MAX / (2.0 * SIZE_UM)
XOFF, YOFF = 16.0, -8.0    # a SECOND fresh area, for the before/after version
SQ = 1.2                   # square side, um
PITCH = 0.06               # raster line pitch, um
VOLT = 10.0
SPEED = 0.25               # um/s; areal dose ~667 V.s/um^2, ~1.7x the
                           # lattice that failed, so a NULL here is meaningful
STEP = 0.02
CENTRES = ((1.6, 2.5), (3.4, 2.5))     # +V left, -V right, inside a 5 um field

STAMP = time.strftime('%y%m%d_%H%M')


def build(ns):
    """Two solid squares, opposite polarity, rastered."""
    tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    for (cx, cy), v in zip(CENTRES, (+VOLT, -VOLT)):
        n = int(round(SQ / PITCH)) + 1
        for i in range(n):
            y = cy - SQ / 2.0 + i * PITCH
            x0, x1 = cx - SQ / 2.0, cx + SQ / 2.0
            # serpentine: alternate direction so travel between lines is short
            pts = [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
            tb.stroke(pts, v)
    return tb


def ldart(ns, g, tag):
    """An LDART frame at the poled area, re-tuned (M12).

    The first poling diagnostic took VDART only, so the in-plane comparison it
    enabled was inside-vs-outside within one frame -- which cannot separate
    'the write changed this patch' from 'this patch was always different'.
    Taking LDART before AND after removes that, and turns a grade-C
    observation into a before/after with its own control.
    """
    _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=256, rate=RATE,
                             angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                             tries=1, verbose=False)
    print('    LDART %s -> %s (tune %.1f kHz)' % (tag, inf['frame'], _c / 1000.0))
    return inf['frame']


def vdart(ns, g, tag):
    g('setup_scan')(size_um=SIZE_UM, px=PX_V, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_vdart')()
    f = g('frame')()
    print('    %s -> %s' % (tag, f))
    try:
        g('orbit_balance')(f)
    except Exception:
        pass
    return f


def report(ns, g, f, tag):
    """Up/down fractions and, crucially, whether the minority forms PATCHES."""
    try:
        d, h = g('ibw')(f)
        out = g('vdart_classes')(f) if 'vdart_classes' in ns else None
        print('    %-8s %s' % (tag, out if out is not None else '(see below)'))
    except Exception:
        pass


def main():
    print('=' * 74)
    print('DIAG: does the tip deliver bias?   %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  two %.1f um squares at %+.0f V and %-.0f V, %.0f nm raster pitch'
          % (SQ, VOLT, -VOLT, PITCH * 1000))
    print('  area (%+.1f,%+.1f), %.0f um frame -- fresh, and not one the'
          % (XOFF, YOFF, SIZE_UM))
    print('  pathway experiments would want')
    print('  NOTE: diagnostic only. campaign_state.json is not touched.')

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    if os.path.exists(A.STOP):
        raise SystemExit('STOP file present')

    tb = build(ns)
    L = tb.path_length_um()
    mins = L / SPEED / 60.0
    # to_arrays() returns THREE arrays -- x, y, v -- not (xy, v). Unpacking the
    # first two as coordinates-and-voltage reports the y column as the voltage,
    # which reads as a plausible +1.9..+3.1 V and hides the real +-10.
    _ar = tb.to_arrays()
    assert len(_ar) == 3, 'to_arrays() returned %d arrays, expected x, y, v' % len(_ar)
    xs, ys, vv = (np.asarray(q, float) for q in _ar)
    print('\n  built: %.1f um of path -> %.1f min at %.2f um/s'
          % (L, mins, SPEED))
    print('  |V| max %.1f, mean %+.3f, %.0f%% at 0 V'
          % (np.nanmax(np.abs(vv)), np.nanmean(vv),
             100.0 * np.mean(np.isclose(vv, 0.0))))
    print('  x %.2f-%.2f um, y %.2f-%.2f um, inside the %.0f um field: %s'
          % (np.nanmin(xs), np.nanmax(xs), np.nanmin(ys), np.nanmax(ys),
             SIZE_UM,
             'yes' if (np.nanmin([xs.min(), ys.min()]) >= 0.0
                       and np.nanmax([xs.max(), ys.max()]) <= SIZE_UM)
             else 'NO'))
    if not (abs(np.nanmax(np.abs(vv)) - VOLT) < 1e-6):
        raise SystemExit('built path does not carry %+.0f V; got |V|max %.3f'
                         % (VOLT, np.nanmax(np.abs(vv))))
    # per-pass dose at a point: the tip crosses a line in (spot/speed) seconds
    print('  per-site dose ~ %.1f V.s (C21 limit %.0f) -- a raster spreads'
          % (VOLT * 0.05 / SPEED, A.CHG_1PULSE_MAX))
    print('  charge along the line instead of stacking it on one point')
    if mins > 6.0:
        raise SystemExit('path too long for a diagnostic: %.1f min' % mins)

    print('\n--- BEFORE ---')
    lb = ldart(ns, g, 'before')
    b = vdart(ns, g, 'before')

    print('\n--- poling ---')
    fn = os.path.join(A.PROJ, 'output', '%s_DIAG_poling.txt' % STAMP)
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)

    print('\n--- AFTER ---')
    a = vdart(ns, g, 'after')
    la = ldart(ns, g, 'after')

    print('\n' + '=' * 74)
    print('READ IT LIKE THIS')
    print('=' * 74)
    print('  VDART  before %s   after %s' % (b, a))
    print('  LDART  before %s   after %s' % (lb, la))
    print('  The LDART pair is the one that matters for the mission: it makes')
    print('  the in-plane comparison BEFORE/AFTER on the same patch, instead of')
    print('  inside-vs-outside on one frame.')
    print('  Look at the AFTER phase image for two %.1f um squares at' % SQ)
    print('  (%.1f,%.1f) and (%.1f,%.1f) um within the frame.'
          % (CENTRES[0][0], CENTRES[0][1], CENTRES[1][0], CENTRES[1][1]))
    print('')
    print('  squares visible  -> the tip writes; the IP voids are real physics')
    print('  no squares       -> no bias reaches the sample; every void tonight')
    print('                      has one cause, and it is not fixable in')
    print('                      software. Stop writing.')
    g('goto_ldart')()


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
        io.open(os.path.join(A.PROJ, 'diag_poling_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
