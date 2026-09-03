# -*- coding: utf-8 -*-
"""survey_lambda.py -- map Lambda, modulation and streak across the scanner.

WHY THIS EXISTS
---------------
On 27-28 Aug, 36 screened candidates at sample position 4 were all unusable: the
lamellar period ran 430-635 nm and a scored measurement at 10 um needs

    148 nm <= Lambda <= ~420 nm

(below that n jumps 16 -> 32 and nothing fits; above it the readout window,
4.2*Lambda, and the halo swallow the frame and leave fewer than 6 control tiles
-- 13 tiles at 420 nm, 4 at 440, 0 at 460. See FINDINGS M9.)

Screening inside a driver answers "can I write HERE, now". It does not answer
"where on this sample should I be", and it costs a tune plus a frame per point
either way. This survey answers the second question and leaves a map.

WHAT IT DOES
------------
Nothing but measure. No bias is applied, no litho file is built, no state is
written. Every frame is 5 um -- the operator's preferred size -- so the tip
covers a quarter the area of a 10 um frame per point and the turn-around is
2.1 min.

For each grid point: tune, one frame, then the pinned triad, the per-member
Lambda, the modulation, the streak index and the dominant director. Results are
appended to CSV after every point, so an interruption keeps everything measured
so far.

OUTPUT
------
    survey_lambda_<date>.csv    one row per point
    survey_lambda_<date>.png    Lambda and modulation maps, buildable points
                                circled

READ IT LIKE THIS
-----------------
A point is worth moving to if Lambda is inside the window AND modulation clears
0.18. Those two have been anti-correlated in both directions on this sample --
at position 3 the best-modulation areas were too FINE, at position 4 the one
in-window area had modulation 0.148 -- so the map is the honest way to find a
point that satisfies both rather than hoping the next candidate does.
"""
import io
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A

SIZE_UM = 5.0                 # operator constraint: keep it small
PX = 256
RATE = A.TIP_SPEED_MAX / (2.0 * SIZE_UM)
SPAN = 36.0                   # +- this, in um; scanner allows |off| + size <= 50
STEP = 9.0                    # grid pitch
WIN_LO, WIN_HI = 148.0, 420.0     # the buildable window at 10 um (M9)
MOD_MIN = 0.18

STAMP = time.strftime('%y%m%d_%H%M')
CSV = os.path.join(A.PROJ, 'survey_lambda_%s.csv' % STAMP)
PNG = os.path.join(A.PROJ, 'survey_lambda_%s.png' % STAMP)


def grid():
    """Offsets on a coarse grid, ordered by distance so the useful part of the
    map exists early if the survey is cut short."""
    pts = []
    n = int(SPAN / STEP)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x, y = i * STEP, j * STEP
            if abs(x) + SIZE_UM <= 50.0 and abs(y) + SIZE_UM <= 50.0:
                pts.append((x, y))
    pts.sort(key=lambda p: p[0] ** 2 + p[1] ** 2)
    return pts


