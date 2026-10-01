"""Revised manuscript and SI figures (revision 2026-09). Every panel reads only files
written by the rv_*.py analysis scripts in revision_2026-09/output (or the archived
submission artifacts where stated). python rv_figures.py [fig4 fig5 fig6 fig7 si]
"""
from __future__ import annotations

import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from rv_common import FIG, OUT, ROOT

sys.path.insert(0, str(ROOT / "codes"))
import _nature_style as ns                                                  # noqa: E402
from _nature_style import BLUE, DARK, GREEN, GREY, ORANGE, PURPLE, SKY, VERMI   # noqa: E402

ns.apply()
FIG.mkdir(parents=True, exist_ok=True)
DPI = 600


def panel(ax, letter, dx=-0.015, dy=1.03):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=9, fontweight="bold",
            va="bottom", ha="right", color=DARK)


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


LABEL = {"median": "train median", "physics": "physics twin (zero-fit)",
         "physics_cal": "physics twin, 2-param. cal.", "knn_ctrl": "controls, kNN",
         "ridge_ctrl": "controls, ridge", "gbm_ctrl": "controls, GBM",
         "gbm_ctrl_fd": "controls + FD, GBM", "hyb_ridge": "physics + ridge residual",
         "hyb_gbm": "physics + GBM residual", "hyb_mlp": "physics + MLP residual"}
KIND = {"median": GREY, "physics": BLUE, "physics_cal": BLUE, "knn_ctrl": ORANGE,
        "ridge_ctrl": ORANGE, "gbm_ctrl": ORANGE, "gbm_ctrl_fd": ORANGE,
        "hyb_ridge": GREEN, "hyb_gbm": GREEN, "hyb_mlp": GREEN}


def boot():
    return json.load(open(OUT / "tap300_benchmark_bootstrap.json"))


def summary():
    return pd.read_csv(OUT / "tap300_benchmark_summary.csv")


# ===================================================================== Fig 3 (annotation wording only)
def fig3():
    """Re-render the submitted Fig. 3 (codes/_make_manuscript_figures_v2.make_fig2) with the panel-c
    annotation reworded from 'force' to the dimensionless interaction-load proxy."""
    import inspect, types
    import _make_manuscript_figures_v2 as mm
    src = inspect.getsource(mm.make_fig2)
    old = '"$Q_{safety}$ = force from amplitude\\nreduction ($A_0$−A) and repulsive\\nphase (φ<90°);  higher = less safe"'
    new = '"$Q_{safety}$: interaction-load proxy from\\namplitude reduction ($A_0$−A)/$A_0$ and\\nrepulsive phase (φ<90°); higher = more load"'
    assert old in src, "annotation string not found"
    src = src.replace(old, new).replace('OUT / "fig2_descriptors_Q.png"', 'FIGOUT / "Fig3_rev.png"')
    src = src.replace("force (setpoint", "interaction load (setpoint")
    src = src.replace('FIGOUT / "Fig3_rev.png", bbox_inches="tight")', 'FIGOUT / "Fig3_rev.png", bbox_inches="tight", dpi=600)')
    ns_ = dict(mm.__dict__); ns_["FIGOUT"] = FIG
    exec(compile(src, "make_fig2_rev", "exec"), ns_)
    ns_["make_fig2"]()

