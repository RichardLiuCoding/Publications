"""
dt_gp_static_calibration.py
===========================

GP-based static controller calibration for SPM digital twin.

This replaces the global linear mapping

    P_sim = c_P * I_exp
    I_sim = c_I * I_exp

with a two-stage GP mapping:

Stage 1:
    Randomly select N train traces.
    Fit local [log10_P, log10_I] for each selected trace using height-channel
    statistical rewards.

Stage 2:
    Train two GP regressors:

        X = [log10(scan_speed_hat), drive_nm, setpoint, log10(I_exp)]
        yP = log10(P_sim)
        yI = log10(I_sim)

Stage 3:
    Randomly select N test traces.
    Predict [P_sim, I_sim] from GP.
    Evaluate the static scan-reward loss on held-out traces.

This file expects your existing scaffold functions/classes from:

    codes.dt_static_dynamic_calibration_scaffold

Specifically:
    ScannerRunConfig
    compute_height_static_signature
    compare_static_signatures
    run_scanner_line
    get_height_from_out
    prepare_fd_table

If your module path is different, change the import block below.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Sequence, Tuple, Dict, Any, List
import numpy as np

from scipy.optimize import differential_evolution, minimize

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import (
        ConstantKernel,
        Matern,
        WhiteKernel,
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
except Exception as exc:
    raise ImportError(
        "This GP calibration module requires scikit-learn. "
        "Install with: pip install scikit-learn"
    ) from exc


# =============================================================================
# Import your existing DT scaffold
# =============================================================================

try:
    # Preferred: updated scaffold with classifier-aware dynamic labels and
    # symmetric static metric loss.
    from codes.dt_static_dynamic_calibration_scaffold_v2 import (
        ScannerRunConfig,
        compute_height_static_signature,
        compare_static_signatures,
        run_scanner_line,
        get_height_from_out,
        prepare_fd_table,
    )
except Exception:
    try:
        from dt_static_dynamic_calibration_scaffold_v2 import (
            ScannerRunConfig,
            compute_height_static_signature,
            compare_static_signatures,
            run_scanner_line,
            get_height_from_out,
            prepare_fd_table,
        )
    except Exception:
        # Backward-compatible fallback. This works, but does not include the
        # symmetric metric loss unless you replace your old scaffold with v2.
        try:
            from codes.dt_static_dynamic_calibration_scaffold import (
                ScannerRunConfig,
                compute_height_static_signature,
                compare_static_signatures,
                run_scanner_line,
                get_height_from_out,
                prepare_fd_table,
            )
        except Exception:
            from dt_static_dynamic_calibration_scaffold import (
                ScannerRunConfig,
                compute_height_static_signature,
                compare_static_signatures,
                run_scanner_line,
                get_height_from_out,
                prepare_fd_table,
            )


try:
    # Preferred when files are stored in a subfolder imported as `codes.*`.
    from codes.dt_trace_classifier import (
        TraceUsabilityConfig,
        classify_height_trace_pair,
        classify_conditions,
        split_informative_conditions,
        summarize_classification_rows,
    )
except Exception:
    try:
        # Fallback when the codes folder itself is added to sys.path.
        from dt_trace_classifier import (
            TraceUsabilityConfig,
            classify_height_trace_pair,
            classify_conditions,
            split_informative_conditions,
            summarize_classification_rows,
        )
    except Exception:
        TraceUsabilityConfig = None
        classify_height_trace_pair = None
        classify_conditions = None
        split_informative_conditions = None
        summarize_classification_rows = None


# =============================================================================
# Configs
# =============================================================================

@dataclass
class GPSubsetCalibrationConfig:
    """
    Configuration for GP-based static calibration.
    """

    # Random subset sizes.
    n_train: int = 100
    n_test: int = 50
    seed: int = 0

    # Number of synthetic lines to average for each experimental condition.
    # Use 2 or 3 while debugging; use 8 for final fitting.
    n_lines_train: int = 3
    n_lines_test: int = 8

    # Edge trimming for height statistics.
    trim: int = 10

    # Static classifier: flat/no-response traces are excluded from local P/I
    # fitting and GP train/test. They should be kept for dynamic quality/safety.
    filter_uninformative: bool = True
    min_mad: float = 0.02
    min_range: float = 0.10
    min_grad_mad: float = 0.002
    min_nonzero_frac: float = 0.05
    min_finite_frac: float = 0.90
    max_mad: Optional[float] = None
    max_range: Optional[float] = None
    max_grad_mad: Optional[float] = None

    # Static loss weights.
    w_trrt: float = 2.0
    w_grad_mean: float = 2.0
    w_grad_std: float = 1.0
    w_grad_p95: float = 0.5
    w_height_mad: float = 0.5
    w_height_range: float = 0.2

    # Per-trace P/I fitting bounds in log10 space.
    bounds_logPI: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (-4.0, 2.0),  # log10 P
        (-5.0, 3.0),  # log10 I
    )

    # Optimizer controls for each local trace.
    # For speed, keep these small at first.
    use_grid_init: bool = True
    n_grid_P: int = 9
    n_grid_I: int = 9
    maxiter_global: int = 20
    popsize: int = 5
    maxiter_local: int = 80

    # Whether to locally refine after grid/global search.
    do_local_refine: bool = True

    # Optional fixed index subsets.
    speed_indices: Optional[Sequence[int]] = None
    drive_indices: Optional[Sequence[int]] = None
    setpoint_indices: Optional[Sequence[int]] = None
    gain_indices: Optional[Sequence[int]] = None

    # Test mode.
    # If True, also fit local oracle P/I on the test traces so you can measure
    # GP prediction error in logP/logI. This is slower.
    fit_test_oracle: bool = False

    # GP settings.
    gp_alpha: float = 1e-6
    gp_n_restarts_optimizer: int = 4
    normalize_y: bool = True



def make_trace_usability_config_from_gp_cfg(cfg):
    if TraceUsabilityConfig is None:
        return None
    return TraceUsabilityConfig(
        trim=cfg.trim,
        min_mad=cfg.min_mad,
        min_range=cfg.min_range,
        min_grad_mad=cfg.min_grad_mad,
        min_nonzero_frac=cfg.min_nonzero_frac,
        min_finite_frac=cfg.min_finite_frac,
        max_mad=cfg.max_mad,
        max_range=cfg.max_range,
        max_grad_mad=cfg.max_grad_mad,
    )


# =============================================================================
# Condition sampling
# =============================================================================

def _indices_or_all(indices, n):
    if indices is None:
        return np.arange(n, dtype=int)
    return np.asarray(indices, dtype=int)


def make_condition_list(
    traces_exp_height,
    *,
    speed_indices=None,
    drive_indices=None,
    setpoint_indices=None,
    gain_indices=None,
):
    """
    Return list of condition indices:
        (speed_index, drive_index, setpoint_index, gain_index)
    """
    traces_exp_height = np.asarray(traces_exp_height)
    n_speed, n_drive, n_sp, n_gain, two, n_pix = traces_exp_height.shape
    if two != 2:
        raise ValueError("traces_exp_height must have shape (..., 2, pixels).")

    speed_ids = _indices_or_all(speed_indices, n_speed)
    drive_ids = _indices_or_all(drive_indices, n_drive)
    sp_ids = _indices_or_all(setpoint_indices, n_sp)
    gain_ids = _indices_or_all(gain_indices, n_gain)

    conds = []
    for si in speed_ids:
        for di in drive_ids:
            for spi in sp_ids:
                for gi in gain_ids:
                    conds.append((int(si), int(di), int(spi), int(gi)))
    return conds


def random_train_test_conditions(
    traces_exp_height,
    *,
    n_train: int = 100,
    n_test: int = 50,
    seed: int = 0,
    speed_indices=None,
    drive_indices=None,
    setpoint_indices=None,
    gain_indices=None,
    usability_cfg=None,
    filter_uninformative: bool = True,
    return_rejected: bool = False,
):
    """
    Randomly split available conditions into train and test sets.

    If filter_uninformative=True, only conditions classified as informative are
    sampled. Rejected conditions are returned when return_rejected=True.
    """
    conds = make_condition_list(
        traces_exp_height,
        speed_indices=speed_indices,
        drive_indices=drive_indices,
        setpoint_indices=setpoint_indices,
        gain_indices=gain_indices,
    )

    rejected = []
    informative = conds

    if filter_uninformative:
        if split_informative_conditions is None:
            raise RuntimeError(
                "filter_uninformative=True but dt_trace_classifier.py could not be imported. "
                "Put dt_trace_classifier.py in the same codes/ folder and import the GP module "
                "as `from codes.dt_gp_static_calibration_v3 import ...`, or add the codes folder "
                "to sys.path before importing."
            )

        # We already built conds using requested subsets, but the classifier helper
        # can do the same filtering directly from index subsets.
        train_dummy, test_dummy, informative, rejected = split_informative_conditions(
            traces_exp_height,
            n_train=len(conds),
            n_test=0,
            seed=seed,
            cfg=usability_cfg,
            speed_indices=speed_indices,
            drive_indices=drive_indices,
            setpoint_indices=setpoint_indices,
            gain_indices=gain_indices,
        )

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(informative))

    n_total = len(informative)
    n_train = min(int(n_train), n_total)
    n_test = min(int(n_test), max(0, n_total - n_train))

    train = [informative[i] for i in perm[:n_train]]
    test = [informative[i] for i in perm[n_train:n_train + n_test]]

    if return_rejected:
        return train, test, informative, rejected

    return train, test


# =============================================================================
# Feature transform for GP mapping
# =============================================================================

def condition_to_gp_features(
    cond,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
):
    """
    Features for GP controller mapping.

    X = [
        log10(scan_speed_hat),
        drive_nm,
        setpoint,
        log10(I_exp),
    ]
    """
    si, di, spi, gi = cond

    speed = max(float(scan_speeds_hat[si]), 1e-12)
    drive = float(drives_nm[di])
    sp = float(setpoints[spi])
    ig = max(float(i_gains_exp[gi]), 1e-12)

    return np.array(
        [
            np.log10(speed),
            drive,
            sp,
            np.log10(ig),
        ],
        dtype=float,
    )


def conditions_to_gp_X(
    conds,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
):
    return np.vstack(
        [
            condition_to_gp_features(
                c,
                scan_speeds_hat=scan_speeds_hat,
                drives_nm=drives_nm,
                setpoints=setpoints,
                i_gains_exp=i_gains_exp,
            )
            for c in conds
        ]
    )


# =============================================================================
# Metric/loss wrappers
# =============================================================================

def static_metric_weights(cfg: GPSubsetCalibrationConfig):
    return {
        "trrt": cfg.w_trrt,
        "grad_mean": cfg.w_grad_mean,
        "grad_std": cfg.w_grad_std,
        "grad_p95": cfg.w_grad_p95,
        "height_mad": cfg.w_height_mad,
        "height_range_p99_p01": cfg.w_height_range,
    }

# Here is the function to remove the latency between trace and retrace

from scipy.interpolate import CubicSpline
from scipy.optimize import minimize

def diff_shifted(y1, y2, thres=0.1):
    '''
    Find the optimal x-shift of y2 with respect to y1 that minimizes the absolute
    difference between y1 and y2_shifted. If the amount of shift is larger than
    thres * len(y1), the original y1 and y2 will be returned.

    Input:
        y1   - list: 1D scan trace/retrace
        y2   - list: 1D scan trace/retrace
        thres- list: threshold to determine if fitting is failed. If x_shift is
                    greater than thres * len(y1), original y1 and y2 will be returned.

    Returns:
        y1_cut     - y1 is cut to keep overlapped part with y2_shifted
        y2_shifted - shifted y2 array

    Usage:
        y1_shifted, y2_shifted = diff_shifted(y1, y2)

    '''
    # Initial guess for the shift
    initial_shift = 0

    x = np.arange(len(y1))

    # Run the optimization
    result = minimize(mse_shift, initial_shift, args=(x, y1, y2))

    # Best shift found
    best_shift = result.x

    # Create a spline of the second trace
    spline = CubicSpline(x, y2)

    # Shift x values by the found optimal shift
    x_shifted = x - best_shift

    # Evaluate the shifted trace at the original x values
    y2_optimal_shifted = spline(x_shifted)

    if np.abs(best_shift) > thres * len(y1):
        return y1, y2
    elif best_shift > 0:
        return y1[int(best_shift)+1:], y2_optimal_shifted[int(best_shift)+1:]
    elif best_shift < -1:
        return y1[:int(best_shift)-1], y2_optimal_shifted[:int(best_shift)-1]
    else:
        return y1, y2

def mse_shift(shift, x, y1, y2):
    # Create a spline of the second trace
    spline = CubicSpline(x, y2)

    # Shift x values
    x_shifted = x - shift

    # Evaluate the shifted trace at the original x values
    y2_shifted = spline(x_shifted)

    # Compute the MSE between the original and shifted traces
    mse = np.mean((y1 - y2_shifted)**2)
    return mse

def get_exp_height_signature_for_condition(
    traces_exp_height,
    cond,
    *,
    trim: int,
):
    si, di, spi, gi = cond
    h_tr = np.asarray(traces_exp_height[si, di, spi, gi, 0], dtype=float)
    h_rt = np.asarray(traces_exp_height[si, di, spi, gi, 1], dtype=float)
    h_tr, h_rt = diff_shifted(h_tr, h_rt)
    return compute_height_static_signature(h_tr, h_rt, trim=trim)


def evaluate_PI_on_condition(
    scanner,
    traces_exp_height,
    synthetic_lines,
    cond,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    P: float,
    I: float,
    scanner_cfg: ScannerRunConfig,
    trim: int,
    metric_weights: Dict[str, float],
    n_lines: int,
    fd_table=None,
):
    """
    Evaluate a candidate P/I on one experimental condition.
    """
    si, di, spi, gi = cond

    speed = float(scan_speeds_hat[si])
    drive = float(drives_nm[di])
    sp = float(setpoints[spi])

    if fd_table is None:
        fd_table = prepare_fd_table(scanner, drive, scanner_cfg.fd_n_d)

    exp_sig = get_exp_height_signature_for_condition(
        traces_exp_height,
        cond,
        trim=trim,
    )

    sigs = []

    for h_line in synthetic_lines[:int(n_lines)]:
        out = run_scanner_line(
            scanner,
            h_line,
            drive_nm=drive,
            setpoint=sp,
            scan_speed_hat=speed,
            P=float(P),
            I=float(I),
            cfg=scanner_cfg,
            fd_table=fd_table,
        )

        sim_tr, sim_rt = get_height_from_out(out)
        sim_tr, sim_rt = diff_shifted(sim_tr, sim_rt)
        
        sigs.append(
            compute_height_static_signature(
                sim_tr,
                sim_rt,
                trim=trim,
            )
        )

    # Average simulated signatures over synthetic lines.
    sim_sig = {}
    for k in sigs[0].keys():
        vals = [s[k] for s in sigs if k in s and np.isfinite(s[k])]
        sim_sig[k] = float(np.mean(vals)) if vals else np.inf

    loss, terms = compare_static_signatures(
        sim_sig,
        exp_sig,
        weights=metric_weights,
    )

    return {
        "loss": float(loss),
        "terms": terms,
        "sim_sig": sim_sig,
        "exp_sig": exp_sig,
        "controls": {
            "scan_speed_hat": speed,
            "drive_nm": drive,
            "setpoint": sp,
            "I_exp": float(i_gains_exp[gi]),
            "P": float(P),
            "I": float(I),
        },
    }


# =============================================================================
# Local P/I fitting for one trace
# =============================================================================

def fit_local_PI_for_condition(
    scanner,
    traces_exp_height,
    synthetic_lines,
    cond,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg: ScannerRunConfig,
    cfg: GPSubsetCalibrationConfig,
    fd_table=None,
):
    """
    Fit [log10_P, log10_I] for one experimental condition.
    """
    metric_weights = static_metric_weights(cfg)
    bounds = list(cfg.bounds_logPI)

    si, di, spi, gi = cond
    drive = float(drives_nm[di])

    if fd_table is None:
        fd_table = prepare_fd_table(scanner, drive, scanner_cfg.fd_n_d)

    def obj(x):
        x = np.asarray(x, dtype=float).ravel()
        logP, logI = x
        P = 10.0 ** logP
        I = 10.0 ** logI

        ev = evaluate_PI_on_condition(
            scanner,
            traces_exp_height,
            synthetic_lines,
            cond,
            scan_speeds_hat=scan_speeds_hat,
            drives_nm=drives_nm,
            setpoints=setpoints,
            i_gains_exp=i_gains_exp,
            P=P,
            I=I,
            scanner_cfg=scanner_cfg,
            trim=cfg.trim,
            metric_weights=metric_weights,
            n_lines=cfg.n_lines_train,
            fd_table=fd_table,
        )
        return ev["loss"]

    best_x = None
    best_loss = np.inf
    res_grid = None
    res_global = None

    if cfg.use_grid_init:
        p_grid = np.linspace(bounds[0][0], bounds[0][1], int(cfg.n_grid_P))
        i_grid = np.linspace(bounds[1][0], bounds[1][1], int(cfg.n_grid_I))

        loss_grid = np.full((len(p_grid), len(i_grid)), np.nan)

        for ip, logP in enumerate(p_grid):
            for ii, logI in enumerate(i_grid):
                x = np.array([logP, logI], dtype=float)
                loss = obj(x)
                loss_grid[ip, ii] = loss
                if np.isfinite(loss) and loss < best_loss:
                    best_loss = float(loss)
                    best_x = x.copy()

        res_grid = {
            "logP_grid": p_grid,
            "logI_grid": i_grid,
            "loss_grid": loss_grid,
        }

        if best_x is None:
            best_x = np.array(
                [
                    0.5 * (bounds[0][0] + bounds[0][1]),
                    0.5 * (bounds[1][0] + bounds[1][1]),
                ],
                dtype=float,
            )

    else:
        res_global = differential_evolution(
            obj,
            bounds=bounds,
            seed=cfg.seed + 1000 * si + 100 * di + 10 * spi + gi,
            maxiter=cfg.maxiter_global,
            popsize=cfg.popsize,
            polish=False,
            updating="immediate",
            workers=1,
        )
        best_x = np.asarray(res_global.x, dtype=float)
        best_loss = float(res_global.fun)

    res_local = None
    if cfg.do_local_refine:
        res_local = minimize(
            obj,
            best_x,
            method="Powell",
            bounds=bounds,
            options={
                "maxiter": cfg.maxiter_local,
                "xtol": 1e-3,
                "ftol": 1e-4,
            },
        )

        if np.isfinite(res_local.fun) and res_local.fun < best_loss:
            best_x = np.asarray(res_local.x, dtype=float)
            best_loss = float(res_local.fun)

    # Full final evaluation.
    final = evaluate_PI_on_condition(
        scanner,
        traces_exp_height,
        synthetic_lines,
        cond,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        P=10.0 ** best_x[0],
        I=10.0 ** best_x[1],
        scanner_cfg=scanner_cfg,
        trim=cfg.trim,
        metric_weights=metric_weights,
        n_lines=cfg.n_lines_train,
        fd_table=fd_table,
    )

    return {
        "cond": tuple(int(v) for v in cond),
        "x": best_x,
        "log10_P": float(best_x[0]),
        "log10_I": float(best_x[1]),
        "P": float(10.0 ** best_x[0]),
        "I": float(10.0 ** best_x[1]),
        "loss": float(best_loss),
        "final_eval": final,
        "res_grid": res_grid,
        "res_global": res_global,
        "res_local": res_local,
    }


def fit_local_PI_for_conditions(
    scanner,
    traces_exp_height,
    synthetic_lines,
    conds,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg: ScannerRunConfig,
    cfg: GPSubsetCalibrationConfig,
    verbose: bool = True,
):
    """
    Fit local P/I labels for a list of randomly selected conditions.
    """
    results = []

    # Cache FD tables by drive index.
    fd_tables = {}
    for cond in conds:
        di = int(cond[1])
        if di not in fd_tables:
            fd_tables[di] = prepare_fd_table(
                scanner,
                float(drives_nm[di]),
                scanner_cfg.fd_n_d,
            )

    for n, cond in enumerate(conds):
        if verbose:
            print(f"[local PI fit] {n+1}/{len(conds)} cond={cond}")

        res = fit_local_PI_for_condition(
            scanner,
            traces_exp_height,
            synthetic_lines,
            cond,
            scan_speeds_hat=scan_speeds_hat,
            drives_nm=drives_nm,
            setpoints=setpoints,
            i_gains_exp=i_gains_exp,
            scanner_cfg=scanner_cfg,
            cfg=cfg,
            fd_table=fd_tables[int(cond[1])],
        )

        results.append(res)

        if verbose:
            print(
                f"    loss={res['loss']:.5g}, "
                f"P={res['P']:.4g}, I={res['I']:.4g}"
            )

    return results


# =============================================================================
# GP mapping
# =============================================================================

def make_gp_regressor(cfg: GPSubsetCalibrationConfig):
    """
    GP pipeline:
        StandardScaler -> GaussianProcessRegressor

    Matern kernel is a good default for smooth but not overly smooth mappings.
    """
    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * Matern(
            length_scale=np.ones(4),
            length_scale_bounds=(1e-2, 1e2),
            nu=2.5,
        )
        + WhiteKernel(
            noise_level=1e-3,
            noise_level_bounds=(1e-8, 1e0),
        )
    )

    gp = GaussianProcessRegressor(
        kernel=kernel,
        alpha=cfg.gp_alpha,
        normalize_y=cfg.normalize_y,
        n_restarts_optimizer=cfg.gp_n_restarts_optimizer,
        random_state=cfg.seed,
    )

    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("gp", gp),
        ]
    )


def train_gp_PI_mapping(
    local_results,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    cfg: GPSubsetCalibrationConfig,
):
    """
    Train GP regressors for log10 P and log10 I.
    """
    conds = [r["cond"] for r in local_results]

    X = conditions_to_gp_X(
        conds,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
    )

    yP = np.array([r["log10_P"] for r in local_results], dtype=float)
    yI = np.array([r["log10_I"] for r in local_results], dtype=float)

    mask = np.isfinite(X).all(axis=1) & np.isfinite(yP) & np.isfinite(yI)

    X_fit = X[mask]
    yP_fit = yP[mask]
    yI_fit = yI[mask]
    conds_fit = [c for c, m in zip(conds, mask) if m]

    gpP = make_gp_regressor(cfg)
    gpI = make_gp_regressor(cfg)

    gpP.fit(X_fit, yP_fit)
    gpI.fit(X_fit, yI_fit)

    return {
        "gpP": gpP,
        "gpI": gpI,
        "X_train": X_fit,
        "yP_train": yP_fit,
        "yI_train": yI_fit,
        "conds_train": conds_fit,
        "feature_names": [
            "log10_scan_speed_hat",
            "drive_nm",
            "setpoint",
            "log10_I_exp",
        ],
    }


def predict_PI_with_gp(
    gp_pack,
    conds,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    return_std: bool = True,
):
    """
    Predict P/I for conditions using trained GP mapping.
    """
    X = conditions_to_gp_X(
        conds,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
    )

    if return_std:
        logP_mu, logP_std = gp_pack["gpP"].predict(X, return_std=True)
        logI_mu, logI_std = gp_pack["gpI"].predict(X, return_std=True)
    else:
        logP_mu = gp_pack["gpP"].predict(X)
        logI_mu = gp_pack["gpI"].predict(X)
        logP_std = np.zeros_like(logP_mu)
        logI_std = np.zeros_like(logI_mu)

    rows = []
    for cond, lp, li, sp, si in zip(conds, logP_mu, logI_mu, logP_std, logI_std):
        rows.append(
            {
                "cond": tuple(int(v) for v in cond),
                "log10_P_pred": float(lp),
                "log10_I_pred": float(li),
                "log10_P_std": float(sp),
                "log10_I_std": float(si),
                "P_pred": float(10.0 ** lp),
                "I_pred": float(10.0 ** li),
            }
        )

    return rows


# =============================================================================
# Test evaluation
# =============================================================================

def evaluate_gp_mapping_on_conditions(
    scanner,
    traces_exp_height,
    synthetic_lines,
    pred_rows,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    scanner_cfg: ScannerRunConfig,
    cfg: GPSubsetCalibrationConfig,
    verbose: bool = True,
):
    """
    Evaluate GP-predicted P/I on held-out conditions.
    """
    metric_weights = static_metric_weights(cfg)

    fd_tables = {}
    out_rows = []

    for n, pr in enumerate(pred_rows):
        cond = pr["cond"]
        di = int(cond[1])

        if di not in fd_tables:
            fd_tables[di] = prepare_fd_table(
                scanner,
                float(drives_nm[di]),
                scanner_cfg.fd_n_d,
            )

        ev = evaluate_PI_on_condition(
            scanner,
            traces_exp_height,
            synthetic_lines,
            cond,
            scan_speeds_hat=scan_speeds_hat,
            drives_nm=drives_nm,
            setpoints=setpoints,
            i_gains_exp=i_gains_exp,
            P=pr["P_pred"],
            I=pr["I_pred"],
            scanner_cfg=scanner_cfg,
            trim=cfg.trim,
            metric_weights=metric_weights,
            n_lines=cfg.n_lines_test,
            fd_table=fd_tables[di],
        )

        row = dict(pr)
        row.update(
            {
                "test_loss": ev["loss"],
                "test_terms": ev["terms"],
                "test_eval": ev,
            }
        )
        out_rows.append(row)

        if verbose:
            print(
                f"[GP test] {n+1}/{len(pred_rows)} cond={cond}, "
                f"loss={ev['loss']:.5g}, "
                f"P={pr['P_pred']:.4g}, I={pr['I_pred']:.4g}"
            )

    return out_rows


def summarize_test_rows(test_rows):
    losses = np.array([r["test_loss"] for r in test_rows], dtype=float)
    finite = losses[np.isfinite(losses)]

    if finite.size == 0:
        return {
            "n_test": len(test_rows),
            "n_finite": 0,
            "loss_mean": np.inf,
            "loss_median": np.inf,
        }

    return {
        "n_test": int(len(test_rows)),
        "n_finite": int(finite.size),
        "loss_mean": float(np.mean(finite)),
        "loss_median": float(np.median(finite)),
        "loss_p25": float(np.percentile(finite, 25)),
        "loss_p75": float(np.percentile(finite, 75)),
        "loss_min": float(np.min(finite)),
        "loss_max": float(np.max(finite)),
    }


def compare_gp_to_oracle_test_fits(
    pred_rows,
    oracle_results,
):
    """
    Compare GP-predicted logP/logI to individually fitted oracle logP/logI
    on test traces.
    """
    oracle_by_cond = {tuple(r["cond"]): r for r in oracle_results}

    rows = []
    for pr in pred_rows:
        cond = tuple(pr["cond"])
        if cond not in oracle_by_cond:
            continue
        orow = oracle_by_cond[cond]

        rows.append(
            {
                "cond": cond,
                "log10_P_pred": pr["log10_P_pred"],
                "log10_I_pred": pr["log10_I_pred"],
                "log10_P_oracle": orow["log10_P"],
                "log10_I_oracle": orow["log10_I"],
                "err_log10_P": pr["log10_P_pred"] - orow["log10_P"],
                "err_log10_I": pr["log10_I_pred"] - orow["log10_I"],
                "gp_loss": pr.get("test_loss", np.nan),
                "oracle_loss": orow["loss"],
            }
        )

    if len(rows) == 0:
        return {
            "rows": rows,
            "summary": {},
        }

    eP = np.array([r["err_log10_P"] for r in rows], dtype=float)
    eI = np.array([r["err_log10_I"] for r in rows], dtype=float)
    gp_loss = np.array([r["gp_loss"] for r in rows], dtype=float)
    oracle_loss = np.array([r["oracle_loss"] for r in rows], dtype=float)

    summary = {
        "n": int(len(rows)),
        "mae_log10_P": float(np.nanmean(np.abs(eP))),
        "mae_log10_I": float(np.nanmean(np.abs(eI))),
        "rmse_log10_P": float(np.sqrt(np.nanmean(eP ** 2))),
        "rmse_log10_I": float(np.sqrt(np.nanmean(eI ** 2))),
        "gp_loss_mean": float(np.nanmean(gp_loss)),
        "oracle_loss_mean": float(np.nanmean(oracle_loss)),
        "loss_ratio_gp_to_oracle": float(
            np.nanmean(gp_loss) / max(np.nanmean(oracle_loss), 1e-12)
        ),
    }

    return {
        "rows": rows,
        "summary": summary,
    }


# =============================================================================
# Full pipeline
# =============================================================================

def fit_gp_static_controller_calibration(
    scanner,
    traces_exp_height,
    synthetic_lines,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
    *,
    scanner_cfg: ScannerRunConfig,
    cfg: GPSubsetCalibrationConfig,
    verbose: bool = True,
):
    """
    Full GP calibration pipeline:

    1. Randomly select train/test conditions.
    2. Fit local P/I for train conditions.
    3. Train GP mapping from controls to local log10(P/I).
    4. Predict P/I on test conditions.
    5. Evaluate test loss.
    6. Optionally fit local oracle P/I for test conditions.
    """

    usability_cfg = make_trace_usability_config_from_gp_cfg(cfg)

    train_conds, test_conds, informative_conds, rejected_conditions = random_train_test_conditions(
        traces_exp_height,
        n_train=cfg.n_train,
        n_test=cfg.n_test,
        seed=cfg.seed,
        speed_indices=cfg.speed_indices,
        drive_indices=cfg.drive_indices,
        setpoint_indices=cfg.setpoint_indices,
        gain_indices=cfg.gain_indices,
        usability_cfg=usability_cfg,
        filter_uninformative=cfg.filter_uninformative,
        return_rejected=True,
    )

    if verbose:
        print(f"Selected {len(train_conds)} train traces and {len(test_conds)} test traces.")
        print(f"Informative conditions available: {len(informative_conds)}")
        print(f"Rejected/uninformative conditions: {len(rejected_conditions)}")
        if summarize_classification_rows is not None and len(rejected_conditions) > 0:
            print("Rejected summary:", summarize_classification_rows(rejected_conditions))

    # Stage 1: local P/I fits on train subset.
    train_local = fit_local_PI_for_conditions(
        scanner,
        traces_exp_height,
        synthetic_lines,
        train_conds,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        scanner_cfg=scanner_cfg,
        cfg=cfg,
        verbose=verbose,
    )

    # Stage 2: GP map from controls -> logP/logI.
    gp_pack = train_gp_PI_mapping(
        train_local,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        cfg=cfg,
    )

    if verbose:
        print("Trained GP mapping.")
        print("GP P kernel:", gp_pack["gpP"].named_steps["gp"].kernel_)
        print("GP I kernel:", gp_pack["gpI"].named_steps["gp"].kernel_)

    # Stage 3: predict on test subset.
    pred_test = predict_PI_with_gp(
        gp_pack,
        test_conds,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        return_std=True,
    )

    # Stage 4: evaluate test traces using GP-predicted P/I.
    test_rows = evaluate_gp_mapping_on_conditions(
        scanner,
        traces_exp_height,
        synthetic_lines,
        pred_test,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        scanner_cfg=scanner_cfg,
        cfg=cfg,
        verbose=verbose,
    )

    test_summary = summarize_test_rows(test_rows)

    oracle_test = None
    oracle_comparison = None

    if cfg.fit_test_oracle:
        if verbose:
            print("Fitting oracle local P/I on held-out test traces...")

        oracle_test = fit_local_PI_for_conditions(
            scanner,
            traces_exp_height,
            synthetic_lines,
            test_conds,
            scan_speeds_hat=scan_speeds_hat,
            drives_nm=drives_nm,
            setpoints=setpoints,
            i_gains_exp=i_gains_exp,
            scanner_cfg=scanner_cfg,
            cfg=cfg,
            verbose=verbose,
        )

        oracle_comparison = compare_gp_to_oracle_test_fits(
            test_rows,
            oracle_test,
        )

    return {
        "train_conds": train_conds,
        "test_conds": test_conds,
        "informative_conds": informative_conds,
        "rejected_conditions": rejected_conditions,
        "usability_cfg": asdict(usability_cfg) if usability_cfg is not None else None,
        "train_local": train_local,
        "gp_pack": gp_pack,
        "test_rows": test_rows,
        "test_summary": test_summary,
        "oracle_test": oracle_test,
        "oracle_comparison": oracle_comparison,
        "scanner_cfg": asdict(scanner_cfg),
        "cfg": asdict(cfg),
    }


# =============================================================================
# Convenience prediction function for future conditions
# =============================================================================

def predict_PI_for_full_grid(
    gp_pack,
    traces_exp_height,
    *,
    scan_speeds_hat,
    drives_nm,
    setpoints,
    i_gains_exp,
):
    """
    Predict P/I over the full experimental grid.

    Returns
    -------
    P_grid, I_grid:
        shape = (n_speed, n_drive, n_setpoint, n_gain)
    pred_rows:
        flattened prediction rows with conditions.
    """
    conds = make_condition_list(traces_exp_height)

    pred_rows = predict_PI_with_gp(
        gp_pack,
        conds,
        scan_speeds_hat=scan_speeds_hat,
        drives_nm=drives_nm,
        setpoints=setpoints,
        i_gains_exp=i_gains_exp,
        return_std=True,
    )

    n_speed, n_drive, n_sp, n_gain, two, n_pix = np.asarray(traces_exp_height).shape

    P_grid = np.full((n_speed, n_drive, n_sp, n_gain), np.nan)
    I_grid = np.full_like(P_grid, np.nan)
    P_std_grid = np.full_like(P_grid, np.nan)
    I_std_grid = np.full_like(P_grid, np.nan)

    for r in pred_rows:
        si, di, spi, gi = r["cond"]
        P_grid[si, di, spi, gi] = r["P_pred"]
        I_grid[si, di, spi, gi] = r["I_pred"]
        P_std_grid[si, di, spi, gi] = r["log10_P_std"]
        I_std_grid[si, di, spi, gi] = r["log10_I_std"]

    return P_grid, I_grid, P_std_grid, I_std_grid, pred_rows
