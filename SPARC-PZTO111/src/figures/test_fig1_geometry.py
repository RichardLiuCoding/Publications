# -*- coding: utf-8 -*-
"""Assert the domain geometry drawn in Figure 1a is self-consistent.

Three facts have to hold together, and an earlier version of the figure broke
the third while satisfying the first two:
  1. the two variants of one laminate are 120 deg apart
  2. their difference lies along the measured stripe director
  3. the three superdomain averages are 120 deg apart as vectors, while the
     three directors are only 60 deg apart as axes
"""
import itertools

import numpy as np

import v3_scenes as V

TRI = [2.0, 62.0, 122.0]
VAR = V._variant_triad(TRI)


def sep(a, b):
    return abs(((b - a) + 180.0) % 360.0 - 180.0)


def test_one_variant_set():
    assert len(VAR) == 3
    for a, b in itertools.combinations(VAR, 2):
        assert abs(sep(a, b) - 120.0) < 0.5, (a, b, sep(a, b))


def test_pair_and_wall():
    for d in TRI:
        (a, b), avg = V._laminate_of(d, VAR)
        assert abs(sep(a, b) - 120.0) < 0.5
        wall = V._axis(V._ang(V._u(a) - V._u(b)))
        assert abs(wall - V._axis(d)) < 0.6, (d, wall)
        perp = abs(((avg - d) + 90.0) % 180.0 - 90.0)
        assert abs(perp - 90.0) < 0.6, (d, avg, perp)


def test_directors_60_averages_120():
    for x, y in itertools.combinations(TRI, 2):
        assert abs(V._axis(x - y) - 60.0) < 0.5 or \
               abs(V._axis(x - y) - 120.0) < 0.5
    avs = [V._laminate_of(d, VAR)[1] for d in TRI]
    for a, b in itertools.combinations(avs, 2):
        assert abs(sep(a, b) - 120.0) < 0.5, (a, b, sep(a, b))


if __name__ == "__main__":
    for nm, fn in sorted(globals().items()):
        if nm.startswith("test_"):
            fn()
            print("  PASS  %s" % nm)
    print("figure 1a geometry is consistent")
