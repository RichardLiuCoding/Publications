# -*- coding: utf-8 -*-
"""nearest_member.py -- with ONE film-wide triad, does the raster pick the
member nearest the commanded axis?

Sections 3.2 and 3.3 test the selection rule against a triad fitted per area.
Section 3.8 then shows those fits carry no information about the landing, which
leaves the rule resting on a reference the same section discredits.

This restates the rule against the single triad of section 3.8. The triad has
ONE free parameter, phi0, fitted to the six landings; that guarantees each
landing sits near SOME member, and guarantees nothing about WHICH. Whether the
member chosen is the one nearest the commanded axis is then a real test with
six independent trials.

Two nulls:
  * the film picks a member at random               -> (1/3)^n
  * the film stays on the member it was already on  -> counted directly

MEASUREMENT-FREE.
"""
from __future__ import annotations

import numpy as np

# area, commanded angle, director before, matched-filter landing (absolute)
ROWS = [
    ('(+12,+12)', 46.0, 63.8, 16.39),
    ('(-6,-6)', 0.0, 56.2, 19.63),
    ('(0,-6)', 120.0, 63.8, 140.88),
    ('(0,+18)', 41.0, 78.8, 20.01),
    ('(+18,-18)', 41.0, 63.8, 17.90),
    ('(-6, 0) rw2', 60.0, 17.98, 75.07),
]


def sep(a, b):
    """Angular separation of two directors, 0-90 deg."""
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def main():
    land = np.array([r[3] for r in ROWS])
    # phi0 by circular mean of the landings reduced modulo 60
    ang = np.radians((land % 60.0) * 6.0)
    phi0 = (np.degrees(np.arctan2(np.sin(ang).mean(),
                                  np.cos(ang).mean())) / 6.0) % 60.0
    members = [(phi0 + 60.0 * k) % 180.0 for k in range(3)]
    print('=' * 84)
    print('ONE TRIAD, FITTED TO THE LANDINGS: phi0 = %.2f deg' % phi0)
    print('  members at %s deg' % ', '.join('%.2f' % m for m in members))
    print('=' * 84)
    print('%-13s %7s %8s %9s %9s %8s %6s %6s'
          % ('area', 'command', 'before', 'landing', 'on member',
             'nearest', 'hit', 'moved'))
    hit = stay = 0
    for nm, cmd, before, l in ROWS:
        on = min(members, key=lambda m: sep(l, m))
        near = min(members, key=lambda m: sep(cmd, m))
        was = min(members, key=lambda m: sep(before, m))
        ok = abs(on - near) < 1e-6
        hit += ok
        stay += abs(on - was) < 1e-6
        print('%-13s %7.1f %8.1f %9.2f %9.2f %8.2f %6s %6.1f'
              % (nm, cmd, before, l, on, near, 'yes' if ok else 'NO',
                 sep(l, before)))
    n = len(ROWS)
    print('\n  landed on the member nearest the command : %d of %d' % (hit, n))
    print('  landed on the member it started nearest  : %d of %d' % (stay, n))
    print('  residuals from the fitted members        : %s'
          % ', '.join('%+.2f' % (l - min(members, key=lambda m: sep(l, m)))
                      for l in land))
    print('  r.m.s. residual                          : %.2f deg'
          % np.sqrt(np.mean([min(sep(l, m) for m in members) ** 2
                             for l in land])))
    print('\n  null 1, a member chosen at random   : p = (1/3)^%d = %.2e'
          % (n, (1.0 / 3.0) ** n))
    print('  null 2, the film stays where it was : excluded %d of %d times'
          % (n - stay, n))
    # It is tempting to ask whether the BEFORE states sit on the triad too,
    # and to answer "no, the write puts them there". That question is not
    # well posed here: five of the six before-states have p = 0.08-0.65, and
    # a direction with p > 0.01 is not a direction -- its distance to
    # anything measures noise. Only the re-aim's starting state is
    # significant, and that state had itself been written.
    da = np.array([min(sep(r[3], m) for m in members) for r in ROWS])
    print('\n  distance to the nearest member AFTER the write:')
    print('    %s' % ', '.join('%.1f' % x for x in da))
    print('    median %.1f deg, max %.1f deg' % (np.median(da), da.max()))
    print('\n  before-states with a significant direction: 1 of 6')
    print('    (-6, 0) rw2, p 0.005, before 17.98 deg -> %.1f deg from a'
          % min(sep(17.98, m) for m in members))
    print('     member; but that state was itself written, in step 1.')
    print('  The other five have p = 0.08-0.65, so NO statement is made here')
    print('  about whether as-grown film sits on the triad. Answering that')
    print('  needs as-grown areas that are individually significant, and')
    print('  these are not.')

    print('\n  One free parameter (phi0) was fitted to these six landings.')
    print('  That forces each landing near SOME member and says nothing about')
    print('  WHICH; the %d-of-%d above is the part that was free to fail.'
          % (hit, n))


if __name__ == '__main__':
    main()
