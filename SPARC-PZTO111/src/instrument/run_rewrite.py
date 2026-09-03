# -*- coding: utf-8 -*-
"""run_rewrite.py -- why does a scan trace fail to rewrite an ORDERED domain?

THE OBSERVATION (operator, 28 Aug). Once a large IP super-domain has been
written, pure scan-trace trajectory litho struggles to re-orient it, while a
point-pulse lattice still can.

TWO EXPLANATIONS FIT, and this morning's control experiment cannot separate them
because its solid raster differed from the lattice in both respects at once:

  A. WAVEVECTOR. A continuous trace carries no periodicity along the trace, and
     its cross-trace pitch is not Lambda, so it has no commensurate Q. By M16
     and M18 it can then only DRIVE. Drive concentrates a disordered region --
     which is what the solid panel did on virgin film, 75 -> 70 deg -- but has
     no mechanism to steer an already-ordered one.

  B. PULSED vs CONTINUOUS. Stationary pulses may nucleate a new orientation in
     a way a moving biased tip cannot, whatever the wavevector.

DESIGN. Three frames, two writes, on ONE area.

  frame 1  virgin
  STAGE 1  a large lattice, lines along A, covering the whole measurement zone.
           This manufactures the ordered super-domain the question is about.
  frame 2  confirm the order exists and read its director
  STAGE 2  inside that ordered region, two 1.4 um panels, both with lines along
           B (a DIFFERENT member):
              P1  TRACE    continuous strokes, same line spacing, same Q
              P2  LATTICE  discrete pulses, same Q, same dose
  frame 3  which one re-oriented?

The four control windows sit inside the ordered region and are NOT re-written,
so they measure what "ordered, left alone" does across the same interval, and
supply the null.

Because P1 and P2 here share a wavevector (|S| at Q = 1.000 for both, checked
offline), this run isolates explanation B. Setting MODE=noQ gives P1 a
non-commensurate line pitch instead, which isolates explanation A.

  both re-orient        -> neither A nor B; the operator's difficulty was dose
                           or trace speed, not geometry
  only the lattice      -> B: the pulsing matters, not the wavevector
  MODE=noQ, only P2     -> A: the commensurate wavevector matters

Diagnostic driver: campaign_state.json is untouched; write minutes are printed
for the ledger.
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
import template_lib as T

SIZE_UM = 5.0
PX = 256
RATE = A.TIP_SPEED_MAX / (2.0 * SIZE_UM)
V = 10.0
STEP = 0.02
SPEED = 0.5
HALF = 0.70
PC = ((1.5, 2.5), (3.5, 2.5))
CC = ((1.5, 0.85), (3.5, 0.85), (1.5, 4.15), (3.5, 4.15))
PRE_C = (2.5, 2.5)
PRE_HALF = (1.7, 2.35)            # covers every measurement window
MAX_MIN = 26.0
CHG_MAX = 20.0

XOFF = float(os.environ.get('AREA_X', '8.0'))
YOFF = float(os.environ.get('AREA_Y', '8.0'))
SIGMA = float(os.environ.get('SIGMA', '667'))
MODE = os.environ.get('MODE', 'sameQ').strip()
SKIP_PRE = os.environ.get('SKIP_PRE', '') not in ('', '0')
STAMP = time.strftime('%y%m%d_%H%M')


def windows():
    return ([('P%d' % (i + 1), c[0], c[1]) for i, c in enumerate(PC)]
            + [('ctrl%d' % (i + 1), c[0], c[1]) for i, c in enumerate(CC)])


def analyse(tag, g):
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    amp = np.abs(np.asarray(d[1], float))
    L = float(h['ScanSize']) * 1e6
    px = L / S.shape[0] * 1000.0
    tri, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    out = {}
    n = S.shape[0]
    hp = int(round(HALF * 1000.0 / px))
    for lab, cx, cy in windows():
        ci, cj = int(round(cx * 1000.0 / px)), int(round(cy * 1000.0 / px))
        j0 = max(0, min(n - 2 * hp, cj - hp))
        i0 = max(0, min(n - 2 * hp, ci - hp))
        sl = (slice(j0, j0 + 2 * hp), slice(i0, i0 + 2 * hp))
        p = g('pops')(S[sl], px)
        w = np.asarray(p[0], float)
        out[lab] = dict(w=w / w.sum(), dom=float(p[2]),
                        amp=1e12 * float(np.nanmean(amp[sl])))
    return out, [float(t) for t in tri], float(tt['mod']), px


def frame(g, what):
    c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                            angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                            tries=1, verbose=False)
    print('  %s -> %s (tune %.1f kHz)' % (what, inf['frame'], c / 1000.0))
    g('contact_check')(inf['frame'])
    return inf['frame']


def gate_and_write(ns, g, tb, label, npts):
    mins = npts * STEP / SPEED / 60.0
    xs, ys, vs = (np.asarray(a, float) for a in tb.to_arrays())
    print('  %s: %d pts -> %.1f min, |V|max %.1f, mean %+.2e'
          % (label, npts, mins, np.abs(vs).max(), vs.mean()))
    if mins > MAX_MIN:
        raise SystemExit('%s: %.1f min over the %.0f cap' % (label, mins, MAX_MIN))
    if abs(vs.mean()) > 1e-6:
        raise SystemExit('%s carries net DC %.2e' % (label, vs.mean()))
    if not (xs.min() >= 0 and ys.min() >= 0
            and xs.max() <= SIZE_UM and ys.max() <= SIZE_UM):
        raise SystemExit('%s leaves the frame' % label)
    budget_check(mins, 'RW_%s_%s' % (MODE, label))
    fn = os.path.join(A.PROJ, 'output', '%s_RW_%s.txt' % (STAMP, label))
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    return mins



def budget_check(minutes, label):
    """Refuse the write if S24 headroom cannot cover it; charge it if it can.

    S24 is a hard cumulative cap. These drivers do not create iterations, but
    their charge is just as real, and leaving it unbilled hid 71 minutes in one
    day. Returns the remaining headroom AFTER charging.
    """
    import json
    p = os.path.join(A.PROJ, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    used = float(st.get('total_write_min', 0.0))
    cap = float(getattr(A, 'MAX_TOTAL_WRITE_MIN', 330.0))
    left = cap - used
    print('  S24 budget: %.1f of %.0f used, %.1f left; this write needs %.1f'
          % (used, cap, left, minutes))
    if minutes > left:
        raise SystemExit('S24: %.1f min needed but only %.1f left. Halt.'
                         % (minutes, left))
    st['total_write_min'] = used + minutes
    st.setdefault('diagnostic_writes', []).append(
        dict(label=label, minutes=round(float(minutes), 2),
             area=[XOFF, YOFF], sample_position=st.get('sample_position'),
             stamp=time.strftime('%Y-%m-%d %H:%M')))
    json.dump(st, io.open(p, 'w', encoding='utf-8'), indent=2)
    return left - minutes


def main():
    print('=' * 74)
    print('REWRITE MECHANISM  MODE=%s  %s'
          % (MODE, time.strftime('%Y-%m-%d %H:%M')))
    print('=' * 74)
    print('  area (%+.1f,%+.1f), sigma %.0f' % (XOFF, YOFF, SIGMA))
    print('  stage 1 pre-orders the zone; stage 2 tries to rewrite it with a')
    print('  continuous TRACE and a pulsed LATTICE, side by side.')

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    if os.path.exists(A.STOP):
        raise SystemExit('STOP file present')
    try:
        print('  live deflection %+.3f V' % float(ns['exp'].read_meter()[1]))
    except Exception as e:
        print('  meter unreadable: %s' % e)

    total_min = 0.0

    # ---------------------------------------------------------- frame 1
    print('\n--- frame 1: virgin ---')
    f1 = frame(g, 'virgin')
    r1, triad, mod1, px = analyse(f1, g)
    _cw = np.mean([r1[l]['w'] for l in r1 if l.startswith('ctrl')], axis=0)
    incumbent = float(triad[int(np.argmax(_cw))])
    print('    triad %s, modulation %.3f, incumbent %.0f deg'
          % ([int(round(t)) for t in triad], mod1, incumbent))
    d, h = g('ibw')(f1)
    S, _, _ = g('signed')(d)
    lam = []
    for t in triad:
        v = g('period')(S, px, t)
        lam.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray)) else float(v))
    lam = [x for x in lam if x == x]
    LAM = float(np.median(lam)) / 1000.0
    print('    Lambda %.0f nm (sp %.0f nm)' % (LAM * 1000, LAM * 500))

    # A = the member furthest from the incumbent, so stage 1 does real work
    order = sorted(triad, key=lambda t: -abs((t - incumbent + 90) % 180 - 90))
    ANG_A = float(order[0])
    ANG_B = float(order[1])
    print('    stage 1 will order along A = %.0f deg' % ANG_A)
    print('    stage 2 will try to rewrite to B = %.0f deg' % ANG_B)

    # ---------------------------------------------------------- stage 1
    if not SKIP_PRE:
        print('\n--- stage 1: pre-order the zone (lines along %.0f) ---' % ANG_A)
        sites = T.parallel(PRE_C, PRE_HALF, LAM, ANG_A, V)
        area = (2 * PRE_HALF[0]) * (2 * PRE_HALF[1])
        dwell = SIGMA * area / (len(sites) * V)
        pn = max(1, int(round(dwell * SPEED / STEP)))
        dwell = pn * STEP / SPEED
        q = V * dwell
        print('  %d sites over %.1f um^2, %d pulses/site, %.1f V.s/site'
              % (len(sites), area, pn, q))
        if q > CHG_MAX:
            raise SystemExit('pre-order %.1f V.s/site over the %.0f limit'
                             % (q, CHG_MAX))
        tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
        for (x0, y0, v0) in sites:
            tb.dwell((x0, y0), v0, n=pn)
        total_min += gate_and_write(ns, g, tb, 'stage1', len(sites) * pn)

        print('\n--- frame 2: after pre-ordering ---')
        f2 = frame(g, 'ordered')
        r2, triad2, mod2, _ = analyse(f2, g)
        print('    triad %s, modulation %.3f -> %.3f'
              % ([int(round(t)) for t in triad2], mod1, mod2))
        print('    %-7s %-22s %s' % ('window', 'w after stage 1', 'dominant'))
        for lab, _a, _b in windows():
            print('    %-7s %-22s %.0f deg'
                  % (lab, np.round(r2[lab]['w'], 3), r2[lab]['dom']))
        _ow = np.mean([r2[l]['w'] for l in r2 if l.startswith('ctrl')], axis=0)
        print('    ordered-zone mean population %s -> dominant %.0f deg'
              % (np.round(_ow, 3), triad2[int(np.argmax(_ow))]))
        if float(np.max(_ow)) < 0.45:
            print('    !! the zone is NOT convincingly ordered (max w %.2f).'
                  % float(np.max(_ow)))
            print('       Stage 2 would then be testing rewriting of a')
            print('       disordered region, which is a different question.')
    else:
        # the area was pre-ordered by an earlier run, so frame 1 IS the ordered
        # state; use it as the stage-2 reference rather than as a virgin one
        r2, triad2, mod2 = r1, triad, mod1
        _ow = np.mean([r2[l]['w'] for l in r2 if l.startswith('ctrl')], axis=0)
        print('\n--- stage 1 SKIPPED: this area is already ordered ---')
        print('    ordered-zone mean population %s -> dominant %.0f deg'
              % (np.round(_ow, 3), triad[int(np.argmax(_ow))]))
        if float(np.max(_ow)) < 0.45:
            print('    !! max w %.2f: not convincingly ordered.'
                  % float(np.max(_ow)))

    # ---------------------------------------------------------- stage 2
    print('\n--- stage 2: rewrite attempts, lines along B = %.0f ---' % ANG_B)
    tb2 = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    npts2 = 0
    specs = []

    # P1: continuous trace
    pitch_note = 'same Q as the lattice'
    lam_trace = LAM
    if MODE == 'noQ':
        lam_trace = LAM * 0.62          # line pitch off the commensurate value
        pitch_note = 'NON-commensurate pitch (%.0f nm vs Lambda %.0f)' % (
            lam_trace * 500, LAM * 1000)
    strokes = T.trace_lines(PC[0], HALF, lam_trace, ANG_B, V)
    npass, per = T.trace_passes(SIGMA, lam_trace, V, SPEED)

    # Sample each stroke into STEP-spaced points explicitly. The output file is
    # the same as tb.stroke would produce -- the tip still moves continuously,
    # visiting each point once -- but the point count per polarity is now known
    # and can be balanced exactly. Net charge is sum(V) over POINTS, not over
    # length, and balancing length left a residue of +1.16e-2 that the DC gate
    # correctly refused.
    def sample(pts):
        a = np.asarray(pts[0], float)
        b = np.asarray(pts[1], float)
        L = float(np.hypot(*(b - a)))
        k = max(2, int(round(L / STEP)) + 1)
        return [tuple(a + (b - a) * t) for t in np.linspace(0.0, 1.0, k)]

    tr_pts = [(sample(pts), vv) for pts, vv in strokes]
    n_pos = sum(len(p) for p, vv in tr_pts if vv > 0)
    n_neg = sum(len(p) for p, vv in tr_pts if vv < 0)
    # drop whole points from the longer polarity, from the ends of its longest
    # strokes, until the two counts agree exactly
    while n_pos != n_neg:
        want = +1.0 if n_pos > n_neg else -1.0
        cand = [i for i, (p, vv) in enumerate(tr_pts)
                if np.sign(vv) == want and len(p) > 2]
        if not cand:
            raise SystemExit('cannot balance the trace: %d + vs %d - points'
                             % (n_pos, n_neg))
        i = max(cand, key=lambda k: len(tr_pts[k][0]))
        tr_pts[i] = (tr_pts[i][0][:-1], tr_pts[i][1])
        n_pos = sum(len(p) for p, vv in tr_pts if vv > 0)
        n_neg = sum(len(p) for p, vv in tr_pts if vv < 0)
    assert n_pos == n_neg, 'trace point counts still unbalanced'

    for _ in range(npass):
        for p_, vv in tr_pts:
            for q_ in p_:
                tb2.dwell((float(q_[0]), float(q_[1])), vv, n=1)
    tlen = sum(float(np.hypot(p[1][0] - p[0][0], p[1][1] - p[0][1]))
               for p, _v in strokes)
    n1 = npass * (n_pos + n_neg)
    npts2 += n1
    print('  P1 trace points %d + / %d - per pass, balanced exactly'
          % (n_pos, n_neg))
    print('  P1 TRACE    %d strokes x %d passes, %s' % (len(strokes), npass, pitch_note))
    print('              %.1f um per pass, sigma %.0f' % (tlen, npass * per))
    specs.append(('P1', 'trace', ANG_B, npass * per))

    # P2: pulsed lattice, same angle and dose
    sites2 = T.parallel(PC[1], HALF, LAM, ANG_B, V)
    area2 = (2 * HALF) ** 2
    dw2 = SIGMA * area2 / (len(sites2) * V)
    pn2 = max(1, int(round(dw2 * SPEED / STEP)))
    dw2 = pn2 * STEP / SPEED
    q2 = V * dw2
    if q2 > CHG_MAX:
        raise SystemExit('P2 %.1f V.s/site over the %.0f limit' % (q2, CHG_MAX))
    for (x0, y0, v0) in sites2:
        tb2.dwell((x0, y0), v0, n=pn2)
    npts2 += len(sites2) * pn2
    print('  P2 LATTICE  %d sites, %d pulses/site, %.1f V.s/site, sigma %.0f'
          % (len(sites2), pn2, q2, len(sites2) * q2 / area2))
    specs.append(('P2', 'lattice', ANG_B, len(sites2) * q2 / area2))

    total_min += gate_and_write(ns, g, tb2, 'stage2', npts2)

    # ---------------------------------------------------------- frame 3
    print('\n--- frame 3: after the rewrite attempts ---')
    f3 = frame(g, 'rewritten')
    r3, triad3, mod3, _ = analyse(f3, g)

    print('\n' + '=' * 74)
    print('RESULT  MODE=%s   target B = %.0f deg' % (MODE, ANG_B))
    print('=' * 74)
    print('  triad %s | modulation virgin %.3f -> ordered %.3f -> after %.3f'
          % ([int(round(t)) for t in triad3], mod1,
             mod2 if not SKIP_PRE else float('nan'), mod3))
    print('\n  %-7s %-20s %-20s %-20s %s'
          % ('window', 'w virgin', 'w ordered', 'w after', 'dom o->a'))
    for lab, _a, _b in windows():
        print('  %-7s %-20s %-20s %-20s %3.0f->%3.0f'
              % (lab, np.round(r1[lab]['w'], 3), np.round(r2[lab]['w'], 3),
                 np.round(r3[lab]['w'], 3), r2[lab]['dom'], r3[lab]['dom']))

    ck = [l for l in r2 if l.startswith('ctrl')]
    dC = np.mean([r3[l]['w'] - r2[l]['w'] for l in ck], axis=0)
    null = float(np.max([np.max(np.abs((r3[l]['w'] - r2[l]['w']) - dC))
                         for l in ck]))
    print('\n  control (ordered, not rewritten) mean change %s | null %.3f'
          % (np.round(dC, 3), null))

    verdict = {}
    for (lab, kind, ang, sig) in specs:
        ex = (r3[lab]['w'] - r2[lab]['w']) - dC
        m = float(np.max(np.abs(ex)))
        cleared = m > 2 * max(null, 1e-3)
        verdict[lab] = (kind, cleared, m, r3[lab]['dom'])
        print('  %s %-8s excess %s  max %.3f = %.1fx null -> %s'
              % (lab, kind, np.round(ex, 3), m, m / max(null, 1e-9),
                 'REWROTE' if cleared else 'did NOT rewrite'))

    print('\n  --- mechanism ---')
    tr = verdict['P1']; la = verdict['P2']
    if not tr[1] and not la[1]:
        print('  Neither template rewrote the ordered region. No positive')
        print('  control in this frame, so this says nothing about mechanism;')
        print('  it says the dose was too low to rewrite ORDERED film, which')
        print('  is itself worth knowing but needs a higher-dose repeat.')
    elif la[1] and not tr[1]:
        if MODE == 'noQ':
            print('  The pulsed lattice rewrote the ordered region and the')
            print('  NON-commensurate trace did not. Consistent with')
            print('  explanation A: the commensurate wavevector is what')
            print('  matters. It does NOT separate A from B, because this')
            print('  trace differs from the lattice in both respects.')
        else:
            print('  The pulsed lattice rewrote the ordered region and the')
            print('  continuous trace did not -- even though both carried the')
            print('  SAME wavevector Q, the same line spacing and the same')
            print('  dose. Explanation A is excluded. **The pulsing itself is')
            print('  what rewrites an ordered domain**: stationary, repeated')
            print('  pulses nucleate a new orientation where a moving biased')
            print('  tip cannot.')
    elif tr[1] and not la[1]:
        print('  The trace rewrote and the lattice did not, which is the')
        print('  reverse of the reported behaviour. Treat this run as')
        print('  suspect and check the two panels were not swapped.')
    else:
        print('  BOTH templates rewrote the ordered region (trace %.1fx, '
              'lattice %.1fx null).' % (tr[2] / max(null, 1e-9),
                                        la[2] / max(null, 1e-9)))
        print('  At matched dose and matched Q a continuous trace CAN')
        print('  re-orient an ordered domain, so the difficulty reported in')
        print('  practice is not intrinsic to tracing. The likely difference')
        print('  is dose: a trace at ordinary scan speed delivers far less')
        print('  charge per area than it appears to. Here it took %d passes'
              % npass)
        print('  at %.2f um/s to reach sigma %.0f.' % (SPEED, SIGMA))
        print('  P1 -> %.0f deg, P2 -> %.0f deg, target %.0f'
              % (tr[3], la[3], ANG_B))

    print('\n  write minutes: %.1f total (stage1 + stage2)' % total_min)


if __name__ == '__main__':
    buf = io.StringIO()

    class Tee(object):
        def __init__(self, *s):
            self.s = s

        def write(self, x):
            for t in self.s:
                t.write(x)
                t.flush()

        def flush(self):
            for t in self.s:
                t.flush()

    import contextlib
    try:
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            main()
    except Exception:
        traceback.print_exc()
    finally:
        io.open(os.path.join(A.PROJ, 'rewrite_%s_%s.txt' % (MODE, STAMP)), 'w',
                encoding='utf-8').write(buf.getvalue())
