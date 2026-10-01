"""Generate SI table blocks (spec format) from the analysis outputs (revision 2026-09)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from rv_benchmark import block_folds
from rv_common import OUT, REV

S = pd.read_csv(OUT / "tap300_benchmark_summary.csv")
B = json.load(open(OUT / "tap300_benchmark_bootstrap.json"))
G = json.load(open(OUT / "grating_benchmark.json"))
f = lambda x, d=3: f"{x:.{d}f}"
LAB = {"median": "Train median", "physics": "Physics twin, zero-fit", "physics_cal": "Physics twin, 2-parameter calibration",
       "knn_ctrl": "Controls, kNN", "ridge_ctrl": "Controls, ridge", "gbm_ctrl": "Controls, GBM",
       "ridge_ctrl_fd": "Controls + FD, ridge", "gbm_ctrl_fd": "Controls + FD, GBM", "hyb_ridge": "Physics + ridge residual",
       "hyb_gbm": "Physics + GBM residual", "hyb_mlp": "Physics + MLP residual"}


def block(tmpl, widths, rows, fs=18):
    return (f"@@ table {tmpl} {','.join(str(w) for w in widths)} fs={fs}\n"
            + "\n".join(" | ".join(r) for r in rows) + "\n")


def t_s2():
    z = np.load(OUT / "tap300_benchmark_speed.npz"); zs = np.load(OUT / "tap300_benchmark_setpoint.npz")
    sp_sizes = np.bincount(z["fold_of"]); st_sizes = np.bincount(zs["fold_of"])
    rows = [["System and scheme", "Held-out unit", "Folds", "Test conditions per fold", "Refitted inside each fold"],
            ["AlScN, blocked (primary)", "block of scan speed and drive (55 blocks)", "5", "179–181", "gain map, topography, scaling, models"],
            ["AlScN, unseen speed", "one scan speed", "5", f"{sp_sizes.min()}–{sp_sizes.max()}", "same"],
            ["AlScN, unseen setpoint", "one pair of adjacent setpoints", "4", f"{st_sizes.min()}–{st_sizes.max()}", "same"],
            ["AlScN, submitted split", "random conditions", "1", "225", "same (held-out conditions only)"],
            ["Grating, submitted split", "random conditions", "1", "20", "gain map, ridge models"],
            ["Grating, 5-fold CV", "random conditions", "5", "12", "same"],
            ["Grating, chronological", "last 20 acquisitions", "1", "20", "same"]]
    return block(11, [1.5, 1.7, 0.5, 1.1, 1.7], rows)


def t_s3():
    rows = [["Target", "Model", "Blocks MedAE [95% CI]", "ρ", "Speed MedAE", "ρ", "Setpoint MedAE", "ρ", "Submit. MedAE", "ρ"]]
    models = ["median", "physics", "physics_cal", "knn_ctrl", "ridge_ctrl", "gbm_ctrl", "ridge_ctrl_fd", "gbm_ctrl_fd",
              "hyb_ridge", "hyb_gbm", "hyb_mlp"]
    for t, tl, d in (("Q_align", "Q_{align} (nm)", 2), ("Q_safety", "load proxy", 3)):
        for m in models:
            r = [tl if m == "median" else "", LAB[m]]
            for sc in ("block5", "speed", "setpoint", "submitted"):
                row = S[(S.scheme == sc) & (S.target == t) & (S.model == m)].iloc[0]
                if sc == "block5":
                    lo, hi = B["block5"][t][m]["MedAE_CI"]
                    r.append(f"{f(row.MedAE, d)} [{f(lo, d)}, {f(hi, d)}]")
                else:
                    r.append(f(row.MedAE, d))
                r.append("–" if not np.isfinite(row.rho) else f"{row.rho:+.2f}".replace("-", "−"))
            rows.append(r)
    rows = [[c.replace("Q_{align}", "Q_{align}") for c in r] for r in rows]
    return block(11, [0.55, 1.3, 1.12, 0.45, 0.52, 0.45, 0.58, 0.45, 0.58, 0.45], rows, fs=14)


def t_s4():
    rows = [["Target", "Model", "Loss", "MedAE", "MAE", "ρ"]]
    spec = [("gbm_ctrl_fd", "Controls + FD, GBM", "selected"), ("gbm_ctrl_fd_sq", "Controls + FD, GBM", "squared"),
            ("gbm_ctrl_fd_abs", "Controls + FD, GBM", "absolute"), ("hyb_gbm", "Physics + GBM residual", "selected"),
            ("hyb_gbm_sq", "Physics + GBM residual", "squared"), ("hyb_gbm_abs", "Physics + GBM residual", "absolute"),
            ("hyb_ridge_sq", "Physics + ridge residual", "squared"), ("hyb_ridge_huber", "Physics + ridge residual", "Huber")]
    for t, tl, d in (("Q_align", "Q_{align} (nm)", 3), ("Q_safety", "load proxy", 4)):
        for i, (m, lab, loss) in enumerate(spec):
            row = S[(S.scheme == "block5") & (S.target == t) & (S.model == m)].iloc[0]
            rows.append([tl if i == 0 else "", lab, loss, f(row.MedAE, d), f(row.MAE, d if t == "Q_safety" else 1), f"{row.rho:+.3f}".replace("-", "−")])
    return block(11, [1.0, 1.9, 0.9, 0.9, 0.9, 0.9], rows)


def t_s5():
    rows = [["Split", "Model", "Q_{align} MAE (nm)", "Q_{align} MedAE (nm)", "Line RMSE, median (nm)", "Line RMSE, mean (nm)"]]
    nm = {"submitted": "Submitted 40/20", "cv5": "5-fold CV (n = 60)", "chrono": "Chronological (last 20)"}
    for s_ in ("submitted", "cv5", "chrono"):
        for i, (k, lab) in enumerate((("physics", "Physics"), ("data", "Data-driven"), ("hybrid", "Hybrid"))):
            o = G[s_][k]
            rows.append([nm[s_] if i == 0 else "", lab, f(o["Q_MAE"], 2), f(o["Q_MedAE"], 2), f(o["line_RMSE_median"], 1), f(o["line_RMSE_mean"], 1)])
    a = G["submitted_archived_bundle"]
    rows.append(["Submitted, archived (shift-aligned)", "Physics / Data / Hybrid",
                 " / ".join(f(a[k]["Q_MAE"], 2) for k in ("physics", "data", "hybrid")), "–",
                 " / ".join(f(a[k]["line_RMSE_median"], 1) for k in ("physics", "data", "hybrid")), "–"])
    for s_ in ("submitted", "cv5", "chrono"):
        c = G[s_]["paired_bootstrap_95CI"]
        rows.append([f"{nm[s_]}: paired 95% CI", "Q MAE phys − hyb; data − hyb; phys − data",
                     "; ".join(f"[{c[k][0]:.1f}, {c[k][1]:.1f}]" for k in ("Q_MAE phys-hyb", "Q_MAE data-hyb", "Q_MAE phys-data")),
                     "", "line phys − hyb; data − hyb", "; ".join(f"[{c[k][0]:.1f}, {c[k][1]:.1f}]" for k in ("lineRMSE_med phys-hyb", "lineRMSE_med data-hyb"))])
    return block(11, [1.35, 1.35, 1.2, 0.8, 1.0, 0.8], rows, fs=16)


def t_s6():
    A = json.load(open(OUT / "step2_cv_tap300.json")); M = json.load(open(OUT / "step2_cv_multi75.json"))
    rows = [["Anchor", "Unit", "AlScN n", "AlScN median |error|", "Grating n", "Grating median |error|"]]
    lab = {"A0": ("A_{0}", "nm"), "d_AR": ("d_{AR}", "nm"), "A_AR": ("A_{AR}", "nm"), "d_phimax": ("d_{φmax}", "nm"),
           "d_50": ("d_{50}", "nm"), "d_70": ("d_{70}", "nm"), "d_contact": ("d_{contact}", "nm"),
           "phi_att": ("φ_{att}", "deg"), "phi_rep": ("φ_{rep}", "deg"), "phi_max": ("φ_{max}", "deg"), "phi_baseline": ("φ_{base}", "deg")}
    for k, (l, u) in lab.items():
        ea = A["per_anchor_median_abs_err_phys"].get(k); em = M["per_anchor_median_abs_err_phys"].get(k)
        rows.append([l, u, str(A["per_anchor_n"].get(k, 0)), "–" if ea is None else f(ea, 2),
                     str(M["per_anchor_n"].get(k, 0)), "–" if em is None else f(em, 2)])
    rows.append(["Tier-weighted MAE (z), all curves", "–", "30", f(A["tier_weighted_MAE_z"]["all"], 3), "15", f(M["tier_weighted_MAE_z"]["all"], 3)])
    rows.append(["Same, curves never used for selection", "–", "22", f(A["tier_weighted_MAE_z"]["orig_train_curves"], 3), "11", f(M["tier_weighted_MAE_z"]["orig_train_curves"], 3)])
    rows.append(["Train-median predictor", "–", "30", f(A["train_median_prior_MAE_z"]["all"], 3), "15", f(M["train_median_prior_MAE_z"]["all"], 3)])
    rows.append(["Submitted single split (for reference)", "–", "8", "0.187", "4", "0.172"])
    return block(11, [2.0, 0.5, 0.7, 1.2, 0.8, 1.3], rows)


def t_s7():
    rows = [["Dataset", "Acquisition", "Cantilever (recorded)", "Content", "Archive file"],
            ["AlScN grid scans", "7–8 May 2026", "Tap-300 class; k = 18.96 N m^{−1}; f = 256.5 kHz", "5 speeds × 11 drives × 8 setpoints × 5 gains; 3 lines × 8 channels × 256 px", "260507-300kHz-AlScN.npz"],
            ["AlScN FD library", "14 May 2026", "same type; k = 21.32 N m^{−1}; f = 270.6 kHz", "30 approach and retract curves", "Tap300_AlScN.npz (from 31 IBW files)"],
            ["AlScN reference image", "7 May 2026, 11:24", "as grid", "topography image (AmpInvOLS for drive conversion; rows for gain fits)", "Image0002.ibw"],
            ["Grating MOBO scans", "15 March 2025", "k = 24.5 N m^{−1}; f = 297.1 kHz", "60 conditions (10 seeds + 50 BO steps); 5 lines × 8 channels × 256 px", "250315_Cali1_MOBO.pickle"],
            ["Grating FD library", "15 March 2025, 22:44, before scans", "as grating scans", "15 curves", "cali_fd.npz (from 15 IBW files)"],
            ["Controller-gain fits", "computed", "–", "AlScN: 80 local fits (52 in the analysed set); grating: 40", "calibration_cache/*.joblib"]]
    return block(11, [1.2, 1.1, 1.45, 1.75, 1.0], rows, fs=16)


if __name__ == "__main__":
    out = {"S2": t_s2(), "S3": t_s3(), "S4": t_s4(), "S5": t_s5(), "S6": t_s6(), "S7": t_s7()}
    json.dump(out, open(REV / "manuscript" / "si_tables.json", "w"), indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(k, v[:400], "\n")
