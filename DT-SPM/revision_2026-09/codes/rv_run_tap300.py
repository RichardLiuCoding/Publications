"""Run the causal benchmark on Tap-300/AlScN for all split schemes.

python rv_run_tap300.py [--schemes block5,speed,setpoint,submitted] [--quick]
Writes output/tap300_benchmark_<scheme>.npz (per-condition predictions) and
output/tap300_benchmark_summary.csv / .json (metrics, block-bootstrap CIs, chosen
hyperparameters per fold).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from rv_benchmark import block_bootstrap, block_folds, fit_predict, metrics
from rv_common import OUT
from rv_tap300 import PhysicsPrior, allowed_from_heldout, build_table, feature_matrix

MODELS = [  # (key, model name, feature block)
    ("median", "median", "controls"),
    ("physics", "physics", "controls"),
    ("physics_cal", "physics_cal", "controls"),
    ("knn_ctrl", "knn", "controls"),
    ("gbm_ctrl", "gbm", "controls"),
    ("gbm_ctrl_fd", "gbm", "controls+fd"),
    ("ridge_ctrl", "ridge", "controls"),
    ("ridge_ctrl_fd", "ridge", "controls+fd"),
    ("hyb_ridge", "hyb_ridge", "controls+fd"),
    ("hyb_gbm", "hyb_gbm", "controls+fd"),
    ("hyb_mlp", "hyb_mlp", "controls+fd"),
]
ABLATION = [  # loss-function ablation (R1.5), run on the primary scheme only
    ("hyb_gbm_sq", "hyb_gbm", "controls+fd", "squared_error"),
    ("hyb_gbm_abs", "hyb_gbm", "controls+fd", "absolute_error"),
    ("hyb_ridge_sq", "hyb_ridge", "controls+fd", "squared_error"),
    ("hyb_ridge_huber", "hyb_ridge", "controls+fd", "huber"),
    ("gbm_ctrl_fd_sq", "gbm", "controls+fd", "squared_error"),
    ("gbm_ctrl_fd_abs", "gbm", "controls+fd", "absolute_error"),
]


def schemes(T):
    N = T["N"]
    out = {}
    out["block5"] = ("speed_drive", block_folds(T["group"], 5))
    out["speed"] = ("speed", [np.where(T["si"] == s)[0] for s in np.unique(T["si"])])
    spb = np.array([0, 0, 1, 1, 2, 2, 3, 3])[T["spi"]]          # setpoint pairs
    out["setpoint"] = ("setpoint", [np.where(spb == k)[0] for k in range(4)])
    out["submitted"] = ("condition", [np.where(T["is_test_submitted"])[0]])
    return out


def regime(sp):
    return np.where(sp >= 0.6, "light", np.where(sp <= 0.2, "hard", "mid"))


def run_scheme(T, pp, how, folds, with_ablation=False, mlp_seeds=(0, 1, 2)):
    N = T["N"]
    Xc = {k: feature_matrix(T, k) for k in ("controls", "controls+fd")}
    y_a = np.log10(T["Q_align"]); y_s = T["Q_safety"]
    models = MODELS + (ABLATION if with_ablation else [])
    P = {t: {m[0]: np.full(N, np.nan) for m in models} for t in ("Q_align", "Q_safety")}
    Pmlp = {t: np.full((len(mlp_seeds), N), np.nan) for t in P}
    prior_a = np.full(N, np.nan); chosen = []
    for f, te in enumerate(folds):
        tr = np.setdiff1d(np.arange(N), te)
        allowed = allowed_from_heldout(T, te, how)
        pr = pp.run(allowed)
        lp = np.log10(np.clip(pr["Q_sim"], 1e-3, None))
        prior_a[te] = lp[te]
        g = T["group"]
        for tname, y, prior in (("Q_align", y_a, lp), ("Q_safety", y_s, T["Qs_prior"])):
            for spec in models:
                key, name, blk = spec[:3]
                fl = spec[3] if len(spec) > 3 else None
                X = Xc[blk]
                if name == "hyb_mlp":
                    for si_, s in enumerate(mlp_seeds):
                        p, bp = fit_predict(name, X[tr], y[tr], g[tr], X[te], prior[tr], prior[te], seed=s)
                        Pmlp[tname][si_, te] = p
                    P[tname][key][te] = Pmlp[tname][:, te].mean(0)
                    chosen.append(dict(fold=f, target=tname, model=key, params=str(bp)))
                    continue
                p, bp = fit_predict(name, X[tr], y[tr], g[tr], X[te], prior[tr], prior[te],
                                    fixed_loss=fl)
                P[tname][key][te] = p
                chosen.append(dict(fold=f, target=tname, model=key, params=str(bp)))
        print(f"   fold {f}: n_test={te.size}, local PI fits used={pr['n_local']}", flush=True)
    return P, Pmlp, prior_a, chosen


def summarise(T, scheme, P, Pmlp):
    rows, boots = [], {}
    reg = regime(T["setpoint"])
    for tname in P:
        y = T["Q_align"] if tname == "Q_align" else T["Q_safety"]
        preds = {k: (10 ** v if tname == "Q_align" else v) for k, v in P[tname].items()}
        for k, p in preds.items():
            r = metrics(y, p, reg); r.update(scheme=scheme, target=tname, model=k)
            rows.append(r)
        # MLP seed spread
        mm = [metrics(y, (10 ** Pmlp[tname][s] if tname == "Q_align" else Pmlp[tname][s]))
              for s in range(Pmlp[tname].shape[0])]
        rows.append(dict(scheme=scheme, target=tname, model="hyb_mlp_seed_sd",
                         MAE=float(np.std([m["MAE"] for m in mm])),
                         MedAE=float(np.std([m["MedAE"] for m in mm])),
                         rho=float(np.std([m["rho"] for m in mm]))))
        ref = "gbm_ctrl_fd"
        boots[tname] = block_bootstrap(y, preds, T["group"], ref=ref)
    return rows, boots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemes", default="block5,speed,setpoint,submitted")
    a = ap.parse_args()
    T = build_table(); pp = PhysicsPrior(T)
    S = schemes(T)
    all_rows, all_boot, all_chosen = [], {}, []
    for sc in a.schemes.split(","):
        how, folds = S[sc]
        t0 = time.time()
        print(f"== scheme {sc} ({how}, {len(folds)} folds)", flush=True)
        P, Pmlp, prior_a, chosen = run_scheme(T, pp, how, folds, with_ablation=(sc == "block5"))
        fold_of = np.full(T["N"], -1)
        for i, f in enumerate(folds):
            fold_of[f] = i
        np.savez(OUT / f"tap300_benchmark_{sc}.npz",
                 **{f"{t}__{k}": v for t in P for k, v in P[t].items()},
                 prior_log10_Qalign=prior_a, Q_align=T["Q_align"], Q_safety=T["Q_safety"],
                 Qs_prior=T["Qs_prior"], setpoint=T["setpoint"], group=T["group"],
                 fold_of=fold_of)
        scored = fold_of >= 0
        if not scored.all():                      # single held-out split: score test only
            Ts = {k: (v[scored] if isinstance(v, np.ndarray) and v.shape[:1] == (T["N"],) else v)
                  for k, v in T.items()}
            P = {t: {k: v[scored] for k, v in d.items()} for t, d in P.items()}
            Pmlp = {t: v[:, scored] for t, v in Pmlp.items()}
        else:
            Ts = T
        rows, boots = summarise(Ts, sc, P, Pmlp)
        all_rows += rows; all_boot[sc] = boots
        all_chosen += [dict(scheme=sc, **c) for c in chosen]
        print(f"   done in {time.time()-t0:.0f} s", flush=True)
    df = pd.DataFrame(all_rows)
    df.to_csv(OUT / "tap300_benchmark_summary.csv", index=False)
    pd.DataFrame(all_chosen).to_csv(OUT / "tap300_benchmark_chosen_params.csv", index=False)
    json.dump(all_boot, open(OUT / "tap300_benchmark_bootstrap.json", "w"), indent=1)
    with pd.option_context("display.width", 200, "display.max_rows", 500):
        print(df[["scheme", "target", "model", "n", "MAE", "MedAE", "P90AE", "rho"]]
              .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
