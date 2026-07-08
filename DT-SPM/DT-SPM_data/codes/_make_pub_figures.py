#!/usr/bin/env python3
"""Publication-quality result figures for the DT-SPM summary, composed from the
saved data of the FINAL verified runs (not the notebook diagnostics).

Outputs to output/pub_figures/:
  r1_step2_pinn.png   — Step-2 PINN: per-descriptor held-out errors (both
                        systems), headline anchor parity, baseline→final bars
  r2_mechanism.png    — Tap-300 fidelity mechanism: real A(d) operating points,
                        amplification-vs-Q correlation, setpoint response of
                        experiment vs simulator
  r3_correction.png   — Step-3b correction: Multi-75 parity panels, Tap-300
                        accuracy ladder (mean + median) and fidelity gains
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nature_style as ns
from _nature_style import BLUE, DARK, GREEN, GREY, ORANGE, PURPLE, SKY, VERMI

ns.apply()
ROOT = Path(__file__).resolve().parents[1]
FIG_M = ROOT / "output" / "descriptor_framework"
FIG_T = ROOT / "output" / "descriptor_framework_Tap300"
OUT = ROOT / "output" / "pub_figures"
OUT.mkdir(parents=True, exist_ok=True)

SYS = {
    "Multi-75 / grating": dict(fig=FIG_M, color=BLUE),
    "Tap-300 / AlScN": dict(fig=FIG_T, color=VERMI),
}

# ================================================================ data loading
def step2_errors(figdir):
    pp = np.load(figdir / "pinn_step2_predictions.npz", allow_pickle=False)
    vocab = [str(v) for v in pp["vocab_cols"]]
    tgt = pd.read_csv(figdir / "fd_vocab_v0_1.csv")[vocab].to_numpy(float)
    pred_z = pp["anchors_z"]
    tgt_z = (tgt - pp["mu"]) / pp["sigma"]
    err = {}
    for split, idx in [("train", pp["fd_train_idx"]), ("test", pp["fd_test_idx"])]:
        e = np.full(len(vocab), np.nan)
        for j in range(len(vocab)):
            m = np.isfinite(tgt[idx, j])
            if m.sum():
                e[j] = np.median(np.abs(pred_z[idx[m], j] - tgt_z[idx[m], j]))
        err[split] = e
    return vocab, err, pp, tgt

# ================================================================ R1 — Step 2
fig = plt.figure(figsize=(7.1, 4.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05], hspace=0.62, wspace=0.30)

for k, (name, cfg) in enumerate(SYS.items()):
    ax = fig.add_subplot(gs[0, k])
    vocab, err, pp, tgt = step2_errors(cfg["fig"])
    x = np.arange(len(vocab))
    ax.bar(x - 0.2, err["train"], 0.4, color=GREY, label="fit (train)", lw=0)
    ax.bar(x + 0.2, err["test"], 0.4, color=cfg["color"], label="held-out test", lw=0)
    ax.axhline(1.0, color=DARK, ls=":", lw=0.6)
    ax.text(len(vocab) - 0.4, 1.03, "1 s.d. of train", fontsize=5.6, ha="right", color=DARK)
    ax.set_xticks(x)
    ax.set_xticklabels(vocab, rotation=60, ha="right", fontsize=5.4)
    ax.set_ylabel("Median |error| (z)")
    ax.set_ylim(0, 1.12)
    ax.set_title(name, fontsize=7, pad=3)
    ax.legend(loc="upper left", bbox_to_anchor=(0.18, 1.0), ncol=2, handlelength=1.0,
              columnspacing=0.8)
    ns.panel_label(ax, "ab"[k])

# c — headline anchor parity (both systems on one panel)
ax = fig.add_subplot(gs[1, 0])
for name, cfg in SYS.items():
    vocab, err, pp, tgt = step2_errors(cfg["fig"])
    pred = pp["anchors_z"] * pp["sigma"] + pp["mu"]
    for col, marker in [("d_AR", "o"), ("phi_max", "s")]:
        j = vocab.index(col)
        for idx, filled in [(pp["fd_train_idx"], False), (pp["fd_test_idx"], True)]:
            m = np.isfinite(tgt[idx, j])
            ax.scatter(tgt[idx[m], j], pred[idx[m], j], s=9 if not filled else 14,
                       marker=marker,
                       facecolors=cfg["color"] if filled else "none",
                       edgecolors=cfg["color"], linewidths=0.6, alpha=0.85,
                       zorder=3 if filled else 2)
lims = [-8, 170]
ax.plot(lims, lims, color=GREY, ls="--", lw=0.7, zorder=1)
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("Measured anchor (nm or °)")
ax.set_ylabel("PINN-predicted anchor (nm or °)")
hnd = [plt.Line2D([], [], marker="o", ls="", mfc="none", mec=DARK, ms=4, label="d_AR"),
       plt.Line2D([], [], marker="s", ls="", mfc="none", mec=DARK, ms=4, label="φ_max"),
       plt.Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=4, label="Multi-75 (filled = test)"),
       plt.Line2D([], [], marker="o", ls="", mfc=VERMI, mec=VERMI, ms=4, label="Tap-300 (filled = test)")]
ax.legend(handles=hnd, loc="upper left", handletextpad=0.2)
ns.panel_label(ax, "c")

# d — baseline → final decision metric
ax = fig.add_subplot(gs[1, 1])
labels = ["Multi-75\noverall", "Multi-75\nTier 1", "Multi-75\nTier 2",
          "Tap-300\noverall", "Tap-300\nTier 1", "Tap-300\nTier 2"]
base = [0.2601, 0.2500, 0.4173, 0.2257, 0.1925, 0.4709]
finl = [0.1716, 0.1675, 0.2360, 0.1869, 0.1545, 0.4254]
x = np.arange(len(labels))
ax.bar(x - 0.2, base, 0.4, color=GREY, label="baseline (first full run)", lw=0)
cols = [BLUE] * 3 + [VERMI] * 3
ax.bar(x + 0.2, finl, 0.4, color=cols, label="final accepted config", lw=0)
for xi, (b, f) in enumerate(zip(base, finl)):
    ax.text(xi + 0.2, f + 0.012, f"{100*(f-b)/b:+.0f}%", ha="center", fontsize=5.6, color=DARK)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.8)
ax.set_ylabel("Tier-weighted test MAE (z)")
ax.set_ylim(0, 0.56)
ax.legend(loc="upper left", handlelength=1.0)
ns.panel_label(ax, "d")
fig.savefig(OUT / "r1_step2_pinn.png")
plt.close(fig)

# ================================================================ R2 — mechanism
b = np.load(ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz",
            allow_pickle=False)
fd = np.load(ROOT / "output" / "Tap300_AlScN.npz")
fd_amp, fd_height = fd["amp"], fd["height"]
fd_drive = np.array([np.nanmean(fd_amp[i, -10:]) for i in range(fd_amp.shape[0])])
drive, sp, speed = b["drive"], b["setpoint"], b["scan_speed"]
te = np.zeros(len(drive), bool); te[b["test_idx"]] = True
rz = np.load(FIG_T / "resim_physical.npz")
Q_exp, Q_pi = rz["Q_exp"], rz["Q_pi"]

def op_point(V, s):
    i = int(np.argmin(np.abs(fd_drive - V)))
    d, A = fd_height[i], fd_amp[i]
    o = np.argsort(d); d, A = d[o], A[o]
    m = np.isfinite(d) & np.isfinite(A); d, A = d[m], A[m]
    A0 = np.nanmean(A[-10:]); At = s * A0
    c = np.where(np.diff(np.sign(A - At)) != 0)[0]
    if c.size == 0: return np.nan, np.nan
    k = c[0]
    dop = d[k] + (At - A[k]) / (A[k + 1] - A[k] + 1e-12) * (d[k + 1] - d[k])
    k2 = min(k + 4, len(d) - 1); k1 = max(k - 4, 0)
    return float(dop), float(abs((A[k2] - A[k1]) / (d[k2] - d[k1] + 1e-12)))

amp_f = np.full(len(drive), np.nan)
for i in range(len(drive)):
    _, s_ = op_point(drive[i], sp[i])
    amp_f[i] = 1.0 / max(s_, 1e-4) if np.isfinite(s_) else np.nan

fig = plt.figure(figsize=(7.1, 2.45))
gs = fig.add_gridspec(1, 3, wspace=0.42)

# a — real Tap-300 FD curve with operating points
ax = fig.add_subplot(gs[0])
i_mid = int(np.argmin(np.abs(fd_drive - np.median(drive))))
d_, A_ = fd_height[i_mid], fd_amp[i_mid]
o = np.argsort(d_); d_, A_ = d_[o], A_[o]
m = np.isfinite(d_) & np.isfinite(A_); d_, A_ = d_[m], A_[m]
A0_ = np.nanmean(A_[-10:])
ax.plot(d_, A_, color=BLUE, lw=1.0)
for s_, col in [(0.3, GREEN), (0.8, VERMI)]:
    dop, slp = op_point(fd_drive[i_mid], s_)
    ax.plot([dop], [s_ * A0_], "o", color=col, ms=3.6, zorder=4)
    ax.plot([d_.min(), dop], [s_ * A0_] * 2, ls=":", color=col, lw=0.7)
    ax.annotate(f"setpoint {s_:g}", (dop + 1.0, s_ * A0_ - 0.45), fontsize=6.0, color=col)
ax.set_xlabel("Tip–sample distance, d (nm)")
ax.set_ylabel("Amplitude, A (nm)")
ax.set_xlim(d_.min(), np.percentile(d_, 98))
ns.panel_label(ax, "a")

# b — amplification vs held-out experimental Q
ax = fig.add_subplot(gs[1])
m = te & np.isfinite(amp_f) & np.isfinite(Q_exp[:, 0])
ax.scatter(amp_f[m], Q_exp[m, 0], s=6, color=BLUE, alpha=0.45, lw=0)
ax.set_xscale("log"); ax.set_yscale("log")
rho = stats.spearmanr(amp_f[m], Q_exp[m, 0]).statistic
ax.set_xlabel("Noise amplification, 1/|dA/dd|(d_op)")
ax.set_ylabel("Experimental Q_align (nm)")
ax.text(0.04, 0.93, f"ρ = {rho:+.2f}\n(held-out, zero-fit)", transform=ax.transAxes,
        fontsize=6.4, va="top")
ns.panel_label(ax, "b")

# c — setpoint response: experiment vs simulator
ax = fig.add_subplot(gs[2])
sps = np.unique(sp)
def med_iqr(Q, col):
    med = [np.nanmedian(Q[sp == v, col]) for v in sps]
    lo = [np.nanpercentile(Q[sp == v, col], 25) for v in sps]
    hi = [np.nanpercentile(Q[sp == v, col], 75) for v in sps]
    return np.array(med), np.array(lo), np.array(hi)
for Q, lab, col in [(Q_exp, "experiment", DARK), (Q_pi, "DT scanner (fitted gains)", SKY)]:
    med, lo, hi = med_iqr(Q, 0)
    ax.plot(sps, med, "-o", color=col, ms=2.8, lw=1.0, label=lab)
    ax.fill_between(sps, lo, hi, color=col, alpha=0.14, lw=0)
ax.set_yscale("log")
ax.set_ylim(0.8, 60)
ax.set_xlabel("Setpoint (fraction of $A_0$)")
ax.set_ylabel("Q_align (nm), median ± IQR")
ax.legend(loc="upper left")
ns.panel_label(ax, "c")
fig.savefig(OUT / "r2_mechanism.png")
plt.close(fig)

# ================================================================ R3 — Step 3b
zm = np.load(FIG_M / "step3b_corrected_Q.npz")
zt = np.load(FIG_T / "step3b_corrected_Q.npz")

fig = plt.figure(figsize=(7.1, 4.5))
gs = fig.add_gridspec(2, 2, hspace=0.52, wspace=0.46)

# a — Multi-75 Q_align parity (height quality, linear); b — Tap-300 Q_align parity (log)
# (the force-based Q_safety, amplitude+phase, is shown in main Fig 6)
ax = fig.add_subplot(gs[0, 0])
Qs, Qp, Qe, m_te = zm["Q_scanner"], zm["Q_pred"], zm["Q_exp"], zm["is_test"]
ax.scatter(Qe[:, 0], Qs[:, 0], s=10, facecolors="none", edgecolors=GREY, linewidths=0.6,
           label="scanner prior")
ax.scatter(Qe[:, 0], Qp[:, 0], s=10, color=GREEN, lw=0, label="corrected (+ΔQ)")
ax.scatter(Qe[m_te, 0], Qp[m_te, 0], s=16, facecolors=GREEN, edgecolors=DARK, linewidths=0.5,
           label="corrected, held-out")
lims = [min(np.nanmin(Qe[:, 0]), np.nanmin(Qp[:, 0])), max(np.nanmax(Qe[:, 0]), np.nanmax(Qp[:, 0]))]
pad = 0.06 * (lims[1] - lims[0]); lims = [lims[0] - pad, lims[1] + pad]
ax.plot(lims, lims, color=GREY, ls="--", lw=0.7); ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("Experimental Q_align (nm)"); ax.set_ylabel("Predicted Q_align (nm)")
ax.set_title("Multi-75 — Q_align", fontsize=7, pad=3)
ax.legend(loc="upper left", handletextpad=0.2)
ns.panel_label(ax, "a")

ax = fig.add_subplot(gs[0, 1])
Qs2, Qp2, Qe2, te2 = zt["Q_scanner"], zt["Q_pred"], zt["Q_exp"], zt["is_test"]
cl = lambda a: np.clip(a, 0.3, None)
mt = te2 & (Qe2[:, 0] > 0)
ax.scatter(cl(Qe2[mt, 0]), cl(Qs2[mt, 0]), s=10, facecolors="none", edgecolors=GREY,
           linewidths=0.6, label="scanner prior")
ax.scatter(cl(Qe2[mt, 0]), cl(Qp2[mt, 0]), s=12, color=GREEN, lw=0, label="corrected (+ΔQ)")
ax.plot([0.3, 4000], [0.3, 4000], color=GREY, ls="--", lw=0.7)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.3, 4000); ax.set_ylim(0.3, 4000)
ax.set_xlabel("Experimental Q_align (nm)"); ax.set_ylabel("Predicted Q_align (nm)")
ax.set_title("Tap-300 — Q_align", fontsize=7, pad=3)
ns.panel_label(ax, "b")

# c — Tap-300 accuracy ladder (mean and median test error)
ax = fig.add_subplot(gs[1, 0])
stages = ["scanner\nonly", "+ first ΔQ\n(raw space)", "+ robust\nz-space", "+ Huber\nδ=1", "+ control &\nphysics recal."]
mean_q = [176490, 171368, 170293, 173668, 171653]
med_q = [2.74, 1343, 1835, 0.57, 0.37]
x = np.arange(len(stages))
ax.bar(x, np.array(mean_q) / 1e3, 0.55, color=SKY, lw=0, label="mean (10³ nm²)")
ax.set_ylabel("Held-out mean MSE (10³ nm²)", color=DARK)
ax.set_ylim(165, 180)
ax2 = ax.twinx()
ax2.plot(x, med_q, "o-", color=VERMI, ms=3.4, lw=1.0, label="median")
ax2.set_yscale("log")
ax2.set_ylabel("Held-out median err² (nm²)", color=VERMI)
ax2.tick_params(axis="y", colors=VERMI)
ax2.spines["top"].set_visible(False)
ax.set_xticks(x); ax.set_xticklabels(stages, fontsize=5.6)
ax.set_title("Tap-300 — Q_align accuracy ladder", fontsize=7, pad=3)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper right")
ns.panel_label(ax, "c")

# d — Tap-300 trend-fidelity gain
ax = fig.add_subplot(gs[1, 1])
Qs, Qsr, Qp, Qe, m_te = (zt["Q_scanner"], zt["Q_scanner_raw"], zt["Q_pred"],
                         zt["Q_exp"], zt["is_test"])
rows, vals = [], []
for j, qlab in [(0, "Q_align")]:
    r_raw = stats.spearmanr(Qe[m_te, j], Qsr[m_te, j]).statistic
    r_rec = stats.spearmanr(Qe[m_te, j], Qs[m_te, j]).statistic
    r_cor = stats.spearmanr(Qe[m_te, j], Qp[m_te, j]).statistic
    rows.append(qlab); vals.append([r_raw, r_rec, r_cor])
vals = np.array(vals)
x = np.arange(len(rows))
w = 0.26
for i, (lab, col) in enumerate([("raw scanner", GREY),
                                ("recalibrated prior", SKY),
                                ("+ ΔQ (final)", GREEN)]):
    ax.bar(x + (i - 1) * w, vals[:, i], w, color=col, lw=0, label=lab)
ax.axhline(0, color=DARK, lw=0.6)
ax.set_xticks(x); ax.set_xticklabels(rows)
ax.set_ylabel("Spearman ρ vs experiment\n(held-out)")
ax.set_ylim(-0.25, 0.85)
ax.legend(loc="upper left")
ax.set_title("Tap-300 — trend fidelity", fontsize=7, pad=3)
ns.panel_label(ax, "d")
fig.savefig(OUT / "r3_correction.png")
plt.close(fig)

print("Publication figures written to", OUT)

# ================================================================ R4 — decoupled channels (2026-06-12)
zt4 = np.load(FIG_T / "model_error_fields.npz")
zm4 = np.load(FIG_M / "model_error_fields.npz")

fig = plt.figure(figsize=(7.1, 4.6))
gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.34)

# a — held-out curve: measured sin-phi vs conservative null vs dissipation model
ax = fig.add_subplot(gs[0, 0])
ci0 = int(zt4["fd_test_idx"][0]); m0 = zt4["curve"] == ci0
ax.plot(zt4["d"][m0], zt4["sin_target"][m0], ".", ms=2.2, color=GREY, label="measured")
ax.plot(zt4["d"][m0], zt4["sin_null"][m0], color=SKY, lw=1.0,
        label="conservative null (E$_{dis}$ = 0)")
ax.plot(zt4["d"][m0], np.clip(zt4["sin_pred"][m0], -1, 1), color=BLUE, lw=1.2,
        label="with dissipation field")
ax.set_xlabel("Tip–sample distance, d (nm)")
ax.set_ylabel("sin φ (offset-corrected)")
ax.legend(loc="lower right", handlelength=1.4)
ns.panel_label(ax, "a")

# b — learned dissipation field, coloured by drive amplitude
ax = fig.add_subplot(gs[0, 1])
sc = ax.scatter(zt4["d"], zt4["D"], c=zt4["drive_A0"], s=2.5, cmap="viridis", lw=0)
ax.set_xlabel("Tip–sample distance, d (nm)")
ax.set_ylabel("D = Q·E$_{dis}$/(πkA₀²)")
cb = plt.colorbar(sc, ax=ax, pad=0.02)
cb.set_label("Free amplitude, A$_0$ (nm)")
cb.ax.tick_params(labelsize=6)
ns.panel_label(ax, "b")

# c — held-out phase error: null vs model, both systems
ax = fig.add_subplot(gs[1, 0])
vals = []
for z4 in (zm4, zt4):
    te4 = np.isin(z4["curve"], z4["fd_test_idx"])
    e_m = np.nanmedian(np.abs((np.clip(z4["sin_pred"], -1, 1) - z4["sin_target"])[te4]))
    e_b = np.nanmedian(np.abs((z4["sin_null"] - z4["sin_target"])[te4]))
    vals.append((e_b, e_m))
x = np.arange(2)
ax.bar(x - 0.18, [v[0] for v in vals], 0.36, color=GREY, label="conservative null", lw=0)
ax.bar(x + 0.18, [v[1] for v in vals], 0.36, color=[BLUE, VERMI][0], lw=0,
       label="dissipation model")
ax.bar(x[1] + 0.18, vals[1][1], 0.36, color=VERMI, lw=0)
for xi, (b_, m_) in zip(x, vals):
    ax.text(xi + 0.18, m_ + 0.0006, f"{100*(m_-b_)/b_:+.0f}%", ha="center", fontsize=6, color=DARK)
ax.set_xticks(x); ax.set_xticklabels(["Multi-75 / grating", "Tap-300 / AlScN"])
ax.set_ylabel("Held-out median |sin φ error|")
ax.legend(loc="upper left")
ns.panel_label(ax, "c")

# d — channel-decoupling evidence: in-loop noise vs per-channel fidelity
ax = fig.add_subplot(gs[1, 1])
labels = ["Q_align", "height\nline s.d.", "amplitude\nline s.d.", "phase\nline s.d."]
det = [0.04, 0.06, 0.35, 0.34]
sto = [0.06, 0.17, 0.33, 0.00]
x = np.arange(4)
ax.bar(x - 0.18, det, 0.36, color=GREY, label="deterministic scanner", lw=0)
ax.bar(x + 0.18, sto, 0.36, color=GREEN, label="+ in-loop amplitude noise", lw=0)
ax.axhline(0, color=DARK, lw=0.6)
ax.annotate("0.00", (x[3] + 0.18, 0.008), ha="center", fontsize=6, color=GREEN,
            fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.8)
ax.set_ylabel("Held-out Spearman ρ vs experiment")
ax.set_ylim(0, 0.45)
ax.legend(loc="upper left")
ns.panel_label(ax, "d")
fig.savefig(OUT / "r4_decoupling.png")
plt.close(fig)
print("added r4_decoupling.png")
