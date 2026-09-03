# -*- coding: utf-8 -*-
"""run_afternoon.py -- the three questions left open at 14:00 on 29 August.

Each job is its own process so a failure costs one job, not the queue.

  1. ROTATED POLING. M26 showed a spatially uniform +V/-V write ordering the
     film onto the triad member nearest the raster direction (0 deg -> member
     16). That is equally consistent with a film preference and with the write
     direction choosing the nearest member -- which is also M23's open
     question, and PITFALLS 21.6's fast-axis artefact. Rotating the raster to
     60 deg separates them:
        orders on member ~76  -> the attractor follows the WRITE (instrumental)
        orders on member ~16  -> the preference belongs to the FILM

  2. OFF-TRIAD REPEAT. The single most consequential test of the day rests on
     one panel. n = 2 is not much, but it is twice n = 1, and a pivotal claim
     should not rest on a single frame.

  3. HI-RES, FREE. 1.25 um at 512 px = 2.44 nm/px over regions already
     written, to push the fine band down to 15-45 nm -- below every lamellar
     harmonic and away from the ~75 nm fast-axis artefact that has swamped
     every nano-domain search so far.
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
    dict(kind='pole', script='block2_pole.py', area=(-8.0, -8.0),
         env=dict(B2_X='-8.0', B2_Y='-8.0', B2_ANG='60'),
         cost=4.70, note='uniform poling, raster rotated to 60 deg'),
    dict(kind='write', script='block1_write.py', area=(8.0, -8.0),
         env=dict(B1_X='8.0', B1_Y='-8.0', B1_SIGMA='133', B1_WANT='midpoint',
                  B1_OFFTRIAD='1', B1_BEFORE_L='', B1_BEFORE_V=''),
         cost=0.90, note='off-triad diagnostic, repeat'),
    dict(kind='image', script='hires.py', area=(8.0, 0.0),
         env=dict(HR_AREA='8,0', HR_C='1.25,1.25', HR_SIZE='1.25',
                  HR_LABEL='poled square, raster 0 deg'),
         cost=0.0, note='hi-res on the 0 deg poled square (free)'),
    dict(kind='image', script='hires.py', area=(-8.0, -8.0),
         env=dict(HR_AREA='-8,-8', HR_C='1.25,1.25', HR_SIZE='1.25',
                  HR_LABEL='poled square, raster 60 deg'),
         cost=0.0, note='hi-res on the 60 deg poled square (free)'),
]


def main():
    p = os.path.join(HERE, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    used = float(st.get('total_write_min', 0.0))
    need = sum(j['cost'] for j in JOBS)
    print('=' * 74)
    print('AFTERNOON QUEUE  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  S24: %.1f of %.0f used, %.1f left; this queue needs %.1f'
          % (used, cap, cap - used, need))
    if need > cap - used:
        print('  REFUSED: not enough headroom.')
        return
    for j in JOBS:
        print('  %-6s (%+5.1f,%+5.1f)  %4.1f min  %s'
              % (j['kind'], j['area'][0], j['area'][1], j['cost'], j['note']))
    if '--dry' in sys.argv:
        print('\nDRY: nothing run.')
        return

    for k, j in enumerate(JOBS):
        log = os.path.join(LOGDIR, 'aft_%d_%s.log' % (k + 1, j['kind']))
        print('\n' + '-' * 74)
        print('[%d/%d] %s  %s' % (k + 1, len(JOBS), j['script'], j['note']))
        print('       log %s' % log)
        env = dict(os.environ)
        env.update(j['env'])
        env['PYTHONIOENCODING'] = 'utf-8'
        try:
            os.remove(os.path.join(HERE, 'autoloop.lock'))
        except OSError:
            pass
        t0 = time.time()
        with io.open(log, 'w', encoding='utf-8') as fh:
            rc = subprocess.call([sys.executable, '-u', j['script']],
                                 cwd=HERE, env=env, stdout=fh,
                                 stderr=subprocess.STDOUT)
        dt = (time.time() - t0) / 60.0
        txt = io.open(log, encoding='utf-8', errors='replace').read()
        key = ''
        for line in txt.split('\n'):
            L = line.strip()
            if L.startswith('super :') or 'CANDIDATE' in L or 'commanded' in L:
                key = L
        print('       rc=%d in %.1f min | %s' % (rc, dt, key[:110]))

    st2 = json.load(io.open(p, encoding='utf-8'))
    print('\n' + '=' * 74)
    print('QUEUE COMPLETE %s   S24 now %.1f of %.0f'
          % (time.strftime('%H:%M'), st2.get('total_write_min', 0.0), cap))


if __name__ == '__main__':
    main()
