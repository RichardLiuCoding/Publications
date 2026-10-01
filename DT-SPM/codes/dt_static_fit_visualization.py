"""
dt_static_fit_visualization.py
==============================

Visualization helpers for GP-based static SPM digital-twin calibration.

Use this after running:

    gp_fit = fit_gp_static_controller_calibration(...)

Main functions
--------------
1. test_rows_to_dataframe(gp_fit)
    Convert held-out test results into a table.

2. plot_test_loss_distribution(gp_fit)
    Histogram and sorted curve of held-out losses.

3. plot_metric_alignment(gp_fit)
    Scatter plots of experimental vs DT-predicted static metrics.

4. plot_test_scan_example(...)
    Re-run one held-out test condition and plot:
        - experimental trace/retrace height
        - simulated trace/retrace height on a synthetic line
        - metric comparison bars

5. plot_test_scan_examples(...)
    Plot several examples selected from best/worst/random/mixed test rows.

Important
---------
The simulated line is a synthetic line with matched roughness/rate statistics,
not the exact experimental ground-truth topography. Therefore, do not interpret
pixelwise sim-vs-exp overlay as a strict height reconstruction. The metric
alignment plots are the primary validation.
"""

from __future__ import annotations

from typing import Optional, Sequence, Dict, Any, List, Tuple
import numpy as np
import matplotlib.pyplot as plt


try:
    import pandas as pd
except Exception:
    pd = None


# =============================================================================
# Import scaffold with both package and local fallback
# =============================================================================

try:
    from codes.dt_static_dynamic_calibration_scaffold_v3 import (
        run_scanner_line,
        get_height_from_out,
        compute_height_static_signature,
        compare_static_signatures,
        prepare_fd_table,
        robust_mad,
    )
except Exception:
    try:
        from dt_static_dynamic_calibration_scaffold_v3 import (
            run_scanner_line,
            get_height_from_out,
            compute_height_static_signature,
            compare_static_signatures,
            prepare_fd_table,
            robust_mad,
        )
    except Exception:
        from codes.dt_static_dynamic_calibration_scaffold_v2 import (
            run_scanner_line,
            get_height_from_out,
            compute_height_static_signature,
            compare_static_signatures,
            prepare_fd_table,
            robust_mad,
        )


DEFAULT_METRIC_KEYS = [
    "trrt",
    "grad_mean",
    "grad_std",
    "grad_p95",
    "height_mad",
    "height_range_p99_p01",
]


# =============================================================================
# Small helpers
# =============================================================================

