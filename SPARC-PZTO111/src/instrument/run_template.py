# -*- coding: utf-8 -*-
"""run_template.py -- write two templates in one frame and read the IP director.

ONE driver for the whole selection programme, because the measurement must be
identical across experiments for the comparison to mean anything:

    EXP=select   two PARALLEL lattices, lines along two DIFFERENT triad
                 members. Selection predicts each panel ends on ITS OWN
                 member; pure drive predicts both end on the same one.
                 This is the decisive test.

    EXP=cross60  two CROSSED panels, red along member A and blue along member
                 B (60 deg apart, both allowed directors), against a crossing
                 that maps onto no triad pair. Competition: the film is offered
                 two commensurate directors at once.

    EXP=cross90  crossings of 90 and 30 deg -- neither maps onto the triad.

    EXP=control  a solid +/- pair, no periodicity. Reproduces M13/M14 at this
                 area and fixes the member that pure drive picks.

WHAT IS MEASURED. LDART before and after, same area, same tune procedure.
Populations over the pinned triad in six size-matched 1.4 um windows: the two
panels and four untouched controls at the same x. Each panel's change is
differenced against the mean control change, so drift and any frame-to-frame
tune difference cancel (C42). The null is the largest deviation any single
control shows from the control mean -- measured, not assumed.

WHAT THIS DRIVER DOES NOT DO. It does not touch campaign_state.json, and it is
not an autoloop iteration; it is a focused instrument for one question. Write
minutes are reported so they can be added to the ledger by hand.

  AREA_X, AREA_Y   offset, um            SIGMA   areal dose, V.s/um^2
  EXP              which experiment      DRY=1   build and gate, do not write
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
# Panel size and placement are overridable so the crosstalk hypothesis (M21)
# can be tested by widening the gap between panels without changing anything
# else about the measurement.
HALF = float(os.environ.get('PANEL_HALF', '0.70'))     # 1.4 um panels
_SEP = float(os.environ.get('PANEL_SEP', '2.0'))       # centre-to-centre, um
_CX0, _CX1 = 2.5 - _SEP / 2.0, 2.5 + _SEP / 2.0
PC = ((_CX0, 2.5), (_CX1, 2.5))
CC = ((_CX0, 0.85), (_CX1, 0.85), (_CX0, 4.15), (_CX1, 4.15))
MAX_MIN = 26.0                    # S-envelope per-iteration write cap
CHG_MAX = 0.5 * 40.0              # C21 half-limit, V.s per site

XOFF = float(os.environ.get('AREA_X', '8.0'))
YOFF = float(os.environ.get('AREA_Y', '0.0'))
SIGMA = float(os.environ.get('SIGMA', '667'))
EXP = os.environ.get('EXP', 'select').strip()
DRY = os.environ.get('DRY', '') not in ('', '0')
STAMP = time.strftime('%y%m%d_%H%M')
RESULTS_CSV = os.path.join(HERE, 'results_templates.csv')


def spec_for(exp, triad, dom):
    """Panel specs from the MEASURED triad and the film's current dominant.

    `triad` ascending, `dom` the dominant director in the before-frame.
    """
    mem = [float(t) for t in triad]
    # the two members the film is NOT currently on: a panel whose template
    # favours the incumbent director predicts "no change" under every
    # hypothesis, so it carries no information
    away = sorted(mem, key=lambda t: -abs((t - dom + 90) % 180 - 90))[:2]
    away.sort()
    m0 = mem[0]

    if exp == 'select':
        return [dict(kind='parallel', ang=away[0], want=away[0],
                     note='lines along %.0f deg -> Q favours director %.0f'
                          % (away[0], away[0])),
                dict(kind='parallel', ang=away[1], want=away[1],
                     note='lines along %.0f deg -> Q favours director %.0f'
                          % (away[1], away[1]))]

    if exp == 'shear':
        a = away[0]
        return [dict(kind='sheared', ang=a, theta=90.0, want=a,
                     note='SQUARE lattice (chains at 90 deg), lines along %.0f'
                          % a),
                dict(kind='sheared', ang=a, theta=60.0, want=a,
                     note='TRIANGULAR lattice (chains at 60/120), same lines '
                          'along %.0f, same Q' % a)]

    if exp == 'shear75':
        a = away[0]
        return [dict(kind='sheared', ang=a, theta=75.0, want=a,
                     note='oblique 75 deg, lines along %.0f' % a),
                dict(kind='sheared', ang=a, theta=60.0, want=a,
                     note='triangular 60 deg, lines along %.0f' % a)]

    if exp == 'control':
        return [dict(kind='solid', ang=0.0, want=None,
                     note='solid +/- pair, no periodicity: DRIVE only'),
                dict(kind='parallel', ang=away[0], want=away[0],
                     note='parallel along %.0f at the same dose: drive + '
                          'selection' % away[0])]

    if exp.startswith('dose'):
        # two doses, same template, same frame, same controls -- the cleanest
        # way to add points to the M15 threshold curve
        lo, hi = {'dose1': (400.0, 530.0),
                  'dose2': (530.0, 800.0),
                  'dose3': (300.0, 470.0),
                  # below the solid square's 400-667 threshold (M15): where
                  # does the COMMENSURATE lattice stop working?
                  'dose4': (150.0, 220.0),
                  'dose5': (75.0, 110.0),
                  'dose6': (40.0, 60.0),
                  # near the floor: one pulse per site is the minimum
                  # quantum, ~17 V.s/um^2 for a 1.4 um panel at 150 nm
                  'dose7': (20.0, 30.0)}.get(exp, (400.0, 667.0))
        a = away[0]
        return [dict(kind='parallel', ang=a, want=a, sigma=lo,
                     note='lines along %.0f at sigma %.0f' % (a, lo)),
                dict(kind='parallel', ang=a, want=a, sigma=hi,
                     note='lines along %.0f at sigma %.0f' % (a, hi))]

    if exp == 'cross':
        return [dict(kind='crossed', ang_red=mem[0], ang_blue=mem[1],
                     want=mem[0],
                     note='crossed families 60 deg apart, both allowed'),
                dict(kind='crossed', ang_red=mem[0],
                     ang_blue=(mem[0] + 90.0) % 180.0, want=mem[0],
                     note='crossed 90 deg, blue matches no triad member')]

    raise SystemExit('unknown EXP=%r' % exp)


def windows():
    out = []
    for i, (cx, cy) in enumerate(PC):
        out.append(('P%d' % (i + 1), cx, cy))
    for i, (cx, cy) in enumerate(CC):
        out.append(('ctrl%d' % (i + 1), cx, cy))
    return out


def analyse(tag, g):
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    amp = np.abs(np.asarray(d[1], float))
    L = float(h['ScanSize']) * 1e6
    px = L / S.shape[0] * 1000.0          # from THIS header (19.11)
    tri, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
    out = {}
    n = S.shape[0]
    # A SQUARE crop, by construction. Rounding cx +- HALF and cy +- HALF
    # independently gave a (71,72) window, and ospec() broadcasts a square
    # window against the crop, so a one-pixel mismatch raises. Take an integer
    # half-width in pixels and use the same span on both axes.
    hp = int(round(HALF * 1000.0 / px))
    for lab, cx, cy in windows():
        ci = int(round(cx * 1000.0 / px))
        cj = int(round(cy * 1000.0 / px))
        j0 = max(0, min(n - 2 * hp, cj - hp))
        i0 = max(0, min(n - 2 * hp, ci - hp))
        sl = (slice(j0, j0 + 2 * hp), slice(i0, i0 + 2 * hp))
        assert S[sl].shape[0] == S[sl].shape[1], \
            '%s window %s is not square' % (lab, S[sl].shape)
        p = g('pops')(S[sl], px)
        w = np.asarray(p[0], float)
        out[lab] = dict(w=w / w.sum(), dom=float(p[2]),
                        amp=1e12 * float(np.nanmean(amp[sl])))
    return out, [float(t) for t in tri], float(tt['mod']), px




def csv_row(**kw):
    """One row per panel. Header written once, on first use."""
    cols = ['stamp', 'exp', 'mode', 'area_x', 'area_y', 'lam_nm', 'triad',
            'panel', 'kind', 'ang', 'theta', 'sigma', 'n_sites', 'q_site',
            'w0_0', 'w0_1', 'w0_2', 'w1_0', 'w1_1', 'w1_2',
            'dom_before', 'dom_after', 'want', 'excess', 'null', 'x_null',
            'cleared', 'amp_before', 'amp_after', 'mod_before', 'mod_after']
    new = not os.path.exists(RESULTS_CSV)
    with io.open(RESULTS_CSV, 'a', encoding='utf-8', newline='') as fh:
        if new:
            fh.write(','.join(cols) + '\n')
        fh.write(','.join(str(kw.get(c, '')) for c in cols) + '\n')


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
    print('TEMPLATE RUN  EXP=%s  %s' % (EXP, time.strftime('%Y-%m-%d %H:%M')))
    print('=' * 74)
    print('  EXP choices: control | select | shear | shear75 | cross | dose1..3')
    print('  area (%+.1f,%+.1f), %.0f um frame, target sigma %.0f V.s/um^2'
          % (XOFF, YOFF, SIZE_UM, SIGMA))
    print('  panels %.1f um at %s' % (2 * HALF, list(PC)))
    print('  %s' % ('DRY RUN: build and gate only, nothing written'
                    if DRY else 'this WILL write to the sample'))

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()
    if os.path.exists(A.STOP):
        raise SystemExit('STOP file present')

    # ---- deflection, reported not gated (19.10) -------------------------
    try:
        live = float(ns['exp'].read_meter()[1])
        print('\n  live deflection %+.3f V  (withdrawn band -0.75..-0.20; '
              'if engaged this is the setpoint being held)' % live)
    except Exception as e:
        print('  meter unreadable: %s' % e)

    # ---- BEFORE ---------------------------------------------------------
    print('\n--- LDART before ---')
    _c, inf = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                             angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                             tries=1, verbose=False)
    before = inf['frame']
    print('    %s (tune %.1f kHz)' % (before, _c / 1000.0))
    g('contact_check')(before)
    rb, triad, mod, px_nm = analyse(before, g)
    print('    triad %s, modulation %.3f, %.2f nm/px'
          % ([int(round(t)) for t in triad], mod, px_nm))

    # Lambda from THIS frame, per triad member
    d, h = g('ibw')(before)
    S, _, _ = g('signed')(d)
    lam = []
    for f_ in triad:
        v = g('period')(S, px_nm, f_)
        lam.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                   else float(v))
    lam = [x for x in lam if x == x]
    LAM = float(np.median(lam)) / 1000.0
    print('    Lambda %s -> median %.0f nm  (sp = %.0f nm)'
          % (['%.0f' % x for x in lam], LAM * 1000, LAM * 500))
    if not (0.148 <= LAM <= 0.420):
        raise SystemExit('Lambda %.0f nm outside the buildable window' % (LAM * 1000))
    # The READOUT window must hold >= 4 periods or the per-window dominant is
    # not a measurement. This is a different condition from buildability and
    # it is the one that produced two fake sub-threshold points (19.15).
    _nper = (2 * HALF) / LAM
    print('    analysis window %.1f um = %.1f Lambda' % (2 * HALF, _nper))
    if _nper < 4.0:
        raise SystemExit(
            'window holds only %.1f Lambda (need >= 4) at Lambda %.0f nm: the '
            'per-window director would not be measurable here. Pick finer film '
            'or a larger window.' % (_nper, LAM * 1000))
    if _nper < 4.3:
        print('    !! marginal: %.1f Lambda. Directions from this area carry '
              'more scatter than usual.' % _nper)

    # ---- build ----------------------------------------------------------
    # The incumbent director, from the MEAN population over all four control
    # windows -- not from one window. A single 1.4 um window's dominant is
    # noisy: on the select run ctrl1 read 25 deg while ctrl2/3/4 read 80/65/90,
    # and taking ctrl1 alone made one panel target the member the film was
    # already on, which leaves that panel nothing to do under either hypothesis.
    _cw = np.mean([rb[l]['w'] for l in rb if l.startswith('ctrl')], axis=0)
    dom_before = float(triad[int(np.argmax(_cw))])
    print('    incumbent director %.0f deg (mean control populations %s)'
          % (dom_before, np.round(_cw, 3)))
    spec = spec_for(EXP, triad, dom_before)
    print('\n--- panels ---')
    tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    built = []
    for k, sp in enumerate(spec):
        centre = PC[k]
        # every builder kwarg must be listed here; 'theta' was missing
        # and got silently dropped, so sheared() raised KeyError at
        # build time. Derive the list from the spec instead of
        # whitelisting, so adding a template kind cannot repeat this.
        kw = {q: sp[q] for q in sp
              if q not in ('kind', 'note', 'want')}
        sites = T.build(sp['kind'], centre, HALF, LAM, V, **kw)
        if sp['kind'] == 'sheared':
            _a, _s, _d = T.oblique_basis(LAM, sp['theta'])
            print('     lattice basis %.0f nm, offset/line %.0f nm, '
                  'perp spacing %.0f nm' % (1000 * _a, 1000 * _s, 1000 * _d))
        # a spec may carry its own sigma, so a dose series can sit in
        # ONE frame against ONE set of controls
        sig_target = float(sp.get('sigma', SIGMA))
        # Per-site charge is sigma*area/(n*V); on coarse film n is small and
        # the C21 half-limit bites. A run at Lambda 354 nm aborted at
        # 20.4 V.s/site. Cap the dose rather than lose the area, and say so.
        _sig_max = CHG_MAX * len(sites) * V / ((2 * HALF) ** 2)
        if sig_target > _sig_max:
            print('     sigma %.0f would need %.1f V.s/site; capped to %.0f '
                  'by C21 (%d sites at Lambda %.0f nm)'
                  % (sig_target, sig_target * (2 * HALF) ** 2
                     / (len(sites) * V), _sig_max, len(sites), LAM * 1000))
            sig_target = _sig_max * 0.98
        dwell = T.dwell_for_sigma(sig_target, sites, V, HALF)
        pn = max(1, int(round(dwell * SPEED / STEP)))
        dwell = pn * STEP / SPEED
        sig, q_site = T.dose(sites, V, dwell, HALF)
        print('  P%d %-8s %s' % (k + 1, sp['kind'], sp['note']))
        print('     %d sites, %d pulses/site, dwell %.2f s, sigma %.0f, '
              '%.1f V.s per site' % (len(sites), pn, dwell, sig, q_site))
        if q_site > CHG_MAX:
            raise SystemExit('P%d per-site charge %.1f V.s over the %.0f limit'
                             % (k + 1, q_site, CHG_MAX))
        vv = np.array([s[2] for s in sites])
        assert abs(vv.mean()) < 1e-9, 'P%d net DC' % (k + 1)
        assert np.abs(vv).max() <= 10.0 + 1e-9, 'P%d |V|' % (k + 1)
        for (x0, y0, v0) in sites:
            tb.dwell((x0, y0), v0, n=pn)
        built.append(dict(spec=sp, n=len(sites), pn=pn, sigma=sig, q=q_site,
                          centre=centre))

    xs, ys, vs = (np.asarray(a, float) for a in tb.to_arrays())
    npts = len(xs)
    # Time comes from the POINT COUNT, not path_length_um(). The path length
    # counts only the geometric extent of the strokes; run_traj also traverses
    # between sites, and travel is additive rather than a fixed multiplier. On
    # the first control run path_length gave 35.5 um -> 1.2 min while the
    # instrument actually took 180 um -> 6.0 min, a 5x under-estimate. Gating
    # the 26 min cap on that number would have let a long panel through.
    mins = npts * STEP / SPEED / 60.0
    mins_geom = tb.path_length_um() / SPEED / 60.0
    print('\n--- built path ---')
    print('  %d pts -> %.1f min of writing at %.2f um/s (cap %.0f)'
          % (npts, mins, SPEED, MAX_MIN))
    print('  stroke length %.1f um (%.1f min); the rest is travel between sites'
          % (tb.path_length_um(), mins_geom))
    print('  |V|max %.1f, mean %+.2e, %.0f%% at 0 V'
          % (np.abs(vs).max(), vs.mean(), 100 * np.mean(np.isclose(vs, 0))))
    print('  x %.2f-%.2f, y %.2f-%.2f um' % (xs.min(), xs.max(),
                                             ys.min(), ys.max()))
    # gate on the BUILT path, never on an estimate
    if mins > MAX_MIN:
        raise SystemExit('path %.1f min over the %.0f min cap' % (mins, MAX_MIN))
    if not (xs.min() >= 0 and ys.min() >= 0
            and xs.max() <= SIZE_UM and ys.max() <= SIZE_UM):
        raise SystemExit('path leaves the frame')
    if abs(vs.mean()) > 1e-6:
        raise SystemExit('path carries net DC %.3e' % vs.mean())
    if DRY:
        print('\nDRY RUN: gates pass, nothing written.')
        return

    # ---- write ----------------------------------------------------------
    budget_check(mins, 'TPL_%s' % EXP)
    print('\n--- writing ---')
    fn = os.path.join(A.PROJ, 'output', '%s_TPL_%s.txt' % (STAMP, EXP))
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)

    # ---- AFTER ----------------------------------------------------------
    print('\n--- LDART after ---')
    _c2, inf2 = g('tune_here')('ldart', size_um=SIZE_UM, px=PX, rate=RATE,
                               angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                               tries=1, verbose=False)
    after = inf2['frame']
    print('    %s (tune %.1f kHz)' % (after, _c2 / 1000.0))
    g('contact_check')(after)
    ra, triad_a, mod_a, _ = analyse(after, g)

    # ---- verdict --------------------------------------------------------
    print('\n' + '=' * 74)
    print('RESULT  EXP=%s   sigma %.0f' % (EXP, SIGMA))
    print('=' * 74)
    print('  triad before %s (mod %.3f) | after %s (mod %.3f)'
          % ([int(round(t)) for t in triad], mod,
             [int(round(t)) for t in triad_a], mod_a))
    print('\n  %-7s %-22s %-22s %9s %9s'
          % ('window', 'w before', 'w after', 'dom b->a', 'lat |A|'))
    for lab, _cx, _cy in windows():
        b, a_ = rb[lab], ra[lab]
        print('  %-7s %-22s %-22s  %3.0f->%3.0f  %5.1f->%5.1f'
              % (lab, np.round(b['w'], 3), np.round(a_['w'], 3),
                 b['dom'], a_['dom'], b['amp'], a_['amp']))

    ck = [l for l in rb if l.startswith('ctrl')]
    dC = np.mean([ra[l]['w'] - rb[l]['w'] for l in ck], axis=0)
    null = float(np.max([np.max(np.abs((ra[l]['w'] - rb[l]['w']) - dC))
                         for l in ck]))
    print('\n  control mean change %s | null %.3f' % (np.round(dC, 3), null))
    moved = []
    for k in range(len(spec)):
        lab = 'P%d' % (k + 1)
        ex = (ra[lab]['w'] - rb[lab]['w']) - dC
        m = float(np.max(np.abs(ex)))
        cleared = m > 2 * max(null, 1e-3)
        moved.append((lab, cleared, m, ra[lab]['dom'], built[k]))
        print('  %s excess %s  max %.3f = %.1fx null  -> %s'
              % (lab, np.round(ex, 3), m, m / max(null, 1e-9),
                 'CLEARS' if cleared else 'within null'))

    print('\n  --- what this says about SELECTION ---')
    # Do the two templates PREDICT the same destination or different ones?
    # Read it off the specs; assuming "different" turned the shear result --
    # a confirmation -- into a printed refutation.
    wants = [sp.get('want') for sp in spec]
    same_target = (len([w for w in wants if w is not None]) == 2
                   and abs((wants[0] - wants[1] + 90) % 180 - 90) < 10)
    if same_target:
        print('  NOTE: both panels carry the SAME template wavevector Q')
        print('  (%.0f deg). They differ in the real-space arrangement only,'
              % wants[0])
        print('  so selection predicts the SAME destination for both. Landing')
        print('  apart would be the surprising outcome here.')

    if not any(c for _l, c, _m, _d, _b in moved):
        print('  Neither panel cleared its own null. VOID, not negative: with')
        print('  no positive control in this frame nothing can be read against')
        print('  anything. Check |A| and r12 on both frames before believing')
        print('  any dose or geometry conclusion (M12).')
    else:
        doms = [d for _l, c, _m, d, _b in moved if c]
        if len(doms) == 2:
            sep = abs((doms[0] - doms[1] + 90) % 180 - 90)
            if same_target:
                if sep <= 20:
                    print('  Both panels reached %.0f/%.0f deg -- the SAME '
                          'member, as predicted.' % (doms[0], doms[1]))
                    print('  The real-space arrangement was changed and the')
                    print('  destination did not move, so selection is set by Q')
                    print('  and not by the point arrangement.')
                else:
                    # the format args belonged to the FIRST line, not the
                    # second; as written this branch raised TypeError -- and it
                    # is the branch that fires only when the result is
                    # surprising, i.e. exactly when a crash costs most
                    print('  The panels ended APART (%.0f and %.0f deg) despite'
                          % (doms[0], doms[1]))
                    print('  sharing a wavevector. That contradicts')
                    print('  selection-by-Q and points at the real-space')
                    print('  arrangement mattering after all.')
            else:
                if sep > 20:
                    print('  The two panels ended on DIFFERENT directors '
                          '(%.0f and %.0f deg, %.0f apart).'
                          % (doms[0], doms[1], sep))
                    print('  Same frame, same dose, same tip: the only')
                    print('  difference is the template. That is SELECTION.')
                else:
                    print('  Both panels ended on the SAME director (%.0f and '
                          '%.0f), despite' % (doms[0], doms[1]))
                    print('  carrying DIFFERENT wavevectors. Consistent with')
                    print('  DRIVE alone, the template not choosing anything.')
        else:
            print('  Only one panel cleared, so the comparison between')
            print('  templates cannot be made. Report it as one-sided.')
        for lab, c, m, dm, b in moved:
            s_ = b['spec']
            want = s_.get('ang', s_.get('ang_red'))
            extra = ''
            if s_.get('theta') is not None:
                extra = ', lattice angle %.0f deg' % s_['theta']
            print('    %s (%s%s) -> %.0f deg; its own template favours %.0f'
                  % (lab, s_['kind'], extra, dm, want))

    for k in range(len(spec)):
        lab = 'P%d' % (k + 1)
        sp = built[k]['spec']
        ex = (ra[lab]['w'] - rb[lab]['w']) - dC
        m = float(np.max(np.abs(ex)))
        csv_row(stamp=STAMP, exp=EXP, mode='', area_x=XOFF, area_y=YOFF,
                lam_nm=round(LAM * 1000, 1),
                triad='|'.join('%.0f' % t for t in triad),
                panel=lab, kind=sp['kind'],
                ang=sp.get('ang', sp.get('ang_red', '')),
                theta=sp.get('theta', ''), sigma=round(built[k]['sigma'], 0),
                n_sites=built[k]['n'], q_site=round(built[k]['q'], 2),
                w0_0=round(rb[lab]['w'][0], 4), w0_1=round(rb[lab]['w'][1], 4),
                w0_2=round(rb[lab]['w'][2], 4),
                w1_0=round(ra[lab]['w'][0], 4), w1_1=round(ra[lab]['w'][1], 4),
                w1_2=round(ra[lab]['w'][2], 4),
                dom_before=round(rb[lab]['dom'], 1),
                dom_after=round(ra[lab]['dom'], 1),
                want=sp.get('want', ''), excess=round(m, 4),
                null=round(null, 4), x_null=round(m / max(null, 1e-9), 2),
                cleared=int(m > 2 * max(null, 1e-3)),
                amp_before=round(rb[lab]['amp'], 1),
                amp_after=round(ra[lab]['amp'], 1),
                mod_before=round(mod, 4), mod_after=round(mod_a, 4))
    print('  -> appended %d rows to %s' % (len(spec),
                                           os.path.basename(RESULTS_CSV)))

    print('\n  write minutes %.2f  (charged to S24; this driver'
          % mins)
    print('  does not touch campaign_state.json)')


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
        io.open(os.path.join(A.PROJ, 'tpl_%s_%s.txt' % (EXP, STAMP)), 'w',
                encoding='utf-8').write(buf.getvalue())
