# -*- coding: utf-8 -*-
"""analyse_offtriad.py -- is the readout the FILM or the TEMPLATE?

FREE: analysis only.

THE PROBLEM. Every director in this campaign has been commanded TO a triad
member. So two hypotheses have never been separated:

  FILM      the film reorganises and adopts an allowed member
  IMPRINT   we are reading back the periodic pattern we just wrote

Both predict "the readout shows the commanded angle", because the commanded
angle IS a member. Commanding the MIDPOINT between two members separates them:

  readout lands near the commanded midpoint  -> IMPRINT
  readout snaps to a triad member            -> FILM

The midpoint is 30 deg from either member and the hit criterion is 15 deg, so
the two outcomes cannot both be satisfied.

  python analyse_offtriad.py L_before V_before L_after V_after want lam_template
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
import scale_tools as ST

SUPER = (150.0, 500.0)
NPERM = 300

ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__


def load(tag):
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
    a = sys.argv[1:]
    if len(a) < 6:
        print(__doc__)
        return
    Lb, Vb, La, Va = a[:4]
    want = float(a[4])
    lam_t = float(a[5])

    SLb, pxl, _ = load(Lb)
    SLa, _, _ = load(La)
    SVb, pxv, _ = load(Vb)
    SVa, _, _ = load(Va)
    tri, tt = g('pin_triad')(Lb, ref_fam=g('FAM_FILM'))
    tri = [float(t) for t in tri]
    dom = float(tri[int(np.argmax(np.asarray(tt['w'], float)))])
    near = min(tri, key=lambda t: ST.angle_between(want, t))

    print('=' * 80)
    print('OFF-TRIAD DIAGNOSTIC')
    print('=' * 80)
    print('  triad %s, incumbent %.0f deg' % ([int(t) for t in tri], dom))
    print('  commanded %.1f deg -- %.1f deg from the nearest member (%.0f)'
          % (want, ST.angle_between(want, near), near))
    print('  template period %.0f nm' % lam_t)
    print()
    print('  IMPRINT predicts the readout at %.1f deg' % want)
    print('  FILM    predicts the readout at %.0f or %.0f deg'
          % (near, min([t for t in tri if t != near],
                       key=lambda t: ST.angle_between(want, t))))
    print()

    print('1. BLIND super-band direction, panel interior')
    print('   %-8s %8s %9s %8s %8s | %9s %9s'
          % ('when', 'dir', 'period', 'aniso', 'p', 'off want', 'off member'))
    res = {}
    for lab, S in (('before', SLb), ('after', SLa)):
        dd, an, per, pv = ST.band_peak(interior(S, pxl), pxl, *SUPER,
                                       n_perm=NPERM)
        res[lab] = (dd, an, per, pv)
        nm = min(tri, key=lambda t: ST.angle_between(dd, t))
        print('   %-8s %8.1f %9.1f %8.2f %8.4f | %9.1f %9.1f (member %.0f)'
              % (lab, dd, per, an, pv, ST.angle_between(dd, want),
                 ST.angle_between(dd, nm), nm))
    da = res['after'][0]
    off_want = ST.angle_between(da, want)
    nm = min(tri, key=lambda t: ST.angle_between(da, t))
    off_mem = ST.angle_between(da, nm)

    print()
    print('2. MATCHED FILTER at the commanded angle vs at the members')
    print('   %-6s %-22s %9s %9s %8s %8s'
          % ('chan', 'tested at', 'before', 'after', 'z', 'p'))
    for ch, (Sb, Sa, px) in (('LDART', (SLb, SLa, pxl)),
                             ('VDART', (SVb, SVa, pxv))):
        tests = [('commanded %.0f deg' % want, want),
                 ('member %.0f deg' % near, near)]
        for lab, d in tests:
            ib = ST.matched_test(interior(Sb, px), px, d, lam_t)
            ia = ST.matched_test(interior(Sa, px), px, d, lam_t)
            cb = np.mean([ST.matched_amplitude(c, px, d, lam_t)
                          for c in corners(Sb, px)])
            ca = np.mean([ST.matched_amplitude(c, px, d, lam_t)
                          for c in corners(Sa, px)])
            print('   %-6s %-22s %9.2f %9.2f %+8.1f %8.4f   (corners x%.2f)'
                  % (ch, lab, ib[0], ia[0], ia[1], ia[2],
                     ca / max(cb, 1e-9)))

    print()
    print('=' * 80)
    print('VERDICT')
    print('=' * 80)
    if res['after'][3] >= 0.01:
        print('  The after-frame has NO significant direction (p = %.3f).'
              % res['after'][3])
        print('  The write did not order the interior; nothing to conclude.')
    elif off_want <= 15.0 and off_mem > 15.0:
        print('  Readout at %.1f deg: within %.1f deg of the COMMANDED angle'
              % (da, off_want))
        print('  and %.1f deg from any member.' % off_mem)
        print('  -> IMPRINT. The readout follows what was written, not the')
        print('     film. Every director result in the campaign that was')
        print('     commanded to a member is confounded and needs re-reading.')
    elif off_mem <= 15.0 and off_want > 15.0:
        print('  Readout at %.1f deg: snapped to member %.0f (%.1f deg off),'
              % (da, nm, off_mem))
        print('  and %.1f deg away from the commanded %.1f.' % (off_want, want))
        print('  -> THE FILM CHOSE. The template steers, but the film lands on')
        print('     its own allowed directions. The campaign readout measures')
        print('     the film.')
    else:
        print('  Readout at %.1f deg: %.1f from the command, %.1f from member'
              ' %.0f.' % (da, off_want, off_mem, nm))
        print('  -> AMBIGUOUS at the 15 deg criterion. Report both numbers.')


if __name__ == '__main__':
    main()
