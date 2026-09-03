# -*- coding: utf-8 -*-
"""hires.py -- re-image an already-written region at the finest scale.

MEASUREMENT ONLY. No bias, no litho. Costs no S24 budget: every region imaged
here is already on the sample.

WHY. Five commensurate panels, one poling square and one incommensurate panel
have all failed to show a reproducible nano-domain periodicity at 2.5 um /
512 px = 4.88 nm/px. The operator reports the nano-domains are ~40-55 nm, which
is 8-11 px at that sampling -- resolvable in principle, but sitting in a fine
band that is contaminated at both ends:

  * the lamellar harmonics Lambda/2, /3, /4 fall at 50-125 nm at the SAME
    director as the lamellae (PITFALLS 21.5);
  * a broadband instrumental feature sits at ~70-80 nm within a few degrees of
    the fast scan axis in every frame, written or not (PITFALLS 21.6).

At 1.25 um / 512 px = 2.44 nm/px a 45 nm structure is 18 px, and the fine band
can be pushed DOWN to 15-45 nm, below every lamellar harmonic that matters and
away from the ~75 nm artefact. If nano-domains are there, this is the sampling
that shows them.

  HR_AREA="8,0"     stage offset of the region
  HR_C="1.25,1.25"  centre within the ORIGINAL 2.5 um frame
  HR_SIZE=1.25      new frame size, um
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

PX = 512
AX, AY = [float(v) for v in os.environ.get('HR_AREA', '8,0').split(',')]
CX, CY = [float(v) for v in os.environ.get('HR_C', '1.25,1.25').split(',')]
SIZE = float(os.environ.get('HR_SIZE', '1.25'))
LABEL = os.environ.get('HR_LABEL', '')
STAMP = time.strftime('%y%m%d_%H%M')

SUPER = (150.0, 500.0)
ULTRA = (15.0, 45.0)      # below every lamellar harmonic that matters
MID = (45.0, 90.0)        # where the fast-axis artefact lives


def main():
    rate = min(2.0, A.TIP_SPEED_MAX / (2.0 * SIZE))
    print('=' * 74)
    print('HI-RES  %s  %s' % (LABEL, time.strftime('%Y-%m-%d %H:%M')))
    print('=' * 74)
    print('  MEASUREMENT ONLY. %.2f um at %d px -> %.2f nm/px, %.1f Hz'
          % (SIZE, PX, SIZE / PX * 1000, rate))
    print('  tip speed %.1f um/s' % (2 * SIZE * rate))
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    xo, yo = AX + (CX - 1.25), AY + (CY - 1.25)
    g('scanner_ok')(xo, yo, SIZE)
    print('  stage offset (%+.2f,%+.2f)' % (xo, yo))

    out = {}
    for mode in ('ldart', 'vdart'):
        print('\n--- %s ---' % mode.upper())
        _c, inf = g('tune_here')(mode, size_um=SIZE, px=PX, rate=rate,
                                 angle_deg=0.0, xoff_um=xo, yoff_um=yo,
                                 tries=1, verbose=False)
        tag = inf['frame']
        print('    %s  tracked %.0f%%' % (tag, 100 * inf['frac']))
        try:
            g('contact_check')(tag)
        except Exception as e:
            print('    contact_check: %s' % e)
        d, h = g('ibw')(tag)
        S, _, r12 = g('signed')(d)
        px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
        print('    %.2f nm/px, |S| %.1f pm, r12 %+.2f' % (px, np.std(S), r12))
        sd, sa, sp, spv = ST.band_peak(S, px, *SUPER, n_perm=200)
        print('    super  %6.1f deg  %7.1f nm  aniso %6.2f  p %.4f'
              % (sd, sp, sa, spv))
        for nm, band in (('mid  ', MID), ('ULTRA', ULTRA)):
            dd, an, per, pv = ST.band_peak(S, px, *band, n_perm=200)
            off0 = ST.angle_between(dd, 0.0)
            offs = ST.angle_between(dd, sd) if sd == sd else float('nan')
            harm = ''
            if sp == sp and per == per:
                k = int(round(sp / max(per, 1e-9)))
                if k >= 2 and abs(per - sp / k) / max(per, 1) < 0.12:
                    harm = ' ~Lambda/%d' % k
            tag2 = ('fast-axis' if off0 < 15 else
                    ('lamellar%s' % harm if offs < 15 else 'OFF BOTH'))
            print('    %s  %6.1f deg  %7.1f nm  aniso %6.2f  p %.4f  %s (%.0f px'
                  '/period)' % (nm, dd, per, an, pv, tag2, per / px))
            if nm == 'ULTRA' and pv < 0.01 and off0 >= 15 and offs >= 15:
                print('       -> CANDIDATE NANO-DOMAINS: %.1f nm at %.0f deg,'
                      ' %.0f deg off the lamellae, %.0f off the fast axis'
                      % (per, dd, offs, off0))
        out[mode] = tag
    print('\n  frames: %s' % ', '.join(out.values()))


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
        io.open(os.path.join(A.PROJ, 'hires_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
