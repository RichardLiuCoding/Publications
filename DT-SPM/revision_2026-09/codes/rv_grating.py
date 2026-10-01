"""Grating system (calibration grating, 60 MOBO-selected conditions): physics / data-driven /
hybrid comparison under three splits (revision 2026-09).

  submitted  : the archived 40/20 random split (all predictions verified not to use held-out scans)
  cv5        : 5-fold random CV over all 60 conditions
  chrono     : chronological split on the MOBO acquisition order (first 40 acquired -> last 20)

For every split the controller-gain map (PolynomialFeatures(2) + RidgeCV on log P, log I, as in
codes/cali_v2_refit_with_multiobjective_loss.py) is refitted on the local PI fits of TRAINING
conditions only; the scanner is re-simulated for every condition; data-driven and hybrid
ridge models (as submitted: Ridge(alpha=10) on quadratic control/FD features) are fitted on
training conditions only. The reference topography is the design square wave (100 nm step,
period/phase from archived condition 9).
Outputs output/grating_benchmark.json and .npz.
"""
from __future__ import annotations

import json

import numpy as np
from joblib import load
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from rv_common import OUT, ROOT, line_rmse, q_align

BUNDLE = ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz"


def scanner_setup():
    import sys
    sys.path.insert(0, str(ROOT))
    import codes.Scanner_fixed_extended_fd as sfe
    import codes.Scanner_numba_substeps_v3 as sn
    from codes.dt_static_dynamic_calibration_scaffold_v3 import ScannerRunConfig, run_scanner_line, get_height_from_out
    sn.install_numba_substep_methods(sfe.ScannerFD, verbose=False)
    fd = np.load(ROOT / "output" / "cali_fd.npz")
    fdh, fda, fdp = fd["height"], fd["amp"], fd["phase"]
    fdd = np.array([np.nanmean(fda[i, -10:]) for i in range(len(fd["drive"]))])
    mfd = {float(fdd[i]): {"d": fdh[i], "A": fda[i], "phi": fdp[i]} for i in range(len(fdd))}
    surf = sfe.FDDriveSurface.from_measured_fd(mfd, x_mode="d_over_A0", common_range="union", n_x=1024,
                                               extend_to_zero_amplitude=True, extension_n_fit=5,
                                               extension_n_bridge=30, extension_phi_mode="linear",
                                               extension_F_mode="nearest")
    params = {"k": 25, "A": float(np.nanmedian(fda)), "d0": float(np.nanmax(fdh) * 0.8), "R": 10,
              "H": 1e-19, "E_star": 1e9, "Q": 250}
    sc = sfe.ScannerFD(params=params, conversions={k: 1.0 for k in params},
                       fd_model=sfe.make_normalized_fd_lookup(surf, conv_L=1.0))
    cfg = ScannerRunConfig(dx_hat=1.0, n_substeps=50, tau_A=None, tau_phi=None, tau_z=None,
                           z_rate_limit_hat=1e6, d_init_hat=0.0, A_meas_init_hat=1.0,
                           phi_meas_init_deg=120.0, T_I=3e-1, h_smooth_sigma_px=0.0, fd_n_d=4096, use_fast=True)
    return sc, cfg, run_scanner_line, get_height_from_out


def gain_map(local, allowed_conds, drive, sp, ig, pct=80):
    L = [r for r in local if int(r["cond"]) in allowed_conds]
    lp = np.array([r["log10_P"] for r in L]); li = np.array([r["log10_I"] for r in L])
    loss = np.array([r["loss"] for r in L]); c = np.array([int(r["cond"]) for r in L])
    hit = (abs(lp + 2.5) < .05) | (abs(lp - 2) < .05) | (abs(li + 1.5) < .05) | (abs(li - 3) < .05)
    cap = np.nanpercentile(loss[np.isfinite(loss)], pct)
    m = np.isfinite(lp) & np.isfinite(li) & np.isfinite(loss) & ~hit & (loss < cap)
    X = np.c_[np.zeros(m.sum()), drive[c[m]], sp[c[m]], np.log10(ig[c[m]])]
    r = make_pipeline(SimpleImputer(strategy="median"), PolynomialFeatures(2, include_bias=False),
                      StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 25), cv=min(5, max(2, int(m.sum())))))
    r.fit(X, np.c_[lp[m], li[m]])
    p = r.predict(np.c_[np.zeros(drive.size), drive, sp, np.log10(ig)])
    p[:, 0] = np.clip(p[:, 0], -2.5, 2); p[:, 1] = np.clip(p[:, 1], -1.5, 3)
    return 10 ** p[:, 0], 10 ** p[:, 1], int(m.sum())


def center(a, trim=10):
    a = a.copy()
    for i in range(a.shape[0]):
        a[i] = a[i] - np.nanmean(a[i, trim:-trim])
    return a


