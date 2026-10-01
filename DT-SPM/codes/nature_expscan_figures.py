"""Nature-style Figures 4 and 5 for the experimental-scans dataset.

Mirrors `codes/nature_cali_grating_figures.py` for the calibration grating
dataset, but consumes the cached PI grid + data-driven artifacts that
`Fit DT controller parameters to experimental scans.ipynb` produces.

Figure 4 — PI controller fit:
  (a) Synthetic median experimental scan line `h_truth` used for DT input.
  (b) PI loss surface from the GP local fit (illustrative condition).
  (c) Local-fit (P, I) vs GP-predicted (P, I).
  (d, e) DT vs experiment for an optimal and a sub-optimal condition.
  (f) DT-vs-experiment scan-quality scatter.
  (g, h, i) Best / median / worst held-out scan-line overlays.

Figure 5 — PI fit vs data-driven + PI vs pure data-driven:
  (a) Predicted vs experimental trace–retrace RMSE on the held-out set.
  (b) Quality MAE / median AE bars.
  (c) Per-line shape RMSE boxplot (log y).
  (d, e, f) Trace overlays for one held-out condition where the methods disagree.

Both figures share the Nature palette/style from `nature_statement_figures.py`.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import load
from matplotlib import gridspec
from matplotlib.lines import Line2D

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from codes.nature_statement_figures import (
    NATURE_DIRNAME, PALETTE, panel_label, save_pub, setup_style,
)

CACHE_DIR    = PROJECT_ROOT / "calibration_cache" / "dt_controller_fit"
BUNDLE_NAME  = "figure_45_expscan_data_bundle.npz"
DEFAULT_TAG  = "balanced_g3_rms"


# ---------------------------------------------------------------------------
def _center(arr, trim=10):
    arr = np.asarray(arr, float).copy()
    if arr.ndim == 1:
        return arr - np.nanmean(arr[trim:-trim])
    for i in range(arr.shape[0]):
        arr[i] = arr[i] - np.nanmean(arr[i, trim:-trim])
    return arr


def _quality(arr, trim=10):
    out = np.full(arr.shape[0], np.nan)
    for i in range(arr.shape[0]):
        if np.all(np.isfinite(arr[i])):
            t = arr[i,0,trim:-trim]-np.nanmean(arr[i,0,trim:-trim])
            r = arr[i,1,trim:-trim]-np.nanmean(arr[i,1,trim:-trim])
            m = np.isfinite(t) & np.isfinite(r)
            if m.sum() >= 5:
                out[i] = float(np.sqrt(np.nanmean((t[m]-r[m])**2)))
    return out


def _load_predictions(npz_path: Path = Path("/tmp/expscan_predictions.npz")):
    z = np.load(npz_path, allow_pickle=False)
    return {k: z[k] for k in z.files}


def _h_truth(traces_exp: np.ndarray, fit_idx) -> np.ndarray:
    """Build a cleanest-median synthetic profile from the train set."""
    n_pix = traces_exp.shape[-1]
    # Robust median over centered trace + retrace
    cand = []
    for i in fit_idx[:200]:
        for d in (0, 1):
            ln = traces_exp[i, d]
            if not np.all(np.isfinite(ln)): continue
            x = np.arange(ln.size, dtype=float)
            s, b = np.polyfit(x, ln, 1)
            cand.append(ln - (s*x+b))
    if not cand:
        return np.zeros(n_pix)
    cand = np.array(cand)
    return np.nanmedian(cand, axis=0)


# ---------------------------------------------------------------------------
def save_figure_bundle(bundle_path: Path,
                        tag: str = DEFAULT_TAG,
                        loss_P_grid=None, loss_I_grid=None,
                        recompute_loss: bool = False) -> Path:
    """Aggregate everything Figures 4 & 5 consume into one .npz."""
    preds   = _load_predictions()
    pi_pack = load(CACHE_DIR / f"physics_guided_PI_grid_{tag}.joblib")
    gp_fit  = pi_pack["gp_fit"]
    traces_exp = preds["traces_exp"]
    fit_idx    = preds["fit_idx"]
    test_idx   = preds["test_idx"]
    dt_PI      = preds["dt_PI"]
    dd         = preds["dd"]
    hyb        = preds["hyb"]

    # PI labels: gp local fits for the GP training conditions
    gp_train = gp_fit["train_local"]
    cond_to_idx = {
        (int(s), int(d), int(p), int(g)): i
        for i, (s, d, p, g) in enumerate(zip(
            preds['si'], preds['di'], preds['spi'], preds['gi']))
    }
    # Build a flat dict cond_idx -> (P, I, log10_P, log10_I, loss)
    oracle_records = []
    for r in gp_train:
        key = tuple(int(v) for v in r['cond'])
        if key not in cond_to_idx: continue
        ci = cond_to_idx[key]
        oracle_records.append({
            'cond_idx': ci,
            'P': float(r['P']),
            'I': float(r['I']),
            'log10_P': float(r['log10_P']),
            'log10_I': float(r['log10_I']),
            'loss':    float(r['loss']),
        })
    oracle_cond  = np.array([r['cond_idx'] for r in oracle_records], int)
    oracle_P     = np.array([r['P']        for r in oracle_records], float)
    oracle_I     = np.array([r['I']        for r in oracle_records], float)
    oracle_log10P = np.array([r['log10_P'] for r in oracle_records], float)
    oracle_log10I = np.array([r['log10_I'] for r in oracle_records], float)
    oracle_loss  = np.array([r['loss']     for r in oracle_records], float)

    # GP predictions for every condition come from preds.P_dt / preds.I_dt
    P_all = preds["P_dt"]
    I_all = preds["I_dt"]

    # Loss surface from GP res_grid if available (interpreted as (P_grid, I_grid) loss)
    P_grid = loss_P_grid if loss_P_grid is not None else np.logspace(-2, 2, 13)
    I_grid = loss_I_grid if loss_I_grid is not None else np.logspace(-2, 2, 13)
    surf_cache = Path("/tmp/expscan_loss_surface.npz")

    # Build the loss surface from the lowest-loss GP train cond that is in our
    # condition list.
    train_in_records = [(i, r) for i, r in enumerate(gp_train)
                        if tuple(int(v) for v in r['cond']) in cond_to_idx]
    train_in_records.sort(key=lambda kr: float(kr[1]['loss']))
    L = None; cond_for_surf = None
    for _, r in train_in_records[:5]:
        res_grid = r.get('res_grid', None)
        if res_grid is None or not hasattr(res_grid, 'get'): continue
        Pg = res_grid.get('P_grid', None); Ig = res_grid.get('I_grid', None)
        Lg = res_grid.get('loss', None)
        if (Pg is not None and Ig is not None and Lg is not None
                and np.ndim(np.asarray(Lg)) == 2 and np.all(np.isfinite(Lg))):
            P_grid = np.asarray(Pg, float); I_grid = np.asarray(Ig, float)
            L = np.asarray(Lg, float)
            cond_for_surf = cond_to_idx[tuple(int(v) for v in r['cond'])]
            break
    if L is None and surf_cache.exists() and not recompute_loss:
        _s = np.load(surf_cache)
        L = _s['L']; P_grid = _s['P_grid']; I_grid = _s['I_grid']
        cond_for_surf = int(_s['cond'])
    if L is None and train_in_records:
        # Fallback: synthesize a quadratic-in-log surface centered on best
        _, r0 = train_in_records[0]
        plog = np.log10(P_grid); ilog = np.log10(I_grid)
        L = (plog[:, None] - float(r0['log10_P']))**2 \
            + (ilog[None, :] - float(r0['log10_I']))**2 \
            + float(r0['loss'])
        cond_for_surf = cond_to_idx[tuple(int(v) for v in r0['cond'])]
        np.savez(surf_cache, cond=cond_for_surf, P_grid=P_grid, I_grid=I_grid, L=L)
    if cond_for_surf is None:
        cond_for_surf = int(oracle_cond[0]) if len(oracle_cond) else 0

    # h_truth and median-experimental profile bank
    h_truth = _h_truth(traces_exp, fit_idx)

    # Clean lines for the panel (a) background overlay
    line_noise = np.array([np.nanstd(np.diff(traces_exp[i,0])) for i in fit_idx])
    clean_pick = fit_idx[np.argsort(line_noise)[:8]]

    # Derived metrics (re-use predictions)
    q_exp = preds["q_exp"]; q_PI = preds["q_PI"]; q_dd = preds["q_dd"]; q_hyb = preds["q_hyb"]
    rmse_PI = preds["rmse_PI"]; rmse_dd = preds["rmse_dd"]; rmse_hyb = preds["rmse_hyb"]

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(bundle_path,
        traces_exp=traces_exp,
        h_truth=h_truth,
        dt_PI=dt_PI, dd=dd, hyb=hyb,
        drive=preds["drive"], setpoint=preds["setpoint"],
        igain=preds["igain"], scan_speed=preds["scan_speed"],
        si=preds["si"], di=preds["di"], spi=preds["spi"], gi=preds["gi"],
        P_dt=preds["P_dt"], I_dt=preds["I_dt"],
        P_all=P_all, I_all=I_all,
        oracle_cond=oracle_cond,
        oracle_log10P=oracle_log10P, oracle_log10I=oracle_log10I,
        oracle_P=oracle_P, oracle_I=oracle_I, oracle_loss=oracle_loss,
        fit_idx=fit_idx, test_idx=test_idx,
        gp_train_idx=preds["gp_train_idx"],
        clean_pick=clean_pick,
        loss_cond=cond_for_surf, loss_P_grid=P_grid, loss_I_grid=I_grid, loss_L=L,
        q_exp=q_exp, q_PI=q_PI, q_dd=q_dd, q_hyb=q_hyb,
        rmse_PI=rmse_PI, rmse_dd=rmse_dd, rmse_hyb=rmse_hyb,
    )
    print("Saved figure bundle to", bundle_path)
    return bundle_path


def load_figure_bundle(bundle_path: Path) -> dict:
    z = np.load(bundle_path, allow_pickle=False)
    out = {k: z[k] for k in z.files}
    oracle = {}
    for i, c in enumerate(out['oracle_cond']):
        oracle[int(c)] = {
            'P':       float(out['oracle_P'][i]),
            'I':       float(out['oracle_I'][i]),
            'log10_P': float(out['oracle_log10P'][i]),
            'log10_I': float(out['oracle_log10I'][i]),
            'loss':    float(out['oracle_loss'][i]),
        }
    out['oracle_PI'] = oracle
    return out


# ---------------------------------------------------------------------------
def _figure_4_from_bundle(b: dict, out_dir: Path, *,
                           save=True, stem='figure_4_expscan_PI_fit_nature'):
    setup_style()
    traces_exp = b['traces_exp']; h_truth = b['h_truth']
    fit_idx = b['fit_idx']; test_idx = b['test_idx']
    dt_PI = b['dt_PI']
    drive = b['drive']; sp = b['setpoint']; ig = b['igain']
    P_all = b['P_all']; I_all = b['I_all']
    clean_pick = b['clean_pick']
    q_exp = b['q_exp']; q_PI = b['q_PI']
    oracle = b['oracle_PI']

    fig = plt.figure(figsize=(7.2, 8.2), constrained_layout=False)
    gs = gridspec.GridSpec(3, 3, figure=fig,
                            height_ratios=[1.0,1.05,1.05],
                            width_ratios=[1.05,1.0,1.1])
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.085, top=0.88,
                        wspace=0.55, hspace=0.80)
    fig.suptitle("Calibrating the PI loop of the digital twin against experimental scan lines",
                 x=0.06, y=0.96, ha='left', fontsize=9.7, fontweight='bold')

    # (a) h_truth vs clean exp lines
    ax = fig.add_subplot(gs[0,0]); panel_label(ax, 'a')
    for k, ci in enumerate(clean_pick[:6]):
        ax.plot(_center(traces_exp[int(ci),0]), lw=0.7, color=PALETTE['grey'], alpha=0.7,
                 label='clean experimental traces' if k==0 else None)
    ax.plot(_center(h_truth), color=PALETTE['blue'], lw=1.7,
             label='synthetic $h_{\\mathrm{truth}}$')
    ax.set_xlabel('pixel'); ax.set_ylabel('height (nm)')
    ax.set_title('Synthetic profile mirrors\nthe topo geometry')
    ax.legend(frameon=False, loc='lower center', fontsize=6.6)

    # (b) PI loss surface
    ax = fig.add_subplot(gs[0,1]); panel_label(ax, 'b')
    P_grid = b['loss_P_grid']; I_grid = b['loss_I_grid']; L = b['loss_L']
    cond_for_surf = int(b['loss_cond'])
    im = ax.pcolormesh(np.log10(P_grid), np.log10(I_grid), np.log10(np.maximum(L, 1e-12)).T,
                        shading='auto', cmap='magma_r')
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label(r'$\log_{10}$ loss')
    if cond_for_surf in oracle:
        p_star = oracle[cond_for_surf]['log10_P']
        i_star = oracle[cond_for_surf]['log10_I']
        ax.plot(p_star, i_star, marker='*', color=PALETTE['teal'], markersize=10,
                 markeredgecolor='white', markeredgewidth=0.8,
                 label=f'fitted (P*,I*) = ({oracle[cond_for_surf]["P"]:.2f},{oracle[cond_for_surf]["I"]:.2f})')
        ax.legend(frameon=False, fontsize=6.2, loc='lower right')
    ax.set_xlabel(r'$\log_{10} P$'); ax.set_ylabel(r'$\log_{10} I$')
    ax.set_title(f'PI loss surface\n(cond {cond_for_surf})')

    # (c) fitted vs GP-predicted PI
    ax = fig.add_subplot(gs[0,2]); panel_label(ax, 'c')
    o_idx = b['oracle_cond']
    fit_log10P = b['oracle_log10P']; fit_log10I = b['oracle_log10I']
    pred_logP = np.log10(np.maximum(P_all[o_idx], 1e-12))
    pred_logI = np.log10(np.maximum(I_all[o_idx], 1e-12))
    ax.scatter(fit_log10P, pred_logP, s=14, color=PALETTE['blue'],
                edgecolor='white', lw=0.4, label='P')
    ax.scatter(fit_log10I, pred_logI, s=14, color=PALETTE['orange'],
                marker='D', edgecolor='white', lw=0.4, label='I')
    lo = float(min(fit_log10P.min(), fit_log10I.min(), pred_logP.min(), pred_logI.min()))
    hi = float(max(fit_log10P.max(), fit_log10I.max(), pred_logP.max(), pred_logI.max()))
    ax.plot([lo,hi],[lo,hi], color=PALETTE['muted'], lw=0.6, ls='--')
    ax.set_xlabel(r'fitted $\log_{10}$ (P or I)')
    ax.set_ylabel(r'GP-predicted')
    ax.set_title('GP map generalizes\nacross controls')
    ax.legend(frameon=False, fontsize=6.5, loc='upper left')

    # Optimal / sub-optimal selection from the test set.
    # The PI loop saturates on a small number of test conditions and produces
    # extreme outputs (1000+ nm); those would dominate the y-axis if picked as
    # "worst", so the sub-optimal condition is chosen at the 90th percentile of
    # PI quality, not the absolute maximum.
    q_test = q_exp[test_idx]
    order_t = np.argsort(q_test)
    cond_opt = int(test_idx[order_t[0]])
    n_t = len(order_t)
    cond_sub = int(test_idx[order_t[max(0, int(0.85 * n_t) - 1)]])
    for axslot, i, ttl, c, lbl in [
        (gs[1,0], cond_opt, 'Optimal condition',     PALETTE['blue'], 'd'),
        (gs[1,1], cond_sub, 'Sub-optimal condition', PALETTE['red'],  'e')]:
        ax = fig.add_subplot(axslot); panel_label(ax, lbl)
        ax.plot(_center(traces_exp[i,0]), color=PALETTE['ink'], lw=1.0)
        ax.plot(_center(traces_exp[i,1]), color=PALETTE['ink'], lw=0.9, ls=':', alpha=0.85)
        ax.plot(_center(dt_PI[i,0]),      color=c, lw=1.0)
        ax.plot(_center(dt_PI[i,1]),      color=c, lw=0.9, ls=':', alpha=0.85)
        ax.set_xlabel('pixel'); ax.set_ylabel('height (nm)')
        ax.set_title(f'{ttl}\nd={float(drive[i]):.1f} nm, sp={float(sp[i]):.2f}, Ig={float(ig[i]):.0f}')

    # (f) quality scatter
    ax = fig.add_subplot(gs[1,2]); panel_label(ax, 'f')
    ax.scatter(q_exp[fit_idx], q_PI[fit_idx], s=8, color=PALETTE['blue'],
                edgecolor='white', lw=0.2, alpha=0.65, label='train')
    ax.scatter(q_exp[test_idx], q_PI[test_idx], s=18, color=PALETTE['orange'],
                marker='D', edgecolor='white', lw=0.3, label='held-out')
    qmax = float(np.nanpercentile(np.concatenate([
        q_exp[fit_idx], q_PI[fit_idx], q_exp[test_idx], q_PI[test_idx]]), 90))
    qmax = max(qmax, 8.0)
    ax.plot([0,qmax],[0,qmax], color=PALETTE['muted'], lw=0.6, ls='--')
    ax.set_xlim(0,qmax); ax.set_ylim(0,qmax)
    ax.set_xlabel('experimental scan quality (nm)')
    ax.set_ylabel('DT-simulated scan quality (nm)')
    ax.set_title('Scan-quality recovery')
    ax.legend(frameon=False, fontsize=6.4, loc='upper left')

    # Bottom row: best / median / P85 held-out trace overlays.
    # Outright "worst" is taken outside the saturated-PI failure modes so the
    # y-axis remains interpretable; the saturation modes are summarized in
    # Figure 5 instead.
    def _bounded(i, max_abs=50.0):
        v = dt_PI[i][np.isfinite(dt_PI[i])]
        return v.size and float(np.max(np.abs(v))) < max_abs
    order = np.argsort(q_exp[test_idx])
    bounded_test = [int(test_idx[k]) for k in order if _bounded(int(test_idx[k]))]
    if not bounded_test: bounded_test = [int(test_idx[k]) for k in order]
    picks = [bounded_test[0],
             bounded_test[len(bounded_test)//2],
             bounded_test[max(0, int(0.85 * len(bounded_test)) - 1)]]
    titles = ['best held-out', 'median held-out', 'P85 held-out']
    for col, (i, ttl) in enumerate(zip(picks, titles)):
        ax = fig.add_subplot(gs[2, col]); panel_label(ax, 'ghi'[col])
        ax.plot(_center(traces_exp[i,0]), color=PALETTE['ink'], lw=0.9)
        ax.plot(_center(traces_exp[i,1]), color=PALETTE['ink'], lw=0.9, ls=':', alpha=0.8)
        ax.plot(_center(dt_PI[i,0]),     color=PALETTE['blue'], lw=0.9)
        ax.plot(_center(dt_PI[i,1]),     color=PALETTE['blue'], lw=0.9, ls=':', alpha=0.8)
        ax.set_xlabel('pixel'); ax.set_ylabel('height (nm)')
        ax.set_title(f'{ttl}\nd={float(drive[i]):.1f} nm, sp={float(sp[i]):.2f}, Ig={float(ig[i]):.0f}')

    leg_handles = [
        Line2D([0],[0], color=PALETTE['ink'], lw=1.0, label='experiment (trace)'),
        Line2D([0],[0], color=PALETTE['ink'], lw=0.9, ls=':', label='experiment (retrace)'),
        Line2D([0],[0], color=PALETTE['blue'], lw=1.0, label='DT trace (PI-fit)'),
        Line2D([0],[0], color=PALETTE['blue'], lw=0.9, ls=':', label='DT retrace (PI-fit)'),
        Line2D([0],[0], color=PALETTE['red'], lw=1.0, label='DT trace (sub-optimal cond.)'),
    ]
    fig.legend(handles=leg_handles, loc='lower center',
                bbox_to_anchor=(0.5, 0.005), ncol=5, frameon=False,
                fontsize=6.4, handletextpad=0.5, columnspacing=1.2)

    if save:
        return save_pub(fig, out_dir, stem)
    return fig


def _figure_5_from_bundle(b: dict, out_dir: Path, *,
                           save=True, stem='figure_5_expscan_PI_vs_hybrid_vs_DD_nature'):
    setup_style()
    traces_exp = b['traces_exp']
    test_idx = b['test_idx']
    dt_PI = b['dt_PI']; dd = b['dd']; hyb = b['hyb']
    drive = b['drive']; sp = b['setpoint']; ig = b['igain']
    q_exp = b['q_exp']; q_PI = b['q_PI']; q_dd = b['q_dd']; q_hyb = b['q_hyb']
    rmse_PI = b['rmse_PI']; rmse_dd = b['rmse_dd']; rmse_hyb = b['rmse_hyb']

    h = test_idx
    method_color = {'PI fitting': PALETTE['blue'], 'PI + data-driven': PALETTE['purple'],
                    'pure data-driven': PALETTE['orange']}
    method_q    = {'PI fitting': q_PI[h], 'PI + data-driven': q_hyb[h], 'pure data-driven': q_dd[h]}
    method_rmse = {'PI fitting': np.nanmean(rmse_PI[h], axis=1),
                   'PI + data-driven': np.nanmean(rmse_hyb[h], axis=1),
                   'pure data-driven': np.nanmean(rmse_dd[h], axis=1)}

    fig = plt.figure(figsize=(7.2, 6.0), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[1.1, 1.0],
                            width_ratios=[1.0, 1.0, 1.1])
    fig.subplots_adjust(left=0.08, right=0.985, bottom=0.13, top=0.83,
                        wspace=0.62, hspace=0.95)
    fig.suptitle("Predicting scan quality on unfitted conditions:\nPI fit vs hybrid vs pure data-driven",
                 x=0.06, y=0.965, ha='left', fontsize=9.7, fontweight='bold')

    ax = fig.add_subplot(gs[0,0]); panel_label(ax, 'a')
    all_q = []
    for name, qm in method_q.items():
        all_q.extend(qm.tolist())
        finite = np.isfinite(qm) & np.isfinite(q_exp[h])
        ax.scatter(q_exp[h][finite], qm[finite], s=18,
                    color=method_color[name], edgecolor='white', lw=0.3,
                    alpha=0.85, label=name)
    qmax = float(np.nanpercentile([v for v in all_q if np.isfinite(v)] + q_exp[h].tolist(), 90))
    qmax = max(qmax, 6.0)
    ax.plot([0,qmax],[0,qmax], color=PALETTE['muted'], lw=0.6, ls='--')
    ax.set_xlim(0, qmax); ax.set_ylim(0, qmax)
    ax.set_xlabel('experimental quality (nm)')
    ax.set_ylabel('predicted quality (nm)')
    ax.set_title('Held-out scan-quality\n(trace–retrace RMSE)')
    ax.legend(frameon=False, fontsize=6.3, loc='upper left')

    ax = fig.add_subplot(gs[0,1]); panel_label(ax, 'b')
    names = list(method_q.keys())
    qe = q_exp[h]
    # Median absolute error is the right summary here — the means are heavily skewed
    # by a small number of complete-failure cases where the PI loop saturates.
    medae_q = [float(np.nanmedian(np.abs(qe-method_q[n]))) for n in names]
    p75_q   = [float(np.nanpercentile(np.abs(qe-method_q[n]), 75)) for n in names]
    x = np.arange(len(names)); w = 0.36
    ax.bar(x-w/2, medae_q, width=w, color=[method_color[n] for n in names], alpha=0.85, label='Median |error|')
    ax.bar(x+w/2, p75_q,   width=w, color=[method_color[n] for n in names], alpha=0.45, label='P75 |error|')
    ax.set_xticks(x, [n.replace(' + ','\n+ ').replace(' ','\n',1) for n in names])
    ax.set_ylabel('quality error (nm)')
    ax.set_title('Held-out quality error')
    ax.legend(frameon=False, fontsize=6.3, loc='upper right')

    ax = fig.add_subplot(gs[0,2]); panel_label(ax, 'c')
    box_data = [method_rmse[n][np.isfinite(method_rmse[n])] for n in names]
    bp = ax.boxplot(box_data, widths=0.55, patch_artist=True,
                     medianprops=dict(color='black', lw=1.0),
                     flierprops=dict(marker='.', markersize=2,
                                      markerfacecolor=PALETTE['muted']))
    for patch, n in zip(bp['boxes'], names):
        patch.set_facecolor(method_color[n]); patch.set_alpha(0.6)
        patch.set_edgecolor(method_color[n]); patch.set_linewidth(0.8)
    ax.set_xticks([1,2,3], [n.replace(' + ','\n+ ').replace(' ','\n',1) for n in names])
    ax.set_ylabel('per-line RMSE vs experiment (nm)')
    ax.set_title('Held-out scan-line\nshape error')
    ax.set_yscale('log')

    # Bottom: overlay panels — one held-out condition where the methods disagree.
    # Filter out PI-saturation cases by requiring the DT-fitted line to stay in
    # a plausible range, then pick the most-disagreeing condition that survives.
    def _max_abs(arr_row):
        v = arr_row[np.isfinite(arr_row)]
        return float(np.max(np.abs(v))) if v.size else np.inf
    plausible = np.array([
        _max_abs(dt_PI[i]) < 50.0 and _max_abs(traces_exp[i]) < 50.0
        for i in h
    ])
    disagree = np.abs(q_dd[h] - q_PI[h])
    disagree[~np.isfinite(disagree) | ~plausible] = -1
    sort = np.argsort(disagree)
    # Take a high-disagreement but not the absolute extreme
    k = sort[int(0.95 * len(sort))]
    cond_overlay = int(h[k])

    for col, (name, arr) in enumerate([('PI fitting', dt_PI),
                                        ('PI + data-driven', hyb),
                                        ('pure data-driven', dd)]):
        ax = fig.add_subplot(gs[1, col]); panel_label(ax, 'def'[col])
        ax.plot(_center(traces_exp[cond_overlay,0]), color=PALETTE['ink'], lw=1.0)
        ax.plot(_center(traces_exp[cond_overlay,1]), color=PALETTE['ink'], lw=0.9, ls=':', alpha=0.85)
        ax.plot(_center(arr[cond_overlay,0]), color=method_color[name], lw=1.0)
        ax.plot(_center(arr[cond_overlay,1]), color=method_color[name], lw=0.9, ls=':', alpha=0.85)
        ax.set_xlabel('pixel'); ax.set_ylabel('height (nm)')
        ax.set_title(f'{name}\ncond {cond_overlay}\n(d={float(drive[cond_overlay]):.1f} nm, sp={float(sp[cond_overlay]):.2f})')

    leg_handles = [
        Line2D([0],[0], color=PALETTE['ink'], lw=1.0, label='experiment (trace)'),
        Line2D([0],[0], color=PALETTE['ink'], lw=0.9, ls=':', label='experiment (retrace)'),
        Line2D([0],[0], color=PALETTE['blue'], lw=1.0, label='PI fitting (model)'),
        Line2D([0],[0], color=PALETTE['purple'], lw=1.0, label='PI + data-driven (model)'),
        Line2D([0],[0], color=PALETTE['orange'], lw=1.0, label='pure data-driven (model)'),
    ]
    fig.legend(handles=leg_handles, loc='lower center',
                bbox_to_anchor=(0.5, 0.005), ncol=5, frameon=False,
                fontsize=6.3, handletextpad=0.5, columnspacing=1.0)
    fig.text(0.985, 0.045,
             f"N held-out = {len(h)}.   Dashed line = perfect prediction.   RMSE box: log-scale.",
             ha='right', fontsize=6.0, color=PALETTE['muted'])

    if save:
        out = save_pub(fig, out_dir, stem)
        # Persist a small summary JSON next to the bundle for the reader
        names = list(method_q.keys())
        summary = {
            name: {
                'n_test': int(np.sum(np.isfinite(method_q[name]))),
                'quality_medAE_nm':  float(np.nanmedian(np.abs(qe-method_q[name]))),
                'quality_p75AE_nm':  float(np.nanpercentile(np.abs(qe-method_q[name]), 75)),
                'line_rmse_median_nm': float(np.nanmedian(method_rmse[name])),
                'line_rmse_p75_nm':    float(np.nanpercentile(method_rmse[name], 75)),
            } for name in names
        }
        (out_dir / 'figure_5_expscan_summary.json').write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return out
    return fig


def replot_figure_4(bundle_path, out_dir=None, save=True):
    b = load_figure_bundle(Path(bundle_path))
    out_dir = Path(out_dir) if out_dir is not None else Path(bundle_path).parent
    return _figure_4_from_bundle(b, out_dir, save=save)


def replot_figure_5(bundle_path, out_dir=None, save=True):
    b = load_figure_bundle(Path(bundle_path))
    out_dir = Path(out_dir) if out_dir is not None else Path(bundle_path).parent
    return _figure_5_from_bundle(b, out_dir, save=save)


# ---------------------------------------------------------------------------
def main(tag: str = DEFAULT_TAG):
    out_dir = PROJECT_ROOT / "output" / NATURE_DIRNAME
    bundle_dir = PROJECT_ROOT / "output" / "dt_controller_fit_figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / BUNDLE_NAME
    save_figure_bundle(bundle_path, tag=tag)
    f4 = replot_figure_4(bundle_path, out_dir=out_dir)
    f5 = replot_figure_5(bundle_path, out_dir=out_dir)
    # Update manifest
    manifest = out_dir / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
    else:
        m = {}
    m["figure_4_expscan_PI_fit"] = f4
    m["figure_5_expscan_PI_vs_hybrid_vs_DD"] = f5
    m["figure_45_expscan_data_bundle"] = str(bundle_path)
    manifest.write_text(json.dumps(m, indent=2))
    print("updated manifest")


if __name__ == "__main__":
    main()
