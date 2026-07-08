#!/usr/bin/env python3
"""Professional workflow (Fig 1) and NN-architecture (Fig 2) figures, built with the
reusable plotkit (codes/_dt_plotkit.py) following NMI/CVPR/NeurIPS figure conventions:
tensor shapes on the data-flow edges, layer-type colour coding, light grouping zones,
concrete example I/O thumbnails, consistent left-to-right flow.

Outputs: output/pub_figures/fig1_pro.png, fig2_pro.png
"""
import sys
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dt_plotkit as pk
from _dt_plotkit import C, DARK, INK, TINT

pk.apply_style()
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pub_figures"
FIG_M = ROOT / "output" / "descriptor_framework"
FIG_T = ROOT / "output" / "descriptor_framework_Tap300"
ASSET = ROOT / "output" / "pptx_assets"
BUND_M = ROOT / "output" / "calibration_grating_v2_figures" / "figure_45_data_bundle.npz"


def curve_xy(figdir, ci):
    z = np.load(figdir / "model_error_fields.npz")
    m = z["curve"] == ci
    d, A, phi = z["d"][m], z["A_meas"][m], z["phi_meas"][m]
    o = np.argsort(d)
    return d[o], A[o], phi[o]


def ctr(a):
    return a - np.nanmedian(a[8:-8])


