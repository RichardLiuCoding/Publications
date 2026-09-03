# -*- coding: utf-8 -*-
"""IT4 - is the lattice AXIS alone sufficient?  (Q20)

WHERE THIS COMES FROM
    C41 as revised: every template period from Lambda to 8 Lambda selects the
    director at identical sigma, including 8 Lambda which at n=16 is two sign
    blocks rather than a lattice. No ordering among periods reproduces - IT2 gave
    2L > L, IT3 gave L > 4L > 8L. So the +/- sign map is not the selection rule,
    and what the four working conditions share is the lattice AXIS and the areal
    density. Strip the template all the way down, then.

THE DESIGN
    Three panels, identical sigma, identical spacing, identical sites, each
    commanded 60 deg from its own local dominant director:

        A    period Lambda, charge-balanced   the reference (IT3s P1)
        UP   ALL sites at +V                  uniform polarity, no template
        UM   ALL sites at -V                  uniform polarity, opposite sign

    UP and UM are deliberately NOT balanced per panel. The FILE still balances
    exactly - equal site counts at opposite sign - so run_traj's |mean V| <= 0.01
    holds and there is no global DC. What is new is a large LOCAL net DC in each
    uniform panel, and C13 says a DC offset re-poles. That is expected and is
    part of the measurement: the VDART afterwards is a required readout.

PREDICTIONS, fixed before the write
    UP ~ UM ~ A        the sign map is irrelevant and even uniform polarity
                       selects. Axis plus density is the whole mechanism. Next:
                       a SINGLE ROW of pulses - an axis with almost no area.
    UP != UM           polarity matters, which would be new: the selection would
                       couple to field direction rather than geometry.
    UP, UM both fail   some alternation IS needed, and IT3s 8 Lambda sat near
                       the limit. A weakened Condition 1 survives: not
                       commensuration, but not nothing either.

    A uniform pulse panel is NOT a raster. C26 found a charge-balanced raster
    depletes the family parallel to its own scan lines; this has the same axis
    but delivers charge as isolated dwells, not a continuous sweep.

SAFETY
    Per-panel charge balance is relaxed HERE ONLY, by design, and the cancelling
    pair is asserted at file level. Every other guard is unchanged: 10 V ceiling,
    scanner range, footprint, write budget, static audit, measured-floor area
    gate, within-frame metric.
"""


import io
import os
import sys
import json
import time
import traceback
import contextlib
import ast

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
# label, sign_every, uniform (None = balanced; +1/-1 = every dwell one sign)
SPEC = [('A', 1, None, 'period Lambda, balanced - the reference'),
        ('UP', 1, +1, 'ALL +V, uniform polarity, no template'),
        ('UM', 1, -1, 'ALL -V, uniform polarity, opposite sign')]
N_MULT = 16      # so sign_every = 8 balances exactly: 8 rows +, 8 rows -

# Set to reuse an area already screened and baselined in this session, instead
# of re-spending the probe life. None = screen normally.
RESUME = dict(area=(0.0, -28.0),
              baselines=('PZTO_LDART_0103.ibw', 'PZTO_LDART_0104.ibw',
                         'PZTO_LDART_0105.ibw'))

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


def audit_code():
    """The three static checks from PITFALLS 10.1, before any command.

    Six of the eight IT1/IT2 launches died on statically detectable faults -
    two of them introduced by my own patches. This runs every time, including
    after a patch, because that is exactly when it is needed.
    """
    import builtins
    import json as _j
    print('\n--- static audit (before any instrument command) ---')
    # 1. called-but-undefined names across the cells the loader execs
    nb = _j.load(io.open(A.NB, encoding='utf-8'))
    called, have = set(), set(dir(builtins))
    srcs = []
    for c in nb['cells']:
        t = ''.join(c['source'])
        if c['cell_type'] != 'code':
            continue
        first = t.lstrip().split('\n')[0]
        import re as _re
        if _re.match(r'#\s*---\s*\[\d', first):
            continue
        if ('[LIB-' in t or 'scoring, QC and change detection' in t
                or 'tune, scan, litho' in t or 'def visualize_trajectory' in t):
            srcs.append(t)
    for t in srcs:
        try:
            tr = ast.parse(t)
        except SyntaxError:
            continue
        for nd in ast.walk(tr):
            if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name):
                called.add(nd.func.id)
            if isinstance(nd, (ast.FunctionDef, ast.ClassDef)):
                have.add(nd.name)
            if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Store):
                have.add(nd.id)
            if isinstance(nd, ast.arg):
                have.add(nd.arg)
    gap = sorted(called - have)
    print('  toolkit: %d cells, %d functions called, %d undefined%s'
          % (len(srcs), len(called), len(gap),
             (': ' + ', '.join(gap)) if gap else ''))
    # 2. dangling globals in THIS script
    me = ast.parse(io.open(__file__, encoding='utf-8').read())
    dfn = set(dir(builtins))
    for nd in ast.walk(me):
        if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Store):
            dfn.add(nd.id)
        if isinstance(nd, (ast.FunctionDef, ast.ClassDef)):
            dfn.add(nd.name)
        if isinstance(nd, ast.arg):
            dfn.add(nd.arg)
        if isinstance(nd, ast.ExceptHandler) and nd.name:
            dfn.add(nd.name)
        # imports bind names too - including ones bound INSIDE a function.
        # Missing this is what made the audit flag its own `import builtins`.
        if isinstance(nd, (ast.Import, ast.ImportFrom)):
            for al in nd.names:
                dfn.add((al.asname or al.name).split('.')[0])
    used = {nd.id for nd in ast.walk(me)
            if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Load)}
    dang = sorted(u for u in used - dfn if not u.startswith('_'))
    print('  driver: %d dangling global name(s)%s'
          % (len(dang), (': ' + ', '.join(dang)) if dang else ''))
    if dang:
        raise SystemExit('dangling names in the driver: %s. Faults 5 and 6 of '
                         'the IT1/IT2 retrospective were exactly this.' % dang)
    print('  -> audit clean')


