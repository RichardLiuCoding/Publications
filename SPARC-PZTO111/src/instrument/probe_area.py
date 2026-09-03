# -*- coding: utf-8 -*-
"""probe_area.py -- measure a handful of offsets before committing to one.

Measurement only: no bias, no litho, no state written.

After a stage move nothing about the new film is known -- not Lambda, not the
triad, not whether the lateral channel is readable here. Every one of those has
been wrong as a constant before (PITFALLS rule 4), and the pre-flight checklist
requires geometry to come from measured values.

Prints, per offset: the fitted triad, modulation, streak, Lambda per member and
the median, plus |A| and r12 from contact_check so a dead readout is visible
immediately rather than after a write (M12).

    python probe_area.py                 # default 5-point cross
    PROBE_PTS="0,0 8,0 -8,0" python probe_area.py
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
PX = 256
RATE = A.TIP_SPEED_MAX / (2.0 * SIZE_UM)

_env = os.environ.get('PROBE_PTS', '').strip()
if _env:
    PTS = [tuple(float(v) for v in p.split(',')) for p in _env.split()]
else:
    PTS = [(0.0, 0.0), (8.0, 0.0), (-8.0, 0.0), (0.0, 8.0), (0.0, -8.0)]

# the window the geometry has to fit into, from M9
WIN_LO, WIN_HI = 148.0, 420.0
MOD_MIN = 0.18

STAMP = time.strftime('%y%m%d_%H%M')


def main():
    print('=' * 74)
    print('AREA PROBE  %s   (measurement only)' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  %d offsets, %.0f um frames, %d px' % (len(PTS), SIZE_UM, PX))
    print('  buildable window %.0f-%.0f nm, modulation floor %.2f'
          % (WIN_LO, WIN_HI, MOD_MIN))

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    rows = []
    for k, (xo, yo) in enumerate(PTS):
        print('\n--- %d/%d  (%+.1f,%+.1f) ---' % (k + 1, len(PTS), xo, yo))
        try:
            g('scanner_ok')(xo, yo, SIZE_UM)
            _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                                     angle_deg=0.0, xoff_um=xo, yoff_um=yo,
                                     tries=1, verbose=False)
            tag = inf['frame']
            cc = g('contact_check')(tag)
            triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
            d, h = g('ibw')(tag)
            S, _, _ = g('signed')(d)
            # px_nm from THIS frame's own header, never from a constant (19.11)
            px_nm = float(h['ScanSize']) * 1e6 / float(S.shape[0]) * 1000.0
            lam = []
            for f in [float(x) for x in triad]:
                v = g('period')(S, px_nm, f)
                lam.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                           else float(v))
            lam = [v for v in lam if v == v]
            lam_med = float(np.median(lam)) if lam else float('nan')
            sk = g('streak_index')(tag, (0.2, SIZE_UM - 0.2, 0.2, 0.8),
                                   verbose=False)
            w = tt.get('w')
            dom = float(triad[int(np.argmax(w))]) if w is not None else float('nan')
            ok = (WIN_LO <= lam_med <= WIN_HI) and (tt['mod'] >= MOD_MIN)
            rows.append(dict(x=xo, y=yo, tag=tag, lam=lam_med, mod=tt['mod'],
                             sk=sk, dom=dom, ok=ok,
                             triad=[float(t) for t in triad]))
            print('    triad %s  dominant %.0f deg' %
                  ([int(round(t)) for t in triad], dom))
            print('    Lambda %s -> median %.0f nm' %
                  (['%.0f' % v for v in lam], lam_med))
            print('    modulation %.3f | streak %.3f  -> %s'
                  % (tt['mod'], sk, 'USABLE' if ok else 'no'))
        except Exception:
            print('    failed, continuing:')
            traceback.print_exc(limit=2)

    print('\n' + '=' * 74)
    if not rows:
        print('nothing measured')
        return
    good = [r for r in rows if r['ok']]
    print('%-16s %8s %7s %7s %8s  %s'
          % ('offset', 'Lambda', 'mod', 'streak', 'dominant', 'usable'))
    for r in sorted(rows, key=lambda q: (-q['ok'], -q['mod'])):
        print('(%+5.1f,%+5.1f)   %7.0f %7.3f %7.3f %8.0f  %s'
              % (r['x'], r['y'], r['lam'], r['mod'], r['sk'], r['dom'],
                 'YES' if r['ok'] else '-'))
    if good:
        b = max(good, key=lambda q: q['mod'])
        print('\n  best: (%+.1f,%+.1f)  Lambda %.0f nm, modulation %.3f, '
              'triad %s' % (b['x'], b['y'], b['lam'], b['mod'],
                            [int(round(t)) for t in b['triad']]))
        print('  spacing for a commensurate lattice, sp = Lambda/2 = %.0f nm'
              % (b['lam'] / 2.0))
    else:
        print('\n  no offset cleared both gates; widen the probe before writing')


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
        io.open(os.path.join(A.PROJ, 'probe_area_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
