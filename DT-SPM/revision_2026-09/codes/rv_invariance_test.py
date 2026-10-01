"""Invariance test: scrambling every scan line of held-out conditions must not change any
tested prediction for those conditions (one blocked fold: scanner, GBM, hybrid GBM and hybrid ridge)."""
import json
import numpy as np
from rv_benchmark import block_folds, fit_predict
from rv_common import OUT
from rv_tap300 import PhysicsPrior, allowed_from_heldout, build_table, feature_matrix


def predict(T, pp, te):
    tr = np.setdiff1d(np.arange(T["N"]), te)
    pr = pp.run(allowed_from_heldout(T, te, "speed_drive"))
    lp = np.log10(np.clip(pr["Q_sim"], 1e-3, None))
    X = feature_matrix(T, "controls+fd"); g = T["group"]
    y = np.log10(T["Q_align"])
    out = {"physics": lp[te]}
    for m in ("gbm", "hyb_gbm", "hyb_ridge"):
        out[m] = fit_predict(m, X[tr], y[tr], g[tr], X[te], lp[tr], lp[te])[0]
    return out


T = build_table(); pp = PhysicsPrior(T)
te = block_folds(T["group"], 5)[0]
a = predict(T, pp, te)
rng = np.random.default_rng(0)
H = T["raw"]["traces_height"]
for c in te:                                    # scramble held-out lines in the raw grid
    idx = (T["si"][c], T["di"][c], T["spi"][c], T["gi"][c])
    H[idx] = rng.normal(0, 1e3, H[idx].shape)
    T["Q_align"][c] = rng.uniform(0.1, 1e3)     # and their targets (never used for inputs)
b = predict(T, pp, te)
res = {k: float(np.max(np.abs(a[k] - b[k]))) for k in a}
json.dump(res, open(OUT / "invariance_test.json", "w"), indent=1)
print(res)
