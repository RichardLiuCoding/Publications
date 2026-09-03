# -*- coding: utf-8 -*-
"""analyse_crosstalk.py -- did a written panel steal its neighbour's director?

M21 noticed that both failed panels in the campaign landed on the director
commanded for the OTHER panel in the same frame. That is either lateral
crosstalk between written regions, or a coincidence: with three triad members a
random miss lands near the neighbour's target about one time in three.

This reads results_templates.csv, pairs the panels by run, classifies each pair,
and reports the defection rate BY PANEL GAP -- which is the variable the round-3
queue deliberately varied while holding dose, targets and everything else fixed.

Classification per panel:
  HIT        within 15 deg of its own commanded director
  DEFECT     more than 15 deg from its own, but within 15 deg of its NEIGHBOUR's
  OTHER      missed both

A binomial p-value is reported for the defect count against the 1/3 chance rate,
because two-out-of-two proves nothing and the honest thing is to say so with a
number.
"""
from __future__ import annotations

import csv
import io
import os
import sys
from math import comb

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, 'results_templates.csv')
WIN_DEFAULT = 1.4



def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]]."""
    n = a + b + c + d

    def pr(x):
        return (comb(a + b, x) * comb(c + d, a + c - x)) / comb(n, a + c)

    p0 = pr(a)
    tot = 0.0
    for k in range(0, min(a + b, a + c) + 1):
        if a + c - k < 0 or a + c - k > c + d:
            continue
        pk = pr(k)
        if pk <= p0 + 1e-12:
            tot += pk
    return min(1.0, tot)


def cdist(a, b):
    return abs((float(a) - float(b) + 90.0) % 180.0 - 90.0)


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding='utf-8')))

    # Panel gap is not a csv column, but the campaign logs print it per job.
    # Recover it so the defection rate can be split by gap -- the variable the
    # round-3 queue varied while holding dose and targets fixed.
    import glob
    import re
    gap_by_area = {}
    logdir = os.environ.get('TEMP', '/tmp')
    for lg in glob.glob(os.path.join(logdir, 'campaign*.log')):
        txt = io.open(lg, encoding='utf-8', errors='ignore').read()
        cur = None
        for line in txt.split(chr(10)):
            m = re.search(r'\] \w+ at \(([-+0-9.]+),([-+0-9.]+)\)', line)
            if m:
                cur = (round(float(m.group(1)), 1), round(float(m.group(2)), 1))
            m = re.search(r'gap ([0-9.]+) um', line)
            if m and cur:
                gap_by_area[cur] = float(m.group(1))
    if gap_by_area:
        print('  gaps recovered from campaign logs: %s'
              % sorted(set(gap_by_area.values())))

    runs = {}
    for r in rows:
        runs.setdefault((r['stamp'], r['area_x'], r['area_y']), []).append(r)

    print('=' * 74)
    print('CROSSTALK: does a panel adopt its neighbour\'s director?')
    print('=' * 74)

    recs = []
    for key, v in sorted(runs.items()):
        if len(v) != 2:
            continue
        a, b = v
        if a['want'] in ('', 'None') or b['want'] in ('', 'None'):
            continue
        # only runs where the two panels were sent to DIFFERENT members can
        # show a defection at all
        if cdist(a['want'], b['want']) < 20:
            continue
        lam = float(a['lam_nm']) / 1000.0
        # panel size is not in the csv; infer the gap from the panel centres
        # when available, else assume the default geometry
        for p, other in ((a, b), (b, a)):
            own = cdist(p['dom_after'], p['want'])
            nbr = cdist(p['dom_after'], other['want'])
            cls = 'HIT' if own <= 15 else ('DEFECT' if nbr <= 15 else 'OTHER')
            ak = (round(float(key[1]), 1), round(float(key[2]), 1))
            recs.append(dict(run=key[0], area='(%s,%s)' % (key[1][:5], key[2][:5]),
                             panel=p['panel'], lam=lam * 1000, cls=cls,
                             own=own, nbr=nbr, sigma=float(p['sigma']),
                             gap=gap_by_area.get(ak, 0.6),
                             nsites=int(p['n_sites'])))

    if not recs:
        print('  no two-panel runs with different targets yet.')
        return

    # panel size from site count is unreliable; use the run stamp to split
    # narrow (default 1.4 um) from wide (1.2 um) via the campaign log if present
    print('\n  %-14s %-11s %-6s %-7s %7s %7s  %s'
          % ('run', 'area', 'panel', 'sigma', 'off own', 'off nbr', 'class'))
    for r in recs:
        print('  %-14s %-11s %-6s %-7.0f %7.1f %7.1f  %s'
              % (r['run'], r['area'], r['panel'], r['sigma'],
                 r['own'], r['nbr'], r['cls']))

    n = len(recs)
    nd = sum(1 for r in recs if r['cls'] == 'DEFECT')
    nh = sum(1 for r in recs if r['cls'] == 'HIT')
    no = sum(1 for r in recs if r['cls'] == 'OTHER')
    print('\n  %d panels in different-target runs: %d hit, %d defect, %d other'
          % (n, nh, nd, no))

    miss = nd + no
    if miss:
        # of the panels that missed, how many landed on the neighbour?
        p_chance = 0.5     # a miss lands on one of the two OTHER members
        pv = sum(comb(miss, k) * p_chance ** miss for k in range(nd, miss + 1))
        print('  of %d misses, %d landed on the neighbour\'s member.' % (miss, nd))
        print('  under chance (a miss picks either other member with p=0.5),')
        print('  P(>= %d of %d) = %.3f' % (nd, miss, pv))
        if pv < 0.05:
            print('  -> significant: misses are NOT random, they go to the')
            print('     neighbour. That is crosstalk.')
        else:
            print('  -> NOT significant at this n. The pattern is suggestive')
            print('     and no more; more different-target runs are needed.')
    else:
        print('  no misses at all: nothing to explain, and crosstalk -- if it')
        print('  exists -- did not bite in this set.')

    # split by gap -- the controlled variable
    gaps = sorted(set(round(r['gap'], 1) for r in recs))
    if len(gaps) > 1:
        print('')
        print('  === DEFECTION RATE BY PANEL GAP (the controlled test) ===')
        for gp in gaps:
            sub = [r for r in recs if round(r['gap'], 1) == gp]
            d = sum(1 for r in sub if r['cls'] == 'DEFECT')
            print('    gap %.1f um: %d panels, %d defect (%.0f%%)'
                  % (gp, len(sub), d, 100.0 * d / max(1, len(sub))))
        nar = [r for r in recs if round(r['gap'], 1) <= 0.7]
        wid = [r for r in recs if round(r['gap'], 1) > 0.7]
        dn = sum(1 for r in nar if r['cls'] == 'DEFECT')
        dw = sum(1 for r in wid if r['cls'] == 'DEFECT')
        if nar and wid:
            a, b = dn, len(nar) - dn
            c, d = dw, len(wid) - dw
            print('    narrow %d/%d defect vs wide %d/%d' % (a, a + b, c, c + d))
            pf = fisher_2x2(a, b, c, d)
            rate = a / float(a + b) if (a + b) else 0.0
            pnull = (1.0 - rate) ** (c + d)
            print('    Fisher exact (2-sided) p = %.3f' % pf)
            print('    P(%d defects in %d wide | narrow rate %.0f%%) = %.2f'
                  % (c, c + d, 100 * rate, pnull))
            if pf < 0.05:
                print('    -> the gap MATTERS: defection rate falls with')
                print('       separation. That is crosstalk.')
            elif pnull > 0.2:
                print('    -> UNDERPOWERED, no conclusion. %d wide panels'
                      % (c + d))
                print('       cannot distinguish a real drop from chance:')
                print('       seeing %d defections there is likely anyway.' % c)
                print('       The direction is right but this is NOT evidence.')
            else:
                print('    -> no significant difference between the gaps.')

    print('\n  NOTE ON POWER. A defection can only be seen in runs whose two')
    print('  panels were sent to DIFFERENT members. Runs where both panels')
    print('  share a target (dose, shear) are blind to it by construction and')
    print('  are excluded above, not counted as successes.')


if __name__ == '__main__':
    main()
