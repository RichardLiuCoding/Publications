# -*- coding: utf-8 -*-
"""analyse_raster.py -- read the night's raster runs and decide what they show.

FREE: analysis only, from the logs and the frames they name.

For each run: the raster angle, the triad, the incumbent, the director before
and after, and which of the two competing hypotheses the result supports.

  SELECTION   the director lands on an ALLOWED orientation, and specifically on
              the one nearest the raster angle
  PATTERN     the director lands on the RASTER ANGLE itself, allowed or not

For rasters commanded AT an allowed orientation these predict the same thing
and the run is uninformative on that question -- it only tests the rule. For a
raster commanded BETWEEN allowed orientations they differ by 30 deg and the
run is decisive.
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


def corners(S, px, size=0.60):
    n = S.shape[0]
    k = int(round(size * 1000.0 / px))
    return [S[0:k, 0:k], S[0:k, n - k:n], S[n - k:n, 0:k], S[n - k:n, n - k:n]]


def parse(path):
    t = io.open(path, encoding='utf-8', errors='replace').read()
    out = {'log': os.path.basename(path)}
    m = re.search(r'BLOCK 3\s+(\w+) raster\s+(\S*)', t)
    if m:
        out['mode'], out['tag'] = m.group(1).lower(), m.group(2)
    m = re.search(r'triad \[([\d,\s]+)\], dominant ([\d.]+) deg, '
                  r'modulation ([\d.]+)', t)
    if m:
        out['tri'] = [float(x) for x in m.group(1).split(',')]
        out['dom'] = float(m.group(2))
        out['mod'] = float(m.group(3))
    m = re.search(r'raster along ([-\d.]+) deg', t)
    if m:
        out['ang'] = float(m.group(1))
    m = re.search(r'sigma\s+(\d+)\s*\(design', t)
    if m:
        out['sigma'] = float(m.group(1))
    m = re.search(r'roughness ([\d.]+) nm, 1-99% range ([\d.]+)', t)
    if m:
        out['rough'], out['p2p'] = float(m.group(1)), float(m.group(2))
    m = re.search(r'before (\S+) / (\S+)\s+after (\S+) / (\S+)', t)
    if m:
        out['Lb'], out['Vb'], out['La'], out['Va'] = m.groups()
    return out


def main():
    logs = sorted(glob.glob(os.path.join(os.environ.get('TEMP', '/tmp'),
                                         'night_*.log')))
    if not logs:
        print('no night_*.log found')
        return
    print('=' * 100)
    print('RASTER RUNS')
    print('=' * 100)
    rows = []
    for lp in logs:
        r = parse(lp)
        if 'La' not in r:
            print('  %-22s incomplete (%s)' % (r.get('log'), 'no after-frame'))
            continue
        try:
            Sb, px, _ = load(r['Lb'])
            Sa, _, _ = load(r['La'])
        except Exception as e:
            print('  %-22s frames unreadable: %s' % (r['log'], e))
            continue
        db, ab, pb, pvb = ST.band_peak(interior(Sb, px), px, *SUPER,
                                       n_perm=NPERM)
        da, aa, pa, pva = ST.band_peak(interior(Sa, px), px, *SUPER,
                                       n_perm=NPERM)
        tri = r.get('tri', [16., 76., 136.])
        ang = r.get('ang', 0.0)
        near = min(tri, key=lambda t: ST.angle_between(t, ang))
        off_mem = ST.angle_between(da, near)
        off_ang = ST.angle_between(da, ang)
        off_any = min(ST.angle_between(da, t) for t in tri)
        # corner control
        cb = np.mean([np.std(c) for c in corners(Sb, px)])
        ca = np.mean([np.std(c) for c in corners(Sa, px)])
        r.update(db=db, pvb=pvb, da=da, aa=aa, pva=pva, near=near,
                 off_mem=off_mem, off_ang=off_ang, off_any=off_any,
                 corner=ca / max(cb, 1e-9), moved=ST.angle_between(da, db))
        rows.append(r)

    print('%-16s %-4s %5s %6s %7s %8s %8s %7s %7s %7s  %s'
          % ('run', 'mode', 'ang', 'incumb', 'before', 'after', 'p after',
             'to memb', 'to ang', 'moved', 'corners'))
    for r in rows:
        print('%-16s %-4s %5.0f %6.0f %7.1f %8.1f %8.4f %7.1f %7.1f %7.1f  %.2f'
              % (r.get('tag', '?'), r.get('mode', '?'), r.get('ang', 0),
                 r.get('dom', 0), r['db'], r['da'], r['pva'], r['off_mem'],
                 r['off_ang'], r['moved'], r['corner']))

    print()
    print('=' * 100)
    print('THE DECISIVE RUN: raster commanded BETWEEN allowed orientations')
    print('=' * 100)
    dec = [r for r in rows if r.get('tag', '').startswith('offtriad')]
    if not dec:
        print('  not present yet')
    for r in dec:
        tri = r['tri']
        print('  triad %s, raster %.0f deg -- %.1f deg from the nearest '
              'allowed orientation (%.0f)'
              % ([int(t) for t in tri], r['ang'],
                 ST.angle_between(r['ang'], r['near']), r['near']))
        print('  director %.1f -> %.1f deg (p %.4f), corners x%.2f'
              % (r['db'], r['da'], r['pva'], r['corner']))
        print('     distance to the nearest ALLOWED orientation : %5.1f deg'
              % r['off_any'])
        print('     distance to the RASTER angle                : %5.1f deg'
              % r['off_ang'])
        if r['pva'] >= 0.01:
            print('  -> no significant direction after; inconclusive.')
        elif r['off_any'] <= 15 and r['off_ang'] > 15:
            print('  -> SELECTION. The raster steers the film onto an ALLOWED')
            print('     orientation, not onto its own axis. The raster result')
            print('     is imprint-free and the manuscript stands.')
        elif r['off_ang'] <= 15 and r['off_any'] > 15:
            print('  -> PATTERN. The readout follows the raster axis to a')
            print('     forbidden orientation, exactly as the pulse lattice')
            print('     does. There is NO imprint-free result in the project')
            print('     and the manuscript must be rebuilt around patterning.')
        else:
            print('  -> AMBIGUOUS: %.1f from an allowed orientation, %.1f from'
                  ' the raster angle.' % (r['off_any'], r['off_ang']))

    print()
    print('=' * 100)
    print('THE ANGLE RULE: does the director go to the member nearest the '
          'raster?')
    print('=' * 100)
    ok = [r for r in rows if r.get('tag', '').startswith(('angle', 'ac', 'rw'))]
    for r in ok:
        v = ('HIT' if (r['pva'] < 0.01 and r['off_mem'] <= 15) else
             ('no direction' if r['pva'] >= 0.01 else 'MISS'))
        print('  %-14s raster %3.0f -> predicted %3.0f, got %5.1f (%4.1f off)'
              '  moved %4.1f deg  %s'
              % (r.get('tag'), r['ang'], r['near'], r['da'], r['off_mem'],
                 r['moved'], v))
    hits = [r for r in ok if r['pva'] < 0.01 and r['off_mem'] <= 15]
    if ok:
        print('\n  %d of %d runs landed on the orientation nearest the raster'
              % (len(hits), len(ok)))

    print()
    print('AC versus DC at matched dose:')
    for r in rows:
        if r.get('mode') in ('ac', 'dc') and r.get('tag') in ('ac0', 'angle0'):
            print('  %-8s %-3s raster %3.0f -> %5.1f (%4.1f from predicted '
                  '%3.0f), aniso %5.2f, p %.4f'
                  % (r['tag'], r['mode'], r['ang'], r['da'], r['off_mem'],
                     r['near'], r['aa'], r['pva']))


if __name__ == '__main__':
    main()
