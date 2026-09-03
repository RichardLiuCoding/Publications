# -*- coding: utf-8 -*-
"""offset_bias.py -- do the landing offsets lean TOWARD the commanded axis?

The landscape written in section 5.2,

    F(theta) = -A cos 6 theta - B cos^2(theta - phi)

does more than say "the film lands on an allowed orientation". It says the
selected minimum is DISPLACED from its crystallographic position, toward the
commanded axis, by

    delta = B sin(2 Delta) / (36 A),     Delta = phi - theta_member

to first order in B/A. The sign is a prediction and it is free: it requires no
fitting, and it is a property no artefact of the estimator would produce, since
the estimator knows nothing about where the raster was commanded.

This script tests it on every raster run on the current probe. The triad
positions are the rigid-triad fits made by the area SCREEN, before any write,
so theta_member is not derived from the same data as theta_after.
"""
from __future__ import annotations

import numpy as np

# area, phi0 from the pre-write screen, raster angle, director after
RUNS = [
    ('(+12,+12)', 16.5, 46.0, 18.8),
    ('(-6,-6)', 24.0, 0.0, 18.8),
    ('(0,-6)', 19.0, 120.0, 138.8),
    ('(0,+18)', 16.5, 41.0, 18.8),
    ('(+18,-18)', 16.5, 41.0, 18.8),
]
RES = 7.5           # estimator angular resolution, degrees


def wrap180(a):
    return (a + 90.0) % 180.0 - 90.0


def main():
    print('=' * 76)
    print('DO THE OFFSETS LEAN TOWARD THE COMMANDED AXIS?')
    print('=' * 76)
    print('  model: delta = B sin(2 Delta) / (36 A), Delta = raster - member')
    print()
    print('%-11s %7s %7s %7s %8s %8s %7s %s'
          % ('area', 'raster', 'member', 'after', 'Delta', 'delta', 'toward', 'B/A'))
    rows = []
    for name, phi0, phi, after in RUNS:
        members = [(phi0 + 60.0 * k) % 180.0 for k in range(3)]
        # the member the film actually landed on
        m = min(members, key=lambda t: abs(wrap180(after - t)))
        delta = wrap180(after - m)             # signed, from member to landing
        Delta = wrap180(phi - m)               # signed, from member to command
        toward = 'yes' if delta * Delta > 0 else 'no'
        s2 = np.sin(np.radians(2 * Delta))
        ba = (np.radians(delta) * 36.0 / s2) if abs(s2) > 1e-6 else np.nan
        rows.append((name, phi, m, after, Delta, delta, toward, ba))
        print('%-11s %7.1f %7.1f %7.1f %8.1f %8.1f %7s %6.2f'
              % (name, phi, m, after, Delta, delta, toward, ba))

    tw = [r for r in rows if r[6] == 'yes']
    k, n = len(tw), len(rows)
    # two-sided sign test against a coin
    from math import comb
    p = sum(comb(n, j) for j in range(k, n + 1)) / 2.0 ** n * 2
    print()
    print('  %d of %d lean toward the commanded axis; sign test p = %.3f'
          % (k, n, min(p, 1.0)))
    ba = np.array([r[7] for r in rows], float)
    print('  implied B/A: median %.2f, range %.2f-%.2f'
          % (np.median(ba), ba.min(), ba.max()))
    d = np.array([abs(r[5]) for r in rows])
    print('  |delta|: median %.1f deg, max %.1f deg, against %.2f deg resolution'
          % (np.median(d), d.max(), RES))
    print()
    if k == n and d.max() < 2 * RES:
        print('  -> The sign is consistent in every run, but every offset is at')
        print('     or below the estimator resolution. The DIRECTION of the')
        print('     lean is a real result; its MAGNITUDE is not resolved, and')
        print('     B/A can only be quoted as an order of magnitude.')
    elif k == n:
        print('  -> consistent lean, resolved in magnitude.')
    else:
        print('  -> the lean is not consistent; the first-order prediction fails.')

    # what would settle it: how large must Delta be for delta to clear 2*RES?
    if k == n:
        m_ba = float(np.median(ba))
        need = np.degrees(np.arcsin(min(1.0, 2 * RES * np.pi / 180 * 36 / m_ba))) / 2
        print()
        print('  To resolve the magnitude, delta must exceed 2 x %.2f = %.1f deg,'
              % (RES, 2 * RES))
        print('  which at B/A = %.2f needs |Delta| = %.1f deg -- i.e. a raster'
              % (m_ba, need))
        print('  commanded %.0f deg from the nearest member. The maximum possible'
              % need)
        print('  is 30 deg, so this is %s with a single raster.'
              % ('reachable' if need <= 30 else 'NOT reachable'))


if __name__ == '__main__':
    main()
