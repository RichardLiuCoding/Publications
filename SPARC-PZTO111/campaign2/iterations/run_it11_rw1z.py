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
    Two panels, identical period Lambda, identical Lambda/2 spacing, identical
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
    - a 2x2 layout settles four slots, of which TWO are written and two are
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

# 14 um, not 12. At Lambda 354 and the rotated triad's worst ANGF 1.411 the
# halo is 2.50 um and pitch 5.10 um, so a 12 um frame settles only a 2x1
# layout -- TWO slots, hence no selection freedom, and attempt 4 halted
# because those two slots started from different members (19 and 79 deg),
# which is precisely C54's confound. Shrinking the reserved tile band to
# force 2x2 into 12 um was checked and rejected: it gains four slots and
# leaves ZERO control tiles, so the C45 null would have no sample.
# 14 um fits 2x2 with ~36 tiles, giving four slots to select two matched
# ones from, at a cost of 0.9 min per frame.
FRAME, PX = 14.0, 256
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
# label, rotation SENSE off the local dominant, description. sigma, spacing,
# density, n and geometry are identical across all four - the only difference is
# which of the two neighbours is commanded. Two replicates per sense, because
# C54 rests on one panel per condition and cannot separate its two explanations.
SIG_RATIO = 1.29           # 1.29 sigma_c: IT9 wrote its rewrite panel here
SPEC = [('P+', +1, 'reach the +60 deg neighbour'),
        ('P-', -1, 'reach the -60 deg neighbour')]
NWRITE = 2                 # written panels. FOUR DOES NOT FIT: at Lambda 354 nm
                           # the halo is 2.45 um, and four panels on a 2x2 grid
                           # at pitch 5.0 um leave 0 of 49 grid tiles clear of
                           # every panel, so the C45 null has no sample at all
                           # (measured in the offline sim, PITFALLS 2.4).

ZOOM_UM   = 5.0            # 15.4 px per lamellar period: resolves the stripes,
ZOOM_PX   = 256            # and still fits ~4 director windows across
DETAIL_UM = 2.0            # 38 px per period; ONE window, so structure only
ANG_CTRL  = 90.0           # scan-angle control: rotates the streak axis
FLAT_REL = 1.5          # reject a slot or tile whose height range exceeds
                        # this multiple of the median range in the same frame.
                        # Relative, because the absolute scale is unknown and
                        # varies with sample, scan size and noise.
N_MULT = 16      # so sign_every = 8 balances exactly: 8 rows +, 8 rows -

