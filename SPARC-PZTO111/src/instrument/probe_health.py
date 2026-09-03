"""Did the readout degrade over TIME, or is this area simply bad film?

IT11 halted at (-2,0) with baseline floor 0.589 and 58 % director flips, and the
driver's advice is "Move". But the same position read modulation 0.200 with
r12 +0.90..+0.94 fifteen minutes earlier, and contact_check on the last baseline
reported the tracked contact resonance at 729 +- 46 kHz against a 665 kHz drive.

PITFALLS 8 catalogues four occasions when the material was blamed for a
measurement problem. The discriminator is simple: score every frame taken today
with the same code, in time order, and see whether the health metrics track the
CLOCK or the POSITION.
"""
import glob
import os
import sys

import numpy as np

_ROOT = os.environ.get(
    'SPARC_DATA',
    r'C:\Users\Asylum User\Documents\Asylum Research Data')
if len(sys.argv) > 1:
    DATA = os.path.join(_ROOT, sys.argv[1], 'PZTO')
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import autoloop as _A
    DATA = _A.resolve_folder()
print('folder: %s\n' % DATA)

from igor2 import binarywave as bw


def load(p):
    w = bw.load(p)
    d = np.transpose(w['wave']['wData'], (2, 0, 1))
    n = w['wave'].get('note', b'')
    if isinstance(n, bytes):
        n = n.decode('latin-1', 'replace')
    h = {}
    for line in n.replace('\r', '\n').split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            h[k.strip()] = v.strip()
    return d, h


rows = []
for p in sorted(glob.glob(os.path.join(DATA, '*.ibw'))):
    try:
        d, h = load(p)
    except Exception as e:
        continue
    # channels: 0 height, 1 Amp1, 2 Amp2, 3 Phase1, 4 Phase2, 5 Freq
    if d.shape[0] < 5:
        continue
    a1, a2 = d[1].astype(float), d[2].astype(float)
    p1, p2 = d[3].astype(float), d[4].astype(float)
    m = np.isfinite(a1) & np.isfinite(a2)
    r12 = float(np.corrcoef(a1[m].ravel(), a2[m].ravel())[0, 1]) if m.sum() > 100 else float('nan')
    amp = float(np.nanmedian(np.hypot(a1, a2))) * 1e12   # pm-ish scale
    s1 = float(np.nanmedian(a1)) * 1e12
    def f(k, sc=1e6):
        try:
            return float(h.get(k)) * sc
        except Exception:
            return float('nan')
    rows.append(dict(name=os.path.basename(p), t=h.get('Time', '?'),
                     size=f('ScanSize'), xo=f('XOffset'), yo=f('YOffset'),
                     sp=f('DeflectionSetpointVolts', 1.0),
                     drive=f('DriveFrequency', 1e-3),
                     r12=r12, amp=amp, a1=s1))

print('every frame taken today, in file order, scored with one piece of code')
print('%-22s %-11s %-6s %-14s %-7s %-9s %-8s %s'
      % ('frame', 'time', 'size', 'offset(um)', 'deflSP', 'drive kHz', 'r12',
         'median |A| (pm)'))
for r in rows:
    print('%-22s %-11s %-6.1f (%+6.2f,%+6.2f) %-7.2f %-9.1f %-8.2f %.1f'
          % (r['name'], r['t'], r['size'], r['xo'], r['yo'], r['sp'],
             r['drive'], r['r12'], r['amp']))

print('')
print('grouped by POSITION (is one area bad?)')
by = {}
for r in rows:
    by.setdefault((round(r['xo'], 1), round(r['yo'], 1)), []).append(r)
for k in sorted(by):
    g = by[k]
    print('  offset %-14s n=%d   r12 %s   |A| %s'
          % (str(k), len(g),
             ' '.join('%+.2f' % x['r12'] for x in g),
             ' '.join('%.0f' % x['amp'] for x in g)))
print('')
print('grouped by TIME (did it degrade?)  first half vs second half')
n = len(rows)
h1, h2 = rows[:n // 2], rows[n // 2:]
for lbl, gg in (('first half ', h1), ('second half', h2)):
    rr = [x['r12'] for x in gg if x['r12'] == x['r12']]
    aa = [x['amp'] for x in gg]
    print('  %s n=%2d   r12 %.2f +- %.2f   median |A| %.1f pm'
          % (lbl, len(gg), np.mean(rr), np.std(rr), np.median(aa)))
print('')
print('deflection setpoints seen today: %s'
      % sorted({round(r['sp'], 2) for r in rows}))
print('(the campaign ran at 0.60 V through IT1-IT10b)')
