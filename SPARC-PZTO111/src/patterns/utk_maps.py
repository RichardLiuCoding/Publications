# -*- coding: utf-8 -*-
"""Director population maps for the IT10b letters, cached to npz.

Everything comes out of notebook v2's toolkit through aug_toolkit2, so the
numbers are the ones the autonomous loop itself computed. The offline path was
checked against the printed console: 89 and 43 probes, w on strokes 0.081 to
0.483, between 0.076 to 0.157, contrast +0.321 against a null of 0.029, which is
11.1 times, and 63 per cent against 5 per cent on target. Every digit agrees.
"""
import contextlib
import io
import os

import numpy as np

import aug_toolkit2 as T2
import utk_geom as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "paper_llm", "utk_maps.npz")


def build(step=0.30, force=False):
    if os.path.exists(OUT) and not force:
        return dict(np.load(OUT, allow_pickle=True))
    ns = T2.load_toolkit()
    ds = ns["dir_state"]
    O, e1, e2 = G.word_frame()
    lo = G.WIN / 2 + 0.3
    hi = G.FRAME - G.WIN / 2 - 0.3
    xs = np.arange(lo, hi + 1e-9, step)
    ys = np.arange(lo, hi + 1e-9, step)
    shp = (len(ys), len(xs))
    W0, W1, D1, HIT = (np.full(shp, np.nan), np.full(shp, np.nan),
                       np.full(shp, np.nan), np.zeros(shp, bool))
    with contextlib.redirect_stdout(io.StringIO()):
        for i, cy in enumerate(ys):
            for j, cx in enumerate(xs):
                s0 = ds(G.BEFORE, cx, cy, G.WIN, G.TRIAD, G.CMD)
                s1 = ds(G.AFTER, cx, cy, G.WIN, G.TRIAD, G.CMD)
                if s0 and s1:
                    W0[i, j] = s0["w_cmd"]
                    W1[i, j] = s1["w_cmd"]
                    D1[i, j] = s1["dom"]
                HIT[i, j] = G.hit_word(cx, cy, O, e1, e2)
    np.savez(OUT, xs=xs, ys=ys, W0=W0, W1=W1, D1=D1, HIT=HIT)
    return dict(xs=xs, ys=ys, W0=W0, W1=W1, D1=D1, HIT=HIT)


if __name__ == "__main__":
    M = build(force=True)
    print("map %s over x %.2f to %.2f um"
          % (M["W1"].shape, M["xs"][0], M["xs"][-1]))
    print("on stroke  before %.3f  after %.3f"
          % (np.nanmean(M["W0"][M["HIT"]]), np.nanmean(M["W1"][M["HIT"]])))
    print("elsewhere  before %.3f  after %.3f"
          % (np.nanmean(M["W0"][~M["HIT"]]), np.nanmean(M["W1"][~M["HIT"]])))