# Set to reuse an area already screened and baselined in this session, instead
# of re-spending the probe life. None = screen normally.
# Resume on the (0,0) baselines taken 17:09-17:20 with per-frame re-tuning:
# |A| 115/108/110 pm, r12 +0.97, floor 0.087, flip 21 % -- the first triplet all
# session to pass the measurability gate. Nothing has been written there, so the
# frames still describe the area. Reproducing them costs ~48 min the clock does
# not have. Set back to None for a fresh area.
RESUME = None   # the 12 um baselines cannot be reused at 14 um

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
    print('IT11/RW1-Z  pathway map: which neighbour can you reach?  %s' % time.strftime('%Y-%m-%d %H:%M'))
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
        # five candidates, not three: the screening-time feasibility gate
        # now rejects areas whose (triad, Lambda) cannot be built on, and
        # Lambda scatters 245-482 nm here (M5), so a buildable area is not
        # assured in three. A rejected candidate costs one frame (~6 min)
        # rather than the four it cost before the gate existed.
        for attempt, (xo, yo) in enumerate(cands[:5]):
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
                # ---- can a matched pair actually be BUILT here? ----------
                # Everything here follows from Lambda and the triad, which we
                # have now. IT11's first launch skipped this, chose an area on
                # modulation alone, and would have halted at placement with
                # n = 32 and no layout fitting -- after three baselines.
                _lam_c = cand['lam']
                _sp_c = _lam_c / 2000.0
                _win_c = max(4.2 * _lam_c / 1000.0, 26 * PX_NM / 1000.0)
                _worst = max(abs(np.cos(np.deg2rad(t)))
                             + abs(np.sin(np.deg2rad(t)))
                             for t in cand['triad'])
                _need = _win_c * _worst + 2 * (_sp_c + 0.10)
                _n_c = int(max(N_MULT, N_MULT * round((_need / _sp_c + 1)
                                                      / float(N_MULT))))
                while (_n_c - 1) * _sp_c < _need and _n_c < 128:
                    _n_c += N_MULT
                _halo_c = (_n_c - 1) * _sp_c * _worst / 2 + R_EFF
                _pitch_c = 2 * _halo_c + 0.10
                _lay_c = None
                for (_nc, _nr) in ((2, 2), (2, 1)):
                    _xs = [FRAME / 2 + (j - (_nc - 1) / 2.0) * _pitch_c
                           for j in range(_nc)]
                    _y0 = 0.35 + _win_c + 0.05 + _halo_c
                    _ys = [_y0 + r * _pitch_c for r in range(_nr)]
                    if (any(x - _halo_c < 0.05 or x + _halo_c > FRAME - 0.05
                            for x in _xs)
                            or max(_ys) + _halo_c > FRAME - 0.05):
                        continue
                    _lay_c = (_nc, _nr)
                    break
                _unit_c = V / _sp_c ** 2
                _pn_c = max(1, int(round((SIG_RATIO * sc / _unit_c)
                                         * SPEED / STEP)))
                _chg_c = V * _pn_c * STEP / SPEED
                _why = []
                if _n_c != N_MULT:
                    _why.append('n would be %d not %d (the %.2f um window does '
                                'not fit inside a %d-site panel at %.0f nm '
                                'spacing)' % (_n_c, N_MULT, _win_c, N_MULT,
                                              _sp_c * 1000))
                if _lay_c is None:
                    _why.append('no layout fits (halo %.2f um needs pitch '
                                '%.2f um in a %.0f um frame)'
                                % (_halo_c, _pitch_c, FRAME))
                if _chg_c > 0.5 * A.CHG_1PULSE_MAX:
                    _why.append('%.1f V.s per site, over half C21s %.0f'
                                % (_chg_c, A.CHG_1PULSE_MAX))
                if _why:
                    print('     NOT BUILDABLE: %s' % '; '.join(_why))
                    print('     worst command ANGF %.3f on triad %s, '
                          'Lambda %.0f nm'
                          % (_worst, [int(round(t)) for t in cand['triad']],
                             _lam_c))
                    continue
                cand['n'] = _n_c
                cand['halo'] = _halo_c
                cand['layout'] = _lay_c
                print('     buildable: n %d, halo %.2f um, %dx%d layout, '
                      '%d pulses (%.1f V.s per site)'
                      % (_n_c, _halo_c, _lay_c[0], _lay_c[1], _pn_c, _chg_c))
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
        print('    each baseline is taken through tune_here, i.e. RE-TUNED')
        print('    first. Measured tonight: screening frames, which re-tune per')
        print('    frame, held |A| 79-110 pm all afternoon, while bare')
        print('    consecutive frames fell 40 -> 21 pm within two frames and')
        print('    took the flip rate to 58 %. The contact resonance drifts over')
        print('    ~5-10 min and the DART loop loses it unless re-tuned.')
        print('    tune_here re-issues the SAME offset, so nothing moves and the')
        print('    frames stay consecutive at one position (which is what the')
        print('    triplet is for). The observable is a within-frame population')
        print('    RATIO, so a tune change between frames does not bias it the')
        print('    way an amplitude comparison would (HANDOFF_2 1).')
        _bl = []
        for _i in range(3):
            _c, _inf = g('tune_here')('ldart', size_um=FRAME, px=PX, rate=RATE,
                                      angle_deg=0.0, xoff_um=XOFF,
                                      yoff_um=YOFF, tries=1)
            _bl.append(_inf['frame'])
            print('    baseline %d: %s (tune centre %.1f kHz)'
                  % (_i + 1, _inf['frame'], (_c or 0) / 1e3))
        b1, b2, b3 = _bl
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

    # ---- placement, sized for the WORST command angle -----------------
    # RW1-Z commands BOTH neighbours of one dominant, and those two are 120 deg
    # apart, so whichever member is dominant, one of the two commands always
    # lands on a large ANGF = |cos| + |sin|. Nothing may be sized on the cheap
    # one: PITFALLS 7.3, anything fixed before the commands are known must
    # assume the worst angle. There is therefore no fixed point to iterate --
    # sizing is deterministic on max(ANGF) over the whole triad.
    print('\n--- placement, sized for the worst command angle ---')
    ang_use = max(ANGF.values())
    print('    ANGF per triad member: %s  ->  sizing on %.3f'
          % (', '.join('%.0f deg %.3f' % (t, ANGF[t]) for t in triad), ang_use))
    settled = None
    for ncol, nrow in ((3, 2), (3, 1), (2, 2), (2, 1)):
        n0, halo, pitch = geom(ang_use)
        xs = [FRAME / 2 + (j - (ncol - 1) / 2.0) * pitch for j in range(ncol)]
        y0 = 0.35 + WIN + 0.05 + halo
        ys_ = [y0 + r * pitch for r in range(nrow)]
        cand_slots = [(x, y) for y in ys_ for x in xs]
        fits = not (any(x - halo < 0.05 or x + halo > FRAME - 0.05 for x in xs)
                    or max(ys_) + halo > FRAME - 0.05)
        print('    %dx%d: n %d, halo %.2f, pitch %.2f -> %s'
              % (ncol, nrow, n0, halo, pitch,
                 'fits' if fits else 'does NOT fit'))
        if fits:
            settled = (ncol * nrow, ang_use, n0, halo, pitch, cand_slots)
            break
    if settled is None:
        raise SystemExit('no grid of panels settles here at factor %.3f'
                         % ang_use)
    nslot, ang_use, n0, halo, pitch, slots = settled

    # ---- per slot: its dominant, and BOTH candidate commands ----------
    # run_it5 kept only the cheaper sense per slot. RW1-Z needs both, because
    # here the sense IS the independent variable rather than a balancing choice.
    cm = []
    for (cx, cyy) in slots:
        both = {}
        for sense in (+1, -1):
            cf = g('command_for')(F_REF, cx, cyy, WIN, triad, sense=sense,
                                  min_lead=0.05, verbose=False)
            if cf is None:
                raise SystemExit('slot (%.2f,%.2f) not measurable' % (cx, cyy))
            both[sense] = cf
        assert both[+1]['dom'] == both[-1]['dom'], 'sense changed the dominant'
        cm.append(dict(dom=both[+1]['dom'], w=both[+1]['w'],
                       lead_dom=both[+1]['lead_dom'], ok=both[+1]['ok'],
                       cmd_p=float(both[+1]['cmd']),
                       cmd_m=float(both[-1]['cmd']),
                       cmd=float(both[+1]['cmd'])))
    print('\n    slot dominants and the two reachable neighbours:')
    for i, ((cx, cyy), c) in enumerate(zip(slots, cm)):
        print('      slot %d (%5.2f,%5.2f)  dominant %3.0f (leads %.3f%s)   '
              '+60 -> %3.0f   -60 -> %3.0f'
              % (i, cx, cyy, c['dom'], c['lead_dom'],
                 '' if c['ok'] else '  TOO CLOSE TO CALL',
                 c['cmd_p'], c['cmd_m']))
    nwrite = min(NWRITE, nslot)
    use = list(SPEC[:nwrite])
    if nwrite < NWRITE:
        raise SystemExit('only %d slots fit; need %d (one per sense)'
                         % (nwrite, NWRITE))
    print('  settled: %d slots for %d panels, factor %.3f, n %d, halo %.2f, '
          'pitch %.2f' % (nslot, nwrite, ang_use, n0, halo, pitch))

    # ---------------------------------------- dose: ONE, for all four
    # This iteration varies the commanded SENSE and nothing else, so the dwell
    # is solved once and every panel gets identical sigma, spacing, density, n
    # and geometry. Any difference between panels is then the sense.
    unit = (1 / sp ** 2) * V                # sigma per second of dwell
    pn = max(1, int(round((SIG_RATIO * sc / unit) * SPEED / STEP)))
    dwell = pn * STEP / SPEED
    sigma = unit * dwell
    print('\n  dose, identical for both panels:')
    print('    spacing %.0f nm  ->  %.0f V.s/um^2 per second of dwell'
          % (sp * 1000, unit))
    print('    target %.2f sigma_c -> %d pulses -> dwell %.2f s -> sigma %.0f '
          '= %.2f sigma_c   (%.1f V.s per site)'
          % (SIG_RATIO, pn, dwell, sigma, sigma / sc, V * dwell))
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.1f V.s per site is over half C21s %.0f V.s, so '
                         'switching would go site-by-site instead of '
                         'collectively' % (V * dwell, A.CHG_1PULSE_MAX))
    _nsite = n0 * n0 * len(SPEC)
    print('    %d sites x %d pulses -> %.1f min of dwell. Travel comes from '
          'the BUILT path, never an estimate: the 1.35x rule only holds near '
          'dwell 1.4 s, and measured overhead ran 1.29-1.53x.'
          % (_nsite, pn, _nsite * pn * STEP / SPEED / 60.0))
    sig_of = {lab: (sigma, dwell, pn) for (lab, _s, _w) in SPEC}


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
    # NWRITE, not 4. Patch 9 cut the design from four panels to two and left
    # this literal behind; the feasibility gate then settled a 2x1 layout and
    # this line demanded four flat slots from two, halting the run AFTER it had
    # passed the floor gate at 0.087 / 21 %. The decision rule below handles the
    # rest: with two slots it requires both to share a dominant.
    if len(flat_ok) < NWRITE:
        raise SystemExit('only %d of %d slots are flat and this design needs '
                         '%d, one per sense. The terrace crosses this area. '
                         'Move.' % (len(flat_ok), len(slots), NWRITE))

    # ---- the decision rule, fixed on the BASELINE, before any write ----
    # Only 4 slots fit at the worst command angle, so there is no selection
    # freedom and the matching has to come from the area itself. Which design
    # runs is therefore decided here, from the baseline frame alone. Deciding
    # it after seeing the result would be choosing the analysis to fit the data.
    #
    #   4 flat slots share a dominant -> DESIGN P: two replicates per sense off
    #       one starting member. Separates a FORBIDDEN transition from a
    #       STOCHASTIC one, which is what C54 (n = 1 per cell) could not do.
    #   slots split 2/2               -> DESIGN Q: two starting members x two
    #       senses, one panel per cell. No replicate, so stochasticity is
    #       untestable -- but DIRECTION and HISTORY separate cleanly, which is
    #       the actual C54 ambiguity.
    #   anything else                 -> void, screen elsewhere.
    from collections import Counter as _Counter
    dom_of = {i: int(round(cm[i]['dom'])) for i in flat_ok}
    tally = _Counter(dom_of.values())
    print('\n--- the decision rule, from the baseline ---')
    print('    flat slots by starting dominant: %s'
          % ', '.join('%d deg x%d' % (d, k) for d, k in sorted(tally.items())))
    _two = sorted([d for d, k in tally.items() if k >= 2],
                  key=lambda d: (-tally[d], d))
    if not _two:
        raise SystemExit('no starting dominant is shared by even two flat '
                         'slots: %s. The two panels would start from different '
                         'members, which is exactly C54s confound, so the '
                         'comparison would not be matched and nothing here '
                         'would be interpretable. Screen another area.'
                         % dict(tally))
    DESIGN = 'M'                       # M for matched pair
    D0 = _two[0]
    grp = [i for i in flat_ok if dom_of[i] == D0][:2]
    senses = [+1, -1]
    core = [0, 1]
    print('    -> DESIGN M: both panels start from %d deg, one per sense.'
          % D0)
    print('       This is C54s comparison with its confound removed: C54s two')
    print('       panels started from DIFFERENT members, so direction and')
    print('       history could not be separated. These share a start, so a')
    print('       difference between them is the rotation sense and nothing')
    print('       else.')
    print('       What it does NOT give: a replicate per sense. A stochastic')
    print('       transition therefore cannot be told from a forbidden one,')
    print('       and that branch is not in the pre-registration.')
    _left = [i for i in flat_ok if i not in grp]
    print('       %d settled slot(s) left UNWRITTEN, at the same height as the')
    print('       panels: they carry control tiles, which four panels did not')
    print('       leave room for (0 of 49 tiles cleared in the offline sim).'
          % ())
    _ = _left

    assign = list(grp)
    assert len(set(assign)) == NWRITE, 'two panels in one slot'
    ctrl_slots = [i for i in range(len(slots)) if i not in assign]
    CORE = list(core)
    print('    written: %s   unwritten (control): %s'
          % (', '.join(SPEC[k][0] for k in range(NWRITE)),
             ', '.join('slot %d' % i for i in ctrl_slots) or 'none'))

    # SPEC fixes the sense per label; the assignment must agree with it, or the
    # printed table and the analysis would disagree about what was written.
    use = [(SPEC[k][0], senses[k], SPEC[k][2]) for k in range(NWRITE)]

    # the command each panel actually gets: from ITS OWN dominant, its own sense
    cmd_of = {}
    for k in range(NWRITE):
        si = assign[k]
        cmd_of[k] = cm[si]['cmd_p'] if senses[k] > 0 else cm[si]['cmd_m']
    print('\n    %-4s%7s%8s%8s%10s  %s'
          % ('', 'slot', 'start', 'sense', 'command', 'position'))
    for k in range(NWRITE):
        si = assign[k]
        print('    %-4s%7d%8.0f%8s%10.0f  (%.2f,%.2f)'
              % (use[k][0], si, cm[si]['dom'], '%+d' % senses[k], cmd_of[k],
                 slots[si][0], slots[si][1]))
    print('    unwritten slots: %s'
          % (', '.join('%d' % i for i in ctrl_slots) or 'none'))
    # S22: the command must be a triad member, 60 deg off THAT panel's dominant
    for k in range(NWRITE):
        si = assign[k]
        c_, d_ = cmd_of[k], cm[si]['dom']
        assert min(abs(c_ - t) for t in triad) < 1e-6, \
            'panel %s command %.3f is not a triad member' % (use[k][0], c_)
        assert abs(c_ - d_) > 1e-6, \
            'panel %s commanded to its own dominant' % use[k][0]
    # both senses must actually be present, or there is no experiment
    assert len(set(senses)) == 2, 'both senses required'
    # and the two senses must give DIFFERENT commands from a shared dominant,
    # the two senses must give DIFFERENT commands from the shared
    # dominant, which is the entire content of the design
    assert len({cmd_of[k] for k in range(NWRITE)}) == NWRITE, \
        'the two senses produced the same command'

    # ---- build, then FIT THE DOSE TO THE CAP from the real path -------
    # The write cap must be enforced on the BUILT trajectory, never on an
    # estimate: travel points are fixed per site by the geometry while dwell
    # points scale with dwell, so the overhead multiplier is not a constant
    # (measured 1.29x at dwell 1.48 s, 1.53x at 0.48 s). An estimate once passed
    # the cap while the real path was 28 min against 26.
    PN_FLOOR = max(1, int(round((0.70 * sc / unit) * SPEED / STEP)))
    pn_try = pn
    for _attempt in range(4):
        panels = []
        tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP,
                                     travel_v=0.0)
        if _attempt == 0:
            print('\n  %-4s%7s%8s%8s%12s%8s%8s  %s'
                  % ('', 'start', 'sense', 'cmd', 'period', 'sites', 'sigma',
                     'tests'))
        for k, (lab, sn, what) in enumerate(use):
            se = 1                # balanced; sign period = 2*se*sp = Lambda
            si = assign[k]
            cx, cy = slots[si]
            cmd_k = cmd_of[k]
            dwell_k = pn_try * STEP / SPEED
            sigma_k = unit * dwell_k
            sites = g('lattice_panel')(n0, sp, (cx, cy), cmd_k, V,
                                       sign_every=se, keep_frac=1.0)
            vv_ = np.array([q[2] for q in sites])
            assert abs(vv_.mean()) < 1e-9, '%s net DC' % lab
            for (x0, y0, v0) in sites:
                tb.dwell((x0, y0), v0, n=pn_try)
            panels.append(dict(label=lab, uniform=None, cx=cx, cy=cy,
                               slot=si, cmd=float(cmd_k),
                               dom0=float(cm[si]['dom']), sign_every=se,
                               sigma=sigma_k, dwell=dwell_k, ratio=SIG_RATIO,
                               sense=int(sn), design=DESIGN,
                               n=len(sites), period_nm=2 * se * sp * 1000,
                               ref=F_REF, tests=what))
            if _attempt == 0:
                print('  %-4s%7.0f%8s%8.0f%12s%8d%8.0f  %s'
                      % (lab, cm[si]['dom'], '%+d' % sn, cmd_k,
                         '%.1f L' % (2 * se * sp * 1000 / LAM), len(sites),
                         sigma_k, what))
        _X, _Y, _V = tb.to_arrays()
        _min = len(_V) * STEP / SPEED / 60.0
        _nsites = sum(p['n'] for p in panels)
        _travel = len(_V) - _nsites * pn_try
        if _attempt == 0:
            print('\n    built path: %d pts = %.2f min  (%d dwell + %d travel; '
                  'overhead %.2fx, %.0f travel pts per panel)'
                  % (len(_V), _min, _nsites * pn_try, _travel,
                     len(_V) / float(_nsites * pn_try),
                     _travel / float(len(panels))))
        if _min <= A.MAX_WRITE_MIN:
            break
        # largest pulse count whose dwell fits in what the cap leaves after the
        # travel this geometry actually costs
        cap_pts = A.MAX_WRITE_MIN * 60.0 * SPEED / STEP
        pn_fit = int((cap_pts - _travel) // _nsites)
        print('    !! %.2f min is over the %.0f min cap. Travel alone is '
              '%.2f min, so the dwell must drop from %d to %d pulses.'
              % (_min, A.MAX_WRITE_MIN, _travel * STEP / SPEED / 60.0,
                 pn_try, pn_fit))
        if pn_fit < PN_FLOOR:
            raise SystemExit(
                'the cap allows only %d pulses per site = %.2f sigma_c, below '
                'the 0.70 sigma_c that is the lowest dose known to select '
                '(C47). Without a working positive control in the frame a null '
                'means nothing, so this is not a dose to write at. Lambda here '
                'is %.0f nm, which makes Lambda/2 spacing expensive; use a '
                'smaller-Lambda area or write 3 panels instead of 4.'
                % (pn_fit, unit * pn_fit * STEP / SPEED / sc, LAM))
        if pn_fit >= pn_try:
            raise SystemExit('cap refit did not reduce the pulse count '
                             '(%d -> %d); refusing to loop' % (pn_try, pn_fit))
        pn_try = pn_fit
    else:
        raise SystemExit('could not fit the write cap in 4 attempts')
    if pn_try != pn:
        pn = pn_try
        dwell = pn * STEP / SPEED
        sigma = unit * dwell
        print('    -> refitted to %d pulses: dwell %.2f s, sigma %.0f = '
              '%.2f sigma_c, %.1f V.s per site. Both panels moved '
              'together, so the comparison between senses is untouched.'
              % (pn, dwell, sigma, sigma / sc, V * dwell))
        if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
            raise SystemExit('%.1f V.s per site after refit is over half '
                             'C21s %.0f V.s' % (V * dwell, A.CHG_1PULSE_MAX))
        for p in panels:
            assert abs(p['sigma'] - sigma) < 1e-6, 'panel sigma out of step'
    sig_of = {lab: (sigma, dwell, pn) for (lab, _s, _w) in SPEC}
    # the arrays and the write time come from the path that will actually be
    # sent, i.e. the last build of the refit loop -- not from any estimate
    X, Y, Vv = _X, _Y, _V
    wr = len(Vv) * STEP / SPEED / 60.0
    tot = sum(p['n'] for p in panels)

    print('\n  %d pulses, %d pts, mean V %+.6f, %.1f min of writing'
          % (tot, len(Vv), Vv.mean(), wr))
    # No panel in this iteration is uniform-polarity, so the +/- pairing
    # bookkeeping run_it5 needed is dead code here. What still matters is that
    # every panel is individually balanced (asserted at build) and that the
    # FILE carries no net DC (asserted below) - C13.

    assert abs(Vv.mean()) < 1e-6 and np.abs(Vv).max() <= V + 1e-9
    assert X.min() > 0.05 and X.max() < FRAME - 0.05
    assert Y.min() > 0.05 and Y.max() < FRAME - 0.05
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('%.1f min over the %.0f min cap' % (wr,
                                                            A.MAX_WRITE_MIN))
    if os.path.exists(A.STOP):
        raise SystemExit('STOP appeared before the write')
    print('\n  predictions, fixed now, and what each would mean:')
    print('    both senses end on their command')
    print('        the transition is SYMMETRIC from this member. C54 was a')
    print('        fluke or specific to its area, and fidelity is not')
    print('        direction-limited here.')
    print('    one sense misses target while still clearing the threshold')
    print('        a SINK or a forbidden transition. Report which member')
    print('        absorbs; that is the answer to Q31 and the ceiling on')
    print('        patterning fidelity.')
    print('    NOT testable here: whether a failure is FORBIDDEN or merely')
    print('        STOCHASTIC. A matched pair has one panel per sense, so a')
    print('        single miss cannot be told from bad luck. That branch is')
    print('        deliberately absent from the pre-registration rather than')
    print('        left in as something this design could report.')
    print('    all four land on the THIRD member')
    print('        the film routinely passes THROUGH the third member and')
    print('        %.2f sigma_c does not complete it. C54 becomes an' % SIG_RATIO)
    print('        unfinished transition, not a failure, and the fix is dose.')
    print('    nothing clears the leave-one-out threshold')
    print('        VOID, not negative: the control failed too, so this says')
    print('        nothing. Check the gates and do not interpret any panel.')


    # ---- zoom readout ------------------------------------------------
    # The 12 um frame gives 6.4 px per lamellar period, so the director there is
    # a statistic over structure the frame cannot resolve. A 5 um frame gives
    # 15.4 px per period and still fits ~4 director windows across, and because
    # a 5 um frame centred on a 2.4 um panel leaves a ~1.3 um untreated annulus
    # it is SELF-REFERENCING: panel against surround, inside one frame.
    #
    # Measured offline against the July 5 um frames before committing to this:
    # consecutive same-offset frames drift 37-74 nm (0.12-0.25 Lambda), and the
    # residual after a stage excursion is under 25 nm with peak/background
    # 71 +- 45 over 20 pairs. So zooming out and back does NOT lose the spot,
    # and the drift is correctable from Height, which the write does not change.
    #
    # Zoomed panels are ONE PER SENSE, not all four. At 5 um the line spacing is
    # 19.5 nm against 46.9 nm at 12 um, so the tip passes 2.4x more often per
    # unit area, and 6x at 2 um. Zooming half the panels keeps the sense
    # comparison balanced AND makes (zoomed vs unzoomed) a free control on
    # whether the readout itself perturbs the state - RW4's third branch.
    # Zoom EVERY written panel. With one panel per sense there is no way to
    # zoom "half" of them without reading the two senses unequally, and the
    # sense comparison is the whole experiment (PITFALLS 7.1: two arms given
    # different tasks are not a comparison). The cost is that the
    # zoomed-versus-unzoomed control on readout perturbation is gone; that
    # question goes to a later iteration instead of being claimed here.
    ZK = list(range(NWRITE))
    print('\n--- zoom plan ---')
    print('    %.0f um / %d px = %.1f nm/px = %.1f px per period; %.1f director '
          'windows across' % (ZOOM_UM, ZOOM_PX, ZOOM_UM * 1000.0 / ZOOM_PX,
                              LAM / (ZOOM_UM * 1000.0 / ZOOM_PX),
                              ZOOM_UM / WIN))
    print('    zooming every written panel: %s. No unzoomed panel remains, so'
          % ', '.join(use[k][0] for k in ZK))
    print('    this iteration does NOT test whether the 5 um reads perturb the')
    print('    state -- reading the two senses unequally would confound the one')
    print('    comparison the design exists to make.')
    _zrate = A.TIP_SPEED_MAX / (2.0 * ZOOM_UM)
    _drate = A.TIP_SPEED_MAX / (2.0 * DETAIL_UM)
    print('    cost: %d x %.1f min (%.0f um) + %d x %.1f min (%.0f um) per pass'
          % (len(ZK), ZOOM_PX / _zrate / 60.0, ZOOM_UM,
             len(ZK), ZOOM_PX / _drate / 60.0, DETAIL_UM))
    # the annulus must actually hold a legal window, or the zoom is not
    # self-referencing and is structure-only
    _pan_um = (n0 - 1) * sp * ang_use
    _ann = 0.5 * (ZOOM_UM - _pan_um)
    print('    panel spans %.2f um at the worst angle -> annulus %.2f um per '
          'side, window %.2f um -> %s'
          % (_pan_um, _ann, WIN,
             'self-referencing' if _ann >= WIN else
             'STRUCTURE ONLY (annulus < window)'))

    def zooms(stage, panel_keys, detail=False):
        # 5 um (and optionally 2 um) frames centred on the given panels.
        out = {}
        scales = [(ZOOM_UM, ZOOM_PX, 'z')]
        if detail:
            scales.append((DETAIL_UM, ZOOM_PX, 'd'))
        # try/finally, not a plain restore at the end: run_traj validates the
        # trajectory against tb.field_um but does NOT set the scan geometry, so
        # if frame() raised in here and left the field at 5 um centred on a
        # panel, the write would go into the WRONG FIELD at the wrong offset --
        # a misplaced 512-site lattice on fresh film, unrecoverable and not even
        # recorded as a written area.
        try:
            for k in panel_keys:
                p_lab = use[k][0]
                cx, cy = slots[assign[k]]
                for (sz, px_, tagn) in scales:
                    rate_ = A.TIP_SPEED_MAX / (2.0 * sz)
                    g('setup_scan')(size_um=sz, px=px_, rate=rate_,
                                    angle_deg=0.0,
                                    xoff_um=XOFF + cx - FRAME / 2.0,
                                    yoff_um=YOFF + cy - FRAME / 2.0)
                    t_ = g('frame')()
                    out['%s_%s_%s' % (stage, tagn, p_lab)] = t_
                    print('      %s %-3s %.0f um -> %s' % (stage, p_lab, sz, t_))
        finally:
            g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                            xoff_um=XOFF, yoff_um=YOFF)
        return out

    print('\n--- zooms BEFORE the write ---')
    ZFR = {}
    ZFR.update(zooms('pre', ZK, detail=True))


    # ---------------------------------------------------- write and read
    fn = os.path.join(A.PROJ, 'output', time.strftime('%y%m%d') + '_IT11_RW1Z.txt')
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

    print('\n--- zooms AFTER the write (same panels, same scales) ---')
    ZFR.update(zooms('post', ZK, detail=True))

    # ---- scan-angle control -------------------------------------------
    # Scan lines run along x, so line-to-line offsets put FFT power on q_y and
    # read as a director of 0 deg (C36). Rotating the SCAN by 90 deg moves that
    # artefact axis while leaving the film untouched, so if the triad and the
    # dominant survive the rotation, the directors are structure rather than
    # streak. What this does NOT do is vector PFM: the cantilever's torsional
    # axis is fixed in the lab, so a scan rotation cannot recover the in-plane
    # polarisation SENSE, and the observable stays a stripe orientation defined
    # mod 180 deg. That limit is real, and is reported rather than glossed.
    print('\n--- scan-angle control: the same area at %.0f deg ---' % ANG_CTRL)
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=ANG_CTRL,
                    xoff_um=XOFF, yoff_um=YOFF)
    a90 = g('frame')()
    _reg = (0.35, FRAME - 0.35, 0.35, FRAME - 0.35)
    print('    streak index over the whole frame, 0 deg vs %.0f deg:' % ANG_CTRL)
    try:
        _s0 = g('streak_index')(a1, _reg, verbose=False)
        _s90 = g('streak_index')(a90, _reg, verbose=False)
        print('      %.3f  ->  %.3f   (healthy 0.009-0.077; above 0.10 is a '
              'bad frame)' % (_s0, _s90))
    except Exception as _e:
        print('      streak_index failed on the rotated frame: %s' % _e)
        _s0 = _s90 = float('nan')
    try:
        _t90, _tt90 = g('pin_triad')(a90, ref_fam=g('FAM_FILM'))
        print('    triad at %.0f deg: %s   (0 deg gave %s)'
              % (ANG_CTRL, ['%.0f' % t for t in _t90],
                 ['%.0f' % t for t in triad]))
        print('    -> if these agree within a few degrees the directors are')
        print('       structure, not a scan-line artefact. This does NOT give')
        print('       the in-plane polarisation sense: the observable is a')
        print('       stripe orientation mod 180 deg, and only vector PFM')
        print('       (two lateral scans with the SAMPLE rotated) would fix it.')
    except Exception as _e:
        print('    pin_triad failed on the rotated frame: %s' % _e)
        _t90 = None
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)

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
        design = 'sense %+d, %.0f->%.0f' % (p['sense'], p['dom0'], p['cmd'])
        res_wf[p['label']] = dict(w_cmd=s1['w_cmd'], excess=float(exc),
                                  excess_after=float(exc1),
                                  excess_before=float(exc0),
                                  x2sd=float(exc / max(thr, 1e-9)),
                                  threshold=thr, threshold_w=float(
                                      2.0 * wa.std(ddof=1)),
                                  d_max=dmax,
                                  beats_max_tile=bool(exc > dmax),
                                  uniform=p['uniform'],
                                  sense=int(p['sense']),
                                  slot=int(p['slot']),
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
    print('IT11 / RW1-Z  VERDICT')
    print('=' * 74)
    P = res['panels']
    W = res['within_frame']
    order = [p['label'] for p in panels]
    print('  design %s: %s'
          % (DESIGN, 'a MATCHED PAIR: one panel per sense, both off the '
             'same starting member'))
    print('  sigma %.0f = %.2f sigma_c, spacing %.0f nm, n %d, %d sites, '
          'sign period %.2f Lambda -- identical for all four'
          % (sigma, sigma / sc, sp * 1000, n0, n0 * n0,
             2 * sp * 1000 / LAM))
    print('')
    print('  %-4s%7s%9s%9s%9s%9s%9s   %-9s %s'
          % ('', 'start', 'cmd', 'ended', 'w(cmd)', 'excess', 'x2sd',
             'cleared', 'on target'))
    for k in order:
        wk = W[k]
        print('  %-4s%7.0f%9.0f%9.0f%9.3f%+9.3f%9.1f   %-9s %s'
              % (k, wk['dom0'], wk['cmd'], wk['dom'], wk['w_cmd'],
                 wk['excess'], wk['x2sd'],
                 'yes' if wk['excess'] > wk['threshold'] else 'no',
                 'YES' if abs((wk['dom'] - wk['cmd'] + 90) % 180 - 90) < 1e-6
                 else 'no -> %.0f' % wk['dom']))
    print('')
    print('  the two criteria are reported SEPARATELY on purpose: C54 exists')
    print('  because one print statement conflated them, and only the second')
    print('  one -- ending on the command -- is what patterning needs.')

    # ---- group by sense -------------------------------------------------
    def _ontgt(k):
        return abs((W[k]['dom'] - W[k]['cmd'] + 90) % 180 - 90) < 1e-6

    def _cleared(k):
        return W[k]['excess'] > W[k]['threshold']

    core_labels = list(order)
    grpA = [k for k in order if W[k]['sense'] > 0]
    grpB = [k for k in order if W[k]['sense'] < 0]
    grpA_all, grpB_all = grpA, grpB
    nA_t, nB_t = sum(_ontgt(k) for k in grpA), sum(_ontgt(k) for k in grpB)
    nA_c, nB_c = sum(_cleared(k) for k in grpA), sum(_cleared(k) for k in grpB)
    print('')
    print('  sense  panels          cleared   on target   mean w(cmd)')
    for lbl, gg in (('+60', grpA), ('-60', grpB)):
        if not gg:
            continue
        print('   %-5s %-15s %d of %d     %d of %d       %.3f'
              % (lbl, ','.join(gg), sum(_cleared(k) for k in gg), len(gg),
                 sum(_ontgt(k) for k in gg), len(gg),
                 float(np.mean([W[k]['w_cmd'] for k in gg]))))

    n_cl = sum(_cleared(k) for k in order)
    n_ot = sum(_ontgt(k) for k in order)
    # where did the ones that missed actually land?
    miss = [k for k in order if not _ontgt(k)]
    third = []
    for k in miss:
        oth = [t for t in triad
               if abs((t - W[k]['cmd'] + 90) % 180 - 90) > 1e-6
               and abs((t - W[k]['dom0'] + 90) % 180 - 90) > 1e-6]
        if oth and abs((W[k]['dom'] - oth[0] + 90) % 180 - 90) < 1e-6:
            third.append(k)
    res['readable'] = bool(n_cl > 0)
    res.update(design=DESIGN, n_cleared=int(n_cl), n_on_target=int(n_ot),
               on_target=[k for k in order if _ontgt(k)], missed=miss,
               went_third=third, senseA=grpA, senseB=grpB, core=core_labels,
               senseA_all=grpA_all, senseB_all=grpB_all,
               zoom_frames=ZFR, angle_ctrl=dict(tag=a90, streak0=float(_s0),
                                                streak90=float(_s90),
                                                triad90=(None if _t90 is None
                                                         else [float(t) for t
                                                               in _t90])))

    # ---- the pre-registered branches, in the order they were declared ----
    if n_cl == 0:
        print('')
        print('  -> VOID, not negative. Not one panel cleared the')
        print('     leave-one-out null, so there is no positive control in')
        print('     this frame and no panel can be read against anything.')
        print('     The control failed too, therefore this says NOTHING about')
        print('     reachability. Check the gates, the meter log and the VDART.')
        print('     Do NOT record a pathway result from this iteration.')
        st['strikes'] = st.get('strikes', 0) + 1
    elif len(third) == len(order):
        print('')
        print('  -> EVERY PANEL WENT TO THE THIRD MEMBER (%d of %d). The'
              % (len(third), len(order)))
        print('     film passes')
        print('     THROUGH the third member and %.2f sigma_c does not' % (sigma / sc))
        print('     complete the transition. C54 is then an unfinished')
        print('     transition rather than a failure, and the fix is DOSE, not')
        print('     a different command. This promotes the incremental-dose')
        print('     iteration ahead of everything else: write in steps of')
        print('     0.3 sigma_c and watch where the population goes.')
        st['strikes'] = 0
    elif nA_t != nB_t and min(nA_t, nB_t) == 0:
        win, lose = (('+60', grpA), ('-60', grpB)) if nA_t else \
                    (('-60', grpB), ('+60', grpA))
        sink = sorted({int(round(W[k]['dom'])) for k in lose[1]})
        print('')
        print('  -> A SINK. Sense %s reached its target %d of %d times;'
              % (win[0], max(nA_t, nB_t), len(win[1])))
        print('     sense %s reached it 0 of %d, and its panels ended on %s.'
              % (lose[0], len(lose[1]), ', '.join('%d deg' % d for d in sink)))
        print('     Both senses had the SAME start, the SAME sigma, spacing,')
        print('     density and geometry, so the asymmetry is the transition')
        print('     itself. That is the answer to Q31 and the ceiling on')
        print('     patterning fidelity: %d of 4 panels obeyed the command.'
              % n_ot)
        print('     NEXT: repeat from a DIFFERENT starting member. If the sink')
        print('     follows the absolute direction it is the scan or lattice')
        print('     geometry; if it follows the rotation sense it is the film.')
        st['strikes'] = 0
    elif False:   # no replicate in a matched pair, so a stochastic
        pass      # transition cannot be identified; branch removed
    elif n_ot == len(order):
        print('')
        print('  -> SYMMETRIC. All %d panels ended on their command, both'
              % len(order))
        print('     senses, at %.2f sigma_c. Fidelity is not' % (sigma / sc))
        print('     direction-limited here, so C54 was either a fluke or')
        print('     specific to its area. The transition matrix is complete')
        print('     for this starting member: both neighbours reachable.')
        print('     NEXT: the limitation is elsewhere -- leftovers, dose floor')
        print('     and size -- not in which pathway is allowed.')
        st['strikes'] = 0
    else:
        print('')
        print('  -> MIXED: %d of %d cleared the null, %d of %d ended on the'
              % (n_cl, len(order), n_ot, len(order)))
        print('     command. %s went to the third member.'
              % (', '.join(third) if third else 'None'))
        print('     Report both criteria per panel rather than a single')
        print('     headline; the design does not resolve this pattern into')
        print('     one of the pre-registered cases, and saying so is the')
        print('     honest outcome.')
        st['strikes'] = 0

    # ---- the leftover question, measured while we are here --------------
    # Question 2 asks about residual population along the ORIGINAL director.
    # It costs nothing to report it now, and it sets the target for the next
    # iteration rather than waiting for it.
    print('')
    print('  leftovers along the ORIGINAL director (question 2s target):')
    print('  %-4s%12s%12s%12s   %s'
          % ('', 'w(start) b', 'w(start) a', 'change', 'reading'))
    lo = {}
    for p in panels:
        s0 = ds(F_REF, p['cx'], p['cy'], WIN, triad, p['dom0'])
        s1 = ds(a1, p['cx'], p['cy'], WIN, triad, p['dom0'])
        if not (s0 and s1):
            continue
        lo[p['label']] = dict(w0=float(s0['w_cmd']), w1=float(s1['w_cmd']),
                              d=float(s1['w_cmd'] - s0['w_cmd']))
        print('  %-4s%12.3f%12.3f%+12.3f   %s'
              % (p['label'], s0['w_cmd'], s1['w_cmd'],
                 s1['w_cmd'] - s0['w_cmd'],
                 'original still present' if s1['w_cmd'] > 0.25 else
                 'original largely cleared'))
    res['leftover'] = lo
    if lo:
        _mean_left = float(np.mean([v['w1'] for v in lo.values()]))
        print('  mean residual population along the original director: %.3f'
              % _mean_left)
        print('  -> a perfect rewrite would drive this to ~0.17 (an equal')
        print('     three-way split is 0.333; the depleted member should go')
        print('     BELOW that). %s'
              % ('There is real leftover to remove.' if _mean_left > 0.25
                 else 'Little leftover remains to remove.'))
        res['leftover_mean'] = _mean_left

    # ---- zoom frames, for the nano-domain analysis ----------------------
    print('')
    print('  zoom frames written this iteration (nano-domain scale):')
    for kk in sorted(ZFR):
        print('    %-14s %s' % (kk, ZFR[kk]))
    print('  these are scored OFFLINE: registered by Height cross-correlation')
    print('  and read with FFT sq_power over >= 4 Lambda windows. The')
    print('  real-space ORIENTATION metric is not used - Q6 records it')
    print('  disagreeing by 2-10x and saturating at 0.000/1.000 in small boxes.')


    st['iteration'] = st.get('iteration', 0) + 1
    if PROP['name'] not in st['completed']:
        st['completed'].append(PROP['name'])   # S26 can only bite if this is set
    # the area and the write minutes were committed before the readout; do not
    # add them twice
    st['history'] = st.get('history', []) + [dict(
        name=PROP['name'], when=time.strftime('%Y-%m-%d %H:%M'),
        offset=[XOFF, YOFF], lam=LAM, triad=triad, mod=chosen['mod'],
        frames=dict(b1=b1, b2=b2, b3=b3, ref=F_REF, after=a1, after2=a2,
                    vdart=vf, angle90=a90, **ZFR),
        design=DESIGN, senses={p['label']: int(p['sense'])
                               for p in panels},
        commands={p['label']: float(p['cmd']) for p in panels},
        sigma=sigma, dwell=dwell, result=res, write_min=wr)]
    note = A.refine_sigma_c(st, res)
    if note:
        print('\n  ' + note)
    A.save_state(st)
    return panels, res, wr


PROP = dict(
    name='IT11_RW1Z_pathway_map',
    hypothesis=(
        'C54 found two panels at the same sigma, spacing and geometry, each '
        'commanded 60 deg from its own dominant: one started at 4 deg, was '
        'commanded to 64 and ended on 64; the other started at 64, was '
        'commanded to 4, cleared the null at 3.4x and ended on 124. So '
        'clearing the threshold and ending on the command are SEPARABLE '
        'outcomes, and only the second is what patterning needs - which is why '
        'C51s letters read 63 % on target rather than 100 %. C54 rests on one '
        'panel per condition and cannot say whether the loser is a DIRECTION '
        '(something about 4 deg, the member nearest the fast scan axis) or a '
        'HISTORY (something about starting on 64 deg).'),
    prediction=(
        'TWO panels identical in sigma (1.29 sigma_c), spacing (Lambda/2), '
        'density (100 %), n (16), footprint and starting member, differing '
        'ONLY in which neighbour is commanded. Four slots are settled and two '
        'are written; the other two stay unwritten and carry control tiles. '
        'This is C54s comparison with its confound removed: C54s two panels '
        'started from DIFFERENT members, so direction and history could not be '
        'separated, while these share a start and a difference between them is '
        'the rotation sense and nothing else. Both criteria - excess above the '
        'leave-one-out null (C45) and dominant ENDING on the command - are '
        'reported separately for each panel, because C54 exists precisely '
        'because one print statement conflated them.'),
    outcomes={
        'both senses end on their command':
            'the transition is symmetric from this member; C54 was a fluke or '
            'area-specific, and fidelity is not direction-limited here. The '
            'limitation then lies in leftovers, dose floor and size rather '
            'than in which pathway is allowed',
        'one sense misses its target while still clearing the threshold':
            'a sink. Report which member absorbs, then repeat from a DIFFERENT '
            'starting member: if the sink follows the absolute direction it is '
            'the scan or lattice geometry, if it follows the rotation sense it '
            'is the film. With one panel per sense this is a candidate sink, '
            'not an established one - the replicate that would separate '
            'forbidden from stochastic does not fit the frame',
        'both land on the third member':
            'the film passes THROUGH the third member and 1.29 sigma_c does '
            'not complete the transition. C54 becomes an unfinished '
            'transition rather than a failure, and the fix is dose. This '
            'promotes the incremental-dose iteration ahead of everything else',
        'nothing clears the leave-one-out null':
            'VOID, not negative - the control failed too, so the iteration '
            'says nothing about reachability. Check the gates and interpret '
            'no panel. This is the branch that fired for real on IT4 and is '
            'the only reason a null was not written up as physics'},
    caveat=(
        'TWO panels, not four. The offline simulation on real frames measured '
        'halo 2.45 um at Lambda 354 nm, where four panels on a 2x2 grid at '
        'pitch 5.0 um cover the frame so completely that ZERO of 49 grid tiles '
        'clear every panel - so the C45 leave-one-out null had no sample and '
        'the primary metric did not exist (PITFALLS 2.4, 19.3). Two panels '
        'leave 13 tiles, verified on real frames. What that costs, stated '
        'plainly: no replicate per sense, so a stochastic transition cannot be '
        'distinguished from a forbidden one, and that branch was removed from '
        'the pre-registration rather than left in. '
        'Only four slots fit a 12 um frame at the worst command angle: RW1-Z '
        'commands both neighbours, the two are 120 deg apart, and one of them '
        'always carries ANGF >= 1.337, at which a 3x2 grid does not fit '
        '(reproduced from IT5 numbers with the real geom()). Growing the frame '
        'at 256 px makes it worse, because WIN is floored at 26 px and pushes '
        'n from 16 to 32. So there is no slot-selection freedom and the '
        'matching must come from the area, which is why the design is chosen '
        'by rule from the baseline. New in the machinery: deterministic '
        'worst-angle placement instead of a fixed point; both senses computed '
        'per slot; 5 um zooms on one panel per sense, which are '
        'self-referencing because a 5 um frame around a 2.4 um panel leaves a '
        '1.3 um untreated annulus; zoomed-versus-unzoomed as a free control on '
        'whether the readout perturbs the state; and a 90 deg scan-angle '
        'control, which tests the streak artefact but CANNOT give the in-plane '
        'polarisation sense - the cantilever torsional axis is fixed in the '
        'lab, so the observable stays a stripe orientation mod 180 deg and '
        'only vector PFM with the SAMPLE rotated would settle it.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
    reuse_areas=[],
    panels=[dict(label=l, keep=1.0, dwell=None, sign_every=1,
                 ratio=SIG_RATIO, spacing_div=2.0)
            for (l, _s, _w) in SPEC[:NWRITE]])


try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(PROP, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT11 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT11 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it11_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
