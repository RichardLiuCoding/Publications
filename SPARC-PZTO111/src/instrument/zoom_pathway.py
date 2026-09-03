# -*- coding: utf-8 -*-
"""zoom_pathway.py -- image written panels at the finest scale this probe allows.

FREE. Costs no S24 write budget: it only images film that is already written.

WHY. M17 established the transition is REPLACEMENT rather than rotation, but
from angular power, not from watching walls. The lamellar period is resolved at
the standard 5 um / 256 px readout (19.5 nm/px, 15 px per Lambda); individual
walls are not. This re-images written panels and their controls at 2 um / 256 px
= 7.8 nm/px -- 2.5x finer, ~38 px per Lambda -- to see whether the wall structure
and the nucleation geometry become visible.

WHAT IT ANSWERS
  * are individual lamellae and their terminations resolved at 7.8 nm/px?
  * inside a rewritten panel, is the new orientation uniform, or does it appear
    as islands with residual patches of the old one? Islands are the signature
    of nucleation-and-growth; a uniform panel with sharp edges is not.
  * do the old and new orientations coexist anywhere, and on what length scale?

If the answer to the first is no, that is a probe limit and the operator has said
a sharper tip is available; the panels stay on the sample and can be re-imaged.

  ZOOM_AREA="16,-16"   which area (must be one already written)
  ZOOM_C="1.5,2.5"     panel centre within the frame, um
  ZOOM_SIZE=2.0        frame size, um
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A

PX = 256
AX = float(os.environ.get('ZOOM_AREA', '0,0').split(',')[0])
AY = float(os.environ.get('ZOOM_AREA', '0,0').split(',')[1])
CX = float(os.environ.get('ZOOM_C', '1.5,2.5').split(',')[0])
CY = float(os.environ.get('ZOOM_C', '1.5,2.5').split(',')[1])
SIZE = float(os.environ.get('ZOOM_SIZE', '2.0'))
STAMP = time.strftime('%y%m%d_%H%M')


def main():
    rate = A.TIP_SPEED_MAX / (2.0 * SIZE)
    print('=' * 74)
    print('ZOOM PATHWAY  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  area (%+.1f,%+.1f), panel centre (%.2f,%.2f) in the frame'
          % (AX, AY, CX, CY))
    print('  %.1f um at %d px -> %.2f nm/px  (%.0f px per Lambda at 300 nm)'
          % (SIZE, PX, SIZE / PX * 1000, 300.0 / (SIZE / PX * 1000)))
    print('  measurement only: no bias, no litho, no state written')

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    # the panel centre is given in the 5 um frame; convert to a stage offset
    xo = AX + (CX - 2.5)
    yo = AY + (CY - 2.5)
    print('\n  stage offset for the zoom: (%+.2f,%+.2f)' % (xo, yo))
    g('scanner_ok')(xo, yo, SIZE)

    _c, inf = g('tune_here')('ldart', size_um=SIZE, px=PX, rate=rate,
                             angle_deg=0.0, xoff_um=xo, yoff_um=yo,
                             tries=1, verbose=False)
    tag = inf['frame']
    print('  -> %s (tune %.1f kHz)' % (tag, _c / 1000.0))
    cc = g('contact_check')(tag)

    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    px_nm = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
    print('  actual %.2f nm/px' % px_nm)

    triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    print('  triad %s, modulation %.3f'
          % ([int(round(t)) for t in triad], tt['mod']))
    lam = []
    for t in triad:
        v = g('period')(S, px_nm, t)
        lam.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                   else float(v))
    lam = [x for x in lam if x == x]
    print('  Lambda %s nm -> %.0f px per period'
          % (['%.0f' % x for x in lam],
             float(np.median(lam)) / px_nm))

    # --- is the panel single-orientation, or islands? -------------------
    # tile the frame and read the dominant in each tile; a uniformly rewritten
    # panel gives one dominant everywhere, nucleation gives a mixture
    n = S.shape[0]
    tile = max(24, int(round(4.0 * float(np.median(lam)) / px_nm)))
    doms, wmax = [], []
    for j in range(0, n - tile + 1, tile // 2):
        for i in range(0, n - tile + 1, tile // 2):
            sub = S[j:j + tile, i:i + tile]
            if sub.shape[0] != sub.shape[1]:
                continue
            try:
                p = g('pops')(sub, px_nm)
            except Exception:
                continue
            w = np.asarray(p[0], float)
            doms.append(float(p[2]))
            wmax.append(float(np.max(w / w.sum())))
    doms = np.asarray(doms)
    wmax = np.asarray(wmax)
    print('\n  %d tiles of %d px (%.2f um, %.1f Lambda each)'
          % (len(doms), tile, tile * px_nm / 1000,
             tile * px_nm / float(np.median(lam))))
    if len(doms):
        # cluster tile dominants onto the triad
        assign = [int(np.argmin([abs((dd - t + 90) % 180 - 90) for t in triad]))
                  for dd in doms]
        frac = [float(np.mean(np.asarray(assign) == k)) for k in range(3)]
        print('  tile dominants by triad member: %s'
              % ' '.join('%.0f deg %.0f%%' % (triad[k], 100 * frac[k])
                         for k in range(3)))
        print('  mean single-member weight per tile %.3f +- %.3f'
              % (float(np.mean(wmax)), float(np.std(wmax))))
        top = max(frac)
        if top > 0.85:
            print('  -> UNIFORM: one orientation across the field. No island')
            print('     structure at this scale, so if nucleation happened the')
            print('     islands have already merged.')
        elif top > 0.5:
            print('  -> MIXED, majority %.0f%%: coexisting orientations at the'
                  % (100 * top))
            print('     %.2f um tile scale. That is the island signature.'
                  % (tile * px_nm / 1000))
        else:
            print('  -> NO MAJORITY: the field is not single-orientation here.')
    print('\n  frame kept: %s' % tag)


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
        io.open(os.path.join(A.PROJ, 'zoom_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
