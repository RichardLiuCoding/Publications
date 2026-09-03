# -*- coding: utf-8 -*-
"""IT9 - can a written state be REWRITTEN, and does it stay written?

TWO QUESTIONS NOTHING IN THIS CAMPAIGN HAS ASKED
    Every iteration so far has written once and read once. Two things follow
    that a memory application turns on entirely, and neither is known:

      RETENTION    does a panel written to director X still read X an hour
                   later, after the tip has scanned over it repeatedly?
      REVERSIBILITY can a panel written to X be rewritten to Y? Or does the
                   first write leave the film in a state that resists further
                   selection - which is what C27 hints at, having found that
                   pre-poling makes the pulse lattice WORSE rather than better.

    If selection is not reversible the technique writes once and is a fuse, not
    a memory. That is worth knowing before anyone builds on it.

THE DESIGN
    Two panels, written in two stages, plus untouched tiles as always.

      STAGE 1   both panels get an identical lattice commanded 60 deg from
                their own local dominant. Read.
      STAGE 2   only panel RW is written again, now commanded BACK toward its
                original director. Panel HOLD is left alone. Read again.

    So one panel measures reversibility (does it come back?) and the other
    measures retention over the same interval (does it drift on its own?),
    with the same frames, the same tiles and the same threshold for both. The
    HOLD panel is what makes the RW result interpretable: without it, a return
    to the original director could just be relaxation.

PREDICTIONS, fixed before the write
    RW returns, HOLD holds     fully reversible and non-volatile. This is the
                               result that makes the effect a memory: three
                               addressable states, written and rewritten at
                               will.
    RW returns, HOLD drifts    reversible but volatile - the state relaxes on
                               its own, and stage 2's apparent success is
                               partly relaxation. Report the difference.
    RW does not return         the first write is not undoable at this sigma.
                               Selection has a history dependence, consistent
                               with C27. Write-once.
    neither moves in stage 1   void - no state was written, so nothing can be
                               said about rewriting it.

SAFETY
    Unchanged. Both stages are charge-balanced lattices under the usual guards:
    10 V ceiling, V.s per site under half C21s single-pulse threshold, the
    26 min per-write cap, scanner range, footprint, flatness, static audit. The
    only thing new is writing the same place twice, which is exactly the point.
"""
import io
import os
import sys
import time
import contextlib
import traceback
import numpy as np
import autoloop as A

FRAME, PX = 12.0, 256
RATE = A.TIP_SPEED_MAX / (2.0 * FRAME)
V, STEP, SPEED, R_EFF = 10.0, 0.02, 0.5, 0.625
SIGMA_RATIO = 1.3
MOD_MIN = 0.18
FLAT_REL = 1.5
N_MULT = 16

buf = io.StringIO()


class Tee(object):
    def __init__(self, *s):
        self.s = s

    def write(self, x):
        for t in self.s:
            t.write(x)
            try:
                t.flush()
            except Exception:
                pass

    def flush(self):
        for t in self.s:
            t.flush()


def meter(ns, tag):
    try:
        w = ns['exp'].read_meter()
        v = np.atleast_1d(np.asarray(w, dtype=float)).ravel()
        print('  meter %-16s defl %+.3f' % (tag, v[1] if len(v) > 1
                                            else float('nan')))
        return [float(q) for q in v[:6]]
    except Exception as e:
        print('  meter %-16s unavailable (%s)' % (tag, type(e).__name__))
        return None


def flatness(d, cx, cy, half, frame):
    z = np.asarray(d, float)
    while z.ndim > 2:
        z = z[0]
    if z.ndim != 2:
        return float('nan')
    if np.nanmax(np.abs(z)) < 1e-3:
        z = z * 1e9
    ny, nx = z.shape
    i0 = max(int((cy - half) / frame * ny), 0)
    i1 = min(int((cy + half) / frame * ny) + 1, ny)
    j0 = max(int((cx - half) / frame * nx), 0)
    j1 = min(int((cx + half) / frame * nx) + 1, nx)
    sub = z[i0:i1, j0:j1]
    if sub.size < 9:
        return float('nan')
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    Am = np.c_[xx.ravel(), yy.ravel(), np.ones(sub.size)]
    c, *_ = np.linalg.lstsq(Am, sub.ravel(), rcond=None)
    return float(np.ptp(sub - (c[0] * xx + c[1] * yy + c[2])))