# ===================================================================== Fig 4
def fig4():
    systems = [("Multi-75", "multi75", BLUE), ("Tap-300", "tap300", VERMI)]
    fig = plt.figure(figsize=(7.2, 4.7))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.55, wspace=0.34)
    groups = [("Distance anchors (nm)", ["d_AR", "d_50", "d_70", "d_phimax"], (0, 0)),
              ("Phase anchors (°)", ["phi_max", "phi_att", "phi_rep"], (0, 1))]
    for title, cols, pos in groups:
        ax = fig.add_subplot(gs[pos]); allv = []
        for name, key, c in systems:
            z = np.load(OUT / f"step2_cv_{key}" / "cv_predictions.npz")
            vocab = [str(v) for v in z["vocab"]]; tgt, prd = z["target"], z["pred_phys"]
            orig_te = z["orig_test"]
            xs, ys, fill = [], [], []
            for col in cols:
                j = vocab.index(col); m = np.isfinite(tgt[:, j]) & np.isfinite(prd[:, j])
                xs += list(tgt[m, j]); ys += list(prd[m, j])
                fill += list(np.isin(np.where(m)[0], orig_te))
            xs, ys, fill = map(np.asarray, (xs, ys, fill))
            allv += list(xs) + list(ys)
            ax.scatter(xs[~fill], ys[~fill], s=13, facecolors=c, edgecolors=c, lw=0.6, alpha=0.8, zorder=3)
            ax.scatter(xs[fill], ys[fill], s=16, facecolors="none", edgecolors=DARK, lw=0.7, zorder=4)
        lo, hi = np.nanpercentile(allv, 1), np.nanpercentile(allv, 99)
        pad = 0.08 * (hi - lo); lo, hi = lo - pad, hi + pad
        ax.plot([lo, hi], [lo, hi], color=GREY, ls="--", lw=0.8, zorder=1)
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_xlabel("Extracted from measured curve"); ax.set_ylabel("Encoder prediction (held out)")
        ax.set_title(title, fontsize=7.4, pad=3)
        panel(ax, "a" if pos[1] == 0 else "b")
    hnd = [plt.Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=5, label="Multi-75"),
           plt.Line2D([], [], marker="o", ls="", mfc=VERMI, mec=VERMI, ms=5, label="Tap-300"),
           plt.Line2D([], [], marker="o", ls="", mfc="none", mec=DARK, ms=5,
                      label="curves in the submitted held-out split")]
    fig.legend(handles=hnd, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=3, fontsize=6.8,
               handletextpad=0.2, columnspacing=1.2)
    ax = fig.add_subplot(gs[1, :])
    anchors = ["A0", "d_AR", "A_AR", "d_phimax", "d_50", "d_70", "phi_att", "phi_rep", "phi_max", "phi_baseline"]
    labels = [r"$A_0$ (nm)", r"$d_{AR}$ (nm)", r"$A_{AR}$ (nm)", r"$d_{\phi max}$ (nm)", r"$d_{50}$ (nm)",
              r"$d_{70}$ (nm)", r"$\phi_{att}$ (°)", r"$\phi_{rep}$ (°)", r"$\phi_{max}$ (°)", r"$\phi_{base}$ (°)"]
    x = np.arange(len(anchors)); w = 0.38
    for k, (name, key, c) in enumerate(systems):
        r = json.load(open(OUT / f"step2_cv_{key}.json"))
        err = [r["per_anchor_median_abs_err_phys"].get(a) or np.nan for a in anchors]
        n = [r["per_anchor_n"].get(a, 0) for a in anchors]
        ax.bar(x + (k - 0.5) * w, err, w, color=c, lw=0, label=f"{name} ({r['n_curves']} curves)")
        for xi, e, nn in zip(x + (k - 0.5) * w, err, n):
            if np.isfinite(e):
                ax.text(xi, e + 0.08, f"{nn}", ha="center", fontsize=5.4, color=DARK)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=6.8)
    ax.set_ylabel("Cross-validated median\n|error| (nm or °)")
    ax.set_ylim(0, 3.2); ax.axvline(5.5, color=GREY, lw=0.5, ls=":")
    ax.legend(loc="upper left", fontsize=6.8)
    ax.text(0.99, 0.95, "numbers above bars: curves with a defined anchor",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.0, color=DARK)
    panel(ax, "c")
    save(fig, "Fig4_rev")