# ============================================================ FIG 2 — architecture
def make_fig2_pro():
    fig = plt.figure(figsize=(7.5, 6.4))
    d = pk.Diagram(fig)
    vc = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")
    dd, A, phi = curve_xy(FIG_T, 8); A0 = vc["A0"][8]
    bM = np.load(BUND_M); pM = np.load(FIG_M / "scanner_PINN_traces.npz")["dt_PINN"]

    cols = [(0.012, 0.225, "physics", "Physics model", C["physics"], 1),
            (0.265, 0.485, "encoder", "Step 2 · PINN encoder", C["dense"], 2),
            (0.525, 0.715, "scanner", "Step 3a · DT scanner", C["conv"], 3),
            (0.755, 0.988, "correction", "Step 3b · CNN-LSTM", C["recur"], 4)]
    for x0, x1, tint, title, ec, num in cols:
        d.zone(x0 - 0.004, 0.045, x1 + 0.004, 0.945, tint, alpha=0.55)
        d.label((x0 + x1) / 2, 0.965, title, fontsize=9.6, fontweight="bold", color=ec)
        d.step_badge(x0 + 0.016, 0.93, num, color=ec)

    yI = (0.795, 0.915)        # input thumb band
    yN = (0.345, 0.745)        # network stack band
    yO = (0.085, 0.235)        # output thumb band

    # ---------- inputs ----------
    d.label((cols[0][0] + cols[0][1]) / 2, 0.86,
            "drive amplitude\ncantilever  k, f$_0$, Q", fontsize=7.9)
    ax = d.thumb(0.300, yI[0], 0.470, yI[1])
    sel = dd <= 16
    ax.plot(dd[sel], A[sel] / A0, color=C["conv"], lw=1.3)
    axt = ax.twinx(); axt.plot(dd[sel], phi[sel], color=C["dense"], lw=1.3)
    axt.set_yticks([]); axt.set_xticks([]); axt.spines["top"].set_visible(False)
    for s in axt.spines.values(): s.set_linewidth(0.5); s.set_color(C["grey"])
    d.label((cols[1][0] + cols[1][1]) / 2, 0.775, "measured FD curve  (A, φ)", fontsize=7.7)
    d.label((cols[2][0] + cols[2][1]) / 2, 0.86, "5 scanner\nparameters", fontsize=7.9)
    ax = d.thumb(0.775, yI[0], 0.985, yI[1])
    for k in range(3):
        ax.plot(ctr(bM["traces_exp"][26 + k, 0]) / 60 - k * 2.4, color=DARK, lw=0.5)
        ax.plot(ctr(pM[26 + k, 0]) / 60 - k * 2.4, color=C["output"], lw=0.7)
    ax.set_xlim(0, 255); ax.set_ylim(-6.2, 1.4)
    d.label((cols[3][0] + cols[3][1]) / 2, 0.775,
            "K = 32 window:\nexperiment + scanner lines", fontsize=7.7)

    # ---------- layer stacks (returns y-centres for shape arrows) ----------
    def shape_between(cx, ys, h, shapes, w, side="right"):
        for i, s in enumerate(shapes):
            yg = (ys[i] - h / 2 + ys[i + 1] + h / 2) / 2
            xx = cx + w / 2 + 0.006 if side == "right" else cx - w / 2 - 0.006
            ha = "left" if side == "right" else "right"
            d.ax.text(xx, yg, s, ha=ha, va="center", fontsize=6.5,
                      style="italic", color=INK, zorder=8)

    # physics
    cx = (cols[0][0] + cols[0][1]) / 2; w = 0.185
    ys, h = d.vstack(cx, yN[1], yN[0], [
        ("driven-cantilever ODE", "physics"), ("RK45 integrate", "physics"),
        ("lock-in  A, φ demod", "physics"), ("→ ω(d), Γ(d) library", "physics")], w=w, fs=7.6)
    # encoder
    cx = (cols[1][0] + cols[1][1]) / 2; w = 0.205
    ys, h = d.vstack(cx, yN[1], yN[0], [
        ("Conv1d 2→16  (k7)", "conv"), ("Conv1d 16→32  (k5)", "conv"),
        ("AdaptiveAvgPool → 8", "pool"), ("flatten + drive, tokens", "pool"),
        ("MLP 64 → 64  (GELU)", "dense"), ("heads → 18 / 5 / aux", "dense")], w=w, fs=7.6)
    shape_between(cx, ys, h, ["16×128", "32×128", "→256", "→261", "→64"], w, side="left")
    # scanner
    cx = (cols[2][0] + cols[2][1]) / 2; w = 0.175
    ys, h = d.vstack(cx, yN[1], yN[0], [
        ("effective FD ω,Γ", "conv"), ("PI feedback loop", "conv"),
        ("numba substep ODE", "conv"), ("→ height z(x)", "conv")], w=w, fs=7.6)
    # correction
    cx = (cols[3][0] + cols[3][1]) / 2; w = 0.205
    ys, h = d.vstack(cx, yN[1], yN[0], [
        ("Conv stem 2→16→32", "conv"), ("→64→32  (k9, /2)", "conv"),
        ("+ scanner Q  (B,K,34)", "pool"), ("LSTM 34→64  (K=32)", "recur"),
        ("MLP 64→32→2", "dense"), ("→ ΔQ (quality, safety)", "dense")], w=w, fs=7.6)
    shape_between(cx, ys, h, ["K×16×256", "K×32", "K×34", "→64", "→2"], w, side="left")

    # ---------- outputs ----------
    ax = d.thumb(0.040, yO[0], 0.205, yO[1])
    ax.plot(dd[sel], A[sel] / A0, color=C["conv"], lw=1.3)
    d.label((cols[0][0] + cols[0][1]) / 2, 0.058, "FD response library", fontsize=7.7)
    ax = d.thumb(0.300, yO[0] + 0.02, 0.470, yO[1])
    ax.bar(range(4), [A0, vc["d_AR"][8], vc["phi_max"][8] / 10, vc["d_50"][8]],
           color=C["dense"], width=0.6, lw=0)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["$A_0$", "$d_{AR}$", "$φ_{m}$", "$d_{50}$"], fontsize=6.0)
    d.label((cols[1][0] + cols[1][1]) / 2, 0.058, "18 physical descriptors", fontsize=7.7)
    ax = d.thumb(0.540, yO[0], 0.705, yO[1])
    ax.plot(ctr(bM["traces_exp"][28, 0]), color=DARK, lw=0.6, label="exp")
    ax.plot(ctr(pM[28, 0]), color=C["output"], lw=0.9, label="DT")
    ax.legend(loc="upper right", fontsize=5.2, handlelength=0.8, borderpad=0.2, labelspacing=0.2)
    d.label((cols[2][0] + cols[2][1]) / 2, 0.058, "simulated scan line", fontsize=7.7)
    ax = d.thumb(0.775, yO[0] + 0.02, 0.985, yO[1])
    zM = np.load(FIG_M / "step3b_corrected_Q.npz"); te = np.where(zM["is_test"])[0]; i = te[0]
    ax.plot([0, 1], [zM["Q_scanner"][i, 1], zM["Q_pred"][i, 1]], "-o", color=C["physics"], ms=4, lw=1.2)
    ax.axhline(zM["Q_exp"][i, 1], color=DARK, ls="--", lw=0.8)
    ax.plot([2], [zM["Q_exp"][i, 1]], "*", color=DARK, ms=8)
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["prior", "+ΔQ", "exp"], fontsize=5.6)
    ax.set_xlim(-0.3, 2.3)
    d.label((cols[3][0] + cols[3][1]) / 2, 0.058, "corrected quality / safety", fontsize=7.7)

    # ---------- vertical & inter-column arrows ----------
    for x0, x1, *_ in cols:
        xc = (x0 + x1) / 2
        d.arrow((xc, yI[0] - 0.004), (xc, yN[1] + 0.006), lw=1.2, ms=9)
        d.arrow((xc, yN[0] - 0.006), (xc, yO[1] + 0.004), lw=1.2, ms=9)
    handoff = ["", "18 anchors\n+ 5 params", ""]
    for (x0a, x1a, *_), (x0b, *_r), lab in zip(cols[:-1], cols[1:], handoff):
        ymid = (yN[0] + yN[1]) / 2
        d.arrow((x1a + 0.006, ymid), (x0b - 0.006, ymid), color=C["grey"], lw=1.8, ms=13)
        if lab:
            d.ax.text((x1a + x0b) / 2, ymid, lab, ha="center", va="center", rotation=90,
                      fontsize=6.8, color=INK, zorder=8,
                      bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5))

    # ---------- layer legend ----------
    pk.legend_chips(d, 0.20, 0.018, [("conv", "conv"), ("pool / reshape", "pool"),
                    ("dense / MLP", "dense"), ("recurrent (LSTM)", "recur"),
                    ("frozen physics", "physics")], dx=0.165, fs=6.4)
    fig.savefig(OUT / "fig2_pro.png", bbox_inches="tight", dpi=300)
    fig.savefig(OUT / "fig2_pro.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig2_pro.png")


