# -*- coding: utf-8 -*-
"""IT1 - the T3 factorial and the sigma_c prediction, autonomous.

Panels, all at spacing Lambda_local/2 except where noted:
  A  1.50 sigma_c, period Lambda, keep 1.00   positive control + reference
  B  1.50 sigma_c, period Lambda, keep 0.50   Q15  is sigma the drive variable?
  C  1.50 sigma_c, period 2 Lambda, keep 1.00 Q16  is commensuration required?
  D  0.70 sigma_c, period Lambda, keep 1.00   below threshold, negative control
  E  1.00 sigma_c, period Lambda, keep 1.00   the sigma_c prediction test
  G  unwritten in-grid control (same scan history as the panels)

sigma = (4 / Lambda_local^2) * keep * V * dwell, so holding sigma equal across
A/B/C while each keeps its OWN local Lambda for the spacing means solving DWELL
per panel. Lambda moved 10-15 % per 10 um across the areas written today, so a
frame-average would put the outlying panels off resonance - which for panel C is
the difference between testing commensuration and confounding it.
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
RATE = A.TIP_SPEED_MAX / (2.0 * FRAME)      # hold tip speed at 20 um/s
V = 10.0
STEP, SPEED = 0.02, 0.5
R_EFF = 0.625
XOFF, YOFF = 0.0, 0.0

# label, target sigma/sigma_c, on-resonance, keep, spacing_div
SPEC = [('A', 1.50, True, 1.00, 2.0, 'positive control and factorial reference'),
        ('B', 1.50, True, 0.50, 2.0, 'Q15 half the sites, same sigma'),
        ('C', 1.50, False, 1.00, 2.0, 'Q16 template period 2 Lambda, same sigma'),
        ('D', 0.70, True, 1.00, 2.0, 'below threshold, negative control'),
        ('E', 1.00, True, 1.00, 2.0, 'AT sigma_c: the prediction test')]

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
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT1  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    if os.path.exists(A.STOP):
        raise SystemExit('STOP file present - halting before any command')
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    for f in ('check_folder', 'scanner_ok', 'setup_scan', 'tune_here', 'frame',
              'pick_ref', 'frame_gate', 'pin_triad', 'command_for', 'dir_state',
              'streak_index', 'ctrl_tiles', 'lattice_panel', 'window_check',
              'run_traj', 'goto_ldart', 'goto_vdart', 'orbit_balance',
              'tracking_rows', 'contact_check', 'probe_fingerprint',
              'TrajectoryBuilder', 'ibw', 'signed', 'period', 'FAM_FILM'):
        if f not in ns:
            raise RuntimeError('toolkit lacks %s' % f)

    # ---------------------------------------------------- guards, no commands
    print('\n--- folder and range (before any instrument command) ---')
    g('check_folder')()
    g('scanner_ok')(XOFF, YOFF, FRAME)
    ok, notes = A.check_area_fresh(st, XOFF, YOFF, FRAME)
    if not ok:
        raise SystemExit('area not usable: %s' % notes)
    busy, age = A.instrument_is_busy(quiet_s=120)
    print('  newest frame %.0f min ago -> %s'
          % (age / 60.0, 'BUSY' if busy else 'idle'))
    if busy:
        raise SystemExit('a frame landed in the last 2 min - something else is '
                         'running')

    # ---------------------------------------------------- tune and baselines
    print('\n--- tune, verified on a full-resolution frame at this offset ---')
    print('  %.0f um at %.2f Hz = %.0f um/s tip speed, %.1f min per frame'
          % (FRAME, RATE, 2 * FRAME * RATE, PX / RATE / 60.0))
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    centre, tv = g('tune_here')('ldart', size_um=FRAME, px=PX, rate=RATE,
                                xoff_um=XOFF, yoff_um=YOFF)
    b1 = tv['frame']
    print('  LDART centre %.0f kHz, %.0f%% tracked; %s is baseline 1'
          % (centre / 1e3, 100 * tv['frac'], b1))
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0)
    g('goto_ldart')()
    b2 = g('frame')()
    b3 = g('frame')()
    g('contact_check')(b3)
    g('probe_fingerprint')(b3, note='IT1 reference, sample position 2')

    print('\n--- reference frame: r12 gate, then coverage, over three ---')
    F_REF, rr = g('pick_ref')([b1, b2, b3],
                              [(0.4, FRAME - 0.4, 0.4, FRAME - 0.4)])
    OTHER = [t for t in (b1, b2, b3) if t != F_REF] or [F_REF]
    g('frame_gate')(F_REF, ref_tags=tuple(OTHER))

    print('\n--- streak screen on untouched film (C36) ---')
    sk = {}
    for t in (b1, b2, b3):
        sk[t] = g('streak_index')(t, (0.35, FRAME - 0.35, 0.35, 1.7))
    if sk[F_REF] > A.STREAK_MAX:
        raise SystemExit('the reference frame is streaky (%.3f > %.2f) - it '
                         'would read excess population near 0 deg. Retake.'
                         % (sk[F_REF], A.STREAK_MAX))

    # ---------------------------------------------------- triad and Lambda
    triad, tt = g('pin_triad')(F_REF, ref_fam=g('FAM_FILM'))
    triad = [float(x) for x in triad]
    if tt['mod'] < A.MOD_MIN:
        raise SystemExit('modulation %.3f < %.2f - no triad texture here to '
                         'rotate. Move.' % (tt['mod'], A.MOD_MIN))
    PX_NM = FRAME / PX * 1000.0
    d, h = g('ibw')(F_REF)
    S, _, _ = g('signed')(d)
    lam_all = []
    for f in triad:
        v = g('period')(S, PX_NM, f)
        v = float(v[0]) if isinstance(v, (tuple, list, np.ndarray)) else float(v)
        lam_all.append(v)
    LAM = float(np.nanmedian(lam_all))
    print('  triad %s  modulation %.3f  frame-median Lambda %.0f nm'
          % (['%.0f' % x for x in triad], tt['mod'], LAM))

    # ---------------------------------------------------- plan and place
    WIN = float(max(4.2 * LAM / 1000.0, 26 * PX_NM / 1000.0))
    g('window_check')(WIN, PX_NM, LAM, name='readout window')
    ANGF = {t: abs(np.cos(np.deg2rad(t))) + abs(np.sin(np.deg2rad(t)))
            for t in triad}
    print('  extent factor by director: '
          + '  '.join('%.0f deg %.3f' % (t, ANGF[t]) for t in triad))
    sp0 = LAM / 2000.0

    def geom(ang):
        need = WIN * ang + 2 * (sp0 + 0.10)
        n = int(max(8, 4 * round((need / sp0 + 1) / 4.0)))
        while (n - 1) * sp0 < need and n < 128:
            n += 4
        halo = (n - 1) * sp0 * ang / 2 + R_EFF
        return n, halo, 2 * halo + 0.10

    def place(pitch, halo, ncol=3, nrow=2):
        xs = [FRAME / 2 + (j - (ncol - 1) / 2.0) * pitch for j in range(ncol)]
        y0 = 0.35 + WIN + 0.05 + halo
        return [(xs[j], y0 + i * pitch) for i in range(nrow) for j in range(ncol)]

    def fits(slots, halo):
        return all(cx - halo >= 0.05 and cx + halo <= FRAME - 0.05
                   and cy - halo >= 0.05 and cy + halo <= FRAME - 0.05
                   for (cx, cy) in slots)

    # Fixed point: provisional placement on the CHEAPEST director, read the
    # commands it implies, re-size on those, repeat until the angle set stops
    # growing. The worst-angle envelope inflates the pitch by up to 1.31x here
    # and made a 3x2 grid impossible when the commands actually in use fit it.
    print("\n--- placement as a fixed point over the commands ---")
    print('    the command is chosen per panel, so the extent factor is not')
    print('    known until the placement is chosen. Start on the cheapest')
    print('    director, read what the commands would be, re-size on those,')
    print('    repeat. Fall back to a smaller grid if it will not settle.')
    settled = None
    for (ncol, nrow, nwrite) in ((3, 2, 5), (2, 2, 4)):
        ang_use = min(ANGF.values())
        for it in range(4):
            n0, halo, pitch = geom(ang_use)
            slots = place(pitch, halo, ncol, nrow)
            if not fits(slots, halo):
                print('    %dx%d factor %.3f -> halo %.2f pitch %.2f: does '
                      'NOT fit' % (ncol, nrow, ang_use, halo, pitch))
                break
            cmds = []
            for (cx, cy) in slots[:nwrite]:
                best = None
                for sense in (+1, -1):
                    cf = g('command_for')(F_REF, cx, cy, WIN, triad,
                                          sense=sense, min_lead=0.05,
                                          verbose=False)
                    if cf is None:
                        continue
                    if best is None or ANGF[cf['cmd']] < ANGF[best['cmd']]:
                        best = cf
                if best is None:
                    raise SystemExit('slot (%.2f,%.2f) is not measurable'
                                     % (cx, cy))
                cmds.append(best)
            new_ang = max(ANGF[c['cmd']] for c in cmds)
            print('    %dx%d pass %d: factor %.3f, n %d, halo %.2f, pitch '
                  '%.2f, dominants %s -> commands %s -> need %.3f'
                  % (ncol, nrow, it + 1, ang_use, n0, halo, pitch,
                     [int(c['dom']) for c in cmds],
                     [int(c['cmd']) for c in cmds], new_ang))
            if new_ang <= ang_use + 1e-9:
                settled = (ncol, nrow, nwrite, ang_use, n0, halo, pitch,
                           slots, cmds)
                break
            ang_use = new_ang
        if settled:
            break
    if settled is None:
        raise SystemExit('no grid settles in a %.0f um frame at Lambda %.0f nm '
                         '- the texture is too mixed for a per-panel command '
                         'here. Move, or raise the frame.' % (FRAME, LAM))
    ncol, nrow, nwrite, ang_use, n0, halo, pitch, slots, cmds = settled
    ys = sorted(set(cy for (_, cy) in slots))
    print('  settled on a %dx%d grid: factor %.3f, n %d, halo %.2f um, pitch '
          '%.2f um' % (ncol, nrow, ang_use, n0, halo, pitch))
    print('  %d slots: ' % len(slots)
          + '  '.join('(%.2f,%.2f)' % t for t in slots))
    if nwrite < len(SPEC):
        dropped = [q[0] for q in SPEC[nwrite:]]
        print('  !! only %d written panels fit, so DROPPING %s.'
              % (nwrite, ', '.join(dropped)))
        print('     Priority kept: A/B/C are the factorial (Q15 and Q16) and D')
        print('     anchors the threshold. %s deserves its own cheap iteration'
              % ', '.join(dropped))
        print('     rather than compromising the factorial.')
    SPEC_USE = SPEC[:nwrite]
    plan = A.plan_iteration(LAM, len(slots), dwell_mean=0.9, ang=ang_use,
                            verbose=True)

    print('\n--- Lambda: is a per-panel value measurable here? ---')
    print('    per triad member on the full frame: %s nm'
          % '  '.join('%.0f' % v for v in lam_all))
    lam_loc, spread = A.lambda_uniformity(ns, F_REF, slots, max(WIN, 1.6), triad)
    memspread = ((max(lam_all) - min(lam_all)) / float(np.mean(lam_all))
                 if len(lam_all) > 1 else 0.0)
    print('    spread across triad members at FULL resolution: %.0f%%'
          % (100 * memspread))
    if spread > 0.20 or memspread > 0.20:
        print('    -> Lambda is NOT a single well-determined number here. The')
        print('       local estimate does not converge with block size, which')
        print('       is an estimator artefact rather than real variation, so')
        print('       every panel uses the frame median %.0f nm.' % LAM)
        print('       Consequence: sigma is unaffected (it uses the spacing we')
        print('       COMMAND, which is exact), but "period = Lambda" is only')
        print('       defined to about +-30 %. The Lambda vs 2 Lambda contrast')
        print('       in panel C survives; a fine detuning would not.')
        lam_loc = np.array([LAM] * len(slots), dtype=float)
        LAM_PER_PANEL = False
    else:
        print('    -> local values are consistent; using them per panel.')
        for i, v in enumerate(lam_loc):
            if not np.isfinite(v):
                lam_loc[i] = LAM
        LAM_PER_PANEL = True

    # ---------------------------------------------------- commands and doses
    print('\n--- command per panel, 60 deg from ITS OWN dominant director ---')
    panels = []
    for k, (lab, ratio, onres, keep, div, what) in enumerate(SPEC_USE):
        cx, cy = slots[k]
        cands = []
        for sense in (+1, -1):
            cf = g('command_for')(F_REF, cx, cy, WIN, triad, sense=sense,
                                  min_lead=0.05, verbose=False)
            if cf is None:
                continue
            af = abs(np.cos(np.deg2rad(cf['cmd']))) + abs(np.sin(np.deg2rad(cf['cmd'])))
            cands.append((af, sense, cf))
        if not cands:
            raise SystemExit('slot %s is not measurable' % lab)
        cands.sort(key=lambda z: z[0])
        af, sense, cf = cands[0]
        if cf['lead_dom'] < 0.05:
            raise SystemExit('slot %s has no clear dominant director (leads by '
                             '%.3f)' % (lab, cf['lead_dom']))
        lam_i = float(lam_loc[k])
        sp = (lam_i / 1000.0) / div
        se = int(div / 2.0) if onres else int(div)
        # dwell solved so sigma hits the target given THIS panel's Lambda
        want = ratio * sc
        dw_raw = want / ((1.0 / sp ** 2) * keep * V)
        pn = max(1, int(round(dw_raw * SPEED / STEP)))
        dwell = pn * STEP / SPEED
        sig = (1.0 / sp ** 2) * keep * V * dwell
        per_pulse = V * dwell
        need_i = WIN * af + 2 * (sp + 0.10)
        n_i = int(max(8, 4 * round((need_i / sp + 1) / 4.0)))
        while (n_i - 1) * sp < need_i and n_i < 128:
            n_i += 4
        agree = all(g('dir_state')(t, cx, cy, WIN, triad)['dom'] == cf['dom']
                    for t in OTHER)
        panels.append(dict(label=lab, cx=cx, cy=cy, cmd=cf['cmd'],
                           dom0=cf['dom'], lead_dom=cf['lead_dom'], sense=sense,
                           keep=keep, dwell=dwell, pulse_n=pn, sign_every=se,
                           spacing_div=div, sp=sp, lam=lam_i, sigma=sig,
                           ratio=sig / sc, per_pulse=per_pulse, n=n_i,
                           on_resonance=onres, tests=what, agree=agree,
                           ref=F_REF))
        print('  %s  Lambda %3.0f nm  dom %3.0f -> cmd %3.0f  keep %3.0f%%  '
              'dwell %.2f s  sigma %5.0f (%.2f x)  %s'
              % (lab, lam_i, cf['dom'], cf['cmd'], 100 * keep, dwell, sig,
                 sig / sc, '3/3 agree' if agree else '!! BASELINES DISAGREE'))
        if per_pulse > 0.5 * A.CHG_1PULSE_MAX:
            print('     !! %.0f V.s per site, over half C21s %.0f - may switch '
                  'site-by-site' % (per_pulse, A.CHG_1PULSE_MAX))
        assert abs(abs((cf['cmd'] - cf['dom'] + 90) % 180 - 90) - 60.0) < 1.0

    fac = [p for p in panels if p['label'] in 'ABC']
    fs = [p['sigma'] for p in fac]
    print('  factorial sigma: %s  spread %.1f%%'
          % (['%.0f' % s for s in fs],
             100 * (max(fs) - min(fs)) / np.mean(fs)))
    if (max(fs) - min(fs)) / np.mean(fs) > 0.08:
        raise SystemExit('A/B/C sigma spread over 8%% - the factorial would not '
                         'be a one-factor comparison')

    # ---------------------------------------------------- build
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    tot = 0
    print('\n  %-3s%6s%8s%9s%9s%9s' % ('', 'n', 'sites', 'PULSE_N', 'dwell',
                                       'site s'))
    for p in panels:
        sites = g('lattice_panel')(p['n'], p['sp'], (p['cx'], p['cy']),
                                   p['cmd'], V, sign_every=p['sign_every'],
                                   keep_frac=p['keep'], rng=np.random.default_rng(1701))
        v = np.array([q[2] for q in sites])
        assert abs(v.mean()) < 1e-9, '%s carries net DC' % p['label']
        for (x0, y0, v0) in sites:
            tb.dwell((x0, y0), v0, n=p['pulse_n'])
        p['npulse'] = len(sites)
        tot += len(sites)
        print('  %-3s%6d%8d%9d%9.2f%9.1f'
              % (p['label'], p['n'], len(sites), p['pulse_n'], p['dwell'],
                 len(sites) * p['dwell'] / 60.0))
    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    dwm = sum(p['npulse'] * p['dwell'] for p in panels) / 60.0
    print('\n  %d pulses, %d pts, mean V %+.6f' % (tot, len(Vv), Vv.mean()))
    print('  %.1f min of dwell, %.1f min of writing (travel %.2fx)'
          % (dwm, wr, wr / max(dwm, 1e-9)))
    assert abs(Vv.mean()) < 1e-6 and np.abs(Vv).max() <= V + 1e-9
    assert X.min() > 0.05 and X.max() < FRAME - 0.05
    assert Y.min() > 0.05 and Y.max() < FRAME - 0.05
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('%.1f min of writing exceeds MAX_WRITE_MIN %.0f. The '
                         'factorial needs sigma well above threshold, which '
                         'costs dwell - shorten it, drop a ladder point, or '
                         'raise the cap deliberately. Do not overrun quietly.'
                         % (wr, A.MAX_WRITE_MIN))
    if os.path.exists(A.STOP):
        raise SystemExit('STOP appeared - halting before the write')

    # ---------------------------------------------------- write
    fn = os.path.join(A.PROJ, 'output', '260821_IT1_factorial.txt')
    print('\n--- writing (%.1f min) ---' % wr)
    g('goto_ldart')()
    # preview=False: a plot nobody sees is pointless headless, and it
    # keeps a plotting failure out of the write path. run_traj calls
    # visualize_trajectory ABOVE TL_RunPy, so a NameError there stopped
    # the litho from ever reaching Igor.
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    print('--- write returned, taking the after frame ---')
    g('goto_ldart')()
    after = g('frame')()
    g('contact_check')(after)
    tra = g('tracking_rows')(after)
    A.say('IT1 wrote %d pulses in %.1f min; after frame %s' % (tot, wr, after))

    # ---------------------------------------------------- read
    print('\n=== DID THE SUPERDOMAINS TURN? ===')
    tiles = g('ctrl_tiles')(0.35, FRAME - 0.35, 0.35, 0.35 + WIN, WIN)
    top = max(ys) + halo + 0.05
    if FRAME - 0.35 - top >= WIN:
        tiles += g('ctrl_tiles')(0.35, FRAME - 0.35, top, FRAME - 0.35, WIN)
    if len(slots) > len(panels):
        gx, gy = slots[len(panels)]
        print('  in-grid control G at (%.2f,%.2f)' % (gx, gy))
    else:
        gx = gy = None
        print('  no spare slot for an in-grid control; the edge bands carry it')
    res = A.read_direction(ns, F_REF, after, panels, triad, WIN, tiles)
    s0 = s1 = None
    if gx is not None:
        s0 = g('dir_state')(F_REF, gx, gy, WIN, triad, panels[0]['cmd'])
        s1 = g('dir_state')(after, gx, gy, WIN, triad, panels[0]['cmd'])
    if s0 and s1:
        res['in_grid_control'] = dict(dom0=s0['dom'], dom1=s1['dom'],
                                      dlead=s1['lead'] - s0['lead'])
        print('  G (unwritten): dom %3.0f -> %3.0f, d(lead) %+.3f'
              % (s0['dom'], s1['dom'], s1['lead'] - s0['lead']))

    print('\n--- VDART: re-poling check at 128 px ---')
    g('setup_scan')(size_um=FRAME, px=128, rate=RATE, angle_deg=0.0)
    g('goto_vdart')()
    vf = g('frame')()
    g('orbit_balance')(vf)
    g('goto_ldart')()
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0)

    # ---------------------------------------------------- the 2x2
    print('\n' + '=' * 74)
    print('IT1 VERDICT')
    print('=' * 74)
    P = res['panels']
    if not res['readable']:
        print('  UNREADABLE, not unsuccessful. flip rate %.0f%%, floor %.3f.'
              % (100 * res['flip_rate'], res['floor']))
        print('  The panels are written and can be re-scored from fresh '
              'baselines. This counts as a strike, not a result.')
        st['strikes'] = st.get('strikes', 0) + 1
    else:
        st['strikes'] = 0
        have = [k for k in 'ABCDE' if k in P]
        a = P['A']['turned'] if 'A' in P else False
        b = P['B']['turned'] if 'B' in P else False
        c = P['C']['turned'] if 'C' in P else False
        dd = P['D']['turned'] if 'D' in P else False
        e = P['E']['turned'] if 'E' in P else None
        for k in have:
            print('  %s  sigma %5.0f (%.2f x)  %s'
                  % (k, P[k]['sigma'], P[k]['sigma'] / sc,
                     'TURNED' if P[k]['turned'] else 'no'))
        if not a:
            print('\n  -> VOID: the positive control did not turn. Do not read '
                  'the others.')
        elif b and not c and not dd:
            print('\n  -> T3 CONFIRMED IN BOTH CONDITIONS, in a fresh area.')
            print('     B turned at half the sites and twice the dwell, so the')
            print('     drive variable is areal charge density. C failed with')
            print('     the period doubled at identical sigma, so commensuration')
            if e is None:
                print('     is required. E was dropped for space, so the')
                print('     sigma_c prediction is still untested.')
            else:
                print('     is required. E at 1.00 sigma_c %s.'
                      % ('turned - the boundary is at or below sigma_c'
                         if e else 'did not - the boundary is above sigma_c'))
        elif not b:
            print('\n  -> sigma IS NOT THE DRIVE VARIABLE. B carried the same')
            print('     areal charge as A and failed, so site density matters in')
            print('     itself and C40 needs replacing.')
        elif c:
            print('\n  -> COMMENSURATION IS NOT REQUIRED. C turned at period')
            print('     2 Lambda, so only the lattice axis matters.')
        elif dd:
            print('\n  -> sigma_c is lower here than 302.')
        else:
            print('\n  -> mixed; report the numbers, do not fit a story.')
        note = A.refine_sigma_c(st, res)
        if note:
            print('\n  ' + note)

    # ---------------------------------------------------- record
    st['iteration'] = st.get('iteration', 0) + 1
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr
    st['used_areas'].append([[XOFF, YOFF], FRAME, 'IT1'])
    if res.get('readable'):
        st['completed'] = st.get('completed', []) + ['IT1_factorial_and_sigma_prediction']
        if st['queue'] and st['queue'][0].startswith('IT1'):
            st['queue'] = st['queue'][1:]
    st['history'] = st.get('history', []) + [dict(
        name='IT1_factorial_and_sigma_prediction',
        when=time.strftime('%Y-%m-%d %H:%M'), lam=LAM, triad=triad,
        frames=dict(b1=b1, b2=b2, b3=b3, ref=F_REF, after=after, vdart=vf),
        panels=[{k: (v if not isinstance(v, np.floating) else float(v))
                 for k, v in p.items() if k != 'ref'} for p in panels],
        result=res, write_min=wr)]
    A.save_state(st)
    return panels, res, wr


prop = json.load(io.open(os.path.join(A.PROJ, 'it1_proposal.json'),
                         encoding='utf-8'))
try:
    with A.Lock():
        with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
            panels, res, wr = main()
    st = A.load_state()
    A.log_to_notebook(prop, res, None, buf.getvalue(), st['iteration'])
except SystemExit as e:
    print('\nHALTED: %s' % e)
    A.say('IT1 halted: %s' % e)
except Exception:
    print('\nFAILED:')
    traceback.print_exc()
    A.say('IT1 failed: %s' % traceback.format_exc().splitlines()[-1])
finally:
    if os.path.exists(A.LOCK):
        os.remove(A.LOCK)
    io.open(os.path.join(A.PROJ, 'it1_console.txt'), 'w',
            encoding='utf-8').write(buf.getvalue())
