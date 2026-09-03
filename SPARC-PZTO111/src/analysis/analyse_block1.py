# -*- coding: utf-8 -*-
"""analyse_block1.py -- did the write create structure, and in which channel?

FREE: analysis only, on frames already taken.

The design has an internal control in every frame. The panel is 1.2 um centred
in a 2.5 um field, so:

    INTERIOR   central 1.0 um   -- written
    SURROUND   beyond 1.5 um    -- not written, same frame, same tune, same tip

and every quantity is measured in both. A change that appears in the interior
and not the surround is the write; a change that appears in both is the tune,
the tip or the day.

Three questions, in order of what they would change:

 1. IN-PLANE. Did the super-domain director rotate to the commanded member,
    and only inside the panel?
 2. OUT-OF-PLANE. Is there a P_z modulation at the commanded wavevector after
    the write, where there was none before? T3's selection term needs one, and
    on virgin film there is none to 5 pm. If the write CREATES it, selection is
    self-reinforcing rather than a coupling to pre-existing order.
 3. NANO-DOMAINS. Did an independent short-period structure appear -- one that
    is significant, off the fast scan axis, and not the second harmonic of the
    super-domain lamellae (PITFALLS 21.5, 21.6)?

  python analyse_block1.py L_before V_before L_after V_after [want_deg]
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
HARM = (90.0, 150.0)
FINE = (18.0, 90.0)
IN_HALF = 0.50           # central 1.0 um
OUT_INNER = 0.75         # surround starts beyond 1.5 um
NPERM = 200

ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__


def load(tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0, r12


def interior(S, px):
    n = S.shape[0]
    hp = int(round(IN_HALF * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def surround(S, px):
    """The border, packed into a 1-D-safe 2-D array by zeroing the middle.

    Zeroing rather than cropping keeps the array square and the frequency grid
    identical to the interior's, so the two are directly comparable.
    """
    n = S.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    r = np.maximum(np.abs(xx - c), np.abs(yy - c)) * px / 1000.0
    out = S.copy()
    out[r < OUT_INNER] = 0.0
    return out


def is_real_nano(fine, sup, tri):
    """Significant, off the fast axis, and not the super-domain harmonic."""
    dn, an, pn, pv = fine
    ds, _as, ps, pvs = sup
    if pv != pv or pv >= 0.01:
        return False, 'not significant (p = %.3f)' % pv
    if ST.angle_between(dn, 0.0) < 12.0:
        return False, 'within %.0f deg of the fast scan axis' \
            % ST.angle_between(dn, 0.0)
    if (ps == ps and pn == pn and abs(pn / (ps / 2.0) - 1.0) < 0.25
            and ST.angle_between(dn, ds) < 15.0):
        return False, 'second harmonic of the %.0f nm lamellae' % ps
    near = min(tri, key=lambda t: ST.angle_between(dn, t))
    return True, ('REAL: %.0f nm at %.0f deg (triad %.0f, off %.0f)'
                  % (pn, dn, near, ST.angle_between(dn, near)))


def main():
    a = sys.argv[1:]
    if len(a) < 4:
        print(__doc__)
        return
    Lb, Vb, La, Va = a[:4]
    want = float(a[4]) if len(a) > 4 else None

    SLb, pxl, _ = load(Lb)
    SVb, pxv, _ = load(Vb)
    SLa, _, _ = load(La)
    SVa, _, _ = load(Va)
    tri, tt = g('pin_triad')(Lb, ref_fam=g('FAM_FILM'))
    tri = [float(t) for t in tri]
    dom = float(tri[int(np.argmax(np.asarray(tt['w'], float)))])
    lam = ST.band_period(SLb, pxl, dom, *SUPER)
    if want is None:
        want = float(min([t for t in tri if ST.angle_between(t, dom) > 45.0],
                         key=lambda t: min(t, 180.0 - t)))
    print('=' * 78)
    print('BLOCK 1 READOUT   triad %s   incumbent %.0f   commanded %.0f   '
          'Lambda %.0f nm' % ([int(t) for t in tri], dom, want, lam))
    print('=' * 78)

    # ------------------------------------------------- 1. in-plane director
    print('\n1. IN-PLANE super-domain director (LDART, %.0f-%.0f nm band)'
          % SUPER)
    print('   %-10s %-8s %8s %9s %8s %8s  %s'
          % ('region', 'when', 'dir', 'period', 'aniso', 'p', 'vs commanded'))
    res = {}
    for rname, fn in (('interior', interior), ('surround', surround)):
        for wname, S in (('before', SLb), ('after', SLa)):
            dd, an, per, pv = ST.band_peak(fn(S, pxl), pxl, *SUPER,
                                           n_perm=NPERM)
            res[(rname, wname)] = (dd, an, per, pv)
            off = ST.angle_between(dd, want) if dd == dd else float('nan')
            print('   %-10s %-8s %8.1f %9.1f %8.2f %8.3f  %6.1f deg%s'
                  % (rname, wname, dd, per, an, pv, off,
                     '  ON TARGET' if off <= 15 else ''))
    di = ST.angle_between(res[('interior', 'before')][0],
                          res[('interior', 'after')][0])
    do = ST.angle_between(res[('surround', 'before')][0],
                          res[('surround', 'after')][0])
    print('   director moved: interior %.1f deg, surround %.1f deg' % (di, do))
    on = ST.angle_between(res[('interior', 'after')][0], want) <= 15.0
    if on and do < 15.0:
        print('   -> THE PANEL ROTATED TO THE COMMANDED MEMBER AND THE '
              'SURROUND DID NOT.')
    elif on:
        print('   -> panel on target, but the surround moved too (%.0f deg): '
              'not localised' % do)
    else:
        print('   -> the panel did NOT reach the commanded member.')

    # ------------------------------------------------- 2. P_z at the template Q
    print('\n2. OUT-OF-PLANE modulation at the commanded wavevector')
    print('   (VDART, matched filter at %.0f deg / %.0f nm)' % (want, lam))
    print('   %-10s %-8s %9s %8s %9s %10s' %
          ('region', 'when', 'amp (pm)', 'z', 'p', 'null sd'))
    pz = {}
    for rname, fn in (('interior', interior), ('surround', surround)):
        for wname, S in (('before', SVb), ('after', SVa)):
            amp, z, p, sd = ST.matched_test(fn(S, pxv), pxv, want, lam)
            pz[(rname, wname)] = (amp, z, p, sd)
            print('   %-10s %-8s %9.2f %+8.1f %9.4f %10.2f'
                  % (rname, wname, amp, z, p, sd))
    ib, ia = pz[('interior', 'before')], pz[('interior', 'after')]
    sb, sa = pz[('surround', 'before')], pz[('surround', 'after')]
    print('   interior change %+.2f pm (z %+.1f -> %+.1f), '
          'surround change %+.2f pm'
          % (ia[0] - ib[0], ib[1], ia[1], sa[0] - sb[0]))
    if ia[2] < 0.01 and ib[2] >= 0.01 and sa[2] >= 0.01:
        print('   -> P_z MODULATION CREATED BY THE WRITE, at the template')
        print('      wavevector, inside the panel only. The template makes')
        print('      the very modulation the selection term couples to.')
    elif ia[2] < 0.01 and ib[2] < 0.01:
        print('   -> P_z was already modulated here before the write.')
    elif ia[2] >= 0.01:
        print('   -> still NO P_z modulation at Q after writing. On this film')
        print('      the selection term cannot be -int(P_z E_z).')

    # ------------------------------------------------------ 3. nano-domains
    print('\n3. NANO-DOMAINS: an independent short-period structure?')
    print('   %-10s %-8s %8s %9s %8s %8s  %s'
          % ('region', 'when', 'dir', 'period', 'aniso', 'p', 'verdict'))
    for chan, (Sb_, Sa_, px) in (('LDART', (SLb, SLa, pxl)),
                                 ('VDART', (SVb, SVa, pxv))):
        print('   -- %s --' % chan)
        for rname, fn in (('interior', interior), ('surround', surround)):
            for wname, S in (('before', Sb_), ('after', Sa_)):
                sup = ST.band_peak(fn(S, px), px, *SUPER, n_perm=NPERM)
                fine = ST.band_peak(fn(S, px), px, *FINE, n_perm=NPERM)
                ok, why = is_real_nano(fine, sup, tri)
                print('   %-10s %-8s %8.1f %9.1f %8.2f %8.3f  %s'
                      % (rname, wname, fine[0], fine[2], fine[1], fine[3],
                         why))

    print('\n' + '=' * 78)
    print('frames: before %s / %s   after %s / %s' % (Lb, Vb, La, Va))


if __name__ == '__main__':
    main()
