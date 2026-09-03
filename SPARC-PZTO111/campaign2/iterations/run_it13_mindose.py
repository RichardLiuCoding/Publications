# -*- coding: utf-8 -*-
"""IT5 - is sigma_c a threshold, or is selection a smooth function of sigma? (Q23)

WHERE THIS COMES FROM
    C45 corrected the threshold: panels are scored on a before/after contrast,
    so the null must be that contrast measured at untouched tiles, not the
    static spread of w. The correct threshold is about 3x tighter.

    sigma_c = 302 was DEFINED as where panels begin to clear a threshold - and
    that threshold was the wrong one. Re-scored against the right null (C46),
    IT1s panel D selected at sigma = 204 = 0.68 sigma_c, and it ended on the
    commanded director. Meanwhile C40s LAW, w = 0.234 ln(sigma) - 0.887, was
    fitted on w rather than on thresholds and is untouched by the correction. A
    smooth law needs no sigma_c at all.

    So the question is not "what is sigma_c" but "is there a threshold".

THE DESIGN
    Four panels, identical period Lambda, identical Lambda/2 spacing, identical
    100 % density, identical geometry. The ONLY difference is dwell, hence
    sigma:

        S04   0.4 sigma_c      well below - must fail if there is a threshold
        S07   0.7 sigma_c      where IT1s panel D sat
        S10   1.0 sigma_c      at it
        S15   1.5 sigma_c      above it

PREDICTIONS, fixed before the write
    threshold    S04 and S07 flat, S10 marginal, S15 clears. sigma_c survives
                 as a real physical threshold and C40 keeps its two regimes.
    smooth law   all four clear, with w(cmd) rising like ln(sigma) and the
                 excess following. sigma_c was an artefact of a threshold that
                 was 3x too high, and the drive condition becomes "more charge
                 gives more alignment", with no special value.
    mixed        a soft knee - the interesting outcome, and the one C40s r=0.974
                 fit over 19 panels would not have revealed either way.

    A null at S04 is only informative if S15 clears in the SAME frame. That is
    why the ladder spans the threshold rather than probing below it.

WHAT IS NEW IN THE MACHINERY
    - per-panel dwell (previous iterations used one sigma for all panels);
    - 3x2 layout tried first, so six slots are settled for four panels and the
      four can be SELECTED to share a starting dominant - IT4s confound;
    - a TOPOGRAPHY FLATNESS gate. The operator reports a large terrace edge in
      this sample, and it is real: a -2.2 nm step at x = 4.4 um in IT4s frame,
      42 nm peak-to-peak, with IT4s UM panel sitting on 37.9 nm of range against
      18.9 for the middle panel. A slot straddling a step writes into two
      surfaces, and a tile straddling one injects variance into the null that
      has nothing to do with switching. Both are now rejected.
    - the C45 threshold, and the non-parametric max|d| criterion beside it.
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
# label, sigma as a multiple of sigma_c, description. Everything else is
# held identical: period Lambda, spacing Lambda/2, 100 % density, same geometry.
# The whole ladder sits BELOW the saturation plateau C47 found over
# 0.7-1.5 sigma_c: everything above 0.7 converges to w(cmd) ~ 0.47 and cannot
# resolve a difference. The top rung is the positive control and is the last
# thing that may be dropped -- a null at the bottom is uninterpretable without
# a rung in the SAME frame that clearly should switch.
SPEC = [('L15', 0.15, 'far below anything tried - the real question'),
        ('L30', 0.30, 'below IT5s dropped 0.41 rung'),
        ('L45', 0.45, 'between the untested region and the known-good one'),
        ('L70', 0.70, 'C47 measured this selecting at 3.5x - POSITIVE CONTROL')]
FLAT_REL = 1.5          # reject a slot or tile whose height range exceeds
                        # this multiple of the median range in the same frame.
                        # Relative, because the absolute scale is unknown and
                        # varies with sample, scan size and noise.
N_MULT = 16      # so sign_every = 8 balances exactly: 8 rows +, 8 rows -

# Set to reuse an area already screened and baselined in this session, instead
# of re-spending the probe life. None = screen normally.
RESUME = None

buf = io.StringIO()


class Tee(object):
    def __init__(self, *s):
        self.s = s

    def write(self, x):
        for t in self.s:
            t.write(x)
            t.flush()          # per line: a 70 min run must be monitorable

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


def flatness(d, cx, cy, half, frame):
    """(height range, largest single-pixel step) in nm inside a square patch.

    A plane is removed first, so scanner tilt does not count as roughness. Rows
    arrive already line-flattened, which is why the largest step is taken over
    the 2-D patch rather than from a row-mean profile: a step running along x
    survives line flattening, one running along y does not.
    """
    z = np.asarray(d, float)
    while z.ndim > 2:
        z = z[0]                      # a channel stack; height is channel 0
    if z.ndim != 2:
        return float('nan'), float('nan')
    ny, nx = z.shape
    if np.nanmax(np.abs(z)) < 1e-3:
        z = z * 1e9                       # metres -> nm
    i0 = max(int((cy - half) / frame * ny), 0)
    i1 = min(int((cy + half) / frame * ny) + 1, ny)
    j0 = max(int((cx - half) / frame * nx), 0)
    j1 = min(int((cx + half) / frame * nx) + 1, nx)
    sub = z[i0:i1, j0:j1]
    if sub.size < 9:
        return float('nan'), float('nan')
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    Am = np.c_[xx.ravel(), yy.ravel(), np.ones(sub.size)]
    c, *_ = np.linalg.lstsq(Am, sub.ravel(), rcond=None)
    fl = sub - (c[0] * xx + c[1] * yy + c[2])
    st = 0.0
    if fl.shape[1] > 1:
        st = max(st, float(np.abs(np.diff(fl, axis=1)).max()))
    if fl.shape[0] > 1:
        st = max(st, float(np.abs(np.diff(fl, axis=0)).max()))
    return float(np.ptp(fl)), st


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
    print('IT13  the LOWER bound on dose: what is not enough?  %s' % time.strftime('%Y-%m-%d %H:%M'))
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
    # 3x2 first: six slots for four panels, so the four can be SELECTED to
    # share a starting dominant. IT4 could not do that - it settled exactly as
    # many slots as panels and the reference took whatever was left.
    for ncol, nrow in ((3, 2), (3, 1), (2, 2), (2, 1)):
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
            # Size on the BEST nwant slots. An awkward slot can be
            # discarded later, so it must not inflate the lattice now.
            nwant = min(len(SPEC), len(slots))
            angs = sorted(ANGF[c['cmd']] for c in cm)
            new = max(angs[:nwant])
            if angs[-1] > new + 1e-9:
                print('        (%d of %d slots want a larger factor, up to '
                      '%.3f; they will be dropped rather than sized for)'
                      % (sum(1 for a_ in angs if a_ > new + 1e-9), len(angs),
                         angs[-1]))
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
    # If fewer slots settled than there are rungs, keep the TOP of the
    # ladder. A null at the bottom is uninterpretable without a rung that
    # clearly should switch, so the positive control is the last thing to drop.
    if nwrite >= len(SPEC):
        use = list(SPEC)
    elif nwrite >= 2:
        use = list(SPEC[-nwrite:])
        print('  !! only %d slots settled; keeping the TOP %d rungs (%s) and '
              'dropping %s, because the positive control is what makes a null '
              'at the bottom readable'
              % (nwrite, nwrite, ', '.join(q[0] for q in use),
                 ', '.join(q[0] for q in SPEC[:-nwrite])))
    else:
        raise SystemExit('only %d slot fits - a ladder needs at least two '
                         'rungs, one of which must be above sigma_c.' % nwrite)
    nwrite = len(use)
    print('  settled: %d slots for %d rungs, factor %.3f, n %d, halo %.2f, '
          'pitch %.2f' % (nslot, nwrite, ang_use, n0, halo, pitch))
    if nwrite < len(SPEC):
        _drop = [q[0] for q in SPEC if q not in use]
        print('  !! only %d written panels fit, dropping %s'
              % (nwrite, ', '.join(_drop)))

    # ------------------------------------------------ dose: one per panel
    # This is the first iteration where sigma VARIES between panels, so the
    # dwell is solved per panel rather than once. Everything else is held equal.
    unit = (1 / sp ** 2) * V              # sigma per second of dwell
    dose = []
    for (lab, ratio, what) in SPEC:
        pn_k = max(1, int(round((ratio * sc / unit) * SPEED / STEP)))
        dose.append(pn_k)
    tot_s = sum(pn_k * n0 * n0 for pn_k in dose) * STEP / SPEED * 1.35
    print('\n  sigma ladder, spacing %.0f nm (%.0f V.s/um^2 per second):'
          % (sp * 1000, unit))
    scale = 1.0
    if tot_s > A.MAX_WRITE_MIN * 60.0:
        scale = A.MAX_WRITE_MIN * 60.0 / tot_s
        print('  !! %.1f min over the %.0f min cap; scaling every dwell by '
              '%.2f so the LADDER is preserved even if the absolute sigmas move'
              % (tot_s / 60.0, A.MAX_WRITE_MIN, scale))
        dose = [max(1, int(round(pn_k * scale))) for pn_k in dose]
    sig_of = {}
    for k, (lab, ratio, what) in enumerate(SPEC):
        dw = dose[k] * STEP / SPEED
        sg = unit * dw
        sig_of[lab] = (sg, dw, dose[k])
        print('    %-4s target %.2f sigma_c -> dwell %.2f s -> sigma %.0f '
              '= %.2f sigma_c  (%.1f V.s/site)'
              % (lab, ratio, dw, sg, sg / sc, V * dw))
        if V * dw > 0.5 * A.CHG_1PULSE_MAX:
            raise SystemExit('%s delivers %.0f V.s per site, over half C21s '
                             '%.0f - it would stop being collective'
                             % (lab, V * dw, A.CHG_1PULSE_MAX))
    hi = max(sig_of[l][0] for l, _r, _w in SPEC) / sc
    lo = min(sig_of[l][0] for l, _r, _w in SPEC) / sc
    print('  the ladder spans %.2f to %.2f sigma_c, a factor of %.1f'
          % (lo, hi, hi / max(lo, 1e-9)))
    if hi < 0.6:
        raise SystemExit('the top of the ladder is only %.2f sigma_c - without '
                         'a panel that clearly should switch, a null at the '
                         'bottom means nothing. C47 measured 0.70 selecting at '
                         '3.5x, so the positive control has to reach ~0.7; '
                         'raise the cap or drop a rung.' % hi)
    # `sigma` and `dwell` keep their old meaning for the budget prints: the
    # top rung, which is the one that has to work.
    sigma = sig_of[SPEC[-1][0]][0]
    dwell = sig_of[SPEC[-1][0]][1]
    pn = sig_of[SPEC[-1][0]][2]

    # ---- which panel goes in which slot -------------------------------
    # Every slot is commanded 60 deg from ITS OWN local dominant director
    # (C36), so the slots do not all start from the same state. The comparison
    # that carries this iteration is UP against UM: if those two sat on
    # different starting dominants, a difference between them could be the film
    # rather than the polarity. So place the uniform pair on slots that share a
    # (dominant, command) wherever the frame allows, give A the closest
    # remaining match, and leave the leftover slot unwritten.
    # ---- topography: which slots are on flat film? --------------------
    _dref, _ = g('ibw')(F_REF)
    print('\n--- topography flatness of each slot (terrace edges) ---')
    _rng = [flatness(_dref, sx, sy, halo, FRAME)[0] for (sx, sy) in slots]
    _fin = [v for v in _rng if v == v]
    _med = float(np.median(_fin)) if _fin else float('nan')
    _cut = FLAT_REL * _med
    print('    median range over %d slots %.1f nm -> rejecting above %.1f nm'
          % (len(_fin), _med, _cut))
    flat_ok = []
    for i, (sx, sy) in enumerate(slots):
        good = (_rng[i] == _rng[i]) and _rng[i] <= _cut
        print('    slot %d (%.2f,%.2f): height range %5.1f nm  %s'
              % (i, sx, sy, _rng[i],
                 'flat' if good else 'REJECTED - terrace or debris'))
        if good:
            flat_ok.append(i)
    # prefer the flattest when there is a choice
    flat_ok.sort(key=lambda i: _rng[i])
    if len(flat_ok) < len(use):
        print('    !! only %d of %d slots are flat but %d rungs need placing.'
              % (len(flat_ok), len(slots), len(use)))
        if len(flat_ok) >= 2:
            print('    Dropping the lowest rungs and keeping the top of the')
            print('    ladder, because a null at the bottom is meaningless')
            print('    without a rung that clearly should switch.')
            use = use[-len(flat_ok):]
            nwrite = len(use)
        else:
            raise SystemExit('only %d flat slot(s) here - the terrace crosses '
                             'this area. Move.' % len(flat_ok))

    def kof(i):
        return (int(round(cm[i]['dom'])), int(round(cm[i]['cmd'])))

    groups = {}
    for i in flat_ok:
        groups.setdefault(kof(i), []).append(i)
    pair = max(groups.values(), key=len)
    # Every panel is a rung of one ladder, so ALL of them want the same
    # starting dominant - the comparison is between magnitudes. Take the largest
    # group of slots that share a (dominant, command) and fill it first.
    # Fill from the TOP rung down. The matched group is finite, and if one
    # rung has to take an unmatched slot it must be the least load-bearing one -
    # the bottom of the ladder, not the positive control. In the simulation the
    # default order gave the unmatched slot to S15, which is exactly backwards:
    # a positive control on a different starting dominant is IT4s confound
    # planted in the one panel that has to work.
    uni_k = list(range(len(use)))[::-1]
    assign = [None] * len(use)
    if len(pair) >= len(uni_k):
        for k, i in zip(uni_k, pair):
            assign[k] = i
        print("\n  all %d rungs matched: dominant %d -> command %d for every "
              "one, so a difference between rungs is sigma and nothing else"
              % ((len(use),) + kof(pair[0])))
    else:
        print("\n  !! only %d slot(s) share a (dominant, command) but %d rungs "
              "need placing, so some rungs start from different states and a "
              "difference between them is confounded with the film. Reported, "
              "not fatal: each rung against the tiles is still clean, and the "
              "question is whether the LOW rungs move at all."
              % (len(pair), len(use)))
    tgt = kof(pair[0])
    free = [i for i in flat_ok if i not in assign]
    free.sort(key=lambda i: (kof(i)[1] != tgt[1], kof(i)[0] != tgt[0]))
    # Fill the leftovers from the TOP rung down as well. When the matched
    # group is smaller than the ladder the branch above is skipped entirely and
    # every rung comes through here - so filling in SPEC order would hand the
    # unmatched slot to the last rung, the positive control, which is the one
    # panel that must not carry a confound. Reversed, the unmatched slot goes to
    # the bottom rung instead.
    for k in reversed(range(len(use))):
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
    for k, (lab, ratio, what) in enumerate(use):
        se, uni = 1, None            # every rung is a balanced period-Lambda
        sigma_k, dwell_k, pn_k = sig_of[lab]
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
            tb.dwell((x0, y0), v0, n=pn_k)
        panels.append(dict(label=lab, uniform=uni, cx=cx, cy=cy,
                           slot=si, cmd=cm[si]['cmd'],
                           dom0=cm[si]['dom'], sign_every=se,
                           sigma=sigma_k, dwell=dwell_k, ratio=ratio,
                           n=len(sites), period_nm=2 * se * sp * 1000,
                           ref=F_REF, tests=what))
        print('  %-4s%8.0f%14s%8d%8.0f  %s'
              % (lab, cm[si]['cmd'], '%.1f L' % (2 * se * sp * 1000 / LAM),
                 len(sites), sigma_k, what))
    # preflight pass 2: the area and the dose are now known, so the checks
    # deferred above can actually run. Fatal - nothing has been written yet.
    print('\n--- preflight, pass 2: geometry and dose, now that they exist ---')
    PROP_RUN = dict(PROP)
    PROP_RUN['offset'] = (XOFF, YOFF)
    PROP_RUN['frame_try'] = [FRAME]
    PROP_RUN['panels'] = [dict(label=p['label'], keep=1.0,
                               dwell=p['dwell'], sign_every=p['sign_every'],
                               sigma=p['sigma'], spacing_div=2.0)
                          for p in panels]
    ok_pf, fails = A.preflight(PROP_RUN, st, ns)
    if not ok_pf:
        raise SystemExit('preflight (pass 2): %s' % '; '.join(fails))

    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    tot = sum(p['n'] for p in panels)
    print('\n  %d pulses, %d pts, mean V %+.6f, %.1f min of writing'
          % (tot, len(Vv), Vv.mean(), wr))
    nup = ndn = 0        # every rung is charge-balanced in itself
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

    # ---- PRE-WRITE control-tile gate ---------------------------------
    # The tiles are built from the AFTER frame, so without this a geometry that
    # leaves none is found only once the write is spent and the C45 null has no
    # sample (the IT11 simulation hit 0 of 49 and 0 of 64). Lambda drives it:
    # 23-32 tiles survive at Lambda <= 301 nm, 7 at 354 nm, 0 at 390 nm, and
    # this film spans 231-410 nm (C2).
    _step_pre = WIN + 0.10
    _cand_pre, _yc = [], 0.35
    while _yc + WIN <= FRAME - 0.35 + 1e-9:
        _cand_pre += g('ctrl_tiles')(0.35, FRAME - 0.35, _yc, _yc + WIN, WIN)
        _yc += _step_pre

    def _clear_pre(rg):
        for _p in panels:
            if not (rg[1] < _p['cx'] - halo - 0.05
                    or rg[0] > _p['cx'] + halo + 0.05
                    or rg[3] < _p['cy'] - halo - 0.05
                    or rg[2] > _p['cy'] + halo + 0.05):
                return False
        return True
    _n_pre = sum(1 for rg in _cand_pre if _clear_pre(rg))
    print('\n--- pre-write control-tile gate ---')
    print('    Lambda %.0f nm, window %.2f um, halo %.2f um, %d panels'
          % (LAM, WIN, halo, len(panels)))
    print('    %d of %d grid tiles would clear every planned panel'
          % (_n_pre, len(_cand_pre)))
    if 6 <= _n_pre < 8:
        print('    !! below the 8 the analysis prefers, so the null will be '
              'reported as inflated rather than tight (HANDOFF_2 4).')
    if _n_pre < 6:
        raise SystemExit(
            'only %d untouched tiles would survive, and the C45 threshold is '
            'measured ON those tiles - below 6 the null cannot carry a panel, '
            'so the write would buy an uninterpretable frame. Lambda here is '
            '%.0f nm, which is what drives it. Re-screen for a smaller-Lambda '
            'area, or write fewer rungs.' % (_n_pre, LAM))
    print('    -> enough untouched film remains to measure the null against')
    print('\n  predictions, fixed now:')
    print('    UP ~ UM ~ A       the sign map is irrelevant; axis plus')
    print('                      density is the whole mechanism.')
    print('    UP != UM          polarity matters - the selection')
    print('                      couples to field direction.')
    print('    UP, UM both fail  some alternation is needed after all.')

    # ---------------------------------------------------- write and read
    fn = os.path.join(A.PROJ, 'output', time.strftime('%y%m%d') + '_IT13_mindose.txt')
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
    # Drop tiles that straddle a terrace step. The tiles ARE the threshold
    # (C45), so topography inside them desensitises the whole test.
    _dt, _ = g('ibw')(a1)
    _tr = []
    for rg in tiles:
        tx, ty = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
        _tr.append(flatness(_dt, tx, ty, 0.5 * WIN, FRAME)[0])
    _fin = [v for v in _tr if v == v]
    _tcut = FLAT_REL * float(np.median(_fin)) if _fin else float('inf')
    _keep = [rg for rg, v in zip(tiles, _tr) if v == v and v <= _tcut]
    _drop = [rg for rg, v in zip(tiles, _tr) if not (v == v and v <= _tcut)]
    print('\n  terrace filter on the control tiles: %d kept, %d dropped '
          '(height range above %.1f nm = %.1f x the median)'
          % (len(_keep), len(_drop), _tcut, FLAT_REL))
    if len(_keep) >= 8:
        tiles = _keep
    else:
        print('  !! only %d flat tiles - keeping all %d and reporting the '
              'null as inflated by topography rather than shrinking the sample'
              % (len(_keep), len(tiles)))
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
        design = '%.2f sigma_c' % (p['sigma'] / sc)
        res_wf[p['label']] = dict(w_cmd=s1['w_cmd'], excess=float(exc),
                                  excess_after=float(exc1),
                                  excess_before=float(exc0),
                                  x2sd=float(exc / max(thr, 1e-9)),
                                  threshold=thr, threshold_w=float(
                                      2.0 * wa.std(ddof=1)),
                                  d_max=dmax,
                                  beats_max_tile=bool(exc > dmax),
                                  uniform=p['uniform'],
                                  # The verdict sorts and prints on
                                  # W[k]['sigma'] and res_wf never placed it:
                                  # "IT5 failed: KeyError: 'sigma'"
                                  # (autoloop.log, 22 Aug 01:08). Still live in
                                  # run_it5.py. Found again 27 Aug by the
                                  # dict-key parity check, which the AST audit
                                  # cannot see because a dict key is a string
                                  # inside a subscript.
                                  sigma=float(p['sigma']),
                                  ratio=float(p['ratio']),
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
    print('IT13 VERDICT')
    print('=' * 74)
    P = res['panels']
    W = res['within_frame']
    rung = sorted(W, key=lambda k: W[k]['sigma'])
    print('  the ladder, in order of sigma:')
    for k in rung:
        print('    %-4s %6.2f sigma_c   excess %+.3f (%.1f x threshold)   %s%s'
              % (k, W[k]['sigma'] / sc, W[k]['excess'], W[k]['x2sd'],
                 'SWITCHED' if W[k]['switched'] else '-',
                 '   beats every untouched tile'
                 if W[k].get('beats_max_tile') else ''))
        print('         dominant %.0f -> %.0f, commanded %.0f, w(cmd) %.3f'
              % (W[k]['dom0'], W[k]['dom'], W[k]['cmd'], W[k]['w_cmd']))
    sw = [k for k in rung if W[k]['switched']]
    print('  switched: %s' % (', '.join(sw) or 'none'))
    readable = True
    res['readable'] = True
    st['strikes'] = 0
    top = rung[-1]
    low = [k for k in rung if W[k]['sigma'] / sc < 0.85]

    # the law, for comparison. It was fitted on w and is untouched by C45.
    print('\n  against C40s law w = 0.234 ln(sigma) - 0.887:')
    for k in rung:
        pred = 0.234 * np.log(W[k]['sigma']) - 0.887
        print('    %-4s w(cmd) %.3f, law %.3f, residual %+.3f'
              % (k, W[k]['w_cmd'], pred, W[k]['w_cmd'] - pred))

    if not W[top]['switched']:
        print('\n  -> VOID, not negative. The top rung at %.2f sigma_c did not'
              % (W[top]['sigma'] / sc))
        print('     clear either, so there is no working positive control in')
        print('     this frame and the low rungs cannot be read against')
        print('     anything. Do not record a threshold result from this.')
        print('     Check the terrace filter, the meter log and the VDART, then')
        print('     repeat at higher sigma or in flatter film.')
    elif len(sw) == len(rung):
        print('\n  -> NO THRESHOLD. Every rung selected, including %s at'
              % rung[0])
        print('     %.2f sigma_c. sigma_c = 302 was an artefact of a threshold'
              % (W[rung[0]]['sigma'] / sc))
        print('     three times too high (C45): panels that "failed" before')
        print('     were being compared against the static spread of w rather')
        print('     than against the null of their own statistic. The drive')
        print('     condition is not a threshold but a smooth law, and C40s')
        print('     two regimes collapse into one. NEXT: how far down does it')
        print('     go? A ladder at 0.1-0.4 sigma_c, and the practical question')
        print('     becomes the minimum charge for a usable pattern, not a')
        print('     forbidden region.')
    elif all(not W[k]['switched'] for k in low) and W[top]['switched']:
        print('\n  -> A THRESHOLD SURVIVES. The rungs below 0.85 sigma_c (%s)'
              % ', '.join(low))
        print('     stayed flat while %s cleared at %.1f x, in the same frame,'
              % (top, W[top]['x2sd']))
        print('     at identical period, spacing, density and geometry. So')
        print('     sigma_c is physical and IT1s panel D was the artefact - it')
        print('     is the one row in C46 from a run whose frames straddle a')
        print('     deflection change. C40 keeps its two regimes.')
    else:
        edge = [k for k in rung if W[k]['switched']][0]
        print('\n  -> A SOFT KNEE, between %s and %s. Selection is neither'
              % (rung[max(rung.index(edge) - 1, 0)], edge))
        print('     forbidden below a sharp sigma_c nor indifferent to sigma:')
        print('     the crossing sits near %.2f sigma_c on this ladder.'
              % (W[edge]['sigma'] / sc))
        print('     Report the crossing, not a threshold. A 19-panel fit could')
        print('     not have distinguished this from either extreme.')
    if not readable:
        print('\n  UNREADABLE: flip %.0f%%, floor %.3f.' % (100 * r_ba, FL))
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
        name=PROP['name'], when=time.strftime('%Y-%m-%d %H:%M'),
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
    name='IT13_min_dose',
    hypothesis=('sigma_c = 302 V.s/um^2 was DEFINED as the sigma where panels '
                'begin to clear a threshold - and C45 showed that threshold '
                'was about three times too high, because the panels are scored '
                'on a before/after contrast while the threshold was the static '
                'spread of w. Re-scored against the correct null, IT1s panel D '
                'selected at 0.68 sigma_c and ended on the commanded director '
                '(C46). C40s LAW, w = 0.234 ln(sigma) - 0.887, was fitted on w '
                'rather than on thresholds and is untouched by the correction - '
                'and a smooth law needs no threshold at all. So the question is '
                'not what sigma_c is, but whether there is one.'),
    prediction=('Four panels differing ONLY in dwell, at 0.4, 0.7, 1.0 and 1.5 '
                'sigma_c, with identical period Lambda, identical Lambda/2 '
                'spacing, identical 100 % density and identical geometry, each '
                'commanded 60 deg from its own local dominant director. If '
                'sigma_c is a real threshold, the bottom two rungs stay flat '
                'and the top one clears. If selection is smooth in sigma, all '
                'four clear with the excess rising like ln(sigma).'),
    outcomes={'S04 and S07 flat, S15 clears':
              'sigma_c is a real threshold and C40s two regimes survive',
              'all four clear, rising with ln(sigma)':
              'there is no threshold. sigma_c was an artefact of a threshold '
              '3x too high, and the drive condition becomes simply "more '
              'charge, more alignment"',
              'a soft knee':
              'the most likely and the most informative - a crossover rather '
              'than a threshold, which a 19-panel fit could not have revealed',
              'nothing clears, including S15':
              'the iteration is void, not negative: without the positive '
              'control there is no scale to read the low rungs against'},
    caveat=('A null at the bottom of the ladder is only interpretable if the '
            'top rung clears in the SAME frame, which is why the ladder spans '
            'the threshold rather than probing below it. New in the machinery: '
            'per-panel dwell; a 3x2 layout so six slots are settled for four '
            'panels and the four can be selected to share a starting dominant '
            '(IT4s confound); and a topography flatness gate, because this '
            'sample carries a terrace edge - a -2.2 nm step at x = 4.4 um in '
            'IT4s frame, 42 nm peak-to-peak - and a tile straddling a step '
            'inflates the very null that sets the threshold.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=True,
    panels=[dict(label=l, keep=1.0, dwell=None, sign_every=1, ratio=r,
                 spacing_div=2.0)
            for (l, r, _w) in SPEC])

try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(PROP, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT13 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT13 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it13_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
