# -*- coding: utf-8 -*-
"""block3_raster.py -- DC and AC trajectory lithography, one driver.

The manuscript needs three write modes compared on the same film with the same
readout, and the campaign has never had them in one place:

  MODE=dc     a +V pass over the square followed by a -V pass over the same
              square. Each pass is unipolar; the two are separated in TIME, so
              the net SPATIAL charge pattern is uniform and there is no
              periodicity to imprint (this is the M26 geometry).

  MODE=ac     ONE pass in which the bias alternates sign every `AC_N` points
              along the path. The spatial sign period is 2*AC_N*STEP, chosen
              far below Lambda, so again there is no spatial pattern at the
              domain scale -- but now the field never sustains one sign for
              longer than a few tens of nanometres.

  MODE=uni    a single unipolar pass. NOT charge balanced, so it is refused
              unless FORCE_DC=1; present only to make the comparison explicit.

Why dc vs ac is the experiment. Both deliver the same |E| and the same areal
dose. They differ only in how long the field holds one sign at a point. If the
in-plane alignment couples to |E| -- electrostrictive, even in E, which is what
[[M13]]/[[M14]]'s polarity independence implies -- then AC should align exactly
like DC. If it needs a sustained unipolar field, AC should not align at all.

SCAN SPEED. sigma = V / (pitch * speed) for a continuous raster, so speed and
dose are confounded unless the pitch compensates. SPEED=1.0 with PITCH=0.015
delivers the same sigma as SPEED=0.5 with PITCH=0.03. That is the only honest
way to vary speed here.

  B3_MODE=dc|ac|uni   B3_ANG=60   B3_X=0 B3_Y=0   B3_HALF=0.70
  B3_PITCH=0.03       B3_SPEED=0.5   B3_V=10   B3_ACN=2
  B3_BEFORE_L=... B3_BEFORE_V=...   (re-use frames, e.g. for a second write
                                     on an already-aligned area)
  B3_DRY=1
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
STEP = 0.02
MAX_MIN = 26.0

MODE = os.environ.get('B3_MODE', 'dc').lower()
ANG = float(os.environ.get('B3_ANG', '0'))
XOFF = float(os.environ.get('B3_X', '0'))
YOFF = float(os.environ.get('B3_Y', '0'))
HALF = float(os.environ.get('B3_HALF', '0.80'))
# 1.6 um square, not 1.4. The readout window must hold 4 lamellar periods
# (PITFALLS 19.15) and the areas screened here run Lambda 215-295 nm, so the
# window has to be >= 1.2 um. A 1.2 um interior needs a 1.6 um square to keep
# 0.2 um of margin from the written edge. The earlier 1.4 um square left only a
# 1.0 um interior = 3.7 Lambda, which is below the floor and halted the queue.
IN_HALF = float(os.environ.get('B3_INHALF', '0.60'))    # 1.2 um readout window
COR = float(os.environ.get('B3_COR', '0.42'))           # corner control patch
PITCH = float(os.environ.get('B3_PITCH', '0.03'))
SPEED = float(os.environ.get('B3_SPEED', '0.5'))
V = float(os.environ.get('B3_V', '10'))
ACN = int(os.environ.get('B3_ACN', '2'))
BEF_L = os.environ.get('B3_BEFORE_L', '')
BEF_V = os.environ.get('B3_BEFORE_V', '')
LABEL = os.environ.get('B3_LABEL', '')
DRY = os.environ.get('B3_DRY', '') == '1'
STAMP = time.strftime('%y%m%d_%H%M')
CENTRE = (SIZE_UM / 2.0, SIZE_UM / 2.0)
SUPER = (150.0, 500.0)
FINE = (18.0, 90.0)


def raster_lines(centre, half, pitch, ang):
    """Serpentine line endpoints for a square rotated to `ang`."""
    cx, cy = centre
    a = np.deg2rad(ang)
    u = np.array([np.cos(a), np.sin(a)])
    n = np.array([-np.sin(a), np.cos(a)])
    out = []
    for k, t in enumerate(np.arange(-half, half + 1e-9, pitch)):
        o = np.array([cx, cy]) + t * n
        p, q = o - half * u, o + half * u
        out.append((p, q) if k % 2 == 0 else (q, p))
    return out


def build_strokes(mode):
    """(list of (polyline, V), description). Charge balance asserted by caller."""
    lines = raster_lines(CENTRE, HALF, PITCH, ANG)
    if mode == 'dc':
        return ([(np.array([p, q]), pol * V)
                 for pol in (+1.0, -1.0) for (p, q) in lines],
                '+V pass then -V pass; sign held for a whole %.1f um line'
                % (2 * HALF))
    if mode == 'uni':
        return ([(np.array([p, q]), V) for (p, q) in lines],
                'single unipolar pass -- NOT charge balanced')
    if mode == 'ac':
        # TWO passes over the same lines, so the geometry, the point count and
        # the total |charge| match MODE=dc exactly. The ONLY difference is that
        # the sign flips every ACN points along the path instead of being held
        # for a whole line. That is the controlled comparison the manuscript
        # needs; anything else confounds "AC vs DC" with dose.
        #
        # stroke() accepts a PER-POINT voltage array, so each line is one
        # stroke with an alternating V. Splitting it into segments instead
        # would duplicate shared endpoints and insert travel moves between
        # every chunk (PITFALLS 21.10), and would not balance.
        segs = []
        for _pass in (0, 1):
            for (p, q) in lines:
                L = float(np.hypot(*(q - p)))
                u = (q - p) / max(L, 1e-12)
                # Points at EXACTLY STEP spacing. resample_constant_step()
                # interpolates the per-point V array, and interpolating a
                # +-V square wave at a different spacing averages it toward
                # zero -- the first version of this lost 24 % of the dose that
                # way and would have compared AC at sigma 517 against DC at
                # 681 while claiming they were matched.
                nfull = int(np.floor(L / STEP))
                nch = (nfull // ACN) // 2 * 2      # whole PAIRS of chunks
                if nch < 2:
                    continue
                npts = nch * ACN
                pts = p[None, :] + (np.arange(npts) * STEP)[:, None] * u[None, :]
                sgn = np.where((np.arange(npts) // ACN) % 2 == 0, 1.0, -1.0)
                segs.append((pts, sgn * V))
        return (segs,
                'TWO passes, sign flips every %d points = %.0f nm; spatial '
                'sign period %.0f nm (dose matched to MODE=dc)'
                % (ACN, ACN * STEP * 1000, 2 * ACN * STEP * 1000))
    raise SystemExit('unknown MODE %r' % mode)


def load(g, tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0, r12


def interior(S, px, h=IN_HALF):
    n = S.shape[0]
    hp = int(round(h * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def corners(S, px, size=COR):
    n = S.shape[0]
    k = int(round(size * 1000.0 / px))
    return [S[0:k, 0:k], S[0:k, n - k:n], S[n - k:n, 0:k], S[n - k:n, n - k:n]]


def budget_check(minutes, label):
    import json
    p = os.path.join(A.PROJ, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    used = float(st.get('total_write_min', 0.0))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    print('  S24: %.1f of %.0f used, %.1f left; this needs %.2f'
          % (used, cap, cap - used, minutes))
    if minutes > cap - used:
        raise SystemExit('S24 exhausted')
    st['total_write_min'] = used + minutes
    st.setdefault('diagnostic_writes', []).append(
        dict(label=label, minutes=round(float(minutes), 3), area=[XOFF, YOFF],
             sample_position=st.get('sample_position'),
             stamp=time.strftime('%Y-%m-%d %H:%M')))
    io.open(p, 'w', encoding='utf-8').write(json.dumps(st, indent=1))


def report(g, tag, label, tri):
    S, px, r12 = load(g, tag)
    Si = interior(S, px)
    sd, sa, sp, spv = ST.band_peak(Si, px, *SUPER, n_perm=200)
    near = min(tri, key=lambda t: ST.angle_between(sd, t))
    print('  %-12s %-22s |S| %5.1f  r12 %+.2f' % (label, tag, np.std(Si), r12))
    print('     super: %6.1f deg  %6.1f nm  aniso %5.2f  p %.4f  | member %3.0f'
          ' (%4.1f off) | raster %4.1f off'
          % (sd, sp, sa, spv, near, ST.angle_between(sd, near),
             ST.angle_between(sd, ANG)))
    return dict(S=S, px=px, dir=sd, per=sp, aniso=sa, p=spv, near=near)


def main():
    print('=' * 78)
    print('BLOCK 3  %s raster  %s  %s'
          % (MODE.upper(), LABEL, time.strftime('%Y-%m-%d %H:%M')))
    print('=' * 78)
    ns = A.load_toolkit(stub_instrument=True if DRY else False)
    g = ns.__getitem__
    if not DRY:
        g('check_folder')()
        g('scanner_ok')(XOFF, YOFF, SIZE_UM)

    tri = [16.0, 76.0, 136.0]
    bl, bv = BEF_L, BEF_V
    if not DRY:
        if not bl or not bv:
            for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
                _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX,
                                         rate=RATE, angle_deg=0.0,
                                         xoff_um=XOFF, yoff_um=YOFF, tries=1,
                                         verbose=False)
                print('  before %s -> %s (%.0f%% tracked)'
                      % (mode.upper(), inf['frame'], 100 * inf['frac']))
                try:
                    g('contact_check')(inf['frame'])
                except Exception as e:
                    print('    contact_check: %s' % e)
                if slot == 'L':
                    bl = inf['frame']
                else:
                    bv = inf['frame']
        triad, tt = g('pin_triad')(bl, ref_fam=g('FAM_FILM'))
        tri = [float(t) for t in triad]
        dom = float(tri[int(np.argmax(np.asarray(tt['w'], float)))])
        print('\n  triad %s, dominant %.0f deg, modulation %.3f'
              % ([int(round(t)) for t in tri], dom, tt['mod']))
        if float(tt['mod']) < 0.10:
            raise SystemExit('S16: modulation %.3f too low' % tt['mod'])
        # TOPOGRAPHY GATE (PITFALLS 21.13). The lateral signal is cantilever
        # torsion, so a step edge injects a DIRECTIONAL in-plane signal that no
        # lateral-channel gate can see. Bad area: roughness 3.28 nm, p2p
        # 19.9 nm. Good areas: 0.39-0.60 and 1.8-3.6.
        _d0, _h0 = g('ibw')(bl)
        _Z = np.nan_to_num(np.asarray(_d0[0], float) * 1e9)
        _Z = _Z - np.nanmedian(_Z)
        _yy, _xx = np.mgrid[0:_Z.shape[0], 0:_Z.shape[1]]
        _M = np.c_[_xx.ravel(), _yy.ravel(), np.ones(_Z.size)]
        _c, _, _, _ = np.linalg.lstsq(_M, _Z.ravel(), rcond=None)
        _F = _Z - (_c[0] * _xx + _c[1] * _yy + _c[2])
        _rough = float(np.std(_F))
        _p2p = float(np.percentile(_F, 99) - np.percentile(_F, 1))
        print('  topography: roughness %.2f nm, 1-99%% range %.2f nm'
              % (_rough, _p2p))
        if (_rough > 1.0 or _p2p > 5.0) and os.environ.get('B3_FORCE') != '1':
            raise SystemExit('topography gate: roughness %.2f nm / p2p %.2f nm '
                             '(limits 1.0 / 5.0). Step edge or debris; move.'
                             % (_rough, _p2p))
        SLb, pxl, _ = load(g, bl)
        # Lambda is a property of the FILM and must be measured where it can
        # be: on the full 2.5 um frame. Measuring it on the 1.0 um interior
        # returns NaN, because the 150-500 nm band is a ~127-pixel annulus
        # there and band_period's +-12 deg direction mask cuts that below its
        # 8-pixel minimum. The 4-Lambda test is then applied to the WINDOW,
        # which is the thing whose size is actually in question.
        lam = ST.band_period(SLb, pxl, dom, *SUPER)
        if lam != lam:
            lam = ST.band_peak(SLb, pxl, *SUPER, n_perm=60)[2]
        ok, nper, msg = ST.window_ok(lam, 2 * IN_HALF, label='interior')
        print('  %s' % msg)
        if not ok and os.environ.get('B3_FORCE') != '1':
            raise SystemExit('halting on the 4-Lambda gate; B3_FORCE=1 to '
                             'override')
        near_raster = min(tri, key=lambda t: ST.angle_between(t, ANG))
        print('  raster along %.1f deg; nearest triad member %.0f deg'
              % (ANG, near_raster))
        print('  PREDICTION (M26): the director goes to %.0f deg' % near_raster)

    # ------------------------------------------------------------- build
    strokes, desc = build_strokes(MODE)
    sigma_design = V / (PITCH * SPEED)
    print('\n%s SQUARE  %.1f um, pitch %.0f nm, %.2f um/s, along %.1f deg'
          % (MODE.upper(), 2 * HALF, PITCH * 1000, SPEED, ANG))
    print('  %s' % desc)
    tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    for pts, v in strokes:
        tb.stroke(pts, v)
    xs, ys, vs = (np.asarray(a, float) for a in tb.to_arrays())
    area = (2 * HALF) ** 2
    q_tot = float(np.sum(np.abs(vs)) * STEP / SPEED)
    npass = 1.0 if MODE == 'uni' else 2.0   # dc and ac both make two passes
    print('  built %d pts, |charge| %.0f V.s over %.2f um^2 -> sigma %.0f'
          ' (design %.0f per pass)'
          % (len(xs), q_tot, area, q_tot / area / npass, sigma_design))
    print('  net DC %+.3e V  |V|max %.1f' % (vs.mean(), np.abs(vs).max()))
    mins = len(xs) * STEP / SPEED / 60.0
    print('  %.2f min at %.2f um/s (S7 cap %.0f)' % (mins, SPEED, MAX_MIN))
    print('  x %.2f-%.2f  y %.2f-%.2f um' % (xs.min(), xs.max(), ys.min(),
                                             ys.max()))
    if MODE != 'uni':
        assert abs(vs.mean()) < 1e-6, 'S4: net DC %.3e' % vs.mean()
    elif os.environ.get('FORCE_DC') != '1':
        raise SystemExit('MODE=uni is not charge balanced; FORCE_DC=1 to allow')
    assert np.abs(vs).max() <= V + 1e-9, 'S1'
    if mins > MAX_MIN:
        raise SystemExit('over the S7 cap')
    if not (xs.min() >= 0.05 and ys.min() >= 0.05
            and xs.max() <= SIZE_UM - 0.05 and ys.max() <= SIZE_UM - 0.05):
        raise SystemExit('S3: path too close to the edge')
    if DRY:
        print('\nDRY RUN: gates pass, nothing written.')
        return

    print('\nBEFORE')
    rb = report(g, bl, 'L before', tri)

    budget_check(mins, 'B3_%s_%.0fdeg_%s' % (MODE, ANG, LABEL or ''))
    print('\n--- writing ---')
    fn = os.path.join(A.PROJ, 'output', '%s_B3%s.txt' % (STAMP, MODE))
    g('goto_ldart')()
    g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
    print('  done.')

    after = {}
    for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
        _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                 angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                                 tries=1, verbose=False)
        after[slot] = inf['frame']
        print('  after %s -> %s (%.0f%% tracked)'
              % (mode.upper(), inf['frame'], 100 * inf['frac']))

    print('\nAFTER')
    ra = report(g, after['L'], 'L after', tri)

    print('\n' + '=' * 78)
    near_raster = min(tri, key=lambda t: ST.angle_between(t, ANG))
    moved = ST.angle_between(ra['dir'], rb['dir'])
    print('  director %.1f -> %.1f deg (moved %.1f)'
          % (rb['dir'], ra['dir'], moved))
    print('  raster %.1f deg, nearest member %.0f deg, |after - that member|'
          ' = %.1f deg' % (ANG, near_raster,
                           ST.angle_between(ra['dir'], near_raster)))
    if ra['p'] >= 0.01:
        print('  -> after-state has NO significant direction (p %.3f).'
              % ra['p'])
    elif ST.angle_between(ra['dir'], near_raster) <= 15.0:
        print('  -> ALIGNED to the member nearest the raster. Rule holds.')
    else:
        print('  -> did NOT go to the member nearest the raster.')
    print('\n  before %s / %s   after %s / %s'
          % (bl, bv, after['L'], after['V']))


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
        io.open(os.path.join(A.PROJ, 'block3_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