def main():
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT9  rewrite and retention   %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    if os.path.exists(A.STOP):
        raise SystemExit('STOP present')
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    print('\n--- preflight, pass 1 ---')
    ok, fails = A.preflight(PROP, st, ns)
    if not ok:
        raise SystemExit('preflight: %s' % '; '.join(fails))

    # ------------------------------------------------------ a fresh area
    cands = A.legal_offsets(st, FRAME, step=2.0)
    prev = tuple(st['used_areas'][-1][0]) if st['used_areas'] else (0.0, 0.0)
    cands.sort(key=lambda c: (c[0] - prev[0]) ** 2 + (c[1] - prev[1]) ** 2)
    print('\n%d legal offsets; nearest first' % len(cands))
    meter(ns, 'at start')
    viable = []
    for att, (xo, yo) in enumerate(cands[:3]):
        print('\n--- candidate %d: (%+.1f,%+.1f) ---' % (att + 1, xo, yo))
        g('scanner_ok')(xo, yo, FRAME)
        okf, notes = A.check_area_fresh(st, xo, yo, FRAME)
        if not okf:
            print('  not usable: %s' % notes)
            continue
        g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                        xoff_um=xo, yoff_um=yo)
        centre, tv = g('tune_here')('ldart', size_um=FRAME, px=PX, rate=RATE,
                                    xoff_um=xo, yoff_um=yo)
        scr = tv['frame']
        triad_t, tt = g('pin_triad')(scr, ref_fam=g('FAM_FILM'))
        with contextlib.redirect_stdout(io.StringIO()):
            sk = g('streak_index')(scr, (0.35, FRAME - 0.35, 0.35, 1.7))
        print('  modulation %.3f (need >= %.2f), streak %.3f'
              % (tt['mod'], MOD_MIN, sk))
        if tt['mod'] < MOD_MIN or sk > A.STREAK_MAX:
            print('  -> rejected')
            continue
        print('  -> viable')
        viable.append(dict(xo=xo, yo=yo, scr=scr, mod=tt['mod'],
                           triad=[float(v) for v in triad_t]))
    if not viable:
        raise SystemExit('no candidate area passed. Move the coarse stage.')
    viable.sort(key=lambda c: -c['mod'])
    chosen = viable[0]
    XOFF, YOFF, triad = chosen['xo'], chosen['yo'], chosen['triad']
    PX_NM = FRAME / PX * 1000.0
    print('\n=== area (%+.1f,%+.1f), triad %s, modulation %.3f ==='
          % (XOFF, YOFF, ['%.0f' % t for t in triad], chosen['mod']))

    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_ldart')()
    b1 = g('frame')()
    b2 = g('frame')()
    g('contact_check')(b2)
    meter(ns, 'after baselines')
    F_REF, _ = g('pick_ref')([b1, b2], [(0.4, FRAME - 0.4, 0.4, FRAME - 0.4)])
    d, _ = g('ibw')(F_REF)
    S, _, _ = g('signed')(d)
    lm = []
    for f in triad:
        v = g('period')(S, PX_NM, f)
        lm.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                  else float(v))
    lm = [v for v in lm if v == v]
    LAM = float(np.median(lm))
    sp = LAM / 2000.0
    WIN = float(max(4.2 * LAM / 1000.0, 26 * PX_NM / 1000.0))
    g('window_check')(WIN, PX_NM, LAM, name='readout window')
    print('  Lambda %.0f nm, spacing %.0f nm, window %.2f um'
          % (LAM, sp * 1000, WIN))

    # ------------------------------------------------------ two slots
    ANGF = {t: abs(np.cos(np.deg2rad(t))) + abs(np.sin(np.deg2rad(t)))
            for t in triad}
    ang = min(ANGF.values())
    n0 = int(max(N_MULT, N_MULT * round(((WIN * ang + 2 * (sp + 0.10)) / sp + 1)
                                        / float(N_MULT))))
    halo = (n0 - 1) * sp * ang / 2 + R_EFF
    pitch = 2 * halo + 0.10
    xs = [FRAME / 2 - pitch / 2, FRAME / 2 + pitch / 2]
    ys = [0.35 + WIN + 0.05 + halo]
    slots = [(x, ys[0]) for x in xs]
    if any(x - halo < 0.05 or x + halo > FRAME - 0.05 for x in xs) \
            or ys[0] + halo > FRAME - 0.05:
        raise SystemExit('two panels do not fit: halo %.2f, pitch %.2f'
                         % (halo, pitch))
    print('\n  n %d, halo %.2f, pitch %.2f, slots %s'
          % (n0, halo, pitch, ['(%.2f,%.2f)' % s for s in slots]))
    dref, _ = g('ibw')(F_REF)
    rngs = [flatness(dref, sx, sy, halo, FRAME) for (sx, sy) in slots]
    print('  slot height ranges: %s nm' % ['%.1f' % r for r in rngs])

    cm = []
    for (cx, cy) in slots:
        best = None
        for sense in (+1, -1):
            cf = g('command_for')(F_REF, cx, cy, WIN, triad, sense=sense,
                                  min_lead=0.05, verbose=False)
            if cf and (best is None or ANGF[cf['cmd']] < ANGF[best['cmd']]):
                best = cf
        if best is None:
            raise SystemExit('slot (%.2f,%.2f) is not measurable' % (cx, cy))
        cm.append(best)
    # RW is the panel that gets rewritten; give it the better-matched slot when
    # the two differ, because it carries the question.
    order = sorted(range(2), key=lambda i: ANGF[cm[i]['cmd']])
    lab_of = {order[0]: 'RW', order[1]: 'HOLD'}
    print('\n  %-5s%10s%10s%10s  %s'
          % ('', 'slot', 'dominant', 'command', 'role'))
    for i in range(2):
        print('  %-5s%10s%10.0f%10.0f  %s'
              % (lab_of[i], '(%.1f,%.1f)' % slots[i], cm[i]['dom'],
                 cm[i]['cmd'],
                 'rewritten in stage 2' if lab_of[i] == 'RW'
                 else 'left alone - retention control'))

    dwell = SIGMA_RATIO * sc * sp ** 2 / V
    pn = max(1, int(round(dwell * SPEED / STEP)))
    dwell = pn * STEP / SPEED
    sigma = (1 / sp ** 2) * V * dwell
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.1f V.s per site over half C21s %.0f'
                         % (V * dwell, A.CHG_1PULSE_MAX))
    print('\n  sigma %.0f = %.2f sigma_c, dwell %.2f s, %.1f V.s per site'
          % (sigma, sigma / sc, dwell, V * dwell))

    def write(which, cmds, tag):
        """One charge-balanced write over the given slots."""
        tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP,
                                     travel_v=0.0)
        tot = 0
        for i in which:
            sites = g('lattice_panel')(n0, sp, slots[i], cmds[i], V,
                                       sign_every=1, keep_frac=1.0)
            vv = np.array([q[2] for q in sites])
            assert abs(vv.mean()) < 1e-9, 'panel not balanced'
            for (x, y, v0) in sites:
                tb.dwell((x, y), v0, n=pn)
            tot += len(sites)
        X, Y, Vv = tb.to_arrays()
        mins = len(Vv) * STEP / SPEED / 60.0
        print('  %s: %d sites over %d panel(s), %d pts, mean V %+.6f, %.1f min'
              % (tag, tot, len(which), len(Vv), Vv.mean(), mins))
        if abs(Vv.mean()) > 1e-6:
            raise SystemExit('%s carries net DC' % tag)
        if np.abs(Vv).max() > A.V_CEILING + 1e-9:
            raise SystemExit('%s over the voltage ceiling' % tag)
        if X.min() < 0.05 or Y.min() < 0.05 or X.max() > FRAME - 0.05 \
                or Y.max() > FRAME - 0.05:
            raise SystemExit('%s leaves the frame' % tag)
        if mins > A.MAX_WRITE_MIN:
            raise SystemExit('%s needs %.1f min against a %.0f min cap'
                             % (tag, mins, A.MAX_WRITE_MIN))
        fn = os.path.join(A.PROJ, 'output', '260822_IT9_%s.txt' % tag)
        g('goto_ldart')()
        g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
        st['total_write_min'] = st.get('total_write_min', 0.0) + mins
        A.save_state(st)
        g('goto_ldart')()
        return mins

    # ---- tiles, once, clear of both panels ---------------------------
    step_t = WIN + 0.10
    cand_t, yc = [], 0.35
    while yc + WIN <= FRAME - 0.35 + 1e-9:
        cand_t += g('ctrl_tiles')(0.35, FRAME - 0.35, yc, yc + WIN, WIN)
        yc += step_t
    tiles = [rg for rg in cand_t
             if all(rg[1] < sx - halo - 0.05 or rg[0] > sx + halo + 0.05
                    or rg[3] < sy - halo - 0.05 or rg[2] > sy + halo + 0.05
                    for (sx, sy) in slots)]
    tr = [flatness(dref, 0.5 * (r[0] + r[1]), 0.5 * (r[2] + r[3]),
                   0.5 * WIN, FRAME) for r in tiles]
    fin = [v for v in tr if v == v]
    cut = FLAT_REL * float(np.median(fin)) if fin else float('inf')
    keep = [r for r, v in zip(tiles, tr) if v == v and v <= cut]
    if len(keep) >= 8:
        tiles = keep
    print('\n  %d control tiles clear of both panels (terrace filter kept %d)'
          % (len(tiles), len(keep)))

    ds = g('dir_state')

    def excess(after, before, i, cmd):
        """Panel-minus-tiles contrast, corrected with the same contrast before,
        and 2 sd of that statistic measured leave-one-out at the tiles (C45)."""
        wa, wb = [], []
        for rg in tiles:
            tx, ty = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
            sa = ds(after, tx, ty, WIN, triad, cmd)
            sb = ds(before, tx, ty, WIN, triad, cmd)
            if sa and sb:
                wa.append(sa['w_cmd'])
                wb.append(sb['w_cmd'])
        wa, wb = np.array(wa), np.array(wb)
        n = len(wa)
        dd = np.empty(n)
        for k in range(n):
            m = np.ones(n, bool)
            m[k] = False
            dd[k] = (wa[k] - wa[m].mean()) - (wb[k] - wb[m].mean())
        thr = float(2.0 * dd.std(ddof=1))
        sa = ds(after, slots[i][0], slots[i][1], WIN, triad, cmd)
        sb = ds(before, slots[i][0], slots[i][1], WIN, triad, cmd)
        exc = ((sa['w_cmd'] - wa.mean()) - (sb['w_cmd'] - wb.mean()))
        return dict(excess=float(exc), thr=thr, x=float(exc / max(thr, 1e-9)),
                    dom=float(sa['dom']), w_cmd=float(sa['w_cmd']),
                    dom_before=float(sb['dom']), dmax=float(np.abs(dd).max()))

    # ============================================== STAGE 1: write both
    cmd1 = [float(c['cmd']) for c in cm]
    print('\n=== STAGE 1: write both panels, commanded %s ==='
          % ['%.0f' % c for c in cmd1])
    m1 = write([0, 1], cmd1, 'stage1')
    a1 = g('frame')()
    meter(ns, 'after stage 1')
    g('contact_check')(a1)
    r1 = {}
    for i in range(2):
        r1[lab_of[i]] = excess(a1, F_REF, i, cmd1[i])
        q = r1[lab_of[i]]
        print('  %-5s commanded %.0f: dominant %.0f -> %.0f, w %.3f, excess '
              '%+.3f = %.1f x %s'
              % (lab_of[i], cmd1[i], q['dom_before'], q['dom'], q['w_cmd'],
                 q['excess'], q['x'],
                 'SWITCHED' if q['x'] > 1 else 'not resolved'))
    if not any(r1[k]['x'] > 1 for k in r1):
        print('\n  VOID: neither panel switched in stage 1, so there is no')
        print('  written state to rewrite. Stopping before stage 2 rather than')
        print('  spending a second write on a question that cannot be asked.')
        st['iteration'] = st.get('iteration', 0) + 1
        A.save_state(st)
        return dict(readable=False, stage1=r1, void=True,
                    area=[XOFF, YOFF], lam=LAM), m1

    # ============================================== STAGE 2: rewrite RW
    i_rw = [i for i in range(2) if lab_of[i] == 'RW'][0]
    i_hold = 1 - i_rw
    # command RW back toward the director it started from
    back = float(r1['RW']['dom_before'])
    cmd2 = list(cmd1)
    cmd2[i_rw] = back
    print('\n=== STAGE 2: rewrite RW back toward %.0f deg (it started there, '
          'went to %.0f) ===' % (back, r1['RW']['dom']))
    print('  HOLD is left alone over the same interval, so retention and')
    print('  reversibility are measured on the same frames.')
    m2 = write([i_rw], cmd2, 'stage2')
    a2 = g('frame')()
    meter(ns, 'after stage 2')
    g('contact_check')(a2)
    a3 = g('frame')()

    print('\n=== RESULT ===')
    rw_back = excess(a2, F_REF, i_rw, back)
    rw_still = excess(a2, F_REF, i_rw, cmd1[i_rw])
    hold_now = excess(a2, F_REF, i_hold, cmd1[i_hold])
    print('  RW, scored toward its ORIGINAL director %.0f: dominant %.0f, '
          'w %.3f, excess %+.3f = %.1f x'
          % (back, rw_back['dom'], rw_back['w_cmd'], rw_back['excess'],
             rw_back['x']))
    print('  RW, still scored toward stage 1s command %.0f: w %.3f, excess '
          '%+.3f = %.1f x'
          % (cmd1[i_rw], rw_still['w_cmd'], rw_still['excess'], rw_still['x']))
    print('  HOLD, untouched since stage 1, toward %.0f: w %.3f (was %.3f), '
          'excess %+.3f = %.1f x, dominant %.0f'
          % (cmd1[i_hold], hold_now['w_cmd'], r1['HOLD']['w_cmd'],
             hold_now['excess'], hold_now['x'], hold_now['dom']))

    res = dict(readable=True, area=[XOFF, YOFF], lam=LAM, window=WIN,
               sigma=sigma, sigma_over_c=sigma / sc, dwell=dwell, n=n0,
               triad=triad, slots=[list(s) for s in slots],
               roles={str(i): lab_of[i] for i in range(2)},
               cmd1=cmd1, cmd2=cmd2, back=back,
               stage1=r1, rw_back=rw_back, rw_still=rw_still,
               hold_now=hold_now, minutes=m1 + m2,
               frames=dict(baseline=[b1, b2], ref=F_REF, after1=a1,
                           after2=[a2, a3]))

    print('\n' + '=' * 74)
    print('IT9 VERDICT')
    print('=' * 74)
    rev = rw_back['x'] > 1 and abs((rw_back['dom'] - back + 90) % 180 - 90) < 20
    held = hold_now['x'] > 1 and abs((hold_now['dom'] - cmd1[i_hold] + 90)
                                     % 180 - 90) < 20
    print('  stage 1 wrote both panels: RW %.1f x, HOLD %.1f x'
          % (r1['RW']['x'], r1['HOLD']['x']))
    print('  reversible: %s   retained: %s' % (rev, held))
    if rev and held:
        print('\n  -> REVERSIBLE AND NON-VOLATILE. RW was driven to %.0f deg,'
              % r1['RW']['dom'])
        print('     then back to %.0f by a second lattice, while HOLD stayed'
              % rw_back['dom'])
        print('     where stage 1 put it over the same interval and the same')
        print('     scans. So the director is a rewritable state variable, not')
        print('     a one-shot change: three addressable states, set and reset')
        print('     at will. This is the result that makes the effect a memory.')
        print('     NEXT: cycle it. Ten writes alternating between two members,')
        print('     watching for fatigue.')
    elif rev and not held:
        print('\n  -> REVERSIBLE BUT VOLATILE. RW came back, but HOLD did not')
        print('     stay put either (%.1f x, dominant %.0f), so part of what'
              % (hold_now['x'], hold_now['dom']))
        print('     looks like a successful rewrite is relaxation over the')
        print('     interval. The honest statement is that the state decays;')
        print('     measure the time constant before claiming a rewrite.')
    elif held and not rev:
        print('\n  -> WRITE-ONCE. HOLD kept its state, so the readout and the')
        print('     interval are fine - but RW would not go back (%.1f x'
              % rw_back['x'])
        print('     toward %.0f, dominant still %.0f). The first write leaves'
              % (back, rw_back['dom']))
        print('     the film in a state that resists further selection, which')
        print('     is what C27 saw when pre-poling made the lattice worse.')
        print('     Selection is history-dependent, and the technique writes')
        print('     once at this sigma. NEXT: does a higher sigma overwrite?')
    else:
        print('\n  -> neither reversible nor retained on this measurement.')
        print('     Before drawing anything from that: HOLD failing means the')
        print('     interval or the readout moved, which also invalidates the')
        print('     RW comparison. Treat as inconclusive, check the meter log')
        print('     and the flatness report, and repeat with a shorter gap.')

    st['iteration'] = st.get('iteration', 0) + 1
    if PROP['name'] not in st['completed']:
        st['completed'].append(PROP['name'])
    A.save_state(st)

    note = ['### Stage 1 - write both panels', '',
            '| panel | commanded | dominant before | after | w(cmd) | excess | x threshold |',
            '|---|---|---|---|---|---|---|']
    for i in range(2):
        q = r1[lab_of[i]]
        note.append('| %s | %.0f deg | %.0f | **%.0f** | %.3f | %+.3f | %.1f |'
                    % (lab_of[i], cmd1[i], q['dom_before'], q['dom'],
                       q['w_cmd'], q['excess'], q['x']))
    note += ['', '### Stage 2 - rewrite RW back toward %.0f deg' % back, '',
             '| measurement | dominant | w | excess | x threshold |',
             '|---|---|---|---|---|',
             '| RW toward its original %.0f | **%.0f** | %.3f | %+.3f | %.1f |'
             % (back, rw_back['dom'], rw_back['w_cmd'], rw_back['excess'],
                rw_back['x']),
             '| RW still toward stage 1s %.0f | %.0f | %.3f | %+.3f | %.1f |'
             % (cmd1[i_rw], rw_still['dom'], rw_still['w_cmd'],
                rw_still['excess'], rw_still['x']),
             '| HOLD, untouched, toward %.0f | %.0f | %.3f | %+.3f | %.1f |'
             % (cmd1[i_hold], hold_now['dom'], hold_now['w_cmd'],
                hold_now['excess'], hold_now['x']),
             '',
             '**Reversible: %s. Retained: %s.** sigma %.2f sigma_c both '
             'stages; %d control tiles; threshold from the leave-one-out null '
             'of the statistic (C45).' % (rev, held, sigma / sc, len(tiles)),
             '',
             'HOLD is what makes RW interpretable: without a panel left alone '
             'over the same interval and the same scans, a return to the '
             'original director could simply be relaxation.']
    res['note'] = chr(10).join(note)
    return res, m1 + m2


