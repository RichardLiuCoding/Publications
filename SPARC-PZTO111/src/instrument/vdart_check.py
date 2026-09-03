# -*- coding: utf-8 -*-
"""vdart_check.py -- does the charge-balanced raster change the OUT-OF-PLANE state?

Every raster write in this campaign recorded a VDART frame before and after,
and none of them has been looked at. That is a gap a referee will find
immediately, because the mechanism section turns on the write being
charge-neutral:

  * if the raster leaves P_z untouched, the in-plane reorientation is not
    dragged by out-of-plane switching, and the charge balance of section 3.1
    is doing what it is supposed to;
  * if the raster poles the square, the whole mechanism discussion changes,
    and the polarity-independence result of section 3.4 becomes much harder
    to read.

The observable is the signed vertical piezoresponse averaged over the WRITTEN
interior minus the same average over the unwritten SURROUND of the same frame.
Taking the difference within a frame cancels the session-to-session offsets
that M38 showed are large.

A +10 V poling square, measured on this film, changes the VDART phase by
-180 deg. That is the scale a real poling event lives on.

MEASUREMENT-FREE.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A

IN_HALF = 0.60          # written interior, um from centre
OUT_HALF = 0.90         # surround starts outside this, um from centre

# label, before VDART, after VDART
PAIRS = [
    ('(+12,+12) raster 46', 'PZTO_VDART_0030.ibw', 'PZTO_VDART_0031.ibw'),
    ('(-6,-6)   raster 0', 'PZTO_VDART_0032.ibw', 'PZTO_VDART_0033.ibw'),
    ('(0,-6)    raster 120', 'PZTO_VDART_0034.ibw', 'PZTO_VDART_0035.ibw'),
    ('(-6,0)    rw step 1', 'PZTO_VDART_0038.ibw', 'PZTO_VDART_0039.ibw'),
    ('(-6,0)    rw step 2', 'PZTO_VDART_0039.ibw', 'PZTO_VDART_0040.ibw'),
    ('(0,+18)   raster 41', 'PZTO_VDART_0041.ibw', 'PZTO_VDART_0042.ibw'),
    ('(+18,-18) raster 41', 'PZTO_VDART_0043.ibw', 'PZTO_VDART_0044.ibw'),
    # AC writes: same |V|, same delivered dose, same geometry, but the sign
    # alternates along the path and NONE of them steers the director. If they
    # raise the vertical response as much as the DC rasters do, the amplitude
    # rise is a generic consequence of a biased tip crossing the area and not
    # a signature of the reorientation.
    ('(+12,0)   AC 120 nm', 'PZTO_VDART_0036.ibw', 'PZTO_VDART_0037.ibw'),
    ('(-18,0)   AC 800 nm', 'PZTO_VDART_0045.ibw', 'PZTO_VDART_0046.ibw'),
    ('(+12,-12) AC 1600 nm', 'PZTO_VDART_0047.ibw', 'PZTO_VDART_0048.ibw'),
]
DC_N = 7          # the first DC_N rows are DC rasters


def masks(n, px):
    hi = int(round(IN_HALF * 1000.0 / px))
    ho = int(round(OUT_HALF * 1000.0 / px))
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    inside = (np.abs(xx - c) < hi) & (np.abs(yy - c) < hi)
    outside = (np.abs(xx - c) > ho) | (np.abs(yy - c) > ho)
    # THE NULL. Split the unwritten surround in two and run the identical
    # statistic on one half against the other. Neither half was written, so
    # whatever this returns is what the statistic gives for no effect --
    # including any drift between the two imaging sessions. Without it there
    # is no scale on which to read the written numbers.
    nullA = outside & (xx < c)
    nullB = outside & (xx >= c)
    return inside, outside, nullA, nullB


def stats(g, tag):
    """Up-fraction, amplitude, and an amplitude-thresholded up-fraction.

    A raw up-fraction conflates poling with signal-to-noise: a region with a
    strong uniform response has a definite sign in every pixel, while a weak
    one flips sign wherever noise exceeds signal. The thresholded version
    counts only pixels whose |response| exceeds the median |response| of the
    SURROUND of the same frame, so both regions are judged at one bar.
    """
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    n = S.shape[0]
    px = float(h['ScanSize']) * 1e6 / n * 1000.0
    ins, out, nA, nB = masks(n, px)
    Si, So = S[ins], S[out]
    Si = Si[np.isfinite(Si)]
    So = So[np.isfinite(So)]
    Sa, Sb = S[nA], S[nB]
    Sa, Sb = Sa[np.isfinite(Sa)], Sb[np.isfinite(Sb)]
    thr = float(np.median(np.abs(So)))
    ti, to = Si[np.abs(Si) > thr], So[np.abs(So) > thr]
    ta, tb = Sa[np.abs(Sa) > thr], Sb[np.abs(Sb) > thr]
    return dict(up_i=float(np.mean(Si > 0)), up_o=float(np.mean(So > 0)),
                amp_i=float(np.median(np.abs(Si))),
                amp_o=float(np.median(np.abs(So))),
                amp_a=float(np.median(np.abs(Sa))),
                amp_b=float(np.median(np.abs(Sb))),
                tup_i=float(np.mean(ti > 0)) if ti.size else np.nan,
                tup_o=float(np.mean(to > 0)) if to.size else np.nan,
                tup_a=float(np.mean(ta > 0)) if ta.size else np.nan,
                tup_b=float(np.mean(tb > 0)) if tb.size else np.nan)


def main():
    print('=' * 90)
    print('DOES THE RASTER POLE? out-of-plane state, interior vs surround')
    print('=' * 90)
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__
    print('%-22s %13s %13s %9s %13s %9s'
          % ('run', 'raw up in/out', 'after in/out', 'd(in-out)',
             'd thresh', 'amp ratio'))
    deltas, tdeltas, ampb, ampa = [], [], [], []
    nulls, nullamp = [], []
    for lab, tb, ta in PAIRS:
        try:
            b = stats(g, tb)
            a = stats(g, ta)
        except Exception as e:
            print('%-22s  %s' % (lab, e))
            continue
        d = (a['up_i'] - a['up_o']) - (b['up_i'] - b['up_o'])
        td = (a['tup_i'] - a['tup_o']) - (b['tup_i'] - b['tup_o'])
        deltas.append(d)
        tdeltas.append(td)
        rb = b['amp_i'] / max(b['amp_o'], 1e-30)
        ra = a['amp_i'] / max(a['amp_o'], 1e-30)
        ampb.append(rb)
        ampa.append(ra)
        nulls.append((a['tup_a'] - a['tup_b']) - (b['tup_a'] - b['tup_b']))
        nullamp.append((a['amp_a'] / max(a['amp_b'], 1e-30))
                       / max(b['amp_a'] / max(b['amp_b'], 1e-30), 1e-30))
        print('%-22s %.3f/%.3f %.3f/%.3f %+8.3f %+9.3f %5.2f->%.2f'
              % (lab, b['up_i'], b['up_o'], a['up_i'], a['up_o'], d, td,
                 rb, ra))
    if not deltas:
        return
    d = np.array(deltas)
    print('\n  change in (interior - surround) up-fraction:')
    print('    median %+.3f, range %+.3f to %+.3f, |max| %.3f'
          % (np.median(d), d.min(), d.max(), np.abs(d).max()))
    print('\n  For scale: a +10 V poling square on this film flips essentially')
    print('  the whole interior, i.e. an up-fraction change of order 1.0, and')
    print('  changes the VDART phase by -180 deg.')
    td = np.array(tdeltas)
    print()
    print('  same quantity, counting only pixels above the surround median:')
    print('    median %+.3f, range %+.3f to %+.3f, |max| %.3f'
          % (np.median(td), td.min(), td.max(), np.abs(td).max()))
    ampb, ampa = np.array(ampb), np.array(ampa)
    print()
    print('  interior/surround VERTICAL response ratio, before -> after:')
    print('    DC rasters (n=%d): median %.2f -> %.2f'
          % (min(DC_N, len(ampa)), np.median(ampb[:DC_N]),
             np.median(ampa[:DC_N])))
    if len(ampa) > DC_N:
        print('    AC writes  (n=%d): median %.2f -> %.2f'
              % (len(ampa) - DC_N, np.median(ampb[DC_N:]),
                 np.median(ampa[DC_N:])))
        print('    -> the AC writes DO/DO NOT reproduce it; compare the two')
        print('       medians. AC does not steer the director, so a matching')
        print('       rise would mean the vertical amplitude change is a')
        print('       generic effect of a biased tip and not a signature of')
        print('       reorientation.')
    print('    all: median %.2f -> %.2f' % (np.median(ampb), np.median(ampa)))
    print('    per run: %s'
          % ', '.join('%.2f->%.2f' % (x, y) for x, y in zip(ampb, ampa)))
    print('  That ratio is why the RAW up-fraction reaches 1.000 in the')
    print('  interior: a stronger signal has a definite sign in every pixel.')
    if np.median(ampa) > 1.5 * np.median(ampb):
        print('  The write RAISES it, so this is an effect of the write and')
        print('  not a property of the middle of a frame.')
    else:
        print('  The interior already responded more strongly before the')
        print('  write, so this is a frame effect, not a result.')
    nl = np.array(nulls)
    na = np.array(nullamp)
    print()
    print('  THE NULL: the same statistics with the unwritten surround split')
    print('  in half, one half against the other, over the same %d pairs:'
          % len(nl))
    print('    thresholded sign-fraction change: median %+.3f, |max| %.3f'
          % (np.median(nl), np.abs(nl).max()))
    print('    response-ratio change:            median %.2f, range %.2f-%.2f'
          % (np.median(na), na.min(), na.max()))
    print('    written interiors, for comparison: sign %.3f max, response'
          % np.abs(td).max())
    print('    ratio %.2f median' % (np.median(ampa) / np.median(ampb)))
    if np.abs(td).max() <= 2.0 * np.abs(nl).max():
        print('    -> the out-of-plane sign change in written squares is NOT')
        print('       distinguishable from two unwritten halves of the same')
        print('       frame. Read it as an upper limit, not a measurement.')
    else:
        print('    -> written squares exceed the null.')
    if np.abs(td).max() < 0.15:
        print('\n  -> NO out-of-plane switching. The charge-balanced raster')
        print('     reorients the in-plane director while leaving P_z as it')
        print('     found it, which is what charge balance is for and what')
        print('     the mechanism of section 5 assumes.')
    else:
        print('\n  -> the interior DOES change out-of-plane; section 5 must')
        print('     account for it.')


if __name__ == '__main__':
    main()
