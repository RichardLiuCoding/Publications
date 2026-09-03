# -*- coding: utf-8 -*-
"""Re-score an iteration from its frames, independently of its driver.

Needed twice now. IT2 crashed after its write on UnboundLocalError and IT5
crashed after its readout on KeyError, both in code that runs last, and in both
cases the measurement was complete and only the verdict was lost. The frames are
on disk, so the result is recoverable - but recovering it by hand invites a third
version of the numbers.

So this is the one implementation: give it the frames, the panel centres and the
commands, and it produces the C45-scored table using the same toolkit functions
the drivers use.

    python rescore.py --console it5_console.txt

parses the geometry out of a driver's console log, or pass the geometry directly
in a small dict at the bottom of the file.

WHAT IT COMPUTES, and why it matches the drivers exactly
    excess   = [w_panel - mean_tiles](after) - [w_panel - mean_tiles](before)
    null     = 2 sd of that same statistic applied to each untouched tile,
               LEAVE-ONE-OUT (C45). A panel is out-of-sample with respect to
               the tiles, so its null must be too.
    also     max|d| over the tiles, a threshold that assumes no distribution.
    tiles    gridded over the frame, then every tile touching a written panel
             is dropped (PITFALLS 11.3), then the terrace filter (C44 note).
"""
import io
import os
import re
import sys
import glob
import argparse
import numpy as np

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)
import autoloop as A                                          # noqa: E402


def index_frames():
    ix = {}
    for f in glob.glob(os.path.join(A.DATA_ROOT, '**', 'PZTO_*.ibw'),
                       recursive=True):
        ix.setdefault(os.path.basename(f), f)
    return ix


def flatness(d, cx, cy, half, frame):
    z = np.asarray(d, float)
    while z.ndim > 2:
        z = z[0]
    if z.ndim != 2:
        return float('nan')
    if np.nanmax(np.abs(z)) < 1e-3:
        z = z * 1e9
    ny, nx = z.shape
    i0 = max(int((cy - half) / frame * ny), 0)
    i1 = min(int((cy + half) / frame * ny) + 1, ny)
    j0 = max(int((cx - half) / frame * nx), 0)
    j1 = min(int((cx + half) / frame * nx) + 1, nx)
    sub = z[i0:i1, j0:j1]
    if sub.size < 9:
        return float('nan')
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    Am = np.c_[xx.ravel(), yy.ravel(), np.ones(sub.size)]
    c, *_ = np.linalg.lstsq(Am, sub.ravel(), rcond=None)
    return float(np.ptp(sub - (c[0] * xx + c[1] * yy + c[2])))


def parse_console(path):
    """Pull the geometry a driver printed out of its own log."""
    t = io.open(path, encoding='utf-8', errors='replace').read()
    g = {}
    m = re.search(r'=== area \(([-+\d.]+),([-+\d.]+)\)', t)
    if m:
        g['area'] = (float(m.group(1)), float(m.group(2)))
    m = re.search(r'spacing (\d+) nm', t)
    m2 = re.search(r'Lambda[^\n]*?-> (\d+) nm', t)
    if m2:
        g['lam'] = float(m2.group(1))
    m = re.search(r'readout window ([\d.]+) um', t)
    if m:
        g['win'] = float(m.group(1))
    m = re.search(r'halo ([\d.]+), pitch', t)
    if m:
        g['halo'] = float(m.group(1))
    # slot assignment lines: "  S15  -> slot 4 at (6.00,6.74), dominant 60 -> command 0"
    pans = []
    for mm in re.finditer(r'^\s+(\w+)\s+-> slot \d+ at \(([\d.]+),([\d.]+)\),'
                          r'\s+dominant (\d+) -> command (\d+)', t, re.M):
        pans.append(dict(label=mm.group(1), cx=float(mm.group(2)),
                         cy=float(mm.group(3)), dom0=float(mm.group(4)),
                         cmd=float(mm.group(5))))
    g['panels'] = pans
    # frames
    ref = re.findall(r'frame_gate (PZTO_LDART_\d+\.ibw)', t)
    if ref:
        g['ref'] = ref[-1]
    fr = re.findall(r'-> (PZTO_LDART_\d+\.ibw)', t)
    g['frames'] = fr
    m = re.search(r'sigma[^\n]*?(\d+) V\.s/um\^2', t)
    if m:
        g['sigma'] = float(m.group(1))
    return g


