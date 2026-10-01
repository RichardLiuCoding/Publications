"""Build a prediction bundle for the experimental-scans dataset Nature figures.

Reads the cached PI grid and data-driven alignment artifacts produced by
`Fit DT controller parameters to experimental scans.ipynb` and assembles a
condition-paired prediction bank for Figures 4 and 5.

Outputs `/tmp/expscan_predictions.npz` containing:
- traces_exp        (N, 2, 256)  experimental trace/retrace per condition
- dt_PI             (N, 2, 256)  DT trace/retrace with fitted PI
- dd                (N, 2, 256)  pure data-driven prediction (NaN if not in DD test set)
- hyb               (N, 2, 256)  DT + data-driven residual (NaN if not in DD test set)
- cond_keys         (N,)         "si_di_spi_gi" string identifiers
- si, di, spi, gi   per-condition indices
- drive_nm, setpoint, igain, scan_speed (per condition)
- P_dt, I_dt        (N,)         fitted DT PI labels per condition
- fit_idx           array of cond indices used to TRAIN the data-driven models
- test_idx          array of cond indices in the data-driven held-out set
- gp_train_idx      array of cond indices used to fit PI labels (GP train set)
- q_exp, q_PI, q_dd, q_hyb       (N,)  trace-retrace RMSE per condition
- rmse_PI, rmse_dd, rmse_hyb     (N,2) per-line RMSE of model vs experiment

Run with: python codes/expscan_build_predictions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import load


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR    = PROJECT_ROOT / "calibration_cache" / "dt_controller_fit"

# Default cache tag matches the notebook's CACHE_TAG = "balanced_g3_rms"
DEFAULT_TAG = "balanced_g3_rms"


def _per_line_rmse(pred, exp, trim=10):
    pred = np.asarray(pred, float); exp = np.asarray(exp, float)
    n = min(len(pred), len(exp))
    if n <= 2*trim+4:
        lo, hi = 0, n
    else:
        lo, hi = trim, n-trim
    sc = pred[lo:hi] - np.nanmean(pred[lo:hi])
    ec = exp[lo:hi]  - np.nanmean(exp[lo:hi])
    m  = np.isfinite(sc) & np.isfinite(ec)
    if m.sum() < 5: return np.nan
    return float(np.sqrt(np.nanmean((sc[m]-ec[m])**2)))


def _trace_retrace_rmse(tr, rt, trim=10):
    tr = np.asarray(tr, float); rt = np.asarray(rt, float)
    n = min(len(tr), len(rt))
    if n <= 2*trim+4: return np.nan
    t = tr[trim:n-trim] - np.nanmean(tr[trim:n-trim])
    r = rt[trim:n-trim] - np.nanmean(rt[trim:n-trim])
    m = np.isfinite(t) & np.isfinite(r)
    if m.sum() < 5: return np.nan
    return float(np.sqrt(np.nanmean((t[m]-r[m])**2)))


def main(tag: str = DEFAULT_TAG, out_path: str = "/tmp/expscan_predictions.npz"):
    pi_pack = load(CACHE_DIR / f"physics_guided_PI_grid_{tag}.joblib")
    dd_pack = load(CACHE_DIR / f"data_driven_alignment_{tag}.joblib")
    gp_fit  = pi_pack["gp_fit"]

    record_df = dd_pack["record_df"]
    Y_exp     = dd_pack["Y_exp"]
    Y_dt      = dd_pack["Y_dt"]
    train_mask = dd_pack["train_mask"]
    test_mask  = dd_pack["test_mask"]
    Y_direct_test = dd_pack["Y_direct_test"]
    Y_aligned_test = dd_pack["Y_aligned_test"]

    # The records are interleaved (trace, retrace) per cond_key (verified by inspection).
    # Build cond-level arrays by grouping.
    n_pix = Y_exp.shape[1]
    grouped = record_df.groupby("cond_key", sort=False)
    cond_keys = []
    si_arr, di_arr, spi_arr, gi_arr = [], [], [], []
    drive_arr, sp_arr, ig_arr, sr_arr = [], [], [], []
    P_arr, I_arr = [], []
    traces_exp = []   # (N, 2, n_pix)
    dt_PI = []
    dd_arr = []
    hyb_arr = []
    is_train = []
    is_test  = []

    # Direction index in test arrays — Y_direct_test / Y_aligned_test follow the order of
    # record_df rows masked by test_mask.  Build a row → test-array-index lookup.
    test_index = np.full(len(record_df), -1, dtype=int)
    test_pos = 0
    for i in range(len(record_df)):
        if test_mask[i]:
            test_index[i] = test_pos
            test_pos += 1

    for cond_key, sub in grouped:
        # Two rows expected: direction="trace" (sign -1) then "retrace" (sign +1).
        sub = sub.sort_values("direction_sign")  # trace (-1) first, retrace (+1) second
        if len(sub) != 2:
            continue
        i_trace, i_retr = sub.index.to_numpy()
        first = sub.iloc[0]
        cond_keys.append(cond_key)
        si_arr.append(int(first.si)); di_arr.append(int(first.di))
        spi_arr.append(int(first.spi)); gi_arr.append(int(first.gi))
        drive_arr.append(float(first.drive_nm)); sp_arr.append(float(first.setpoint))
        ig_arr.append(float(first.I_exp)); sr_arr.append(float(first.scan_speed_hat))
        P_arr.append(float(first.P_dt)); I_arr.append(float(first.I_dt))

        traces_exp.append(np.stack([Y_exp[i_trace], Y_exp[i_retr]], axis=0))
        dt_PI.append(np.stack([Y_dt[i_trace], Y_dt[i_retr]], axis=0))

        # Data-driven / hybrid: only available on the held-out set
        d_pair  = np.full((2, n_pix), np.nan)
        h_pair  = np.full((2, n_pix), np.nan)
        if test_mask[i_trace] and test_mask[i_retr]:
            d_pair[0] = Y_direct_test[test_index[i_trace]]
            d_pair[1] = Y_direct_test[test_index[i_retr]]
            h_pair[0] = Y_aligned_test[test_index[i_trace]]
            h_pair[1] = Y_aligned_test[test_index[i_retr]]
        dd_arr.append(d_pair); hyb_arr.append(h_pair)

        is_train.append(bool(train_mask[i_trace] and train_mask[i_retr]))
        is_test.append(bool(test_mask[i_trace] and test_mask[i_retr]))

    traces_exp = np.array(traces_exp)
    dt_PI      = np.array(dt_PI)
    dd_arr     = np.array(dd_arr)
    hyb_arr    = np.array(hyb_arr)
    fit_idx    = np.where(is_train)[0]
    test_idx   = np.where(is_test )[0]

    N = traces_exp.shape[0]
    print(f"Built {N} condition pairs   ({fit_idx.size} train, {test_idx.size} test)")

    # GP training conditions, mapped to indices in our condition list
    cond_to_idx = {(int(s), int(d), int(p), int(g)): i for i, (s,d,p,g)
                   in enumerate(zip(si_arr, di_arr, spi_arr, gi_arr))}
    gp_train_idx = []
    for c in gp_fit["train_conds"]:
        key = tuple(int(v) for v in c)
        if key in cond_to_idx:
            gp_train_idx.append(cond_to_idx[key])
    gp_train_idx = np.array(sorted(gp_train_idx), int)
    print(f"GP train cond indices found in record_df: {gp_train_idx.size} / {len(gp_fit['train_conds'])}")

    # Quality (trace–retrace RMSE) per condition
    def quality(arr):
        out = np.full(arr.shape[0], np.nan)
        for i in range(arr.shape[0]):
            if np.all(np.isfinite(arr[i])):
                out[i] = _trace_retrace_rmse(arr[i,0], arr[i,1])
        return out
    q_exp = quality(traces_exp)
    q_PI  = quality(dt_PI)
    q_dd  = quality(dd_arr)
    q_hyb = quality(hyb_arr)

    def line_rmse(arr):
        out = np.full((arr.shape[0], 2), np.nan)
        for i in range(arr.shape[0]):
            if np.any(np.isnan(arr[i])):
                continue
            out[i,0] = _per_line_rmse(arr[i,0], traces_exp[i,0])
            out[i,1] = _per_line_rmse(arr[i,1], traces_exp[i,1])
        return out

    rmse_PI  = line_rmse(dt_PI)
    rmse_dd  = line_rmse(dd_arr)
    rmse_hyb = line_rmse(hyb_arr)

    # Save
    out_path = Path(out_path)
    np.savez(out_path,
        cond_keys=np.array(cond_keys),
        si=np.array(si_arr), di=np.array(di_arr), spi=np.array(spi_arr), gi=np.array(gi_arr),
        drive=np.array(drive_arr), setpoint=np.array(sp_arr),
        igain=np.array(ig_arr), scan_speed=np.array(sr_arr),
        P_dt=np.array(P_arr), I_dt=np.array(I_arr),
        traces_exp=traces_exp, dt_PI=dt_PI, dd=dd_arr, hyb=hyb_arr,
        fit_idx=fit_idx, test_idx=test_idx, gp_train_idx=gp_train_idx,
        q_exp=q_exp, q_PI=q_PI, q_dd=q_dd, q_hyb=q_hyb,
        rmse_PI=rmse_PI, rmse_dd=rmse_dd, rmse_hyb=rmse_hyb,
    )
    print(f"Saved {out_path}")
    print("DT-vs-exp median per-line RMSE :", float(np.nanmedian(rmse_PI[test_idx])))
    print("DD  median per-line RMSE       :", float(np.nanmedian(rmse_dd[test_idx])))
    print("HYB median per-line RMSE       :", float(np.nanmedian(rmse_hyb[test_idx])))
    print()
    qe = q_exp[test_idx]
    for name, qm in [("PI", q_PI), ("DD", q_dd), ("HYB", q_hyb)]:
        mae = float(np.nanmean(np.abs(qe - qm[test_idx])))
        med = float(np.nanmedian(np.abs(qe - qm[test_idx])))
        print(f"held-out quality MAE/medAE {name:3s}: {mae:.3f} / {med:.3f} nm")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default=DEFAULT_TAG)
    p.add_argument("--out", default="/tmp/expscan_predictions.npz")
    a = p.parse_args()
    main(a.tag, a.out)
