# -*- coding: utf-8 -*-
"""round3_report.py -- assemble the dose and speed series from the round 3 logs.

Parses the block3_raster logs, pulls the DELIVERED dose (computed from the built
path, never from the design formula) and the before/after directors, and adds a
matched-filter measurement of each after-frame so the landing angles are
comparable with the sub-degree numbers in section 3.8.

MEASUREMENT-FREE.
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
import scale_tools as ST
from fine_angle import peak_angle, interior, wrap180

LOGDIR = os.environ.get('TEMP', '/tmp')
SUPER = (150.0, 500.0)

# reference point from sections 3.2-3.3, for the top of the dose series
REFERENCE = dict(tag='reference', pitch=30.0, speed=0.5, sigma=686.0,
                 ang=41.0, member=16.5, after=18.8, aniso=18.60, p=0.0050,
                 frame='PZTO_LDART_0069.ibw')


def parse(path):
    t = io.open(path, encoding='utf-8', errors='replace').read()
    d = {}
    m = re.search(r'sigma (\d+) \(design (\d+)', t)
    if m:
        d['sigma'] = float(m.group(1))
        d['sigma_design'] = float(m.group(2))
    m = re.search(r'raster along ([\d.]+) deg; nearest triad member (\d+)', t)
    if m:
        d['ang'] = float(m.group(1))
        d['member'] = float(m.group(2))
    m = re.search(r'phi0 = ([\d.]+) deg', t)
    if m:
        d['phi0'] = float(m.group(1))
    sup = re.findall(r'super:\s+([\d.]+) deg\s+([\d.]+) nm\s+aniso\s+([\d.]+)'
                     r'\s+p ([\d.]+)', t)
    if len(sup) >= 2:
        d['before'] = tuple(float(x) for x in sup[0])
        d['after'] = tuple(float(x) for x in sup[-1])
    m = re.search(r'after LDART -> (\S+\.ibw)', t)
    if m:
        d['frame'] = m.group(1)
    m = re.search(r'(\d+\.\d+) min at ([\d.]+) um/s', t)
    if m:
        d['minutes'] = float(m.group(1))
        d['speed'] = float(m.group(2))
    m = re.search(r'holds ([\d.]+) Lambda at (\d+) nm', t)
    if m:
        d['periods'] = float(m.group(1))
        d['lam'] = float(m.group(2))
    d['aligned'] = 'Rule holds' in t
    return d


def main():
    logs = sorted(glob.glob(os.path.join(LOGDIR, 'r3_*.log')))
    if not logs:
        print('no round 3 logs yet.')
        return
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__

    print('=' * 96)
    print('ROUND 3 REPORT')
    print('=' * 96)
    rows = []
    for L in logs:
        tag = os.path.basename(L)[3:-4]
        d = parse(L)
        if 'after' not in d:
            print('  %-14s incomplete' % tag)
            continue
        fine = np.nan
        if d.get('frame'):
            try:
                dd, hh = g('ibw')(d['frame'])
                S, _, _ = g('signed')(dd)
                px = float(hh['ScanSize']) * 1e6 / S.shape[0] * 1000.0
                I = interior(S, px)
                d0, an, lam, pv = ST.band_peak(I, px, *SUPER, n_perm=200)
                fine = peak_angle(I, px, d0, lam)[0]
            except Exception as e:
                print('    (%s: %s)' % (d['frame'], e))
        d.update(tag=tag, fine=fine)
        rows.append(d)

    print('\n%-14s %6s %6s %7s %8s %8s %7s %7s %6s %s'
          % ('run', 'pitch', 'speed', 'sigma', 'before', 'after', 'fine',
             'member', 'aniso', 'p'))
    for d in rows:
        pitch = 10.0 / (d['sigma'] * d.get('speed', 0.5)) * 1000.0 \
            if d.get('sigma') else float('nan')
        print('%-14s %6.0f %6.2f %7.0f %8.1f %8.1f %7.2f %7.1f %6.2f %.4f'
              % (d['tag'], pitch, d.get('speed', np.nan), d.get('sigma', np.nan),
                 d['before'][0], d['after'][0], d['fine'],
                 d.get('member', np.nan), d['after'][2], d['after'][3]))

    dose = [d for d in rows if d.get('speed') == 0.5 and 'dose' in d['tag']]
    if dose:
        print('\n  DOSE SERIES at 0.5 um/s, all commanded at 41 deg:')
        for d in sorted(dose, key=lambda x: -x['sigma']):
            off = abs(wrap180(d['after'][0] - d['member']))
            print('    sigma %4.0f -> director %5.1f, %4.1f deg from member '
                  '%.0f, aniso %5.2f, p %.4f  %s'
                  % (d['sigma'], d['after'][0], off, d['member'],
                     d['after'][2], d['after'][3],
                     'ALIGNED' if d['aligned'] else 'not aligned'))
        print('    reference sigma  686 -> director  18.8,  2.2 deg from '
              'member 16, aniso 18.60, p 0.0050  ALIGNED')

    sp = [d for d in rows if 'speed' in d['tag']]
    lo = [d for d in rows if d['tag'].startswith('dose178')]
    if sp and lo:
        a, b = lo[0], sp[0]
        print('\n  SPEED CONTROL at matched dose:')
        for d in (a, b):
            print('    %.1f um/s, sigma %.0f -> director %.1f (fine %.2f), '
                  'aniso %.2f, p %.4f'
                  % (d['speed'], d['sigma'], d['after'][0], d['fine'],
                     d['after'][2], d['after'][3]))
        print('    dose differs by %.0f %%, speed by %.1fx'
              % (100 * abs(a['sigma'] - b['sigma']) / a['sigma'],
                 b['speed'] / a['speed']))

    rw = [d for d in rows if d['tag'].startswith('rw2')]
    if len(rw) == 2:
        s1, s2 = sorted(rw, key=lambda x: x['tag'])
        if np.isfinite(s1['fine']) and np.isfinite(s2['fine']):
            sep = abs(wrap180(s2['fine'] - s1['fine']))
            print('\n  SECOND REWRITE PAIR (same area, reference cancels):')
            print('    step 1 %.2f deg, step 2 %.2f deg -> separation %.2f'
                  % (s1['fine'], s2['fine'], sep))
            print('    shortfall from 60.00 deg: %+.2f  (first pair: -2.83)'
                  % (sep - 60.0))
            print('    anisotropy %.2f -> %.2f' % (s1['after'][2],
                                                   s2['after'][2]))


if __name__ == '__main__':
    main()
