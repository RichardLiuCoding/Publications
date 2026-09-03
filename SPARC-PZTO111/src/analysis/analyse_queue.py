# -*- coding: utf-8 -*-
"""analyse_queue.py -- the five 2.5 um panels, one table.

FREE: analysis only.

THE QUESTION. Block 1 found that after a commensurate write both channels
carry a modulation at the written wavevector, where the virgin film had one
only in-plane (M24). Two explanations:

  IMPRINT      the template alternates polarity every Lambda/2, so each +- site
               simply wrote its own patch of P_z. No cooperation from the film
               is needed, and the result must appear at the TEMPLATE's own
               wavevector whatever the film's period is.
  COOPERATIVE  the film reorganises, which requires the template to match the
               film's own periodicity.

They differ on ONE panel: the incommensurate control at (-4,0), written with a
sign period of 328 nm into film whose own period is 253 nm. Under IMPRINT the
P_z modulation appears at 328 nm. Under COOPERATIVE it does not appear at all.

Everything is measured with the matched filter at a KNOWN direction and period,
with the four corner patches of the same frame as the unwritten control. The
corners are used for CHANGE, not level: at 0.62 um they hold too few periods
for an absolute amplitude to mean much.
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
FINE = (18.0, 90.0)
IN_HALF = 0.50
CORNER = 0.62
NPERM = 200

# area, triad, commanded, TEMPLATE Lambda (nm), film Lambda (nm), sigma, frames
JOBS = [
    dict(area='( 0, 0)', tri=[16, 76, 136], want=16.5, lam_t=219.0,
         lam_f=224.0, sigma=133, note='commensurate',
         Lb='PZTO_LDART_0000.ibw', Vb='PZTO_VDART_0000.ibw',
         La='PZTO_LDART_0001.ibw', Va='PZTO_VDART_0001.ibw'),
    dict(area='(+4, 0)', tri=[4, 64, 124], want=4.0, lam_t=225.0,
         lam_f=225.0, sigma=122, note='commensurate, repeat',
         Lb='PZTO_LDART_0002.ibw', Vb='PZTO_VDART_0002.ibw',
         La='PZTO_LDART_0003.ibw', Va='PZTO_VDART_0003.ibw'),
    dict(area='(-4, 0)', tri=[19, 79, 139], want=19.0, lam_t=328.0,
         lam_f=253.0, sigma=130, note='INCOMMENSURATE q = 1.3 Q',
         Lb='PZTO_LDART_0004.ibw', Vb='PZTO_VDART_0004.ibw',
         La='PZTO_LDART_0005.ibw', Va='PZTO_VDART_0005.ibw'),
    dict(area='( 0,+4)', tri=[22, 82, 142], want=21.5, lam_t=242.0,
         lam_f=242.0, sigma=53, note='commensurate, low dose',
         Lb='PZTO_LDART_0006.ibw', Vb='PZTO_VDART_0006.ibw',
         La='PZTO_LDART_0007.ibw', Va='PZTO_VDART_0007.ibw'),
    dict(area='( 0,-4)', tri=[16, 76, 136], want=16.5, lam_t=251.0,
         lam_f=251.0, sigma=263, note='commensurate, high dose',
         Lb='PZTO_LDART_0008.ibw', Vb='PZTO_VDART_0008.ibw',
         La='PZTO_LDART_0009.ibw', Va='PZTO_VDART_0009.ibw'),
]

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


def corners(S, px):
    n = S.shape[0]
    k = int(round(CORNER * 1000.0 / px))
    return [S[0:k, 0:k], S[0:k, n - k:n], S[n - k:n, 0:k], S[n - k:n, n - k:n]]


def mt(S, px, d, per):
    return ST.matched_test(S, px, d, per)


def main():
    print('=' * 96)
    print('FIVE PANELS AT 2.5 um -- did the write create a modulation at the '
          'template wavevector?')
    print('=' * 96)

    rows = []
    for j in JOBS:
        SLb, pxl, _ = load(j['Lb'])
        SLa, _, _ = load(j['La'])
        SVb, pxv, _ = load(j['Vb'])
        SVa, _, _ = load(j['Va'])
        d, per = j['want'], j['lam_t']

        # in-plane: where did the director actually go?
        da, aa, pera, pva = ST.band_peak(interior(SLa, pxl), pxl, *SUPER,
                                         n_perm=NPERM)
        db, ab, perb, pvb = ST.band_peak(interior(SLb, pxl), pxl, *SUPER,
                                         n_perm=NPERM)
        off = ST.angle_between(da, d)

        # matched filter at the TEMPLATE wavevector, both channels
        r = {}
        for ch, (Sb, Sa, px) in (('L', (SLb, SLa, pxl)),
                                 ('V', (SVb, SVa, pxv))):
            ib = mt(interior(Sb, px), px, d, per)
            ia = mt(interior(Sa, px), px, d, per)
            cb = np.mean([mt(c, px, d, per)[0] for c in corners(Sb, px)])
            ca = np.mean([mt(c, px, d, per)[0] for c in corners(Sa, px)])
            r[ch] = dict(ib=ib, ia=ia, cb=cb, ca=ca)
        j['res'] = r
        j['dir_before'] = (db, pvb)
        j['dir_after'] = (da, pera, pva, off)
        rows.append(j)

    # ------------------------------------------------------- in-plane table
    print('\n1. IN-PLANE: did the panel reach the commanded director?')
    print('   %-9s %-26s %7s %9s %9s %8s  %s'
          % ('area', 'template', 'want', 'got', 'period', 'p', 'offset'))
    for j in rows:
        da, pera, pva, off = j['dir_after']
        print('   %-9s %-26s %7.1f %9.1f %9.1f %8.3f  %5.1f deg %s'
              % (j['area'], j['note'], j['want'], da, pera, pva, off,
                 'HIT' if off <= 15 and pva < 0.01 else 'MISS'))

    # ---------------------------------------------------- the imprint test
    print('\n2. MODULATION AT THE TEMPLATE WAVEVECTOR (matched filter)')
    print('   amplitudes in pm; corners are the unwritten film in the same '
          'frame')
    print('   %-9s %-26s %-6s %8s %8s %7s %7s  %s'
          % ('area', 'template', 'chan', 'before', 'after', 'z aft',
             'p aft', 'corners b->a'))
    for j in rows:
        for ch in ('L', 'V'):
            r = j['res'][ch]
            flag = ''
            if r['ia'][2] < 0.01 and r['ib'][2] >= 0.01:
                flag = '  ** CREATED **'
            elif r['ia'][2] < 0.01:
                flag = '  (present before)'
            print('   %-9s %-26s %-6s %8.2f %8.2f %+7.1f %7.4f  %5.1f->%5.1f%s'
                  % (j['area'] if ch == 'L' else '',
                     j['note'] if ch == 'L' else '',
                     'LDART' if ch == 'L' else 'VDART',
                     r['ib'][0], r['ia'][0], r['ia'][1], r['ia'][2],
                     r['cb'], r['ca'], flag))
        print()

    # --------------------------------------------------------- the verdict
    print('=' * 96)
    print('VERDICT')
    print('=' * 96)
    inc = [j for j in rows if 'INCOMM' in j['note']][0]
    com = [j for j in rows if 'INCOMM' not in j['note']]
    print('\nCOMMENSURATE panels (%d), P_z at the template wavevector:' % len(com))
    for j in com:
        v = j['res']['V']
        print('   %s sigma %-4d : %6.2f -> %6.2f pm   z %+6.1f   p %.4f'
              % (j['area'], j['sigma'], v['ib'][0], v['ia'][0], v['ia'][1],
                 v['ia'][2]))
    v = inc['res']['V']
    print('\nINCOMMENSURATE panel, same dose, P_z at the TEMPLATE wavevector:')
    print('   %s sigma %-4d : %6.2f -> %6.2f pm   z %+6.1f   p %.4f'
          % (inc['area'], inc['sigma'], v['ib'][0], v['ia'][0], v['ia'][1],
             v['ia'][2]))
    # and at the FILM's wavevector, which the template did NOT match
    SLa, pxl, _ = load(inc['La'])
    SVa, pxv, _ = load(inc['Va'])
    SVb, _, _ = load(inc['Vb'])
    fb = mt(interior(SVb, pxv), pxv, inc['want'], inc['lam_f'])
    fa = mt(interior(SVa, pxv), pxv, inc['want'], inc['lam_f'])
    print('   and at the FILM period (%.0f nm, which the template missed):'
          % inc['lam_f'])
    print('            %6.2f -> %6.2f pm   z %+6.1f   p %.4f'
          % (fb[0], fa[0], fa[1], fa[2]))
    print()
    if v['ia'][2] < 0.01:
        print('  -> P_z appears at the TEMPLATE wavevector even when it does')
        print('     NOT match the film. That is an IMPRINT: the alternating')
        print('     bias writes its own pattern, and commensurability is not')
        print('     required for it. The modulation is a product of writing,')
        print('     not evidence of a cooperative film response.')
    else:
        print('  -> NO P_z at the template wavevector when q != Q, at matched')
        print('     dose and matched voltage. The modulation is NOT a simple')
        print('     bias imprint: it appears only when the template matches')
        print('     the film. That is a COOPERATIVE response.')


if __name__ == '__main__':
    main()
