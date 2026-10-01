"""Sample-efficiency (learning-curve) analysis on Tap-300 (revision 2026-09).

For each outer fold of the blocked (speed, drive) scheme and of the setpoint-block
scheme, models are trained on random subsets of n training conditions and scored on
the untouched outer test fold. Q_safety: zero-fit physics prior, 2-parameter calibrated
prior, controls-only ridge and GBM, prior + ridge/GBM residual. Q_align: train median,
controls-only kNN/ridge/GBM (the physics prior carries no rank information for Q_align).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from rv_benchmark import block_folds, fit_predict
from rv_common import OUT
from rv_tap300 import build_table, feature_matrix

NS = [10, 20, 40, 80, 160, 320, 10_000]
REPS = 5
MODELS = {"Q_safety": ["physics", "physics_cal", "ridge", "gbm", "hyb_ridge", "hyb_gbm"],
          "Q_align": ["median", "knn", "ridge", "gbm"]}


def main():
    T = build_table()
    Xc = feature_matrix(T, "controls"); Xf = feature_matrix(T, "controls+fd")
    g = T["group"]
    spb = np.array([0, 0, 1, 1, 2, 2, 3, 3])[T["spi"]]
    schemes = {"block5": block_folds(g, 5), "setpoint": [np.where(spb == k)[0] for k in range(4)]}
    rows = []
    for sc, folds in schemes.items():
        for f, te in enumerate(folds):
            tr_all = np.setdiff1d(np.arange(T["N"]), te)
            for n in NS:
                reps = 1 if n >= tr_all.size else REPS
                for r in range(reps):
                    rng = np.random.default_rng(1000 * f + 10 * r + n % 997)
                    tr = tr_all if n >= tr_all.size else np.sort(rng.choice(tr_all, n, replace=False))
                    for tname, y, prior in (("Q_safety", T["Q_safety"], T["Qs_prior"]),
                                            ("Q_align", np.log10(T["Q_align"]), None)):
                        yt = T["Q_safety"] if tname == "Q_safety" else T["Q_align"]
                        for m in MODELS[tname]:
                            X = Xf if m.startswith("hyb") else Xc
                            pt = prior[tr] if prior is not None else None
                            pe = prior[te] if prior is not None else None
                            try:
                                p, _ = fit_predict(m if m != "gbm" else "gbm", X[tr], y[tr], g[tr], X[te], pt, pe)
                            except Exception as e:           # tiny n with too few groups
                                continue
                            p = 10 ** p if tname == "Q_align" else p
                            e = np.abs(p - yt[te])
                            rows.append(dict(scheme=sc, fold=f, n=int(tr.size), rep=r, target=tname, model=m,
                                             MedAE=float(np.median(e)), MAE=float(np.mean(e)),
                                             rho=float(spearmanr(yt[te], p).statistic) if np.std(p) > 0 else np.nan))
            print(sc, "fold", f, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "tap300_learning_curve.csv", index=False)
    s = (df.groupby(["scheme", "target", "model", "n"])[["MedAE", "rho"]].median().reset_index())
    with pd.option_context("display.width", 200, "display.max_rows", 400):
        print(s.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
