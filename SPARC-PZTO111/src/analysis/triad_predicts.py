# -*- coding: utf-8 -*-
"""triad_predicts.py -- does the per-area triad fit predict where the film lands?

Section 3.8 argues the film carries ONE triad and the per-area as-grown fits
are noise around it. The evidence quoted is that the written landings have a
smaller circular range (5.81 deg) than the fits (7.50 deg). With six points
that comparison is weak, and a referee would say the landings could simply have
inherited the clustering of the fits.

There is a sharper test that does not depend on comparing two ranges.

  * If each area really has its OWN triad, the pre-write fit is an estimate of
    it, and the landing must track the fit: correlation near +1, slope near 1.
  * If there is ONE triad and the fits are noise around it, the fit carries no
    information about the landing: correlation near 0.

The fits are also quantised -- three of the six areas were fitted to exactly
16.5 deg and two to exactly 24.0 -- so the test has a second form: areas given
IDENTICAL fits should land at identical angles if the fit is meaningful.

MEASUREMENT-FREE.
"""
from __future__ import annotations

import numpy as np

# area, as-grown fit mod 60, matched-filter landing mod 60
ROWS = [
    ('(+12,+12)', 16.5, 16.39),
    ('(-6,-6)', 24.0, 19.63),
    ('(0,-6)', 19.0, 20.88),
    ('(0,+18)', 16.5, 20.01),
    ('(+18,-18)', 16.5, 17.90),
    ('(-6, 0)', 24.0, 15.07),
]
NPERM = 200000


def main():
    fit = np.array([r[1] for r in ROWS])
    land = np.array([r[2] for r in ROWS])
    print('=' * 72)
    print('DOES THE PRE-WRITE TRIAD FIT PREDICT THE LANDING?')
    print('=' * 72)
    print('%-11s %10s %10s' % ('area', 'fit', 'landing'))
    for nm, f, l in ROWS:
        print('%-11s %10.2f %10.2f' % (nm, f, l))

    r = float(np.corrcoef(fit, land)[0, 1])
    sl = float(np.polyfit(fit, land, 1)[0])
    print('\n  correlation fit vs landing : r = %+.3f' % r)
    print('  slope                      : %+.3f  (1.0 if the fit is right)'
          % sl)

    rng = np.random.default_rng(0)
    null = np.empty(NPERM)
    for k in range(NPERM):
        null[k] = np.corrcoef(fit, rng.permutation(land))[0, 1]
    p = float(np.mean(np.abs(null) >= abs(r)))
    print('  permutation p (two-sided)  : %.3f  over %d shuffles' % (p, NPERM))

    print('\n  ranges: fits %.2f deg, landings %.2f deg'
          % (fit.max() - fit.min(), land.max() - land.min()))

    print('\n  areas given IDENTICAL fits:')
    for v in sorted(set(fit)):
        m = fit == v
        if m.sum() > 1:
            ls = land[m]
            print('    fit %.1f deg (%d areas): landings %s -> spread %.2f deg'
                  % (v, m.sum(), ', '.join('%.2f' % x for x in ls),
                     ls.max() - ls.min()))

    print('\n  scatter of landings about their own mean : %.2f deg'
          % land.std(ddof=1))
    print('  scatter of landings about their own fit   : %.2f deg'
          % np.sqrt(np.mean((land - fit) ** 2)))
    print()
    if abs(r) < 0.5:
        print('  -> The fit carries no useful information about the landing.')
        print('     Areas assigned the SAME fit land up to 4.6 deg apart, and')
        print('     areas assigned fits 7.5 deg apart land within 5.8 deg of')
        print('     one another with no ordering between them. That is what a')
        print('     single triad plus fit noise looks like, and not what a set')
        print('     of genuinely different per-area triads would look like.')
    else:
        print('  -> the fit does predict the landing; per-area triads are live.')


if __name__ == '__main__':
    main()