def _finite_xy(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    return x[m], y[m], m


def _r2_score(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    m = np.isfinite(y_true) & np.isfinite(y_pred)
    if np.sum(m) < 3:
        return np.nan
    yt = y_true[m]
    yp = y_pred[m]
    denom = np.sum((yt - np.mean(yt)) ** 2)
    if denom <= 0:
        return np.nan
    return float(1.0 - np.sum((yp - yt) ** 2) / denom)


def _corrcoef(x, y):
    x, y, _ = _finite_xy(x, y)
    if x.size < 3:
        return np.nan
    if np.nanstd(x) <= 0 or np.nanstd(y) <= 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _safe_log10(x, floor=1e-12):
    x = np.asarray(x, dtype=float)
    return np.log10(np.maximum(x, floor))


def _format_cond(cond):
    return f"s={cond[0]}, d={cond[1]}, sp={cond[2]}, g={cond[3]}"


def _center_line(x):
    x = np.asarray(x, dtype=float).ravel()
    return x - np.nanmedian(x)


def _zscore_robust_line(x):
    x = np.asarray(x, dtype=float).ravel()
    return (x - np.nanmedian(x)) / max(robust_mad(x), 1e-12)


def _preprocess_line_for_plot(x, mode: Optional[str]):
    if mode is None or mode == "raw":
        return np.asarray(x, dtype=float).ravel()
    if mode == "center":
        return _center_line(x)
    if mode == "robust_zscore":
        return _zscore_robust_line(x)
    raise ValueError("mode must be None, 'raw', 'center', or 'robust_zscore'.")


def get_test_rows(gp_fit):
    rows = gp_fit.get("test_rows", None)
    if rows is None:
        raise ValueError("gp_fit does not contain 'test_rows'.")
    return rows


# =============================================================================
# Convert test rows to table
# =============================================================================

def test_rows_to_records(
    gp_fit,
    metric_keys: Optional[Sequence[str]] = None,
):
    """
    Convert gp_fit['test_rows'] to list of flat dictionaries.

    Each row includes:
        cond indices
        controls
        P/I predictions and GP uncertainty
        test loss
        exp_<metric>
        sim_<metric>
        diff_<metric>
        relsym_<metric>
    """
    if metric_keys is None:
        metric_keys = DEFAULT_METRIC_KEYS

    records = []

    for row in get_test_rows(gp_fit):
        cond = tuple(row["cond"])
        ev = row.get("test_eval", {})
        controls = ev.get("controls", {})
        sim_sig = ev.get("sim_sig", {})
        exp_sig = ev.get("exp_sig", {})
        terms = row.get("test_terms", ev.get("terms", {}))

        rec = {
            "si": int(cond[0]),
            "di": int(cond[1]),
            "spi": int(cond[2]),
            "gi": int(cond[3]),
            "cond": cond,
            "test_loss": float(row.get("test_loss", ev.get("loss", np.nan))),
            "P_pred": float(row.get("P_pred", np.nan)),
            "I_pred": float(row.get("I_pred", np.nan)),
            "log10_P_pred": float(row.get("log10_P_pred", np.nan)),
            "log10_I_pred": float(row.get("log10_I_pred", np.nan)),
            "log10_P_std": float(row.get("log10_P_std", np.nan)),
            "log10_I_std": float(row.get("log10_I_std", np.nan)),
        }

        for k, v in controls.items():
            rec[k] = v

        for k in metric_keys:
            a = float(sim_sig.get(k, np.nan))
            b = float(exp_sig.get(k, np.nan))
            rec[f"sim_{k}"] = a
            rec[f"exp_{k}"] = b
            rec[f"diff_{k}"] = a - b
            rec[f"absdiff_{k}"] = abs(a - b) if np.isfinite(a) and np.isfinite(b) else np.nan
            rec[f"relsym_{k}"] = abs(a - b) / (abs(a) + abs(b) + 1e-12) if np.isfinite(a) and np.isfinite(b) else np.nan

        for k, v in terms.items():
            rec[f"term_{k}"] = v

        records.append(rec)

    return records


def test_rows_to_dataframe(
    gp_fit,
    metric_keys: Optional[Sequence[str]] = None,
):
    """
    Return pandas DataFrame of held-out test results.

    If pandas is not available, returns list of records.
    """
    records = test_rows_to_records(gp_fit, metric_keys=metric_keys)
    if pd is None:
        return records
    return pd.DataFrame(records)


# =============================================================================
# Summary plots
# =============================================================================

def plot_test_loss_distribution(
    gp_fit,
    *,
    bins: int = 30,
    figsize: Tuple[float, float] = (10, 4),
):
    """
    Plot histogram and sorted curve of held-out test losses.
    """
    rows = get_test_rows(gp_fit)
    losses = np.array([r.get("test_loss", np.nan) for r in rows], dtype=float)
    finite = losses[np.isfinite(losses)]

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].hist(finite, bins=bins)
    axes[0].set_xlabel("test loss")
    axes[0].set_ylabel("count")
    axes[0].set_title("Held-out loss distribution")

    if finite.size > 0:
        axes[1].plot(np.sort(finite), marker=".", lw=1)
    axes[1].set_xlabel("sorted test condition")
    axes[1].set_ylabel("test loss")
    axes[1].set_title("Sorted held-out losses")

    fig.tight_layout()
    return fig, axes


def plot_metric_alignment(
    gp_fit,
    *,
    metric_keys: Optional[Sequence[str]] = None,
    log_scale: bool = False,
    ncols: int = 3,
    figsize_per_panel: Tuple[float, float] = (4.0, 3.5),
    annotate: bool = True,
):
    """
    Scatter plot of DT-predicted metric vs experimental metric for held-out tests.

    x-axis: experimental metric
    y-axis: simulated / DT-predicted metric
    """
    if metric_keys is None:
        metric_keys = DEFAULT_METRIC_KEYS

    records = test_rows_to_records(gp_fit, metric_keys=metric_keys)

    n = len(metric_keys)
    ncols = int(ncols)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(figsize_per_panel[0] * ncols, figsize_per_panel[1] * nrows),
        squeeze=False,
    )

    for ax, key in zip(axes.ravel(), metric_keys):
        exp = np.array([r[f"exp_{key}"] for r in records], dtype=float)
        sim = np.array([r[f"sim_{key}"] for r in records], dtype=float)

        x, y, m = _finite_xy(exp, sim)

        if log_scale:
            x_plot = _safe_log10(x)
            y_plot = _safe_log10(y)
            xlabel = f"log10 experimental {key}"
            ylabel = f"log10 DT {key}"
        else:
            x_plot = x
            y_plot = y
            xlabel = f"experimental {key}"
            ylabel = f"DT {key}"

        ax.scatter(x_plot, y_plot, s=25, alpha=0.8)

        if x_plot.size > 0:
            lo = np.nanmin(np.r_[x_plot, y_plot])
            hi = np.nanmax(np.r_[x_plot, y_plot])
            if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                pad = 0.05 * (hi - lo)
                ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "--", lw=1)
                ax.set_xlim(lo - pad, hi + pad)
                ax.set_ylim(lo - pad, hi + pad)

        r = _corrcoef(x_plot, y_plot)
        r2 = _r2_score(x_plot, y_plot)

        if annotate:
            ax.text(
                0.05,
                0.95,
                f"r = {r:.2f}\nR² = {r2:.2f}\nn = {x_plot.size}",
                transform=ax.transAxes,
                va="top",
                ha="left",
            )

        ax.set_title(key)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

    for ax in axes.ravel()[n:]:
        ax.axis("off")

    fig.tight_layout()
    return fig, axes