# ===================================================================== Fig 5
def fig5():
    z = np.load(OUT / "mechanism_block5.npz"); M = json.load(open(OUT / "mechanism_block5.json"))
    fd = np.load(ROOT / "output" / "Tap300_AlScN.npz")
    sp, sde, sdt, y, amp = z["setpoint"], z["sd_exp"], z["sd_twin"], z["Q_align"], z["amp"]
    fig = plt.figure(figsize=(7.2, 5.0))
    gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.38)
    # a
    ax = fig.add_subplot(gs[0, 0])
    rng = np.random.RandomState(0); jit = (rng.rand(sp.size) - 0.5) * 0.035
    ax.scatter(sp + jit - 0.012, np.clip(sde, 0.5, None), s=5, color=DARK, alpha=0.35, lw=0, label="experiment")
    ax.scatter(sp + jit + 0.012, np.clip(sdt, 0.5, None), s=5, color=SKY, alpha=0.45, lw=0,
               label="deterministic twin (calibrated outside block)")
    u = np.unique(sp)
    for arr, c, off in [(sde, DARK, -0.012), (sdt, BLUE, 0.012)]:
        ax.plot(u + off, [np.nanmedian(arr[sp == s]) for s in u], "-", color=c, lw=1.0)
        ax.plot(u + off, [np.nanpercentile(arr[sp == s], 90) for s in u], "--", color=c, lw=0.8)
    ax.set_yscale("log"); ax.set_ylim(1, 400)
    ax.set_xlabel("Setpoint (fraction of $A_0$)"); ax.set_ylabel("Scan-line s.d. (nm)")
    ax.legend(loc="upper left", fontsize=6.2, markerscale=1.6, frameon=True, facecolor="white",
              framealpha=0.9, edgecolor="none")
    ax.text(0.98, 0.04, "solid: median   dashed: 90th percentile", transform=ax.transAxes,
            ha="right", fontsize=5.8, color=DARK)
    panel(ax, "a")
    # b
    ax = fig.add_subplot(gs[0, 1])
    keys = [("setpoint", "setpoint\nalone", PURPLE), ("controls_kNN", "controls\n(kNN)", ORANGE),
            ("deterministic_twin", "deterministic\ntwin", SKY), ("global_gain_resim", "global-gain\nre-sim.", GREY),
            ("amplification_factor", "amplification\n1/|A′($d_{op}$)|", BLUE)]
    for i, (k, lab, c) in enumerate(keys):
        r = M[k]["rho"]; lo, hi = M[k]["CI"]
        ax.bar(i, r, color=c, width=0.62, lw=0)
        ax.errorbar(i, r, yerr=[[r - lo], [hi - r]], fmt="none", ecolor=DARK, elinewidth=0.6, capsize=1.5)
        ax.text(i, (hi + 0.05) if r >= 0 else (lo - 0.12), f"{r:+.2f}", ha="center", fontsize=6.6)
    ax.axhline(0, color=DARK, lw=0.6)
    ax.set_xticks(range(len(keys))); ax.set_xticklabels([k[1] for k in keys], fontsize=6.0)
    ax.set_ylabel("Spearman ρ with measured $Q_{align}$"); ax.set_ylim(-0.6, 1.15)
    ax.set_title("Held-out blocks, n = 900, 95% CI", fontsize=6.6, pad=3)
    panel(ax, "b")
    # c
    ax = fig.add_subplot(gs[1, 0])
    fA0 = np.nanmean(fd["amp"][:, -10:], axis=1); b = np.load(ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz")
    i_mid = int(np.argmin(np.abs(fA0 - np.median(b["drive"]))))
    d_, A_ = fd["height"][i_mid], fd["amp"][i_mid]
    o = np.argsort(d_); d_, A_ = d_[o], A_[o]; m = np.isfinite(d_) & np.isfinite(A_); d_, A_ = d_[m], A_[m]
    A0_ = np.nanmean(A_[-10:])
    ax.plot(d_, A_, color=BLUE, lw=1.2)
    for s_, col, xo, yo in [(0.3, GREEN, 9.0, 0.4), (0.8, VERMI, 8.0, -1.6)]:
        c = np.where(np.diff(np.sign(A_ - s_ * A0_)) != 0)[0][0]
        dop = d_[c]
        ax.plot([dop], [s_ * A0_], "o", color=col, ms=4.2, zorder=4)
        ax.annotate(f"setpoint {s_:g}", (dop, s_ * A0_), xytext=(dop + xo, s_ * A0_ + yo), fontsize=6.4,
                    color=col, va="center", arrowprops=dict(arrowstyle="->", color=col, lw=0.6))
    ax.set_xlabel("Tip–sample distance, d (nm)"); ax.set_ylabel("Amplitude, A (nm)")
    ax.set_xlim(d_.min(), np.percentile(d_, 98))
    ax.set_title("Measured FD curve: slope flattens toward $A_0$", fontsize=6.6, pad=3)
    panel(ax, "c")
    # d
    ax = fig.add_subplot(gs[1, 1])
    m = np.isfinite(amp) & (y > 0)
    sc_ = ax.scatter(amp[m], y[m], c=sp[m], cmap="viridis", s=6, alpha=0.7, lw=0)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Zero-fit amplification 1/|dA/dd|($d_{op}$)"); ax.set_ylabel("Measured $Q_{align}$ (nm)")
    r = M["amplification_factor"]
    ax.text(0.03, 0.96, f"ρ = {r['rho']:+.2f} [{r['CI'][0]:.2f}, {r['CI'][1]:.2f}], n = {r['n']}",
            transform=ax.transAxes, va="top", fontsize=6.4, color=DARK,
            bbox=dict(fc="white", ec=BLUE, lw=0.4, alpha=0.9, pad=2.0))
    cb = fig.colorbar(sc_, ax=ax, fraction=0.05, pad=0.02); cb.set_label("setpoint", fontsize=6.4)
    cb.ax.tick_params(labelsize=6)
    panel(ax, "d")
    save(fig, "Fig5_rev")


# ===================================================================== Fig 6
def _hbar(ax, sc, target, models, B, S, xlabel, logx=False):
    d = S[(S.scheme == sc) & (S.target == target)].set_index("model")
    y = np.arange(len(models))[::-1]
    for yi, m in zip(y, models):
        med = d.loc[m, "MedAE"]; lo, hi = B[sc][target][m]["MedAE_CI"]
        ax.barh(yi, med, color=KIND[m], height=0.62, lw=0, alpha=0.9)
        ax.errorbar(med, yi, xerr=[[med - lo], [hi - med]], fmt="none", ecolor=DARK, elinewidth=0.6, capsize=1.5)
        ax.text(1.02, yi, f"{d.loc[m, 'rho']:+.2f}", transform=ax.get_yaxis_transform(), va="center",
                fontsize=6.4, color=DARK)
    ax.set_yticks(y); ax.set_yticklabels([LABEL[m] for m in models], fontsize=6.6)
    ax.set_xlabel(xlabel)
    if logx:
        ax.set_xscale("log")
    ax.text(1.02, 1.0, "ρ", transform=ax.transAxes, fontsize=7, fontweight="bold", va="bottom")


def fig6():
    A = json.load(open(OUT / "audit_summary.json"))["step3b_Q_align"]
    S = summary(); B = boot()
    fig = plt.figure(figsize=(7.2, 5.4))
    W, H = 0.25, 0.33                               # axes width / height (figure fraction)
    axa = fig.add_axes([0.235, 0.56, W, H]); axb = fig.add_axes([0.715, 0.56, W, H])
    axc = fig.add_axes([0.235, 0.08, W, H]); axd = fig.add_axes([0.64, 0.08, 0.27, H])
    # a - retrospective audit of the submitted correction
    ax = axa
    sub = S[(S.scheme == "submitted") & (S.target == "Q_align")].set_index("model")
    rows = [("scanner prior, raw", A["prior_raw"], GREY),
            ("scanner prior, ridge-recal.", A["prior_recal"], GREY),
            ("submitted, true target line", A["submitted_corrected"], VERMI),
            ("submitted, target permuted", A["target_line_permuted"], "#F2B8A0"),
            ("submitted, target masked", A["target_line_masked"], "#F2B8A0"),
            ("causal: controls, GBM", dict(MedAE=sub.loc["gbm_ctrl", "MedAE"], rho=sub.loc["gbm_ctrl", "rho"]), ORANGE)]
    y = np.arange(len(rows))[::-1]
    for yi, (lab, r, c) in zip(y, rows):
        ax.barh(yi, r["MedAE"], color=c, height=0.62, lw=0)
        ax.text(1.03, yi, f"{r['rho']:+.2f}", transform=ax.get_yaxis_transform(), va="center", fontsize=6.4)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=6.5)
    ax.set_xscale("log"); ax.set_xlabel("Median |error|, $Q_{align}$ (nm)")
    ax.text(1.03, 1.01, "ρ", transform=ax.transAxes, fontsize=7, fontweight="bold", va="bottom")
    ax.set_title("Submitted split (215 held-out windows)", fontsize=6.8, pad=3)
    # b - Q_align blocked CV
    models = ["median", "physics", "physics_cal", "knn_ctrl", "gbm_ctrl", "gbm_ctrl_fd", "hyb_gbm", "hyb_mlp"]
    _hbar(axb, "block5", "Q_align", models, B, S, "Median |error|, $Q_{align}$ (nm)", logx=True)
    axb.set_title("$Q_{align}$, held-out speed–drive blocks", fontsize=6.8, pad=3)
    # c - Q_safety blocked CV
    models_s = ["median", "physics", "physics_cal", "ridge_ctrl", "gbm_ctrl", "hyb_ridge", "hyb_gbm", "hyb_mlp"]
    _hbar(axc, "block5", "Q_safety", models_s, B, S, "Median |error|, load proxy", logx=True)
    axc.set_title("Load proxy, held-out speed–drive blocks", fontsize=6.8, pad=3)
    # d - parity of the best causal Q_align model, coloured by setpoint
    z = np.load(OUT / "tap300_benchmark_block5.npz")
    yq = z["Q_align"]; p = 10 ** z["Q_align__gbm_ctrl"]; sp = z["setpoint"]
    ax = axd
    sc_ = ax.scatter(np.clip(yq, 0.1, None), np.clip(p, 0.1, None), c=sp, cmap="viridis", s=6, lw=0, alpha=0.8)
    ax.plot([0.1, 5000], [0.1, 5000], color=GREY, ls="--", lw=0.7)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.1, 5000); ax.set_ylim(0.1, 5000)
    ax.set_xlabel("Measured $Q_{align}$ (nm)"); ax.set_ylabel("Predicted before scan (nm)")
    cax = fig.add_axes([0.925, 0.08, 0.012, H])
    cb = fig.colorbar(sc_, cax=cax); cb.set_label("setpoint", fontsize=6.6); cb.ax.tick_params(labelsize=6)
    ax.set_title("Controls, GBM; held-out blocks", fontsize=6.8, pad=3)
    for letter, (x, yy) in zip("abcd", [(0.01, 0.93), (0.49, 0.93), (0.01, 0.45), (0.555, 0.45)]):
        fig.text(x, yy, letter, fontsize=9, fontweight="bold", color=DARK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GREY, BLUE, ORANGE, GREEN)]
    fig.legend(handles, ["baseline", "physics only", "data only", "physics + learned residual"],
               loc="upper center", ncol=4, bbox_to_anchor=(0.55, 1.0), fontsize=6.8)
    save(fig, "Fig6_rev")

