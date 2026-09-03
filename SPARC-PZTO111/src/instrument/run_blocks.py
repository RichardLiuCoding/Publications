# -*- coding: utf-8 -*-
"""run_blocks.py -- queue of single-panel runs at 2.5 um, one per area.

Each job is a separate `block1_write.py` process so that a crash in one costs
one area rather than the queue, and so each job charges S24 itself.

  python run_blocks.py            # run the queue
  python run_blocks.py --dry      # print the plan and the budget, write nothing

Job fields: area, sigma, want ('' = auto, 60 deg from the incumbent), and a
note. Areas are spaced 4 um so 2.5 um frames cannot overlap (S9); the guard
below checks that against everything already written this session.
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

SIZE_UM = 2.5
MIN_GAP = 3.6          # centre-to-centre, um: 2.5 um frames plus a margin
LOGDIR = os.environ.get('TEMP', '/tmp')
STAMP = time.strftime('%y%m%d_%H%M')

# ---------------------------------------------------------------- the queue
# Dose ladder for the nano-domain question. The doses straddle the completion
# threshold M22 puts between 52 and 67 V.s/um^2, so if the nano-domains appear
# only when the super-domain rewrite COMPLETES, the ladder will show it.
JOBS = [
    # 1. THE NULL. No write at all: two before-pairs and two after-pairs at
    #    the same spot, same tunes, same everything. Every "created by the
    #    write" number today is a before/after difference, and none of them
    #    means anything until we know what a before/after difference looks
    #    like when NOTHING happened. sigma = 0 skips the write.
    dict(area=(4.0, 4.0), sigma=0, lam='', want='',
         note='NO-WRITE NULL: how much does a re-tune alone move it?'),
    # 2. THE PROPER INCOMMENSURATE CONTROL. The first attempt used a template
    #    period of 328 nm against a 253 nm film: dq = 0.90 /um against a
    #    window resolution of 1.00 /um, i.e. INSIDE one resolution element, so
    #    it could not have decided anything. 155 nm against ~250 nm gives
    #    dq = 2.5 /um, two and a half resolution elements, and q/Q = 1.618 is
    #    the ratio least well approximated by a low-order rational.
    dict(area=(-4.0, -4.0), sigma=130, lam='155', want='',
         note='INCOMMENSURATE q/Q = 1.62, properly resolvable'),
]


def used_areas():
    """Every area already written, from the campaign ledger."""
    p = os.path.join(HERE, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    pos = st.get('sample_position')
    out = []
    for d in st.get('diagnostic_writes', []):
        if d.get('sample_position') == pos and d.get('area'):
            out.append(tuple(float(v) for v in d['area']))
    return out, st


def main():
    dry = '--dry' in sys.argv
    prev, st = used_areas()
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    used = float(st.get('total_write_min', 0.0))
    print('=' * 74)
    print('BLOCK QUEUE  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  S24: %.1f of %.0f used, %.1f left' % (used, cap, cap - used))
    print('  already written this position: %s' % sorted(set(prev)))

    plan = []
    for j in JOBS:
        ax, ay = j['area']
        clash = [p for p in prev
                 if max(abs(p[0] - ax), abs(p[1] - ay)) < MIN_GAP]
        if clash:
            print('  SKIP (%+.1f,%+.1f): within %.1f um of written %s (S9)'
                  % (ax, ay, MIN_GAP, clash))
            continue
        plan.append(j)

    print('\n  %-16s %8s  %s' % ('area', 'sigma', 'note'))
    for j in plan:
        print('  (%+5.1f,%+5.1f)   %8d  %s' % (j['area'][0], j['area'][1],
                                               j['sigma'], j['note']))
    print('\n  %d jobs, ~%.0f min each -> ~%.1f h'
          % (len(plan), 21, len(plan) * 21 / 60.0))
    if dry:
        print('\nDRY: nothing run.')
        return

    results = []
    for k, j in enumerate(plan):
        ax, ay = j['area']
        tag = 'b1_%+.0f_%+.0f' % (ax, ay)
        log = os.path.join(LOGDIR, 'blk_%s.log' % tag.replace('+', 'p')
                           .replace('-', 'm'))
        print('\n' + '-' * 74)
        print('[%d/%d] area (%+.1f,%+.1f) sigma %d   %s'
              % (k + 1, len(plan), ax, ay, j['sigma'], j['note']))
        print('       log %s' % log)
        env = dict(os.environ)
        env.update(B1_X=str(ax), B1_Y=str(ay), B1_SIGMA=str(j['sigma']),
                   B1_WANT=str(j['want']), B1_BEFORE_L='', B1_BEFORE_V='',
                   PYTHONIOENCODING='utf-8')
        env.pop('B1_LAM', None)          # each area measures its own...
        if j.get('lam'):                 # ...unless the job pins it on purpose
            env['B1_LAM'] = str(j['lam'])
        t0 = time.time()
        try:
            os.remove(os.path.join(HERE, 'autoloop.lock'))
        except OSError:
            pass
        with io.open(log, 'w', encoding='utf-8') as fh:
            rc = subprocess.call([sys.executable, '-u', 'block1_write.py'],
                                 cwd=HERE, env=env, stdout=fh,
                                 stderr=subprocess.STDOUT)
        dt = (time.time() - t0) / 60.0
        txt = io.open(log, encoding='utf-8', errors='replace').read()
        verdict = 'rc=%d' % rc
        for line in txt.split('\n'):
            if 'commanded' in line and 'sigma' in line:
                verdict = line.strip()
        print('       -> %s in %.1f min' % (verdict, dt))
        results.append((j, rc, verdict, dt))

    print('\n' + '=' * 74)
    print('QUEUE COMPLETE  %s' % time.strftime('%H:%M'))
    print('=' * 74)
    for j, rc, v, dt in results:
        print('  (%+5.1f,%+5.1f) sigma %-4d  %s'
              % (j['area'][0], j['area'][1], j['sigma'], v))
    _, st2 = used_areas()
    print('\n  S24 now %.1f of %.0f' % (st2.get('total_write_min', 0.0), cap))


if __name__ == '__main__':
    main()
