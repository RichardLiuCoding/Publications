# -*- coding: utf-8 -*-
"""run_round3.py -- close the dose confound, and repeat the rewrite.

The second referee pass found that the paper's headline contrast is confounded
with dose: the point-pulse lattice runs at sigma ~120 V.s/um^2 and the raster
at ~680, a factor of six. "One selects a variant, the other writes a pattern"
could therefore be "high dose selects, low dose imprints", which would be a
different and much weaker paper.

The test is an OFF-TRIAD RASTER AT LATTICE-LIKE DOSE. Two routes, because
either one alone is confounded:

  * coarsen the line pitch to 120 nm at the same 0.5 um/s -> sigma 178. Speed
    matches the sigma 686 reference, so only dose changes. A 170 nm pitch would
    hit sigma 127 exactly but lies INSIDE the 150-500 nm readout band and would
    imprint; 120 nm is below it and safe.
  * reach a MATCHING dose at a different speed: 60 nm pitch at 1.0 um/s gives
    sigma 171, within 4 % of the 120 nm / 0.5 um/s point but at twice the
    speed and half the pitch. If dose is what matters the two agree; if speed
    matters they do not.

    2.8 um/s was the original plan, since it reaches sigma 123 at the
    reference pitch. It was dropped: STEP is 20 nm, so 2.8 um/s asks the Igor
    litho engine for 140 points/s against the 25 points/s this campaign has
    ever driven, and run_traj waits a COMPUTED duration and then issues a hard
    Stop. If the engine cannot keep up, the write is truncated part-way
    through the path and nothing reports it -- the file validates, the frame
    looks normal, and the delivered dose is neither what was asked for nor
    what is recorded. 1.0 um/s is a 2x extrapolation instead of 5.6x.

If both still land on an allowed orientation, the raster/lattice contrast is a
property of the tool and survives. If they land at the commanded angle, it is a
dose effect and the framing must change.

A mid-dose point at 60 nm pitch (sigma 343) makes the three pitch points a dose
series, which the referee also asked for (section 3.6 currently has no curve).

Finally a second write-then-re-aim pair, because the paper's most
application-relevant claim rests on one instance.
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
LAM_MAX = 300.0            # 1.2 um readout window needs Lambda <= 300 nm


def fresh_areas():
    """Screened areas that pass 4-Lambda at a 1.2 um window and are unwritten."""
    st = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                           encoding='utf-8'))
    pos = st.get('sample_position')
    used = {tuple(float(v) for v in d['area'])
            for d in st.get('diagnostic_writes', [])
            if d.get('sample_position') == pos and d.get('area')}
    out, seen = [], set()
    for f in sorted(glob.glob(os.path.join(HERE, 'screen_*.txt')),
                    reverse=True):
        txt = io.open(f, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'\(([-+ \d.]+),([-+ \d.]+)\)\s+([\d.]+)\s+'
                             r'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+'
                             r'(\d+)\s+YES', txt):
            x, y = float(m.group(1)), float(m.group(2))
            lam = float(m.group(7))
            if (x, y) in used or (x, y) in seen or lam > LAM_MAX:
                continue
            seen.add((x, y))
            out.append(((x, y), lam))
    return out


JOBSPEC = [
    ('dose343', dict(B3_MODE='dc', B3_ANG='41', B3_PITCH='0.06',
                     B3_SPEED='0.5'), 3.2,
     'off-triad raster, 60 nm pitch, 0.5 um/s -> sigma 343 (half dose)'),
    ('dose178', dict(B3_MODE='dc', B3_ANG='41', B3_PITCH='0.12',
                     B3_SPEED='0.5'), 1.7,
     'off-triad raster, 120 nm pitch, 0.5 um/s -> sigma 178 '
     '(lattice-like dose: THE decisive point)'),
    ('speed171', dict(B3_MODE='dc', B3_ANG='41', B3_PITCH='0.06',
                      B3_SPEED='1.0'), 1.7,
     'off-triad raster, 60 nm pitch at 1.0 um/s -> sigma 171 '
     '(dose matched to dose178, twice the speed)'),
    ('rw2_step1', dict(B3_MODE='dc', B3_ANG='0', B3_PITCH='0.03',
                       B3_SPEED='0.5'), 6.2,
     'REWRITE 2, step 1: align with a 0 deg raster'),
    ('rw2_step2', dict(B3_MODE='dc', B3_ANG='120', B3_PITCH='0.03',
                       B3_SPEED='0.5', B3_FORCE='1'), 6.2,
     'REWRITE 2, step 2: re-aim the SAME area with a 120 deg raster'),
]


def main():
    areas = fresh_areas()
    print('=' * 78)
    print('ROUND 3  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    print('  fresh areas (Lambda <= %.0f nm): %s'
          % (LAM_MAX, [(a, int(l)) for a, l in areas]))
    if len(areas) < 4:
        print('  need 4, have %d. Screen more areas.' % len(areas))
        if not areas:
            return
    jobs = []
    pool = [a for a, _ in areas]
    for k, (tag, env, cost, note) in enumerate(JOBSPEC):
        if tag == 'rw2_step2':
            if not jobs or jobs[-1]['tag'] != 'rw2_step1':
                continue
            ar = jobs[-1]['area']            # same area as step 1
        else:
            if not pool:
                break
            ar = pool.pop(0)
        jobs.append(dict(tag=tag, area=ar, env=env, cost=cost, note=note))

    st = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                           encoding='utf-8'))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    used = float(st.get('total_write_min', 0.0))
    need = sum(j['cost'] for j in jobs)
    print('  S24: %.1f of %.0f used, %.1f left; round 3 needs %.1f'
          % (used, cap, cap - used, need))
    for j in jobs:
        print('  %-11s (%+5.1f,%+5.1f) %5.1f min  %s'
              % (j['tag'], j['area'][0], j['area'][1], j['cost'], j['note']))
    if need > cap - used:
        print('  REFUSED: not enough headroom.')
        return
    if '--dry' in sys.argv:
        print('\nDRY: nothing run.')
        return

    prev_after = None
    for k, j in enumerate(jobs):
        ax, ay = j['area']
        log = os.path.join(LOGDIR, 'r3_%d_%s.log' % (k + 1, j['tag']))
        print('\n' + '-' * 78)
        print('[%d/%d] %-11s (%+.1f,%+.1f)  %s'
              % (k + 1, len(jobs), j['tag'], ax, ay, j['note']))
        if subprocess.call([sys.executable, '-u', 'instrument_free.py'],
                           cwd=HERE) != 0:
            print('       instrument busy; stopping.')
            break
        env = dict(os.environ)
        env.update(j['env'])
        env.update(B3_X=str(ax), B3_Y=str(ay), B3_LABEL=j['tag'],
                   PYTHONIOENCODING='utf-8')
        if j['tag'] == 'rw2_step2' and prev_after:
            env['B3_BEFORE_L'], env['B3_BEFORE_V'] = prev_after
            print('       before-frames inherited: %s / %s' % prev_after)
        else:
            env['B3_BEFORE_L'] = env['B3_BEFORE_V'] = ''
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
        m = re.search(r'after (\S+) / (\S+)\s*$', txt, re.M)
        if j['tag'] == 'rw2_step1' and m:
            prev_after = (m.group(1), m.group(2))
        print('       rc=%d in %.1f min | %s'
              % (rc, (time.time() - t0) / 60.0, key[:100]))

    st2 = json.load(io.open(os.path.join(HERE, 'campaign_state.json'),
                            encoding='utf-8'))
    print('\n' + '=' * 78)
    print('ROUND 3 COMPLETE %s   S24 %.1f of %.0f'
          % (time.strftime('%H:%M'), st2.get('total_write_min', 0.0), cap))


if __name__ == '__main__':
    main()
