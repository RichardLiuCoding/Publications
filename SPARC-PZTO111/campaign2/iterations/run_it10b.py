# -*- coding: utf-8 -*-
"""IT10b - the letters, onto the canvas IT6 already prepared.

WHY THIS EXISTS
    IT6 rastered (-14,-14) along 62 deg, measured the result, and then halted at
    preflight before writing its letters: S9 saw the area IT6 itself had just
    registered and reported a self-overlap (PITFALLS 17, since fixed). So the
    canvas exists and is unused:

        background aligned to 62 deg at w = 0.601, lead 0.381
        Lambda 280 nm, window 1.22 um, post-raster frame PZTO_LDART_0123

    Re-running the whole of IT6 would spend 23.5 minutes re-rastering film that
    is already prepared. This writes stage B only.

AND IT CARRIES IT10's FIX
    IT6's word was horizontal while its raster ran at 62 deg, and since
    gen_center_out_raster measures its box in the rotated frame, only 39 % of the
    word's stroke area landed on treated film - 97 % of the T, 19 % of the U,
    18 % of the K (PITFALLS 16). Here the word is laid ALONG 62 deg, which puts
    97-100 % of every letter on the prepared stripe.

WHAT THE RASTER ACTUALLY DID, and why it does not change the plan
    C26 says a charge-balanced raster DEPLETES the family parallel to its scan
    lines. On this virgin film it did the opposite: w(62) went 0.415 -> 0.601
    while the other two fell. C26's own single unpoled control hinted at this
    (0.15 -> 0.23 along its raster). So the raster is an ALIGNER on unpoled film
    and a depleter on pre-poled film - see C49.

    Either way stage B is unchanged: it needs a known, uniform local dominant to
    command 60 deg away from, and 62 deg at w = 0.601 is a better canvas than
    the depletion recipe was aiming for.
"""
import io
import os
import sys
import time
import contextlib
import traceback
import numpy as np
import autoloop as A

PROJ = A.PROJ
# Reuse IT10's letter machinery by IMPORTING it, not by exec'ing a slice of the
# file. run_it10.py guards its run behind `if __name__ == "__main__"`, so the
# import only defines things. The earlier version injected these names through
# globals() at runtime, which works but is invisible to the static audit - and
# the static audit has caught three real faults tonight, so it is worth keeping
# able to see.
from run_it10 import (word_frame, hit_word, in_letter, letter_segments,
                      utk_sites, director_map, save_figure, flatness, Tee,
                      meter, FRAME, PX, RATE, V, STEP, SPEED, R_EFF,
                      SIGMA_RATIO, LET_W, LET_H, LET_GAP, STROKE, BOX_W,
                      BOX_H)

# --- the canvas IT6 left, read off it6_console.txt -----------------------
AREA = (-14.0, -14.0)
TRIAD = [2.0, 62.0, 122.0]
LAM = 280.0
REF = 'PZTO_LDART_0123.ibw'      # the post-raster frame: before the letters
ANG_RAST = 62.0                  # the raster direction = the word direction
ANG_BG = 62.0                    # the background director it produced
W_BG = 0.601

buf = io.StringIO()


