# -*- coding: utf-8 -*-
"""IT7 - lattice axis, or sign boundary? (Q19)

Every panel in this campaign has alternated sign perpendicular to the command,
so the sign-boundary lines have always run PARALLEL to the commanded axis. "The
director follows the lattice axis" and "the director follows the sign
boundaries" have therefore never been distinguishable - they predict the same
result for every experiment run so far.

C46 makes the boundary hypothesis the more attractive of the two, because the
re-scored magnitudes are monotonic in boundary count: 16 boundaries 7.3x, 4
boundaries 5.7x, 1 boundary 2.5x, 0 boundaries (uniform) nothing. Not a
periodicity effect - a boundary effect.

THE DESIGN
    Four panels. Identical sites, identical sigma, identical lattice grid,
    identical command. The only difference is which index the sign alternates
    along:

        PAR   sign alternates perpendicular to the command
              -> boundaries PARALLEL to the command      (the standard recipe)
        PERP  sign alternates along the command
              -> boundaries PERPENDICULAR to the command

    Two replicates of each. IT4 rested on one panel per condition and its
    reference arm turned out to be confounded; this does not.

PREDICTIONS, fixed before the write
    both rotate            the lattice AXIS selects; boundary orientation is
                           irrelevant.
    PAR yes, PERP no       the SIGN BOUNDARY selects. Same lattice, same dose,
                           same axis, boundaries turned 90 deg - and it stops
                           working. This answers Q19.
    PERP goes elsewhere    the same answer, stronger: the director follows the
                           boundary lines, so boundaries across the command
                           should push it to a different triad member.
    neither                void. The positive control failed; read nothing in.
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
MOD_MIN_IT2 = 0.18          # hard floor; candidates are RANKED
FLOOR_MAX = 0.25            # measured from the baselines, the
FLIP_MAX_PRE = 0.25         # real gate - see the module docstring
# Lambda consistency is REPORTED, not gated: the per-member spread
# ran 15-62 % across every area measured today, which is estimator
# noise rather than film quality.
# label, sigma as a multiple of sigma_c, description. Everything else is
# held identical: period Lambda, spacing Lambda/2, 100 % density, same geometry.
# label, sign-boundary orientation relative to the command, description.
# Everything else is held identical: period Lambda, spacing Lambda/2, 100 %
# density, one sigma, same command, same sites.
# label, arm, description. sigma, command, panel footprint and starting
# member are held identical; only the LATTICE GEOMETRY differs.
#   ISO  Lambda/2 along, Lambda/2 across - the standard recipe
#   DEN  Lambda/4 ALONG the same-polarity lines, Lambda/2 across, so the sign
#        period stays at the super-domain period Lambda. This is the arm that
#        separates within-line DENSITY from the SIGN PERIOD for the first time:
#        every Lambda/4 panel in the campaign so far also halved its sign
#        period, so C48 (spacing sets purity) and C41 (period does not matter)
#        are confounded with each other in all existing data.
#   Q4   Lambda/4 both ways - halves the sign period too. The known-good
#        high-purity reference (C39/C48), which is what makes DEN readable.
SPEC = [('ISO', 'iso', 'the standard recipe, Lambda/2 both ways'),
        ('DEN', 'den', 'DENSER along the lines, sign period UNCHANGED'),
        ('Q4', 'q4', 'Lambda/4 both ways - sign period halved as well')]
SIGMA_RATIO = 0.94       # one sigma for every panel. Lowered from 1.3
                         # after C47 (IT5) found the response saturates
                         # at w(cmd) ~ 0.47 over 0.7-1.5 sigma_c: a
                         # saturating observable compresses the very
                         # differences these two iterations measure.
                         # 0.9 keeps a margin above IT5s working 0.70
                         # while staying off the plateau, and cuts the
                         # write by 31 % since time = Area*sigma/V.
FLAT_REL = 1.5          # reject a slot or tile whose height range exceeds
                        # this multiple of the median range in the same frame.
                        # Relative, because the absolute scale is unknown and
                        # varies with sample, scan size and noise.
N_MULT = 16      # n even is all IT7 needs; kept at 16 for comparability with
                 # every previous panel

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


def lattice_panel_aniso(n_a, n_b, sp_a, sp_b, centre, cmd_deg, v,
                        sign_every=1):
    """Rectangular lattice: sp_a ALONG the command, sp_b ACROSS it.

    Sign alternates every sign_every rows of the ACROSS index, exactly as
    lattice_panel does, so the sign-boundary lines stay PARALLEL to the command
    and the sign period is 2 * sign_every * sp_b. Shrinking sp_a therefore
    densifies the same-polarity lines WITHOUT touching the sign period, which is
    the separation this iteration exists to make.

    Serpentine along each row: a sign-ordered site list makes the tip cross the
    panel between every pulse and cost 2.85x the time (PITFALLS 7.10).

    Candidate for promotion into the notebook [TOOLKIT] cell once it has run
    once - kept local until then so a shared implementation is not changed
    mid-session (HANDOFF_1 1).
    """
    assert (n_b // sign_every) % 2 == 0, 'odd sign-band count -> net DC'
    cells = [(ai, bi, +1.0 if (bi // sign_every) % 2 == 0 else -1.0)
             for bi in range(n_b) for ai in range(n_a)]
    cells.sort(key=lambda c: (c[1], c[0] if c[1] % 2 == 0 else -c[0]))
    t = np.deg2rad(cmd_deg)
    u = np.array([np.cos(t), np.sin(t)])
    nn = np.array([-np.sin(t), np.cos(t)])
    c0 = np.array(centre, float)
    ia = np.arange(n_a) - (n_a - 1) / 2.0
    ib = np.arange(n_b) - (n_b - 1) / 2.0
    out = []
    for (ai, bi, sg) in cells:
        p = c0 + ia[ai] * sp_a * u + ib[bi] * sp_b * nn
        out.append((p[0], p[1], sg * v))
    assert abs(np.mean([o[2] for o in out])) < 1e-12, 'net DC'
    return out


def arm_geometry(arm, n0, sp):
    """(n_a, n_b, sp_a, sp_b) for one arm, at a MATCHED panel footprint."""
    side = (n0 - 1) * sp
    sp_a, sp_b = {'iso': (sp, sp),
                  'den': (sp / 2.0, sp),
                  'q4': (sp / 2.0, sp / 2.0)}[arm]
    n_a = int(round(side / sp_a)) + 1
    n_b = int(round(side / sp_b)) + 1
    if n_b % 2:
        n_b += 1                     # even rows -> exact charge balance
    return n_a, n_b, sp_a, sp_b


def boundary_panel(n, sp, centre, cmd_deg, v, mode, sign_every=1):
    """A charge-balanced lattice whose sign-boundary lines run either parallel
    to the command or perpendicular to it.

    The grid is identical in both cases - u along the command, nn across it, n
    by n at spacing sp. Only the index the sign alternates along changes:

        mode 'par'   sign = f(bi), bi across the command
                     -> boundary LINES run along u, PARALLEL to the command.
                        This is what lattice_panel does, i.e. every panel in
                        this campaign so far.
        mode 'perp'  sign = f(ai), ai along the command
                     -> boundary LINES run along nn, PERPENDICULAR to it.

    Both are exactly balanced when n is even. Sites come back in serpentine
    order so the tip does not cross the panel between consecutive pulses.
    """
    cells = []
    for bi in range(n):
        for ai in range(n):
            idx = bi if mode == 'par' else ai
            cells.append((ai, bi, +1.0 if (idx // sign_every) % 2 == 0
                          else -1.0))
    pos = [c for c in cells if c[2] > 0]
    neg = [c for c in cells if c[2] < 0]
    k = min(len(pos), len(neg))
    kept = pos[:k] + neg[:k]
    kept.sort(key=lambda c: (c[1], c[0] if c[1] % 2 == 0 else -c[0]))
    t = np.deg2rad(cmd_deg)
    u = np.array([np.cos(t), np.sin(t)])
    nn = np.array([-np.sin(t), np.cos(t)])
    c0 = np.array(centre, float)
    off = np.arange(n) - (n - 1) / 2.0
    out = []
    for (ai, bi, sg) in kept:
        p = c0 + off[ai] * sp * u + off[bi] * sp * nn
        out.append((float(p[0]), float(p[1]), float(sg * v)))
    return out


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
    print('IT12  leftovers: denser along the lines, or a shorter sign period?  %s' % time.strftime('%Y-%m-%d %H:%M'))
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

    # ------------------------------------------------- dose: one for all
    # IT7 varies the sign-boundary ORIENTATION, not the dose, so every panel
    # gets the same sigma. Any difference between PAR and PERP is geometry.
    # sigma = V * dwell / (sp_a * sp_b), so matching sigma across arms means
    # dwell proportional to (sp_a * sp_b). Choose the ISO pulse count on a
    # multiple of 4 so that halving and quartering it stay INTEGER: quantisation
    # is worst at the shortest dwell, and an unmatched sigma would confound the
    # only comparison this iteration makes.
    unit = (1 / sp ** 2) * V
    _pn_raw = (SIGMA_RATIO * sc / unit) * SPEED / STEP
    # NEAREST multiple of 4, not the next one down: rounding down can cost 30 %
    # of sigma (at Lambda 245 nm it would drop 0.94 -> 0.71 sigma_c).
    pn = max(4, int(round(_pn_raw / 4.0)) * 4)
    dwell = pn * STEP / SPEED
    sigma = unit * dwell
    n_pan = min(len(SPEC), 4)
    est = n_pan * n0 * n0 * dwell * 1.4 / 60.0
    if est > A.MAX_WRITE_MIN:
        pn = max(1, int(pn * A.MAX_WRITE_MIN / est))
        dwell = pn * STEP / SPEED
        sigma = unit * dwell
        print('  budget-limited: dwell trimmed to %.2f s -> sigma %.2f sigma_c'
              % (dwell, sigma / sc))
    print('\n  one sigma for all panels: %.0f V.s/um^2 = %.2f sigma_c'
          % (sigma, sigma / sc))
    print('  spacing %.0f nm, dwell %.2f s (%.1f V.s per site), keep 100 %%'
          % (sp * 1000, dwell, V * dwell))
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.1f V.s per site is over half C21s %.0f'
                         % (V * dwell, A.CHG_1PULSE_MAX))
    # The floor is tied to evidence, not to the target: IT5 (C47) showed
    # 0.70 sigma_c selects at 3.5x the null, so anything at or above ~0.65 is a
    # credible positive control. The old floor of 0.9 was written when the
    # target was 1.3, to catch the BUDGET forcing sigma down; with the target
    # now 0.9 it rejected its own rounding (0.88).
    if sigma / sc < 0.65:
        raise SystemExit('the budget forces sigma to %.2f sigma_c, below the '
                         'lowest value ever shown to work (0.70 sigma_c, C47), '
                         'so there would be no credible positive control'
                         % (sigma / sc))
    # per-arm pulse count, from the spacing product, so sigma is identical
    sig_of = {}
    print('\n  dose, matched in AREAL CHARGE across the three geometries:')
    print('    %-5s%10s%10s%8s%8s%9s%10s%10s'
          % ('arm', 'sp_along', 'sp_across', 'n_a', 'n_b', 'sites', 'pulses',
             'sigma'))
    for (_lab, _arm, _w) in SPEC:
        _na, _nb, _sa, _sb = arm_geometry(_arm, n0, sp)
        _pn = int(round(pn * (_sa * _sb) / (sp * sp)))
        if _pn < 1:
            raise SystemExit('arm %s needs %d pulses per site, i.e. under one '
                             'trajectory step - raise SIGMA_RATIO or use a '
                             'coarser arm' % (_lab, _pn))
        _dw = _pn * STEP / SPEED
        _sg = V * _dw / (_sa * _sb)
        sig_of[_lab] = (_sg, _dw, _pn)
        print('    %-5s%10.4f%10.4f%8d%8d%9d%10d%10.0f'
              % (_lab, _sa, _sb, _na, _nb, _na * _nb, _pn, _sg))
        if V * _dw > 0.5 * A.CHG_1PULSE_MAX:
            raise SystemExit('%s delivers %.1f V.s per site, over half C21s '
                             '%.0f' % (_lab, V * _dw, A.CHG_1PULSE_MAX))
    _sgs = [sig_of[q[0]][0] for q in SPEC]
    _spread = (max(_sgs) - min(_sgs)) / float(np.mean(_sgs))
    print('    sigma spread across arms: %.3f %%  (%s)'
          % (100 * _spread, 'matched' if _spread < 0.02 else 'NOT MATCHED'))
    if _spread > 0.02:
        raise SystemExit('the arms differ in sigma by %.1f %%, so a difference '
                         'between them would be dose rather than geometry. '
                         'Lambda %.0f nm does not quantise cleanly at pn = %d; '
                         'adjust SIGMA_RATIO.' % (100 * _spread, LAM, pn))

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
    # Most load-bearing arm FIRST. DEN against ISO is the question; Q4 is the
    # anchor whose value is already on record (C39/C48), so Q4 is the arm that
    # can afford an unmatched starting member. run_it7 filled from the last arm
    # backwards, which handed the matched pair to Q4 and DEN and left ISO --
    # half of the primary contrast -- on a different dominant (seen in the
    # offline simulation: ISO on 122 deg, DEN and Q4 on 62).
    _prio = {q[0]: i for i, q in enumerate(use)}
    PRIORITY = sorted(range(len(use)),
                      key=lambda k: {'ISO': 0, 'DEN': 1, 'Q4': 2}.get(
                          use[k][0], 9))
    uni_k = list(PRIORITY)
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
    for k in PRIORITY:
        if assign[k] is None:
            assign[k] = free.pop(0)
    assert len(set(assign)) == len(assign), 'two panels in one slot'
    ctrl_slots = [i for i in range(len(slots)) if i not in assign]
    _starts = {use[k][0]: kof(assign[k])[0] for k in range(len(use))}
    _iso_den_matched = _starts.get('ISO') == _starts.get('DEN')
    print('\n  starting member per arm: %s'
          % ', '.join('%s from %d deg' % (a, d)
                      for a, d in sorted(_starts.items())))
    if _iso_den_matched:
        print('  -> ISO and DEN share a starting member, so the PRIMARY')
        print('     contrast (within-line density at fixed sign period) is')
        print('     matched and a difference between them is geometry.')
    else:
        print('  !! ISO and DEN start from DIFFERENT members (%d vs %d), so the'
              % (_starts.get('ISO', -1), _starts.get('DEN', -1)))
        print('     primary contrast is CONFOUNDED with the starting state -')
        print('     IT4s confound, Q13. Each arm against the tiles is still')
        print('     clean, but DEN-minus-ISO is not attributable to geometry.')
        print('     This is reported, not fatal, and the verdict says so.')
    for k, q in enumerate(use):
        print("    %-3s -> slot %d at (%.2f,%.2f), dominant %d -> command %d"
              % (q[0], assign[k], slots[assign[k]][0], slots[assign[k]][1],
                 kof(assign[k])[0], kof(assign[k])[1]))
    print("    unwritten: %s"
          % (", ".join("slot %d (%.2f,%.2f)" % (i, slots[i][0], slots[i][1])
                       for i in ctrl_slots) or "none"))

    # ---- adapt the arm count to what the frame can actually audit ------
    # The control tiles are what the C45 null is measured on, and Lambda drives
    # how many survive: at Lambda 354/388/430 nm a 4-panel frame leaves 7/0/5
    # and a 2-panel frame 25/12/10. Rather than build three arms and halt at the
    # pre-write gate, project the count now and drop Q4 if three would starve
    # the null. ISO against DEN is the contrast the question turns on; Q4 is the
    # anchor already on record (C39/C48), so Q4 is what may be given up.
    def _proj_tiles(n_panels):
        _c, _yc = [], 0.35
        while _yc + WIN <= FRAME - 0.35 + 1e-9:
            _c += g('ctrl_tiles')(0.35, FRAME - 0.35, _yc, _yc + WIN, WIN)
            _yc += WIN + 0.10
        _cent = [slots[assign[k]] for k in range(min(n_panels, len(assign)))]
        _ok = 0
        for rg in _c:
            if all(rg[1] < cx - halo - 0.05 or rg[0] > cx + halo + 0.05
                   or rg[3] < cy - halo - 0.05 or rg[2] > cy + halo + 0.05
                   for (cx, cy) in _cent):
                _ok += 1
        return _ok, len(_c)

    _t3, _tot3 = _proj_tiles(len(use))
    print('\n--- can this frame audit %d panels? ---' % len(use))
    print('    Lambda %.0f nm -> window %.2f um, halo %.2f um' % (LAM, WIN, halo))
    print('    %d panels would leave %d of %d grid tiles untouched'
          % (len(use), _t3, _tot3))
    if _t3 < 8 and len(use) > 2:
        _t2, _tot2 = _proj_tiles(2)
        print('    %d panels would leave %d of %d' % (2, _t2, _tot2))
        if _t2 >= 8:
            _dropped = [q[0] for q in use[2:]]
            use = use[:2]
            print('    -> DROPPING %s. Three arms would leave the C45 null with'
                  % ', '.join(_dropped))
            print('       %d tiles, which cannot carry a 2 sd threshold, so the'
                  % _t3)
            print('       iteration would be void after the write. ISO against')
            print('       DEN is the contrast the question turns on and it')
            print('       survives; what is given up is knowing whether halving')
            print('       the SIGN PERIOD as well would have added more, which')
            print('       C39/C48 already put at w(cmd) 0.83-0.86 for Lambda/4.')
            print('       Recorded as a TWO-ARM iteration, not a three-arm one.')
        else:
            print('    -> even two panels leave only %d tiles; the pre-write '
                  'gate will halt this.' % _t2)
    else:
        print('    -> enough untouched film for all %d arms' % len(use))


    panels = []
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    print('\n  %-4s%8s%14s%8s%8s  %s'
          % ('', 'cmd', 'period', 'sites', 'sigma', 'tests'))
    for k, (lab, mode, what) in enumerate(use):
        se, uni = 1, None
        sigma_k, dwell_k, pn_k = sig_of[lab]
        si = assign[k]
        cx, cy = slots[si]
        _na, _nb, _sa, _sb = arm_geometry(mode, n0, sp)
        sites = lattice_panel_aniso(_na, _nb, _sa, _sb, (cx, cy),
                                    cm[si]['cmd'], V)
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
                           sigma=sigma_k, dwell=dwell_k, mode=mode,
                           sp_along=_sa, sp_across=_sb, n_a=_na, n_b=_nb,
                           n=len(sites), period_nm=2 * se * _sb * 1000,
                           ref=F_REF, tests=what))
        print('  %-4s%8.0f%14s%8d%8.0f  %s'
              % (lab, cm[si]['cmd'],
                 '%.2f L' % (2 * se * _sb * 1000 / LAM),
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
    # The tiles below are built from the AFTER frame, so without this check a
    # geometry that leaves none is discovered only after the write is spent and
    # the C45 null has no sample (the IT11 simulation hit 0 of 49 and 0 of 64).
    # Reproduce the same grid and the same clearance test on the PLANNED panel
    # positions now. Lambda drives this: 23-32 tiles survive at Lambda <= 301 nm,
    # 7 at 354 nm and 0 at 390 nm, and this film spans 231-410 nm (C2).
    _step = WIN + 0.10
    _MARG_PRE = 0.05
    _cand_pre, _yc = [], 0.35
    while _yc + WIN <= FRAME - 0.35 + 1e-9:
        _cand_pre += g('ctrl_tiles')(0.35, FRAME - 0.35, _yc, _yc + WIN, WIN)
        _yc += _step

    def _clear_pre(rg):
        for _p in panels:
            if not (rg[1] < _p['cx'] - halo - _MARG_PRE
                    or rg[0] > _p['cx'] + halo + _MARG_PRE
                    or rg[3] < _p['cy'] - halo - _MARG_PRE
                    or rg[2] > _p['cy'] + halo + _MARG_PRE):
                return False
        return True
    _n_pre = sum(1 for rg in _cand_pre if _clear_pre(rg))
    print('\n--- pre-write control-tile gate ---')
    print('    Lambda %.0f nm, window %.2f um, halo %.2f um, %d panels'
          % (LAM, WIN, halo, len(panels)))
    print('    %d of %d grid tiles would clear every planned panel'
          % (_n_pre, len(_cand_pre)))
    if 6 <= _n_pre < 8:
        print('    !! %d tiles is below the 8 the analysis prefers, so the '
              'null will be reported as inflated rather than treated as '
              'tight (HANDOFF_2 4). Proceeding.' % _n_pre)
    if _n_pre < 6:
        raise SystemExit(
            'only %d untouched tiles would survive this geometry, and the C45 '
            'threshold is measured ON those tiles - below 6 the null is either '
            'absent or too noisy to read a panel against, so the write would '
            'be spent on an uninterpretable frame. Lambda here is %.0f nm, '
            'which is what drives it (23-32 tiles at 301 nm, 7 at 354, 0 at '
            '390). Re-screen for a smaller-Lambda area, or write fewer panels.'
            % (_n_pre, LAM))
    print('    -> enough untouched film remains to measure the null against')
    print('\n  predictions, fixed now:')
    print('    UP ~ UM ~ A       the sign map is irrelevant; axis plus')
    print('                      density is the whole mechanism.')
    print('    UP != UM          polarity matters - the selection')
    print('                      couples to field direction.')
    print('    UP, UM both fail  some alternation is needed after all.')

    # ---------------------------------------------------- write and read
    fn = os.path.join(A.PROJ, 'output', time.strftime('%y%m%d') + '_IT12_leftovers.txt')
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
        design = {'iso': 'L/2 x L/2', 'den': 'L/4 along, L/2 across',
                  'q4': 'L/4 x L/4'}.get(p['mode'], p['mode'])
        res_wf[p['label']] = dict(w_cmd=s1['w_cmd'], excess=float(exc),
                                  excess_after=float(exc1),
                                  excess_before=float(exc0),
                                  x2sd=float(exc / max(thr, 1e-9)),
                                  threshold=thr, threshold_w=float(
                                      2.0 * wa.std(ddof=1)),
                                  d_max=dmax,
                                  beats_max_tile=bool(exc > dmax),
                                  uniform=p['uniform'],
                                  # NOTE 27 Aug: do NOT add mode / sigma /
                                  # sign_every / bound_per_um here. The ** splat
                                  # below already supplies them from the panel
                                  # dict, and a duplicate keyword makes dict()
                                  # raise TypeError at call time -- in the
                                  # scoring block, after the write.
                                  design=design, cmd=float(p['cmd']),
                                  dom0=float(p['dom0']), dom=s1['dom'],
                                  switched=ok, period_nm=p['period_nm'],
                                  # Inherit the panel's descriptive fields, so
                                  # the verdict can read either dict. IT5
                                  # crashed on W[k]['sigma'], which lives only
                                  # on `panels`.
                                  **{_k: p[_k] for _k in
                                     ('sigma', 'dwell', 'mode', 'sign_every',
                                      'n_bound', 'bound_per_um', 'ratio')
                                     if _k in p})
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
    print('IT12 VERDICT')
    print('=' * 74)
    P = res['panels']
    W = res['within_frame']
    order = ['ISO', 'DEN', 'Q4']
    order = [k for k in order if k in W]
    NAME = {'ISO': 'Lambda/2 both ways (the standard recipe)',
            'DEN': 'Lambda/4 ALONG the lines, Lambda/2 across',
            'Q4': 'Lambda/4 both ways'}

    def _ontgt(k):
        return abs((W[k]['dom'] - W[k]['cmd'] + 90) % 180 - 90) < 1e-6

    def _cleared(k):
        return W[k]['excess'] > W[k]['threshold']

    print('  every arm: same command, same sigma to machine precision, same')
    print('  panel footprint. Only the lattice geometry differs.')
    print('')
    print('  %-4s%-32s%9s%9s%8s%9s%9s   %s'
          % ('', 'geometry', 'sites', 'sign P', 'w(cmd)', 'excess', 'x thr',
             'on target'))
    for k in order:
        wk = W[k]
        print('  %-4s%-32s%9d%9s%8.3f%+9.3f%9.1f   %s'
              % (k, NAME[k], P[k]['n'],
                 '%.2f L' % (wk['period_nm'] / LAM), wk['w_cmd'],
                 wk['excess'], wk['x2sd'],
                 'YES' if _ontgt(k) else 'no -> %.0f' % wk['dom']))

    # ---- the leftover, which is what question 2 actually asks -------------
    print('')
    print('  LEFTOVER along each panel own ORIGINAL director:')
    print('  %-4s%12s%12s%12s   %s'
          % ('', 'w(start) b', 'w(start) a', 'change', 'reading'))
    left = {}
    for p in panels:
        s0 = ds(F_REF, p['cx'], p['cy'], WIN, triad, p['dom0'])
        s1 = ds(a1, p['cx'], p['cy'], WIN, triad, p['dom0'])
        if not (s0 and s1):
            continue
        left[p['label']] = dict(w0=float(s0['w_cmd']), w1=float(s1['w_cmd']),
                                d=float(s1['w_cmd'] - s0['w_cmd']))
        print('  %-4s%12.3f%12.3f%+12.3f   %s'
              % (p['label'], s0['w_cmd'], s1['w_cmd'],
                 s1['w_cmd'] - s0['w_cmd'],
                 'cleared below an equal split' if s1['w_cmd'] < 0.25
                 else 'original still present'))
    res['leftover'] = left
    print('  an equal three-way split is 0.333; a depleted member should go')
    print('  BELOW that, and 0.17 would be a genuinely clean rewrite.')

    ok_ref = 'ISO' in W and _cleared('ISO')
    res.update(design_order=order, cleared=[k for k in order if _cleared(k)],
               on_target=[k for k in order if _ontgt(k)],
               iso_den_matched=bool(_iso_den_matched))

    # ---- the comparisons, in the order they were pre-registered ----------
    print('')
    if not ok_ref:
        print('  -> VOID. ISO is the standard recipe and it did not clear the')
        print('     leave-one-out null in this frame, so there is no working')
        print('     positive control and neither DEN nor Q4 can be read')
        print('     against anything. Every earlier iteration used this exact')
        print('     geometry and it worked, so suspect the frame before the')
        print('     physics: check the meter log, the flatness report, the')
        print('     VDART and the tile count. Record nothing about density.')
        st['strikes'] = st.get('strikes', 0) + 1
    else:
        w_iso = W['ISO']['w_cmd']
        w_den = W['DEN']['w_cmd'] if 'DEN' in W else float('nan')
        w_q4 = W['Q4']['w_cmd'] if 'Q4' in W else float('nan')
        thr = max(W[k]['threshold'] for k in order)
        d_di = w_den - w_iso
        d_qd = w_q4 - w_den
        print('  w(cmd):  ISO %.3f   DEN %.3f   Q4 %.3f      threshold %.3f'
              % (w_iso, w_den, w_q4, thr))
        print('  DEN - ISO = %+.3f   (density at FIXED sign period)' % d_di)
        print('  Q4  - DEN = %+.3f   (additionally HALVING the sign period)'
              % d_qd)
        if not _iso_den_matched:
            print('  !! ISO and DEN started from different members, so')
            print('     DEN - ISO is confounded with the starting state and the')
            print('     reading below is provisional (Q13).')
        big_di, big_qd = abs(d_di) > thr, abs(d_qd) > thr
        # d_qd is nan when Q4 was dropped, so big_qd is False and no
        # Q4-dependent branch can fire. Assert it rather than trust it:
        # a KeyError here would land AFTER the write.
        assert ('Q4' in W) or not big_qd, 'Q4 branch without Q4'
        st['strikes'] = 0
        if big_di and not big_qd and d_di > 0:
            print('')
            print('  -> WITHIN-LINE DENSITY IS WHAT MATTERS. Doubling the site')
            print('     density ALONG the same-polarity lines raised w(cmd) by')
            print('     %+.3f while additionally halving the sign period added' % d_di)
            print('     only %+.3f. So C48s purity-versus-spacing law is a' % d_qd)
            print('     DENSITY law, not a sign-period law, and C41 (period')
            print('     does not matter over Lambda..8Lambda) extends downward.')
            print('     PRACTICAL ANSWER to the leftover question: densify')
            print('     along the lines and keep the period.')
            if 'Q4' in P:
                print('     DEN reaches this with %d sites against Q4s %d - '
                      'half the travel for the same result.'
                      % (P['DEN']['n'], P['Q4']['n']))
            else:
                print('     Q4 was not written in this frame, so whether')
                print('     halving the sign period would add more is untested')
                print('     here; C39/C48 put Lambda/4 at w(cmd) 0.83-0.86.')
        elif big_qd and not big_di and d_qd > 0:
            print('')
            print('  -> THE SIGN PERIOD IS WHAT MATTERS, not within-line')
            print('     density. Densifying along the lines at fixed period')
            print('     bought %+.3f; halving the period bought %+.3f.' % (d_di, d_qd))
            print('     This CONTRADICTS C41, which found every period from')
            print('     Lambda to 8*Lambda equivalent - and it means C48s')
            print('     spacing law is really about the sign period. The two')
            print('     were confounded in all previous data because one')
            print('     spacing set both. Reconciling C41 with this is now the')
            print('     open question.')
        elif big_di and big_qd and d_di > 0 and d_qd > 0:
            print('')
            print('  -> BOTH CONTRIBUTE. Density along the lines gave %+.3f and'
                  % d_di)
            print('     halving the period gave a further %+.3f. Report the'
                  % d_qd)
            print('     split rather than a single mechanism; the practical')
            print('     recipe is Q4 if purity is worth the travel, DEN if it')
            print('     is not.')
        elif not big_di and not big_qd:
            print('')
            print('  -> NEITHER KNOB MOVES PURITY at this sigma. All three')
            print('     geometries land within one threshold of each other')
            print('     (%.3f, %.3f, %.3f against %.3f). Then C48s'
                  % (w_iso, w_den, w_q4, thr))
            print('     spacing-sets-purity result was confounded with')
            print('     something else - sigma, or the area - and the leftover')
            print('     cannot be removed by geometry alone at this dose.')
        else:
            print('')
            print('  -> MIXED / UNEXPECTED: DEN - ISO %+.3f, Q4 - DEN %+.3f'
                  % (d_di, d_qd))
            print('     against a threshold of %.3f. At least one difference' % thr)
            print('     runs the wrong way, so no pre-registered reading')
            print('     applies. Report the three numbers and the leftovers')
            print('     and do not choose a mechanism.')
        if left:
            best = min(left, key=lambda k: left[k]['w1'])
            print('')
            print('  lowest residual along the original director: %s at %.3f'
                  % (best, left[best]['w1']))
            if left[best]['w1'] >= 0.25:
                print('     -> no arm cleared the original member below an')
                print('        equal split, so the leftover survives every')
                print('        geometry tried. The next lever is dose or a')
                print('        second pass, not spacing.')

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
    name='IT12_leftovers',
    hypothesis=('Every panel in this campaign alternated sign perpendicular to '
                'the command, so the sign-boundary LINES always ran parallel to '
                'the commanded axis. "The director follows the lattice axis" and '
                '"the director follows the sign boundaries" are therefore not '
                'distinguishable by anything run so far. C46 favours the second: '
                'the re-scored magnitudes are monotonic in boundary count - 16 '
                'boundaries 7.3x, 4 boundaries 5.7x, 1 boundary 2.5x, uniform '
                'nothing - which looks like a boundary effect rather than a '
                'periodicity effect.'),
    prediction=('Four panels, two per condition, identical sites, sigma, '
                'lattice and command. PAR alternates sign across the command so '
                'its boundaries run along it; PERP alternates along the command '
                'so its boundaries run across it. If the axis selects, both '
                'rotate the director to the command. If the boundary selects, '
                'PAR rotates and PERP does not - and if it selects by '
                'direction, PERP ends on a different triad member.'),
    outcomes={'both rotate to the command':
              'the lattice axis is the mechanism; boundary orientation is '
              'irrelevant and C46s trend is about boundary density',
              'PAR rotates, PERP does not':
              'the sign boundary is the mechanism - answers Q19 and rewrites '
              'T3 around boundary orientation',
              'PERP ends on a different member':
              'the strongest form of the same answer: the director follows the '
              'boundary lines',
              'neither rotates':
              'void, not negative - the positive control failed, so nothing '
              'can be read from the comparison'},
    caveat=('Two replicates per condition, deliberately: IT4 rested on one '
            'panel per condition and its reference arm turned out to have a '
            'different starting population from the panels it was meant to '
            'calibrate. Slots are matched on (dominant, command) where the '
            'frame allows, and the pairing is printed. Everything else is '
            'unchanged - one sigma, period Lambda, Lambda/2 spacing, 100 % '
            'density - so a PAR/PERP difference is geometry and nothing else.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
    panels=[dict(label=l, keep=1.0, dwell=None, sign_every=1, mode=m,
                 spacing_div=2.0)
            for (l, m, _w) in SPEC])

try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(PROP, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT12 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT12 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it12_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
