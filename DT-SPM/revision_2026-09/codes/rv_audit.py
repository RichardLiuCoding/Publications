"""Leakage audit of the SUBMITTED Step-3b corrections (revision 2026-09).

1. Executes the submitted full-pipeline notebook (DT-SPM_colab/DT-SPM_full_digital_twin.ipynb,
   code cells 1-52, unmodified except that FIG_DIR is redirected to revision_2026-09/output/
   audit_run so no shipped artifact is overwritten) and then perturbs ONLY the target
   condition's measured line at inference:
     permuted : target line replaced by the measured line of another held-out condition
     masked   : target line replaced by the scanner line of the same condition
   A pre-acquisition predictor must be invariant to both perturbations.
2. Re-runs codes/_qsafety_ap.py (output path redirected) and applies the same test to the
   force-based Q_safety correction.
3. Counts exposure of held-out conditions inside training windows and the overlap of the
   controller-calibration set with the held-out set.
Writes output/audit_summary.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
from scipy.stats import spearmanr

from rv_common import OUT, ROOT

COLAB = ROOT / "DT-SPM_colab"
RUN = OUT / "audit_run"
RUN.mkdir(parents=True, exist_ok=True)


def _m(y, p):
    e = np.abs(p - y)
    return dict(MedAE=float(np.median(e)), MAE=float(np.mean(e)),
                rho=float(spearmanr(y, p).statistic))


def audit_step3b(summary):
    import nbformat
    nb = nbformat.read(COLAB / "DT-SPM_full_digital_twin.ipynb", as_version=4)
    code = [c for c in nb.cells]
    os.chdir(COLAB)
    import types
    mod = types.ModuleType("__audit_nb__"); sys.modules["__audit_nb__"] = mod
    ns = mod.__dict__
    t0 = time.time()
    for i, c in enumerate(code):
        if c.cell_type != "code" or i > 52:        # stop before the REPORT cell overwrites state
            continue
        exec(compile(c.source, f"<cell {i}>", "exec"), ns)
        if i == 3:                                   # redirect outputs before anything is written
            ns["FIG_DIR"] = RUN
    print(f"notebook cells executed in {time.time()-t0:.0f} s", flush=True)
    import torch
    model, mk, test_w, win_cond = ns["model"], ns["make_window"], ns["test_w"], ns["win_cond"]
    Qs, Qe, q_sc = ns["Q_scanner"], ns["Q_exp"], ns["q_sc"]
    sl, el = ns["scanner_lines"], ns["exp_lines"]

    def predict(ex):
        sc = np.stack([mk(i)[1] for i in test_w]); sq = np.stack([mk(i)[2] for i in test_w])
        with torch.no_grad():
            dQ = model(torch.tensor(ex, dtype=torch.float32), torch.tensor(sc, dtype=torch.float32),
                       torch.tensor(sq, dtype=torch.float32)).numpy()
        return Qs[test_w] + dQ * q_sc[None, :]

    ex_true = np.stack([mk(i)[0] for i in test_w])
    base = predict(ex_true)
    rng = np.random.default_rng(0)
    perm = rng.permutation(test_w)
    ex_perm = ex_true.copy(); ex_perm[:, -1] = el[perm]
    ex_mask = ex_true.copy(); ex_mask[:, -1] = sl[test_w]
    y = Qe[test_w, 0]
    res = {"n_test_windows": int(test_w.size), "n_train_windows": int(win_cond.size - test_w.size),
           "prior_recal": _m(y, Qs[test_w, 0]), "submitted_corrected": _m(y, base[:, 0]),
           "target_line_permuted": _m(y, predict(ex_perm)[:, 0]),
           "target_line_masked": _m(y, predict(ex_mask)[:, 0]),
           "prior_raw": _m(y, ns["Q_scanner_raw"][test_w, 0])}
    # exposure: held-out condition ids appearing anywhere in a TRAINING window's inputs
    K = ns["K"]; test_idx = set(np.asarray(ns["test_idx"]).tolist())
    train_w = np.setdiff1d(win_cond, test_w)
    seen = set()
    for e_ in train_w:
        seen.update(range(max(0, e_ - K + 1), e_ + 1))
    res["heldout_ids_in_training_inputs"] = int(len(seen & test_idx))
    res["n_heldout_ids"] = len(test_idx)
    summary["step3b_Q_align"] = res
    print(json.dumps(res, indent=1), flush=True)


def audit_qsafety(summary):
    src = (ROOT / "codes" / "_qsafety_ap.py").read_text()
    src = src.replace('OUTNPZ = FIG_T / "qsafety_ap.npz"',
                      f'OUTNPZ = Path(r"{RUN / "qsafety_ap_audit.npz"}")')
    ns = {"__name__": "__audit__", "__file__": str(ROOT / "codes" / "_qsafety_ap.py")}
    exec(compile(src, "_qsafety_ap.py", "exec"), ns)
    import torch
    model, lines, feat_t, widx_t = ns["model"], ns["lines"], ns["feat_t"], ns["widx_t"]
    win_cond, is_te_w = ns["win_cond"], ns["is_te_w"]
    Qp, Qe, iqr, med = ns["Q_prior"], ns["Q_exp"], ns["iqr"], ns["med"]
    te = win_cond[is_te_w]

    def predict(L):
        with torch.no_grad():
            enc = model.encode(torch.tensor(L))
            dz = model.predict(enc, feat_t, widx_t).numpy()
        return (Qp[win_cond] + dz * iqr + med)[is_te_w]

    base = predict(lines)
    rng = np.random.default_rng(0)
    Lp = lines.copy(); Lp[te] = lines[rng.permutation(te)]
    y = Qe[te]
    res = {"n_test_windows": int(te.size), "prior": _m(y, Qp[te]),
           "submitted_corrected": _m(y, base), "target_lines_permuted": _m(y, predict(Lp)),
           "direct_calculation_from_measured_channels": {"MedAE": 0.0, "MAE": 0.0, "rho": 1.0}}
    summary["qsafety_force"] = res
    print(json.dumps(res, indent=1), flush=True)


def audit_calibration(summary):
    b = np.load(ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz")
    te = set(b["test_idx"].tolist()); gpt = set(b["gp_train_idx"].tolist())
    from joblib import load
    p = load(ROOT / "calibration_cache" / "dt_controller_fit" / "physics_guided_PI_grid_balanced_g3_rms.joblib")
    summary["controller_calibration"] = {
        "local_PI_fits_total": len(p["gp_fit"]["train_local"]),
        "local_fits_inside_900_condition_set": len(gpt),
        "local_fits_on_heldout_conditions": len(gpt & te),
        "gp_alpha": p["gp_fit"]["cfg"]["gp_alpha"],
        "reference_topography": "median of all 1320 measured trace lines (includes the 225 held-out conditions)",
        "rms_normalisation": "median RMS over all 1320 measured conditions (includes held-out)",
    }


if __name__ == "__main__":
    import torch
    torch.set_num_threads(2)
    S = {}
    audit_calibration(S)
    audit_qsafety(S)
    audit_step3b(S)
    json.dump(S, open(OUT / "audit_summary.json", "w"), indent=1)
    print("saved", OUT / "audit_summary.json")
