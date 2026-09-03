# -*- coding: utf-8 -*-
"""run_night.py -- the experiments the manuscript is missing.

Reads the most recent screen_*.txt, takes the areas that passed every gate
(topography included), and runs a planned set. Each job is its own process.

THE PLAN, and why each job is in it.

  A. RASTER ANGLE SERIES on as-grown film, 0 / 60 / 120 deg.
     Section 3.1 rests on two angles. Three makes it a rule, and 120 deg is a
     genuine pre-registered prediction: the director should go to whichever
     allowed orientation lies nearest 120 deg.

  B. AC vs DC at matched delivered dose.
     Section 3.3 says the drive is even in E. If so, a bias alternating every
     120 nm should align exactly like one held for a whole 1.4 um line. The
     pair is matched on delivered sigma (measured from the built path, not the
     design formula), on |V|, and on geometry.

  C. SCAN SPEED at matched dose.
     sigma = V/(pitch*speed), so speed alone is only varied by compensating the
     pitch. 1.0 um/s at 15 nm pitch delivers what 0.5 um/s at 30 nm does.

  D. REWRITE AN ALIGNED STATE.
     The whole question of the project: once a super-domain is aligned, can the
     same tool re-aim it? Raster at 0 deg, measure, then raster at 60 deg on
     the SAME area and measure again. This is also the direct test of the
     as-grown/poled sign inversion of section 3.2 with the current probe.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A

LOGDIR = os.environ.get('TEMP', '/tmp')
MIN_GAP = 3.6


def usable_areas():
    """Areas that passed every gate in the most recent screen."""
    fs = sorted(glob.glob(os.path.join(HERE, 'screen_*.txt')))
    if not fs:
        return [], None
    txt = io.open(fs[-1], encoding='utf-8', errors='replace').read()
    m = re.search(r'usable offsets: (.+)', txt)
    if not m:
        return [], fs[-1]
    out = []
    for tok in m.group(1).split():
        try:
            x, y = tok.split(',')
            out.append((float(x), float(y)))
        except ValueError:
            pass
    return out, fs[-1]


def plan(areas):
    """Explicit assignments. Each raster angle is chosen for ITS area so that
    the predicted destination is NOT the incumbent -- otherwise the job tests
    nothing, which is the flaw the referee pass found in the existing 60 deg
    datum (before 63.8, after 78.8, on film already sitting on member 76).

    Area triads and incumbents from screen_areas:
      (12,12) 16/76/136 dom 76   Lambda 279   roughness 0.38
      (-6,-6) 24/84/144 dom 84   Lambda 253   roughness 0.38
      ( 0,-6) 19/79/139 dom 79   Lambda 295   roughness 0.52
      (-6, 0) 24/84/144 dom 84   Lambda 245   roughness 0.62
      (12, 0)  4/64/124 dom 64   Lambda 215   roughness 0.65
    """
    have = set(areas)

    def use(a):
        return a if a in have else None

    jobs = []

    # 1. THE DECISIVE ONE. Raster BETWEEN allowed orientations. 46 deg is 30
    #    from both 16 and 76. Snaps to one -> variant selection; sits at 46 ->
    #    the raster writes a pattern like the lattice does, and the paper has
    #    no imprint-free result.
    if use((12.0, 12.0)):
        jobs.append(dict(tag='offtriad_raster', area=(12.0, 12.0),
                         env=dict(B3_MODE='dc', B3_ANG='46', B3_PITCH='0.03',
                                  B3_SPEED='0.5'),
                         cost=6.2,
                         note='raster 46 deg, BETWEEN members 16 and 76'))

    # 2. angle 0 on a film whose incumbent is member 84 -> a real 60 deg move
    if use((-6.0, -6.0)):
        jobs.append(dict(tag='angle0', area=(-6.0, -6.0),
                         env=dict(B3_MODE='dc', B3_ANG='0', B3_PITCH='0.03',
                                  B3_SPEED='0.5'),
                         cost=6.2,
                         note='DC 0 deg; predicts member 24 from incumbent 84'))

    # 3. angle 120, likewise a real move, and a pre-registered prediction
    if use((0.0, -6.0)):
        jobs.append(dict(tag='angle120', area=(0.0, -6.0),
                         env=dict(B3_MODE='dc', B3_ANG='120', B3_PITCH='0.03',
                                  B3_SPEED='0.5'),
                         cost=6.2,
                         note='DC 120 deg; predicts member 139 from '
                              'incumbent 79'))

    # 4. AC against DC at the SAME angle and pitch. Delivered sigma 633 vs
    #    681, 7 % apart and LOWER, so equal alignment would be conservative.
    if use((12.0, 0.0)):
        jobs.append(dict(tag='ac0', area=(12.0, 0.0),
                         env=dict(B3_MODE='ac', B3_ANG='0', B3_ACN='3',
                                  B3_PITCH='0.03', B3_SPEED='0.5'),
                         cost=6.2,
                         note='AC 0 deg, 120 nm sign period; predicts member 4'))

    # 5-6. REWRITE AN ALIGNED STATE, two writes on one area. Align to member
    #      24 with a 0 deg raster, then re-aim to member 84 with a 60 deg
    #      raster on the SAME film. This is the project's central question and
    #      also the current-probe test of the as-grown/poled sign inversion.
    if use((-6.0, 0.0)):
        jobs.append(dict(tag='rw_step1', area=(-6.0, 0.0),
                         env=dict(B3_MODE='dc', B3_ANG='0', B3_PITCH='0.03',
                                  B3_SPEED='0.5'),
                         cost=6.2,
                         note='REWRITE 1/2: align to member 24 (raster 0)'))
        jobs.append(dict(tag='rw_step2', area=(-6.0, 0.0),
                         env=dict(B3_MODE='dc', B3_ANG='60', B3_PITCH='0.03',
                                  B3_SPEED='0.5', B3_FORCE='1'),
                         cost=6.2,
                         note='REWRITE 2/2: re-aim the SAME film to member 84'))
    return jobs


def main():
    areas, src = usable_areas()
    print('=' * 78)
    print('NIGHT QUEUE  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    print('  screen: %s' % (os.path.basename(src) if src else 'none found'))
    print('  usable areas: %s' % (areas if areas else 'NONE'))
    if not areas:
        print('  nothing to run. Screen more areas or move the stage.')
        return
    jobs = plan(areas)
    st = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                           encoding='utf-8'))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    used = float(st.get('total_write_min', 0.0))
    need = sum(j['cost'] for j in jobs)
    print('  S24: %.1f of %.0f used, %.1f left; queue needs %.1f'
          % (used, cap, cap - used, need))
    print('\n  %-11s %-13s %5s  %s' % ('job', 'area', 'min', 'note'))
    for j in jobs:
        print('  %-11s (%+5.1f,%+5.1f) %5.1f  %s'
              % (j['tag'], j['area'][0], j['area'][1], j['cost'], j['note']))
    print('\n  %d jobs, ~24 min each -> ~%.1f h'
          % (len(jobs), len(jobs) * 24 / 60.0))
    if '--dry' in sys.argv:
        print('\nDRY: nothing run.')
        return

    prev = {}
    for k, j in enumerate(jobs):
        ax, ay = j['area']
        log = os.path.join(LOGDIR, 'night_%d_%s.log' % (k + 1, j['tag']))
        print('\n' + '-' * 78)
        print('[%d/%d] %-11s (%+.1f,%+.1f)  %s'
              % (k + 1, len(jobs), j['tag'], ax, ay, j['note']))
        env = dict(os.environ)
        env.update(j['env'])
        env.update(B3_X=str(ax), B3_Y=str(ay), B3_LABEL=j['tag'],
                   PYTHONIOENCODING='utf-8')
        # step 2 of the rewrite re-uses step 1's AFTER frames as its BEFORE,
        # so the comparison is against the aligned state and not a fresh tune
        if j['tag'] == 'rw_step2' and prev.get('rw_after'):
            env['B3_BEFORE_L'], env['B3_BEFORE_V'] = prev['rw_after']
            print('       before-frames inherited from step 1: %s / %s'
                  % prev['rw_after'])
        else:
            env['B3_BEFORE_L'] = env['B3_BEFORE_V'] = ''
        try:
            os.remove(os.path.join(HERE, 'autoloop.lock'))
        except OSError:
            pass
        t0 = time.time()
        with io.open(log, 'w', encoding='utf-8') as fh:
            rc = subprocess.call([sys.executable, '-u', 'block3_raster.py'],
                                 cwd=HERE, env=env, stdout=fh,
                                 stderr=subprocess.STDOUT)
        dt = (time.time() - t0) / 60.0
        txt = io.open(log, encoding='utf-8', errors='replace').read()
        key = ''
        for line in txt.split('\n'):
            L = line.strip()
            if L.startswith('->') or 'director ' in L:
                key = L
        m = re.search(r'after (\S+) / (\S+)\s*$', txt, re.M)
        if j['tag'] == 'rw_step1' and m:
            prev['rw_after'] = (m.group(1), m.group(2))
        print('       rc=%d in %.1f min | %s' % (rc, dt, key[:100]))

    st2 = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                            encoding='utf-8'))
    print('\n' + '=' * 78)
    print('QUEUE COMPLETE %s   S24 %.1f of %.0f'
          % (time.strftime('%H:%M'), st2.get('total_write_min', 0.0), cap))


if __name__ == '__main__':
    main()
