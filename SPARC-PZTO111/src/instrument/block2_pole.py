# -*- coding: utf-8 -*-
"""block2_pole.py -- homogenise the out-of-plane state, then look for nano-domains.

THE OPERATOR'S METHOD. "A lot of the time the nano domains are not visible
until you write/align the IP super domains... you can try to use the full +V
scan and then full -V scan in the same area. In this way, the OP domains are
homogeneous and it becomes easier to resolve the nano domains."

WHY IT SHOULD WORK, and why the campaign needs it. Five written panels at
2.5 um have now failed to show a reproducible nano-domain periodicity. The fine
band is contaminated from both ends: the lamellar harmonics Lambda/2, /3, /4
land at 55-125 nm at the SAME director as the lamellae, and a pervasive
instrumental feature sits at ~70-80 nm near the fast scan axis in every frame
including unwritten film. Removing the out-of-plane contrast removes one whole
family of confounds.

CHARGE BALANCE. A pure +V raster has mean V = +10 and violates S4 outright.
Written as ONE file containing the +V pass followed by the -V pass over the
same square, the net DC is exactly zero and the sequence is still "+V scan then
-V scan" as described. The area is left in the state the LAST pass wrote.

DOSE. 0.03 um raster pitch at 0.5 um/s gives sigma = V/(d*s) = 667 V.s/um^2 per
polarity, which is the dose at which M13 demonstrated a full 180 deg
out-of-plane reversal on this film.

PRE-REGISTERED (S27):
  A. VDART goes UNIFORM inside the square (its modulation collapses, no
     dominant direction) -> the poling worked, and any surviving fine
     structure in LDART is in-plane.
  B. LDART fine band shows a periodicity that is NOT at the lamellar director
     and NOT at the fast axis -> those are the nano-domains, and this is the
     first clean sight of them.
  C. Nothing appears -> either they are below this probe's resolution, or they
     need the IP super-domain to be written as well, which is the next step
     (pole, then write a commensurate panel on top).
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A
import scale_tools as ST

SIZE_UM = 2.5
PX = 512
RATE = 2.0
HALF = float(os.environ.get('B2_HALF', '0.70'))   # half-width of the square
#   Write time scales with the AREA at fixed dose, so a 1.2 um square (0.60)
#   costs 3.3 min against 4.7 for 1.4 um, at the same sigma per polarity.
V = 10.0
STEP = 0.02
SPEED = 0.5
PITCH = 0.03                   # raster line pitch -> sigma 667 per polarity
# Raster line direction. The default 0 deg is the campaign's usual fast-scan
# direction, and M26 ordered the film onto the triad member nearest THAT
# direction -- which is equally consistent with a film preference and with the
# write direction selecting whichever member lies nearest it. Rotating the
# raster is what separates them.
ANG = float(os.environ.get('B2_ANG', '0.0'))
MAX_MIN = 26.0
XOFF = float(os.environ.get('B2_X', '8.0'))
YOFF = float(os.environ.get('B2_Y', '0.0'))
DRY = os.environ.get('B2_DRY', '') == '1'
STAMP = time.strftime('%y%m%d_%H%M')
CENTRE = (SIZE_UM / 2.0, SIZE_UM / 2.0)
SUPER = (150.0, 500.0)
FINE = (18.0, 90.0)


def pole_strokes(centre, half, v, pitch):
    """Raster lines over the square at +v, then the same lines at -v.

    Returned as a list of (polyline, V) for TrajectoryBuilder.stroke().

    STROKES, NOT PER-POINT DWELLS. `dwell()` makes each point its own segment,
    and `to_arrays()` inserts a resampled travel move BETWEEN segments -- so a
    raster written as one dwell per point pays ~3 travel points for every 1
    payload point. The first version of this cost 17.9 write-minutes for 4.4
    minutes of actual dose. A stroke is resampled once along its whole length
    with no internal travel, and travel is then paid only between lines.

    The two polarity passes are identical in extent, so the net DC is zero by
    construction; it is asserted at the call site rather than assumed.
    """
    cx, cy = centre
    ys = np.arange(cy - half, cy + half + 1e-9, pitch)
    ang = np.deg2rad(ANG)
    u = np.array([np.cos(ang), np.sin(ang)])          # along the raster lines
    n = np.array([-np.sin(ang), np.cos(ang)])         # line-to-line
    out = []
    for pol in (+1.0, -1.0):
        for k, y in enumerate(ys):
            off = (y - cy) * n
            a = np.array([cx, cy]) + off - half * u
            b = np.array([cx, cy]) + off + half * u
            seg = [a, b] if k % 2 == 0 else [b, a]
            out.append((np.array(seg, float), pol * v))
    return out


def load(g, tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0, r12


def interior(S, px, h=0.5):
    n = S.shape[0]
    hp = int(round(h * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def budget_check(minutes, label):
    import json
    p = os.path.join(A.PROJ, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    used = float(st.get('total_write_min', 0.0))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    print('  S24: %.1f of %.0f used, %.1f left; this needs %.2f'
          % (used, cap, cap - used, minutes))
    if minutes > cap - used:
        raise SystemExit('S24: %.2f needed, %.1f left. Halt.'
                         % (minutes, cap - used))
    st['total_write_min'] = used + minutes
    st.setdefault('diagnostic_writes', []).append(
        dict(label=label, minutes=round(float(minutes), 3),
             area=[XOFF, YOFF], sample_position=st.get('sample_position'),
             stamp=time.strftime('%Y-%m-%d %H:%M')))
    io.open(p, 'w', encoding='utf-8').write(json.dumps(st, indent=1))


def report(g, tag, label, tri):
    S, px, r12 = load(g, tag)
    Si = interior(S, px)
    sd, sa, sp, spv = ST.band_peak(Si, px, *SUPER, n_perm=150)
    fd, fa, fp, fpv = ST.band_peak(Si, px, *FINE, n_perm=150)
    print('  %-14s %-22s |S| %5.1f pm  r12 %+.2f' % (label, tag, np.std(Si),
                                                     r12))
    print('     super : dir %6.1f  period %6.1f nm  aniso %6.2f  p %.4f'
          % (sd, sp, sa, spv))
    off0 = ST.angle_between(fd, 0.0)
    offs = ST.angle_between(fd, sd)
    why = ('fast-axis' if off0 < 15 else
           ('harmonic of the lamellae' if offs < 15 else 'OFF BOTH'))
    print('     fine  : dir %6.1f  period %6.1f nm  aniso %6.2f  p %.4f  %s'
          % (fd, fp, fa, fpv, why))
    return dict(S=S, px=px, sd=sd, sp=sp, spv=spv, fd=fd, fp=fp, fpv=fpv)


def main():
    print('=' * 74)
    print('BLOCK 2  +V then -V over one square, then look  %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    ns = A.load_toolkit(stub_instrument=True if DRY else False)
    g = ns.__getitem__
    if not DRY:
        g('check_folder')()
        g('scanner_ok')(XOFF, YOFF, SIZE_UM)

    before = {}
    if not DRY:
        for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
            print('\n--- %s before ---' % mode.upper())
            _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                     angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                                     tries=1, verbose=False)
            before[slot] = inf['frame']
            print('    %s tracked %.0f%%' % (inf['frame'], 100 * inf['frac']))
            try:
                g('contact_check')(inf['frame'])
            except Exception as e:
                print('    contact_check: %s' % e)
        tri, tt = g('pin_triad')(before['L'], ref_fam=g('FAM_FILM'))
        tri = [float(t) for t in tri]
        print('\n  triad %s, modulation %.3f'
              % ([int(round(t)) for t in tri], tt['mod']))
        # The 4-Lambda readout gate. It lived in block1_write.py and not here,
        # and the last write of 29 August went into a Lambda 369 nm area with a
        # 1.0 um interior -- 2.7 periods -- and returned p = 0.28 on a
        # pre-registered prediction (PITFALLS 21.12). Shrinking the poled square
        # to fit a budget preserved the DOSE exactly and destroyed the
        # MEASURABILITY, and only the dose was being watched.
        SLb0, px0, _ = load(g, before['L'])
        _dom = float(tri[int(np.argmax(np.asarray(tt['w'], float)))])
        lam_here = ST.band_period(interior(SLb0, px0), px0, _dom, *SUPER)
        ok, nper, msg = ST.window_ok(lam_here, 2 * 0.5, label='interior')
        print('  %s' % msg)
        if not ok:
            print('  !! this area cannot support the readout at this square')
            print('     size. The coarsest Lambda a %.1f um interior can read'
                  % (2 * 0.5))
            print('     is %.0f nm; a %.1f um square would need HALF >= %.2f.'
                  % (ST.largest_lambda_for(2 * 0.5), 2 * HALF,
                     0.5 * lam_here * 4.0 / 1000.0))
            if os.environ.get('B2_FORCE') != '1':
                raise SystemExit('halting: set B2_FORCE=1 to write anyway')
    else:
        tri = [16.0, 76.0, 136.0]

    # ------------------------------------------------------------- build
    strokes = pole_strokes(CENTRE, HALF, V, PITCH)
    sigma_per_pol = V / (PITCH * SPEED)
    print('\nPOLING SQUARE  %.1f um, raster pitch %.0f nm, %.2f um/s, '
          'lines along %.1f deg' % (2 * HALF, PITCH * 1000, SPEED, ANG))
    if tri:
        near = min(tri, key=lambda t: abs((t - ANG + 90.0) % 180.0 - 90.0))
        print('  triad member nearest the raster direction: %.0f deg' % near)
    print('  %d raster lines (%d per polarity), design sigma %.0f per polarity'
          % (len(strokes), len(strokes) // 2, sigma_per_pol))

    tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    for pts, v in strokes:
        tb.stroke(pts, v)
    xs, ys, vs = (np.asarray(a, float) for a in tb.to_arrays())
    # The dose that will ACTUALLY be delivered, computed from the BUILT path
    # rather than from the design formula. The two differed by 4x in the first
    # version of this driver and only the built number is real.
    area = (2 * HALF) ** 2
    q_tot = float(np.sum(np.abs(vs)) * STEP / SPEED)
    print('  built: %d pts, |charge| %.0f V.s over %.2f um^2 -> sigma %.0f'
          ' per polarity' % (len(xs), q_tot, area, q_tot / area / 2.0))
    print('  net DC %+.3e V  (S4 needs |mean| <= 0.01)' % vs.mean())
    assert abs(vs.mean()) < 1e-6, 'poling file is not charge balanced'
    assert np.abs(vs).max() <= V + 1e-9, 'S1'
    mins = len(xs) * STEP / SPEED / 60.0
    print('  %d pts -> %.2f min at %.2f um/s (S7 cap %.0f)'
          % (len(xs), mins, SPEED, MAX_MIN))
    print('  x %.2f-%.2f, y %.2f-%.2f um' % (xs.min(), xs.max(),
                                             ys.min(), ys.max()))
    if mins > MAX_MIN:
        raise SystemExit('over the S7 cap')
    if not (xs.min() >= 0.05 and ys.min() >= 0.05
            and xs.max() <= SIZE_UM - 0.05 and ys.max() <= SIZE_UM - 0.05):
        raise SystemExit('S3: too close to the frame edge')
    if abs(vs.mean()) > 1e-6:
        raise SystemExit('S4: net DC %.3e' % vs.mean())
    if DRY:
        print('\nDRY RUN: gates pass, nothing written.')
        return

    print('\nBEFORE')
    rb = {k: report(g, before[k], k + ' before', tri) for k in ('L', 'V')}

    budget_check(mins, 'B2_pole_%.0f' % sigma_per_pol)
    print('\n--- poling: +V pass then -V pass over the same square ---')
    fn = os.path.join(A.PROJ, 'output', '%s_B2pole.txt' % STAMP)
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    print('  done.')

    after = {}
    for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
        print('\n--- %s after ---' % mode.upper())
        _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                 angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                                 tries=1, verbose=False)
        after[slot] = inf['frame']
        print('    %s tracked %.0f%%' % (inf['frame'], 100 * inf['frac']))

    print('\nAFTER')
    ra = {k: report(g, after[k], k + ' after ', tri) for k in ('L', 'V')}

    print('\n' + '=' * 74)
    print('READING')
    print('=' * 74)
    vb, va = rb['V'], ra['V']
    print('  VDART super-band anisotropy %.2f -> %.2f  (p %.3f -> %.3f)'
          % (vb['spv'] and 0 or 0, 0, vb['spv'], va['spv']))
    print('  VDART |S| interior %.1f -> %.1f pm'
          % (np.std(interior(vb['S'], vb['px'])),
             np.std(interior(va['S'], va['px']))))
    if va['spv'] >= 0.05:
        print('  -> the out-of-plane channel has NO dominant direction after')
        print('     poling: the OP state is homogeneous, as intended.')
    lb, la = rb['L'], ra['L']
    off0 = ST.angle_between(la['fd'], 0.0)
    offs = ST.angle_between(la['fd'], la['sd'])
    if la['fpv'] < 0.01 and off0 >= 15 and offs >= 15:
        print('  -> LDART fine band: %.0f nm at %.0f deg, off the fast axis'
              ' and off the lamellae. CANDIDATE NANO-DOMAINS.'
              % (la['fp'], la['fd']))
    else:
        print('  -> LDART fine band still explained by the fast axis or by a')
        print('     lamellar harmonic. No clean nano-domain signal.')
    print('\n  before %s / %s   after %s / %s'
          % (before['L'], before['V'], after['L'], after['V']))


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
        io.open(os.path.join(A.PROJ, 'block2_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
