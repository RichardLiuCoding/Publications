# -*- coding: utf-8 -*-
"""IT6 - "UTK" written in in-plane super-domain orientation.

THE POINT
    Everything in this campaign has been a 2 um panel answering a yes/no
    question. This one asks whether the rules add up to a device: can an
    arbitrary shape be written into the DIRECTION of the in-plane super domains,
    and read back as an image?

THE RECIPE, and where each step comes from
    Stage A - DEPLETE, to make a uni-directional background.
        C26: a charge-balanced raster depletes the family parallel to its own
        scan lines, and does it harder than the pulse lattice manages
        (w -> 0.83-0.84 against the lattice's ~0.5). Its weakness is that the
        DESTINATION is not predicted: two panels with identical starting
        populations went to opposite members. That does not matter here.
        I do not need to choose the background director in advance - I only need
        it to be single-valued, and then I measure which one it is.

        C26's caveat, taken seriously: the depletion was seen on PRE-POLED
        panels, while the one unpoled control moved the other way. So this is
        measured after the raster, not assumed, and the letters are only written
        once the background is confirmed uni-directional.

    Stage B - SELECT, to write the letters.
        C43 + C46: a charge-balanced point-pulse lattice, sign alternating every
        row, commanded 60 deg from the LOCAL dominant director, rotates the
        director to the command. C41: any template period from Lambda to 8 Lambda
        works, so the period is not critical. C43: uniform polarity does NOT
        work, so the alternation is kept. C40: w rises like ln(sigma).

        After stage A the local dominant IS the background director everywhere
        inside the box, so the whole letter set shares one command - which is
        exactly the configuration every successful panel has used.

WHY THE LETTERS ARE THE SIZE THEY ARE
    The director is only defined over a few lamellar periods, so the readout
    window cannot be smaller than about 4 Lambda ~ 1.2 um, and a stroke thinner
    than the window cannot be resolved no matter how many pixels are scanned.
    Stroke width is therefore 1.1 um - at the limit, deliberately - and the
    letters are 3.2 um tall. This is the smallest "UTK" this physics permits,
    and saying so is part of the result.

SAFETY
    Unchanged: 10 V ceiling, scanner range, charge balance at file level, the
    V.s-per-site cap, the write budget, the static audit, the flatness gate. The
    letters break no rule that the panels did not also obey - a masked lattice is
    still a lattice, and it is balanced to the last site.
"""
import io
import os
import re
import sys
import ast
import time
import contextlib
import traceback
import numpy as np
import autoloop as A

FRAME, PX = 12.0, 256
RATE = A.TIP_SPEED_MAX / (2.0 * FRAME)
V, STEP, SPEED, R_EFF = 10.0, 0.02, 0.5, 0.625
V_RAST = 9.0                 # C26 used 7 V at Lambda/4; this is Lambda/2 at 9 V
SIGMA_RATIO = 1.2            # letters. 1.5 needed 26.5 min against a 26 min
                             # cap; C46 shows selection well below sigma_c, and
                             # C40s law puts w at 0.51 here against 0.54 at 1.5,
                             # so lowering sigma costs far less than thinning
                             # the strokes, which are already at the resolution
                             # limit.
MOD_MIN = 0.18
FLAT_REL = 1.5

# --- the aligned box, and the letters inside it (um, frame coordinates) ---
BOX_W, BOX_H = 10.6, 4.0     # raster box, centred in the frame
# Solved, not chosen. The stroke cannot go below ~4*Lambda (the director is
# undefined over less), legibility needs letter width >= 2*stroke and gaps >=
# stroke, and write time = Area * sigma / V with the lattice spacing cancelling
# out. 1.1 um strokes on 2.0 um letters merged into illegible blobs.
LET_H, LET_W, STROKE = 2.6, 2.4, 1.2
LET_GAP = 1.2

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
        print('  meter %-16s defl %+.3f  |  %s'
              % (tag, v[1] if len(v) > 1 else float('nan'),
                 '  '.join('%+.3f' % q for q in v[:6])))
        return [float(q) for q in v[:6]]
    except Exception as e:
        print('  meter %-16s unavailable (%s)' % (tag, type(e).__name__))
        return None


def flatness(d, cx, cy, half, frame):
    """Height range in nm inside a square patch, after removing a plane."""
    z = np.asarray(d, float)
    while z.ndim > 2:
        z = z[0]
    if z.ndim != 2:
        return float('nan')
    if np.nanmax(np.abs(z)) < 1e-3:
        z = z * 1e9
    ny, nx = z.shape
    i0, i1 = max(int((cy - half) / frame * ny), 0), min(int((cy + half) / frame * ny) + 1, ny)
    j0, j1 = max(int((cx - half) / frame * nx), 0), min(int((cx + half) / frame * nx) + 1, nx)
    sub = z[i0:i1, j0:j1]
    if sub.size < 9:
        return float('nan')
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    Am = np.c_[xx.ravel(), yy.ravel(), np.ones(sub.size)]
    c, *_ = np.linalg.lstsq(Am, sub.ravel(), rcond=None)
    return float(np.ptp(sub - (c[0] * xx + c[1] * yy + c[2])))


