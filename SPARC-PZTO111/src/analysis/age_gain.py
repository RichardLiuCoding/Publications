# -*- coding: utf-8 -*-
"""age_gain.py -- does the anisotropy gain depend on how old the panel is?

The retention run found the written panels MORE anisotropic hours later than
immediately after the write, median 138 %. The obvious reading is that the
structure consolidates over hours. That reading makes a prediction: older
panels should have gained more.

Panel ages are the write time against the .ibw modification time of the
retention frame.
"""
from __future__ import annotations

import numpy as np

# area, age in hours, anisotropy at the write, anisotropy in the retention run
ROWS = [
    ('(+12,+12)', 4.80, 10.85, 15.35),
    ('(-6,-6)', 4.02, 22.74, 36.10),
    ('(0,-6)', 3.75, 9.61, 12.38),
    ('(-6, 0)', 2.45, 5.70, 4.57),
    ('(0,+18)', 1.60, 18.60, 24.94),
    ('(+18,-18)', 1.31, 16.86, 50.53),
]


def rank(v):
    return np.argsort(np.argsort(v)).astype(float)


def main():
    age = np.array([r[1] for r in ROWS])
    gain = np.array([r[3] / r[2] for r in ROWS])
    print('%-11s %6s %8s %8s %7s' % ('area', 'age h', 'then', 'now', 'gain'))
    for (nm, a, t, w), gg in zip(ROWS, gain):
        print('%-11s %6.2f %8.2f %8.2f %7.2f' % (nm, a, t, w, gg))
    r = float(np.corrcoef(age, gain)[0, 1])
    rs = float(np.corrcoef(rank(age), rank(gain))[0, 1])
    print('\n  median gain %.2f, range %.2f-%.2f'
          % (np.median(gain), gain.min(), gain.max()))
    print('  Pearson r = %+.3f, Spearman = %+.3f  (n = %d)'
          % (r, rs, len(ROWS)))
    if abs(rs) < 0.5:
        print('\n  -> NO relationship with age. The largest gain (%.2fx) is on'
              % gain.max())
        print('     the YOUNGEST panel (%.1f h) and the only loss is on a'
              % age[int(np.argmax(gain))])
        print('     panel of middling age. Whatever raises the anisotropy is')
        print('     not a slow consolidation; it is more likely a difference')
        print('     between the two MEASUREMENTS -- the first frame is taken')
        print('     immediately after the tip has delivered +/-10 V over the')
        print('     area, the second after withdrawal, retune and re-approach.')
    else:
        print('\n  -> gain tracks age; consolidation is a live reading.')


if __name__ == '__main__':
    main()
