# -*- coding: utf-8 -*-
"""check_arc_p.py -- verify the circular-range p-value by simulation.

Section 3.8 claims that six written directions falling within 6.51 deg of one
another modulo 60 deg has probability 9e-5 under a uniform null. That uses the
analytic CDF of the circular range,

    P(range <= L) = n (L/C)^(n-1)      for L <= C/2

evaluated at the OBSERVED range. Two things could be wrong: the formula, and
the legitimacy of evaluating it at a value taken from the data. The second is
fine -- the CDF of the range is exactly the probability of a range at least as
small as observed -- but the campaign has been caught twice by a p-value from
an analytic expression that did not match its own null (PITFALLS 21.2, 21.3),
so it gets simulated.
"""
from __future__ import annotations

import numpy as np

C = 60.0
OBS = 5.81
N = 6
NSIM = 4_000_000


def circ_range(x, C=60.0):
    """Smallest arc containing all points, for points on a circle of size C."""
    x = np.sort(x, axis=-1)
    gaps = np.diff(x, axis=-1)
    wrap = (x[..., 0] + C - x[..., -1])[..., None]
    allg = np.concatenate([gaps, wrap], axis=-1)
    return C - allg.max(axis=-1)


def main():
    rng = np.random.default_rng(0)
    hits = 0
    done = 0
    block = 500_000
    while done < NSIM:
        m = min(block, NSIM - done)
        x = rng.uniform(0.0, C, size=(m, N))
        hits += int(np.sum(circ_range(x, C) <= OBS))
        done += m
    p_sim = hits / float(NSIM)
    p_ana = N * (OBS / C) ** (N - 1)
    se = (p_sim * (1 - p_sim) / NSIM) ** 0.5
    print('observed circular range %.2f deg for n = %d on a %.0f deg circle'
          % (OBS, N, C))
    print('  analytic  n(L/C)^(n-1) = %.3e' % p_ana)
    print('  simulated %d draws     = %.3e  (+/- %.1e)' % (NSIM, p_sim, se))
    ok = abs(p_sim - p_ana) < 4 * se + 1e-12
    print('  agree within 4 s.e.: %s' % ok)

    # sanity: the same machinery on the actual landings
    land = np.array([16.39, 19.63, 20.88, 20.01, 17.90, 15.07])
    print('\n  circular range of the six landings: %.2f deg'
          % circ_range(land[None, :], C)[0])


if __name__ == '__main__':
    main()