def main():
    z = np.load(BUNDLE, allow_pickle=True)
    te_, drive, sp, ig, h = z["traces_exp"], z["drive_exp"], z["setpoint_exp"], z["igain_exp"], z["h_truth"]
    N = te_.shape[0]
    local = load(ROOT / "calibration_cache" / "calibration_grating_v2" / "local_PI_fits_multi.joblib")
    sc, cfg, run_line, get_h = scanner_setup()
    tables = {}

    def simulate(P, I):
        out = np.zeros_like(te_)
        for i in range(N):
            k = round(float(drive[i]), 6)
            if k not in tables:
                tables[k] = sc.prepare_fd_table_for_drive(float(drive[i]), n_d=cfg.fd_n_d)
            o = run_line(sc, h, drive_nm=float(drive[i]), setpoint=float(sp[i]), scan_speed_hat=1.0,
                         P=float(P[i]), I=float(I[i]), cfg=cfg, fd_table=tables[k])
            a, b = get_h(o); n = min(len(a), 256); out[i, 0, :n] = a[:n]; out[i, 1, :n] = b[:n]
        return out

    A0 = np.array([float(sc.get_A0_hat(float(d))) for d in drive])
    lg = np.log10(np.maximum(ig, 1e-12))
    X = np.c_[drive, sp, ig, lg, A0, np.log10(A0), drive * sp, drive * lg, sp * lg, A0 * sp]
    Yt, Yr = center(te_[:, 0]), center(te_[:, 1])
    rng = np.random.default_rng(7); perm = rng.permutation(N)
    splits = {"submitted": [z["test_idx"]], "cv5": [np.sort(perm[k::5]) for k in range(5)],
              "chrono": [np.arange(40, 60)]}
    q_exp = np.array([q_align(te_[i, 0], te_[i, 1]) for i in range(N)])
    res, store = {}, {}
    for name, folds in splits.items():
        pred = {k: np.full_like(te_, np.nan) for k in ("physics", "data", "hybrid")}
        n_maps = []
        for te in folds:
            tr = np.setdiff1d(np.arange(N), te)
            P, I, nm = gain_map(local, set(tr.tolist()), drive, sp, ig); n_maps.append(nm)
            dt = center(simulate(P, I).reshape(N * 2, -1)).reshape(te_.shape)
            poly = PolynomialFeatures(2, include_bias=False); ss = StandardScaler()
            Xtr = ss.fit_transform(poly.fit_transform(X[tr])); Xte = ss.transform(poly.transform(X[te]))
            for d, Y in ((0, Yt), (1, Yr)):
                pred["physics"][te, d] = dt[te, d]
                pred["data"][te, d] = Ridge(alpha=10.0).fit(Xtr, Y[tr]).predict(Xte)
                pred["hybrid"][te, d] = dt[te, d] + Ridge(alpha=10.0).fit(Xtr, (Y - dt[:, d])[tr]).predict(Xte)
        idx = np.concatenate(folds)
        out = {"n_test": int(idx.size), "gain_map_training_fits": n_maps}
        err_q, err_l = {}, {}
        for k, p in pred.items():
            q = np.array([q_align(p[i, 0], p[i, 1]) for i in idx])
            err_q[k] = np.abs(q - q_exp[idx])
            err_l[k] = np.array([0.5 * (line_rmse(p[i, 0], te_[i, 0]) + line_rmse(p[i, 1], te_[i, 1])) for i in idx])
            out[k] = dict(Q_MAE=float(err_q[k].mean()), Q_MedAE=float(np.median(err_q[k])),
                          line_RMSE_median=float(np.median(err_l[k])), line_RMSE_mean=float(err_l[k].mean()))
        b = np.random.default_rng(3); B = []
        for _ in range(20000):
            ii = b.integers(0, idx.size, idx.size)
            B.append([err_q["physics"][ii].mean() - err_q["hybrid"][ii].mean(),
                      err_q["data"][ii].mean() - err_q["hybrid"][ii].mean(),
                      err_q["physics"][ii].mean() - err_q["data"][ii].mean(),
                      np.median(err_l["physics"][ii]) - np.median(err_l["hybrid"][ii]),
                      np.median(err_l["data"][ii]) - np.median(err_l["hybrid"][ii])])
        B = np.array(B)
        names = ["Q_MAE phys-hyb", "Q_MAE data-hyb", "Q_MAE phys-data", "lineRMSE_med phys-hyb", "lineRMSE_med data-hyb"]
        out["paired_bootstrap_95CI"] = {n: [float(np.percentile(B[:, j], 2.5)), float(np.percentile(B[:, j], 97.5))]
                                        for j, n in enumerate(names)}
        res[name] = out
        store[name] = dict(idx=idx, **{f"pred_{k}": v for k, v in pred.items()})
        print(name, json.dumps(out, indent=1), flush=True)
    # archived bundle numbers (aligned line RMSE as in the submission), for continuity
    t = z["test_idx"]
    res["submitted_archived_bundle"] = {k: dict(Q_MAE=float(np.nanmean(np.abs(z[f"q_{k2}"][t] - z["q_exp"][t]))),
                                                line_RMSE_median=float(np.nanmedian(np.nanmean(z[f"rmse_{k2}"][t], 1))))
                                        for k, k2 in (("physics", "PI"), ("data", "dd"), ("hybrid", "hyb"))}
    json.dump(res, open(OUT / "grating_benchmark.json", "w"), indent=1)
    np.savez(OUT / "grating_benchmark.npz", q_exp=q_exp,
             **{f"{s}__{k}": v for s, d in store.items() for k, v in d.items()})


if __name__ == "__main__":
    main()
