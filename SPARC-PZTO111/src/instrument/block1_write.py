# -*- coding: utf-8 -*-
"""block1_write.py -- one panel, both channels, before and after.

THE QUESTION. Block 0 established, on virgin film at this area:
  * a strong IN-PLANE modulation, 219-224 nm along the 76 deg triad member;
  * NO out-of-plane modulation at that same wavevector, matched-filter
    amplitude 7.3 pm against a 5 pm detection limit and p = 0.15;
  * no independent nano-domain periodicity -- the only short-period feature is
    the second harmonic of the super-domain lamellae, at the same director.

T3's selection term is -int(P_z E_z), which is non-zero only if the film HAS a
P_z modulation at Q. On virgin film it does not, to 5 pm. The operator's
observation that "nano domains are not visible until you write/align the IP
super domains" suggests the modulation is CREATED by the write rather than
being a pre-existing property the template couples to.

That is a different mechanism from the one in the manuscript, and this run
tests it directly: one commensurate panel, and the same two measurements
after.

PRE-REGISTERED PREDICTIONS (S27), written before the write:

  A. If a P_z modulation at Q APPEARS after writing (matched-filter amplitude
     rises above the 5 pm limit at the COMMANDED director), then the template
     creates the very modulation it is said to couple to. Selection would be
     self-reinforcing rather than a coupling to a pre-existing order, and the
     manuscript's section 6.2 needs rewriting.
  B. If the in-plane director rotates to the commanded member but P_z stays
     flat, the selection term cannot be -int(P_z E_z) on this film, and the
     mechanism is purely in-plane.
  C. If a NEW short-period structure appears at a director unrelated to the
     super-domain harmonic, those are the operator's nano-domains, and their
     period and angle are new measurements.
  D. If nothing changes, the write did not take -- a probe/chain failure, not
     a physics result. The control for this is the surround, which must also
     not change.

Geometry: 2.5 um frame, 512 px, 2.0 Hz, ONE 1.2 um panel centred, surround
beyond 1.5 um as the in-frame control.
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
import template_lib as T
import scale_tools as ST

SIZE_UM = 2.5
PX = 512
RATE = 2.0
HALF = 0.60                      # 1.2 um panel
V = 10.0
STEP = 0.02
SPEED = 0.5
CHG_MAX = 0.5 * 40.0             # C21 half-limit, V.s per site
MAX_MIN = 26.0                   # S7
XOFF = float(os.environ.get('B1_X', '0.0'))
YOFF = float(os.environ.get('B1_Y', '0.0'))
SIGMA = float(os.environ.get('B1_SIGMA', '120'))
LAM_NM = float(os.environ.get('B1_LAM', '219'))
WANT = os.environ.get('B1_WANT', '')          # blank -> pick 60 deg away
BEFORE_L = os.environ.get('B1_BEFORE_L', 'PZTO_LDART_0000.ibw')
BEFORE_V = os.environ.get('B1_BEFORE_V', 'PZTO_VDART_0000.ibw')
DRY = os.environ.get('B1_DRY', '') == '1'
STAMP = time.strftime('%y%m%d_%H%M')
CENTRE = (SIZE_UM / 2.0, SIZE_UM / 2.0)

SUPER = (150.0, 500.0)
HARM = (90.0, 150.0)
FINE = (18.0, 90.0)


def budget_check(minutes, label):
    import json
    p = os.path.join(A.PROJ, 'campaign_state.json')
    st = json.load(io.open(p, encoding='utf-8'))
    used = float(st.get('total_write_min', 0.0))
    cap = float(A.MAX_TOTAL_WRITE_MIN)
    left = cap - used
    print('  S24: %.1f of %.0f used, %.1f left; this write needs %.2f'
          % (used, cap, left, minutes))
    if minutes > left:
        raise SystemExit('S24: %.2f min needed, %.1f left. Halt.'
                         % (minutes, left))
    st['total_write_min'] = used + minutes
    st.setdefault('diagnostic_writes', []).append(
        dict(label=label, minutes=round(float(minutes), 3),
             area=[XOFF, YOFF], sample_position=st.get('sample_position'),
             stamp=time.strftime('%Y-%m-%d %H:%M')))
    io.open(p, 'w', encoding='utf-8').write(
        __import__('json').dumps(st, indent=1))
    return left - minutes


def load(g, tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0, r12


def crop(S, px, half_um):
    """Central square of half-width `half_um`, in pixels."""
    n = S.shape[0]
    hp = int(round(half_um * 1000.0 / px))
    c = n // 2
    return S[max(0, c - hp):c + hp, max(0, c - hp):c + hp]


def ring(S, px, inner_um):
    """Everything outside `inner_um` half-width, as a masked copy (surround)."""
    n = S.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    r = np.maximum(np.abs(xx - c), np.abs(yy - c)) * px / 1000.0
    out = S.copy()
    out[r < inner_um] = 0.0
    return out


def scan_bands(S, px, label, tri, n_perm=120):
    print('  %s' % label)
    print('    %-14s %7s %9s %8s %8s  %s'
          % ('band (nm)', 'dir', 'period', 'aniso', 'p', 'note'))
    got = {}
    for nm, (lo, hi) in (('super', SUPER), ('harm', HARM), ('fine', FINE)):
        dd, an, per, pv = ST.band_peak(S, px, lo, hi, n_perm=n_perm)
        got[nm] = (dd, an, per, pv)
        off0 = ST.angle_between(dd, 0.0) if dd == dd else float('nan')
        near = (min(tri, key=lambda t: ST.angle_between(dd, t))
                if dd == dd else float('nan'))
        note = ('fast-axis artefact' if off0 < 12 else
                'near triad %.0f (%.0f off)' % (near, ST.angle_between(dd, near)))
        print('    %-14s %7.1f %9.1f %8.2f %8.3f  %s'
              % ('%.0f-%.0f' % (lo, hi), dd, per, an, pv, note))
    return got


def main():
    print('=' * 74)
    print('BLOCK 1  one commensurate panel, both channels  %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    ns = A.load_toolkit(stub_instrument=True if DRY else False)
    g = ns.__getitem__
    if not DRY:
        g('check_folder')()
        g('scanner_ok')(XOFF, YOFF, SIZE_UM)

    # ---------------------------------------------------- the before state
    # Blank BEFORE_* means "this is a fresh area": acquire the pair here.
    # Both frames go through tune_here at the SAME settings the after-frames
    # will use, because M12 cost a whole iteration to a re-tune applied to one
    # half of a before/after pair and not the other.
    bl, bv = BEFORE_L, BEFORE_V
    if not bl or not bv:
        for mode, slot in (('ldart', 'L'), ('vdart', 'V')):
            print('\n--- %s before ---' % mode.upper())
            _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                     angle_deg=0.0, xoff_um=XOFF,
                                     yoff_um=YOFF, tries=1, verbose=False)
            print('    %s  tracked %.0f%%, offset %.1f kHz'
                  % (inf['frame'], 100 * inf['frac'],
                     (inf['offset_hz'] or float('nan')) / 1e3))
            try:
                g('contact_check')(inf['frame'])
            except Exception as e:
                print('    contact_check: %s' % e)
            if slot == 'L':
                bl = inf['frame']
            else:
                bv = inf['frame']
    SLb, pxl, r12l = load(g, bl)
    SVb, pxv, r12v = load(g, bv)
    tri, tt = g('pin_triad')(bl, ref_fam=g('FAM_FILM'))
    tri = [float(t) for t in tri]
    w = np.asarray(tt['w'], float)
    dom = float(tri[int(np.argmax(w))])
    print('\nBEFORE  %s / %s' % (BEFORE_L, BEFORE_V))
    print('  triad %s, dominant %.0f deg, modulation %.3f'
          % ([int(round(t)) for t in tri], dom, tt['mod']))
    print('  |S| LDART %.1f pm (r12 %+.2f) | VDART %.1f pm (r12 %+.2f)'
          % (np.std(SLb), r12l, np.std(SVb), r12v))

    # S16: there must be texture to rotate. On a queue this gate is what stops
    # a bad area consuming a write and 9 minutes of after-frames as well as the
    # before-frames it has already cost.
    if float(tt['mod']) < 0.10:
        raise SystemExit('S16: modulation %.3f below 0.10 -- nothing to rotate '
                         'at this area. Skipping before any write.'
                         % float(tt['mod']))

    # S22: command a member 60 deg from the incumbent, never the one it is on
    if WANT == 'midpoint':
        # Halfway between two triad members: the only command for which
        # "the film obeyed" and "we are reading back what we wrote" predict
        # DIFFERENT answers. Pick the midpoint that is furthest from the
        # incumbent, and never one within 25 deg of the fast scan axis, since
        # structure there is confounded with the scan artefact (PITFALLS 21.6).
        mids = [(t + 30.0) % 180.0 for t in tri]
        ok = [m for m in mids if ST.angle_between(m, 0.0) >= 25.0]
        if not ok:
            ok = mids
        want = float(max(ok, key=lambda m: ST.angle_between(m, dom)))
        print('  midpoints available %s -> commanding %.1f deg'
              % (['%.0f' % m for m in mids], want))
    elif WANT:
        want = float(WANT)
    else:
        cand = [t for t in tri if ST.angle_between(t, dom) > 45.0]
        # of the two, take the one nearest 0-30 deg: FINDINGS M23 says the
        # ~135 deg member fails 4 times in 9, and the first write with a new
        # probe must not confound "the probe cannot write" with "this member
        # is hard". The hard member is Block 4's job, with a baseline in hand.
        want = float(min(cand, key=lambda t: min(t, 180.0 - t)))
    if os.environ.get('B1_OFFTRIAD') == '1':
        # DELIBERATE S22 RELAXATION, for the one experiment that tests whether
        # the readout is measuring the FILM or the TEMPLATE.
        #
        # Every director in this campaign has been commanded TO a triad member,
        # so "the film went where it was told" and "we are reading back the
        # pattern we wrote" predict the same answer and have never been
        # separated. Commanding a direction BETWEEN two members separates them:
        #   lands near the commanded angle  -> we are reading the imprint
        #   snaps to a triad member         -> the film chose
        # The midpoint is only ~30 deg from the incumbent, which S22's 45 deg
        # rule forbids, so the rule is relaxed here on purpose and on the
        # record (PITFALLS 13). The 15 deg hit criterion is unchanged and the
        # two hypotheses are 30 deg apart, so the test still has room.
        nearest = min(tri, key=lambda t: ST.angle_between(want, t))
        assert ST.angle_between(want, nearest) > 20.0, \
            'B1_OFFTRIAD but %.1f is only %.1f deg from member %.1f' \
            % (want, ST.angle_between(want, nearest), nearest)
        assert ST.angle_between(want, dom) > 25.0, 'commanded too near the incumbent'
        print('  OFF-TRIAD DIAGNOSTIC: %.1f deg is %.1f deg from the nearest'
              ' member (%.0f) and %.1f deg from the incumbent'
              % (want, ST.angle_between(want, nearest), nearest,
                 ST.angle_between(want, dom)))
    else:
        assert ST.angle_between(want, dom) > 45.0, 'S22: commanded the incumbent'
    print('  commanding %.1f deg (incumbent %.0f, move %.0f deg)'
          % (want, dom, ST.angle_between(want, dom)))

    # ------------------------------------------------------------- build
    # Lambda from THIS area's own frame unless the caller pins it. Geometry
    # solved from a Lambda measured somewhere else is PITFALLS rule 4.
    lam_meas = ST.band_period(SLb, pxl, dom, *SUPER)
    if os.environ.get('B1_LAM'):
        lam_nm = LAM_NM
        print('  Lambda pinned by caller: %.0f nm (this area measures %.0f)'
              % (lam_nm, lam_meas))
    else:
        lam_nm = lam_meas
        print('  Lambda measured here: %.0f nm' % lam_nm)
    if not (120.0 <= lam_nm <= 500.0):
        raise SystemExit('Lambda %.0f nm outside the buildable window' % lam_nm)
    # How incommensurate is this template, in units the READOUT can resolve?
    # A 1.0 um interior window resolves dq = 1/1.0 um. The first attempt at an
    # incommensurate control used 328 nm against a 253 nm film -- dq = 0.90,
    # INSIDE one resolution element, so it could not have decided anything.
    dq = abs(1000.0 / lam_nm - 1000.0 / lam_meas)
    print('  q_template/Q_film = %.3f;  dq = %.2f /um against a window'
          ' resolution of %.2f /um  -> %s'
          % ((lam_meas / lam_nm), dq, 1.0 / 1.0,
             'resolvable' if dq * 1.0 > 1.0 else
             'NOT RESOLVABLE -- this cannot test commensurability'))
    nper = 1.0 / (lam_nm / 1000.0)
    if 1.0 * nper < 4.0:
        print('  !! a 1.0 um interior window holds only %.1f Lambda' % nper)
    lam_um = lam_nm / 1000.0
    sites = T.parallel(CENTRE, HALF, lam_um, want, V)
    smax = CHG_MAX * len(sites) * V / ((2 * HALF) ** 2)
    sig_t = min(SIGMA, 0.98 * smax)
    dwell = T.dwell_for_sigma(sig_t, sites, V, HALF)
    pn = max(1, int(round(dwell * SPEED / STEP)))
    dwell = pn * STEP / SPEED
    sig, q_site = T.dose(sites, V, dwell, HALF)
    print('\nPANEL  parallel lattice, %.1f um, Lambda %.0f nm, sp %.0f nm'
          % (2 * HALF, lam_nm, lam_nm / 2))
    print('  %d sites, %d pulses/site, dwell %.2f s -> sigma %.0f V.s/um^2, '
          '%.2f V.s/site (limit %.0f)' % (len(sites), pn, dwell, sig,
                                          q_site, CHG_MAX))
    if q_site > CHG_MAX:
        raise SystemExit('per-site charge %.1f over limit' % q_site)

    tb = ns['TrajectoryBuilder'](field_um=SIZE_UM, step_um=STEP, travel_v=0.0)
    vv = np.array([s[2] for s in sites])
    assert abs(vv.mean()) < 1e-9, 'net DC in the site list'
    assert np.abs(vv).max() <= V + 1e-9, '|V| over ceiling'
    for (x0, y0, v0) in sites:
        tb.dwell((x0, y0), v0, n=pn)
    xs, ys, vs = (np.asarray(a, float) for a in tb.to_arrays())
    mins = len(xs) * STEP / SPEED / 60.0
    print('  %d pts -> %.2f min at %.2f um/s (S7 cap %.0f)'
          % (len(xs), mins, SPEED, MAX_MIN))
    print('  x %.2f-%.2f, y %.2f-%.2f um in a %.1f um frame'
          % (xs.min(), xs.max(), ys.min(), ys.max(), SIZE_UM))
    print('  |V|max %.1f, net DC %+.2e' % (np.abs(vs).max(), vs.mean()))
    if mins > MAX_MIN:
        raise SystemExit('over the S7 cap')
    if not (xs.min() >= 0.05 and ys.min() >= 0.05
            and xs.max() <= SIZE_UM - 0.05 and ys.max() <= SIZE_UM - 0.05):
        raise SystemExit('S3: path too close to the frame edge')
    if abs(vs.mean()) > 1e-6:
        raise SystemExit('S4: path carries net DC %.3e' % vs.mean())
    if DRY:
        print('\nDRY RUN: every gate passes, nothing written.')
        return

    # ------------------------------------------------------------- write
    if SIGMA <= 0:
        # NO-WRITE NULL. Everything else in this run is identical -- same
        # tunes, same frames, same analysis -- so the after-frames measure how
        # far a re-tune and a second pass move the readout on their own. Every
        # "created by the write" number in this campaign is a before/after
        # difference and none of them means anything without this.
        #
        # The first attempt at this silently wrote a sigma 17 panel because
        # the guard was added by a patch script whose replacement did not
        # match and which reported success anyway. dwell_for_sigma(0) rounds
        # up to one pulse, so "sigma 0" is not self-enforcing: the skip has to
        # be explicit and it has to be here, at the instrument call.
        print('\n--- NO-WRITE NULL: the write is skipped on purpose ---')
        print('  the panel above was built and passed every gate, and is NOT')
        print('  being sent. S24 is not charged.')
    else:
        budget_check(mins, 'B1_sigma%.0f' % sig)
        print('\n--- writing ---')
        fn = os.path.join(A.PROJ, 'output', '%s_B1.txt' % STAMP)
        g('goto_ldart')()
        g('run_traj')(tb, fn, speed_um_s=SPEED, preview=False)
        print('  written.')

    # ------------------------------------------------------------- after
    out = {}
    for mode, key in (('ldart', 'L'), ('vdart', 'V')):
        print('\n--- %s after ---' % mode.upper())
        _c, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                 angle_deg=0.0, xoff_um=XOFF, yoff_um=YOFF,
                                 tries=1, verbose=False)
        out[key] = inf['frame']
        print('    %s  tracked %.0f%%, offset %.1f kHz'
              % (inf['frame'], 100 * inf['frac'],
                 (inf['offset_hz'] or float('nan')) / 1e3))
        try:
            g('contact_check')(inf['frame'])
        except Exception as e:
            print('    contact_check: %s' % e)

    SLa, _, _ = load(g, out['L'])
    SVa, _, _ = load(g, out['V'])

    # ----------------------------------------------------------- readout
    print('\n' + '=' * 74)
    print('READOUT')
    print('=' * 74)
    print('\nLDART, panel interior (central %.1f um):' % (2 * 0.5))
    b_in = scan_bands(crop(SLb, pxl, 0.5), pxl, 'before', tri)
    a_in = scan_bands(crop(SLa, pxl, 0.5), pxl, 'after ', tri)
    print('\nLDART, surround (the in-frame control, beyond %.1f um):' % 0.75)
    b_out = scan_bands(ring(SLb, pxl, 0.75), pxl, 'before', tri)
    a_out = scan_bands(ring(SLa, pxl, 0.75), pxl, 'after ', tri)

    print('\nP_z AT THE COMMANDED WAVEVECTOR (matched filter, %.1f deg / %.0f nm):'
          % (want, LAM_NM))
    for lab, S in (('VDART before', SVb), ('VDART after ', SVa)):
        amp, z, p, sd = ST.matched_test(crop(S, pxv, 0.5), pxv, want, lam_nm)
        print('  %s  amp %6.2f pm   z %+5.1f   p %.4f   (null sd %.2f)'
              % (lab, amp, z, p, sd))
    print('\n  and at the OLD (incumbent) wavevector %.1f deg:' % dom)
    for lab, S in (('VDART before', SVb), ('VDART after ', SVa)):
        amp, z, p, sd = ST.matched_test(crop(S, pxv, 0.5), pxv, dom, lam_nm)
        print('  %s  amp %6.2f pm   z %+5.1f   p %.4f' % (lab, amp, z, p))

    print('\n' + '=' * 74)
    print('  before: %s / %s' % (bl, bv))
    print('  after : %s / %s' % (out['L'], out['V']))
    print('  commanded %.1f deg at sigma %.0f' % (want, sig))


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
        io.open(os.path.join(A.PROJ, 'block1_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
