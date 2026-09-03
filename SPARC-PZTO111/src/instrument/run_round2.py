# -*- coding: utf-8 -*-
"""run_round2.py -- replicate the decisive run, and find the AC crossover.

Screen 2 gave seven areas passing topography, but three have Lambda 307-310 nm,
which holds only 3.87-3.91 periods in the 1.2 um readout window and fails the
4-Lambda rule. The usable pool is four, and each raster angle is chosen so its
predicted destination is NOT the incumbent:

    (  0, 18)  triad 16/76/136  dom 76  Lambda 202
    ( 18,-18)  triad 16/76/136  dom 76  Lambda 270
    (-18,  0)  triad  9/69/129  dom 69  Lambda 199
    ( 12,-12)  triad 22/82/142  dom 22  Lambda 215

JOBS 1-2, REPLICATE THE DECISIVE RUN. The paper's central claim -- that the
raster selects an allowed variant rather than writing a pattern -- rests on one
off-triad run. These repeat it at **41 deg** rather than 46. Why 41: 46 is
equidistant from members 16 and 76, which maximises the pattern-vs-selection
separation but cannot say WHICH member the rule picks. 41 deg is 25 deg from
member 16 and 35 deg from member 76, so "nearest allowed orientation" predicts
16 unambiguously while "pattern" still predicts 41 -- a 25 deg separation
against a 15 deg criterion. Both areas sit on member 76, so a hit is also a
60 deg move.

JOBS 3-4, THE AC SIGN-PERIOD CROSSOVER. M32 found that AC at a 120 nm sign
period DISORDERS the film where a dose-matched DC raster aligns it, so the
field must hold one sign over a length far above 60 nm. These find where it
starts working: **800 nm** and **1600 nm** sign periods, both far above the
150-500 nm readout band so neither can imprint into the measurement. Both at
120 deg, against the DC 120 deg reference already measured (member 139, 0.2 deg
offset).
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A

LOGDIR = os.environ.get('TEMP', '/tmp')

JOBS = [
    dict(tag='offtriad_rep1', area=(0.0, 18.0), cost=6.2,
         env=dict(B3_MODE='dc', B3_ANG='41', B3_PITCH='0.03', B3_SPEED='0.5'),
         note='REPLICATE off-triad: raster 41 deg -> predicts member 16'),
    dict(tag='offtriad_rep2', area=(18.0, -18.0), cost=6.2,
         env=dict(B3_MODE='dc', B3_ANG='41', B3_PITCH='0.03', B3_SPEED='0.5'),
         note='REPLICATE off-triad: raster 41 deg -> predicts member 16'),
    dict(tag='ac800', area=(-18.0, 0.0), cost=6.2,
         env=dict(B3_MODE='ac', B3_ANG='120', B3_ACN='20', B3_PITCH='0.03',
                  B3_SPEED='0.5'),
         note='AC, 800 nm sign period -> predicts member 129'),
    dict(tag='ac1600', area=(12.0, -12.0), cost=6.2,
         env=dict(B3_MODE='ac', B3_ANG='120', B3_ACN='40', B3_PITCH='0.03',
                  B3_SPEED='0.5'),
         note='AC, 1600 nm sign period -> predicts member 142'),
]


def main():
    st = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                           encoding='utf-8'))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    used = float(st.get('total_write_min', 0.0))
    need = sum(j['cost'] for j in JOBS)
    print('=' * 78)
    print('ROUND 2  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    print('  S24: %.1f of %.0f used, %.1f left; round 2 needs %.1f'
          % (used, cap, cap - used, need))
    for j in JOBS:
        print('  %-15s (%+5.1f,%+5.1f) %5.1f min  %s'
              % (j['tag'], j['area'][0], j['area'][1], j['cost'], j['note']))
    if need > cap - used:
        print('  REFUSED: not enough headroom.')
        return
    if '--dry' in sys.argv:
        print('\nDRY: nothing run.')
        return

    for k, j in enumerate(JOBS):
        ax, ay = j['area']
        log = os.path.join(LOGDIR, 'r2_%d_%s.log' % (k + 1, j['tag']))
        print('\n' + '-' * 78)
        print('[%d/%d] %-15s (%+.1f,%+.1f)  %s'
              % (k + 1, len(JOBS), j['tag'], ax, ay, j['note']))
        if subprocess.call([sys.executable, '-u', 'instrument_free.py'],
                           cwd=HERE) != 0:
            print('       instrument busy; stopping the queue.')
            break
        env = dict(os.environ)
        env.update(j['env'])
        env.update(B3_X=str(ax), B3_Y=str(ay), B3_LABEL=j['tag'],
                   B3_BEFORE_L='', B3_BEFORE_V='', PYTHONIOENCODING='utf-8')
        t0 = time.time()
        with io.open(log, 'w', encoding='utf-8') as fh:
            rc = subprocess.call([sys.executable, '-u', 'block3_raster.py'],
                                 cwd=HERE, env=env, stdout=fh,
                                 stderr=subprocess.STDOUT)
        txt = io.open(log, encoding='utf-8', errors='replace').read()
        key = ''
        for line in txt.split('\n'):
            L = line.strip()
            if L.startswith('->') or L.startswith('director '):
                key = L
        print('       rc=%d in %.1f min | %s'
              % (rc, (time.time() - t0) / 60.0, key[:100]))

    st2 = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                            encoding='utf-8'))
    print('\n' + '=' * 78)
    print('ROUND 2 COMPLETE %s   S24 %.1f of %.0f'
          % (time.strftime('%H:%M'), st2.get('total_write_min', 0.0), cap))


if __name__ == '__main__':
    main()