def score(ref, after, panels, win, halo, frame=12.0, triad=None, verbose=True):
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__
    ds = g('dir_state')
    if triad is None:
        triad, tt = g('pin_triad')(after, ref_fam=g('FAM_FILM'))
        triad = [float(v) for v in triad]
    step = win + 0.10
    cand, yc = [], 0.35
    while yc + win <= frame - 0.35 + 1e-9:
        cand += g('ctrl_tiles')(0.35, frame - 0.35, yc, yc + win, win)
        yc += step
    tiles = [rg for rg in cand
             if all(rg[1] < p['cx'] - halo - 0.05
                    or rg[0] > p['cx'] + halo + 0.05
                    or rg[3] < p['cy'] - halo - 0.05
                    or rg[2] > p['cy'] + halo + 0.05 for p in panels)]
    d0, _ = g('ibw')(ref)
    tr = [flatness(d0, 0.5 * (r[0] + r[1]), 0.5 * (r[2] + r[3]), 0.5 * win,
                   frame) for r in tiles]
    fin = [v for v in tr if v == v]
    cut = 1.5 * float(np.median(fin)) if fin else float('inf')
    keep = [r for r, v in zip(tiles, tr) if v == v and v <= cut]
    if len(keep) >= 8:
        tiles = keep
    if verbose:
        print('  %d control tiles clear of %d panels (terrace filter kept %d)'
              % (len(tiles), len(panels), len(keep)))

    cache = {}

    def stats(cmd):
        k = round(float(cmd), 3)
        if k not in cache:
            wa, wb = [], []
            for rg in tiles:
                tx, ty = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
                sa = ds(after, tx, ty, win, triad, cmd)
                sb = ds(ref, tx, ty, win, triad, cmd)
                if sa and sb:
                    wa.append(sa['w_cmd'])
                    wb.append(sb['w_cmd'])
            wa, wb = np.array(wa), np.array(wb)
            n = len(wa)
            dd = np.empty(n)
            for i in range(n):
                m = np.ones(n, bool)
                m[i] = False
                dd[i] = (wa[i] - wa[m].mean()) - (wb[i] - wb[m].mean())
            cache[k] = (wa, wb, dd)
        return cache[k]

    out = []
    for p in panels:
        wa, wb, dd = stats(p['cmd'])
        thr = float(2.0 * dd.std(ddof=1))
        sa = ds(after, p['cx'], p['cy'], win, triad, p['cmd'])
        sb = ds(ref, p['cx'], p['cy'], win, triad, p['cmd'])
        if not (sa and sb):
            continue
        exc = (sa['w_cmd'] - wa.mean()) - (sb['w_cmd'] - wb.mean())
        ic = int(np.argmin([abs((t - p['cmd'] + 90) % 180 - 90)
                            for t in triad]))
        out.append(dict(p, w_cmd=float(sa['w_cmd']), excess=float(exc),
                        threshold=thr, x=float(exc / max(thr, 1e-9)),
                        d_max=float(np.abs(dd).max()),
                        beats_max_tile=bool(exc > np.abs(dd).max()),
                        dom=float(sa['dom']),
                        on_target=bool(sa['dom'] == triad[ic]),
                        switched=bool(exc > thr and sa['dom'] == triad[ic])))
    return out, triad, len(tiles)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--console', required=True)
    ap.add_argument('--ref', default=None)
    ap.add_argument('--after', default=None)
    ap.add_argument('--frame', type=float, default=12.0)
    a = ap.parse_args()
    g = parse_console(os.path.join(PROJ, a.console))
    print('parsed from %s:' % a.console)
    for k in ('area', 'lam', 'win', 'halo', 'sigma', 'ref'):
        print('  %-6s %s' % (k, g.get(k)))
    print('  panels: %s' % [(p['label'], p['cx'], p['cy'], p['cmd'])
                            for p in g['panels']])
    print('  frames seen: %s' % [f[-8:-4] for f in g.get('frames', [])])
    ref = a.ref or g.get('ref')
    after = a.after or (g['frames'][-1] if g.get('frames') else None)
    if not (ref and after and g.get('panels')):
        raise SystemExit('could not determine ref/after/panels - pass them')
    print('\nscoring %s (after) against %s (before)'
          % (after[-8:-4], ref[-8:-4]))
    rows, triad, ntile = score(ref, after, g['panels'], g['win'], g['halo'],
                               frame=a.frame)
    print('\n  %-6s%9s%9s%10s%9s%9s  %s'
          % ('', 'cmd', 'w(cmd)', 'excess', 'x thr', 'thr', 'verdict'))
    for r in rows:
        print('  %-6s%9.0f%9.3f%+10.3f%9.1f%9.3f  %s%s'
              % (r['label'], r['cmd'], r['w_cmd'], r['excess'], r['x'],
                 r['threshold'], 'SWITCHED' if r['switched'] else
                 ('on target, sub-threshold' if r['on_target'] else 'no'),
                 '  beats every tile' if r['beats_max_tile'] else ''))
    print('\n  triad %s, %d tiles' % ([int(t) for t in triad], ntile))
