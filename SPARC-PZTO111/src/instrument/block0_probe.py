# -*- coding: utf-8 -*-
"""block0_probe.py -- prove the new probe, in both channels, before anything else.

MEASUREMENT ONLY: no bias, no litho, no state written.

A new probe invalidates every constant the campaign carries. Its contact
resonances differ (600/320 kHz on the operator's measurement, against the old
650/350), its spring constant and tip radius differ, and M8 records what a stale
tune looks like from the outside: an area gate calling perfectly good film
"bad". The purpose of this block is to establish, before any judgement is made
about the film, that BOTH channels are healthy at the new nominals.

It also measures the two length scales that set every downstream choice:

  * the SUPER-domain period Lambda, which the campaign has been fitting all
    along (245-388 nm), and which sets the commensurate template spacing
    Lambda/2 and the 4-Lambda readout window;
  * the NANO-domain period, which the previous probe could not resolve and
    which the operator's screenshot puts at roughly 40-55 nm.

Whether 2.5 um at 512 px (4.9 nm/px) resolves the second is the question that
decides whether the pathway experiment is possible at all. It is answered here,
on one frame, before any sample is spent.

Geometry, fixed by the operator: 2.5 um, 512 px, 2.0 Hz.
  tip speed = 2 * 2.5 * 2.0 = 10 um/s, half the campaign's usual 20 um/s.
  frame time = 512 / 2.0 = 256 s = 4.3 min per channel.
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
XOFF = float(os.environ.get('B0_X', '0.0'))
YOFF = float(os.environ.get('B0_Y', '0.0'))
STAMP = time.strftime('%y%m%d_%H%M')

# the bands each length scale is searched in, kept generous because the point
# is to MEASURE them, not to confirm a guess
SUPER_LO, SUPER_HI = 150.0, 500.0      # nm
NANO_LO, NANO_HI = 18.0, 120.0         # nm


def radial_spectrum(S, px_nm):
    """Isotropic power spectrum against period, for finding length scales.

    Returns (periods_nm, power) with the DC term removed. Used to find BOTH
    scales at once without assuming either.
    """
    a = np.asarray(S, float)
    a = a - np.nanmean(a)
    a = np.nan_to_num(a)
    n = min(a.shape)
    a = a[:n, :n]
    win = np.outer(np.hanning(n), np.hanning(n))
    F = np.abs(np.fft.fftshift(np.fft.fft2(a * win))) ** 2
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - c, yy - c)
    rb = r.astype(int)
    prof = np.bincount(rb.ravel(), F.ravel()) / np.maximum(
        1, np.bincount(rb.ravel()))
    k = np.arange(len(prof))
    with np.errstate(divide='ignore'):
        per = np.where(k > 0, n * px_nm / np.maximum(k, 1e-9), np.inf)
    return per[1:], prof[1:]


def peak_in_band(per, pw, lo, hi):
    """Strongest period inside a band, and how far it stands above the band."""
    m = (per >= lo) & (per <= hi)
    if not m.any():
        return float('nan'), float('nan')
    sub_p, sub_w = per[m], pw[m]
    i = int(np.argmax(sub_w))
    med = float(np.median(sub_w))
    return float(sub_p[i]), float(sub_w[i] / max(med, 1e-30))


def directional_period(g, S, px_nm, ang_deg):
    v = g('period')(S, px_nm, float(ang_deg))
    return (float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
            else float(v))


def report_frame(g, tag, label):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    px_nm = float(h['ScanSize']) * 1e6 / float(S.shape[0]) * 1000.0
    print('\n  --- %s: %s ---' % (label, tag))
    print('      %d px, %.2f nm/px, r12 %+.2f, |S| %.1f'
          % (S.shape[0], px_nm, r12, float(np.std(S))))
    # The first version of this used a bare radial spectrum with no
    # significance test and no band-edge check, and it reported "NANO-DOMAINS
    # RESOLVED at 119 nm" on a frame whose only short-period feature was the
    # SECOND HARMONIC of the 219 nm super-domain lamellae, at the same
    # director. scale_tools is permutation-tested against synthetic negative
    # controls; this is not. Use the tested one.
    print('      %-14s %7s %9s %8s %8s  %s'
          % ('band (nm)', 'dir', 'period', 'aniso', 'p', 'reading'))
    got = {}
    for nm, (lo, hi) in (('super', (150.0, 500.0)), ('harm', (90.0, 150.0)),
                         ('fine', (18.0, 90.0))):
        dd, an, per_, pv = ST.band_peak(S, px_nm, lo, hi, n_perm=120)
        got[nm] = (dd, an, per_, pv)
        off0 = ST.angle_between(dd, 0.0) if dd == dd else float('nan')
        if pv != pv or pv >= 0.01:
            note = 'no direction (p >= 0.01)'
        elif off0 < 12.0:
            note = 'ALONG THE FAST SCAN AXIS -- artefact'
        else:
            note = 'real: %.1f px per period' % (per_ / px_nm)
        print('      %-14s %7.1f %9.1f %8.2f %8.3f  %s'
              % ('%.0f-%.0f' % (lo, hi), dd, per_, an, pv, note))
    p_sup = got['super'][2]
    # a genuine nano-domain structure must be significant, off the fast axis,
    # and NOT at the harmonic of the super-domain period
    dn, an_, pn_, pvn = got['fine']
    harm_like = (p_sup == p_sup and pn_ == pn_
                 and abs(pn_ / (p_sup / 2.0) - 1.0) < 0.25
                 and ST.angle_between(dn, got['super'][0]) < 15.0)
    p_nan = pn_ if (pvn == pvn and pvn < 0.01
                    and ST.angle_between(dn, 0.0) >= 12.0
                    and not harm_like) else float('nan')
    if harm_like:
        print('      the fine-band peak is the 2nd harmonic of the '
              'super-domain lamellae, not a separate structure')
    return dict(tag=tag, S=S, px_nm=px_nm, r12=r12, h=h,
                p_super=p_sup, s_super=got['super'][1],
                p_nano=p_nan, s_nano=got['fine'][1], bands=got)


def main():
    print('=' * 74)
    print('BLOCK 0  new probe, both channels  %s'
          % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 74)
    print('  MEASUREMENT ONLY. No bias, no litho, no state written.')
    print('  frame %.1f um, %d px -> %.2f nm/px, %.1f Hz -> tip %.1f um/s'
          % (SIZE_UM, PX, SIZE_UM / PX * 1000, RATE, 2 * SIZE_UM * RATE))
    print('  offset (%+.1f,%+.1f)' % (XOFF, YOFF))
    assert 2 * SIZE_UM * RATE <= A.TIP_SPEED_MAX + 1e-9, 'tip speed over S6'

    ns = A.load_toolkit(stub_instrument=False)
    g = ns.__getitem__
    print('  DART nominals now %s, tol %.0f kHz -> sweep %.0f kHz'
          % ({k: '%.0f kHz' % (v / 1e3) for k, v in ns['DART_NOM'].items()},
             ns['DART_TOL'] / 1e3, 2 * ns['DART_TOL'] / 1e3))
    g('check_folder')()
    g('scanner_ok')(XOFF, YOFF, SIZE_UM)

    out = {}
    for mode in ('ldart', 'vdart'):
        print('\n' + '-' * 74)
        print('%s at nominal %.0f kHz' % (mode.upper(),
                                          ns['DART_NOM'][mode] / 1e3))
        print('-' * 74)
        try:
            cen, inf = g('tune_here')(mode, size_um=SIZE_UM, px=PX, rate=RATE,
                                      angle_deg=0.0, xoff_um=XOFF,
                                      yoff_um=YOFF, tries=2, verbose=True)
            tag = inf['frame']
            print('      tracked %.0f%% of lines, offset %.1f kHz'
                  % (100 * inf['frac'],
                     (inf['offset_hz'] or float('nan')) / 1e3))
            try:
                g('contact_check')(tag)
            except Exception as e:
                print('      contact_check said: %s' % e)
            out[mode] = report_frame(g, tag, mode.upper())
        except Exception:
            print('  %s FAILED:' % mode.upper())
            traceback.print_exc(limit=3)
            out[mode] = None

    # ------------------------------------------------ the in-plane triad
    if out.get('ldart'):
        tag = out['ldart']['tag']
        try:
            triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))
            triad = [float(t) for t in triad]
            S, px_nm = out['ldart']['S'], out['ldart']['px_nm']
            lam = [directional_period(g, S, px_nm, t) for t in triad]
            lam = [v for v in lam if v == v]
            lam_med = float(np.median(lam)) if lam else float('nan')
            sk = g('streak_index')(tag, (0.2, SIZE_UM - 0.2, 0.2, 0.8),
                                   verbose=False)
            w = tt.get('w')
            dom = float(triad[int(np.argmax(w))]) if w is not None else float('nan')
            print('\n' + '-' * 74)
            print('IN-PLANE STATE at this offset')
            print('-' * 74)
            print('  triad %s, dominant %.0f deg, modulation %.3f, streak %.3f'
                  % ([int(round(t)) for t in triad], dom, tt['mod'], sk))
            print('  Lambda per member %s -> median %.0f nm'
                  % (['%.0f' % v for v in lam], lam_med))
            out['triad'] = triad
            out['lam'] = lam_med
            out['mod'] = float(tt['mod'])
            out['streak'] = float(sk)
            out['dom'] = dom
        except Exception:
            print('  triad fit FAILED:')
            traceback.print_exc(limit=2)

    # ------------------------------------------------------- the verdict
    print('\n' + '=' * 74)
    print('VERDICT')
    print('=' * 74)
    l, v = out.get('ldart'), out.get('vdart')
    if not l:
        print('  LDART did not produce a frame. Nothing downstream can run.')
        print('  -> STOP and report. Do not write.')
        return
    print('  LDART   %s' % ('healthy' if abs(l['r12']) > 0.3 else
                            'r12 low -- suspect readout (M8/M12)'))
    if v:
        print('  VDART   frame acquired: the out-of-plane channel is live')
    else:
        print('  VDART   NO FRAME. The P_z measurement (Block 1) is not')
        print('          possible until this tunes; LDART-only work can go on.')
    nano = l['p_nano']
    if nano == nano:
        print('  NANO-DOMAINS PRESENT at %.0f nm = %.1f px, off the fast axis'
              ' and not a harmonic.' % (nano, nano / l['px_nm']))
    else:
        print('  NO independent nano-domain periodicity on this VIRGIN area.')
        print('  -> This is NOT a probe verdict. The operator reports that the')
        print('     nano-domains are often invisible until the IP super-domain')
        print('     is written or aligned, so absence here is the expected')
        print('     starting state and is the BEFORE half of the measurement.')
        print('     Judge the probe on |S|, r12 and tracking, which are above.')
    if out.get('lam') == out.get('lam'):
        win = 4.0 * out['lam'] / 1000.0
        print('  Lambda %.0f nm -> a 4-Lambda FFT window needs %.2f um.'
              % (out['lam'], win))
        if win <= 1.25:
            print('     A 1.2 um panel in a 2.5 um frame CLEARS this.')
        else:
            print('     A 1.2 um panel does NOT clear this. Use the structure')
            print('     tensor for the interior and report no FFT populations')
            print('     (PITFALLS 19.15, 20.8).')
    print('\n  frames kept: %s' % ', '.join(
        x['tag'] for x in (l, v) if x))


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
        io.open(os.path.join(A.PROJ, 'block0_%s.txt' % STAMP), 'w',
                encoding='utf-8').write(buf.getvalue())