# ============================================================ FIG 1 — workflow
def make_fig1_pro():
    fig = plt.figure(figsize=(7.4, 6.3))
    d = pk.Diagram(fig)
    vc = pd.read_csv(FIG_T / "fd_vocab_v0_1.csv")
    dd, A, phi = curve_xy(FIG_T, 8); A0 = vc["A0"][8]
    bM = np.load(BUND_M); pM = np.load(FIG_M / "scanner_PINN_traces.npz")["dt_PINN"]

    # ---- panel a: illustrated workflow (top band) ----
    d.panel_letter(0.005, 0.995, "a")
    stages = [(0.02, 0.235, "physics", "AFM instrument", C["physics"]),
              (0.275, 0.495, "encoder", "Physics descriptors\n+ PINN encoder", C["dense"]),
              (0.535, 0.755, "scanner", "Calibrated digital twin", C["conv"]),
              (0.785, 0.998, "correction", "Predict & interpret", C["recur"])]
    for x0, x1, tint, title, ec in stages:
        d.zone(x0, 0.565, x1, 0.955, tint, alpha=0.5)
        d.label((x0 + x1) / 2, 0.945, title, fontsize=7.8, fontweight="bold", color=ec)
    for xa, xb in [(0.235, 0.275), (0.495, 0.535), (0.755, 0.785)]:
        d.arrow((xa, 0.76), (xb, 0.76), lw=1.6, ms=12)
    # instrument render
    ax = d.thumb(0.025, 0.62, 0.232, 0.90, frame=False)
    ax.imshow(mpimg.imread(ASSET / "cantilever_render.png"))
    d.label(0.128, 0.59, "FD curves + scan archive", fontsize=6.2, color=INK)
    # encoder FD curve
    ax = d.thumb(0.305, 0.66, 0.475, 0.89)
    sel = dd <= 16
    ax.plot(dd[sel], A[sel] / A0, color=C["conv"], lw=1.3)
    axt = ax.twinx(); axt.plot(dd[sel], phi[sel], color=C["dense"], lw=1.3)
    axt.plot([vc["d_AR"][8]], [90], "^", mfc=DARK, mec="white", ms=6)
    axt.set_yticks([]); axt.set_xticks([]); axt.spines["top"].set_visible(False)
    for s in axt.spines.values(): s.set_linewidth(0.5); s.set_color(C["grey"])
    d.label(0.385, 0.635, "18 anchors: $A_0$, $d_{AR}$, $φ_{max}$ …", fontsize=6.4, color=INK)
    # twin: scanner + correction node
    ax = d.thumb(0.560, 0.80, 0.728, 0.905)
    ax.plot(ctr(bM["traces_exp"][28, 0]), color=DARK, lw=0.7, label="exp")
    ax.plot(ctr(pM[28, 0]), color=C["output"], lw=1.0, label="DT")
    ax.legend(loc="upper right", fontsize=5.0, handlelength=0.8, borderpad=0.2, labelspacing=0.2)
    d.label(0.645, 0.92, "deterministic scanner (3a)", fontsize=6.6, color=C["conv"])
    d.node(0.560, 0.625, 0.730, 0.755, "CNN-LSTM correction (3b)",
           sub="$Q_{pred}=Q_{sim}+ΔQ$", fc="white", ec=C["physics"], tcol=C["physics"], fs=6.6)
    d.arrow((0.645, 0.795), (0.645, 0.758), color=C["physics"], lw=1.1, ms=9)
    # predictions
    for i, (img, lab) in enumerate([("scanline_traceretrace.png", "predicted scan quality"),
                                    ("groundtruth.png", "inferred ground truth"),
                                    ("peakforce.png", "predicted peak force")]):
        y0 = 0.85 - i * 0.097
        ax = d.thumb(0.80, y0, 0.965, y0 + 0.07, frame=False)
        ax.imshow(mpimg.imread(ASSET / img))
        d.label(0.885, y0 + 0.082, lab, fontsize=6.6, color=INK)

    # ---- panel b: formal pipeline (bottom band): small cards, wide gaps ----
    d.panel_letter(0.005, 0.50, "b")
    # 6 cards of width 0.125 separated by 0.045 gaps -> room for stylish arrows
    xs = [0.020, 0.190, 0.360, 0.530, 0.700, 0.870]
    wb = 0.125
    steps = [("io", "Measured\nFD curves", None),
             ("physics", "Step 1\ndescriptor\nextraction", 1),
             ("dense", "Step 2\nPINN\nencoder", 2),
             ("conv", "Step 3a\nDT\nscanner", 3),
             ("recur", "Step 3b\nCNN-LSTM", 4),
             ("output", "Calibrated\nQ + safety", None)]
    yb0, yb1 = 0.265, 0.465
    for x0, (kind, title, num) in zip(xs, steps):
        d.node(x0, yb0, x0 + wb, yb1, title, fc=pk.LAYER_FC[kind], ec=pk.LAYER_EC[kind],
               lw=1.3, fs=8.2)
        if num:
            d.step_badge(x0 + 0.013, yb1 - 0.013, num, color=pk.LAYER_EC[kind])
    for x0 in xs[:-1]:
        d.arrow((x0 + wb + 0.004, (yb0 + yb1) / 2), (x0 + wb + 0.041, (yb0 + yb1) / 2),
                lw=2.0, ms=15)
    # feedback loop
    d.node(0.020, 0.045, 0.145, 0.205, "Scan archive\n/ instrument", fc=TINT["neutral"],
           ec=C["io"], fs=7.8)
    d.arrow((0.083, 0.205), (0.083, 0.262), color=C["grey"], lw=1.4, ms=11)
    d.arrow((0.145, 0.125), (0.760, 0.125), color=C["grey"], lw=1.6, ms=13)
    d.label(0.45, 0.150, "experimental scan lines + controls", fontsize=7.4, color=INK)
    d.arrow((0.7625, 0.128), (0.7625, 0.262), color=C["grey"], lw=1.4, ms=11)
    pk.legend_chips(d, 0.31, 0.020, [("frozen physics", "physics"), ("learned: PINN", "dense"),
                    ("learned: correction", "recur"), ("output", "output")], dx=0.175, fs=7.2)
    fig.savefig(OUT / "fig1_pro.png", bbox_inches="tight", dpi=300)
    fig.savefig(OUT / "fig1_pro.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig1_pro.png")


if __name__ == "__main__":
    make_fig1_pro()
    make_fig2_pro()