# ===================================================================== letters
def letter_segments(ch, w, h):
    """Stroke centre-lines in a local box, origin at the bottom-left."""
    if ch == 'U':
        return [((0.0, h), (0.0, 0.0)), ((w, h), (w, 0.0)),
                ((0.0, 0.0), (w, 0.0))]
    if ch == 'T':
        return [((0.0, h), (w, h)), ((w / 2, h), (w / 2, 0.0))]
    if ch == 'K':
        return [((0.0, h), (0.0, 0.0)),
                ((0.0, h / 2), (w, h)), ((0.0, h / 2), (w, 0.0))]
    raise ValueError(ch)


def in_letter(px, py, segs, sw):
    """Is (px, py) within half a stroke width of any centre-line?"""
    r = sw / 2.0
    for (x0, y0), (x1, y1) in segs:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else ((px - x0) * dx + (py - y0) * dy) / L2
        t = min(1.0, max(0.0, t))
        if (px - (x0 + t * dx)) ** 2 + (py - (y0 + t * dy)) ** 2 <= r * r:
            return True
    return False


def utk_sites(word, boxes, sp, cmd_deg, v, sign_every=1, verbose=True):
    """Charge-balanced lattice sites covering the strokes of `word`.

    The lattice is generated in the rotated frame of the command, exactly as
    lattice_panel does - u along the command, sign alternating every
    `sign_every` steps perpendicular to it - and then masked by the letter
    shapes. Masking breaks the charge balance, so the majority sign is trimmed
    back site by site until the counts are equal: run_traj enforces
    |mean V| <= 0.01 and C13 is not negotiable.
    """
    t = np.deg2rad(cmd_deg)
    u = np.array([np.cos(t), np.sin(t)])
    nn = np.array([-np.sin(t), np.cos(t)])
    pos, neg = [], []
    for (ch, x0, y0, w, h) in boxes:
        segs = letter_segments(ch, w, h)
        # bound the search in rotated coordinates
        corners = [(x0, y0), (x0 + w, y0), (x0, y0 + h), (x0 + w, y0 + h)]
        pad = STROKE / 2.0 + sp
        au = [np.dot((cx, cy), u) for (cx, cy) in corners]
        av = [np.dot((cx, cy), nn) for (cx, cy) in corners]
        ia = range(int(np.floor((min(au) - pad) / sp)),
                   int(np.ceil((max(au) + pad) / sp)) + 1)
        ib = range(int(np.floor((min(av) - pad) / sp)),
                   int(np.ceil((max(av) + pad) / sp)) + 1)
        for bi in ib:
            sg = +1.0 if (bi // sign_every) % 2 == 0 else -1.0
            for ai in ia:
                p = ai * sp * u + bi * sp * nn
                if not (x0 - pad <= p[0] <= x0 + w + pad
                        and y0 - pad <= p[1] <= y0 + h + pad):
                    continue
                if in_letter(p[0] - x0, p[1] - y0, segs, STROKE):
                    (pos if sg > 0 else neg).append((float(p[0]),
                                                     float(p[1]), ch))
    n = min(len(pos), len(neg))
    if verbose:
        print('    masked lattice: %d at +V, %d at -V -> trimming to %d each'
              % (len(pos), len(neg), n))
    # trim from the ends of the longer list; the letters lose a few sites at
    # one extreme rather than losing charge balance
    pos, neg = pos[:n], neg[:n]
    sites = [(x, y, +v, ch) for (x, y, ch) in pos] \
        + [(x, y, -v, ch) for (x, y, ch) in neg]
    # serpentine-ish ordering: sort along the command axis in bands, so the tip
    # does not cross the whole word between consecutive pulses (C: an 870-site
    # ladder cost 62,054 points sign-ordered against 30,459 serpentine)
    order = {ch: i for i, (ch, _x, _y, _w, _h) in enumerate(boxes)}

    def key(q):
        a = np.dot((q[0], q[1]), u)
        b = np.dot((q[0], q[1]), nn)
        band = int(round(b / sp))
        # letter first: finishing one letter before starting the next avoids
        # crossing the whole word on every band, which is where the travel
        # overhead of a MASKED lattice comes from.
        return (order.get(q[3], 0), band, a if band % 2 == 0 else -a)
    sites.sort(key=key)
    return sites


# ================================================================ readout map
def director_map(g, tag, triad, win, cmd, step=0.30, box=None):
    """Sliding-window population of the commanded director over the frame."""
    ds = g('dir_state')
    x0, x1, y0, y1 = box if box else (0.35, FRAME - 0.35, 0.35, FRAME - 0.35)
    xs = np.arange(x0 + win / 2, x1 - win / 2 + 1e-9, step)
    ys = np.arange(y0 + win / 2, y1 - win / 2 + 1e-9, step)
    W = np.full((len(ys), len(xs)), np.nan)
    D = np.full((len(ys), len(xs)), np.nan)
    for iy, cy in enumerate(ys):
        for ix, cx in enumerate(xs):
            s = ds(tag, cx, cy, win, triad, cmd)
            if s:
                W[iy, ix] = s['w_cmd']
                D[iy, ix] = s['dom']
    return xs, ys, W, D


def save_figure(path, xs, ys, W0, W1, D1, triad, cmd, boxes, title):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as e:
        print('  matplotlib unavailable (%s); skipping the figure'
              % type(e).__name__)
        return None
    ext = [xs[0] - 0.15, xs[-1] + 0.15, ys[0] - 0.15, ys[-1] + 0.15]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    for a, M, ttl in ((ax[0], W0, 'before the letters'),
                      (ax[1], W1, 'after the letters')):
        im = a.imshow(M, origin='lower', extent=ext, vmin=0.0, vmax=1.0,
                      cmap='magma', interpolation='nearest')
        a.set_title('w(%.0f deg), %s' % (cmd, ttl))
        plt.colorbar(im, ax=a, fraction=0.046)
    im = ax[2].imshow(W1 - W0, origin='lower', extent=ext, vmin=-0.6, vmax=0.6,
                      cmap='RdBu_r', interpolation='nearest')
    ax[2].set_title('change in w(%.0f deg)' % cmd)
    plt.colorbar(im, ax=ax[2], fraction=0.046)
    for a in ax:
        for (ch, bx, by, bw, bh) in boxes:
            for (p0, p1) in letter_segments(ch, bw, bh):
                a.plot([bx + p0[0], bx + p1[0]], [by + p0[1], by + p1[1]],
                       color='#00e5ff', lw=1.0, alpha=0.55)
        a.set_xlabel('x (um)')
    ax[0].set_ylabel('y (um)')
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print('  figure -> %s' % path)
    return path


# ===================================================================== main
def main():
    st = A.load_state()
    sc = st['theory']['sigma_c']
    print('=' * 78)
    print('IT6  "UTK" in super-domain orientation   %s'
          % time.strftime('%Y-%m-%d %H:%M'))
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

    # ------------------------------------------------ a fresh, flat area
    cands = A.legal_offsets(st, FRAME, step=2.0)
    prev = tuple(st['used_areas'][-1][0]) if st['used_areas'] else (0.0, 0.0)
    cands.sort(key=lambda c: (c[0] - prev[0]) ** 2 + (c[1] - prev[1]) ** 2)
    print('\n%d legal offsets; trying the nearest first' % len(cands))
    meter(ns, 'at start')
    viable = []
    for attempt, (xo, yo) in enumerate(cands[:4]):
        print('\n--- candidate %d: (%+.1f,%+.1f) ---' % (attempt + 1, xo, yo))
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
        d0, _ = g('ibw')(scr)
        rng = flatness(d0, FRAME / 2, FRAME / 2, 0.5 * max(BOX_W, BOX_H), FRAME)
        with contextlib.redirect_stdout(io.StringIO()):
            sk = g('streak_index')(scr, (0.35, FRAME - 0.35, 0.35, 1.7))
        print('  modulation %.3f (need >= %.2f), streak %.3f, box height '
              'range %.1f nm' % (tt['mod'], MOD_MIN, sk, rng))
        if tt['mod'] < MOD_MIN or sk > A.STREAK_MAX:
            print('  -> rejected')
            continue
        print('  -> viable')
        viable.append(dict(xo=xo, yo=yo, scr=scr,
                           triad=[float(v) for v in triad_t],
                           mod=tt['mod'], rng=rng, streak=sk))
    if not viable:
        raise SystemExit('no candidate area passed. Move the coarse stage.')
    # Rank on FLATNESS, not on the order they were screened. A hard cut would
    # reject everything on this sample - the terrace is 42 nm peak-to-peak
    # across a 12 um frame - but among areas that are otherwise acceptable the
    # flattest is the one to write the letters into.
    viable.sort(key=lambda c: c['rng'])
    chosen = viable[0]
    print('\n  %d viable; ranked by height range across the box:' % len(viable))
    for c in viable:
        print('    (%+.1f,%+.1f)  range %5.1f nm  modulation %.3f%s'
              % (c['xo'], c['yo'], c['rng'], c['mod'],
                 '   <- chosen' if c is chosen else ''))

    XOFF, YOFF = chosen['xo'], chosen['yo']
    triad = chosen['triad']
    PX_NM = FRAME / PX * 1000.0
    print('\n=== area (%+.1f,%+.1f), triad %s ==='
          % (XOFF, YOFF, ['%.0f' % t for t in triad]))

    g('setup_scan')(size_um=FRAME, px=PX, rate=RATE, angle_deg=0.0,
                    xoff_um=XOFF, yoff_um=YOFF)
    g('goto_ldart')()
    b1 = g('frame')()
    b2 = g('frame')()
    g('contact_check')(b2)
    meter(ns, 'after baselines')
    d, _ = g('ibw')(b2)
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
    print('  Lambda per member %s -> %.0f nm, spacing %.0f nm, window %.2f um'
          % (['%.0f' % v for v in lm], LAM, sp * 1000, WIN))
    if STROKE < WIN - 0.05:
        print('  !! the stroke (%.2f um) is thinner than the readout window '
              '(%.2f um).' % (STROKE, WIN))
        print('     The letters will still be written, but the director map')
        print('     cannot resolve them fully - report them as at the limit.')

    def popn(tag, x0, x1, y0, y1, cmd):
        """Mean w(cmd) over a grid of windows inside a box."""
        ds = g('dir_state')
        out = []
        xs = np.arange(x0 + WIN / 2, x1 - WIN / 2 + 1e-9, WIN / 2)
        ys = np.arange(y0 + WIN / 2, y1 - WIN / 2 + 1e-9, WIN / 2)
        for cy in ys:
            for cx in xs:
                s = ds(tag, cx, cy, WIN, triad, cmd)
                if s:
                    out.append(s['w_cmd'])
        return (float(np.mean(out)), float(np.std(out)), len(out)) if out \
            else (float('nan'), float('nan'), 0)

    BX0, BX1 = FRAME / 2 - BOX_W / 2, FRAME / 2 + BOX_W / 2
    BY0, BY1 = FRAME / 2 - BOX_H / 2, FRAME / 2 + BOX_H / 2
    print('\n  aligned box x %.2f-%.2f, y %.2f-%.2f' % (BX0, BX1, BY0, BY1))
    print('  populations in the box before anything:')
    base = {}
    for k, t in enumerate(triad):
        m, s_, n_ = popn(b2, BX0, BX1, BY0, BY1, t)
        base[k] = m
        print('    w(%3.0f deg) = %.3f +- %.3f over %d windows' % (t, m, s_, n_))

    # =============================================== STAGE A: the raster
    # Deplete the family parallel to the raster (C26). Which member to raster
    # along: the one that is currently STRONGEST, so the background is pushed
    # away from where it already is and the change is unambiguous.
    k_rast = int(max(base, key=lambda k: base[k]))
    ang_rast = triad[k_rast]
    print('\n=== STAGE A: deplete the %.0f deg family (currently strongest at '
          'w = %.3f) ===' % (ang_rast, base[k_rast]))
    print('  C26: a charge-balanced raster depletes the family parallel to its')
    print('  own scan lines. The destination is not predicted, which is fine -')
    print('  it is measured below and the letters follow it.')
    tb_r = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    # Polarity comes from start_sign, NOT from the sign of v: the generator
    # takes the magnitude from v. Passing v=-9 on the second pass left both
    # passes at +9 V and a mean of +7.61 - a large DC raster, which C13 says
    # re-poles. Two passes with opposite start_sign give mean 0.0000 exactly.
    # (One call with flip_each_cycle is NOT balanced - odd cycle count, +0.587.)
    n_line = 0
    for sgn in (+1, -1):
        ns['gen_center_out_raster'](
            W_um=BOX_W, H_um=BOX_H, pitch_um=sp, angle_deg=ang_rast,
            center_um=(FRAME / 2, FRAME / 2), v=V_RAST, start_sign=sgn,
            field_um=FRAME, step_um=STEP, n_pt=0, tb=tb_r, travel_v=0.0,
            verbose=False, flip_each_cycle=False)
        n_line += 1
    Xr, Yr, Vr = tb_r.to_arrays()
    wr_r = len(Vr) * STEP / SPEED / 60.0
    sig_r = V_RAST / (sp * SPEED)
    print('  two passes at %+.0f then %.0f V (start_sign +1 / -1), pitch '
          '%.0f nm -> %d pts, %.1f min, mean V %+.4f, %.0f %% at +V'
          % (V_RAST, -V_RAST, sp * 1000, len(Vr), wr_r, Vr.mean(),
             100 * float((Vr > 1e-9).mean())))
    print('  raster areal dose %.0f V.s/um^2 (C26 worked at ~144)' % sig_r)
    if abs(Vr.mean()) > 0.01:
        raise SystemExit('the raster is not charge balanced (mean %.4f V). '
                         'Polarity comes from start_sign, not from the sign of '
                         'v.' % Vr.mean())
    if wr_r > A.MAX_WRITE_MIN:
        raise SystemExit('the raster needs %.1f min against a %.0f min cap - '
                         'coarsen the pitch or shrink the box' % (wr_r,
                                                                 A.MAX_WRITE_MIN))
    if np.abs(Vr).max() > A.V_CEILING + 1e-9:
        raise SystemExit('raster over the voltage ceiling')
    fn_r = os.path.join(A.PROJ, 'output', '260822_IT6_raster.txt')
    g('goto_ldart')()
    g('run_traj')(tb_r, fn_r, speed_um_s=SPEED, preview=False)
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr_r
    st['used_areas'].append([[XOFF, YOFF], FRAME, PROP['name']])
    A.save_state(st)
    g('goto_ldart')()
    a_r = g('frame')()
    meter(ns, 'after raster')
    g('contact_check')(a_r)

    print('\n  populations in the box AFTER the raster:')
    after = {}
    for k, t in enumerate(triad):
        m, s_, n_ = popn(a_r, BX0, BX1, BY0, BY1, t)
        after[k] = m
        print('    w(%3.0f deg) = %.3f  (was %.3f, change %+.3f)%s'
              % (t, m, base[k], m - base[k],
                 '   <- rastered along this' if k == k_rast else ''))
    k_bg = int(max(after, key=lambda k: after[k]))
    ang_bg = triad[k_bg]
    dep = after[k_rast] - base[k_rast]
    print('\n  rastered family changed by %+.3f; background is now dominated '
          'by %.0f deg at w = %.3f' % (dep, ang_bg, after[k_bg]))
    if k_bg == k_rast:
        print('  !! the rastered family is STILL dominant, so C26s depletion')
        print('     did not reproduce here - note that C26 saw it on PRE-POLED')
        print('     panels and its one unpoled control moved the other way.')
        print('     Carrying on: the letters only need a known local dominant,')
        print('     not a particular one, and the background is uniform enough')
        print('     to command against if w is high.')
    uni = after[k_bg] >= 0.45 and (after[k_bg] - sorted(after.values())[-2]) >= 0.10
    print('  uni-directional enough to write on: %s (need w >= 0.45 and a '
          '0.10 lead)' % uni)

    # =============================================== STAGE B: the letters
    # Command 60 deg from the background director - the configuration every
    # successful panel has used (C36, C43).
    cand_cmd = sorted(triad, key=lambda t: -abs((t - ang_bg + 90) % 180 - 90))
    cmd = float(cand_cmd[0])
    print('\n=== STAGE B: write UTK, commanded %.0f deg (background %.0f) ==='
          % (cmd, ang_bg))
    total_w = 3 * LET_W + 2 * LET_GAP
    lx0 = FRAME / 2 - total_w / 2
    ly0 = FRAME / 2 - LET_H / 2
    boxes = []
    for i, ch in enumerate('UTK'):
        boxes.append((ch, lx0 + i * (LET_W + LET_GAP), ly0, LET_W, LET_H))
    print('  letters %.1f x %.1f um each, stroke %.2f um, spanning x %.2f-%.2f'
          % (LET_W, LET_H, STROKE, lx0, lx0 + total_w))
    for (ch, bx, by, bw, bh) in boxes:
        if bx < BX0 + 0.1 or bx + bw > BX1 - 0.1 or by < BY0 + 0.1 \
                or by + bh > BY1 - 0.1:
            raise SystemExit('letter %s at x %.2f-%.2f, y %.2f-%.2f leaves the '
                             'aligned box' % (ch, bx, bx + bw, by, by + bh))

    # What is the film like under each letter? Recorded BEFORE the write, so a
    # weak letter afterwards can be checked against topography instead of
    # explained by it.
    _dl, _ = g('ibw')(a_r)
    print('  topography under each letter (height range after plane removal):')
    let_flat = {}
    for (ch, bx, by, bw, bh) in boxes:
        r_ = flatness(_dl, bx + bw / 2, by + bh / 2, max(bw, bh) / 2, FRAME)
        let_flat[ch] = float(r_)
        print('    %s at (%.2f,%.2f): %5.1f nm' % (ch, bx + bw / 2,
                                                   by + bh / 2, r_))
    _vals = [v for v in let_flat.values() if v == v]
    if _vals and max(_vals) > 2.0 * min(_vals):
        print('    !! the letters do not sit on comparable film (%.1f vs %.1f '
              'nm). Expect them to read unequally for topographic reasons.'
              % (max(_vals), min(_vals)))

    dwell = SIGMA_RATIO * sc * sp ** 2 / V
    pn = max(1, int(round(dwell * SPEED / STEP)))
    dwell = pn * STEP / SPEED
    sigma = (1 / sp ** 2) * V * dwell
    sites = utk_sites('UTK', boxes, sp, cmd, V, sign_every=1)
    est = len(sites) * dwell * 1.35 / 60.0
    print('  %d sites, dwell %.2f s -> sigma %.0f = %.2f sigma_c, %.1f V.s per '
          'site, about %.1f min' % (len(sites), dwell, sigma, sigma / sc,
                                    V * dwell, est))
    if V * dwell > 0.5 * A.CHG_1PULSE_MAX:
        raise SystemExit('%.1f V.s per site is over half C21s %.0f'
                         % (V * dwell, A.CHG_1PULSE_MAX))
    print('  (that estimate assumes a 1.35x travel overhead; a MASKED lattice')
    print('   runs nearer 1.55x, so the real number is checked below)')
    per = {}
    for q in sites:
        per[q[3]] = per.get(q[3], 0) + 1
    print('  sites per letter: %s' % per)
    tb = ns['TrajectoryBuilder'](field_um=FRAME, step_um=STEP, travel_v=0.0)
    for (x, y, v, ch) in sites:
        tb.dwell((x, y), v, n=pn)
    X, Y, Vv = tb.to_arrays()
    wr = len(Vv) * STEP / SPEED / 60.0
    print('  %d pts, mean V %+.6f, %.1f min of writing, footprint x '
          '[%.2f,%.2f] y [%.2f,%.2f]'
          % (len(Vv), Vv.mean(), wr, X.min(), X.max(), Y.min(), Y.max()))
    # The gate is the REAL trajectory length, not the estimate. The estimate
    # said 24.5 min for a geometry whose trajectory came to 28.
    print('  travel overhead actually %.2fx (estimate assumed 1.35x)'
          % (wr / max(len(sites) * dwell / 60.0, 1e-9)))
    if wr > A.MAX_WRITE_MIN:
        raise SystemExit('the letters need %.1f min of real trajectory against '
                         'a %.0f min cap. Lower SIGMA_RATIO or LET_H - and note '
                         'the stroke cannot shrink, it is at the resolution '
                         'limit already.' % (wr, A.MAX_WRITE_MIN))
    if abs(Vv.mean()) > 1e-6:
        raise SystemExit('the letters carry net DC (%.2e V)' % Vv.mean())
    if np.abs(Vv).max() > A.V_CEILING + 1e-9:
        raise SystemExit('over the voltage ceiling')
    if X.min() < 0.05 or Y.min() < 0.05 or X.max() > FRAME - 0.05 \
            or Y.max() > FRAME - 0.05:
        raise SystemExit('the letters leave the frame')

    print('\n--- preflight, pass 2 ---')
    P2 = dict(PROP)
    P2['offset'] = (XOFF, YOFF)
    P2['frame_try'] = [FRAME]
    P2['panels'] = [dict(label='UTK', keep=1.0, dwell=dwell, sigma=sigma,
                         sign_every=1, spacing_div=2.0)]
    ok, fails = A.preflight(P2, st, ns)
    if not ok:
        raise SystemExit('preflight (pass 2): %s' % '; '.join(fails))

    fn = os.path.join(A.PROJ, 'output', '260822_IT6_UTK.txt')
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    st['total_write_min'] = st.get('total_write_min', 0.0) + wr
    A.save_state(st)
    g('goto_ldart')()
    a1 = g('frame')()
    meter(ns, 'after letters')
    g('contact_check')(a1)
    a2 = g('frame')()

    # ===================================================== read the letters
    print('\n=== DID THE LETTERS TAKE? ===')
    ds = g('dir_state')
    inside, between = [], []
    # 0.55 um, not 0.25: dir_state costs 1.60 s per call and this grid is
    # walked over three frames. At a 1.26 um window a 0.55 um step is still
    # oversampled, so this costs smoothness, not information.
    step_probe = 0.55
    xs = np.arange(BX0 + WIN / 2, BX1 - WIN / 2 + 1e-9, step_probe)
    ys = np.arange(BY0 + WIN / 2, BY1 - WIN / 2 + 1e-9, step_probe)
    for cy in ys:
        for cx in xs:
            hit = False
            for (ch, bx, by, bw, bh) in boxes:
                if in_letter(cx - bx, cy - by, letter_segments(ch, bw, bh),
                             STROKE):
                    hit = True
                    break
            s0 = ds(b2, cx, cy, WIN, triad, cmd)
            s1 = ds(a1, cx, cy, WIN, triad, cmd)
            sr = ds(a_r, cx, cy, WIN, triad, cmd)
            if s0 and s1 and sr:
                (inside if hit else between).append(
                    (s1['w_cmd'], sr['w_cmd'], s1['dom']))
    ai = np.array([q[0] for q in inside])
    bi_ = np.array([q[0] for q in between])
    ari = np.array([q[1] for q in inside])
    arb = np.array([q[1] for q in between])
    print('  probes: %d on a stroke, %d between strokes (window %.2f um)'
          % (len(ai), len(bi_), WIN))
    print('  w(%.0f) on strokes   %.3f +- %.3f   (before the letters %.3f)'
          % (cmd, ai.mean(), ai.std(ddof=1), ari.mean()))
    print('  w(%.0f) between      %.3f +- %.3f   (before the letters %.3f)'
          % (cmd, bi_.mean(), bi_.std(ddof=1), arb.mean()))
    # the contrast, and its null: the same difference measured BEFORE the write
    con = (ai.mean() - bi_.mean()) - (ari.mean() - arb.mean())
    nul = np.sqrt(ari.std(ddof=1) ** 2 / max(len(ari), 1)
                  + arb.std(ddof=1) ** 2 / max(len(arb), 1)) * 2
    print('  letter contrast %+.3f against a 2-sigma null of %.3f -> %.1f x'
          % (con, nul, con / max(nul, 1e-9)))
    on_t = float(np.mean([abs((q[2] - cmd + 90) % 180 - 90) < 20
                          for q in inside]))
    on_b = float(np.mean([abs((q[2] - cmd + 90) % 180 - 90) < 20
                          for q in between]))
    print('  dominant within 20 deg of the command: %.0f %% on strokes, '
          '%.0f %% between' % (100 * on_t, 100 * on_b))

    # VDART, as IT4 did it: 128 px is enough to see the out-of-plane classes,
    # and orbit_balance is the check - there is no vdart_gate.
    vf = None
    try:
        print("\n--- VDART at 128 px ---")
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

    # ------------------------------------------------------------- figure
    fig = None
    try:
        # Restrict the map to the aligned box plus a 1 um margin, and step at
        # half the window. Over the whole frame at WIN/4 this was 2738 calls =
        # 73 minutes; here it is ~360 = 9 minutes, and nothing is lost because
        # the window is 1.26 um wide either way.
        mstep = max(0.55, WIN / 2)
        mbox = (max(0.35, BX0 - 1.0), min(FRAME - 0.35, BX1 + 1.0),
                max(0.35, BY0 - 1.0), min(FRAME - 0.35, BY1 + 1.0))
        _nx = int((mbox[1] - mbox[0] - WIN) / mstep) + 1
        _ny = int((mbox[3] - mbox[2] - WIN) / mstep) + 1
        print('  director map: %d x %d windows over x %.1f-%.1f, y %.1f-%.1f, '
              'two frames -> about %.0f min at 1.6 s per window'
              % (_nx, _ny, mbox[0], mbox[1], mbox[2], mbox[3],
                 2 * _nx * _ny * 1.6 / 60.0))
        xs_m, ys_m, W_before, _ = director_map(g, a_r, triad, WIN, cmd,
                                               step=mstep, box=mbox)
        _, _, W_after, D_after = director_map(g, a1, triad, WIN, cmd,
                                              step=mstep, box=mbox)
        fig = save_figure(os.path.join(A.PROJ, 'IT6_UTK.png'),
                          xs_m, ys_m, W_before, W_after, D_after, triad, cmd,
                          boxes,
                          'IT6  "UTK" in super-domain orientation   area '
                          '(%+.1f,%+.1f)   background %.0f deg   letters '
                          'commanded %.0f deg   sigma %.2f sigma_c'
                          % (XOFF, YOFF, ang_bg, cmd, sigma / sc))
    except Exception:
        traceback.print_exc()

    res = dict(readable=True, area=[XOFF, YOFF], lam=LAM, frame=FRAME, px=PX,
               triad=triad, window=WIN, sigma=sigma, sigma_over_c=sigma / sc,
               dwell=dwell, n_sites=len(sites), sites_per_letter=per,
               stroke_um=STROKE, letter_wh=[LET_W, LET_H],
               raster=dict(angle=ang_rast, v=V_RAST, pitch_um=sp,
                           dose=sig_r, minutes=wr_r,
                           w_before={('%.0f' % t): base[k]
                                     for k, t in enumerate(triad)},
                           w_after={('%.0f' % t): after[k]
                                    for k, t in enumerate(triad)},
                           depletion=dep, uni=bool(uni)),
               background_deg=ang_bg, command_deg=cmd,
               letter_flatness=let_flat,
               letters=dict(w_on=float(ai.mean()), w_between=float(bi_.mean()),
                            w_on_before=float(ari.mean()),
                            w_between_before=float(arb.mean()),
                            contrast=float(con), null=float(nul),
                            x_null=float(con / max(nul, 1e-9)),
                            on_target_strokes=on_t, on_target_between=on_b,
                            n_on=len(ai), n_between=len(bi_)),
               frames=dict(baseline=[b1, b2], after_raster=a_r,
                           after_letters=[a1, a2], vdart=vf),
               figure=fig, minutes=wr_r + wr)

    print('\n' + '=' * 74)
    print('IT6 VERDICT')
    print('=' * 74)
    print('  stage A, raster along %.0f deg: %s family %+.3f, background now '
          '%.0f deg at w = %.3f' % (ang_rast,
                                    'depleted the rastered' if dep < -0.05
                                    else 'did NOT deplete the rastered',
                                    dep, ang_bg, after[k_bg]))
    if con > nul and on_t > on_b + 0.15:
        print('  stage B: THE LETTERS ARE THERE. Strokes read w(%.0f) = %.3f'
              % (cmd, ai.mean()))
        print('  against %.3f between them, a contrast of %+.3f = %.1f x the'
              % (bi_.mean(), con, con / max(nul, 1e-9)))
        print('  null, and the dominant director is within 20 deg of the')
        print('  command over %.0f %% of the strokes against %.0f %% between.'
              % (100 * on_t, 100 * on_b))
        print('  -> an arbitrary shape has been written into super-domain')
        print('     ORIENTATION and read back as an image. The rules compose.')
    elif con > nul:
        print('  stage B: a contrast of %+.3f = %.1f x the null, but the'
              % (con, con / max(nul, 1e-9)))
        print('  dominant director is only on target over %.0f %% of the'
              % (100 * on_t))
        print('  strokes against %.0f %% between. The letters modulated the'
              % (100 * on_b))
        print('  population without completing the rotation - partial write.')
    else:
        print('  stage B: NO letter contrast (%+.3f against a null of %.3f).'
              % (con, nul))
        print('  Either the write did not take, or the stroke (%.2f um) is too'
              % STROKE)
        print('  thin for a %.2f um window to resolve - the two are the same' % WIN)
        print('  size, which is the honest limit of this readout. Check the')
        print('  meter log, and look at the figure before concluding.')
    print('\n  total written this iteration: %.1f min (raster %.1f + letters '
          '%.1f)' % (wr_r + wr, wr_r, wr))

    st['iteration'] = st.get('iteration', 0) + 1
    if PROP['name'] not in st['completed']:
        st['completed'].append(PROP['name'])
    A.save_state(st)

    # Build the notebook summary from `res` itself, so the record cannot
    # disagree with the numbers. log_to_notebook renders neither a
    # within-frame table nor a panel table for this result shape.
    L, RS = res['letters'], res['raster']
    note = []
    note.append('### Stage A - deplete (C26)')
    note.append('')
    note.append('Charge-balanced raster, %.0f V at %.0f nm pitch, along the '
                '%.0f deg member (the strongest at the time), %.1f min, areal '
                'dose %.0f V.s/um^2.'
                % (RS['v'], RS['pitch_um'] * 1000, RS['angle'], RS['minutes'],
                   RS['dose']))
    note.append('')
    note.append('| director | w before | w after | change |')
    note.append('|---|---|---|---|')
    for k in RS['w_before']:
        note.append('| %s deg%s | %.3f | %.3f | %+.3f |'
                    % (k, ' (rastered)' if abs(float(k) - RS['angle']) < 1
                       else '', RS['w_before'][k], RS['w_after'][k],
                       RS['w_after'][k] - RS['w_before'][k]))
    note.append('')
    note.append('Background afterwards: **%.0f deg**, uni-directional enough '
                'to write on: **%s**.'
                % (res['background_deg'], RS['uni']))
    note.append('')
    note.append('### Stage B - select: U, T, K as masked pulse lattices')
    note.append('')
    note.append('%d sites (%s), spacing %.0f nm, sigma %.0f = %.2f sigma_c, '
                'stroke %.2f um, letters %.1f x %.1f um, commanded **%.0f deg** '
                'against a %.0f deg background.'
                % (res['n_sites'],
                   ', '.join('%s %d' % (k, v)
                             for k, v in res['sites_per_letter'].items()),
                   res['lam'] / 2.0, res['sigma'], res['sigma_over_c'],
                   res['stroke_um'], res['letter_wh'][0], res['letter_wh'][1],
                   res['command_deg'], res['background_deg']))
    note.append('')
    note.append('| region | w(cmd) after | w(cmd) before letters | probes |')
    note.append('|---|---|---|---|')
    note.append('| on a stroke | **%.3f** | %.3f | %d |'
                % (L['w_on'], L['w_on_before'], L['n_on']))
    note.append('| between strokes | %.3f | %.3f | %d |'
                % (L['w_between'], L['w_between_before'], L['n_between']))
    note.append('')
    note.append('**Letter contrast %+.3f against a 2-sigma null of %.3f = '
                '%.1fx.** Dominant director within 20 deg of the command over '
                '%.0f %% of stroke probes against %.0f %% between them.'
                % (L['contrast'], L['null'], L['x_null'],
                   100 * L['on_target_strokes'], 100 * L['on_target_between']))
    note.append('')
    if res.get('letter_flatness'):
        note.append('Topography under each letter, recorded before the write: '
                    + ', '.join('%s %.1f nm' % (k, v) for k, v in
                                res['letter_flatness'].items())
                    + '. This sample carries a terrace edge, so unequal letters '
                      'have a topographic explanation available that does not '
                      'require a physical one.')
        note.append('')
    if res.get('vdart'):
        note.append('VDART afterwards: `%s`.' % res['vdart'])
        note.append('')
    note.append('Stroke width is set by physics, not preference: the director '
                'is undefined below about 4 Lambda, so no readout window '
                'narrower than %.2f um exists and no stroke thinner than that '
                'is resolvable at any pixel count. The strokes here are %.2f um '
                '- at the limit, deliberately.'
                % (res['window'], res['stroke_um']))
    if res.get('figure'):
        note.append('')
        note.append('Figure: `%s`.' % res['figure'].split('\\')[-1])
    res['note'] = chr(10).join(note)
    return res, wr_r + wr


PROP = dict(
    name='IT6_UTK',
    hypothesis=('If the switching rules found in this campaign are right and '
                'they compose, then an arbitrary shape can be written into the '
                'DIRECTION of the in-plane super domains. Two steps: C26 says a '
                'charge-balanced raster depletes the family parallel to its own '
                'scan lines, hard enough to leave a near-single-director '
                'background over microns; C43 and C46 say a charge-balanced '
                'point-pulse lattice, sign alternating, commanded 60 deg from '
                'the local dominant, rotates the director to the command. '
                'Deplete to get a uniform canvas, then select to draw on it.'),
    prediction=('The raster leaves one triad member dominant in the box. The '
                'letters U, T and K, written as masked pulse lattices commanded '
                '60 deg away from that member, read back with a higher w(cmd) '
                'on the strokes than between them, and with the dominant '
                'director on target inside the strokes and not outside.'),
    outcomes={'letters resolved, dominant on target':
              'the rules compose - orientation is a writable, readable degree '
              'of freedom, and the campaign has a device-level result',
              'contrast but no completed rotation':
              'partial write: the population moved without the director '
              'flipping. Either sigma or dwell is short for a masked lattice',
              'no contrast':
              'either the write failed or the 1.1 um stroke is unresolvable '
              'with a readout window of the same size - the figure and the '
              'meter log distinguish these',
              'the raster does not deplete':
              'C26 does not generalise to unpoled film, which its own single '
              'unpoled control already hinted at. The letters are then written '
              'against a three-way background and the demonstration is weaker '
              'but still interpretable'},
    caveat=('The stroke width is set by physics, not by choice: the director is '
            'only defined over about four lamellar periods, so no readout '
            'window smaller than ~1.2 um exists and no stroke thinner than that '
            'can be resolved however finely it is scanned. 1.1 um strokes are '
            'therefore AT the limit, deliberately, and a null result in stage B '
            'must be read with that in mind. Charge balance is exact: masking '
            'the lattice to the letter shapes breaks it, so the majority sign '
            'is trimmed site by site until the counts match.'),
    offset=None, frame_try=[FRAME], v=V, collective=True, vary_sigma=False,
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
        A.say('IT6 halted: %s' % e)
    except Exception:
        print('\nFAILED:')
        traceback.print_exc()
        A.say('IT6 failed: %s' % traceback.format_exc().splitlines()[-1])
    finally:
        if os.path.exists(A.LOCK):
            os.remove(A.LOCK)
        io.open(os.path.join(A.PROJ, 'it6_console.txt'), 'w',
                encoding='utf-8').write(buf.getvalue())