def main():
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT10b  UTK along the raster, on IT6s canvas   %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 78)
    if os.path.exists(A.STOP):
        raise SystemExit('STOP present')
    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    g('check_folder')()

    XOFF, YOFF = AREA
    print('\n--- resuming on the canvas IT6 prepared ---')
    print('    area (%+.1f,%+.1f), background %.0f deg at w = %.3f'
          % (XOFF, YOFF, ANG_BG, W_BG))
    print('    reference frame %s (post-raster, pre-letters)' % REF)
    print('    IT6 spent 23.5 min rastering this; re-running stage A would')
    print('    spend it again on film that is already prepared.')
    g('scanner_ok')(XOFF, YOFF, FRAME)
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_ldart')()
    meter(ns, 'at start')

    triad = list(TRIAD)
    PX_NM = FRAME / PX * 1000.0
    sp = LAM / 2000.0
    WIN = float(max(4.2 * LAM / 1000.0, 26 * PX_NM / 1000.0))
    g('window_check')(WIN, PX_NM, LAM, name='readout window')

    # Confirm the canvas is still there before writing on it. The raster was
    # over an hour ago and the tip has been elsewhere; if the background has
    # relaxed, the command would be computed against a state that no longer
    # exists. This is cheap and it is the whole premise of the iteration.
    print('\n--- is the canvas still aligned? (fresh frame, same offset) ---')
    chk = g('frame')()
    ds = g('dir_state')
    BX0, BX1 = FRAME / 2 - BOX_W / 2, FRAME / 2 + BOX_W / 2
    BY0, BY1 = FRAME / 2 - BOX_H / 2, FRAME / 2 + BOX_H / 2

    def popn(tag, cmd):
        out = []
        for cy in np.arange(BY0 + WIN / 2, BY1 - WIN / 2 + 1e-9, WIN / 2):
            for cx in np.arange(BX0 + WIN / 2, BX1 - WIN / 2 + 1e-9, WIN / 2):
                s = ds(tag, cx, cy, WIN, triad, cmd)
                if s:
                    out.append(s['w_cmd'])
        return (float(np.mean(out)), float(np.std(out)), len(out)) if out \
            else (float('nan'), float('nan'), 0)

    now = {}
    for t in triad:
        m, sd, n = popn(chk, t)
        now[t] = m
        print('    w(%3.0f deg) = %.3f +- %.3f over %d windows%s'
              % (t, m, sd, n, '   <- the raster direction' if abs(t - ANG_RAST)
                 < 1 else ''))
    dom_now = max(now, key=lambda k: now[k])
    lead_now = now[dom_now] - sorted(now.values())[-2]
    print('    dominant %.0f deg at w = %.3f, lead %.3f  (IT6 measured %.0f at '
          '%.3f)' % (dom_now, now[dom_now], lead_now, ANG_BG, W_BG))
    if abs(dom_now - ANG_BG) > 1 or now[dom_now] < 0.45:
        raise SystemExit('the canvas has changed: dominant %.0f at w %.3f '
                         'against %.0f at %.3f an hour ago. Writing letters '
                         'commanded from a stale background would be '
                         'meaningless - re-run the full IT10 instead.'
                         % (dom_now, now[dom_now], ANG_BG, W_BG))
    print('    -> the canvas holds. This is also a RETENTION measurement: the')
    print('       raster-aligned state survived %s and several scans.'
          % 'about an hour')

    # ------------------------------------------------------- the letters
    cand = sorted(triad, key=lambda t: -abs((t - dom_now + 90) % 180 - 90))
    cmd = float(cand[0])
    total_w = 3 * LET_W + 2 * LET_GAP
    WORD_ANG = float(ANG_RAST)
    layout = [(ch, i * (LET_W + LET_GAP), LET_W, LET_H)
              for i, ch in enumerate('UTK')]
    O, e1, e2 = word_frame(WORD_ANG, total_w, LET_H, FRAME)
    print('\n=== write UTK, commanded %.0f deg against a %.0f deg background '
          '===' % (cmd, dom_now))
    print('  word laid along %.0f deg so it lies on the rastered stripe'
          % WORD_ANG)
    corners = []
    for (ch, x0, w, h) in layout:
        for (aa, bb) in ((x0, 0.0), (x0 + w, 0.0), (x0, h), (x0 + w, h)):
            corners.append(O + aa * e1 + bb * e2)
    cx_all = [float(c[0]) for c in corners]
    cy_all = [float(c[1]) for c in corners]
    print('  spans x %.2f-%.2f, y %.2f-%.2f in the scan frame'
          % (min(cx_all), max(cx_all), min(cy_all), max(cy_all)))
    if min(cx_all) < 0.3 or min(cy_all) < 0.3 or max(cx_all) > FRAME - 0.3 \
            or max(cy_all) > FRAME - 0.3:
        raise SystemExit('the tilted word leaves the frame')

    dref, _ = g('ibw')(chk)
    print('  topography under each letter:')
    let_flat = {}
    for (ch, x0, w, h) in layout:
        c = O + (x0 + w / 2) * e1 + (h / 2) * e2
        r_ = flatness(dref, float(c[0]), float(c[1]), max(w, h) / 2, FRAME)
        let_flat[ch] = float(r_)
        print('    %s at (%.2f,%.2f): %5.1f nm' % (ch, c[0], c[1], r_))

    dwell = SIGMA_RATIO * sc * sp ** 2 / V
    pn = max(1, int(round(dwell * SPEED / STEP)))
    dwell = pn * STEP / SPEED
    sigma = (1 / sp ** 2) * V * dwell
    sites = utk_sites('UTK', layout, O, e1, e2, sp, cmd, V, sign_every=1)
    per = {}
    for q in sites:
        per[q[3]] = per.get(q[3], 0) + 1
    print('  %d sites %s, dwell %.2f s -> sigma %.0f = %.2f sigma_c, %.1f V.s '
          'per site' % (len(sites), per, dwell, sigma, sigma / sc, V * dwell))
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.1f V.s per site over half C21s %.0f'
                         % (V * dwell, A.CHG_1PULSE_MAX))
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    for (x, y, v, ch) in sites:
        tb.dwell((x, y), v, n=pn)
    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    print('  %d pts, mean V %+.6f, %.1f min, footprint x [%.2f,%.2f] '
          'y [%.2f,%.2f]' % (len(Vv), Vv.mean(), wr, X.min(), X.max(),
                             Y.min(), Y.max()))
    if abs(Vv.mean()) > 1e-6:
        raise SystemExit('net DC %.2e' % Vv.mean())
    if np.abs(Vv).max() > A.V_CEILING + 1e-9:
        raise SystemExit('over the voltage ceiling')
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('%.1f min against a %.0f min cap'
                         % (wr, A.MAX_WRITE_MIN))
    print('\n--- preflight ---')
    P2 = dict(PROP)
    P2['offset'] = (XOFF, YOFF)
    P2['frame_try'] = [FRAME]
    P2['panels'] = [dict(label='UTK', keep=1.0, dwell=dwell, sigma=sigma,
                         sign_every=1, spacing_div=2.0)]
    ok, fails = A.preflight(P2, st, ns)
    if not ok:
        raise SystemExit('preflight: %s' % '; '.join(fails))

    fn = os.path.join(PROJ, 'output', '260822_IT10b_UTK.txt')
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr
    A.save_state(st)
    g('goto_ldart')()
    a1 = g('frame')()
    meter(ns, 'after letters')
    g('contact_check')(a1)
    a2 = g('frame')()

    # ------------------------------------------------------- the readout
    print('\n=== DID THE LETTERS TAKE? ===')
    step_probe = 0.55
    inside, between = [], []
    for _b in np.arange(-0.35, LET_H + 0.35 + 1e-9, step_probe):
        for _a in np.arange(-0.35, total_w + 0.35 + 1e-9, step_probe):
            p = O + _a * e1 + _b * e2
            cx, cy = float(p[0]), float(p[1])
            if cx - WIN / 2 < 0.3 or cy - WIN / 2 < 0.3 \
                    or cx + WIN / 2 > FRAME - 0.3 \
                    or cy + WIN / 2 > FRAME - 0.3:
                continue
            hit = hit_word(cx, cy, layout, O, e1, e2, STROKE)
            s0 = ds(chk, cx, cy, WIN, triad, cmd)
            s1 = ds(a1, cx, cy, WIN, triad, cmd)
            if s0 and s1:
                (inside if hit else between).append((s1['w_cmd'], s0['w_cmd'],
                                                     s1['dom']))
    ai = np.array([q[0] for q in inside])
    bi_ = np.array([q[0] for q in between])
    a0 = np.array([q[1] for q in inside])
    b0 = np.array([q[1] for q in between])
    print('  %d probes on a stroke, %d between (window %.2f um)'
          % (len(ai), len(bi_), WIN))
    print('  w(%.0f) on strokes   %.3f +- %.3f   (before %.3f)'
          % (cmd, ai.mean(), ai.std(ddof=1), a0.mean()))
    print('  w(%.0f) between      %.3f +- %.3f   (before %.3f)'
          % (cmd, bi_.mean(), bi_.std(ddof=1), b0.mean()))
    con = (ai.mean() - bi_.mean()) - (a0.mean() - b0.mean())
    nul = 2.0 * np.sqrt(a0.std(ddof=1) ** 2 / max(len(a0), 1)
                        + b0.std(ddof=1) ** 2 / max(len(b0), 1))
    print('  letter contrast %+.3f against a 2-sigma null of %.3f -> %.1f x'
          % (con, nul, con / max(nul, 1e-9)))
    on_t = float(np.mean([abs((q[2] - cmd + 90) % 180 - 90) < 20
                          for q in inside])) if inside else float('nan')
    on_b = float(np.mean([abs((q[2] - cmd + 90) % 180 - 90) < 20
                          for q in between])) if between else float('nan')
    print('  dominant within 20 deg of the command: %.0f %% on strokes, '
          '%.0f %% between' % (100 * on_t, 100 * on_b))
    # per letter, since IT6s coverage problem was per letter
    print('\n  per letter (all should be alike now that coverage is uniform):')
    per_let = {}
    for (ch, x0, w, h) in layout:
        v1, v0 = [], []
        for _b in np.arange(-0.2, h + 0.2, 0.35):
            for _a in np.arange(x0 - 0.2, x0 + w + 0.2, 0.35):
                p = O + _a * e1 + _b * e2
                cx, cy = float(p[0]), float(p[1])
                if not hit_word(cx, cy, layout, O, e1, e2, STROKE):
                    continue
                if cx - WIN / 2 < 0.3 or cy - WIN / 2 < 0.3 \
                        or cx + WIN / 2 > FRAME - 0.3 \
                        or cy + WIN / 2 > FRAME - 0.3:
                    continue
                s1 = ds(a1, cx, cy, WIN, triad, cmd)
                s0 = ds(chk, cx, cy, WIN, triad, cmd)
                if s0 and s1:
                    v1.append(s1['w_cmd'])
                    v0.append(s0['w_cmd'])
        if v1:
            per_let[ch] = dict(after=float(np.mean(v1)),
                               before=float(np.mean(v0)),
                               gain=float(np.mean(v1) - np.mean(v0)),
                               n=len(v1))
            print('    %s: w %.3f -> %.3f, gain %+.3f over %d probes'
                  % (ch, np.mean(v0), np.mean(v1),
                     np.mean(v1) - np.mean(v0), len(v1)))

    vf = None
    try:
        print('\n--- VDART at 128 px ---')
        g('setup_scan')(size_um=FRAME, px=128, rate=RATE, angle_deg=0.0,
                        xoff_um=XOFF, yoff_um=YOFF)
        g('goto_vdart')()
        vf = g('frame')()
        g('orbit_balance')(vf)
    except Exception as e:
        print('  VDART skipped (%s)' % type(e).__name__)
    g('goto_ldart')()
    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    meter(ns, 'at end')

    fig = None
    try:
        mstep = max(0.55, WIN / 2)
        mbox = (max(0.35, min(cx_all) - 1.0),
                min(FRAME - 0.35, max(cx_all) + 1.0),
                max(0.35, min(cy_all) - 1.0),
                min(FRAME - 0.35, max(cy_all) + 1.0))
        nx = int((mbox[1] - mbox[0] - WIN) / mstep) + 1
        ny = int((mbox[3] - mbox[2] - WIN) / mstep) + 1
        print('\n  director map %d x %d over two frames, about %.0f min'
              % (nx, ny, 2 * nx * ny * 1.6 / 60.0))
        xs_m, ys_m, Wb, _ = director_map(g, chk, triad, WIN, cmd, step=mstep,
                                         box=mbox)
        _, _, Wa, Da = director_map(g, a1, triad, WIN, cmd, step=mstep,
                                    box=mbox)
        fig = save_figure(os.path.join(PROJ, 'IT10b_UTK.png'), xs_m, ys_m,
                          Wb, Wa, Da, triad, cmd, layout, O, e1, e2,
                          'IT10b  "UTK" along the raster   area (%+.1f,%+.1f)  '
                          ' background %.0f deg   commanded %.0f deg   '
                          'sigma %.2f sigma_c' % (XOFF, YOFF, dom_now, cmd,
                                                  sigma / sc))
    except Exception:
        traceback.print_exc()

    res = dict(readable=True, area=[XOFF, YOFF], lam=LAM, window=WIN,
               triad=triad, sigma=sigma, sigma_over_c=sigma / sc, dwell=dwell,
               n_sites=len(sites), sites_per_letter=per, stroke_um=STROKE,
               letter_wh=[LET_W, LET_H], word_angle=WORD_ANG,
               background_deg=dom_now, command_deg=cmd,
               canvas=dict(measured_now={('%.0f' % t): now[t] for t in triad},
                           it6_after={'2': 0.179, '62': 0.601, '122': 0.220},
                           it6_before={'2': 0.242, '62': 0.415, '122': 0.343},
                           retained=True),
               letters=dict(w_on=float(ai.mean()), w_between=float(bi_.mean()),
                            w_on_before=float(a0.mean()),
                            w_between_before=float(b0.mean()),
                            contrast=float(con), null=float(nul),
                            x_null=float(con / max(nul, 1e-9)),
                            on_target_strokes=on_t, on_target_between=on_b,
                            n_on=len(ai), n_between=len(bi_)),
               per_letter=per_let, letter_flatness=let_flat,
               frames=dict(ref=chk, it6_post_raster=REF,
                           after=[a1, a2], vdart=vf),
               figure=fig, minutes=wr)

    print('\n' + '=' * 74)
    print('IT10b VERDICT')
    print('=' * 74)
    gains = [v['gain'] for v in per_let.values()]
    spread = (max(gains) - min(gains)) if gains else float('nan')
    print('  canvas held at %.0f deg, w %.3f (IT6 left it at %.3f)'
          % (dom_now, now[dom_now], W_BG))
    print('  contrast %+.3f = %.1f x the null; on target %.0f %% on strokes '
          'against %.0f %% between'
          % (con, con / max(nul, 1e-9), 100 * on_t, 100 * on_b))
    print('  per-letter gains %s, spread %.3f'
          % (', '.join('%s %+.3f' % (k, v['gain'])
                       for k, v in per_let.items()), spread))
    if con > nul and on_t > on_b + 0.15:
        print('\n  -> THE LETTERS ARE THERE, on a background the raster')
        print('     aligned and the letters then locally overrode. An')
        print('     arbitrary shape written into super-domain ORIENTATION and')
        print('     read back as an image: the rules compose.')
        if spread == spread and spread < 0.10:
            print('     The three letters agree to %.3f, which is what IT6s'
                  % spread)
            print('     coverage problem predicted would improve.')
    elif con > nul:
        print('\n  -> contrast present (%.1f x) but the dominant director is'
              % (con / max(nul, 1e-9)))
        print('     only on target over %.0f %% of strokes. Partial write.'
              % (100 * on_t))
    else:
        print('\n  -> NO letter contrast (%+.3f against %.3f). With the canvas'
              % (con, nul))
        print('     confirmed aligned beforehand, this is the letters failing,')
        print('     not the background. Check the meter log and the figure.')

    st['iteration'] = st.get('iteration', 0) + 1
    if PROP['name'] not in st['completed']:
        st['completed'].append(PROP['name'])
    A.save_state(st)

    note = ['### The canvas IT6 prepared, re-measured an hour later', '',
            '| director | IT6 before raster | IT6 after | now |',
            '|---|---|---|---|']
    for t in triad:
        note.append('| %.0f deg%s | %.3f | %.3f | **%.3f** |'
                    % (t, ' (rastered)' if abs(t - ANG_RAST) < 1 else '',
                       res['canvas']['it6_before']['%.0f' % t],
                       res['canvas']['it6_after']['%.0f' % t], now[t]))
    note += ['',
             'The raster-aligned state was still there after about an hour and '
             'several intervening scans, which is a retention result in its own '
             'right.',
             '', '### The letters', '',
             '%d sites (%s), spacing %.0f nm, sigma %.0f = %.2f sigma_c, '
             'stroke %.2f um, word laid along %.0f deg, commanded %.0f deg '
             'against a %.0f deg background.'
             % (len(sites), ', '.join('%s %d' % kv for kv in per.items()),
                sp * 1000, sigma, sigma / sc, STROKE, WORD_ANG, cmd, dom_now),
             '',
             '| region | w(cmd) after | before | probes |',
             '|---|---|---|---|',
             '| on a stroke | **%.3f** | %.3f | %d |'
             % (ai.mean(), a0.mean(), len(ai)),
             '| between strokes | %.3f | %.3f | %d |'
             % (bi_.mean(), b0.mean(), len(bi_)),
             '',
             '**Contrast %+.3f against a 2-sigma null of %.3f = %.1fx.** '
             'Dominant within 20 deg of the command over %.0f %% of stroke '
             'probes against %.0f %% between.'
             % (con, nul, con / max(nul, 1e-9), 100 * on_t, 100 * on_b),
             '', '| letter | w before | w after | gain | probes |',
             '|---|---|---|---|---|']
    for k, v in per_let.items():
        note.append('| %s | %.3f | %.3f | **%+.3f** | %d |'
                    % (k, v['before'], v['after'], v['gain'], v['n']))
    note += ['',
             'IT6 put 97 %% of its T but only 19 %% of its U and 18 %% of its '
             'K on treated film, because its word was horizontal while its '
             'raster ran at 62 deg (PITFALLS 16). Here the word lies along the '
             'raster, so coverage is 97-100 %% for every letter and the '
             'per-letter gains are directly comparable.',
             '',
             'Topography under each letter: '
             + ', '.join('%s %.1f nm' % kv for kv in let_flat.items()) + '.']
    if fig:
        note += ['', 'Figure: `%s`.' % os.path.basename(fig)]
    res['note'] = chr(10).join(note)
    return res, wr


