"""
dt_static_dynamic_calibration_scaffold.py
========================================

Calibration scaffold for an SPM digital twin using:

1. Static controller calibration from height-channel statistical rewards.
2. Dynamic residual calibration using amplitude/phase response.
3. Quality/safety feature extraction for predictive modeling.

Assumed experimental array shapes
---------------------------------
traces_exp_height:
    shape = (n_speed, n_drive, n_setpoint, n_gain, 2, n_pix)
    channel 2 is [trace, retrace] height.

Optional traces_exp_amp, traces_exp_phase:
    same shape = (n_speed, n_drive, n_setpoint, n_gain, 2, n_pix)

Controls:
    scan_speeds_hat: shape (n_speed,)
    drives_nm:       shape (n_drive,)
    setpoints:       shape (n_setpoint,)
    i_gains_exp:     shape (n_gain,)

Scanner:
    your ScannerFD object with either:
        scanner.simulate_trace_retrace_substeps_fast(...)
    or:
        scanner.scan_line_trace_retrace_pi_drive(...)

Synthetic line generator:
    expects generate_synthetic_scan_line(...) from synthetic_scan_line_generator_v2.py
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple, Callable
import numpy as np

try:
    from scipy.optimize import differential_evolution, minimize
    from scipy.stats import wasserstein_distance
except Exception as exc:
    raise ImportError("This file requires scipy. Install with: pip install scipy") from exc


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
        # Allows the rest of the scaffold to run even if the classifier file is not
        # on the import path. Classification will be disabled unless passed directly.
        TraceUsabilityConfig = None
        classify_height_trace_pair = None
        classify_conditions = None
        split_informative_conditions = None
        summarize_classification_rows = None



# =============================================================================
# Robust utilities
# =============================================================================

def robust_mad(x, eps: float = 1e-12) -> float:
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return eps
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)) + eps)


def finite_flatten(x):
    x = np.asarray(x, dtype=float).ravel()
    return x[np.isfinite(x)]


def crop_to_common_length(*arrays):
    arrays = [np.asarray(a, dtype=float).ravel() for a in arrays]
    n = min(len(a) for a in arrays)
    return tuple(a[:n] for a in arrays)


def trim_edges(a, trim: int):
    a = np.asarray(a, dtype=float).ravel()
    trim = int(trim)
    if trim <= 0 or len(a) <= 2 * trim + 4:
        return a
    return a[trim:-trim]


def safe_rel_denom(a, b, floor_frac: float = 1e-6):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = np.abs(a) + np.abs(b)
    scale = np.nanmedian(np.abs(np.r_[a, b]))
    if not np.isfinite(scale) or scale <= 0:
        scale = robust_mad(np.r_[a, b])
    return np.maximum(denom, floor_frac * max(scale, 1e-12))


def wasserstein_scaled(a, b, eps: float = 1e-12):
    a = finite_flatten(a)
    b = finite_flatten(b)
    if a.size < 5 or b.size < 5:
        return np.inf
    scale = robust_mad(np.r_[a, b], eps=eps)
    return float(wasserstein_distance(a / scale, b / scale))


# =============================================================================
# Static height-channel metrics
# =============================================================================

def trace_retrace_rel_mismatch(h_tr, h_rt, trim: int = 0, floor_frac: float = 1e-6):
    h_tr, h_rt = crop_to_common_length(h_tr, h_rt)
    h_tr = trim_edges(h_tr, trim)
    h_rt = trim_edges(h_rt, trim)
    h_tr, h_rt = crop_to_common_length(h_tr, h_rt)

    mask = np.isfinite(h_tr) & np.isfinite(h_rt)
    if np.sum(mask) < 5:
        return np.inf

    h_tr = h_tr[mask]
    h_rt = h_rt[mask]

    denom = safe_rel_denom(h_tr, h_rt, floor_frac=floor_frac)
    return float(np.nanmean(np.abs(h_tr - h_rt) / denom))


def gradient_signature(h_tr, h_rt, trim: int = 0, floor_frac: float = 1e-6):
    """Relative gradient mean/std using an N-1 midpoint denominator."""
    h_tr, h_rt = crop_to_common_length(h_tr, h_rt)
    h_tr = trim_edges(h_tr, trim)
    h_rt = trim_edges(h_rt, trim)
    h_tr, h_rt = crop_to_common_length(h_tr, h_rt)

    mask = np.isfinite(h_tr) & np.isfinite(h_rt)
    if np.sum(mask) < 6:
        return {"grad_mean": np.inf, "grad_std": np.inf, "grad_p95": np.inf, "grad_max": np.inf}

    h_tr = h_tr[mask]
    h_rt = h_rt[mask]

    dtr = np.diff(h_tr)
    drt = np.diff(h_rt)

    denom = 0.5 * (
        np.abs(h_tr[:-1]) + np.abs(h_tr[1:])
        + np.abs(h_rt[:-1]) + np.abs(h_rt[1:])
    )

    scale = np.nanmedian(np.abs(np.r_[h_tr, h_rt]))
    if not np.isfinite(scale) or scale <= 0:
        scale = robust_mad(np.r_[h_tr, h_rt])

    denom = np.maximum(denom, floor_frac * max(scale, 1e-12))

    g = (np.abs(dtr) + np.abs(drt)) / denom
    g = g[np.isfinite(g)]

    if g.size < 5:
        return {"grad_mean": np.inf, "grad_std": np.inf, "grad_p95": np.inf, "grad_max": np.inf}

    return {
        "grad_mean": float(np.nanmean(g)),
        "grad_std": float(np.nanstd(g)),
        "grad_p95": float(np.nanpercentile(g, 95)),
        "grad_max": float(np.nanmax(g)),
    }


def height_distribution_signature(h_tr, h_rt, trim: int = 0):
    h_tr, h_rt = crop_to_common_length(h_tr, h_rt)
    h_tr = trim_edges(h_tr, trim)
    h_rt = trim_edges(h_rt, trim)
    h = finite_flatten(np.r_[h_tr, h_rt])

    if h.size < 5:
        return {"height_mad": np.inf, "height_range_p99_p01": np.inf, "height_std": np.inf}

    return {
        "height_mad": robust_mad(h),
        "height_range_p99_p01": float(np.nanpercentile(h, 99) - np.nanpercentile(h, 1)),
        "height_std": float(np.nanstd(h)),
    }


def compute_height_static_signature(h_tr, h_rt, trim: int = 10):
    sig = {}
    sig["trrt"] = trace_retrace_rel_mismatch(h_tr, h_rt, trim=trim)
    sig.update(gradient_signature(h_tr, h_rt, trim=trim))
    sig.update(height_distribution_signature(h_tr, h_rt, trim=trim))
    return sig


def symmetric_metric_loss(sim_value, exp_value, floor: float = 1e-6):
    """
    Symmetric normalized difference.

    This prevents near-flat experimental traces from producing huge losses:
        |sim-exp| / (|exp| + eps) -> 1e12

    Instead:
        |sim-exp| / (|sim| + |exp| + floor)
    """
    a = float(sim_value)
    b = float(exp_value)
    if not np.isfinite(a) or not np.isfinite(b):
        return np.inf
    return float(abs(a - b) / (abs(a) + abs(b) + float(floor)))


def compare_static_signatures(sim_sig: Dict[str, float], exp_sig: Dict[str, float], *, weights=None, metric_floor: float = 1e-6, flat_penalty: bool = True):
    if weights is None:
        weights = {
            "trrt": 2.0,
            "grad_mean": 2.0,
            "grad_std": 1.0,
            "grad_p95": 0.5,
            "height_mad": 0.5,
            "height_range_p99_p01": 0.2,
        }

    loss_terms = {}
    loss = 0.0

    for k, w in weights.items():
        if k not in sim_sig or k not in exp_sig:
            continue
        a = float(sim_sig[k])
        b = float(exp_sig[k])
        term = symmetric_metric_loss(a, b, floor=metric_floor)
        loss_terms[k] = float(term)
        loss += float(w) * term

    # Small guard against a degenerate flat simulated trace when the experiment
    # has nonzero height response. The main flat-trace handling should happen
    # by excluding flat experimental traces from static calibration.
    if flat_penalty:
        exp_mad = float(exp_sig.get("height_mad", np.nan))
        sim_mad = float(sim_sig.get("height_mad", np.nan))
        if np.isfinite(exp_mad) and np.isfinite(sim_mad) and exp_mad > metric_floor:
            ratio = sim_mad / max(exp_mad, metric_floor)
            if ratio < 0.02:
                p = 5.0 * (0.02 - ratio) ** 2
                loss += p
                loss_terms["flat_sim_mad_penalty"] = float(p)

    if not np.isfinite(loss):
        loss = np.inf

    return float(loss), loss_terms


# =============================================================================
# Scanner adapter
# =============================================================================

@dataclass
class ScannerRunConfig:
    dx_hat: float = 1.0
    n_substeps: int = 50
    dt_inner_max: Optional[float] = None

    tau_A: Optional[float] = None
    tau_phi: Optional[float] = None
    tau_z: Optional[float] = None

    z_rate_limit_hat: Optional[float] = 1e6
    d_init_hat: float = 0.0
    A_meas_init_hat: Optional[float] = 1.0
    phi_meas_init_deg: float = 120.0
    T_I: Optional[float] = 3e-1
    integ_clip: Optional[float] = None

    antiwindup: bool = True
    contact_A_frac: float = 0.02
    saturation_A_frac: float = 0.98
    record_mode: str = "last"
    carry_state_to_retrace: bool = True

    h_smooth_sigma_px: float = 0.0
    fd_n_d: int = 4096
    use_fast: bool = True


def _filter_order_from_tau(tau):
    return 1 if tau is not None and np.isfinite(float(tau)) and float(tau) > 0 else None


def prepare_fd_table(scanner, drive_nm, fd_n_d: int = 4096):
    if hasattr(scanner, "prepare_fd_table_for_drive"):
        return scanner.prepare_fd_table_for_drive(drive_nm=drive_nm, n_d=fd_n_d)
    return None


def run_scanner_line(scanner, h_line, *, drive_nm, setpoint, scan_speed_hat, P, I, cfg: ScannerRunConfig, fd_table=None):
    h_line = np.asarray(h_line, dtype=float).ravel()

    A_filter_order = _filter_order_from_tau(cfg.tau_A)
    phi_filter_order = _filter_order_from_tau(cfg.tau_phi)
    z_filter_order = _filter_order_from_tau(cfg.tau_z)

    if fd_table is None:
        fd_table = prepare_fd_table(scanner, drive_nm, cfg.fd_n_d)

    if cfg.use_fast and hasattr(scanner, "simulate_trace_retrace_substeps_fast"):
        return scanner.simulate_trace_retrace_substeps_fast(
            h_line,
            drive_nm=drive_nm,
            setpoint=setpoint,
            scan_speed_hat=scan_speed_hat,
            dx_hat=cfg.dx_hat,
            P=P,
            I=I,
            A_filter_order=A_filter_order,
            tau_A=cfg.tau_A,
            phi_filter_order=phi_filter_order,
            tau_phi=cfg.tau_phi,
            z_filter_order=z_filter_order,
            tau_z=cfg.tau_z,
            z_rate_limit_hat=cfg.z_rate_limit_hat,
            d_init_hat=cfg.d_init_hat,
            A_meas_init_hat=cfg.A_meas_init_hat,
            phi_meas_init_deg=cfg.phi_meas_init_deg,
            T_I=cfg.T_I,
            integ_clip=cfg.integ_clip,
            n_substeps=cfg.n_substeps,
            dt_inner_max=cfg.dt_inner_max,
            antiwindup=cfg.antiwindup,
            contact_A_frac=cfg.contact_A_frac,
            saturation_A_frac=cfg.saturation_A_frac,
            record_mode=cfg.record_mode,
            carry_state_to_retrace=cfg.carry_state_to_retrace,
            fd_table=fd_table,
            fd_n_d=cfg.fd_n_d,
            h_smooth_sigma_px=cfg.h_smooth_sigma_px,
        )

    return scanner.scan_line_trace_retrace_pi_drive(
        h_hat=h_line,
        drive_nm=drive_nm,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=cfg.dx_hat,
        P=P,
        I=I,
        A_filter_order=A_filter_order,
        tau_A=cfg.tau_A,
        phi_filter_order=phi_filter_order,
        tau_phi=cfg.tau_phi,
        z_filter_order=z_filter_order,
        tau_z=cfg.tau_z,
        z_rate_limit_hat=cfg.z_rate_limit_hat,
        d_init_hat=cfg.d_init_hat,
        A_meas_init_hat=cfg.A_meas_init_hat,
        phi_meas_init_deg=cfg.phi_meas_init_deg,
        T_I=cfg.T_I,
        integ_clip=cfg.integ_clip,
        use_substeps=True,
        n_substeps=cfg.n_substeps,
        dt_inner_max=cfg.dt_inner_max,
    )


def get_height_from_out(out):
    tr = np.asarray(out["trace"]["d_hat"], dtype=float).ravel()
    rt = np.asarray(out["retrace"]["d_hat"], dtype=float).ravel()
    return tr, rt


def get_amp_phase_from_out(out):
    tr = out["trace"]
    rt = out["retrace"]

    def get(d, keys):
        for k in keys:
            if k in d:
                return np.asarray(d[k], dtype=float).ravel()
        return None

    A_tr = get(tr, ["A_hat", "A_meas", "A_true_hat", "A_true"])
    A_rt = get(rt, ["A_hat", "A_meas", "A_true_hat", "A_true"])
    p_tr = get(tr, ["phi_deg", "phi_meas", "phi_true_deg", "phi_true"])
    p_rt = get(rt, ["phi_deg", "phi_meas", "phi_true_deg", "phi_true"])
    return A_tr, A_rt, p_tr, p_rt


# =============================================================================
# Synthetic line generation wrapper
# =============================================================================

def make_synthetic_lines_from_map(
    h_map,
    *,
    generate_synthetic_scan_line: Callable,
    n_lines: int = 8,
    n_pixels: int = 256,
    dx_hat: float = 1.0,
    scan_speed_hat_for_generation: float = 1.0,
    mode: str = "filtered_iid",
    direction: str = "x",
    corr_sigma_px: float = 1.0,
    preserve_max_abs_dh: bool = True,
    max_abs_dh: Optional[float] = None,
    max_abs_rate: Optional[float] = None,
    slope_limit_mode: str = "rescale",
    seed0: int = 0,
):
    lines = []
    packs = []

    for q in range(int(n_lines)):
        pack = generate_synthetic_scan_line(
            h_map,
            n_pixels=n_pixels,
            dx_hat=dx_hat,
            scan_speed_hat=scan_speed_hat_for_generation,
            mode=mode,
            direction=direction,
            corr_sigma_px=corr_sigma_px,
            preserve_max_abs_dh=preserve_max_abs_dh,
            max_abs_dh=max_abs_dh,
            max_abs_rate=max_abs_rate,
            slope_limit_mode=slope_limit_mode,
            random_state=seed0 + q,
        )
        lines.append(np.asarray(pack["generated"]["h_hat"], dtype=float).ravel())
        packs.append(pack)

    return lines, packs


# =============================================================================
# Static calibration over experimental grid
# =============================================================================

@dataclass
class StaticCalibrationConfig:
    # P_sim = p_scale * I_exp + p_offset; I_sim = i_scale * I_exp + i_offset.
    # Scales are optimized in log10-space. Offsets are optional linear params.
    use_P_offset: bool = False
    use_I_offset: bool = False

    trim: int = 10
    n_lines: int = 8

    w_trrt: float = 2.0
    w_grad_mean: float = 2.0
    w_grad_std: float = 1.0
    w_grad_p95: float = 0.5
    w_height_mad: float = 0.5
    w_height_range: float = 0.2

    speed_indices: Optional[np.ndarray] = None
    drive_indices: Optional[np.ndarray] = None
    setpoint_indices: Optional[np.ndarray] = None
    gain_indices: Optional[np.ndarray] = None

    bounds_log: Tuple[Tuple[float, float], ...] = ((-3.0, 3.0), (-3.0, 3.0))
    maxiter: int = 80
    popsize: int = 8
    seed: int = 0


def unpack_static_params(x, cfg: StaticCalibrationConfig):
    x = np.asarray(x, dtype=float).ravel()
    p_scale = 10.0 ** x[0]
    i_scale = 10.0 ** x[1]

    idx = 2
    if cfg.use_P_offset:
        p_offset = x[idx]
        idx += 1
    else:
        p_offset = 0.0

    if cfg.use_I_offset:
        i_offset = x[idx]
        idx += 1
    else:
        i_offset = 0.0

    return {"p_scale": float(p_scale), "i_scale": float(i_scale), "p_offset": float(p_offset), "i_offset": float(i_offset)}


def map_exp_gain_to_sim_PI(i_gain_exp, pars):
    i_gain_exp = float(i_gain_exp)
    P = pars["p_scale"] * i_gain_exp + pars["p_offset"]
    I = pars["i_scale"] * i_gain_exp + pars["i_offset"]
    return max(float(P), 0.0), max(float(I), 0.0)


def _indices_or_all(indices, n):
    if indices is None:
        return np.arange(n, dtype=int)
    return np.asarray(indices, dtype=int)


def build_static_metric_weights(cfg: StaticCalibrationConfig):
    return {
        "trrt": cfg.w_trrt,
        "grad_mean": cfg.w_grad_mean,
        "grad_std": cfg.w_grad_std,
        "grad_p95": cfg.w_grad_p95,
        "height_mad": cfg.w_height_mad,
        "height_range_p99_p01": cfg.w_height_range,
    }


def make_static_calibration_objective(scanner, traces_exp_height, synthetic_lines, scan_speeds_hat, drives_nm, setpoints, i_gains_exp, *, scanner_cfg: ScannerRunConfig, calib_cfg: StaticCalibrationConfig):
    """
    Build objective for static DT controller calibration.

    For each experimental condition, it simulates all synthetic lines and averages
    the height signatures, then compares to the experimental height signature.
    """
    traces_exp_height = np.asarray(traces_exp_height, dtype=float)
    n_speed, n_drive, n_sp, n_gain, two, n_pix = traces_exp_height.shape
    assert two == 2

    speed_ids = _indices_or_all(calib_cfg.speed_indices, n_speed)
    drive_ids = _indices_or_all(calib_cfg.drive_indices, n_drive)
    sp_ids = _indices_or_all(calib_cfg.setpoint_indices, n_sp)
    gain_ids = _indices_or_all(calib_cfg.gain_indices, n_gain)
    metric_weights = build_static_metric_weights(calib_cfg)

    exp_sigs = {}
    for si in speed_ids:
        for di in drive_ids:
            for spi in sp_ids:
                for gi in gain_ids:
                    h_tr = traces_exp_height[si, di, spi, gi, 0]
                    h_rt = traces_exp_height[si, di, spi, gi, 1]
                    exp_sigs[(int(si), int(di), int(spi), int(gi))] = compute_height_static_signature(h_tr, h_rt, trim=calib_cfg.trim)

    fd_tables = {int(di): prepare_fd_table(scanner, float(drives_nm[di]), scanner_cfg.fd_n_d) for di in drive_ids}

    def objective(x, return_full=False):
        pars = unpack_static_params(x, calib_cfg)
        total_loss = 0.0
        count = 0
        details = []

        try:
            for si in speed_ids:
                speed = float(scan_speeds_hat[si])
                for di in drive_ids:
                    drive = float(drives_nm[di])
                    fd_table = fd_tables[int(di)]
                    for spi in sp_ids:
                        sp = float(setpoints[spi])
                        for gi in gain_ids:
                            I_exp = float(i_gains_exp[gi])
                            P_sim, I_sim = map_exp_gain_to_sim_PI(I_exp, pars)

                            sig_list = []
                            for h_line in synthetic_lines[:calib_cfg.n_lines]:
                                out = run_scanner_line(scanner, h_line, drive_nm=drive, setpoint=sp, scan_speed_hat=speed, P=P_sim, I=I_sim, cfg=scanner_cfg, fd_table=fd_table)
                                sim_tr, sim_rt = get_height_from_out(out)
                                sig_list.append(compute_height_static_signature(sim_tr, sim_rt, trim=calib_cfg.trim))

                            sim_sig = {}
                            for k in sig_list[0].keys():
                                vals = [s[k] for s in sig_list if np.isfinite(s[k])]
                                sim_sig[k] = float(np.mean(vals)) if vals else np.inf

                            exp_sig = exp_sigs[(int(si), int(di), int(spi), int(gi))]
                            loss, terms = compare_static_signatures(sim_sig, exp_sig, weights=metric_weights)

                            if np.isfinite(loss):
                                total_loss += loss
                                count += 1

                            if return_full:
                                details.append({
                                    "indices": (int(si), int(di), int(spi), int(gi)),
                                    "controls": {"scan_speed_hat": speed, "drive_nm": drive, "setpoint": sp, "I_exp": I_exp, "P_sim": P_sim, "I_sim": I_sim},
                                    "loss": float(loss),
                                    "terms": terms,
                                    "sim_sig": sim_sig,
                                    "exp_sig": exp_sig,
                                })

            mean_loss = total_loss / max(count, 1)
            if return_full:
                return float(mean_loss), {"pars": pars, "count": int(count), "details": details}
            return float(mean_loss)

        except Exception as exc:
            if return_full:
                return np.inf, {"error": str(exc), "pars": pars}
            return np.inf

    return objective


def fit_static_controller_calibration(scanner, traces_exp_height, synthetic_lines, scan_speeds_hat, drives_nm, setpoints, i_gains_exp, *, scanner_cfg: ScannerRunConfig, calib_cfg: StaticCalibrationConfig):
    objective = make_static_calibration_objective(scanner, traces_exp_height, synthetic_lines, scan_speeds_hat, drives_nm, setpoints, i_gains_exp, scanner_cfg=scanner_cfg, calib_cfg=calib_cfg)

    res_global = differential_evolution(objective, bounds=list(calib_cfg.bounds_log), seed=calib_cfg.seed, maxiter=calib_cfg.maxiter, popsize=calib_cfg.popsize, polish=False, updating="immediate", workers=1)

    res_local = minimize(objective, res_global.x, method="Nelder-Mead", options={"maxiter": 200, "xatol": 1e-3, "fatol": 1e-4})

    candidates = [("global", res_global.x, res_global.fun), ("local", res_local.x, res_local.fun)]
    best_source, best_x, best_fun = min(candidates, key=lambda t: t[2])
    best_loss, best_details = objective(best_x, return_full=True)

    return {
        "best_x": best_x,
        "best_loss": best_loss,
        "best_source": best_source,
        "best_pars": unpack_static_params(best_x, calib_cfg),
        "best_details": best_details,
        "res_global": res_global,
        "res_local": res_local,
        "objective": objective,
        "scanner_cfg": asdict(scanner_cfg),
        "calib_cfg": asdict(calib_cfg),
    }


# =============================================================================
# Dynamic residual / predictive feature extraction
# =============================================================================

def channel_signature(A_tr=None, A_rt=None, p_tr=None, p_rt=None, trim: int = 10):
    """Extract amplitude/phase signatures. Works when some channels are missing."""
    out = {}

    if A_tr is not None and A_rt is not None:
        A_tr, A_rt = crop_to_common_length(A_tr, A_rt)
        A_tr = trim_edges(A_tr, trim)
        A_rt = trim_edges(A_rt, trim)
        A = finite_flatten(np.r_[A_tr, A_rt])
        if A.size >= 5:
            out["A_mean"] = float(np.nanmean(A))
            out["A_std"] = float(np.nanstd(A))
            out["A_mad"] = robust_mad(A)
            out["A_p05"] = float(np.nanpercentile(A, 5))
            out["A_p95"] = float(np.nanpercentile(A, 95))
            out["A_trrt_wdist"] = wasserstein_scaled(A_tr, A_rt)
            out["A_trrt_rel"] = trace_retrace_rel_mismatch(A_tr, A_rt, trim=0)
            A0_est = max(float(np.nanpercentile(A, 95)), 1e-12)
            out["A_collapse_frac_10pct"] = float(np.nanmean(A < 0.10 * A0_est))

    if p_tr is not None and p_rt is not None:
        p_tr, p_rt = crop_to_common_length(p_tr, p_rt)
        p_tr = trim_edges(p_tr, trim)
        p_rt = trim_edges(p_rt, trim)
        p = finite_flatten(np.r_[p_tr, p_rt])
        if p.size >= 5:
            out["phi_mean"] = float(np.nanmean(p))
            out["phi_std"] = float(np.nanstd(p))
            out["phi_mad"] = robust_mad(p)
            out["phi_p05"] = float(np.nanpercentile(p, 5))
            out["phi_p95"] = float(np.nanpercentile(p, 95))
            out["phi_trrt_wdist"] = wasserstein_scaled(p_tr, p_rt)
            out["phi_trrt_rel"] = trace_retrace_rel_mismatch(p_tr, p_rt, trim=0)
            out["phi_spike_count_10deg"] = int(np.sum(np.abs(np.diff(p)) > 10.0))

    return out


def compute_quality_safety_labels_from_height_amp_phase(h_tr, h_rt, A_tr=None, A_rt=None, p_tr=None, p_rt=None, *, trim: int = 10, A_collapse_frac_threshold: float = 0.10, phase_spike_threshold: int = 20, trrt_threshold: float = 0.05, usability_cfg=None):
    """Heuristic labels for training a predictive quality/safety model.

    Flat/no-response traces are kept here. They are usually low quality or
    uninformative, but not necessarily unsafe. Amplitude/phase features decide
    whether they are safe or unsafe.
    """
    hsig = compute_height_static_signature(h_tr, h_rt, trim=trim)
    csig = channel_signature(A_tr, A_rt, p_tr, p_rt, trim=trim)

    if classify_height_trace_pair is not None:
        if usability_cfg is None and TraceUsabilityConfig is not None:
            usability_cfg = TraceUsabilityConfig(trim=trim)
        usability = classify_height_trace_pair(h_tr, h_rt, cfg=usability_cfg)
    else:
        usability = {
            "use_for_static_calibration": True,
            "class": "unknown",
            "reason": "classifier_unavailable",
        }

    trrt = hsig.get("trrt", np.inf)
    A_collapse = csig.get("A_collapse_frac_10pct", 0.0)
    phase_spikes = csig.get("phi_spike_count_10deg", 0)

    # Quality is a continuous label. Flat traces are penalized as low-quality
    # because they contain little topographic information, but they may remain safe.
    flat_penalty = 1.0 if usability.get("class") == "flat_or_uninformative" else 0.0
    invalid_penalty = 5.0 if usability.get("class") == "invalid" else 0.0

    quality = -(
        2.0 * trrt
        + 1.0 * hsig.get("grad_std", 0.0)
        + 0.5 * csig.get("A_trrt_rel", 0.0)
        + 0.5 * csig.get("phi_trrt_rel", 0.0)
        + flat_penalty
        + invalid_penalty
    )

    # Safe means the scan is not obviously unstable/damaging. A flat trace at a
    # too-large setpoint can be safe but low quality.
    safe = (
        usability.get("class") != "invalid"
        and np.isfinite(trrt)
        and trrt < trrt_threshold
        and A_collapse < A_collapse_frac_threshold
        and phase_spikes < phase_spike_threshold
    )

    return {
        "quality": float(quality),
        "safe": bool(safe),
        "height_sig": hsig,
        "channel_sig": csig,
        "usability": usability,
    }


def build_dynamic_residual_dataset(scanner, traces_exp_height, traces_exp_amp, traces_exp_phase, synthetic_lines, scan_speeds_hat, drives_nm, setpoints, i_gains_exp, *, static_pars: Optional[Dict[str, float]] = None, controller_grid=None, controller_mapper=None, scanner_cfg: ScannerRunConfig, trim: int = 10, n_lines: int = 8, usability_cfg=None, keep_uninformative: bool = True):
    """
    Build a tabular dataset for dynamic residual / quality-safety modeling.

    Each row is one experimental condition. Simulated signatures are averaged
    over synthetic lines. Targets are experimental signatures and residuals.
    """
    traces_exp_height = np.asarray(traces_exp_height, dtype=float)
    if traces_exp_amp is not None:
        traces_exp_amp = np.asarray(traces_exp_amp, dtype=float)
    if traces_exp_phase is not None:
        traces_exp_phase = np.asarray(traces_exp_phase, dtype=float)

    n_speed, n_drive, n_sp, n_gain, two, n_pix = traces_exp_height.shape
    assert two == 2

    rows = []
    fd_tables = {di: prepare_fd_table(scanner, float(drives_nm[di]), scanner_cfg.fd_n_d) for di in range(n_drive)}

    for si in range(n_speed):
        speed = float(scan_speeds_hat[si])
        for di in range(n_drive):
            drive = float(drives_nm[di])
            fd_table = fd_tables[di]
            for spi in range(n_sp):
                sp = float(setpoints[spi])
                for gi in range(n_gain):
                    I_exp = float(i_gains_exp[gi])

                    # Controller mapping can come from:
                    #   1. controller_grid=(P_grid, I_grid), e.g. GP prediction over full grid
                    #   2. controller_mapper callable
                    #   3. static_pars linear fallback from old calibration
                    if controller_grid is not None:
                        P_grid, I_grid = controller_grid
                        P_sim = float(P_grid[si, di, spi, gi])
                        I_sim = float(I_grid[si, di, spi, gi])
                    elif controller_mapper is not None:
                        P_sim, I_sim = controller_mapper(
                            si, di, spi, gi, speed, drive, sp, I_exp
                        )
                        P_sim = float(P_sim)
                        I_sim = float(I_sim)
                    elif static_pars is not None:
                        P_sim, I_sim = map_exp_gain_to_sim_PI(I_exp, static_pars)
                    else:
                        raise ValueError(
                            "Provide one of static_pars, controller_grid=(P_grid, I_grid), "
                            "or controller_mapper."
                        )

                    eh_tr = traces_exp_height[si, di, spi, gi, 0]
                    eh_rt = traces_exp_height[si, di, spi, gi, 1]

                    if traces_exp_amp is not None:
                        eA_tr = traces_exp_amp[si, di, spi, gi, 0]
                        eA_rt = traces_exp_amp[si, di, spi, gi, 1]
                    else:
                        eA_tr = eA_rt = None

                    if traces_exp_phase is not None:
                        ep_tr = traces_exp_phase[si, di, spi, gi, 0]
                        ep_rt = traces_exp_phase[si, di, spi, gi, 1]
                    else:
                        ep_tr = ep_rt = None

                    exp_labels = compute_quality_safety_labels_from_height_amp_phase(eh_tr, eh_rt, eA_tr, eA_rt, ep_tr, ep_rt, trim=trim, usability_cfg=usability_cfg)
                    usability = exp_labels.get("usability", {})

                    # Dynamic dataset keeps flat/uninformative traces by default so
                    # the quality/safety model can learn to reject them. Set
                    # keep_uninformative=False to mimic static calibration behavior.
                    if (not keep_uninformative) and (not usability.get("use_for_static_calibration", True)):
                        continue
                    exp_hsig = exp_labels["height_sig"]
                    exp_csig = exp_labels["channel_sig"]

                    sim_hsigs = []
                    sim_csigs = []
                    for h_line in synthetic_lines[:n_lines]:
                        out = run_scanner_line(scanner, h_line, drive_nm=drive, setpoint=sp, scan_speed_hat=speed, P=P_sim, I=I_sim, cfg=scanner_cfg, fd_table=fd_table)
                        sh_tr, sh_rt = get_height_from_out(out)
                        sA_tr, sA_rt, sp_tr, sp_rt = get_amp_phase_from_out(out)
                        sim_hsigs.append(compute_height_static_signature(sh_tr, sh_rt, trim=trim))
                        sim_csigs.append(channel_signature(sA_tr, sA_rt, sp_tr, sp_rt, trim=trim))

                    sim_hsig = {}
                    for k in sim_hsigs[0].keys():
                        vals = [s[k] for s in sim_hsigs if k in s and np.isfinite(s[k])]
                        sim_hsig[k] = float(np.mean(vals)) if vals else np.nan

                    sim_csig = {}
                    all_keys = sorted(set().union(*[s.keys() for s in sim_csigs])) if sim_csigs else []
                    for k in all_keys:
                        vals = [s[k] for s in sim_csigs if k in s and np.isfinite(s[k])]
                        sim_csig[k] = float(np.mean(vals)) if vals else np.nan

                    row = {
                        "scan_speed_hat": speed,
                        "drive_nm": drive,
                        "setpoint": sp,
                        "I_exp": I_exp,
                        "P_sim": P_sim,
                        "I_sim": I_sim,
                        "quality": exp_labels["quality"],
                        "safe": int(exp_labels["safe"]),
                        "use_for_static_calibration": int(usability.get("use_for_static_calibration", 1)),
                        "trace_class": usability.get("class", "unknown"),
                        "trace_reject_reason": usability.get("reason", "none"),
                        "classifier_height_mad": usability.get("height_mad", np.nan),
                        "classifier_height_range_p99_p01": usability.get("height_range_p99_p01", np.nan),
                        "classifier_grad_mad": usability.get("grad_mad", np.nan),
                        "classifier_nonzero_frac": usability.get("nonzero_frac", np.nan),
                    }

                    for k, v in exp_hsig.items():
                        row[f"exp_h_{k}"] = v
                    for k, v in sim_hsig.items():
                        row[f"sim_h_{k}"] = v
                        if k in exp_hsig:
                            row[f"res_h_{k}"] = exp_hsig[k] - v

                    for k, v in exp_csig.items():
                        row[f"exp_{k}"] = v
                    for k, v in sim_csig.items():
                        row[f"sim_{k}"] = v
                        if k in exp_csig:
                            row[f"res_{k}"] = exp_csig[k] - v

                    rows.append(row)

    return rows


def rows_to_numpy_table(rows: List[Dict[str, Any]], feature_keys=None, target_keys=None):
    if len(rows) == 0:
        raise ValueError("No rows provided.")

    if feature_keys is None:
        default = [
            "scan_speed_hat", "drive_nm", "setpoint", "I_exp", "P_sim", "I_sim",
            "sim_h_trrt", "sim_h_grad_mean", "sim_h_grad_std",
            "sim_A_mean", "sim_A_std", "sim_A_trrt_rel",
            "sim_phi_mean", "sim_phi_std", "sim_phi_trrt_rel",
        ]
        feature_keys = [k for k in default if k in rows[0]]

    if target_keys is None:
        target_keys = ["quality", "safe"] + [k for k in rows[0].keys() if k.startswith("res_")]

    X = np.array([[float(r.get(k, np.nan)) for k in feature_keys] for r in rows], dtype=float)
    Y = np.array([[float(r.get(k, np.nan)) for k in target_keys] for r in rows], dtype=float)
    return X, Y, feature_keys, target_keys


def fit_quality_safety_models_from_rows(rows, feature_keys=None):
    """
    Train simple sklearn models:
        - RandomForestRegressor for quality
        - RandomForestClassifier for safety

    Replace with GP/DKL/ensemble later if needed.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        raise ImportError("Install scikit-learn to use this helper.") from exc

    X, Y, feature_keys, target_keys = rows_to_numpy_table(rows, feature_keys=feature_keys, target_keys=["quality", "safe"])
    q = Y[:, 0]
    s = Y[:, 1].astype(int)

    mask = np.isfinite(q) & np.isfinite(s)
    X = X[mask]
    q = q[mask]
    s = s[mask]

    quality_model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        RandomForestRegressor(n_estimators=300, random_state=0, min_samples_leaf=3),
    )

    safety_model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        RandomForestClassifier(n_estimators=300, random_state=0, class_weight="balanced", min_samples_leaf=3),
    )

    quality_model.fit(X, q)
    safety_model.fit(X, s)

    return {"quality_model": quality_model, "safety_model": safety_model, "feature_keys": feature_keys}


def predict_candidate_quality_safety(model_pack, candidate_rows: List[Dict[str, Any]]):
    X = np.array([[float(r.get(k, np.nan)) for k in model_pack["feature_keys"]] for r in candidate_rows], dtype=float)
    q_pred = model_pack["quality_model"].predict(X)

    if hasattr(model_pack["safety_model"], "predict_proba"):
        p_safe = model_pack["safety_model"].predict_proba(X)[:, 1]
    else:
        p_safe = model_pack["safety_model"].predict(X).astype(float)

    out = []
    for r, q, p in zip(candidate_rows, q_pred, p_safe):
        rr = dict(r)
        rr["quality_pred"] = float(q)
        rr["p_safe"] = float(p)
        rr["acquisition"] = float(q + 0.5 * p)
        out.append(rr)

    out.sort(key=lambda z: z["acquisition"], reverse=True)
    return out
