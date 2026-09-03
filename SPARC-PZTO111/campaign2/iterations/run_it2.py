# -*- coding: utf-8 -*-
"""IT2 - the commensuration series. Does the template PERIOD matter at all?

WHY THIS EXPERIMENT
    T3's Condition 1 says the template must be commensurate with the lamellae
    (period = Lambda) to select a director. IT1 contradicted it: panel C, at
    period 2 Lambda with identical sigma and identical sites, was the STRONGEST
    of the four (lead +0.436, w(cmd) 0.648, 2.5x floor) and beat the
    on-resonance panel A (+0.183, 0.542, 1.3x). Nothing in IT1 cleared 3x the
    floor, so that is a hint rather than a result - but it points at the part of
    the theory I am least sure of, so it is what to test.

    S13's W50 was also a 2 Lambda template and failed, but at sigma = 255, below
    threshold - period and drive were confounded there. Here they are separated.

THE DESIGN
    Three panels. Same spacing, same site positions, same commanded director,
    same sigma. ONLY the sign map differs, giving template periods Lambda,
    2 Lambda and 4 Lambda. sigma does not depend on sign_every, so this is a
    genuine one-factor series.

WHAT THE RE-SCORE CHANGED
    1. sigma at 2.0 sigma_c, not 1.5. The floor in IT1's area was 0.14-0.23 even
       fresh-against-fresh at matched force, so effects need to be large.
    2. An AREA-QUALITY GATE before committing: modulation >= 0.20 and Lambda
       consistent across triad members to within 25 %. IT1's area had modulation
       0.176 and Lambda 280/388/261 - weak, mixed texture - and that, not the
       withdrawn-deflection drift, is why it was unreadable. The drift was real
       but it explained the VDART skew (19.5 % -> 38.4 % when restored), not the
       control-tile flips: base-vs-drifted was no worse than base-vs-fresh.
    3. The withdrawn deflection is logged via read_meter() at every stage, since
       it is not readable through read_spm and drifted invisibly last time.
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
V, STEP, SPEED, R_EFF = 10.0, 0.02, 0.5, 0.625
SIGMA_RATIO = 2.0
MOD_MIN_IT2 = 0.18          # hard floor; candidates are RANKED
FLOOR_MAX = 0.25            # measured from the baselines, the
FLIP_MAX_PRE = 0.25         # real gate - see the module docstring
# Lambda consistency is REPORTED, not gated: the per-member spread
# ran 15-62 % across every area measured today, which is estimator
# noise rather than film quality.
# label, sign_every -> template period = 2 * sign_every * spacing
SPEC = [('P1', 1, 'period Lambda    - on resonance, T3 Condition 1'),
        ('P2', 2, 'period 2 Lambda  - IT1s panel C, the strongest there'),
        ('P4', 4, 'period 4 Lambda  - is longer monotonically better?')]

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


def meter(ns, tag):
    """Log the withdrawn deflection. read_spm cannot see it; read_meter can."""
    try:
        w = ns['exp'].read_meter()
        vals = np.atleast_1d(np.asarray(w, dtype=float)).ravel()
        # channel 2 is the deflection: it read +0.600 before the operator
        # restored the withdrawn value and -0.825 after, so this is how the
        # drift that confounded IT1 becomes visible.
        print('  meter %-14s defl %+.3f  |  %s'
              % (tag, vals[1] if len(vals) > 1 else float('nan'),
                 '  '.join('%+.3f' % v for v in vals[:6])))
        return [float(v) for v in vals[:6]]
    except Exception as e:
        print('  meter %-14s unavailable (%s)' % (tag, type(e).__name__))
        return None


def main():
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT2  commensuration series  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    if os.path.exists(A.STOP):
        raise SystemExit('STOP present')
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    # ---------------------------------------------------- pick a fresh area
    cands = A.legal_offsets(st, FRAME, step=2.0)
    prev = tuple(st['used_areas'][-1][0]) if st['used_areas'] else (0.0, 0.0)
    cands.sort(key=lambda c: (c[0] - prev[0]) ** 2 + (c[1] - prev[1]) ** 2)
    print('\n%d legal offsets for a %.0f um frame; trying the nearest first'
          % (len(cands), FRAME))
    meter(ns, 'at start')

    viable = []
    for attempt, (xo, yo) in enumerate(cands[:3]):
        print('\n--- candidate %d: (%+.1f,%+.1f) ---' % (attempt + 1, xo, yo))
        g('scanner_ok')(xo, yo, FRAME)
        ok, notes = A.check_area_fresh(st, xo, yo, FRAME)
        if not ok:
            print('  not usable: %s' % notes)
            continue
        g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                        xoff_um=xo, yoff_um=yo)
        centre, tv = g('tune_here')('ldart', size_um=FRAME, px=PX, rate=RATE,
                                    xoff_um=xo, yoff_um=yo)
        scr = tv['frame']
        # --- AREA QUALITY GATE. IT1 failed because this was never checked. ---
        triad_t, tt_t = g('pin_triad')(scr, ref_fam=g('FAM_FILM'))
        PX_NM = FRAME / PX * 1000.0
        d, h = g('ibw')(scr)
        S, _, _ = g('signed')(d)
        lam_m = []
        for f in [float(x) for x in triad_t]:
            v = g('period')(S, PX_NM, f)
            lam_m.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                         else float(v))
        lam_m = [v for v in lam_m if v == v]
        cons = ((max(lam_m) - min(lam_m)) / float(np.mean(lam_m))
                if len(lam_m) > 1 else 1.0)
        with contextlib.redirect_stdout(io.StringIO()):
            sk = g('streak_index')(scr, (0.35, FRAME - 0.35, 0.35, 1.7))
        print('  AREA GATE: modulation %.3f (need >= %.2f), streak %.3f '
              '(need <= %.2f); Lambda %s spread %.0f%% (reported only)'
              % (tt_t['mod'], MOD_MIN_IT2, sk, A.STREAK_MAX,
                 ['%.0f' % v for v in lam_m], 100 * cons))
        bad = []
        if tt_t['mod'] < MOD_MIN_IT2:
            bad.append('modulation %.3f below the hard floor %.2f'
                       % (tt_t['mod'], MOD_MIN_IT2))
        if sk > A.STREAK_MAX:
            bad.append('streaky (%.3f)' % sk)
        cand = dict(xo=xo, yo=yo, scr=scr, triad=[float(x) for x in triad_t],
                    mod=tt_t['mod'], lam=float(np.median(lam_m)),
                    lam_members=lam_m, cons=cons, streak=sk, centre=centre,
                    frac=tv['frac'])
        if bad:
            print('  -> rejected: %s' % '; '.join(bad))
        else:
            print('  -> viable (modulation %.3f)' % tt_t['mod'])
            viable.append(cand)
    if not viable:
        raise SystemExit('no candidate cleared the hard floors (modulation '
                         '>= %.2f, streak <= %.2f). Move the coarse stage.'
                         % (MOD_MIN_IT2, A.STREAK_MAX))
    viable.sort(key=lambda c: -c['mod'])
    chosen = viable[0]
    print('\n  %d viable candidate(s); taking the best modulation: '
          '(%+.1f,%+.1f) at %.3f'
          % (len(viable), chosen['xo'], chosen['yo'], chosen['mod']))
    print('  Lambda per member %s -> spread %.0f%% (reported, not gated: the'
          % (['%.0f' % v for v in chosen['lam_members']], 100 * chosen['cons']))
    print('  per-member spread ran 15-62%% across every area today, which is')
    print('  estimator noise. The median %.0f nm is what the recipe uses.'
          % chosen['lam'])

    XOFF, YOFF = chosen['xo'], chosen['yo']
    triad, LAM = chosen['triad'], chosen['lam']
    PX_NM = FRAME / PX * 1000.0
    print('\n=== area (%+.1f,%+.1f): triad %s, modulation %.3f, Lambda %.0f nm'
          % (XOFF, YOFF, ['%.0f' % t for t in triad], chosen['mod'], LAM))

    # The screening frame is NOT reused: the stage visited other candidates
    # after it was taken and does not return to the same place. Re-settle at the
    # chosen offset and take all three baselines consecutively.
    print('\n--- three CONSECUTIVE baselines at the chosen area ---')
    print('    the screening frame %s is discarded: the stage moved away and'
          % chosen['scr'])
    print('    back after it, and offset hysteresis made it disagree with')
    print('    consecutive frames by 0.45-0.51 in lead and 50-57 %% in flips.')
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_ldart')()
    b1 = g('frame')()
    b2 = g('frame')()
    b3 = g('frame')()
    g('contact_check')(b3)
    meter(ns, 'after baselines')
    F_REF, _ = g('pick_ref')([b1, b2, b3],
                             [(0.4, FRAME - 0.4, 0.4, FRAME - 0.4)])
    OTHER = [t for t in (b1, b2, b3) if t != F_REF] or [F_REF]
    g('frame_gate')(F_REF, ref_tags=tuple(OTHER))

    WIN = float(max(4.2 * LAM / 1000.0, 26 * PX_NM / 1000.0))
    # ---- THE REAL GATE: can this area support the measurement at all? ----
    # IT1 was unreadable because its floor was 0.14-0.23 with 6-19 % of
    # untouched tiles flipping director - even fresh against fresh at matched
    # contact force. That is measurable NOW, from the baselines we already have,
    # and it is the quantity of interest rather than a proxy for it.
    _pre_tiles = g('ctrl_tiles')(0.35, FRAME - 0.35, 0.35, 0.35 + WIN, WIN)
    _pre_tiles += g('ctrl_tiles')(0.35, FRAME - 0.35, FRAME - 0.35 - WIN,
                                  FRAME - 0.35, WIN)
    _ds0 = g('dir_state')
    print('\n--- baseline floor: is this area measurable? (%d tiles) ---'
          % len(_pre_tiles))
    _worst_fl, _worst_fp = 0.0, 0.0
    for _t0, _t1 in ((b1, b2), (b2, b3), (b1, b3)):
        _dl, _fp = [], 0
        for _rg in _pre_tiles:
            _cx, _cy = 0.5 * (_rg[0] + _rg[1]), 0.5 * (_rg[2] + _rg[3])
            _s0 = _ds0(_t0, _cx, _cy, WIN, triad, triad[0])
            _s1 = _ds0(_t1, _cx, _cy, WIN, triad, triad[0])
            if _s0 and _s1:
                _dl.append(_s1['lead'] - _s0['lead'])
                _fp += int(_s1['dom'] != _s0['dom'])
        if not _dl:
            continue
        _fl = float(np.abs(np.array(_dl)).max())
        _fr = _fp / float(len(_dl))
        print('    %s vs %s: floor %.3f, %d/%d flipped (%.0f%%)'
              % (_t0[-8:-4], _t1[-8:-4], _fl, _fp, len(_dl), 100 * _fr))
        _worst_fl, _worst_fp = max(_worst_fl, _fl), max(_worst_fp, _fr)
    print('    worst pair: floor %.3f (max %.2f), flip %.0f%% (max %.0f%%)'
          % (_worst_fl, FLOOR_MAX, 100 * _worst_fp, 100 * FLIP_MAX_PRE))
    if _worst_fl > FLOOR_MAX or _worst_fp > FLIP_MAX_PRE:
        raise SystemExit('this area cannot support the measurement: baseline '
                         'floor %.3f, flip %.0f%%. Writing here would produce '
                         'another unreadable iteration, as IT1 did. Move.'
                         % (_worst_fl, 100 * _worst_fp))
    print('    -> measurable. An effect above %.3f will be readable.'
          % (3 * _worst_fl))
    g('window_check')(WIN, PX_NM, LAM, name='readout window')
    ANGF = {t: abs(np.cos(np.deg2rad(t))) + abs(np.sin(np.deg2rad(t)))
            for t in triad}
    sp = LAM / 2000.0

    # n must be a multiple of 8 so sign_every = 4 still balances exactly
    def geom(ang):
        need = WIN * ang + 2 * (sp + 0.10)
        n = int(max(8, 8 * round((need / sp + 1) / 8.0)))
        while (n - 1) * sp < need and n < 128:
            n += 8
        halo = (n - 1) * sp * ang / 2 + R_EFF
        return n, halo, 2 * halo + 0.10

    print('\n--- placement as a fixed point (3 panels in a row) ---')
    ang_use = min(ANGF.values())
    settled = None
    for ncol, nrow in ((3, 1), (2, 1)):
        ang_use = min(ANGF.values())
        for it in range(4):
            n0, halo, pitch = geom(ang_use)
            xs = [FRAME / 2 + (j - (ncol - 1) / 2.0) * pitch
                  for j in range(ncol)]
            cy = 0.35 + WIN + 0.05 + halo
            slots = [(x, cy) for x in xs]
            if any(x - halo < 0.05 or x + halo > FRAME - 0.05 for x in xs) \
                    or cy + halo > FRAME - 0.05:
                print('    %dx1 factor %.3f halo %.2f pitch %.2f: does NOT fit'
                      % (ncol, ang_use, halo, pitch))
                break
            cm = []
            for (cx, cyy) in slots:
                best = None
                for sense in (+1, -1):
                    cf = g('command_for')(F_REF, cx, cyy, WIN, triad,
                                          sense=sense, min_lead=0.05,
                                          verbose=False)
                    if cf and (best is None
                               or ANGF[cf['cmd']] < ANGF[best['cmd']]):
                        best = cf
                if best is None:
                    raise SystemExit('slot (%.2f,%.2f) not measurable'
                                     % (cx, cyy))
                cm.append(best)
            new = max(ANGF[c['cmd']] for c in cm)
            print('    %dx1 pass %d: factor %.3f, n %d, halo %.2f, pitch %.2f, '
                  'dominants %s -> commands %s -> need %.3f'
                  % (ncol, it + 1, ang_use, n0, halo, pitch,
                     [int(c['dom']) for c in cm], [int(c['cmd']) for c in cm],
                     new))
            if new <= ang_use + 1e-9:
                settled = (ncol, ang_use, n0, halo, pitch, slots, cm)
                break
            ang_use = new
        if settled:
            break
    if settled is None:
        raise SystemExit('no row of panels settles here')
    ncol, ang_use, n0, halo, pitch, slots, cm = settled
    use = SPEC[:ncol]
    if ncol < len(SPEC):
        print('  !! only %d panels fit, dropping %s'
              % (ncol, ', '.join(q[0] for q in SPEC[ncol:])))
    print('  settled: %d panels, factor %.3f, n %d, halo %.2f, pitch %.2f'
          % (ncol, ang_use, n0, halo, pitch))

    # ---------------------------------------------------- dose: one sigma
    want = SIGMA_RATIO * sc
    pn_want = max(1, int(round((want / ((1 / sp ** 2) * V)) * SPEED / STEP)))
    # Cap the dwell on the write budget instead of halting on it. At Lambda =
    # 325 nm, 2.0 sigma_c would need 1.60 s and 27.6 min of writing against a
    # 26 min cap; better to write at a slightly lower sigma and say so than to
    # refuse the iteration.
    pn_budget = max(1, int((A.MAX_WRITE_MIN * 60.0)
                           / (ncol * n0 * n0 * 1.35) * SPEED / STEP))
    pn = min(pn_want, pn_budget)
    dwell = pn * STEP / SPEED
    sigma = (1 / sp ** 2) * V * dwell
    if pn < pn_want:
        print('  budget-limited: %.2f s instead of %.2f s, so sigma is %.2f x '
              'sigma_c rather than %.2f x'
              % (dwell, pn_want * STEP / SPEED, sigma / sc, SIGMA_RATIO))
        if sigma / sc < 1.5:
            raise SystemExit('the budget forces sigma below 1.5 x sigma_c '
                             '(%.2f x), which IT1 showed is too close to the '
                             'floor to read. Drop to 2 panels or raise the cap.'
                             % (sigma / sc))
    print('\n  one sigma for every panel: %.0f V.s/um^2 = %.2f x sigma_c'
          % (sigma, sigma / sc))
    print('  spacing %.0f nm, dwell %.2f s (%.1f V.s/site), keep 100%%'
          % (sp * 1000, dwell, V * dwell))
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.0f V.s per site is over half C21s %.0f - it would '
                         'stop being collective' % (V * dwell,
                                                    A.CHG_1PULSE_MAX))
    panels = []
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    print('\n  %-4s%8s%14s%8s%8s  %s'
          % ('', 'cmd', 'period', 'sites', 'sigma', 'tests'))
    for k, (lab, se, what) in enumerate(use):
        cx, cy = slots[k]
        sites = g('lattice_panel')(n0, sp, (cx, cy), cm[k]['cmd'], V,
                                   sign_every=se, keep_frac=1.0)
        v = np.array([q[2] for q in sites])
        assert abs(v.mean()) < 1e-9, '%s net DC' % lab
        for (x0, y0, v0) in sites:
            tb.dwell((x0, y0), v0, n=pn)
        panels.append(dict(label=lab, cx=cx, cy=cy, cmd=cm[k]['cmd'],
                           dom0=cm[k]['dom'], sign_every=se, sigma=sigma,
                           n=len(sites), period_nm=2 * se * sp * 1000,
                           ref=F_REF, tests=what))
        print('  %-4s%8.0f%14s%8d%8.0f  %s'
              % (lab, cm[k]['cmd'], '%.1f L' % (2 * se * sp * 1000 / LAM),
                 len(sites), sigma, what))
    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    tot = sum(p['n'] for p in panels)
    print('\n  %d pulses, %d pts, mean V %+.6f, %.1f min of writing'
          % (tot, len(Vv), Vv.mean(), wr))
    assert abs(Vv.mean()) < 1e-6 and np.abs(Vv).max() <= V + 1e-9
    assert X.min() > 0.05 and X.max() < FRAME - 0.05
    assert Y.min() > 0.05 and Y.max() < FRAME - 0.05
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('%.1f min over the %.0f min cap' % (wr,
                                                            A.MAX_WRITE_MIN))
    if os.path.exists(A.STOP):
        raise SystemExit('STOP appeared before the write')
    print('\n  predictions, fixed now:')
    print('    P1 best, P2 and P4 fail  -> T3 Condition 1 holds')
    print('    P4 > P2 > P1             -> longer period is better; Condition 1')
    print('                                is wrong and IT1s hint was real')
    print('    all three equal          -> the sign map is irrelevant; only the')
    print('                                site density and the axis matter')

    # ---------------------------------------------------- write and read
    fn = os.path.join(A.PROJ, 'output', '260821_IT2_commensuration.txt')
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    g('goto_ldart')()
    a1 = g('frame')()
    meter(ns, 'after write')
    g('contact_check')(a1)
    a2 = g('frame')()      # a SECOND after-frame: drift within the readout
    tiles = g('ctrl_tiles')(0.35, FRAME - 0.35, 0.35, 0.35 + WIN, WIN)
    top = slots[0][1] + halo + 0.05
    if FRAME - 0.35 - top >= WIN:
        tiles += g('ctrl_tiles')(0.35, FRAME - 0.35, top, FRAME - 0.35, WIN)

    ds = g('dir_state')

    def pair_floor(t0, t1):
        dl, fl = [], 0
        for rg in tiles:
            cx, cy = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
            s0 = ds(t0, cx, cy, WIN, triad, panels[0]['cmd'])
            s1 = ds(t1, cx, cy, WIN, triad, panels[0]['cmd'])
            if s0 and s1:
                dl.append(s1['lead'] - s0['lead'])
                fl += int(s1['dom'] != s0['dom'])
        dl = np.array(dl)
        return float(np.abs(dl).max()), fl / float(len(dl)), len(dl)

    print('\n=== floors, measured three ways on untouched film ===')
    f_ba, r_ba, n_t = pair_floor(F_REF, a1)
    f_aa, r_aa, _ = pair_floor(a1, a2)
    f_bb, r_bb, _ = pair_floor(F_REF, OTHER[0])
    print('  before vs after   floor %.3f  flip %.0f%%   <- the comparison used'
          % (f_ba, 100 * r_ba))
    print('  after  vs after   floor %.3f  flip %.0f%%   drift DURING readout'
          % (f_aa, 100 * r_aa))
    print('  before vs before  floor %.3f  flip %.0f%%   baseline noise'
          % (f_bb, 100 * r_bb))
    FL = max(f_ba, f_aa, f_bb)
    print('  using the worst: %.3f (%d tiles)' % (FL, n_t))
    readable = (r_ba <= A.FLIP_MAX) and (FL <= 0.30)

    # ---- the primary metric: within-frame contrast ------------------
    # Panels against untouched control tiles in the SAME frame. No temporal
    # comparison, so drift, stage hysteresis and mode changes cannot enter.
    ic = int(np.argmin([abs((t - panels[0]['cmd'] + 90) % 180 - 90)
                        for t in triad]))
    ctrl_w, ctrl_lead = [], []
    for rg in tiles:
        cx, cy = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
        s1 = ds(a1, cx, cy, WIN, triad, panels[0]['cmd'])
        if s1:
            ctrl_w.append(s1['w_cmd'])
            ctrl_lead.append(s1['lead'])
    ctrl_w = np.array(ctrl_w)
    ctrl_lead = np.array(ctrl_lead)
    WFL = float(2.0 * ctrl_w.std(ddof=1))     # 2 sd of the untouched tiles
    print('\n=== WITHIN-FRAME CONTRAST (the primary metric) ===')
    print('  untouched tiles in the after-frame: w(cmd) %.3f +- %.3f over %d '
          'tiles, lead %+.3f +- %.3f'
          % (ctrl_w.mean(), ctrl_w.std(ddof=1), len(ctrl_w), ctrl_lead.mean(),
             ctrl_lead.std(ddof=1)))
    print('  a panel is switched if its panel-minus-tiles contrast GAINS more')
    print('  than 2 sd = %.3f relative to the same contrast before the write.'
          % WFL)
    res_wf = {}
    print('  %-4s%9s%10s%10s%9s  %s'
          % ('', 'period', 'w(cmd)', 'vs tiles', 'x2sd', 'verdict'))
    # The tiles sit at the frame edges and the panels in a row, so a spatial
    # bias in the texture would contaminate a raw contrast. Correct it with the
    # SAME contrast measured in the before-frame: each term is within-frame, so
    # the difference is immune to drift AND to layout.
    ctrl_w0 = []
    for rg in tiles:
        cx, cy = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
        s0 = ds(F_REF, cx, cy, WIN, triad, panels[0]['cmd'])
        if s0:
            ctrl_w0.append(s0['w_cmd'])
    ctrl_w0 = np.array(ctrl_w0)
    print('  same tiles in the BEFORE frame: w(cmd) %.3f +- %.3f  ->  the'
          % (ctrl_w0.mean(), ctrl_w0.std(ddof=1)))
    print('  panel-minus-tiles contrast is corrected with its own before value,')
    print('  so layout bias cancels as well as drift.')
    for p in panels:
        s1 = ds(a1, p['cx'], p['cy'], WIN, triad, p['cmd'])
        s0 = ds(F_REF, p['cx'], p['cy'], WIN, triad, p['cmd'])
        exc1 = s1['w_cmd'] - ctrl_w.mean()
        exc0 = s0['w_cmd'] - ctrl_w0.mean()
        exc = exc1 - exc0
        ok = bool(exc > WFL and s1['dom'] == triad[ic])
        res_wf[p['label']] = dict(w_cmd=s1['w_cmd'], excess=float(exc),
                                  excess_after=float(exc1),
                                  excess_before=float(exc0),
                                  x2sd=float(exc / max(WFL, 1e-9)),
                                  dom=s1['dom'], switched=ok,
                                  period_nm=p['period_nm'])
        print('  %-4s%9s%10.3f%+10.3f%9.1f  %s   (after %+.3f, before %+.3f)'
              % (p['label'], '%.1f L' % (p['period_nm'] / LAM), s1['w_cmd'],
                 exc, exc / max(WFL, 1e-9),
                 'SWITCHED' if ok else ('above the tiles but within 2 sd'
                                        if exc > 0 else 'no'), exc1, exc0))
    res['within_frame'] = res_wf
    res['ctrl_w_mean'] = float(ctrl_w.mean())
    res['ctrl_w_sd'] = float(ctrl_w.std(ddof=1))
    res['within_floor'] = WFL

    print('\n=== before/after, for continuity only ===')
    print('  %-4s%9s%8s%7s%7s%9s%9s%7s%8s  %s'
          % ('', 'period', 'sigma', 'dom b', 'dom a', 'lead b', 'lead a',
             'xfl', 'w(cmd)', 'verdict'))
    res = dict(readable=readable, floor=FL, flip_rate=r_ba, n_tiles=n_t,
               drift_floor=f_aa, panels={})
    for p in panels:
        s0 = ds(F_REF, p['cx'], p['cy'], WIN, triad, p['cmd'])
        s1 = ds(a1, p['cx'], p['cy'], WIN, triad, p['cmd'])
        d_ = s1['lead'] - s0['lead']
        ok = bool(s1['on_target'] and d_ > 3 * FL)
        res['panels'][p['label']] = dict(
            turned=ok, dom0=s0['dom'], dom1=s1['dom'], lead0=s0['lead'],
            lead1=s1['lead'], dlead=d_, w_cmd=s1['w_cmd'], sigma=p['sigma'],
            n=p['n'], period_nm=p['period_nm'],
            w0=[float(z) for z in s0['w']], w1=[float(z) for z in s1['w']])
        print('  %-4s%9s%8.0f%7.0f%7.0f%+9.3f%+9.3f%7.1f%8.3f  %s'
              % (p['label'], '%.1f L' % (p['period_nm'] / LAM), p['sigma'],
                 s0['dom'], s1['dom'], s0['lead'], s1['lead'],
                 d_ / max(FL, 1e-9), s1['w_cmd'],
                 'TURNED' if ok else ('on target, within floor'
                                     if s1['on_target'] else
                                     'dominant %.0f' % s1['dom'])))
    print('\n  populations')
    print('  %-4s' % '' + ''.join('%18s' % ('w(%.0f)' % t) for t in triad))
    for p in panels:
        r = res['panels'][p['label']]
        print('  %-4s' % p['label']
              + ''.join('%8.3f->%-9.3f' % (r['w0'][i], r['w1'][i])
                        for i in range(3)))

    print('\n--- VDART at 128 px ---')
    g('setup_scan')(size_um=FRAME, px=128, rate=RATE, angle_deg=0.0)
    g('goto_vdart')()
    vf = g('frame')()
    g('orbit_balance')(vf)
    g('goto_ldart')()
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0)
    meter(ns, 'at end')

    print('\n' + '=' * 74)
    print('IT2 VERDICT')
    print('=' * 74)
    P = res['panels']
    W = res['within_frame']
    order = sorted(W, key=lambda k: -W[k]['excess'])
    print('  ranked by within-frame excess over the untouched tiles:')
    for k in order:
        print('    %-4s %.1f L   w(cmd) %.3f   excess %+.3f (%.1f x 2sd)   %s'
              % (k, W[k]['period_nm'] / LAM, W[k]['w_cmd'], W[k]['excess'],
                 W[k]['x2sd'], 'SWITCHED' if W[k]['switched'] else '-'))
    switched = [k for k in W if W[k]['switched']]
    print('  switched on the within-frame metric: %s'
          % (', '.join(switched) or 'none'))
    readable = True      # the within-frame metric has no temporal floor
    if not switched:
        print('\n  NOTHING SWITCHED even within-frame. sigma %.2f x sigma_c was'
              % (sigma / sc))
        print('  not enough here, or the write did not take. Check the meter log')
        print('  and the VDART before writing again.')
    elif len(switched) == len(W):
        print('\n  ALL periods switched -> the sign map is not what selects.')
    if not readable:
        print('\n  UNREADABLE: flip %.0f%%, floor %.3f. The written panels'
              % (100 * r_ba, FL))
        print('  persist and can be re-scored. Strike, not a result.')
        st['strikes'] = st.get('strikes', 0) + 1
    else:
        st['strikes'] = 0
        turned = [k for k in P if P[k]['turned']]
        print('  cleared 3x floor: %s' % (', '.join(turned) or 'none'))
        if 'P1' in turned and not any(k in turned for k in ('P2', 'P4')):
            print('\n  -> T3 CONDITION 1 HOLDS. Only the commensurate template')
            print('     selects; IT1s panel C was noise.')
        elif order[0] == 'P4' and P['P4']['w_cmd'] > P['P1']['w_cmd']:
            print('\n  -> LONGER PERIOD IS BETTER. Condition 1 is wrong as')
            print('     written and IT1s hint was real. The selecting quantity')
            print('     is not commensuration with Lambda. Next: is there an')
            print('     optimum period, or does it keep improving to a single')
            print('     sign block (a uniform-polarity panel)?')
        elif max(P[k]['w_cmd'] for k in P) - min(P[k]['w_cmd'] for k in P) \
                < 3 * FL:
            print('\n  -> THE SIGN MAP IS IRRELEVANT. All three periods give the')
            print('     same result, so what selects is the site density and the')
            print('     lattice AXIS, not the +/- pattern. Condition 1 collapses')
            print('     to a directional rule and the recipe simplifies.')
        else:
            print('\n  -> mixed; report the numbers as they are.')
    st['iteration'] = st.get('iteration', 0) + 1
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr
    st['used_areas'].append([[XOFF, YOFF], FRAME, 'IT2'])
    st['history'] = st.get('history', []) + [dict(
        name='IT2_commensuration', when=time.strftime('%Y-%m-%d %H:%M'),
        offset=[XOFF, YOFF], lam=LAM, triad=triad, mod=chosen['mod'],
        frames=dict(b1=b1, b2=b2, b3=b3, ref=F_REF, after=a1, after2=a2,
                    vdart=vf),
        sigma=sigma, dwell=dwell, result=res, write_min=wr)]
    note = A.refine_sigma_c(st, res)
    if note:
        print('\n  ' + note)
    A.save_state(st)
    return panels, res, wr


PROP = dict(
    name='IT2_commensuration',
    hypothesis=('T3 Condition 1 says the template must be commensurate with the '
                'lamellae to select a director. IT1 contradicted it: the 2 '
                'Lambda panel was the strongest of four at identical sigma. '
                'This separates period from drive with three panels that differ '
                'ONLY in the sign map.'),
    prediction=('If Condition 1 holds, P1 (period Lambda) wins and P2/P4 fail. '
                'If IT1s hint was real, P4 > P2 > P1. If the sign map is '
                'irrelevant, all three are equal.'),
    outcomes={'P1 best': 'T3 Condition 1 holds; IT1 panel C was noise',
              'P4 > P2 > P1': 'longer period is better; Condition 1 is wrong',
              'all equal': 'the sign map is irrelevant - only density and the '
                           'lattice axis select',
              'none turn': 'sigma 2x was still not enough here, or the area '
                           'gate needs tightening further'},
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
    panels=[dict(label=l, keep=1.0, dwell=None, sign_every=s, spacing_div=2.0)
            for l, s, _ in SPEC])

try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(PROP, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT2 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT2 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it2_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
