#!/usr/bin/env python3
"""Revised main manuscript figures (v2) for the descriptor-aligned DT-SPM paper.

Addresses the second-round review:
  fig1_overview       — illustrated framework overview (uses the PPTX cantilever render
                        + real FD / scan-line visuals); answers "what is the DT".
  fig2_descriptors_Q  — schematic definitions of the Step-2 FD descriptors AND of the
                        scan-quality descriptors Q_align (quality) and Q_safety.
  fig3_step2_fit      — Step-2 fitting performance in PHYSICAL units (parity + per-anchor
                        error bars + reconstructed-vs-measured curves), easy to read.
  fig4_mechanism_Q    — the fidelity problem posed as explicit questions Q1-Q4 with the
                        diagnostic answer (operating-point noise amplification).
  fig5_step3b_predict — Step-3b prediction performance: prior->corrected parity onto the
                        diagonal, both systems, in physical units.
  fig6_three_models   — pure physics vs pure data-driven vs hybrid: metrics (scalar
                        quality + line-shape) AND example simulation-vs-experiment traces.
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nature_style as ns
from _nature_style import (BLUE, DARK, GREEN, GREY, ORANGE, PURPLE, SKY, VERMI,
                           YELLOW, LIGHT)

ns.apply()
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pub_figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG_M = ROOT / "output" / "descriptor_framework"
FIG_T = ROOT / "output" / "descriptor_framework_Tap300"
ASSET = ROOT / "output" / "pptx_assets"
BUND_T = ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz"
BUND_M = ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz"


def panel(ax, letter, dx=-0.015, dy=1.04):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=9, fontweight="bold",
            va="bottom", ha="right", color=DARK)


def curve_xy(figdir, ci):
    z = np.load(figdir / "model_error_fields.npz")
    m = z["curve"] == ci
    d, A, phi = z["d"][m], z["A_meas"][m], z["phi_meas"][m]
    o = np.argsort(d)
    return d[o], A[o], phi[o]


# ===================================================================== FIG 2
def make_fig2():
    """Schematic definitions: FD descriptors (a) + Q_align (b) + Q_safety (c)."""
    fig = plt.figure(figsize=(7.2, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.42, wspace=0.28)

    # ---- a: FD-curve descriptors on a real Tap-300 curve -----------------
    ax = fig.add_subplot(gs[0, :])
    vocab = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")
    ci = 8                                       # full-vocabulary curve
    d, A, phi = curve_xy(FIG_T, ci)
    A0 = vocab["A0"][ci]
    v = {k: vocab[k][ci] for k in vocab.columns}
    # zoom to engagement
    eng = d[(A / A0) < 0.985]
    dmax = min(d.max(), (eng.max() if eng.size else d.max()) * 1.45)
    sel = d <= dmax
    d, A, phi = d[sel], A[sel], phi[sel]
    ax.plot(d, A / A0, color=BLUE, lw=1.8, zorder=3)
    axp = ax.twinx(); axp.spines["top"].set_visible(False)
    axp.spines["right"].set_visible(True); axp.spines["right"].set_color(PURPLE)
    axp.spines["right"].set_linewidth(0.6)
    axp.plot(d, phi, color=PURPLE, lw=1.8, zorder=3)
    phi_top = max(np.nanmax(phi) + 42, 150)          # headroom for top annotations
    ax.set_ylim(0, 1.30); axp.set_ylim(min(np.nanmin(phi) - 10, 25), phi_top)
    ax.set_xlim(0, dmax)
    dAR = v["d_AR"]
    delta = dmax * 0.06
    # phi_att / phi_rep integration windows (shaded vertical bands on the phase regime;
    # capped at ymax=0.78 so they never reach the top regime labels; light so anchor
    # markers/labels that fall inside a window stay legible)
    axp.axvspan(dAR + delta, dAR + 4 * delta, ymin=0.0, ymax=0.78, color=LIGHT["blue"], alpha=0.35, zorder=0)
    axp.axvspan(max(dAR - 4 * delta, 0.0), dAR - delta, ymin=0.0, ymax=0.78, color=LIGHT["vermi"], alpha=0.35, zorder=0)
    # regime labels along the top, inside the amplitude headroom
    ax.text(dAR * 0.5, 1.26, "repulsive / contact", ha="center", va="top", fontsize=7.0, color=VERMI)
    ax.text((dAR + dmax) / 2, 1.26, "attractive  →  far field", ha="center", va="top",
            fontsize=7.0, color=BLUE)
    ax.axvline(dAR, color=GREY, ls="--", lw=0.6, zorder=1)
    # A0 line
    ax.axhline(1.0, color=BLUE, ls=":", lw=0.8, zorder=1)
    ax.annotate("$A_0$ free amplitude", xy=(dmax * 0.99, 1.0), xytext=(dmax * 0.99, 1.12),
                fontsize=7.1, color=BLUE, ha="right",
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.7))
    # d50 / d70 on amplitude
    for frac, name in [(0.5, "d$_{50}$"), (0.7, "d$_{70}$")]:
        dd = v[f"d_{int(frac*100)}"]
        ax.plot([dd], [frac], "s", mfc=BLUE, mec="white", ms=6, zorder=5)
        ax.annotate(name, xy=(dd, frac), xytext=(dd + dmax * 0.03, frac - 0.16),
                    fontsize=7.1, color=BLUE, zorder=6,
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.5),
                    arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.6))
    # d_AR on phase (90 deg crossing)
    axp.plot([dAR], [90], "^", mfc=DARK, mec="white", ms=9, zorder=6)
    axp.annotate("$d_{AR}$  (φ = 90°)", xy=(dAR, 90), xytext=(dAR - dmax * 0.02, 50),
                 fontsize=7.1, color=DARK, ha="right",
                 arrowprops=dict(arrowstyle="->", color=DARK, lw=0.7))
    axp.axhline(90, color=GREY, ls=":", lw=0.6, zorder=1)
    # phi_max
    dphimax = v["d_phimax"]
    axp.plot([dphimax], [v["phi_max"]], "o", mfc=PURPLE, mec="white", ms=7, zorder=6)
    axp.annotate("$\\phi_{max}$", xy=(dphimax, v["phi_max"]),
                 xytext=(dphimax + dmax * 0.04, v["phi_max"] - phi_top * 0.18),
                 fontsize=7.2, color=PURPLE,
                 arrowprops=dict(arrowstyle="->", color=PURPLE, lw=0.6))
    # window labels (inside the shaded bands, below the top regime labels)
    axp.text(dAR + 2.5 * delta, phi_top * 0.70, "$\\phi_{att}$", ha="center", va="center",
             fontsize=7.2, color=BLUE, fontweight="bold")
    axp.text(dAR - 2.5 * delta, phi_top * 0.70, "$\\phi_{rep}$", ha="center", va="center",
             fontsize=7.2, color=VERMI, fontweight="bold")
    ax.set_xlabel("Tip–sample distance, d (nm)")
    ax.set_ylabel("Amplitude  A / A$_0$", color=BLUE); ax.tick_params(axis="y", colors=BLUE)
    axp.set_ylabel("Phase  φ (°)", color=PURPLE); axp.tick_params(axis="y", colors=PURPLE)
    ax.set_yticks([0, 0.5, 0.7, 1.0])
    panel(ax, "a")

    # ---- shared synthetic grating for Q schematics ----------------------
    x = np.arange(256)

    def grating(period=64, amp=50.0, edge=2.0):
        s = amp * np.tanh(np.sin(2 * np.pi * x / period) / (edge / period))
        return s - s.mean()

    # ---- b: Q_align = RMS(trace - retrace) ------------------------------
    ax = fig.add_subplot(gs[1, 0])
    np.random.seed(3)
    base = grating()
    # trace and retrace: same grating, but retrace lags (hysteresis) + small noise
    trace = base + np.cumsum(np.random.randn(256)) * 0.25
    retrace = np.roll(base, 5) * 0.9 + np.cumsum(np.random.randn(256)) * 0.25 - 2
    ax.fill_between(x, trace, retrace, color=ORANGE, alpha=0.35, lw=0, zorder=1)
    ax.plot(x, trace, color=DARK, lw=1.1, zorder=3, label="trace")
    ax.plot(x, retrace, color=SKY, lw=1.3, zorder=2, label="retrace")
    ax.plot([], [], color=ORANGE, lw=4, alpha=0.4, label="mismatch")
    ax.set_xlim(0, 255); ax.set_ylim(-152, 90)        # extra headroom below for the caption box
    ax.set_xlabel("Fast-scan pixel"); ax.set_ylabel("Height z (nm)")
    ax.legend(loc="upper right", fontsize=6.4, handlelength=1.2, ncol=3, columnspacing=0.8)
    ax.text(0.03, 0.03, "$Q_{align}$ = RMS(trace − retrace)\nscan quality — lower is better",
            transform=ax.transAxes, fontsize=7.2, va="bottom", color=DARK,
            bbox=dict(fc="white", ec=GREY, lw=0.4, alpha=0.9, pad=2.0))
    panel(ax, "b")
    ax.set_title("Q$_{align}$ — alignment / quality", fontsize=7, pad=3, color=ORANGE)

    # ---- c: Q_safety = force from amplitude reduction + repulsive phase --
    ax = fig.add_subplot(gs[1, 1])
    qs = np.load(FIG_T / "qsafety_ap.npz")
    spv, A0v = qs["setpoint"], qs["drive"]
    ci = 171                         # setpoint 0.3, amplitude reduced + repulsive phase (φ≈87°)
    Aex = qs["A_exp"][ci, 0]; Pex = qs["PHI_exp"][ci, 0]
    a0 = A0v[ci]; sset = spv[ci]
    An = Aex / a0
    Pw = np.mod(Pex, 360.0); Pw = np.where(Pw > 180, Pw - 360, Pw)
    kk = np.ones(5) / 5; Pw = np.convolve(Pw, kk, mode="same"); An = np.convolve(An, kk, mode="same")
    ax.axhline(1.0, color=BLUE, ls=":", lw=0.8, zorder=2)
    ax.axhline(sset, color=GREY, ls="--", lw=0.8, zorder=2)
    ax.fill_between(x, An, 1.0, color=ORANGE, alpha=0.30, lw=0, zorder=1)   # reduction = force
    ax.plot(x, An, color=BLUE, lw=1.0, zorder=4)
    ax.set_ylim(0, 1.18); ax.set_xlim(0, 255)
    ax.set_ylabel("Amplitude A / A$_0$", color=BLUE); ax.tick_params(axis="y", colors=BLUE)
    ax.text(250, 1.02, "free A$_0$", color=BLUE, fontsize=6.0, ha="right", va="bottom")
    ax.text(250, sset + 0.02, "setpoint", color=GREY, fontsize=6.0, ha="right", va="bottom")
    axp = ax.twinx(); axp.spines["top"].set_visible(False)
    axp.spines["right"].set_visible(True); axp.spines["right"].set_color(PURPLE)
    axp.spines["right"].set_linewidth(0.6)
    axp.set_ylim(55, 145)
    axp.axhspan(55, 90, color=PURPLE, alpha=0.10, lw=0, zorder=0)          # repulsive zone
    axp.plot(x, Pw, color=PURPLE, lw=1.1, zorder=3)
    axp.axhline(90, color=PURPLE, ls=":", lw=0.9)
    axp.set_ylabel("Phase φ (°)", color=PURPLE); axp.tick_params(axis="y", colors=PURPLE)
    axp.text(248, 91, "φ = 90°", color=PURPLE, fontsize=6.0, ha="right", va="bottom")
    axp.text(10, 60, "repulsive (φ<90°)", color=PURPLE, fontsize=5.8, va="center")
    ax.set_xlabel("Fast-scan pixel")
    ax.text(0.025, 0.965,
            "$Q_{safety}$ = force from amplitude\nreduction ($A_0$−A) and repulsive\nphase (φ<90°);  higher = less safe",
            transform=ax.transAxes, fontsize=6.3, va="top", ha="left", color=DARK, zorder=8,
            bbox=dict(fc="white", ec=GREY, lw=0.4, alpha=0.95, pad=2.2))
    panel(ax, "c")
    ax.set_title(f"Q$_{{safety}}$ — force (setpoint {sset:.1f})", fontsize=7, pad=3, color=VERMI)

    fig.savefig(OUT / "fig2_descriptors_Q.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig2_descriptors_Q.png")


# ===================================================================== FIG 6
def make_fig6():
    """Pure physics vs pure data-driven vs hybrid: metrics + example traces."""
    b = np.load(BUND_M)
    ti = b["test_idx"]
    qe, qpi, qdd, qhyb = b["q_exp"], b["q_PI"], b["q_dd"], b["q_hyb"]
    mae = [np.nanmean(np.abs(q[ti] - qe[ti])) for q in (qpi, qdd, qhyb)]
    rms = [np.nanmedian(np.nanmean(b[k][ti], 1)) for k in ("rmse_PI", "rmse_dd", "rmse_hyb")]
    names = ["pure\nphysics", "pure\ndata-driven", "hybrid\n(physics+learn)"]
    cols = [BLUE, ORANGE, GREEN]

    fig = plt.figure(figsize=(7.2, 4.8))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.92], hspace=0.62, wspace=0.40)

    # a — scalar scan-quality error
    ax = fig.add_subplot(gs[0, 0])
    ax.bar(range(3), mae, color=cols, width=0.62, lw=0)
    for i, m in enumerate(mae):
        ax.text(i, m + 0.12, f"{m:.1f}", ha="center", fontsize=7.2, color=DARK)
    ax.set_xticks(range(3)); ax.set_xticklabels(names, fontsize=6.6)
    ax.set_ylabel("Scan-quality error\nMAE (nm)"); ax.set_ylim(0, max(mae) * 1.5)
    ax.set_title("Predict scalar quality", fontsize=7, pad=3)
    # vertical callout above the winning (lowest) bar — never crosses the value labels
    ax.annotate("physics best", xy=(0, mae[0] + 0.9), xytext=(0, max(mae) * 1.42),
                fontsize=6.8, color=BLUE, ha="center", va="top",
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=0.7))
    panel(ax, "a")

    # b — line-shape RMSE
    ax = fig.add_subplot(gs[0, 1])
    ax.bar(range(3), rms, color=cols, width=0.62, lw=0)
    for i, m in enumerate(rms):
        ax.text(i, m + 1.2, f"{m:.0f}", ha="center", fontsize=7.2, color=DARK)
    ax.set_xticks(range(3)); ax.set_xticklabels(names, fontsize=6.6)
    ax.set_ylabel("Line-shape error\nmedian RMSE (nm)"); ax.set_ylim(0, max(rms) * 1.5)
    ax.set_title("Reconstruct line shape", fontsize=7, pad=3)
    ax.annotate("learning best", xy=(1, rms[1] + 3.0), xytext=(1.5, max(rms) * 1.42),
                fontsize=6.8, color=ORANGE, ha="center", va="top",
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.7))
    panel(ax, "b")

    # c — Pareto scatter
    ax = fig.add_subplot(gs[0, 2])
    for i, (lab, c) in enumerate(zip(["pure physics", "pure data-driven", "hybrid"], cols)):
        ax.scatter(mae[i], rms[i], s=70, color=c, zorder=3, edgecolors="white", lw=0.8)
        ax.annotate(lab, (mae[i], rms[i]), xytext=(6, 4 if i != 1 else -10),
                    textcoords="offset points", fontsize=6.8, color=c)
    ax.set_xlabel("Scalar quality error (nm)")
    ax.set_ylabel("Line-shape RMSE (nm)")
    ax.set_xlim(6.5, 9.5); ax.set_ylim(10, 55)
    ax.annotate("better", xy=(6.8, 14), xytext=(8.4, 30),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8), fontsize=6.8, color=GREY)
    ax.set_title("Trade-off (Pareto)", fontsize=7, pad=3)
    panel(ax, "c")

    # d,e,f — example traces (held-out cond 37): exp vs each method
    ci = 37
    px = np.arange(256)
    def ctr(a): return a - np.nanmedian(a[8:-8])
    exp = ctr(b["traces_exp"][ci, 0])
    methods = [("dt_PI", "pure physics", BLUE), ("dd", "pure data-driven", ORANGE),
               ("hyb", "hybrid", GREEN)]
    for k, (key, lab, c) in enumerate(methods):
        ax = fig.add_subplot(gs[1, k])
        sim = ctr(b[key][ci, 0])
        r = np.sqrt(np.nanmean((exp[8:-8] - sim[8:-8]) ** 2))
        ax.plot(px, exp, color=DARK, lw=0.8, label="experiment", zorder=3)
        ax.plot(px, sim, color=c, lw=1.2, label=lab, zorder=2)
        ax.set_xlim(0, 255); ax.set_ylim(-140, 140)
        ax.set_xlabel("Fast-scan pixel")
        if k == 0:
            ax.set_ylabel("Height z (nm)\n(centred)")
        ax.legend(loc="upper right", fontsize=6.4, handlelength=1.1)
        ax.set_title(f"{lab} · RMSE {r:.0f} nm", fontsize=7.0, pad=3, color=c)
        panel(ax, "def"[k], dy=1.17)
    fig.savefig(OUT / "fig6_three_models.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig6_three_models.png")


# ===================================================================== FIG 1
def make_fig1():
    """Illustrated framework overview using the rendered cantilever + real outputs."""
    fig = plt.figure(figsize=(7.2, 3.9))
    bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off")
    bg.set_xlim(0, 1); bg.set_ylim(0, 1)

    def box(x0, y0, x1, y1, fc, ec, lw=0.8, alpha=1.0, r=0.02):
        bg.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                     boxstyle=f"round,pad=0.004,rounding_size={r}",
                     fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=1,
                     transform=bg.transAxes, mutation_aspect=0.5))

    def arrow(x0, y0, x1, y1, color=DARK, lw=1.4):
        bg.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                     mutation_scale=11, color=color, lw=lw, zorder=5,
                     transform=bg.transAxes, shrinkA=0, shrinkB=0))

    # stage background bands
    stages = [("1", "AFM instrument", 0.005, 0.225, LIGHT["grey"]),
              ("2", "Physics descriptors\n+ PINN encoder", 0.265, 0.495, LIGHT["purple"]),
              ("3", "Calibrated digital twin", 0.535, 0.755, LIGHT["blue"]),
              ("4", "Predict & interpret", 0.785, 0.998, LIGHT["green"])]
    for num, title, x0, x1, fc in stages:
        box(x0, 0.06, x1, 0.93, fc, "none", alpha=0.55)
        bg.text((x0 + x1) / 2, 0.90, title, ha="center", va="top", fontsize=7,
                fontweight="bold", color=DARK, zorder=6)
        bg.add_patch(plt.Circle((x0 + 0.018, 0.895), 0.016, color=DARK, zorder=7,
                     transform=bg.transAxes))
        bg.text(x0 + 0.018, 0.895, num, ha="center", va="center", fontsize=7.2,
                color="white", fontweight="bold", zorder=8)
    # inter-stage arrows
    for xa, xb in [(0.225, 0.265), (0.495, 0.535), (0.755, 0.785)]:
        arrow(xa, 0.5, xb, 0.5)

    # 1 — cantilever render
    ax = fig.add_axes([0.01, 0.10, 0.215, 0.66]); ax.axis("off")
    ax.imshow(mpimg.imread(ASSET / "cantilever_render.png"))
    bg.text(0.115, 0.085, "FD curves + scan archive", ha="center", fontsize=6.6,
            color=DARK, style="italic", zorder=6)

    # 2 — FD descriptor mini (real Tap-300 curve)
    ax = fig.add_axes([0.295, 0.20, 0.175, 0.52])
    d, A, phi = curve_xy(FIG_T, 8)
    vocab = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv"); A0 = vocab["A0"][8]
    sel = d <= 16
    ax.plot(d[sel], A[sel] / A0, color=BLUE, lw=1.3)
    axp = ax.twinx(); axp.plot(d[sel], phi[sel], color=PURPLE, lw=1.3)
    axp.plot([vocab["d_AR"][8]], [90], "^", mfc=DARK, mec="white", ms=6)
    ax.set_xticks([]); ax.set_yticks([]); axp.set_yticks([])
    for s in ax.spines.values(): s.set_linewidth(0.5)
    axp.spines["top"].set_visible(False)
    ax.set_ylabel("A", color=BLUE, fontsize=6.8, labelpad=1); axp.set_ylabel("φ", color=PURPLE, fontsize=6.8, labelpad=1)
    bg.text(0.38, 0.155, "18 anchors: A$_0$, d$_{AR}$, φ$_{max}$ …",
            ha="center", fontsize=6.4, color=DARK, zorder=6)

    # 3 — twin: scanner + correction (clean Multi-75 grating: PINN scanner vs exp)
    ax = fig.add_axes([0.560, 0.46, 0.165, 0.26]);
    bM = np.load(BUND_M); pM = np.load(FIG_M / "scanner_PINN_traces.npz")
    def ctr(a): return a - np.nanmedian(a[8:-8])
    ax.plot(ctr(bM["traces_exp"][28, 0]), color=DARK, lw=0.7, label="exp")
    ax.plot(ctr(pM["dt_PINN"][28, 0]), color=VERMI, lw=1.0, label="DT")
    ax.set_xticks([]); ax.set_yticks([])
    ax.legend(loc="upper right", fontsize=6.0, handlelength=0.9, borderpad=0.2, labelspacing=0.2)
    for s in ax.spines.values(): s.set_linewidth(0.5)
    bg.text(0.645, 0.745, "deterministic scanner (3a)", ha="center", fontsize=6.4, color=BLUE, zorder=6)
    box(0.560, 0.20, 0.730, 0.40, "white", GREEN, lw=0.9)
    bg.text(0.645, 0.355, "CNN-LSTM\ncorrection (3b)", ha="center", va="top", fontsize=6.8,
            color=GREEN, zorder=6, fontweight="bold")
    bg.text(0.645, 0.245, "Q$_{pred}$ = Q$_{sim}$ + ΔQ", ha="center", fontsize=6.6, color=DARK, zorder=6)
    arrow(0.645, 0.455, 0.645, 0.405, color=GREEN, lw=1.1)

    # 4 — predictions: three stacked outputs
    outs = [("scanline_traceretrace.png", "predicted scan quality"),
            ("groundtruth.png", "inferred ground truth"),
            ("peakforce.png", "predicted peak force")]
    for i, (img, lab) in enumerate(outs):
        y0 = 0.62 - i * 0.245
        ax = fig.add_axes([0.80, y0, 0.165, 0.18]); ax.axis("off")
        ax.imshow(mpimg.imread(ASSET / img))
        bg.text(0.885, y0 + 0.195, lab, ha="center", fontsize=6.4, color=DARK, zorder=6)

    fig.text(0.5, 0.985, "A descriptor-aligned digital twin of amplitude-modulation SPM",
             ha="center", fontsize=8, fontweight="bold", color=DARK)
    fig.savefig(OUT / "fig1_overview.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("wrote fig1_overview.png")


# ===================================================================== FIG 3
def _step2(figdir):
    pp = np.load(figdir / "pinn_step2_predictions.npz")
    vocab = [str(v) for v in pp["vocab_cols"]]
    tgt = pd.read_csv(figdir / "fd_vocab_v0_1.csv")[vocab].to_numpy(float)
    pred = pp["anchors_z"] * pp["sigma"] + pp["mu"]
    return vocab, tgt, pred, pp["fd_train_idx"], pp["fd_test_idx"]


def make_fig3():
    systems = [("Multi-75", FIG_M, BLUE), ("Tap-300", FIG_T, VERMI)]
    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.5, wspace=0.34)

    # a — parity, distance anchors (nm); b — parity, phase anchors (deg)
    groups = [("Distance anchors (nm)", ["d_AR", "d_50", "d_70", "d_phimax"], (0, 0)),
              ("Phase anchors (°)", ["phi_max", "phi_att", "phi_rep"], (0, 1))]
    for title, cols, pos in groups:
        ax = fig.add_subplot(gs[pos])
        allv = []
        for name, figdir, c in systems:
            vocab, tgt, pred, tri, tei = _step2(figdir)
            for idx, fill, lab in [(tri, "none", "fit"), (tei, c, "held-out")]:
                xs, ys = [], []
                for col in cols:
                    j = vocab.index(col)
                    m = np.isfinite(tgt[idx, j])
                    xs += list(tgt[idx[m], j]); ys += list(pred[idx[m], j])
                allv += xs + ys
                ax.scatter(xs, ys, s=14, facecolors=fill, edgecolors=c, lw=0.7,
                           alpha=0.85, zorder=3)
        lo, hi = np.nanpercentile(allv, 1), np.nanpercentile(allv, 99)
        pad = 0.08 * (hi - lo); lo, hi = lo - pad, hi + pad
        ax.plot([lo, hi], [lo, hi], color=GREY, ls="--", lw=0.8, zorder=1)
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_xlabel("Measured"); ax.set_ylabel("PINN-predicted")
        ax.set_title(title, fontsize=7, pad=3)
        panel(ax, "a" if pos[1] == 0 else "b")
    hnd = [plt.Line2D([], [], marker="o", ls="", mfc="none", mec=DARK, ms=5, label="fit (train)"),
           plt.Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=5, label="Multi-75 held-out"),
           plt.Line2D([], [], marker="o", ls="", mfc=VERMI, mec=VERMI, ms=5, label="Tap-300 held-out")]
    fig.legend(handles=hnd, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=3,
               fontsize=6.8, handletextpad=0.2, columnspacing=1.2)

    # c — per-anchor held-out error in physical units (report card)
    ax = fig.add_subplot(gs[1, :])
    anchors = ["A0", "d_AR", "A_AR", "phi_att", "phi_rep", "phi_max", "d_phimax",
               "d_50", "d_70", "phi_baseline"]
    labels = [r"$A_0$ (nm)", r"$d_{AR}$ (nm)", r"$A_{AR}$ (nm)", r"$\phi_{att}$ (°)",
              r"$\phi_{rep}$ (°)", r"$\phi_{max}$ (°)", r"$d_{\phi max}$ (nm)",
              r"$d_{50}$ (nm)", r"$d_{70}$ (nm)", r"$\phi_{base}$ (°)"]
    x = np.arange(len(anchors)); w = 0.38
    for k, (name, figdir, c) in enumerate(systems):
        vocab, tgt, pred, tri, tei = _step2(figdir)
        err = []
        for col in anchors:
            j = vocab.index(col); m = np.isfinite(tgt[tei, j])
            err.append(np.nanmedian(np.abs(pred[tei[m], j] - tgt[tei[m], j])) if m.sum() else np.nan)
        ax.bar(x + (k - 0.5) * w, err, w, color=c, lw=0, label=name)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=6.8)
    ax.set_ylabel("Held-out median\n|error| (nm or °)")
    ax.set_ylim(0, 6.0)
    ax.legend(loc="upper left", fontsize=7.0)
    ax.set_title("Step-2 fitting accuracy in physical units (held-out)", fontsize=7, pad=3)
    ax.text(0.99, 0.92, "headline anchor d$_{AR}$ ≈ 0.4 nm", transform=ax.transAxes,
            ha="right", fontsize=6.8, color=DARK)
    panel(ax, "c")
    fig.savefig(OUT / "fig3_step2_fit.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig3_step2_fit.png")


# ===================================================================== FIG 5
def make_fig5():
    fig = plt.figure(figsize=(7.2, 4.7))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 0.95], hspace=0.62, wspace=0.40)

    # a — Tap-300 force-based Q_safety (amplitude + phase): prior -> corrected
    qa = np.load(FIG_T / "qsafety_ap.npz")
    Qe, Qpr, Qpd, te = qa["Q_exp"], qa["Q_prior"], qa["Q_pred"], qa["is_test"]
    ax = fig.add_subplot(gs[0, 0])
    m = te & np.isfinite(Qpd)
    ax.scatter(Qe[m], Qpr[m], s=12, facecolors="none", edgecolors=GREY, lw=0.6,
               label="scanner prior", zorder=2)
    ax.scatter(Qe[m], Qpd[m], s=14, color=GREEN, lw=0, label="+ ΔQ corrected", zorder=3)
    lim = [0.1, 1.25]; ax.plot(lim, lim, color=GREY, ls="--", lw=0.8); ax.set_xlim(lim); ax.set_ylim(lim)
    rp = stats.spearmanr(Qe[m], Qpr[m]).statistic; rc = stats.spearmanr(Qe[m], Qpd[m]).statistic
    ax.set_xlabel("Experimental Q$_{safety}$ (force)"); ax.set_ylabel("Predicted Q$_{safety}$")
    ax.set_title("Tap-300: force-based Q$_{safety}$ (A + φ)", fontsize=7, pad=3, color=VERMI)
    ax.legend(loc="upper left", fontsize=6.6, handletextpad=0.2)
    ax.text(0.97, 0.06, f"Spearman ρ\nprior {rp:+.2f} → corrected {rc:+.2f}",
            transform=ax.transAxes, ha="right", fontsize=6.4, va="bottom", color=DARK)
    panel(ax, "a")

    # b — Tap-300 Q_align parity (height-based quality, log)
    zT = np.load(FIG_T / "step3b_corrected_Q.npz")
    ax = fig.add_subplot(gs[0, 1])
    Qs, Qp, Qae, tem = zT["Q_scanner"], zT["Q_pred"], zT["Q_exp"], zT["is_test"]
    def clip(a): return np.clip(a, 0.3, None)
    mm = tem & (Qae[:, 0] > 0)
    ax.scatter(clip(Qae[mm, 0]), clip(Qs[mm, 0]), s=10, facecolors="none", edgecolors=GREY,
               lw=0.6, label="scanner prior", zorder=2)
    ax.scatter(clip(Qae[mm, 0]), clip(Qp[mm, 0]), s=12, color=GREEN, lw=0, label="+ ΔQ corrected", zorder=3)
    ax.plot([0.3, 4000], [0.3, 4000], color=GREY, ls="--", lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.3, 4000); ax.set_ylim(0.3, 4000)
    ax.set_xlabel("Experimental Q$_{align}$ (nm)"); ax.set_ylabel("Predicted Q$_{align}$ (nm)")
    ax.set_title("Tap-300: Q$_{align}$ (height quality)", fontsize=7, pad=3, color=VERMI)
    ax.legend(loc="upper left", fontsize=6.6, handletextpad=0.2)
    panel(ax, "b")

    # c — Q_safety error ladder prior->corrected, across setpoint
    ax = fig.add_subplot(gs[1, 0])
    sps = np.unique(qa["setpoint"][te])
    def med_err(Q):
        return np.array([np.nanmedian(np.abs(Q - Qe)[te & (qa["setpoint"] == s)]) for s in sps])
    ax.plot(sps, med_err(Qpr), "-o", color=GREY, ms=3, lw=1.0, label="scanner prior")
    ax.plot(sps, med_err(Qpd), "-o", color=GREEN, ms=3, lw=1.0, label="+ ΔQ corrected")
    ax.set_xlabel("Setpoint (fraction of $A_0$)"); ax.set_ylabel("Held-out median\n|error| in Q$_{safety}$")
    ax.legend(loc="upper right", fontsize=6.6)
    ax.set_title("Q$_{safety}$ accuracy across tapping regime", fontsize=7, pad=3)
    panel(ax, "c")

    # d — channels: amplitude tracks force (setpoint), phase carries independent branch
    ax = fig.add_subplot(gs[1, 1])
    Ae, Pe, sp, A0 = qa["A_exp"], qa["PHI_exp"], qa["setpoint"], qa["drive"]
    def wrapp(p): p = np.mod(p, 360.0); return np.where(p > 180, p - 360, p)
    amp_q = np.array([np.nanmean([np.nanpercentile((A0[i] - Ae[i, d]) / A0[i], 90) for d in (0, 1)])
                      for i in range(len(sp))])
    phi_q = np.array([np.nanmean([np.nanpercentile(np.clip((90 - wrapp(Pe[i, d])) / 90, -1, 1), 90) for d in (0, 1)])
                      for i in range(len(sp))])
    ra = stats.spearmanr(amp_q[te], sp[te]).statistic
    rph = stats.spearmanr(phi_q[te], sp[te]).statistic
    ax.bar([0, 1], [abs(ra), abs(rph)], color=[VERMI, PURPLE], width=0.6, lw=0)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["amplitude\n(force)", "phase\n(branch)"], fontsize=6.6)
    ax.set_ylabel("|Spearman ρ| vs setpoint"); ax.set_ylim(0, 1.5)
    ax.text(0, abs(ra) + 0.03, f"{ra:+.2f}", ha="center", fontsize=6.6, color=DARK)
    ax.text(1, abs(rph) + 0.03, f"{rph:+.2f}", ha="center", fontsize=6.6, color=DARK)
    ax.set_title("Two channels carry distinct information", fontsize=7, pad=3)
    ax.text(0.5, 0.97, "amplitude ↔ tapping force;\nphase adds the branch,\nset-point-independent",
            transform=ax.transAxes, ha="center", va="top", fontsize=5.8, color=DARK)
    panel(ax, "d")
    fig.savefig(OUT / "fig5_step3b_predict.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig5_step3b_predict.png")


# ===================================================================== FIG 4
def make_fig4():
    """The fidelity problem, posed as explicit diagnostic questions Q1-Q4."""
    b = np.load(BUND_T)
    rz = np.load(FIG_T / "resim_physical.npz")
    fd = np.load(ROOT / "output" / "Tap300_AlScN.npz")
    fd_amp, fd_h = fd["amp"], fd["height"]
    fd_drive = np.array([np.nanmean(fd_amp[i, -10:]) for i in range(fd_amp.shape[0])])
    drive, sp = b["drive"], b["setpoint"]
    te = np.zeros(len(drive), bool); te[b["test_idx"]] = True
    Qexp, Qpi = rz["Q_exp"][:, 0], rz["Q_pi"][:, 0]

    def op_point(V, s):
        i = int(np.argmin(np.abs(fd_drive - V)))
        d, A = fd_h[i], fd_amp[i]
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

    fig = plt.figure(figsize=(7.2, 5.0))
    gs = fig.add_gridspec(2, 2, hspace=0.62, wspace=0.36)
    QHEAD = dict(fontsize=7.0, fontweight="bold", color=DARK)

    # a — Q1: can the deterministic twin predict scan quality?  -> No
    # show the dramatic signal: experimental line s.d. blows up with setpoint, twin stays flat
    ax = fig.add_subplot(gs[0, 0])
    pT = np.load(FIG_T / "scanner_PINN_traces.npz")["dt_PINN"]
    def line_sd(traces):
        out = np.full(len(traces), np.nan)
        for i in range(len(traces)):
            t = traces[i, 0]; t = t - np.nanmedian(t[8:-8])
            out[i] = np.nanstd(t[8:-8])
        return out
    sd_exp = line_sd(b["traces_exp"]); sd_twin = line_sd(pT)
    rng = np.random.RandomState(0)
    jit = (rng.rand(len(sp)) - 0.5) * 0.04
    mt = te & np.isfinite(sd_exp)
    ax.scatter(sp[mt] + jit[mt], np.clip(sd_exp[mt], 0.5, None), s=8, color=DARK,
               alpha=0.45, lw=0, label="experiment")
    ax.scatter(sp[mt] + jit[mt], np.clip(sd_twin[mt], 0.5, None), s=8, color=SKY,
               alpha=0.5, lw=0, label="deterministic twin")
    ax.set_yscale("log"); ax.set_ylim(1, 400)
    ax.set_xlabel("Setpoint (fraction of $A_0$)"); ax.set_ylabel("Scan-line s.d. (nm)")
    ax.legend(loc="upper left", fontsize=6.8, markerscale=1.4, frameon=True,
              facecolor="white", framealpha=0.92, edgecolor="none")
    ax.text(0, 1.18, "Q1", transform=ax.transAxes, **QHEAD)
    ax.text(0.13, 1.18, "Can the deterministic twin predict scan quality?",
            transform=ax.transAxes, fontsize=7.2, va="bottom", color=DARK)
    panel(ax, "a")

    # b — Q2/Q3: is it the controls or the gains?  -> No to both
    ax = fig.add_subplot(gs[0, 1])
    rhos = [0.86, -0.14, 0.03]
    labs = ["controls only\n(kNN)", "deterministic\ntwin", "global-gain\nre-simulation"]
    cols = [GREEN, SKY, ORANGE]
    ax.bar(range(3), rhos, color=cols, width=0.6, lw=0)
    ax.axhline(0, color=DARK, lw=0.6)
    for i, r in enumerate(rhos):
        ax.text(i, r + (0.04 if r >= 0 else -0.08), f"{r:+.2f}", ha="center", fontsize=7.2, color=DARK)
    ax.set_xticks(range(3)); ax.set_xticklabels(labs, fontsize=6.6)
    ax.set_ylabel("Spearman ρ vs\nexperiment (held-out)"); ax.set_ylim(-0.3, 1.45)
    ax.text(0, 1.18, "Q2·Q3", transform=ax.transAxes, **QHEAD)
    ax.text(0.22, 1.18, "Mis-recorded controls, or wrong gains?",
            transform=ax.transAxes, fontsize=7.2, va="bottom", color=DARK)
    ax.text(0.5, 0.985, "controls carry the signal (ρ = 0.86) —\nneither the twin nor a gain re-sim use it",
            transform=ax.transAxes, ha="center", fontsize=6.6, color=DARK, va="top",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    panel(ax, "b")

    # c — Q4 geometry: operating point and slope collapse
    ax = fig.add_subplot(gs[1, 0])
    i_mid = int(np.argmin(np.abs(fd_drive - np.median(drive))))
    d_, A_ = fd_h[i_mid], fd_amp[i_mid]
    o = np.argsort(d_); d_, A_ = d_[o], A_[o]
    m = np.isfinite(d_) & np.isfinite(A_); d_, A_ = d_[m], A_[m]
    A0_ = np.nanmean(A_[-10:])
    ax.plot(d_, A_, color=BLUE, lw=1.3)
    for s_, col, xo, yo in [(0.3, GREEN, 9.0, 0.5), (0.85, VERMI, 8.0, -1.9)]:
        dop, slp = op_point(fd_drive[i_mid], s_)
        ax.plot([dop], [s_ * A0_], "o", color=col, ms=4.5, zorder=4)
        ax.annotate(f"setpoint {s_:g}\nslope {'steep' if s_<0.5 else 'collapses'}",
                    (dop, s_ * A0_), xytext=(dop + xo, s_ * A0_ + yo),
                    fontsize=6.6, color=col, va="center",
                    arrowprops=dict(arrowstyle="->", color=col, lw=0.6))
    ax.set_xlabel("Tip–sample distance, d (nm)"); ax.set_ylabel("Amplitude, A (nm)")
    ax.set_xlim(d_.min(), np.percentile(d_, 98))
    ax.text(0, 1.18, "Q4", transform=ax.transAxes, **QHEAD)
    ax.text(0.13, 1.18, "What is it? Operating-point geometry",
            transform=ax.transAxes, fontsize=7.2, va="bottom", color=DARK)
    panel(ax, "c")

    # d — the answer: amplification factor correlates with exp quality
    ax = fig.add_subplot(gs[1, 1])
    m = te & np.isfinite(amp_f) & np.isfinite(Qexp) & (Qexp > 0)
    ax.scatter(amp_f[m], Qexp[m], s=7, color=BLUE, alpha=0.45, lw=0)
    ax.set_xscale("log"); ax.set_yscale("log")
    rho = stats.spearmanr(amp_f[m], Qexp[m]).statistic
    ax.set_xlabel("Noise amplification  1/|dA/dd|($d_{op}$)")
    ax.set_ylabel("Experimental Q$_{align}$ (nm)")
    ax.text(0, 1.18, "Answer", transform=ax.transAxes, **QHEAD)
    ax.text(0.30, 1.18, "Feedback noise blows up where the slope collapses",
            transform=ax.transAxes, fontsize=7.0, va="bottom", color=DARK)
    ax.text(0.04, 0.96, f"zero-fit physics factor\nρ = {rho:+.2f} (held-out)",
            transform=ax.transAxes, va="top", fontsize=7.0, color=DARK,
            bbox=dict(fc="white", ec=BLUE, lw=0.4, alpha=0.9, pad=2.0))
    panel(ax, "d")
    fig.savefig(OUT / "fig4_mechanism_Q.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig4_mechanism_Q.png")


# ===================================================================== FIG 1 COMBINED
def make_fig1_combined():
    """Fig 1 = illustrated overview (a) + formal pipeline boxes (b)."""
    fig = plt.figure(figsize=(7.2, 6.2))
    bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)

    def rbox(x0, y0, x1, y1, fc, ec, lw=0.9, alpha=1.0, r=0.012, z=1):
        bg.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                     boxstyle=f"round,pad=0.003,rounding_size={r}", fc=fc, ec=ec,
                     lw=lw, alpha=alpha, zorder=z, transform=bg.transAxes, mutation_aspect=0.5))

    def harrow(x0, x1, y, color=DARK, lw=1.5):
        bg.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=12,
                     color=color, lw=lw, zorder=6, transform=bg.transAxes, shrinkA=0, shrinkB=0))

    def varrow(x, y0, y1, color=DARK, lw=1.1):
        bg.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=9,
                     color=color, lw=lw, zorder=6, transform=bg.transAxes, shrinkA=0, shrinkB=0))

    # ============ panel a — illustrated overview (top band y 0.55-0.99) ============
    bg.text(0.012, 0.985, "a", fontsize=11, fontweight="bold", color=DARK, va="top")
    stages = [("AFM instrument", 0.02, 0.235, LIGHT["grey"], GREY),
              ("Physics descriptors\n+ PINN encoder", 0.275, 0.495, LIGHT["purple"], PURPLE),
              ("Calibrated digital twin", 0.535, 0.755, LIGHT["blue"], BLUE),
              ("Predict & interpret", 0.785, 0.998, LIGHT["green"], GREEN)]
    for title, x0, x1, fc, ec in stages:
        rbox(x0, 0.565, x1, 0.965, fc, "none", alpha=0.5)
        bg.text((x0 + x1) / 2, 0.95, title, ha="center", va="top", fontsize=7.5,
                fontweight="bold", color=ec, zorder=6)
    for xa, xb in [(0.235, 0.275), (0.495, 0.535), (0.755, 0.785)]:
        harrow(xa, xb, 0.76)
    # cantilever render
    ax = fig.add_axes([0.02, 0.60, 0.215, 0.30]); ax.axis("off")
    ax.imshow(mpimg.imread(ASSET / "cantilever_render.png"))
    bg.text(0.127, 0.585, "FD curves + scan archive", ha="center", fontsize=6.8,
            color=DARK, style="italic")
    # FD descriptor curve
    ax = fig.add_axes([0.305, 0.66, 0.17, 0.22])
    d, A, phi = curve_xy(FIG_T, 8); A0 = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")["A0"][8]
    sel = d <= 16
    ax.plot(d[sel], A[sel] / A0, color=BLUE, lw=1.3); axp = ax.twinx()
    axp.plot(d[sel], phi[sel], color=PURPLE, lw=1.3)
    axp.plot([pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")["d_AR"][8]], [90], "^", mfc=DARK, mec="white", ms=6)
    ax.set_xticks([]); ax.set_yticks([]); axp.set_yticks([]); axp.spines["top"].set_visible(False)
    for s in ax.spines.values(): s.set_linewidth(0.5)
    bg.text(0.385, 0.645, "18 anchors: A$_0$, d$_{AR}$, φ$_{max}$ …", ha="center",
            fontsize=6.6, color=DARK)
    # twin: scanner + correction
    ax = fig.add_axes([0.560, 0.80, 0.165, 0.115])
    bM = np.load(BUND_M); pM = np.load(FIG_M / "scanner_PINN_traces.npz")["dt_PINN"]
    def ctr(a): return a - np.nanmedian(a[8:-8])
    ax.plot(ctr(bM["traces_exp"][28, 0]), color=DARK, lw=0.7, label="exp")
    ax.plot(ctr(pM[28, 0]), color=VERMI, lw=1.0, label="DT")
    ax.set_xticks([]); ax.set_yticks([])
    ax.legend(loc="upper right", fontsize=6.0, handlelength=0.8, borderpad=0.2, labelspacing=0.2)
    for s in ax.spines.values(): s.set_linewidth(0.5)
    bg.text(0.645, 0.925, "deterministic scanner (3a)", ha="center", fontsize=6.4, color=BLUE)
    rbox(0.560, 0.63, 0.730, 0.755, "white", GREEN, lw=0.9)
    bg.text(0.645, 0.735, "CNN-LSTM\ncorrection (3b)", ha="center", va="top", fontsize=6.8,
            color=GREEN, fontweight="bold")
    bg.text(0.645, 0.655, "Q$_{pred}$ = Q$_{sim}$ + ΔQ", ha="center", fontsize=6.6, color=DARK)
    varrow(0.645, 0.795, 0.758, color=GREEN)
    # predictions
    outs = [("scanline_traceretrace.png", "predicted scan quality"),
            ("groundtruth.png", "inferred ground truth"),
            ("peakforce.png", "predicted peak force")]
    for i, (img, lab) in enumerate(outs):
        y0 = 0.86 - i * 0.105
        ax = fig.add_axes([0.80, y0, 0.165, 0.085]); ax.axis("off")
        ax.imshow(mpimg.imread(ASSET / img))
        bg.text(0.885, y0 + 0.092, lab, ha="center", fontsize=6.3, color=DARK)

    # ============ panel b — formal pipeline (bottom band y 0.02-0.50) ============
    bg.text(0.012, 0.50, "b", fontsize=11, fontweight="bold", color=DARK, va="top")
    steps = [("Measured\nFD curves", 0.02, 0.15, LIGHT["grey"], GREY, ""),
             ("Step 1\ndescriptor\nextraction", 0.185, 0.335, LIGHT["blue"], BLUE, "frozen physics"),
             ("Step 2\nPINN encoder\nanchors+params", 0.355, 0.520, LIGHT["purple"], PURPLE, "learned"),
             ("Step 3a\nDT scanner\nQ-descriptors", 0.540, 0.690, LIGHT["blue"], BLUE, "frozen physics"),
             ("Step 3b\nCNN-LSTM\nQ=Q+ΔQ", 0.710, 0.860, LIGHT["green"], GREEN, "learned"),
             ("Calibrated\nquality + safety\nprediction", 0.880, 0.995, LIGHT["orange"], ORANGE, "output")]
    yb0, yb1 = 0.28, 0.45
    for title, x0, x1, fc, ec, _ in steps:
        rbox(x0, yb0, x1, yb1, fc, ec, lw=1.0)
        bg.text((x0 + x1) / 2, (yb0 + yb1) / 2, title, ha="center", va="center",
                fontsize=7.2, color=DARK, zorder=3)
    for a, b in zip(steps[:-1], steps[1:]):
        harrow(a[2], b[1], (yb0 + yb1) / 2)
    # feedback row: scan archive + experimental lines, Step 4, Transfer
    rbox(0.02, 0.05, 0.15, 0.20, LIGHT["grey"], GREY, lw=0.9)
    bg.text(0.085, 0.125, "Scan archive\n/ instrument", ha="center", va="center", fontsize=7.2, color=DARK)
    bg.add_patch(FancyArrowPatch((0.085, 0.205), (0.085, 0.275), arrowstyle="-|>",
                 mutation_scale=9, color=GREY, lw=1.0, transform=bg.transAxes))
    # exp-lines feedback into 3b
    bg.add_patch(FancyArrowPatch((0.15, 0.12), (0.785, 0.12), arrowstyle="-|>",
                 mutation_scale=10, color=GREY, lw=1.1, transform=bg.transAxes,
                 connectionstyle="arc3,rad=0"))
    bg.text(0.45, 0.135, "experimental scan lines + controls", ha="center", fontsize=6.6, color=GREY)
    bg.add_patch(FancyArrowPatch((0.785, 0.125), (0.785, 0.275), arrowstyle="-|>",
                 mutation_scale=8, color=GREY, lw=1.0, transform=bg.transAxes))
    # legend chips
    chips = [("frozen physics", LIGHT["blue"], BLUE), ("learned: PINN", LIGHT["purple"], PURPLE),
             ("learned: correction", LIGHT["green"], GREEN), ("output", LIGHT["orange"], ORANGE)]
    cx = 0.34
    for lab, fc, ec in chips:
        rbox(cx, 0.035, cx + 0.025, 0.065, fc, ec, lw=0.8)
        bg.text(cx + 0.032, 0.05, lab, va="center", fontsize=6.6, color=DARK)
        cx += 0.165
    fig.savefig(OUT / "fig1_combined.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("wrote fig1_combined.png")


# ===================================================================== FIG ARCH
def make_fig_arch():
    """Physics model + PINN and CNN-LSTM architectures with example I/O (data flow)."""
    fig = plt.figure(figsize=(7.4, 5.4))
    bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)

    def rbox(x0, y0, x1, y1, fc, ec, lw=1.0, alpha=1.0, r=0.012, z=1):
        bg.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                     boxstyle=f"round,pad=0.003,rounding_size={r}", fc=fc, ec=ec,
                     lw=lw, alpha=alpha, zorder=z, transform=bg.transAxes, mutation_aspect=0.55))

    def harrow(x0, x1, y, color=DARK, lw=1.6):
        bg.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=12,
                     color=color, lw=lw, zorder=6, transform=bg.transAxes, shrinkA=0, shrinkB=0))

    def varrow(x, y0, y1, color=DARK, lw=1.3):
        bg.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=9,
                     color=color, lw=lw, zorder=6, transform=bg.transAxes, shrinkA=0, shrinkB=0))

    def layers(x0, x1, ytop, ybot, items, fc):
        n = len(items); h = (ytop - ybot) / n
        for i, lab in enumerate(items):
            yy = ytop - (i + 1) * h
            rbox(x0, yy + 0.004, x1, yy + h - 0.004, fc, DARK, lw=0.6, z=3)
            bg.text((x0 + x1) / 2, yy + h / 2, lab, ha="center", va="center",
                    fontsize=7.2, color=DARK, zorder=4)

    # stage columns
    cols = [(0.015, 0.215, "Physics model", LIGHT["blue"], BLUE),
            (0.275, 0.495, "Step 2 · PINN encoder", LIGHT["purple"], PURPLE),
            (0.555, 0.715, "Step 3a · DT scanner", LIGHT["blue"], BLUE),
            (0.775, 0.985, "Step 3b · CNN-LSTM", LIGHT["green"], GREEN)]
    yI0, yI1 = 0.80, 0.965        # input band
    yN0, yN1 = 0.34, 0.72         # network band
    yO0, yO1 = 0.085, 0.245       # output band
    for x0, x1, title, fc, ec in cols:
        rbox(x0 - 0.006, 0.015, x1 + 0.006, 0.995, fc, "none", alpha=0.32, r=0.02, z=0)
        bg.text((x0 + x1) / 2, 0.985, title, ha="center", va="top", fontsize=8,
                fontweight="bold", color=ec, zorder=7)

    # --- input thumbnails ---
    # physics input: drive + cantilever params (text icon)
    bg.text((0.015 + 0.215) / 2, 0.90, "drive amplitude,\ncantilever k, f$_0$, Q",
            ha="center", va="center", fontsize=7.2, color=DARK)
    # PINN input: measured (A, phi) curve
    axi = fig.add_axes([0.305, 0.795, 0.16, 0.17])
    d, A, phi = curve_xy(FIG_T, 8); A0 = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")["A0"][8]
    sel = d <= 16
    axi.plot(d[sel], A[sel] / A0, color=BLUE, lw=1.2); axt = axi.twinx()
    axt.plot(d[sel], phi[sel], color=PURPLE, lw=1.2)
    axi.set_xticks([]); axi.set_yticks([]); axt.set_yticks([])
    for s in list(axi.spines.values()) + list(axt.spines.values()): s.set_linewidth(0.5)
    axt.spines["top"].set_visible(False)
    bg.text((0.275 + 0.495) / 2, 0.785, "measured FD curve (A, φ)", ha="center", va="top",
            fontsize=7.2, color=DARK)
    # scanner input: effective FD / params
    bg.text((0.555 + 0.715) / 2, 0.90, "ω(d), Γ(d)\nfrom 5 params", ha="center", va="center",
            fontsize=7.2, color=DARK)
    # CNN-LSTM input: K window of exp+sim lines
    axi = fig.add_axes([0.80, 0.795, 0.18, 0.17]); axi.axis("off")
    bM = np.load(BUND_M); pM = np.load(FIG_M / "scanner_PINN_traces.npz")["dt_PINN"]
    def ctr(a): return a - np.nanmedian(a[8:-8])
    for k in range(3):
        off = -k * 2.4
        axi.plot(ctr(bM["traces_exp"][26 + k, 0]) / 60 + off, color=DARK, lw=0.5)
        axi.plot(ctr(pM[26 + k, 0]) / 60 + off, color=VERMI, lw=0.7)
    axi.set_xlim(0, 255); axi.set_ylim(-6.2, 1.4)
    bg.text((0.775 + 0.985) / 2, 0.785, "K = 32 window of\nexperiment + scanner lines",
            ha="center", va="top", fontsize=7.2, color=DARK)

    # --- network blocks ---
    layers(0.03, 0.20, yN1, yN0,
           ["RK45 cantilever ODE", "lock-in A, φ demod", "joblib FD prior", "→ ω(d), Γ(d)"], "white")
    layers(0.29, 0.48, yN1, yN0,
           ["Conv1d 2→16  (k7)", "Conv1d 16→32  (k5)", "AdaptiveAvgPool → 8",
            "concat: drive + tokens", "MLP 64 → 64 (GELU)",
            "heads: 18 anchors / 5 params / aux"], "white")
    layers(0.565, 0.705, yN1, yN0,
           ["PI feedback loop", "numba substep ODE", "trace / retrace", "→ height z(x)"], "white")
    layers(0.79, 0.975, yN1, yN0,
           ["per-line Conv1d 2→16→32", "→64→32  (k9, stride 2)", "LSTM 34 → 64  (K = 32)",
            "+ scanner Q (2)", "MLP 64 → 32 → 2", "→ ΔQ (quality, safety)"], "white")

    # --- output thumbnails ---
    vc = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")
    # physics output: effective FD curve
    axo = fig.add_axes([0.045, 0.10, 0.15, 0.135])
    axo.plot(d[sel], A[sel] / A0, color=BLUE, lw=1.3); axo.set_xticks([]); axo.set_yticks([])
    for s in axo.spines.values(): s.set_linewidth(0.5)
    bg.text((0.015 + 0.215) / 2, 0.055, "FD response library", ha="center", va="top",
            fontsize=7.2, color=DARK)
    # PINN output: anchor bars
    axo = fig.add_axes([0.305, 0.115, 0.155, 0.12])
    vals = [A0, vc["d_AR"][8], vc["phi_max"][8] / 10, vc["d_50"][8]]
    axo.bar(range(4), vals, color=PURPLE, width=0.6, lw=0)
    axo.set_xticks(range(4))
    axo.set_xticklabels(["$A_0$", "$d_{AR}$", "$φ_{max}$", "$d_{50}$"], fontsize=6.6)
    axo.set_yticks([])
    for s in axo.spines.values(): s.set_linewidth(0.5)
    bg.text((0.275 + 0.495) / 2, 0.055, "physical descriptors", ha="center", va="top",
            fontsize=7.2, color=DARK)
    # scanner output: sim vs exp trace
    axo = fig.add_axes([0.565, 0.10, 0.15, 0.135])
    axo.plot(ctr(bM["traces_exp"][28, 0]), color=DARK, lw=0.6, label="exp")
    axo.plot(ctr(pM[28, 0]), color=VERMI, lw=0.9, label="DT")
    axo.set_xticks([]); axo.set_yticks([])
    axo.legend(loc="upper right", fontsize=6.0, handlelength=0.8, borderpad=0.15, labelspacing=0.15)
    for s in axo.spines.values(): s.set_linewidth(0.5)
    bg.text((0.555 + 0.715) / 2, 0.055, "simulated scan line", ha="center", va="top",
            fontsize=7.2, color=DARK)
    # CNN-LSTM output: prior -> corrected vs exp
    axo = fig.add_axes([0.805, 0.115, 0.16, 0.12])
    zM = np.load(FIG_M / "step3b_corrected_Q.npz"); te = np.where(zM["is_test"])[0]
    i = te[0]
    axo.plot([0, 1], [zM["Q_scanner"][i, 1], zM["Q_pred"][i, 1]], "-o", color=GREEN, ms=4, lw=1.2)
    axo.axhline(zM["Q_exp"][i, 1], color=DARK, ls="--", lw=0.8)
    axo.plot([2], [zM["Q_exp"][i, 1]], "*", color=DARK, ms=8)
    axo.set_xticks([0, 1, 2]); axo.set_xticklabels(["prior", "+ΔQ", "exp"], fontsize=6.2)
    axo.set_yticks([]); axo.set_xlim(-0.3, 2.3)
    for s in axo.spines.values(): s.set_linewidth(0.5)
    bg.text((0.775 + 0.985) / 2, 0.055, "corrected quality / safety", ha="center", va="top",
            fontsize=7.2, color=DARK)

    # arrows: input -> network -> output within each column, and between columns
    for x0, x1, *_ in cols:
        xc = (x0 + x1) / 2
        varrow(xc, yI0 - 0.005, yN1 + 0.008)
        varrow(xc, yN0 - 0.008, yO1 + 0.005)
    for (x0a, x1a, *_), (x0b, *_rest) in zip(cols[:-1], cols[1:]):
        harrow(x1a + 0.006, x0b - 0.006, (yN0 + yN1) / 2, color=GREY, lw=1.4)
    fig.savefig(OUT / "fig_arch_dataflow.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("wrote fig_arch_dataflow.png")


if __name__ == "__main__":
    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
    make_fig6()
    make_fig_arch()