def main():
    print('=' * 74)
    print('LAMBDA SURVEY  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  %.0f um frames, %d px, %.1f Hz -> %.1f min each'
          % (SIZE_UM, PX, RATE, PX / RATE / 60.0))
    print('  measurement only: no bias, no litho, no state written')
    print('  buildable window at 10 um: %.0f-%.0f nm, modulation >= %.2f'
          % (WIN_LO, WIN_HI, MOD_MIN))

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    pts = grid()
    print('  %d grid points, %.0f um pitch, span +-%.0f um'
          % (len(pts), STEP, SPAN))
    print('  estimated %.0f min total\n' % (len(pts) * (PX / RATE / 60.0 + 0.9)))

    io.open(CSV, 'w', encoding='utf-8').write(
        'xoff_um,yoff_um,tag,lam_med_nm,lam_members_nm,modulation,streak,'
        'dominant_deg,triad_deg,buildable\n')

    rows = []
    for k, (xo, yo) in enumerate(pts):
        print('--- point %d/%d  (%+.0f,%+.0f) ---' % (k + 1, len(pts), xo, yo))
        try:
            if os.path.exists(A.STOP):
                print('  STOP file present; ending the survey here.')
                break
            _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                                     angle_deg=0.0, xoff_um=xo, yoff_um=yo,
                                     tries=1, verbose=False)
            tag = inf['frame']
            # pin_triad takes no verbose= -- checked against the toolkit
            # signature rather than assumed; it prints a few lines per
            # point and that is acceptable in a survey log.
            triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
            d, h = g('ibw')(tag)
            S, _, _ = g('signed')(d)
            px_nm = SIZE_UM / PX * 1000.0
            lam = []
            for f in [float(x) for x in triad]:
                v = g('period')(S, px_nm, f)
                lam.append(float(v[0]) if isinstance(v, (tuple, list,
                                                         np.ndarray))
                           else float(v))
            lam = [v for v in lam if v == v]
            lam_med = float(np.median(lam)) if lam else float('nan')
            sk = g('streak_index')(tag, (0.2, SIZE_UM - 0.2, 0.2, 0.8),
                                   verbose=False)
            w = tt.get('w')
            dom = float(triad[int(np.argmax(w))]) if w is not None else float('nan')
            ok = (WIN_LO <= lam_med <= WIN_HI) and (tt['mod'] >= MOD_MIN)
            print('    Lambda %.0f nm %s | modulation %.3f | streak %.3f | '
                  'dominant %.0f -> %s'
                  % (lam_med, ['%.0f' % v for v in lam], tt['mod'], sk, dom,
                     'BUILDABLE' if ok else 'no'))
            rows.append(dict(x=xo, y=yo, lam=lam_med, mod=tt['mod'], sk=sk,
                             dom=dom, ok=ok))
            io.open(CSV, 'a', encoding='utf-8').write(
                '%.1f,%.1f,%s,%.1f,%s,%.4f,%.4f,%.1f,%s,%d\n'
                % (xo, yo, tag, lam_med,
                   '|'.join('%.0f' % v for v in lam), tt['mod'], sk, dom,
                   '|'.join('%.0f' % t for t in triad), int(ok)))
        except Exception:
            print('    point failed, continuing:')
            traceback.print_exc(limit=2)

    print('\n' + '=' * 74)
    print('SURVEY DONE: %d points measured' % len(rows))
    if not rows:
        return
    lam = np.array([r['lam'] for r in rows], float)
    mod = np.array([r['mod'] for r in rows], float)
    good = [r for r in rows if r['ok']]
    print('  Lambda  min %.0f  median %.0f  max %.0f nm'
          % (np.nanmin(lam), np.nanmedian(lam), np.nanmax(lam)))
    print('  modulation  min %.3f  median %.3f  max %.3f'
          % (np.nanmin(mod), np.nanmedian(mod), np.nanmax(mod)))
    print('  inside the window %.0f-%.0f nm: %d of %d'
          % (WIN_LO, WIN_HI, int(np.sum((lam >= WIN_LO) & (lam <= WIN_HI))),
             len(rows)))
    print('  BUILDABLE (window AND modulation >= %.2f): %d'
          % (MOD_MIN, len(good)))
    for r in sorted(good, key=lambda q: -q['mod'])[:10]:
        print('     (%+6.1f,%+6.1f)  Lambda %.0f nm, modulation %.3f, '
              'dominant %.0f' % (r['x'], r['y'], r['lam'], r['mod'], r['dom']))
    if not good:
        print('     none. Within +-%.0f um of this stage position there is no'
              % SPAN)
        print('     point that is both fine enough and textured enough. The')
        print('     coarse stage has to move.')
    print('\n  csv: %s' % CSV)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        x = np.array([r['x'] for r in rows]); y = np.array([r['y'] for r in rows])
        fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))
        s0 = ax[0].scatter(x, y, c=lam, s=260, cmap='viridis', marker='s',
                           edgecolors='k', linewidths=0.4)
        plt.colorbar(s0, ax=ax[0], label='Lambda (nm)')
        ax[0].set_title('lamellar period\nbuildable window %.0f-%.0f nm circled'
                        % (WIN_LO, WIN_HI))
        s1 = ax[1].scatter(x, y, c=mod, s=260, cmap='magma', marker='s',
                           edgecolors='k', linewidths=0.4)
        plt.colorbar(s1, ax=ax[1], label='triad modulation')
        ax[1].set_title('modulation\nfloor %.2f' % MOD_MIN)
        for a in ax:
            a.set_xlabel('x offset (um)'); a.set_ylabel('y offset (um)')
            a.set_aspect('equal'); a.grid(alpha=0.25)
            for r in good:
                a.plot(r['x'], r['y'], 'o', mfc='none', mec='lime', mew=2.4,
                       ms=20)
        fig.suptitle('Lambda / modulation survey, %s -- %d points at %.0f um, '
                     'measurement only' % (STAMP, len(rows), SIZE_UM))
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(PNG, dpi=130)
        print('  figure: %s' % PNG)
    except Exception:
        print('  (figure skipped)')
        traceback.print_exc(limit=1)


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
        io.open(os.path.join(A.PROJ, 'survey_console_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