PROP = dict(
    name='IT9_rewrite_and_retention',
    hypothesis=('Every iteration in this campaign has written once and read '
                'once, so two things a memory application depends on are '
                'completely unknown: whether a written director is RETAINED '
                'over an interval of repeated scanning, and whether it can be '
                'REWRITTEN to a different member. C27 is the reason to doubt '
                'the second - pre-poling made the pulse lattice worse, not '
                'better, which suggests selection carries a history.'),
    prediction=('Two panels get an identical lattice commanded 60 deg from '
                'their own dominant. Then one (RW) is written again, commanded '
                'back toward the director it started from, while the other '
                '(HOLD) is left alone over the same interval and the same '
                'scans. If the effect is a rewritable state variable, RW '
                'returns and HOLD stays. HOLD is the control that makes RW '
                'interpretable - without it a return could be relaxation.'),
    outcomes={'RW returns, HOLD holds':
              'reversible and non-volatile - three addressable states, set and '
              'reset at will. The effect is a memory',
              'RW returns, HOLD drifts':
              'reversible but volatile; part of the apparent rewrite is '
              'relaxation, and the state has a decay time worth measuring',
              'RW does not return, HOLD holds':
              'write-once at this sigma. Selection is history-dependent, '
              'consistent with C27',
              'neither':
              'inconclusive - HOLD failing invalidates the RW comparison too'},
    caveat=('The two panels sit in different places, so their starting '
            'populations differ and the stage-1 magnitudes are not strictly '
            'comparable; the better-matched slot is given to RW because it '
            'carries the question. Stage 2 is only written if stage 1 actually '
            'switched something - there is no point rewriting a state that was '
            'never written, and the script stops rather than spending the '
            'second write.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
    panels=[dict(label='RW', keep=1.0, dwell=None, sign_every=1,
                 spacing_div=2.0),
            dict(label='HOLD', keep=1.0, dwell=None, sign_every=1,
                 spacing_div=2.0)])

if __name__ == '__main__':
    try:
        with A.Lock():
            with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
                res, mins = main()
        stt = A.load_state()
        A.log_to_notebook(PROP, res, res.get('note'), buf.getvalue(),
                          stt['iteration'])
    except SystemExit as e:
        print('\nHALTED: %s' % e)
        A.say('IT9 halted: %s' % e)
    except Exception:
        print('\nFAILED:')
        traceback.print_exc()
        A.say('IT9 failed: %s' % traceback.format_exc().splitlines()[-1])
    finally:
        if os.path.exists(A.LOCK):
            os.remove(A.LOCK)
        io.open(os.path.join(A.PROJ, 'it9_console.txt'), 'w',
                encoding='utf-8').write(buf.getvalue())