def plot_metric_residuals(
    gp_fit,
    *,
    metric_keys: Optional[Sequence[str]] = None,
    ncols: int = 3,
    figsize_per_panel: Tuple[float, float] = (4.0, 3.0),
):
    """
    Plot symmetric residual terms for each metric across held-out traces.

    Values close to 0 mean good alignment.
    Values close to 1 mean poor alignment.
    """
    if metric_keys is None:
        metric_keys = DEFAULT_METRIC_KEYS

    records = test_rows_to_records(gp_fit, metric_keys=metric_keys)

    n = len(metric_keys)
    ncols = int(ncols)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(figsize_per_panel[0] * ncols, figsize_per_panel[1] * nrows),
        squeeze=False,
    )

    for ax, key in zip(axes.ravel(), metric_keys):
        vals = np.array([r[f"relsym_{key}"] for r in records], dtype=float)
        vals = vals[np.isfinite(vals)]
        ax.hist(vals, bins=20)
        ax.set_title(key)
        ax.set_xlabel("symmetric normalized residual")
        ax.set_ylabel("count")

    for ax in axes.ravel()[n:]:
        ax.axis("off")

    fig.tight_layout()
    return fig, axes


def plot_loss_vs_gp_uncertainty(
    gp_fit,
    *,
    figsize: Tuple[float, float] = (5, 4),
):
    """
    Plot held-out test loss vs GP predictive uncertainty in log10 P/I.
    """
    records = test_rows_to_records(gp_fit)

    loss = np.array([r["test_loss"] for r in records], dtype=float)
    uP = np.array([r["log10_P_std"] for r in records], dtype=float)
    uI = np.array([r["log10_I_std"] for r in records], dtype=float)
    u = np.sqrt(uP ** 2 + uI ** 2)

    m = np.isfinite(loss) & np.isfinite(u)

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(u[m], loss[m], s=30, alpha=0.8)
    ax.set_xlabel("GP uncertainty, sqrt(std_logP² + std_logI²)")
    ax.set_ylabel("test loss")
    ax.set_title("Does GP uncertainty flag bad predictions?")
    fig.tight_layout()
    return fig, ax


# =============================================================================
# Select examples
# =============================================================================

