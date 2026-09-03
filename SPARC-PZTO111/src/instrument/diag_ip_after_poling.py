# -*- coding: utf-8 -*-
"""diag_ip_after_poling.py -- does a KNOWN-GOOD write move the in-plane director?

WHY THIS EXISTS
---------------
Three in-plane iterations came back VOID on 28 Aug. Two explanations survived:
the point-pulse lattice does not move the IP super-domain director at
sigma ~400 V.s/um^2, or nothing was reaching the sample at all.

`diag_poling.py` settled the second one. Two solid 1.2 um squares at +-10 V
produced, in VDART:

    +10 V square   phase -180.2 deg vs control, |A| 45.5 -> 166.5 pm
    -10 V square   phase   -1.8 deg vs control, |A| 52.0 -> 186.5 pm
    control        phase   +2.5 deg,            |A| 43.1 ->  47.9 pm

A full 180 deg polarisation reversal under +10 V, none under -10 V (the film's
native state already points that way), both squares driven to a phase-uniform
single domain (sd 55.7 -> 30.8 and 53.3 -> 6.2). Confirmed on BOTH DART phase
channels: -180.2 and -178.5 deg. **The tip writes.**

So there now exists a patch of this sample whose out-of-plane polarisation is
known to have been completely reversed. That is the positive control the in-plane
experiments never had.

WHAT THIS ASKS
--------------
Image the same area in LDART and compare the in-plane director INSIDE each
square against the untouched film around them -- a within-frame comparison, so
drift cancels (C42). Two outcomes, both worth having:

  the squares differ from their surroundings
      -> a strong enough write DOES rewrite the IP director. The lattice at
         sigma ~400 is simply below what this film needs, and the dose ladder
         becomes the right next experiment.

  the squares are indistinguishable
      -> reversing P_z by 180 deg does NOT drag the in-plane super-domain
         director with it. The two order parameters are decoupled under
         uniform DC poling, and the point-pulse lattice's commensurate
         template (T3's selection condition) is doing something a solid poled
         square cannot. That is a real statement about the rewriting rules and
         it is what the mission is for.

Note what this canNOT say: there is no LDART "before" of this area, because the
poling diagnostic only took VDART frames. The comparison is therefore
inside-vs-outside within one frame, not before-vs-after. Inside-vs-outside is
sound for detecting a difference, but it cannot separate "the write changed the
squares" from "the squares were always different" -- so the surrounding film is
also compared against the campaign's own triad, and any claim here is graded
accordingly.

Diagnostic only: campaign_state.json is not touched.
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
XOFF, YOFF = 8.0, -8.0          # the poled area
SQ = 1.2
CENTRES = ((1.6, 2.5), (3.4, 2.5))
LABELS = ('+10V (reversed)', '-10V (unchanged)')
STAMP = time.strftime('%y%m%d_%H%M')


def sub(S, px_nm, x0, x1, y0, y1):
    """Crop in um -> pixel slice, on a square frame of PX pixels."""
    f = lambda u: max(0, min(S.shape[0], int(round(u * 1000.0 / px_nm))))
    return S[f(y0):f(y1), f(x0):f(x1)]


def main():
    print('=' * 74)
    print('DIAG: in-plane director inside a KNOWN-reversed square   %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  area (%+.1f,%+.1f), %.0f um, LDART' % (XOFF, YOFF, SIZE_UM))
    print('  the +10 V square is confirmed 180 deg reversed out of plane;')
    print('  the -10 V square is confirmed NOT reversed. So the two squares')
    print('  are also a control for each other: same dose, same geometry,')
    print('  same tip, opposite outcome out of plane.')
    print('  diagnostic only: no state is written.')

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    print('\n--- LDART frame at the poled area ---')
    _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                             angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                             tries=1, verbose=False)
    tag = inf['frame']
    print('    %s (tune centre %.1f kHz)' % (tag, _c / 1000.0))
    g('contact_check')(tag)

    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    px_nm = float(h['ScanSize']) * 1e6 / float(S.shape[0]) * 1000.0
    print('    px %.2f nm/px' % px_nm)

    triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    print('    whole-frame triad %s, modulation %.3f'
          % ([int(round(t)) for t in triad], tt['mod']))

    # regions: the two squares, and four untouched patches around them
    regions = []
    for (cx, cy), lab in zip(CENTRES, LABELS):
        regions.append((lab, cx - SQ / 2, cx + SQ / 2, cy - SQ / 2, cy + SQ / 2))
    # Controls are the SAME 1.2 um size as the squares and sit directly above
    # and below each one. Equal area matters because the triad estimate is
    # FFT-based and its variance depends on how many periods the window holds;
    # comparing a 1.2 um square against a 3.8 x 1.0 um strip would compare two
    # different estimators. ospec also requires a square crop -- a non-square
    # one raises on a broadcast, which is how this was caught.
    for cx, tagn in ((CENTRES[0][0], 'A'), (CENTRES[1][0], 'B')):
        regions.append(('control %s-below' % tagn,
                        cx - SQ / 2, cx + SQ / 2, 0.3, 0.3 + SQ))
        regions.append(('control %s-above' % tagn,
                        cx - SQ / 2, cx + SQ / 2, 3.5, 3.5 + SQ))

    print('\n  %-18s %8s %8s %8s   %s'
          % ('region', 'w(t0)', 'w(t1)', 'w(t2)', 'dominant'))
    out = {}
    for lab, x0, x1, y0, y1 in regions:
        Ssub = sub(S, px_nm, x0, x1, y0, y1)
        try:
            # pops() returns a 5-tuple (w, ?, dominant_deg, angles, power),
            # not an array. np.asarray() on the whole thing raises on the
            # inhomogeneous shapes, and .ravel()[:3] on a coerced version
            # would silently mix the populations with the scalars.
            _p = g('pops')(Ssub, px_nm)
            w = np.asarray(_p[0], float).ravel()[:3]
            w = w / w.sum() if w.sum() else w
            dom = float(_p[2])
            out[lab] = w
            # The populations from a 1.2 um window are weak: that is only
            # ~4.3 periods at Lambda 280 nm, the bare minimum the FFT estimate
            # needs, and on UNWRITTEN film four such windows scattered over
            # w[0] = 0.29-0.59 with dominants 45/90/90/135. So carry two
            # robust scalars alongside them -- lateral amplitude and the
            # modulation depth -- which is exactly what made the VDART answer
            # unambiguous (45 -> 166 pm) while its phase histogram did not.
            amp = 1e12 * float(np.nanmean(np.abs(AMP[_sl(lab)])))
            md = float(np.nanmax(_p[4]) / np.nanmean(_p[4])) if len(_p[4]) else float('nan')
            AUX[lab] = (amp, md)
            print('  %-18s %8.3f %8.3f %8.3f   %3.0f deg  %7.1f pm  %6.2f'
                  % (lab, w[0], w[1], w[2], dom, amp, md))
        except Exception as e:
            print('  %-18s failed: %s' % (lab, e))

    ctrl = [out[k] for k in out if k.startswith('control')]
    if ctrl and all(l in out for l in LABELS):
        cmean = np.mean(ctrl, axis=0)
        # null = the largest deviation any control shows from the control
        # mean. With four controls this is a real (if small) leave-one-out
        # style spread rather than a single difference.
        cspread = float(np.max([np.max(np.abs(c - np.mean(ctrl, axis=0)))
                                for c in ctrl])) if len(ctrl) > 1 else 0.0
        print('\n  control mean  %8.3f %8.3f %8.3f' % tuple(cmean))
        print('  control-to-control spread (the only null available here): '
              '%.3f' % cspread)
        print('')
        for lab in LABELS:
            dmax = float(np.max(np.abs(out[lab] - cmean)))
            verdict = ('DIFFERS from the surrounding film'
                       if dmax > 2 * max(cspread, 1e-3)
                       else 'indistinguishable from the surrounding film')
            print('  %-18s max |w - control| = %.3f  -> %s'
                  % (lab, dmax, verdict))
        print('')
        print('  lateral amplitude and modulation, which do NOT depend on a')
        print('  3-component fit from a 4-period window:')
        _ca = [AUX[k][0] for k in AUX if k.startswith('control')]
        _cm2 = [AUX[k][1] for k in AUX if k.startswith('control')]
        print('    control lat |A| %.1f +- %.1f pm,  mod %.2f +- %.2f'
              % (np.mean(_ca), np.std(_ca), np.nanmean(_cm2), np.nanstd(_cm2)))
        for lab in LABELS:
            a, mo = AUX[lab]
            za = (a - np.mean(_ca)) / (np.std(_ca) if np.std(_ca) else 1e-9)
            zm = (mo - np.nanmean(_cm2)) / (np.nanstd(_cm2) if np.nanstd(_cm2) else 1e-9)
            print('    %-18s lat |A| %.1f pm (%+.1f sd),  mod %.2f (%+.1f sd)'
                  % (lab, a, za, mo, zm))
        print('')
        print('  Read with care: four control patches give a coarse null,')
        print('  which is far weaker than C45s leave-one-out over 12-31 tiles.')
        print('  This is a DIAGNOSTIC and is graded C at best. It is here to')
        print('  say which experiment to run next, not to settle the question.')


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
        io.open(os.path.join(A.PROJ, 'diag_ip_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
