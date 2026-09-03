# -*- coding: utf-8 -*-
"""Re-score IT1 at the restored withdrawn deflection. IMAGING ONLY - no writes.

The withdrawn deflection drifted -0.8 -> -0.6 V across IT1 and has been set back
to -0.8. The baselines (LDART_0061-0063) were taken at -0.8; the after-frame
(LDART_0071) at -0.6. So the pair straddled a change in contact force, which
moves the measurement without moving the material - and that is very likely why
5 of 16 untouched control tiles appeared to change dominant director.

This script:
  1. takes three fresh LDART frames at the restored -0.8;
  2. scores the four panels against the ORIGINAL baselines, so before and after
     are once again at the same contact force;
  3. builds the floor from the fresh frames' mutual disagreement, which is the
     honest frame-to-frame noise at this setpoint;
  4. quantifies the artefact directly by comparing the -0.6 after-frame against
     the fresh -0.8 ones over untouched film;
  5. re-checks the out-of-plane orbit, to see whether the 19.5 % minority that
     shut the gate was also a setpoint artefact.

Panels, from the IT1 run: 2x2 at Lambda 280 nm, all commanded 6 deg from a local
dominant of 66 deg.
"""
import io
import os
import sys
import json
import time
import traceback
import contextlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A

FRAME, PX = 12.0, 256
RATE = A.TIP_SPEED_MAX / (2.0 * FRAME)
XOFF, YOFF = 0.0, 0.0
BASE = ['PZTO_LDART_0061.ibw', 'PZTO_LDART_0062.ibw', 'PZTO_LDART_0063.ibw']
F_REF_OLD = 'PZTO_LDART_0061.ibw'
AFTER_DRIFTED = 'PZTO_LDART_0071.ibw'
TRIAD = [6.0, 66.0, 126.0]
LAM, WIN = 280.0, 1.22
PANELS = [dict(label='A', cx=4.16, cy=3.40, cmd=6.0, sigma=449.9, n=256),
          dict(label='B', cx=7.84, cy=3.40, cmd=6.0, sigma=449.9, n=128),
          dict(label='C', cx=4.16, cy=7.08, cmd=6.0, sigma=449.9, n=256),
          dict(label='D', cx=7.84, cy=7.08, cmd=6.0, sigma=204.5, n=256)]

buf = io.StringIO()


class Tee(object):
    def __init__(self, *s):
        self.s = s

    def write(self, x):
        for t in self.s:
            t.write(x)

    def flush(self):
        for t in self.s:
            t.flush()


