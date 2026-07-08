#!/usr/bin/env python3
"""Per-step experiment-vs-simulation comparison figures for the DT-SPM manuscript.

For each stage of the PINN + CNN-LSTM digital twin we show *characteristic*
held-out cases spanning good, borderline ("bad"), and outlier outcomes, so the
reader sees the real spread of agreement, not only an aggregate metric.

Outputs to output/pub_figures/:
  c1_step2_fdfits.png   — Step-2 descriptor recovery: measured FD curve vs
                          PINN-recovered anchors (good/typical/outlier, both systems)
  c2_step3a_traces.png  — Step-3a scanner wiring: experimental height scan line
                          vs deterministic DT scanner (good/bad/outlier, both systems)
  c3_step3b_correction.png — Step-3b reward correction: per-condition quality
                          prior -> corrected vs experiment (good/bad/outlier)
  c4_phase_decoupling.png  — Section-9d phase channel: measured sin phi vs the
                          conservative null vs the dissipation-field model
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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

TW = {'A0': 1, 'phi_baseline': 1, 'Q_eff': 1, 'd_AR': 2, 'A_AR': 1, 'phi_att': 1.5,
      'phi_rep': 1.5, 'phi_max': 1.5, 'd_phimax': .7, 'd_50': .7, 'A_50': .7,
      'd_70': .7, 'A_70': .7, 'slope_AR': .3, 'slope_contact': .3, 'd_contact': .7,
      'slope_50': .3, 'slope_70': .3}


def header(ax, letter, text, color=DARK):
    """Bold panel letter at top-left + a left-aligned descriptor, never overlapping."""
    ax.text(-0.02, 1.16, letter, transform=ax.transAxes, fontsize=8.5,
            fontweight="bold", va="top", ha="right", color=ns.DARK)
    ax.text(0.10, 1.16, text, transform=ax.transAxes, fontsize=6.9,
            va="top", ha="left", color=color)


def load_step2(figdir):
    pp = np.load(figdir / "pinn_step2_predictions.npz")
    vocab = [str(v) for v in pp["vocab_cols"]]
    tgt = pd.read_csv(figdir / "fd_vocab_v0_1.csv")
    tg = tgt[vocab].to_numpy(float)
    pred = pp["anchors_z"] * pp["sigma"] + pp["mu"]      # physical units
    tg_z = (tg - pp["mu"]) / pp["sigma"]
    n = tg.shape[0]
    werr = np.full(n, np.nan)
    for i in range(n):
        num = den = 0.0
        for j, c in enumerate(vocab):
            if np.isfinite(tg[i, j]):
                num += TW[c] * abs(pp["anchors_z"][i, j] - tg_z[i, j]); den += TW[c]
        werr[i] = num / den if den else np.nan
    mef = np.load(figdir / "model_error_fields.npz")
    return dict(vocab=vocab, tg=tg, pred=pred, werr=werr,
                test=set(pp["fd_test_idx"].tolist()), drive=tgt["drive_nm"].to_numpy(),
                mef=mef)


def pick_cases(werr, test):
    """good / typical / outlier among held-out curves."""
    ti = np.array(sorted(test))
    o = ti[np.argsort(werr[ti])]
    return int(o[0]), int(o[len(o) // 2]), int(o[-1])


def curve_xy(mef, ci):
    m = mef["curve"] == ci
    d, A, phi = mef["d"][m], mef["A_meas"][m], mef["phi_meas"][m]
    o = np.argsort(d)
    return d[o], A[o], phi[o]


# ============================================================ C1 — Step 2
def make_c1():
    systems = [("Tap-300 / AlScN", load_step2(FIG_T), VERMI),
               ("Multi-75 / grating", load_step2(FIG_M), BLUE)]
    fig = plt.figure(figsize=(7.2, 4.7))
    gs = fig.add_gridspec(2, 3, hspace=0.70, wspace=0.42)
    tags = ["good", "bad", "outlier"]
    pl = iter("abcdefghi")
    for r, (name, S, col) in enumerate(systems):
        g, t, o = pick_cases(S["werr"], S["test"])
        for cc, (ci, tag) in enumerate(zip([g, t, o], tags)):
            ax = fig.add_subplot(gs[r, cc])
            d, A, phi = curve_xy(S["mef"], ci)
            j = {k: S["vocab"].index(k) for k in S["vocab"]}
            A0 = S["tg"][ci, j["A0"]]
            # zoom to the engagement region: outermost distance where A recovers to 0.97 A0
            eng = d[(A / A0) < 0.97]
            d_eng = eng.max() if eng.size else d.max()
            anchor_d = [S["tg"][ci, j[k]] for k in ("d_AR", "d_phimax", "d_50", "d_70")
                        if np.isfinite(S["tg"][ci, j[k]])]
            d_view = min(d.max(), 1.35 * max([d_eng] + anchor_d))
            # amplitude (normalised) on left axis
            ax.plot(d, A / A0, color=BLUE, lw=1.2, zorder=2)
            ax.set_ylim(0, 1.18)
            ax.set_xlim(0, d_view)
            # phase on right axis
            axp = ax.twinx()
            axp.plot(d, phi, color=PURPLE, lw=1.1, zorder=2)
            axp.spines["top"].set_visible(False)
            axp.set_ylim(min(np.nanmin(phi) - 8, 20), max(np.nanmax(phi) + 8, 100))
            # measured vs PINN anchors -- pick the headline descriptor per type
            def mark(axA, axP, col_meas, col_pred):
                # phase anchors: d_AR (Type A) marked at the 90-deg crossing, else d_phimax
                if np.isfinite(S["tg"][ci, j["d_AR"]]):
                    for src, fill in [(S["tg"], DARK), (S["pred"], "none")]:
                        axP.plot([src[ci, j["d_AR"]]], [90.0], "^", mfc=fill,
                                 mec=(DARK if fill != "none" else col), ms=6, mew=0.9, zorder=5)
                else:
                    for src, fill in [(S["tg"], PURPLE), (S["pred"], "none")]:
                        axP.plot([src[ci, j["d_phimax"]]], [src[ci, j["phi_max"]]], "o",
                                 mfc=fill, mec=(DARK if fill != "none" else col),
                                 ms=5.5, mew=0.9, zorder=5)
                # amplitude anchors d_50/d_70
                for k in ["d_50", "d_70"]:
                    ak = "A_50" if k == "d_50" else "A_70"
                    for src, ls in [(S["tg"], "-"), (S["pred"], "--")]:
                        dx = src[ci, j[k]]; ay = src[ci, j[ak]] / A0
                        axA.plot([dx], [ay], "s", mfc=("none" if ls == "--" else BLUE),
                                 mec=(col if ls == "--" else DARK), ms=4.5, mew=0.9, zorder=4)
            mark(ax, axp, DARK, col)
            header(ax, next(pl),
                   f"{tag}: drive {S['drive'][ci]:.0f} nm, err {S['werr'][ci]:.2f} z", col)
            if cc == 0:
                ax.set_ylabel("A / A$_0$", color=BLUE)
            if cc == 2:
                axp.set_ylabel("φ (°)", color=PURPLE)
            if r == 1:
                ax.set_xlabel("Tip–sample distance, d (nm)")
            ax.tick_params(axis="y", colors=BLUE)
            axp.tick_params(axis="y", colors=PURPLE)
    # one shared legend
    hnd = [plt.Line2D([], [], color=BLUE, lw=1.2, label="amplitude A/A$_0$"),
           plt.Line2D([], [], color=PURPLE, lw=1.2, label="phase φ"),
           plt.Line2D([], [], color=DARK, marker="^", ls="", ms=5, label="d$_{AR}$"),
           plt.Line2D([], [], color=DARK, marker="o", ls="", ms=5, label="φ$_{max}$"),
           plt.Line2D([], [], color=DARK, marker="s", ls="", ms=4.5, label="d$_{50}$, d$_{70}$"),
           plt.Line2D([], [], color=DARK, marker="s", mfc="none", ls="", ms=4.5,
                      label="open = PINN  /  filled = measured")]
    fig.legend(handles=hnd, loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.03),
               handlelength=1.3, columnspacing=1.0, handletextpad=0.4)
    fig.text(0.5, 1.005, "Tap-300 / AlScN  (top)            Multi-75 / grating  (bottom)",
             ha="center", fontsize=7.2, color=DARK)
    fig.savefig(OUT / "c1_step2_fdfits.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote c1_step2_fdfits.png")


# ============================================================ C2 — Step 3a
def _center(x):
    return x - np.nanmedian(x[..., 8:-8], axis=-1, keepdims=True)


def make_c2():
    bM = np.load(ROOT / "output/calibration_grating_v2_figures/figure_45_data_bundle.npz")
    pM = np.load(FIG_M / "scanner_PINN_traces.npz")
    bT = np.load(ROOT / "output/dt_controller_fit_figures/figure_45_expscan_data_bundle.npz")
    pT = np.load(FIG_T / "scanner_PINN_traces.npz")

    def rms_trace(b, p):
        e, s = _center(b["traces_exp"][:, 0]), _center(p["dt_PINN"][:, 0])
        return np.sqrt(np.nanmean((e - s)[:, 8:-8] ** 2, axis=-1))

    def cases(b, p, testkey):
        r = rms_trace(b, p)
        test = np.zeros(len(r), bool); test[b[testkey]] = True
        ti = np.where(test & np.isfinite(r))[0]
        o = ti[np.argsort(r[ti])]
        return int(o[0]), int(o[len(o) // 2]), int(o[-1]), r

    gM, tM, oM, rM = cases(bM, pM, "test_idx")
    _, _, _, rT = cases(bT, pT, "test_idx")
    # Tap-300: curated held-out cases (good agreement; twin too quiet vs noisy exp;
    # experiment in a noise-amplified runaway) — the three regimes of the fidelity gap
    gT, tT, oT = 595, 65, 126
    px = np.arange(256)

    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(2, 3, hspace=0.66, wspace=0.32)
    pl = iter("abcdef")
    rows = [("Multi-75 / grating", bM, pM, [gM, tM, oM], rM, True),
            ("Tap-300 / AlScN", bT, pT, [gT, tT, oT], rT, False)]
    tags = ["good", "bad", "outlier"]
    for r, (name, b, p, idxs, rms, has_truth) in enumerate(rows):
        for cc, (ci, tag) in enumerate(zip(idxs, tags)):
            ax = fig.add_subplot(gs[r, cc])
            exp = _center(b["traces_exp"][ci, 0])
            sim = _center(p["dt_PINN"][ci, 0])
            if has_truth:
                ht = b["h_truth"] - np.nanmedian(b["h_truth"][8:-8])
                ax.plot(px, ht, color=GREY, lw=1.6, alpha=0.8, zorder=1, label="known grating")
            ax.plot(px, exp, color=DARK, lw=0.8, zorder=3, label="experiment")
            ax.plot(px, sim, color=VERMI, lw=1.1, zorder=2, label="DT scanner")
            # robust per-panel y-limits; annotate if experiment runs off scale
            span = np.nanpercentile(np.abs(np.concatenate([exp[8:-8], sim[8:-8]])), 98)
            esd, ssd = np.nanstd(exp[8:-8]), np.nanstd(sim[8:-8])
            ylim = 1.4 * max(span, 1e-3)
            ax.set_ylim(-ylim, ylim)
            off = np.nanmax(np.abs(exp[8:-8])) > ylim
            spv = b["setpoint"][ci] if "setpoint" in b else b["setpoint_exp"][ci]
            header(ax, next(pl), f"{tag}: setpoint {spv:.2f},  exp/DT s.d. {esd:.0f}/{ssd:.0f} nm",
                   (BLUE if has_truth else VERMI))
            if off:
                ax.text(0.5, 0.94, f"experiment ±{np.nanmax(np.abs(exp[8:-8])):.0f} nm (off scale)",
                        transform=ax.transAxes, fontsize=6.4, ha="center", va="top", color=DARK,
                        bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.6))
            if cc == 0:
                ax.set_ylabel("Height z (nm)\n(centred)")
            if r == 1:
                ax.set_xlabel("Fast-scan pixel")
            ax.set_xlim(0, 255)
    hnd = [plt.Line2D([], [], color=GREY, lw=1.6, label="known grating (h$_{truth}$)"),
           plt.Line2D([], [], color=DARK, lw=0.9, label="experimental scan line"),
           plt.Line2D([], [], color=VERMI, lw=1.2, label="deterministic DT scanner")]
    fig.legend(handles=hnd, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02),
               handlelength=1.6, columnspacing=1.4)
    fig.text(0.5, 1.004, "Multi-75 / grating  (top)            Tap-300 / AlScN  (bottom)",
             ha="center", fontsize=7.2, color=DARK)
    fig.savefig(OUT / "c2_step3a_traces.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote c2_step3a_traces.png")


# ============================================================ C3 — Step 3b
def make_c3():
    def pick(figdir, jcol):
        z = np.load(figdir / "step3b_corrected_Q.npz")
        Qs, Qp, Qe = z["Q_scanner"], z["Q_pred"], z["Q_exp"]
        ti = np.where(z["is_test"])[0]
        ec = np.abs(Qp[:, jcol] - Qe[:, jcol]); ep = np.abs(Qs[:, jcol] - Qe[:, jcol])
        # good: prior was meaningfully off, correction fixed it best
        cand = ti[(ep[ti] > np.nanmedian(ep[ti])) & np.isfinite(ec[ti])]
        good = cand[np.argmin(ec[cand])] if len(cand) else ti[np.argmin(ec[ti])]
        med = np.nanmedian(np.abs(Qe[ti, jcol]))
        scale = np.nanpercentile(np.abs(Qe[ti, jcol] - med), 90) * 4 + 30
        runaway = ti[np.abs(Qe[ti, jcol] - med) > scale]
        if len(runaway):                                    # true outlier exists
            outlier = runaway[np.argmax(np.abs(Qe[runaway, jcol] - med))]
        else:                                               # else hardest-to-correct
            outlier = ti[np.argmax(ec[ti])]
        rem = ti[(ti != good) & (ti != outlier) &
                 (np.abs(Qe[ti, jcol] - med) <= scale) & np.isfinite(ec[ti])]
        bad = rem[np.argmax(ec[rem])] if len(rem) else ti[np.argmax(ec[ti])]
        return z, dict(good=good, bad=bad, outlier=outlier), jcol

    # Q_align (height quality) for both systems; the force-based Q_safety (amplitude+phase,
    # contact-regime only) is shown in main Fig 6.
    systems = [("Multi-75 / grating", FIG_M, BLUE, 0, "Q$_{align}$"),
               ("Tap-300 / AlScN", FIG_T, VERMI, 0, "Q$_{align}$")]
    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(2, 3, hspace=0.66, wspace=0.46)
    pl = iter("abcdef")
    xticks = ["scanner\nprior", "+ ΔQ\n(LSTM)", "experiment"]
    for r, (name, figdir, col, jcol, ylab) in enumerate(systems):
        z, cs, jcol = pick(figdir, jcol)
        Qs, Qp, Qe = z["Q_scanner"], z["Q_pred"], z["Q_exp"]
        for cc, tag in enumerate(["good", "bad", "outlier"]):
            i = cs[tag]
            ax = fig.add_subplot(gs[r, cc])
            prior, corr, exp = Qs[i, jcol], Qp[i, jcol], Qe[i, jcol]
            ax.plot([0, 1], [prior, corr], "-o", color=col, ms=5, lw=1.3, zorder=3)
            ax.axhline(exp, color=DARK, ls="--", lw=0.8, zorder=1)
            ax.plot([2], [exp], "*", color=DARK, ms=9, zorder=4)
            # error annotations
            ax.annotate("", xy=(1, corr), xytext=(0, prior),
                        arrowprops=dict(arrowstyle="->", color=col, lw=1.0))
            ax.set_xticks([0, 1, 2]); ax.set_xticklabels(xticks, fontsize=6.6)
            ax.set_xlim(-0.35, 2.35)
            vals = [prior, corr, exp]
            lo, hi = min(vals), max(vals); pad = 0.30 * (hi - lo + 1e-6)
            ax.set_ylim(lo - pad, hi + pad)
            header(ax, next(pl),
                   f"{tag}: cond {int(z['win_cond'][i])}, err {abs(prior-exp):.0f}→{abs(corr-exp):.0f} nm", col)
            if cc == 0:
                ax.set_ylabel(f"{ylab} (nm)")
    hnd = [plt.Line2D([], [], color=GREY, marker="o", ms=5, label="scanner prior → corrected"),
           plt.Line2D([], [], color=DARK, ls="--", marker="*", ms=8, label="experiment (target)")]
    fig.legend(handles=hnd, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02),
               handlelength=1.8, columnspacing=1.6)
    fig.text(0.5, 1.004, "Multi-75 / grating  (top)            Tap-300 / AlScN  (bottom)",
             ha="center", fontsize=7.2, color=DARK)
    fig.savefig(OUT / "c3_step3b_correction.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote c3_step3b_correction.png")


# ============================================================ C4 — phase decoupling
def make_c4():
    def load(figdir):
        z = np.load(figdir / "model_error_fields.npz")
        return z

    def cases(z):
        te = np.array(sorted(set(z["fd_test_idx"].tolist())))
        err = []
        for ci in te:
            m = z["curve"] == ci
            e = np.nanmedian(np.abs(np.clip(z["sin_pred"][m], -1, 1) - z["sin_target"][m]))
            err.append(e)
        err = np.array(err)
        o = te[np.argsort(err)]
        return int(o[0]), int(o[len(o) // 2]), int(o[-1])

    systems = [("Tap-300 / AlScN", FIG_T, VERMI), ("Multi-75 / grating", FIG_M, BLUE)]
    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(2, 3, hspace=0.62, wspace=0.34)
    pl = iter("abcdef")
    for r, (name, figdir, col) in enumerate(systems):
        z = load(figdir)
        g, t, o = cases(z)
        for cc, (ci, tag) in enumerate(zip([g, t, o], ["good", "bad", "outlier"])):
            ax = fig.add_subplot(gs[r, cc])
            m = z["curve"] == ci
            d = z["d"][m]; oo = np.argsort(d); d = d[oo]
            st = z["sin_target"][m][oo]; sn = z["sin_null"][m][oo]
            sp = np.clip(z["sin_pred"][m][oo], -1, 1)
            ax.plot(d, st, ".", ms=2.4, color=GREY, label="measured", zorder=2)
            ax.plot(d, sn, color=SKY, lw=1.1, label="conservative null", zorder=3)
            ax.plot(d, sp, color=DARK, lw=1.3, label="dissipation model", zorder=4)
            eng = d[st < 0.985]
            ax.set_xlim(0, min(d.max(), (eng.max() if eng.size else d.max()) * 1.3))
            ax.set_ylim(min(np.nanmin(st), np.nanmin(sn)) - 0.04, 1.04)
            enull = np.nanmedian(np.abs(sn - st)); emod = np.nanmedian(np.abs(sp - st))
            header(ax, next(pl), f"{tag}: |error| {enull:.3f} → {emod:.3f}", col)
            if cc == 0:
                ax.set_ylabel("sin φ\n(offset-corrected)")
            if r == 1:
                ax.set_xlabel("Tip–sample distance, d (nm)")
    hnd = [plt.Line2D([], [], color=GREY, marker=".", ls="", ms=5, label="measured sin φ"),
           plt.Line2D([], [], color=SKY, lw=1.1, label="conservative null (E$_{dis}$=0)"),
           plt.Line2D([], [], color=DARK, lw=1.3, label="one-field dissipation model")]
    fig.legend(handles=hnd, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02),
               handlelength=1.6, columnspacing=1.4)
    fig.text(0.5, 1.004, "Tap-300 / AlScN  (top)            Multi-75 / grating  (bottom)",
             ha="center", fontsize=7.2, color=DARK)
    fig.savefig(OUT / "c4_phase_decoupling.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote c4_phase_decoupling.png")


if __name__ == "__main__":
    make_c1()
    make_c2()
    make_c3()
    make_c4()