PROP = dict(
    name='IT10b_UTK_on_IT6_canvas',
    hypothesis=('IT6 rastered (-14,-14) along 62 deg and then halted before '
                'writing its letters, when S9 saw the area IT6 had itself just '
                'registered (PITFALLS 17). The canvas is therefore prepared and '
                'unused: background 62 deg at w = 0.601. It also showed that on '
                'virgin film a charge-balanced raster ALIGNS the family parallel '
                'to its scan lines rather than depleting it, the opposite of '
                'C26 and consistent with C26s own unpoled control. Stage B '
                'should now work as designed, with the word laid ALONG the '
                'raster so every letter sits on treated film.'),
    prediction=('The canvas is re-measured first: if it has relaxed, the '
                'iteration stops rather than commanding from a stale '
                'background. Then U, T and K as masked pulse lattices commanded '
                '60 deg from the background director. Coverage is 97-100 % per '
                'letter instead of IT6s 39 %, so the three letters should read '
                'alike - which is the specific prediction the coverage fix '
                'makes.'),
    outcomes={'letters resolved and per-letter gains alike':
              'the rules compose, and the coverage explanation for IT6 is '
              'confirmed',
              'letters resolved but unequal':
              'something other than background coverage varies across the '
              'word - topography is the first thing to check, and it is '
              'recorded per letter',
              'no contrast':
              'with the canvas verified aligned beforehand this is the letters '
              'failing rather than the background',
              'canvas has relaxed':
              'the iteration halts, and that is itself a retention result - '
              'the raster-aligned state does not survive an hour'},
    caveat=('This reuses a canvas prepared an hour earlier rather than a fresh '
            'one, so the before-letters reference frame is separated from the '
            'write by that interval plus several scans. The canvas check at the '
            'start is what makes that defensible: it confirms the background is '
            'still where IT6 left it before anything is written. The letters '
            'are at Lambda/2 spacing, which C48 says caps purity near 0.49; '
            'Lambda/4 would reach ~0.85 but costs 1.4x the time and exceeds the '
            'per-write cap for a word this size.'),
    offset=list(AREA), frame_try=[FRAME], v=V, collective=True,
    vary_sigma=False,
    # Declared on purpose: this iteration writes onto the area IT6 prepared.
    # S9 would otherwise refuse the footprint, and renaming to dodge the check
    # would hide that there were two iterations here rather than one.
    reuse_areas=['IT6_UTK'],
    panels=[dict(label='UTK', keep=1.0, dwell=None, sign_every=1,
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
        A.say('IT10b halted: %s' % e)
    except Exception:
        print('\nFAILED:')
        traceback.print_exc()
        A.say('IT10b failed: %s' % traceback.format_exc().splitlines()[-1])
    finally:
        if os.path.exists(A.LOCK):
            os.remove(A.LOCK)
        io.open(os.path.join(PROJ, 'it10b_console.txt'), 'w',
                encoding='utf-8').write(buf.getvalue())
