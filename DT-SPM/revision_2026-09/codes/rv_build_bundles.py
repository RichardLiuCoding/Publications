"""Producers for the two plot bundles named by Referee 3 (revision 2026-09).

  figure_45_expscan_data_bundle.npz  (AlScN / Tap-300 grid)
      raw grid (data/260507-300kHz-AlScN.npz) + FD library + archived local PI fits and
      simulated traces in calibration_cache/dt_controller_fit/  ->  codes/expscan_build_predictions.py
      -> codes/nature_expscan_figures.save_figure_bundle   (hard-coded /tmp paths redirected here)
  figure_45_data_bundle.npz          (calibration grating, 60 MOBO conditions)
      raw MOBO archive (data/250315/pickles/250315_Cali1_MOBO.pickle) + FD library
      (output/cali_fd.npz) + archived local PI fits (local_PI_fits_multi.joblib)  ->  this file
      (the same steps as codes/cali_v2_refit_with_multiobjective_loss.py, without /tmp caches)

Every regenerated array is compared with the archived bundle; the report is written to
output/bundles/bundle_regeneration_report.json. The per-condition local PI fits are the
expensive calibration step (Nelder-Mead / differential evolution over the scanner loss);
`--verify-local N` re-fits N archived grating conditions from raw data to check that path.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import pickle
import sys
import time

import numpy as np

from rv_common import OUT, ROOT

sys.path.insert(0, str(ROOT))
BOUT = OUT / "bundles"
BOUT.mkdir(parents=True, exist_ok=True)
SHIPPED_E = ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz"
SHIPPED_G = ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz"


def compare(new, shipped, keys=None):
    a, b = np.load(new, allow_pickle=True), np.load(shipped, allow_pickle=True)
    rep = {}
    for k in (keys or b.files):
        if k not in a.files:
            rep[k] = "not regenerated"; continue
        x, y = a[k], b[k]
        if x.shape != y.shape:
            rep[k] = f"shape {x.shape} vs {y.shape}"; continue
        if x.dtype.kind in "fc":
            rep[k] = dict(allclose=bool(np.allclose(x, y, equal_nan=True, atol=1e-6)),
                          max_abs_diff=float(np.nanmax(np.abs(x - y))) if x.size else 0.0)
        else:
            rep[k] = dict(equal=bool(np.array_equal(x, y)))
    return rep


# ------------------------------------------------------------------ AlScN / Tap-300
def build_expscan():
    import matplotlib; matplotlib.use("Agg")
    import codes.expscan_build_predictions as ebp
    import codes.nature_expscan_figures as nfe
    pred = BOUT / "expscan_predictions.npz"
    ebp.main("balanced_g3_rms", out_path=str(pred))
    _P = pathlib.Path

    def _redir(p, *a, **k):
        s = str(p)
        if s.startswith("/tmp/"):
            s = str(BOUT / ("tmp_" + s[5:]))
        return _P(s, *a, **k)
    nfe.Path = _redir
    nfe._load_predictions = lambda npz_path=pred: {k: v for k, v in np.load(pred, allow_pickle=False).items()}
    out = BOUT / "figure_45_expscan_data_bundle.npz"
    nfe.save_figure_bundle(out, tag="balanced_g3_rms")
    return out


# ------------------------------------------------------------------ grating
def build_grating(verify_local=0):
    from joblib import load
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    from codes.cali_v2_synthetic_grating import build_phase_aligned_grating
    from codes.dt_gp_static_calibration_v3 import diff_shifted
    from rv_grating import gain_map, scanner_setup, center

    p = pickle.load(open(ROOT / "data" / "250315" / "pickles" / "250315_Cali1_MOBO.pickle", "rb"))
    tr, xm = np.asarray(p["traces"]), np.asarray(p["x_measured"])
    N = tr.shape[0]
    te_ = np.zeros((N, 2, 256))
    for i in range(N):
        for j in range(2):
            ln = tr[i, -1, j]; te_[i, j] = (ln - np.nanmin(ln)) * 1e9
    drive, sp, ig = xm[:, 0], xm[:, 1] / xm[:, 0], xm[:, 2]
    sh = np.random.default_rng(35).permutation(np.arange(N))
    fit_idx, test_idx = np.sort(sh[:40]), np.sort(sh[40:])

    def detr(line):
        x = np.arange(line.size, dtype=float); s, b = np.polyfit(x, line, 1); d = line - (s * x + b)
        return d - np.nanmin(d)
    h, _ = build_phase_aligned_grating(detr(te_[9, 0]), plateau_height=100.0, duty_cycle=0.5, edge_smooth_sigma=1.5)
    local = load(ROOT / "calibration_cache" / "calibration_grating_v2" / "local_PI_fits_multi.joblib")
    P_all, I_all, _ = gain_map(local, set(fit_idx.tolist()), drive, sp, ig)
    sc, cfg, run_line, get_h = scanner_setup()

    def run(i, P, I):
        o = run_line(sc, h, drive_nm=float(drive[i]), setpoint=float(sp[i]), scan_speed_hat=1.0, P=float(P),
                     I=float(I), cfg=cfg, fd_table=sc.prepare_fd_table_for_drive(float(drive[i]), n_d=cfg.fd_n_d))
        a, b = get_h(o); return a[:256], b[:256]
    dt = np.zeros_like(te_)
    for i in range(N):
        dt[i, 0], dt[i, 1] = run(i, P_all[i], I_all[i])
    op = {int(r["cond"]): (r["P"], r["I"]) for r in local}
    dto = np.full_like(te_, np.nan)
    for i in fit_idx:
        dto[i, 0], dto[i, 1] = run(i, *op[int(i)])
    A0 = np.array([float(sc.get_A0_hat(float(d))) for d in drive]); lg = np.log10(np.maximum(ig, 1e-12))
    X = np.c_[drive, sp, ig, lg, A0, np.log10(A0), drive * sp, drive * lg, sp * lg, A0 * sp]
    poly, ss = PolynomialFeatures(2, include_bias=False), StandardScaler()
    Xtr = ss.fit_transform(poly.fit_transform(X[fit_idx])); Xa = ss.transform(poly.transform(X))
    Yt, Yr = center(te_[:, 0]), center(te_[:, 1]); dtc = np.stack([center(dt[:, 0]), center(dt[:, 1])], 1)
    dd = np.stack([Ridge(alpha=10.0).fit(Xtr, Y[fit_idx]).predict(Xa) for Y in (Yt, Yr)], 1)
    hyb = np.stack([dtc[:, d] + Ridge(alpha=10.0).fit(Xtr, (Y - dtc[:, d])[fit_idx]).predict(Xa)
                    for d, Y in ((0, Yt), (1, Yr))], 1)

    def lrmse(pred, exp, trim=10):
        sa, ea = diff_shifted(pred, exp); n = min(len(sa), len(ea))
        lo, hi = (trim, n - trim) if n > 2 * trim + 4 else (0, n)
        a = sa[lo:hi] - np.nanmean(sa[lo:hi]); e = ea[lo:hi] - np.nanmean(ea[lo:hi]); m = np.isfinite(a) & np.isfinite(e)
        return float(np.sqrt(np.nanmean((a[m] - e[m]) ** 2))) if m.sum() >= 5 else np.nan

    def trrt(arr, trim=10):
        out = np.zeros(arr.shape[0])
        for i in range(arr.shape[0]):
            t = arr[i, 0, trim:-trim] - np.nanmean(arr[i, 0, trim:-trim]); r = arr[i, 1, trim:-trim] - np.nanmean(arr[i, 1, trim:-trim])
            m = np.isfinite(t) & np.isfinite(r); out[i] = float(np.sqrt(np.nanmean((t[m] - r[m]) ** 2)))
        return out
    rm = lambda arr: np.array([[lrmse(arr[i, 0], te_[i, 0]), lrmse(arr[i, 1], te_[i, 1])] for i in range(N)])
    out = BOUT / "figure_45_data_bundle.npz"
    oc = np.array(sorted(op));
    np.savez(out, traces_exp=te_, h_truth=h, dt_PI=dt, dt_oracle=dto, dd=dd, hyb=hyb, drive_exp=drive,
             setpoint_exp=sp, igain_exp=ig, P_all=P_all, I_all=I_all, fit_idx=fit_idx, test_idx=test_idx,
             q_exp=trrt(te_), q_PI=trrt(dt), q_dd=trrt(dd), q_hyb=trrt(hyb),
             rmse_PI=rm(dt), rmse_dd=rm(dd), rmse_hyb=rm(hyb), oracle_cond=oc,
             oracle_P=np.array([op[c][0] for c in oc]), oracle_I=np.array([op[c][1] for c in oc]))
    vl = {}
    if verify_local:
        from codes.cali_v2_multiobjective_loss import multi_objective_loss, behaviour_signature, DEFAULT_WEIGHTS
        from scipy.optimize import minimize
        for ci in [int(c) for c in fit_idx[:verify_local]]:
            t0 = time.time(); et, er = te_[ci, 0], te_[ci, 1]; es = behaviour_signature(et, er)

            def Lf(lp, li):
                try:
                    s, r = run(ci, 10 ** lp, 10 ** li)
                except Exception:
                    return 1e6
                return multi_objective_loss(s, r, et, er, weights=DEFAULT_WEIGHTS,
                                            aligned_pairs=(diff_shifted(s, et), diff_shifted(r, er)), exp_sig=es)
            grid = [(lp, li, Lf(lp, li)) for lp in np.linspace(-2.5, 2.0, 9) for li in np.linspace(-1.5, 3.0, 9)]
            b0 = min(grid, key=lambda g: g[2])
            res = minimize(lambda x: Lf(x[0], x[1]), x0=np.array(b0[:2]), method="Nelder-Mead",
                           options={"xatol": 0.01, "fatol": 1e-2, "maxiter": 60})
            lp, li = (res.x if res.fun < b0[2] else b0[:2])
            lp, li = float(np.clip(lp, -2.5, 2.0)), float(np.clip(li, -1.5, 3.0))   # bounds of the archived fit
            vl[ci] = dict(refit_log10P=float(lp), refit_log10I=float(li), archived_log10P=float(np.log10(op[ci][0])),
                          archived_log10I=float(np.log10(op[ci][1])), seconds=round(time.time() - t0, 1))
            print("local fit", ci, vl[ci], flush=True)
    return out, vl


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--verify-local", type=int, default=0)
    a = ap.parse_args()
    rep = {}
    t0 = time.time(); e = build_expscan(); rep["expscan"] = dict(seconds=round(time.time() - t0, 1), keys=compare(e, SHIPPED_E))
    t0 = time.time(); g, vl = build_grating(a.verify_local)
    keys = ["traces_exp", "h_truth", "dt_PI", "dt_oracle", "dd", "hyb", "drive_exp", "setpoint_exp", "igain_exp",
            "P_all", "I_all", "fit_idx", "test_idx", "q_exp", "q_PI", "q_dd", "q_hyb", "rmse_PI", "rmse_dd",
            "rmse_hyb", "oracle_cond", "oracle_P", "oracle_I"]
    rep["grating"] = dict(seconds=round(time.time() - t0, 1), keys=compare(g, SHIPPED_G, keys),
                          not_regenerated=("loss_*, demo_*, example_*, three_examples_json, clean_*: diagnostic "
                                           "panels of the development figures, not used in the manuscript"),
                          local_fit_verification=vl)
    json.dump(rep, open(BOUT / "bundle_regeneration_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))