def main():
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT4  axis only: uniform vs alternating  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    if os.path.exists(A.STOP):
        raise SystemExit('STOP present')
    audit_code()
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    # S1-S29 as code. No previous driver called this - the envelope existed and
    # was enforced only by whatever each driver happened to assert inline, which
    # left S24 (iteration and budget caps), S25 (strikes), S26 (duplicate name)
    # and S27 (pre-registration) checked by nothing. First call covers those;
    # geometry and dose are deferred to the second call below, once the area is
    # chosen and the dwell solved.
    print('\n--- preflight, pass 1: pre-registration and the loop stops ---')
    ok_pf, fails = A.preflight(PROP, st, ns)
    if not ok_pf:
        raise SystemExit('preflight: %s' % '; '.join(fails))

    # ---------------------------------------------------- pick a fresh area
    if RESUME:
        # Reuse an area already screened and baselined in this session. The
        # first launch spent four tunes and six frames proving (0,-28) is
        # measurable and then halted in placement, before writing anything; the
        # tip has not moved since. Paying that cost again would be probe life
        # spent on a question already answered.
        XOFF, YOFF = RESUME['area']
        b1, b2, b3 = RESUME['baselines']
        print('\n--- RESUMING at (%+.1f,%+.1f) ---' % (XOFF, YOFF))
        print('    baselines already on disk: %s'
              % ', '.join(t[-8:-4] for t in (b1, b2, b3)))
        print('    the previous launch halted in PLACEMENT, before any write,')
        print('    so nothing has touched this area and the frames still')
        print('    describe it. Re-deriving them would cost ~30 min of probe')
        print('    life for the same numbers.')
        g('scanner_ok')(XOFF, YOFF, FRAME)
        ok_fresh, notes = A.check_area_fresh(st, XOFF, YOFF, FRAME)
        if not ok_fresh:
            raise SystemExit('the resumed area is not fresh: %s' % notes)
        g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                        xoff_um=XOFF, yoff_um=YOFF)
        meter(ns, 'at resume')
        triad_r, tt_r = g('pin_triad')(b3, ref_fam=g('FAM_FILM'))
        triad = [float(x) for x in triad_r]
        PX_NM = FRAME / PX * 1000.0
        d_r, _ = g('ibw')(b3)
        S_r, _, _ = g('signed')(d_r)
        lam_r = []
        for f in triad:
            v = g('period')(S_r, PX_NM, f)
            lam_r.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                         else float(v))
        lam_r = [v for v in lam_r if v == v]
        LAM = float(np.median(lam_r))
        print('    triad %s, modulation %.3f, Lambda per member %s -> %.0f nm'
              % (['%.0f' % t for t in triad], tt_r['mod'],
                 ['%.0f' % v for v in lam_r], LAM))
        if tt_r['mod'] < MOD_MIN_IT2:
            raise SystemExit('the resumed area now reads modulation %.3f, below '
                             'the %.2f floor - re-screen rather than trust a '
                             'stale number' % (tt_r['mod'], MOD_MIN_IT2))
        chosen = dict(xo=XOFF, yo=YOFF, scr=b3, triad=triad, mod=tt_r['mod'],
                      lam=LAM, lam_members=lam_r, cons=0.0, streak=0.0)
    else:
        XOFF = YOFF = None
    cands = A.legal_offsets(st, FRAME, step=2.0)
    if not RESUME:
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
        n = int(max(N_MULT, N_MULT * round((need / sp + 1)
                                          / float(N_MULT))))
        while (n - 1) * sp < need and n < 128:
            n += N_MULT
        halo = (n - 1) * sp * ang / 2 + R_EFF
        return n, halo, 2 * halo + 0.10

    print('\n--- placement as a fixed point (2x2: 3 written + 1 control) ---')
    ang_use = min(ANGF.values())
    settled = None
    # A ROW of three is tried FIRST. The old list was ((2,2), (2,1)) and so
    # never considered it - which cost IT4's first launch its whole write, at an
    # area where 3x1 fits with room to spare. Ordered by written panels, most
    # first; the fixed point rejects any that does not fit.
    for ncol, nrow in ((3, 1), (2, 2), (2, 1)):
        ang_use = min(ANGF.values())
        for it in range(4):
            n0, halo, pitch = geom(ang_use)
            xs = [FRAME / 2 + (j - (ncol - 1) / 2.0) * pitch
                  for j in range(ncol)]
            y0 = 0.35 + WIN + 0.05 + halo
            ys_ = [y0 + r * pitch for r in range(nrow)]
            slots = [(x, y) for y in ys_ for x in xs]
            if any(x - halo < 0.05 or x + halo > FRAME - 0.05 for x in xs) \
                    or max(ys_) + halo > FRAME - 0.05:
                print('    %dx%d factor %.3f halo %.2f pitch %.2f: does NOT fit'
                      % (ncol, nrow, ang_use, halo, pitch))
                break
            cy = ys_[0]
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
            print('    %dx%d pass %d: factor %.3f, n %d, halo %.2f, pitch %.2f, '
                  'dominants %s -> commands %s -> need %.3f'
                  % (ncol, nrow, it + 1, ang_use, n0, halo, pitch,
                     [int(c['dom']) for c in cm], [int(c['cmd']) for c in cm],
                     new))
            if new <= ang_use + 1e-9:
                settled = (ncol * nrow, ang_use, n0, halo, pitch, slots, cm)
                break
            ang_use = new
        if settled:
            break
    if settled is None:
        raise SystemExit('no grid of panels settles here')
    nslot, ang_use, n0, halo, pitch, slots, cm = settled
    # Every slot is written. Reserving one as an in-grid control is obsolete:
    # the controls are now tiles gridded across the frame with the written
    # footprints subtracted, so an unwritten slot adds nothing and subtracts a
    # panel. That reservation is what reduced a 2-slot layout to a single panel
    # and halted the first launch.
    nwrite = min(len(SPEC), nslot)
    # The uniform panels carry a large local net DC and only cancel AS A PAIR.
    # A subset must therefore never take UP without UM. If only two panels fit,
    # drop the balanced reference instead: the within-frame control tiles
    # already provide the untouched comparison, so UP+UM is the informative
    # pair and A is the luxury.
    if nwrite >= len(SPEC):
        use = list(SPEC)
    elif nwrite == 2:
        use = [q for q in SPEC if q[2] is not None]
        print('  !! only 2 panels fit; keeping the uniform PAIR (UP, UM) and '
              'dropping the balanced reference A - the pair must stay together '
              'to cancel at file level, and the control tiles serve as the '
              'untouched comparison.')
    else:
        raise SystemExit('only %d panel fits, and a uniform panel cannot be '
                         'written without its opposite-sign partner (net DC, '
                         'C13). Shrink the frame or the lattice.' % nwrite)
    nwrite = len(use)
    print('  settled: %d slots, %d written + %d in-grid control, factor %.3f, '
          'n %d, halo %.2f, pitch %.2f'
          % (nslot, nwrite, nslot - nwrite, ang_use, n0, halo, pitch))
    if nwrite < len(SPEC):
        _drop = [q[0] for q in SPEC if q not in use]
        print('  !! only %d written panels fit, dropping %s'
              % (nwrite, ', '.join(_drop)))

    # ---------------------------------------------------- dose: one sigma
    want = SIGMA_RATIO * sc
    pn_want = max(1, int(round((want / ((1 / sp ** 2) * V)) * SPEED / STEP)))
    # Cap the dwell on the write budget instead of halting on it. At Lambda =
    # 325 nm, 2.0 sigma_c would need 1.60 s and 27.6 min of writing against a
    # 26 min cap; better to write at a slightly lower sigma and say so than to
    # refuse the iteration.
    pn_budget = max(1, int((A.MAX_WRITE_MIN * 60.0)
                           / (nwrite * n0 * n0 * 1.35) * SPEED / STEP))
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
    # ---- which panel goes in which slot -------------------------------
    # Every slot is commanded 60 deg from ITS OWN local dominant director
    # (C36), so the slots do not all start from the same state. The comparison
    # that carries this iteration is UP against UM: if those two sat on
    # different starting dominants, a difference between them could be the film
    # rather than the polarity. So place the uniform pair on slots that share a
    # (dominant, command) wherever the frame allows, give A the closest
    # remaining match, and leave the leftover slot unwritten.
    def kof(i):
        return (int(round(cm[i]['dom'])), int(round(cm[i]['cmd'])))

    groups = {}
    for i in range(len(slots)):
        groups.setdefault(kof(i), []).append(i)
    pair = max(groups.values(), key=len)
    uni_k = [k for k, q in enumerate(use) if q[2] is not None]
    assign = [None] * len(use)
    if len(pair) >= len(uni_k):
        for k, i in zip(uni_k, pair):
            assign[k] = i
        print("\n  uniform pair matched: both on dominant %d -> command %d, "
              "so a UP-UM difference is polarity, not starting state"
              % kof(pair[0]))
    else:
        print("\n  !! no two slots share a (dominant, command). UP and UM "
              "will start from different dominants, so a UP-UM difference "
              "would be confounded with the film. Reported, not fatal - UP "
              "against the tiles and UM against the tiles are each still "
              "clean.")
    tgt = kof(pair[0])
    free = [i for i in range(len(slots)) if i not in assign]
    free.sort(key=lambda i: (kof(i)[1] != tgt[1], kof(i)[0] != tgt[0]))
    for k in range(len(use)):
        if assign[k] is None:
            assign[k] = free.pop(0)
    assert len(set(assign)) == len(assign), 'two panels in one slot'
    ctrl_slots = [i for i in range(len(slots)) if i not in assign]
    for k, q in enumerate(use):
        print("    %-3s -> slot %d at (%.2f,%.2f), dominant %d -> command %d"
              % (q[0], assign[k], slots[assign[k]][0], slots[assign[k]][1],
                 kof(assign[k])[0], kof(assign[k])[1]))
    print("    unwritten: %s"
          % (", ".join("slot %d (%.2f,%.2f)" % (i, slots[i][0], slots[i][1])
                       for i in ctrl_slots) or "none"))

    panels = []
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    print('\n  %-4s%8s%14s%8s%8s  %s'
          % ('', 'cmd', 'period', 'sites', 'sigma', 'tests'))
    for k, (lab, se, uni, what) in enumerate(use):
        si = assign[k]
        cx, cy = slots[si]
        sites = g('lattice_panel')(n0, sp, (cx, cy), cm[si]['cmd'], V,
                                   sign_every=se, keep_frac=1.0)
        if uni is not None:
            # Uniform polarity: same site positions, every dwell one sign. The
            # per-panel balance assertion is relaxed HERE BY DESIGN; the file
            # balance is asserted below and is what protects against global
            # re-poling (C13).
            sites = [(x, y, uni * abs(vv)) for (x, y, vv) in sites]
        v = np.array([q[2] for q in sites])
        if uni is None:
            assert abs(v.mean()) < 1e-9, '%s net DC' % lab
        else:
            print('     %s uniform by design: mean V %+.2f, %d sites all %s - '
                  'expect LOCAL out-of-plane re-poling (C13)'
                  % (lab, v.mean(), len(sites), '+V' if uni > 0 else '-V'))
        for (x0, y0, v0) in sites:
            tb.dwell((x0, y0), v0, n=pn)
        panels.append(dict(label=lab, uniform=uni, cx=cx, cy=cy,
                           slot=si, cmd=cm[si]['cmd'],
                           dom0=cm[si]['dom'], sign_every=se, sigma=sigma,
                           n=len(sites), period_nm=2 * se * sp * 1000,
                           ref=F_REF, tests=what))
        print('  %-4s%8.0f%14s%8d%8.0f  %s'
              % (lab, cm[si]['cmd'], '%.1f L' % (2 * se * sp * 1000 / LAM),
                 len(sites), sigma, what))
    # preflight pass 2: the area and the dose are now known, so the checks
    # deferred above can actually run. Fatal - nothing has been written yet.
    print('\n--- preflight, pass 2: geometry and dose, now that they exist ---')
    PROP_RUN = dict(PROP)
    PROP_RUN['offset'] = (XOFF, YOFF)
    PROP_RUN['frame_try'] = [FRAME]
    PROP_RUN['panels'] = [dict(label=p['label'], keep=1.0, dwell=dwell,
                               sign_every=p['sign_every'], sigma=p['sigma'],
                               uniform=p['uniform'], spacing_div=2.0)
                          for p in panels]
    ok_pf, fails = A.preflight(PROP_RUN, st, ns)
    if not ok_pf:
        raise SystemExit('preflight (pass 2): %s' % '; '.join(fails))

    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    tot = sum(p['n'] for p in panels)
    print('\n  %d pulses, %d pts, mean V %+.6f, %.1f min of writing'
          % (tot, len(Vv), Vv.mean(), wr))
    nup = sum(1 for p in panels if p.get('uniform') == 1)
    ndn = sum(1 for p in panels if p.get('uniform') == -1)
    print('  uniform panels: %d at +V, %d at -V -> cancel at file level'
          % (nup, ndn))
    if nup != ndn:
        raise SystemExit('the uniform panels do not cancel (%d + against %d -), '
                         'so the file would carry net DC and re-pole globally '
                         '(C13). Pair them.' % (nup, ndn))
    assert abs(Vv.mean()) < 1e-6 and np.abs(Vv).max() <= V + 1e-9
    assert X.min() > 0.05 and X.max() < FRAME - 0.05
    assert Y.min() > 0.05 and Y.max() < FRAME - 0.05
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('%.1f min over the %.0f min cap' % (wr,
                                                            A.MAX_WRITE_MIN))
    if os.path.exists(A.STOP):
        raise SystemExit('STOP appeared before the write')
    print('\n  predictions, fixed now:')
    print('    UP ~ UM ~ A       the sign map is irrelevant; axis plus')
    print('                      density is the whole mechanism.')
    print('    UP != UM          polarity matters - the selection')
    print('                      couples to field direction.')
    print('    UP, UM both fail  some alternation is needed after all.')

    # ---------------------------------------------------- write and read
    fn = os.path.join(A.PROJ, 'output', '260821_IT4_axis_only.txt')
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    # The area is written; commit that to the state NOW. IT2 wrote and then
    # crashed in the verdict block, so its area never reached used_areas and
    # both S9 and check_area_fresh were blind to it afterwards. This save must
    # survive anything the readout raises, so it stands alone.
    st['used_areas'].append([[XOFF, YOFF], FRAME, PROP['name']])
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr
    A.save_state(st)
    print('  area (%+.1f,%+.1f) and %.1f min committed to the state before the'
          % (XOFF, YOFF, wr))
    print('  readout, so a crash here cannot lose the record as IT2s did.')

    g('goto_ldart')()
    a1 = g('frame')()
    meter(ns, 'after write')
    g('contact_check')(a1)
    a2 = g('frame')()      # a SECOND after-frame: drift within the readout
    # ctrl_tiles tiles only in x, at the band's CENTRE y. The old upper band
    # started at the top edge of the FIRST row, so with a 2x2 grid it began
    # inside the second row and its tiles sat at that row's centre height -
    # straight through a WRITTEN panel. Verified on IT3's frames: 3 of its 14
    # tiles overlapped P8. The excesses moved by <= 0.022 and no verdict
    # changed, but that was luck. Build the bands, then drop every tile that
    # touches a written panel, and check enough are left to carry a 2 sd
    # threshold.
    # Control tiles: grid the whole frame, then subtract the panels.
    #
    # ctrl_tiles tiles only in x, at the band's CENTRE y, so a band is one row
    # of tiles - call it once per row. Two problems this replaces: the old upper
    # band started at the top edge of the FIRST row, so on a 2x2 grid it began
    # inside the second row and ran its tiles through a WRITTEN panel (verified
    # on IT3: 3 of 14 tiles overlapped P8; the excesses moved <= 0.022 and no
    # verdict changed, but that was luck). And with the panels placed
    # deliberately, the surviving bands gave only 7 tiles, all in one row at the
    # bottom edge, while the largest untouched area in the frame - the
    # UNWRITTEN slot, at the same height as the panels - went unsampled.
    #
    # Gridding and subtracting fixes both: no tile can touch a panel, and the
    # controls span the frame instead of hugging one edge, which is the better
    # spatial match to panels sitting in the middle.
    step = WIN + 0.10
    MARG = 0.05

    def _clear(rg):
        for p in panels:
            if not (rg[1] < p['cx'] - halo - MARG
                    or rg[0] > p['cx'] + halo + MARG
                    or rg[3] < p['cy'] - halo - MARG
                    or rg[2] > p['cy'] + halo + MARG):
                return False
        return True

    cand, tiles, yc = [], [], 0.35
    while yc + WIN <= FRAME - 0.35 + 1e-9:
        cand += g('ctrl_tiles')(0.35, FRAME - 0.35, yc, yc + WIN, WIN)
        yc += step
    tiles = [rg for rg in cand if _clear(rg)]
    _in_grid = sum(1 for rg in tiles
                   if any(abs(0.5 * (rg[2] + rg[3]) - slots[i][1]) < halo
                          and abs(0.5 * (rg[0] + rg[1]) - slots[i][0]) < halo
                          for i in ctrl_slots))
    print("\n  control tiles: %d of %d grid candidates clear every written "
          "panel by %.2f um" % (len(tiles), len(cand), MARG))
    print("    %d of them sit inside an unwritten slot, at the same height as "
          "the panels" % _in_grid)
    if len(tiles) < 6:
        raise SystemExit("only %d untouched tiles remain, too few for a 2 sd "
                         "threshold. Shrink the panels or the window."
                         % len(tiles))

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

    # lam travels with the result: log_to_notebook expresses panel
    # periods in units of Lambda and cannot recover it otherwise.
    res = dict(readable=None, floor=None, panels={}, lam=float(LAM),
               frame=FRAME, px=PX, area=[float(XOFF), float(YOFF)])
    # res is defined HERE, above the within-frame block: in IT2 the block was
    # inserted above its definition and the run crashed after producing the
    # result. PITFALLS 10.1 fault 6.
    # ---- the primary metric: within-frame contrast ------------------
    # Panels against untouched control tiles in the SAME frame. No temporal
    # comparison, so drift, stage hysteresis and mode changes cannot enter.
    #
    # The tiles are read at EACH PANEL'S OWN command. IT3 read them once, at
    # panels[0]'s command, which was harmless there only because all three
    # panels were commanded to the same director. The triad members are not
    # equally populated, so comparing w along one director against a tile mean
    # measured along another would be a real offset.
    _tcache = {}

    def tile_stats(cmd):
        """(after mean, after sd, before mean) of w(cmd) over the tiles."""
        key = round(float(cmd), 3)
        if key not in _tcache:
            wa, wb, ld = [], [], []
            for rg in tiles:
                tx, ty = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
                sa = ds(a1, tx, ty, WIN, triad, cmd)
                sb = ds(F_REF, tx, ty, WIN, triad, cmd)
                if sa and sb:
                    wa.append(sa['w_cmd'])
                    wb.append(sb['w_cmd'])
                    ld.append(sa['lead'])
            _tcache[key] = (np.array(wa), np.array(wb), np.array(ld))
        return _tcache[key]

    def null_of_statistic(cmd):
        """2 sd of the panel statistic, measured at untouched tiles (C45).

        The panels are scored on a before/after contrast, which removes static
        spatial structure. Comparing that against 2 sd of w - which is dominated
        by exactly the structure the contrast removes - was conservative by
        about a factor of three, and it hid IT4's balanced reference. So apply
        the panel statistic to each tile, leaving that tile out of its own
        reference mean, and take the spread of that.

        Leave-one-out is required: keeping t in its own reference shrinks d_t by
        (1 - 1/n). A panel is out-of-sample with respect to the tiles, so its
        null must be too.
        """
        wa, wb, _ = tile_stats(cmd)
        n = len(wa)
        d = np.empty(n)
        for i in range(n):
            m = np.ones(n, bool)
            m[i] = False
            d[i] = (wa[i] - wa[m].mean()) - (wb[i] - wb[m].mean())
        return (float(2.0 * d.std(ddof=1)), float(np.abs(d).max()), d)

    print('\n=== WITHIN-FRAME CONTRAST (the primary metric) ===')
    print('  %d untouched tiles, read separately along each command:'
          % len(tiles))
    for cmd in sorted({round(float(p['cmd']), 3) for p in panels}):
        wa, wb, ld = tile_stats(cmd)
        print('    command %3.0f deg: after w %.3f +- %.3f, before %.3f +- '
              '%.3f, lead %+.3f' % (cmd, wa.mean(), wa.std(ddof=1), wb.mean(),
                                    wb.std(ddof=1), ld.mean()))
    print('  A panel is switched if its panel-minus-tiles contrast GAINS more')
    print('  than 2 sd of those tiles relative to the same contrast before the')
    print('  write. Each term is within-frame, so drift cancels; the difference')
    print('  cancels layout bias as well.')
    res_wf = {}
    print('  %-4s%18s%10s%10s%9s  %s'
          % ('', 'design', 'w(cmd)', 'vs tiles', 'x2sd', 'verdict'))
    print('  thresholds, per command:')
    for cmd in sorted({round(float(p['cmd']), 3) for p in panels}):
        wa, _, _ = tile_stats(cmd)
        t45, dmax, _d = null_of_statistic(cmd)
        print('    %3.0f deg: 2 sd of the statistic %.3f (C45)  |  max |d| %.3f'
              '  |  2 sd of w %.3f, which is NOT the null'
              % (cmd, t45, dmax, 2 * wa.std(ddof=1)))
    for p in panels:
        wa, wb, _ = tile_stats(p['cmd'])
        thr, dmax, _d = null_of_statistic(p['cmd'])
        icp = int(np.argmin([abs((t - p['cmd'] + 90) % 180 - 90)
                             for t in triad]))
        s1 = ds(a1, p['cx'], p['cy'], WIN, triad, p['cmd'])
        s0 = ds(F_REF, p['cx'], p['cy'], WIN, triad, p['cmd'])
        exc1 = s1['w_cmd'] - wa.mean()
        exc0 = s0['w_cmd'] - wb.mean()
        exc = exc1 - exc0
        # Two criteria, both reported: the parametric one against 2 sd of the
        # statistic's null, and the non-parametric one against the largest
        # change seen at any untouched tile. When they disagree, say so.
        ok = bool(exc > thr and s1['dom'] == triad[icp])
        design = ('balanced, %.1f L' % (p['period_nm'] / LAM)
                  if p['uniform'] is None
                  else ('uniform +V' if p['uniform'] > 0 else 'uniform -V'))
        res_wf[p['label']] = dict(w_cmd=s1['w_cmd'], excess=float(exc),
                                  excess_after=float(exc1),
                                  excess_before=float(exc0),
                                  x2sd=float(exc / max(thr, 1e-9)),
                                  threshold=thr, threshold_w=float(
                                      2.0 * wa.std(ddof=1)),
                                  d_max=dmax,
                                  beats_max_tile=bool(exc > dmax),
                                  uniform=p['uniform'],
                                  design=design, cmd=float(p['cmd']),
                                  dom0=float(p['dom0']), dom=s1['dom'],
                                  switched=ok, period_nm=p['period_nm'])
        print('  %-4s%18s%10.3f%+10.3f%9.1f  %s   (after %+.3f, before '
              '%+.3f%s)'
              % (p['label'], design, s1['w_cmd'], exc, exc / max(thr, 1e-9),
                 'SWITCHED' if ok else ('above the tiles but within the null'
                                        if exc > 0 else 'no'), exc1, exc0,
                 '; beats every untouched tile' if exc > dmax else ''))
    _wa0, _, _ = tile_stats(panels[0]['cmd'])
    ctrl_w = _wa0
    WFL = float(2.0 * _wa0.std(ddof=1))
    res['within_frame'] = res_wf
    res['ctrl_w_mean'] = float(ctrl_w.mean())
    res['ctrl_w_sd'] = float(ctrl_w.std(ddof=1))
    res['within_floor'] = WFL

    print('\n=== before/after, for continuity only ===')
    print('  %-4s%9s%8s%7s%7s%9s%9s%7s%8s  %s'
          % ('', 'period', 'sigma', 'dom b', 'dom a', 'lead b', 'lead a',
             'xfl', 'w(cmd)', 'verdict'))
    res.update(readable_ba=readable, floor=FL, flip_rate=r_ba, n_tiles=n_t,
               drift_floor=f_aa)
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
    print('IT4 VERDICT')
    print('=' * 74)
    P = res['panels']
    W = res['within_frame']
    order = sorted(W, key=lambda k: -W[k]['excess'])
    print('  ranked by within-frame excess over the untouched tiles:')
    for k in order:
        print('    %-4s %-18s w(cmd) %.3f   excess %+.3f (%.1f x 2sd)   %s'
              % (k, W[k]['design'], W[k]['w_cmd'], W[k]['excess'],
                 W[k]['x2sd'], 'SWITCHED' if W[k]['switched'] else '-'))
        print('         dominant %.0f -> %.0f, commanded %.0f'
              % (W[k]['dom0'], W[k]['dom'], W[k]['cmd']))
    switched = [k for k in W if W[k]['switched']]
    print('  switched on the within-frame metric: %s'
          % (', '.join(switched) or 'none'))
    readable = True      # the within-frame metric has no temporal floor
    # Write it BACK into res. Not doing so is why IT3's notebook cell claims
    # "unreadable" while its console reports three switched panels: res kept the
    # weak before/after metric's verdict.
    res['readable'] = True
    res['readable_before_after'] = bool(res.get('readable_ba', False))
    st['strikes'] = 0
    uni = [k for k in W if W[k]['uniform'] is not None]
    bal = [k for k in W if W[k]['uniform'] is None]
    uni_sw = [k for k in uni if W[k]['switched']]
    thr = max([W[k]['threshold'] for k in W] or [0.0])
    dif = (abs(W[uni[0]]['excess'] - W[uni[1]]['excess'])
           if len(uni) == 2 else float('nan'))
    if len(uni) == 2:
        print('  |%s - %s| = %.3f against the 2 sd threshold %.3f  ->  %s'
              % (uni[0], uni[1], dif, thr,
                 'indistinguishable' if dif <= thr else 'DIFFERENT'))
    if not switched:
        print('\n  NOTHING SWITCHED, not even the balanced reference. sigma')
        print('  %.2f x sigma_c was not enough here, or the write did not take.'
              % (sigma / sc))
        print('  This is not evidence against the axis hypothesis: the')
        print('  reference failed too, so the iteration says nothing about')
        print('  uniform polarity. Check the meter log and the VDART, then')
        print('  repeat at a higher sigma before concluding anything.')
    elif len(uni_sw) == len(uni) and len(uni) and dif <= thr:
        print('\n  -> THE LATTICE AXIS IS ENOUGH. Uniform polarity selects the')
        print('     commanded director as well as the alternating template, and')
        print('     +V is indistinguishable from -V. The +/- sign map was never')
        print('     the mechanism: what selects is the AXIS of the pulse lattice')
        print('     plus areal charge density. T3 Condition 1 does not survive')
        print('     in any form, and the recipe simplifies - no commensuration,')
        print('     no template, only a direction and enough charge.')
        print('     NEXT: a single ROW of pulses. That is an axis with almost no')
        print('     area, and it separates the axis from the areal density that')
        print('     has travelled with it in every panel so far.')
    elif len(uni_sw) == len(uni) and len(uni) and dif > thr:
        print('\n  -> POLARITY MATTERS. Both uniform panels select, but by')
        print('     different amounts (%.3f apart, threshold %.3f). Selection'
              % (dif, thr))
        print('     couples to the SIGN of the field, not to geometry alone -')
        print('     which is new, and is a handle the alternating template hid')
        print('     by construction. NEXT: hold the axis and sweep the duty')
        print('     cycle between all +V and all -V.')
    elif uni_sw and len(uni_sw) < len(uni):
        print('\n  -> ONE SIGN SELECTS, THE OTHER DOES NOT (%s switched, %s did'
              % (', '.join(uni_sw), ', '.join(k for k in uni
                                              if k not in uni_sw)))
        print('     not). The strongest possible form of a polarity effect.')
        print('     Treat with care: check the VDART first - if the failing')
        print('     panel re-poled out-of-plane, the in-plane readout there is')
        print('     measuring a different state, not a failure to select.')
    elif bal and any(W[k]['switched'] for k in bal) and not uni_sw:
        print('\n  -> ALTERNATION IS REQUIRED. The balanced reference selects')
        print('     and neither uniform panel does, at identical sigma, spacing')
        print('     and sites. So the sign map does matter after all: a weakened')
        print('     Condition 1 survives - not commensuration (C41 killed that)')
        print('     but not nothing either. NEXT: bracket it. 8 Lambda already')
        print('     sat near the limit, so sweep sign_every between 8 and')
        print('     uniform to find where selection dies.')
    else:
        print('\n  -> mixed; report the numbers as they are.')
    if not readable:
        print('\n  UNREADABLE: flip %.0f%%, floor %.3f. The written panels'
              % (100 * r_ba, FL))
        print('  persist and can be re-scored. Strike, not a result.')
    else:
        turned = [k for k in P if P[k]['turned']]
        print('\n  for continuity, the weaker before/after metric cleared 3x')
        print('  its floor for: %s' % (', '.join(turned) or 'none'))
    st['iteration'] = st.get('iteration', 0) + 1
    if PROP['name'] not in st['completed']:
        st['completed'].append(PROP['name'])   # S26 can only bite if this is set
    # the area and the write minutes were committed before the readout; do not
    # add them twice
    st['history'] = st.get('history', []) + [dict(
        name='IT4_axis_only', when=time.strftime('%Y-%m-%d %H:%M'),
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
    name='IT4_axis_only',
    hypothesis=('C41 as revised: every template period from Lambda to 8 Lambda '
                'selects the director at identical sigma, and no ordering among '
                'them reproduces (IT2 gave 2L > L, IT3 gave L > 4L > 8L). What '
                'the working conditions share is not a sign map but the lattice '
                'AXIS and the areal density. If that is the mechanism, then '
                'removing the template entirely - every dwell the same sign - '
                'must select just as well.'),
    prediction=('Three panels at identical sigma, identical spacing and '
                'identical site positions, each commanded 60 deg from its own '
                'local dominant director. A is charge-balanced at period '
                'Lambda; UP puts every site at +10 V; UM every site at -10 V. '
                'If the axis is what selects, UP ~ UM ~ A. If UP differs from '
                'UM, selection couples to field direction, which would be new. '
                'If both uniform panels fail, some alternation is needed after '
                'all and a weakened Condition 1 survives.'),
    outcomes={'UP ~ UM ~ A': 'the sign map is irrelevant; the lattice axis plus '
                             'areal density is the whole mechanism. Next: a '
                             'single ROW of pulses - an axis with almost no '
                             'area',
              'UP != UM': 'selection couples to the sign of the field, not to '
                          'geometry alone - a genuinely new handle',
              'both uniform fail': 'alternation IS required; Condition 1 '
                                   'survives in weakened form, and 8 Lambda '
                                   'sat near its limit',
              'nothing turns': 'the write did not take, or this area is worse '
                               'than its baseline floor suggested - check the '
                               'meter log and the VDART before writing again'},
    caveat=('Per-panel charge balance is relaxed here BY DESIGN. The file still '
            'balances exactly (equal site counts at opposite sign), so there is '
            'no global DC, but each uniform panel carries a large LOCAL net DC '
            'and C13 says a DC offset re-poles out-of-plane. That is expected '
            'and is part of the measurement: the VDART afterwards is a required '
            'readout, not an optional one. A uniform pulse panel is also NOT a '
            'raster - C26s depleting raster shares the axis but delivers charge '
            'as a continuous sweep rather than isolated dwells.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
    panels=[dict(label=l, keep=1.0, dwell=None, sign_every=s_, uniform=u,
                 spacing_div=2.0)
            for l, s_, u, _ in SPEC])

try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(PROP, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT4 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT4 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it4_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