def main():
    print('=' * 78)
    print('IT1 RE-SCORE at the restored withdrawn deflection  %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    print('  IMAGING ONLY - this script never writes.')
    if os.path.exists(A.STOP):
        raise SystemExit('STOP file present')
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    print('\n--- three fresh frames at the restored setpoint ---')
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_ldart')()
    fresh = [g('frame')() for _ in range(3)]
    print('  ' + ', '.join(fresh))
    g('contact_check')(fresh[-1])

    print('\n--- hygiene: the two setpoint regimes side by side ---')
    print('  %-22s%-10s%8s%8s%9s%9s'
          % ('frame', 'regime', '|S|', 'r12', 'tracked', 'streak'))
    for t, reg in ([(b, '-0.8 base') for b in BASE]
                   + [(AFTER_DRIFTED, '-0.6 drift')]
                   + [(f, '-0.8 fresh') for f in fresh]):
        d, h = g('ibw')(t)
        S, _, r12 = g('signed')(d)
        tr = g('tracking_rows')(t, verbose=False)
        with contextlib.redirect_stdout(io.StringIO()):
            sk = g('streak_index')(t, (0.35, FRAME - 0.35, 0.35, 1.7))
        print('  %-22s%-10s%8.1f%+8.2f%8.0f%%%9.3f'
              % (t, reg, np.std(S), r12, 100 * tr['frac'], sk))

    ds = g('dir_state')
    ct = g('ctrl_tiles')(0.35, FRAME - 0.35, 0.35, 0.35 + WIN, WIN)
    top = 7.08 + 1.79 + 0.05
    if FRAME - 0.35 - top >= WIN:
        ct += g('ctrl_tiles')(0.35, FRAME - 0.35, top, FRAME - 0.35, WIN)
    print('\n  %d control tiles on untouched film' % len(ct))

    def floor_between(t0, t1):
        dl, flip = [], 0
        for rg in ct:
            cx, cy = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
            s0 = ds(t0, cx, cy, WIN, TRIAD, 6.0)
            s1 = ds(t1, cx, cy, WIN, TRIAD, 6.0)
            if s0 is None or s1 is None:
                continue
            dl.append(s1['lead'] - s0['lead'])
            flip += int(s1['dom'] != s0['dom'])
        dl = np.array(dl)
        return (float(np.abs(dl).max()), flip / float(len(dl)), len(dl),
                float(dl.mean()), float(dl.std(ddof=1)))

    print('\n=== how big is the setpoint artefact? (untouched film only) ===')
    print('  %-34s%9s%9s%10s%9s' % ('comparison', 'floor', 'flip %', 'mean',
                                    'sd'))
    for lab, t0, t1 in (('fresh vs fresh   (-0.8 vs -0.8)', fresh[0], fresh[1]),
                        ('fresh vs fresh   (-0.8 vs -0.8)', fresh[1], fresh[2]),
                        ('base  vs fresh   (-0.8 vs -0.8)', F_REF_OLD, fresh[0]),
                        ('base  vs drifted (-0.8 vs -0.6)', F_REF_OLD,
                         AFTER_DRIFTED),
                        ('drift vs fresh   (-0.6 vs -0.8)', AFTER_DRIFTED,
                         fresh[0])):
        fl, fr, n, m, sd = floor_between(t0, t1)
        print('  %-34s%9.3f%8.0f%%%10.3f%9.3f' % (lab, fl, 100 * fr, m, sd))
    print('  If "base vs drifted" is much worse than "base vs fresh", the')
    print('  31 % flip rate was the setpoint change, not the material.')

    FL, FLIP, NT, _, _ = floor_between(F_REF_OLD, fresh[0])
    print('\n=== THE PANELS, scored -0.8 against -0.8 ===')
    print('  floor %.3f from base vs fresh on untouched film, flip %.0f%%, '
          '%d tiles' % (FL, 100 * FLIP, NT))
    print('  %-3s%9s%7s%7s%9s%9s%9s%6s%8s  verdict'
          % ('', 'sigma', 'dom b', 'dom a', 'lead b', 'lead a', 'd(lead)',
             'xfl', 'w(cmd)'))
    out = {}
    for p in PANELS:
        s0 = ds(F_REF_OLD, p['cx'], p['cy'], WIN, TRIAD, p['cmd'])
        s1 = ds(fresh[0], p['cx'], p['cy'], WIN, TRIAD, p['cmd'])
        d_ = s1['lead'] - s0['lead']
        ok = bool(s1['on_target'] and d_ > 3 * FL)
        out[p['label']] = dict(sigma=p['sigma'], dom0=s0['dom'], dom1=s1['dom'],
                               lead0=s0['lead'], lead1=s1['lead'], dlead=d_,
                               w_cmd=s1['w_cmd'], turned=ok, n=p['n'],
                               w0=[float(z) for z in s0['w']],
                               w1=[float(z) for z in s1['w']])
        print('  %-3s%9.0f%7.0f%7.0f%+9.3f%+9.3f%+9.3f%6.1f%8.3f  %s'
              % (p['label'], p['sigma'], s0['dom'], s1['dom'], s0['lead'],
                 s1['lead'], d_, d_ / max(FL, 1e-9), s1['w_cmd'],
                 'TURNED' if ok else ('on target, within floor'
                                      if s1['on_target'] else
                                      'dominant %.0f, NOT the command'
                                      % s1['dom'])))
    print('\n  populations')
    print('  %-3s' % '' + ''.join('%18s' % ('w(%.0f)' % t) for t in TRIAD))
    for p in PANELS:
        r = out[p['label']]
        print('  %-3s' % p['label']
              + ''.join('%8.3f->%-9.3f' % (r['w0'][i], r['w1'][i])
                        for i in range(3)))

    print('\n--- VDART at the restored setpoint: did the gate reopen? ---')
    g('setup_scan')(size_um=FRAME, px=128, rate=RATE, angle_deg=0.0)
    g('goto_vdart')()
    vf = g('frame')()
    g('orbit_balance')(vf)
    print('  before IT1 the trend was 46.0 -> 36.4 -> 33.0 %% minority; the')
    print('  after-IT1 VDART at -0.6 read 19.5 %%, outside the 21-36 %% range.')
    print('  If this one is back inside, the skew was the setpoint too.')
    g('goto_ldart')()
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0)

    print('\n' + '=' * 74)
    print('RE-SCORE VERDICT')
    print('=' * 74)
    nturn = sum(1 for v in out.values() if v['turned'])
    ontgt = sum(1 for v in out.values() if v['dom1'] == 6.0)
    print('  %d of 4 panels above 3x the floor; %d of 4 end dominant at the '
          'commanded 6 deg' % (nturn, ontgt))
    if out['D']['turned'] and out['A']['turned']:
        print('  !! D turned as well as A. D is the negative control at 0.68 '
              'sigma_c,')
        print('     so either sigma_c is much lower here, or something drove the')
        print('     whole frame. Do not read the factorial until that is settled.')
    elif out['A']['turned'] and not out['D']['turned']:
        print('  A turned and D did not, so the threshold behaves as expected')
        print('     here and the factorial (B vs C) can be read.')
    return out, fresh, FL, FLIP


try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            out, fresh, FL, FLIP = main()
    st = A.load_state()
    st['history'][-1]['rescore'] = dict(
        when=time.strftime('%Y-%m-%d %H:%M'), fresh=fresh, floor=FL,
        flip=FLIP, panels=out,
        note='setpoint restored to -0.8; scored -0.8 baselines against -0.8 '
             'fresh frames')
    A.save_state(st)
except Exception:
    traceback.print_exc()
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it1_rescore.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
