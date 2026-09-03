# -*- coding: utf-8 -*-
"""run_campaign.py -- execute a queue of template experiments unattended.

WHY. The binding constraint tonight is the S24 write budget (75 min), not the
clock. So the queue is ordered by scientific value per write-minute, and every
job is charged before it runs. A job that cannot be afforded is skipped, not
truncated.

WHAT IT DOES. Runs each job as a SUBPROCESS of run_template.py, so a fault in
one job cannot take down the queue or corrupt the ones already done. Results
accumulate in results_templates.csv; this script only sequences and reports.

  python run_campaign.py                 run the default queue
  python run_campaign.py --dry           print the plan and the cost, run nothing
  QUEUE=select,dose1 python run_campaign.py    run a subset

STOPPING. Checks for the STOP file before every job, and refuses to start a job
whose estimated cost exceeds the remaining S24 headroom.
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

STATE = os.path.join(HERE, 'campaign_state.json')
LOGDIR = os.environ.get('TEMP', '/tmp')
DRY = '--dry' in sys.argv

# Estimated write-minutes per job. Measured: a two-panel 1.4 um run at
# sigma 667 is 5.5 min; cost scales roughly with the mean sigma.
EST = {'select': 5.5, 'control': 6.0, 'shear': 5.6, 'shear75': 5.6,
       'dose1': 3.9, 'dose2': 5.5, 'dose3': 3.2, 'cross': 5.5,
       'dose4': 1.2, 'dose5': 0.6, 'dose6': 0.4, 'dose7': 0.2}
# select at sigma 120 costs ~1.0 min, not 5.5 -- dwell scales with dose
EST_LOWDOSE = 1.1

# The queue, in priority order. Each entry: (EXP, area, sigma, why)
QUEUE = [
    # ROUND 3. Areas assigned so each satisfies the 4-Lambda READOUT rule for
    # ITS OWN panel size (19.15): wide panels are 1.2 um so they need
    # Lambda <= 300 nm; narrow panels are 1.4 um so they need <= 350 nm.
    # (+24,0) and (-24,+24) are excluded -- they failed the modulation floor.
    ('select',  (-16.0, 16.0), 120, 'crosstalk NARROW 1, gap 0.6 um, L 301'),
    ('select',  (24.0, 24.0),  120, 'crosstalk WIDE 1, gap 1.8 um, L 245'),
    ('select',  (-24.0, -24.0), 120, 'crosstalk NARROW 2, L 325'),
    ('select',  (0.0, 24.0),   120, 'crosstalk WIDE 2, L 231'),
    ('select',  (0.0, -24.0),  120, 'crosstalk NARROW 3, L 301'),
    ('select',  (24.0, -24.0), 120, 'crosstalk WIDE 3, L 261'),
    ('dose7',   (-24.0, 0.0),  667, 'sigma 20/30 on fine film, L 301'),
]

# geometry per job: (PANEL_HALF, PANEL_SEP). None = driver default.
GEOM = {1: (0.70, 2.0), 2: (0.60, 3.0), 3: (0.70, 2.0),
        4: (0.60, 3.0), 5: (0.70, 2.0), 6: (0.60, 3.0)}


def headroom():
    st = json.load(io.open(STATE, encoding='utf-8'))
    cap = float(getattr(A, 'MAX_TOTAL_WRITE_MIN', 330.0))
    return cap - float(st.get('total_write_min', 0.0))


def used_areas():
    """Areas already written by the diagnostic drivers, from the ledger."""
    st = json.load(io.open(STATE, encoding='utf-8'))
    pos = st.get('sample_position')
    out = set()
    for d in st.get('diagnostic_writes', []):
        # offsets only mean the same film WITHIN one stage position; after a
        # move the same (x,y) is different material
        if d.get('sample_position') != pos:
            continue
        a = d.get('area')
        if a:
            out.add((round(float(a[0]), 1), round(float(a[1]), 1)))
    return out


def main():
    want = os.environ.get('QUEUE', '').strip()
    queue = [q for q in QUEUE if not want or q[0] in want.split(',')]

    print('=' * 74)
    print('CAMPAIGN  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    hr = headroom()
    print('  S24 headroom %.1f write-minutes' % hr)
    def _est(exp, sig):
        if exp == 'select' and sig < 300:
            return EST_LOWDOSE
        return EST.get(exp, 5.5)
    print('  %d jobs queued, estimated %.1f min'
          % (len(queue), sum(_est(q[0], q[2]) for q in queue)))
    done_areas = used_areas()
    if done_areas:
        print('  already written: %s' % sorted(done_areas))
    print()
    print('  %-3s %-8s %-14s %-6s %s' % ('#', 'exp', 'area', 'est', 'why'))
    for i, (exp, area, sig, why) in enumerate(queue, 1):
        print('  %-3d %-8s (%+5.1f,%+5.1f) %-6.1f %s'
              % (i, exp, area[0], area[1], _est(exp, sig), why))
    if DRY:
        print('\n  --dry: nothing run.')
        return

    results = []
    for i, (exp, area, sig, why) in enumerate(queue, 1):
        if os.path.exists(A.STOP):
            print('\nSTOP file present; ending the queue.')
            break
        hr = headroom()
        if exp == 'select' and sig < 300:
            est = EST_LOWDOSE
        else:
            est = EST.get(exp, 5.5)
        print('\n' + '-' * 74)
        print('[%d/%d] %s at (%+.1f,%+.1f)  est %.1f min, headroom %.1f'
              % (i, len(queue), exp, area[0], area[1], est, hr))
        print('       %s' % why)
        if est > hr:
            print('       SKIPPED: not affordable within S24.')
            results.append((exp, area, 'skipped-budget'))
            continue
        if (round(area[0], 1), round(area[1], 1)) in used_areas():
            print('       SKIPPED: area already written.')
            results.append((exp, area, 'skipped-used'))
            continue

        log = os.path.join(LOGDIR, 'camp_%s_%+.0f_%+.0f.log'
                           % (exp, area[0], area[1]))
        env = dict(os.environ, EXP=exp, AREA_X=str(area[0]),
                   AREA_Y=str(area[1]), SIGMA=str(sig))
        if i in GEOM:
            env['PANEL_HALF'] = str(GEOM[i][0])
            env['PANEL_SEP'] = str(GEOM[i][1])
            print('       geometry: panel %.1f um, centres %.1f um apart '
                  '(gap %.1f um)'
                  % (2 * GEOM[i][0], GEOM[i][1], GEOM[i][1] - 2 * GEOM[i][0]))
        t0 = time.time()
        with io.open(log, 'w', encoding='utf-8') as fh:
            rc = subprocess.call([sys.executable, '-u',
                                  os.path.join(HERE, 'run_template.py')],
                                 stdout=fh, stderr=subprocess.STDOUT, env=env,
                                 cwd=HERE)
        dt = (time.time() - t0) / 60.0
        txt = io.open(log, encoding='utf-8', errors='ignore').read()
        verdict = 'ok' if rc == 0 else 'rc=%d' % rc
        for key in ('That is SELECTION', 'DRIVE alone',
                    'as predicted', 'VOID', 'one-sided'):
            if key in txt:
                verdict = key
                break
        print('       -> %s in %.1f min (log %s)'
              % (verdict, dt, os.path.basename(log)))
        results.append((exp, area, verdict))

    print('\n' + '=' * 74)
    print('QUEUE COMPLETE  %s' % time.strftime('%H:%M'))
    print('=' * 74)
    for exp, area, v in results:
        print('  %-8s (%+5.1f,%+5.1f)  %s' % (exp, area[0], area[1], v))
    print('\n  S24 headroom now %.1f min' % headroom())
    csv = os.path.join(HERE, 'results_templates.csv')
    if os.path.exists(csv):
        n = sum(1 for _ in io.open(csv, encoding='utf-8')) - 1
        print('  results_templates.csv: %d panel rows' % n)


if __name__ == '__main__':
    main()