# ===================================================================== Fig 7
def fig7():
    S = summary(); G = json.load(open(OUT / "grating_benchmark.json"))
    gz = np.load(OUT / "grating_benchmark.npz")
    lc = pd.read_csv(OUT / "tap300_learning_curve.csv")
    fig = plt.figure(figsize=(7.2, 5.6))
    gs = fig.add_gridspec(2, 3, hspace=0.62, wspace=0.58, height_ratios=[1, 0.9])
    # a - load proxy: interpolation vs extrapolation
    ax = fig.add_subplot(gs[0, 0])
    models = ["physics", "ridge_ctrl", "gbm_ctrl", "hyb_ridge", "hyb_gbm", "hyb_mlp"]
    cols = [BLUE, "#F5C26B", ORANGE, "#7FD1B9", GREEN, "#006B4F"]
    schemes = [("block5", "held-out\nblocks"), ("speed", "unseen\nspeed"), ("setpoint", "unseen\nsetpoint")]
    w = 0.13
    for j, (m, c) in enumerate(zip(models, cols)):
        v = [S[(S.scheme == sc) & (S.target == "Q_safety") & (S.model == m)]["MedAE"].values[0] for sc, _ in schemes]
        short = {"physics": "physics", "ridge_ctrl": "ridge", "gbm_ctrl": "GBM", "hyb_ridge": "phys.+ridge",
                 "hyb_gbm": "phys.+GBM", "hyb_mlp": "phys.+MLP"}
        ax.bar(np.arange(3) + (j - 2.5) * w, v, w, color=c, lw=0, label=short[m])
    ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in schemes], fontsize=6.4)
    ax.set_yscale("log"); ax.set_ylabel("Median |error|, load proxy")
    ax.legend(fontsize=5.2, loc="upper left", ncol=2, handlelength=0.9, columnspacing=0.6,
              borderaxespad=0.1)
    ax.set_ylim(3e-3, 30)
    ax.set_title("AlScN: interpolation vs extrapolation", fontsize=6.4, pad=3, loc="right")
    panel(ax, "a")
    # b - learning curve, unseen-setpoint scheme
    ax = fig.add_subplot(gs[0, 1])
    d = lc[(lc.scheme == "setpoint") & (lc.target == "Q_safety")].copy()
    d["nn"] = np.where(d.n > 600, 700, d.n)
    for m, c, lab in [("physics", BLUE, "physics (zero-fit)"), ("gbm", ORANGE, "controls, GBM"),
                      ("ridge", "#F5C26B", "controls, ridge"), ("hyb_gbm", GREEN, "physics + GBM residual"),
                      ("hyb_ridge", "#7FD1B9", "physics + ridge residual")]:
        g = d[d.model == m].groupby("nn")["MedAE"].median()
        ax.plot(g.index, g.values, "-o", ms=2.6, lw=1.0, color=c, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Training conditions"); ax.set_ylabel("Median |error|, load proxy")
    ax.set_title("AlScN: unseen setpoints", fontsize=6.4, pad=3, loc="right")
    ax.set_ylim(0.03, 0.8)
    ax.legend(fontsize=5.2, loc="upper right", handlelength=1.2, ncol=1)
    panel(ax, "b")
    # c - grating: scalar vs line-shape error for three splits
    ax = fig.add_subplot(gs[0, 2])
    mk = {"submitted": "o", "cv5": "s", "chrono": "^"}
    cc = {"physics": BLUE, "data": ORANGE, "hybrid": GREEN}
    for sp_, mm in mk.items():
        for k in ("physics", "data", "hybrid"):
            ax.plot(G[sp_][k]["Q_MAE"], G[sp_][k]["line_RMSE_median"], mm, color=cc[k], ms=5,
                    mfc=cc[k] if sp_ == "submitted" else "none", mew=1.0)
    ax.set_xlabel("Scalar $Q_{align}$ MAE (nm)"); ax.set_ylabel("Median line RMSE (nm)")
    h1 = [plt.Line2D([], [], color=c, marker="o", ls="", ms=4, label=k) for k, c in
          (("physics", BLUE), ("data-driven", ORANGE), ("hybrid", GREEN))]
    h2 = [plt.Line2D([], [], color=DARK, marker=m, ls="", ms=4, mfc="none", label=l) for m, l in
          (("o", "submitted 40/20"), ("s", "5-fold CV"), ("^", "chronological"))]
    ax.legend(handles=h1 + h2, fontsize=5.4, loc="center right", handlelength=0.8)
    ax.set_xlim(0, 17); ax.set_ylim(15, 55)
    ax.set_title("Grating: two objectives", fontsize=6.4, pad=3, loc="right")
    panel(ax, "c")
    # d-f - grating example held-out line (submitted split), median data-driven error case
    te_ = np.load(ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz")["traces_exp"]
    idx = gz["submitted__idx"]
    pr = {k: gz[f"submitted__pred_{k}"] for k in ("physics", "data", "hybrid")}
    from rv_common import line_rmse
    rm = np.array([line_rmse(pr["data"][i, 0], te_[i, 0]) for i in idx])
    ci = int(idx[np.argsort(rm)[len(rm) // 2]])
    for j, (k, c, lab) in enumerate([("physics", BLUE, "physics"), ("data", ORANGE, "data-driven"),
                                      ("hybrid", GREEN, "hybrid")]):
        ax = fig.add_subplot(gs[1, j])
        e = te_[ci, 0] - np.nanmean(te_[ci, 0][10:-10])
        ax.plot(e, color=DARK, lw=0.8, label="experiment")
        ax.plot(pr[k][ci, 0], color=c, lw=1.0, label=lab)
        ax.set_xlabel("Fast-scan pixel"); ax.set_ylabel("Height (nm)" if j == 0 else "")
        r = line_rmse(pr[k][ci, 0], te_[ci, 0])
        ax.set_title(f"{lab}, RMSE {r:.0f} nm", fontsize=6.4, pad=3, loc="right")
        ax.legend(fontsize=5.8, loc="upper right", handlelength=1.0)
        ax.set_ylim(-160, 190)
        panel(ax, "def"[j])
    save(fig, "Fig7_rev")

# ===================================================================== SI figures
def si():
    lc = pd.read_csv(OUT / "tap300_learning_curve.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.2)); plt.subplots_adjust(hspace=0.5, wspace=0.35)
    spec = {"Q_safety": [("physics", BLUE, "physics (zero-fit)"), ("physics_cal", SKY, "physics, 2-param."),
                         ("ridge", "#F5C26B", "controls, ridge"), ("gbm", ORANGE, "controls, GBM"),
                         ("hyb_ridge", "#7FD1B9", "physics + ridge"), ("hyb_gbm", GREEN, "physics + GBM")],
            "Q_align": [("median", GREY, "train median"), ("knn", "#B07AA1", "controls, kNN"),
                        ("ridge", "#F5C26B", "controls, ridge"), ("gbm", ORANGE, "controls, GBM")]}
    for i, t in enumerate(["Q_align", "Q_safety"]):
        for j, sc in enumerate(["block5", "setpoint"]):
            ax = axs[i, j]; d = lc[(lc.scheme == sc) & (lc.target == t)].copy()
            d["nn"] = np.where(d.n > 600, 700, d.n)
            for m, c, lab in spec[t]:
                g = d[d.model == m].groupby("nn")["MedAE"].median()
                ax.plot(g.index, g.values, "-o", ms=2.5, lw=1.0, color=c, label=lab)
            ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Training conditions")
            ax.set_ylabel("Median |error|" + (" (nm)" if t == "Q_align" else ""))
            ax.set_title(("$Q_{align}$" if t == "Q_align" else "load proxy") + ", " +
                         ("held-out blocks" if sc == "block5" else "unseen setpoints"), fontsize=7, loc="right")
            ax.legend(fontsize=5.2, loc="lower left", ncol=2, handlelength=1.0, columnspacing=0.6)
            ax.set_ylim(ax.get_ylim()[0] / 2.5, ax.get_ylim()[1])
            panel(ax, "abcd"[2 * i + j])
    save(fig, "FigS9_learning_curves")
    # FigS10: audit of the load-proxy correction + error by setpoint
    A = json.load(open(OUT / "audit_summary.json"))["qsafety_force"]
    S = summary(); z = np.load(OUT / "tap300_benchmark_block5.npz")
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6)); plt.subplots_adjust(wspace=0.55)
    ax = axs[0]
    sub = S[(S.scheme == "submitted") & (S.target == "Q_safety")].set_index("model")
    rows = [("prior (zero-fit)", A["prior"]["MedAE"], A["prior"]["rho"], GREY),
            ("submitted, true lines", A["submitted_corrected"]["MedAE"], A["submitted_corrected"]["rho"], VERMI),
            ("submitted, permuted", A["target_lines_permuted"]["MedAE"], A["target_lines_permuted"]["rho"], "#F2B8A0"),
            ("causal: controls, GBM", sub.loc["gbm_ctrl", "MedAE"], sub.loc["gbm_ctrl", "rho"], ORANGE)]
    y = np.arange(len(rows))[::-1]
    for yi, (lab, m, r, c) in zip(y, rows):
        ax.barh(yi, m, color=c, height=0.6); ax.text(1.03, yi, f"{r:+.2f}", transform=ax.get_yaxis_transform(), va="center", fontsize=6)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=6.2); ax.set_xscale("log")
    ax.set_xlabel("Median |error|, load proxy"); ax.set_title("submitted split", fontsize=6.6, loc="right")
    panel(ax, "a", dx=-0.9)
    sp = z["setpoint"]; u = np.unique(sp)
    for k, (t, ylab) in enumerate([("Q_align", "Median |error| (nm)"), ("Q_safety", "Median |error|")]):
        ax = axs[k + 1]; yv = z[t]
        for m, c, lab in [("physics", BLUE, "physics"), ("gbm_ctrl", ORANGE, "controls, GBM"),
                          ("hyb_gbm", GREEN, "physics + GBM"), ("median", GREY, "train median")]:
            p = 10 ** z[f"{t}__{m}"] if t == "Q_align" else z[f"{t}__{m}"]
            ax.plot(u, [np.median(np.abs(p - yv)[sp == s_]) for s_ in u], "-o", ms=2.5, color=c, label=lab)
        ax.set_yscale("log"); ax.set_xlabel("Setpoint"); ax.set_ylabel(ylab)
        ax.set_title(("$Q_{align}$" if t == "Q_align" else "load proxy") + ", held-out blocks", fontsize=6.6, loc="right")
        ax.legend(fontsize=5.2)
        panel(ax, "bc"[k])
    save(fig, "FigS10_audit_regimes")


if __name__ == "__main__":
    which = sys.argv[1:] or ["fig4", "fig6"]
    for w in which:
        globals()[w]()