def select_test_rows(
    gp_fit,
    *,
    n_examples: int = 6,
    mode: str = "mixed",
    seed: int = 0,
):
    """
    Select held-out test rows.

    mode:
        "best"   : lowest-loss rows
        "worst"  : highest-loss rows
        "random" : random finite-loss rows
        "mixed"  : spread across low/median/high losses
    """
    rows = list(get_test_rows(gp_fit))
    rows = [r for r in rows if np.isfinite(r.get("test_loss", np.nan))]

    if len(rows) == 0:
        return []

    rows_sorted = sorted(rows, key=lambda r: r["test_loss"])

    n_examples = min(int(n_examples), len(rows_sorted))

    if mode == "best":
        return rows_sorted[:n_examples]

    if mode == "worst":
        return rows_sorted[-n_examples:][::-1]

    if mode == "random":
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(rows_sorted), size=n_examples, replace=False)
        return [rows_sorted[i] for i in idx]

    if mode == "mixed":
        if n_examples == 1:
            return [rows_sorted[len(rows_sorted) // 2]]
        idx = np.linspace(0, len(rows_sorted) - 1, n_examples).astype(int)
        return [rows_sorted[i] for i in idx]

    raise ValueError("mode must be 'best', 'worst', 'random', or 'mixed'.")


# =============================================================================
# Rerun and plot held-out scan examples
# =============================================================================

def rerun_test_row_prediction(
    scanner,
    traces_exp_height,
    synthetic_lines,
    row,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg,
    synthetic_line_index: int = 0,
    fd_cache: Optional[Dict[int, Any]] = None,
):
    """
    Rerun one held-out row using GP-predicted P/I and one synthetic line.
    """
    cond = tuple(row["cond"])
    si, di, spi, gi = cond

    if fd_cache is None:
        fd_cache = {}

    if di not in fd_cache:
        fd_cache[di] = prepare_fd_table(scanner, float(drives_nm[di]), scanner_cfg.fd_n_d)

    h_line = np.asarray(synthetic_lines[int(synthetic_line_index)], dtype=float).ravel()

    out = run_scanner_line(
        scanner,
        h_line,
        drive_nm=float(drives_nm[di]),
        setpoint=float(setpoints[spi]),
        scan_speed_hat=float(scan_speeds_hat[si]),
        P=float(row["P_pred"]),
        I=float(row["I_pred"]),
        cfg=scanner_cfg,
        fd_table=fd_cache[di],
    )

    sim_tr, sim_rt = get_height_from_out(out)

    exp_tr = np.asarray(traces_exp_height[si, di, spi, gi, 0], dtype=float).ravel()
    exp_rt = np.asarray(traces_exp_height[si, di, spi, gi, 1], dtype=float).ravel()

    return {
        "cond": cond,
        "row": row,
        "out": out,
        "sim_tr": sim_tr,
        "sim_rt": sim_rt,
        "exp_tr": exp_tr,
        "exp_rt": exp_rt,
        "h_line": h_line,
    }


def plot_test_scan_example(
    scanner,
    traces_exp_height,
    synthetic_lines,
    row,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg,
    synthetic_line_index: int = 0,
    trim: int = 10,
    metric_keys: Optional[Sequence[str]] = None,
    preprocess: Optional[str] = "center",
    fd_cache: Optional[Dict[int, Any]] = None,
    figsize: Tuple[float, float] = (11, 8),
):
    """
    Plot one held-out test example.

    preprocess:
        "center"         : subtract median from each line. Recommended.
        "robust_zscore"  : subtract median and divide by MAD.
        "raw" or None    : raw values.
    """
    if metric_keys is None:
        metric_keys = DEFAULT_METRIC_KEYS

    data = rerun_test_row_prediction(
        scanner,
        traces_exp_height,
        synthetic_lines,
        row,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        scanner_cfg=scanner_cfg,
        synthetic_line_index=synthetic_line_index,
        fd_cache=fd_cache,
    )

    cond = data["cond"]
    si, di, spi, gi = cond

    exp_tr = _preprocess_line_for_plot(data["exp_tr"], preprocess)
    exp_rt = _preprocess_line_for_plot(data["exp_rt"], preprocess)
    sim_tr = _preprocess_line_for_plot(data["sim_tr"], preprocess)
    sim_rt = _preprocess_line_for_plot(data["sim_rt"], preprocess)

    exp_sig = compute_height_static_signature(data["exp_tr"], data["exp_rt"], trim=trim)
    sim_sig = compute_height_static_signature(data["sim_tr"], data["sim_rt"], trim=trim)

    loss, terms = compare_static_signatures(sim_sig, exp_sig)

    fig = plt.figure(figsize=figsize)

    ax1 = fig.add_subplot(3, 1, 1)
    ax1.plot(exp_tr, label="exp trace", lw=1.5)
    ax1.plot(exp_rt, label="exp retrace", lw=1.5)
    ax1.set_ylabel("exp height")
    ax1.legend(loc="best")
    ax1.set_title(
        f"Experimental held-out scan, cond=({_format_cond(cond)})"
    )

    ax2 = fig.add_subplot(3, 1, 2)
    ax2.plot(sim_tr, label="DT trace", lw=1.5)
    ax2.plot(sim_rt, label="DT retrace", lw=1.5)
    ax2.set_ylabel("DT height")
    ax2.legend(loc="best")
    ax2.set_title(
        f"DT prediction on synthetic line #{synthetic_line_index}; "
        f"P={row.get('P_pred', np.nan):.3g}, I={row.get('I_pred', np.nan):.3g}, "
        f"loss={loss:.3g}"
    )

    ax3 = fig.add_subplot(3, 1, 3)
    x = np.arange(len(metric_keys))
    width = 0.38
    exp_vals = np.array([exp_sig.get(k, np.nan) for k in metric_keys], dtype=float)
    sim_vals = np.array([sim_sig.get(k, np.nan) for k in metric_keys], dtype=float)

    ax3.bar(x - width / 2, exp_vals, width, label="exp")
    ax3.bar(x + width / 2, sim_vals, width, label="DT")
    ax3.set_xticks(x)
    ax3.set_xticklabels(metric_keys, rotation=30, ha="right")
    ax3.set_ylabel("metric value")
    ax3.set_title("Static metric comparison")
    ax3.legend(loc="best")

    controls = data["row"].get("test_eval", {}).get("controls", {})
    subtitle = (
        f"speed={float(scan_speeds_hat[si]):.3g}, "
        f"drive={float(drives_nm[di]):.3g}, "
        f"setpoint={float(setpoints[spi]):.3g}, "
        f"I_exp={float(i_gains_exp[gi]):.3g}"
    )
    fig.suptitle(subtitle, y=0.995)

    fig.tight_layout()
    return fig, (ax1, ax2, ax3), data


def plot_test_scan_examples(
    scanner,
    traces_exp_height,
    synthetic_lines,
    gp_fit,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg,
    n_examples: int = 6,
    mode: str = "mixed",
    synthetic_line_index: int = 0,
    trim: int = 10,
    preprocess: Optional[str] = "center",
    seed: int = 0,
):
    """
    Plot multiple held-out scan examples.

    Returns
    -------
    figs, selected_rows
    """
    rows = select_test_rows(
        gp_fit,
        n_examples=n_examples,
        mode=mode,
        seed=seed,
    )

    fd_cache = {}
    figs = []

    for r in rows:
        fig, axes, data = plot_test_scan_example(
            scanner,
            traces_exp_height,
            synthetic_lines,
            r,
            scan_speeds_hat=scan_speeds_hat,
            drives_nm=drives_nm,
            setpoints=setpoints,
            i_gains_exp=i_gains_exp,
            scanner_cfg=scanner_cfg,
            synthetic_line_index=synthetic_line_index,
            trim=trim,
            preprocess=preprocess,
            fd_cache=fd_cache,
        )
        figs.append(fig)

    return figs, rows


# =============================================================================
# One-call dashboard
# =============================================================================

def plot_static_fit_dashboard(
    gp_fit,
    *,
    metric_keys: Optional[Sequence[str]] = None,
    log_metric_alignment: bool = False,
):
    """
    Create the standard summary figures for static GP fit.
    """
    figs = {}

    fig, axes = plot_test_loss_distribution(gp_fit)
    figs["loss_distribution"] = fig

    fig, axes = plot_metric_alignment(
        gp_fit,
        metric_keys=metric_keys,
        log_scale=log_metric_alignment,
    )
    figs["metric_alignment"] = fig

    fig, axes = plot_metric_residuals(
        gp_fit,
        metric_keys=metric_keys,
    )
    figs["metric_residuals"] = fig

    fig, ax = plot_loss_vs_gp_uncertainty(gp_fit)
    figs["loss_vs_uncertainty"] = fig

    return figs
