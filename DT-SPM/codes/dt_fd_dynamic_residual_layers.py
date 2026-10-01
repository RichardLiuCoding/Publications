"""
dt_fd_dynamic_residual_layers.py
================================

Static + dynamic residual calibration layers for an SPM digital twin.

Implements:
    1. Static FD residuals:
           delta_A0(drive, d)
           delta_phi0(drive, d)

    2. Dynamic residuals:
           delta_d_dyn, delta_A_dyn, delta_phi_dyn
       from DT state/history.

The controller calibration is assumed frozen. This module does not re-fit drive,
setpoint, scan speed, P, or I. It only calibrates how the FD-derived DT channels
map to measured amplitude/phase/height during real scanning.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Sequence, Tuple, Callable, Union
import numpy as np

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    from codes.dt_static_dynamic_calibration_scaffold_v3 import run_scanner_line, prepare_fd_table
except Exception:
    try:
        from dt_static_dynamic_calibration_scaffold_v3 import run_scanner_line, prepare_fd_table
    except Exception:  # pragma: no cover
        run_scanner_line = None
        prepare_fd_table = None


# =============================================================================
# Configs
# =============================================================================

@dataclass
class ResidualDatasetConfig:
    """
    Configuration for building per-pixel residual data.

    pairing:
        "pixel"         : direct pixel pairing. Use only if the DT line is aligned
                          with the measured line.
        "quantile_by_A" : sort DT samples by A_FD and experimental samples by
                          A_exp, then pair quantiles. Recommended when DT uses
                          synthetic roughness lines.
        "quantile_by_h" : pair by height quantiles.
    """
    pairing: str = "quantile_by_A"
    max_points_per_direction: int = 128
    n_synthetic_lines_per_condition: int = 1
    random_state: int = 0
    phase_period_deg: float = 360.0
    stable_only: bool = True
    min_A_frac_of_A95: float = 0.03
    max_abs_phi_jump_deg: Optional[float] = None
    include_retrace: bool = True
    trim_edges: int = 5


@dataclass
class StaticFDResidualConfig:
    """Static layer: [drive_nm, d_dt] -> [delta_A0, delta_phi0]."""
    feature_cols: Tuple[str, ...] = ("drive_nm", "d_dt")
    target_cols: Tuple[str, ...] = ("delta_A_raw", "delta_phi_raw")
    model_type: str = "histgb"  # "histgb", "extratrees", or "randomforest"
    random_state: int = 0
    max_iter: int = 300
    learning_rate: float = 0.05
    max_leaf_nodes: int = 31
    min_samples_leaf: int = 20
    n_estimators: int = 300
    max_depth: Optional[int] = None
    max_train_points: Optional[int] = 50000


@dataclass
class DynamicResidualConfig:
    """
    Dynamic layer:
        controls + DT state + one-step history ->
        [delta_d_dyn, delta_A_dyn, delta_phi_dyn]
    """
    feature_cols: Tuple[str, ...] = (
        "log_scan_speed", "drive_nm", "setpoint", "log_I_exp",
        "log_P_sim", "log_I_sim", "direction_sign", "x_norm",
        "d_dt", "A_fd", "phi_fd", "h_dt", "z_dt",
        "dd_dt", "dA_fd", "dphi_fd", "dh_dt", "dz_dt",
        "A_static", "phi_static",
    )
    target_cols: Tuple[str, ...] = (
        "delta_d_dyn_target", "delta_A_dyn_target", "delta_phi_dyn_target",
    )
    model_type: str = "histgb"  # "histgb", "extratrees", or "randomforest"
    random_state: int = 0
    max_iter: int = 400
    learning_rate: float = 0.04
    max_leaf_nodes: int = 31
    min_samples_leaf: int = 30
    n_estimators: int = 400
    max_depth: Optional[int] = None
    max_train_points: Optional[int] = 100000


# =============================================================================
# Basic utilities
# =============================================================================

def robust_mad(x, eps: float = 1e-12) -> float:
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return eps
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)) + eps)


def wrap_phase_diff_deg(diff, period: float = 360.0):
    diff = np.asarray(diff, dtype=float)
    return (diff + 0.5 * period) % period - 0.5 * period


def _trim(x, trim: int):
    x = np.asarray(x, dtype=float).ravel()
    trim = int(trim)
    if trim <= 0 or x.size <= 2 * trim + 4:
        return x
    return x[trim:-trim]


def _finite_mask(*arrays):
    m = np.ones_like(np.asarray(arrays[0], dtype=float), dtype=bool)
    for a in arrays:
        m &= np.isfinite(np.asarray(a, dtype=float))
    return m


def _subsample_indices(n: int, max_points: Optional[int], rng):
    n = int(n)
    if max_points is None or n <= int(max_points):
        return np.arange(n, dtype=int)
    return np.sort(rng.choice(n, size=int(max_points), replace=False))


def _as_dataframe(rows):
    return pd.DataFrame(rows) if pd is not None else rows


def _require_pandas(df):
    if pd is None:
        raise ImportError("This function requires pandas. Install with: pip install pandas")
    if not hasattr(df, "columns"):
        raise TypeError("Expected a pandas DataFrame.")


# =============================================================================
# FD table cache and interpolation
# =============================================================================

class FDTableCache:
    """
    Cache FD tables by drive.

    fd_tables can be:
        - list/tuple indexed by drive index
        - dict keyed by drive index or rounded drive_nm
    """
    def __init__(self, scanner=None, fd_tables: Optional[Union[Sequence[dict], Dict[Any, dict]]] = None,
                 n_d: int = 4096, round_decimals: int = 8):
        self.scanner = scanner
        self.fd_tables = fd_tables
        self.n_d = int(n_d)
        self.round_decimals = int(round_decimals)
        self.cache = {}

    def _drive_key(self, drive_nm):
        return round(float(drive_nm), self.round_decimals)

    def get(self, drive_nm, drive_index: Optional[int] = None):
        if self.fd_tables is not None:
            if isinstance(self.fd_tables, dict):
                if drive_index is not None and drive_index in self.fd_tables:
                    return self.fd_tables[drive_index]
                k = self._drive_key(drive_nm)
                if k in self.fd_tables:
                    return self.fd_tables[k]
                if float(drive_nm) in self.fd_tables:
                    return self.fd_tables[float(drive_nm)]
            elif drive_index is not None:
                return self.fd_tables[int(drive_index)]

        k = self._drive_key(drive_nm)
        if k not in self.cache:
            if self.scanner is None:
                raise ValueError("FD table is missing and scanner is None.")
            if hasattr(self.scanner, "prepare_fd_table_for_drive"):
                self.cache[k] = self.scanner.prepare_fd_table_for_drive(
                    drive_nm=float(drive_nm), n_d=self.n_d
                )
            elif prepare_fd_table is not None:
                self.cache[k] = prepare_fd_table(self.scanner, float(drive_nm), self.n_d)
            else:
                raise ValueError("Cannot prepare FD table for this scanner.")
        return self.cache[k]


def _fd_arrays(fd_table):
    d = np.asarray(fd_table.get("d_grid", fd_table.get("d", None)), dtype=float)
    A = np.asarray(fd_table.get("A_grid", fd_table.get("A", None)), dtype=float)
    phi = np.asarray(fd_table.get("phi_grid", fd_table.get("phi", None)), dtype=float)
    order = np.argsort(d)
    return d[order], A[order], phi[order]


def interp_fd_table(fd_table, d_query):
    d, A, phi = _fd_arrays(fd_table)
    dq = np.asarray(d_query, dtype=float)
    A_q = np.interp(dq, d, A, left=A[0], right=A[-1])
    phi_q = np.interp(dq, d, phi, left=phi[0], right=phi[-1])
    return A_q, phi_q


def invert_fd_A_to_d(fd_table, A_query):
    """
    Approximate inverse d(A). If A(d) is not strictly monotonic, this gives an
    interpolation over the sorted A branch and is best interpreted as an
    effective-distance estimate.
    """
    d, A, _ = _fd_arrays(fd_table)
    Aq = np.asarray(A_query, dtype=float)
    order = np.argsort(A)
    A_sorted = A[order]
    d_sorted = d[order]
    A_unique, unique_idx = np.unique(A_sorted, return_index=True)
    d_unique = d_sorted[unique_idx]
    if A_unique.size < 2:
        return np.full_like(Aq, np.nan, dtype=float)
    A_clip = np.clip(Aq, A_unique[0], A_unique[-1])
    return np.interp(A_clip, A_unique, d_unique)


# =============================================================================
# Extract DT channels
# =============================================================================

def _pick_first(dct, keys):
    for k in keys:
        if k in dct and dct[k] is not None:
            return np.asarray(dct[k], dtype=float).ravel()
    return None


def extract_dt_direction_state(direction_dict, fd_table=None):
    """
    Extract arrays from one output direction, e.g. out['trace'].

    Returned keys:
        h_dt, z_dt, d_dt, A_fd, phi_fd
    """
    h_dt = _pick_first(direction_dict, ["h_hat", "height_hat", "height", "d_hat", "z_out_hat"])
    z_dt = _pick_first(direction_dict, ["z_hat", "z", "z_meas_hat", "z_cmd_hat", "z_out_hat"])
    d_dt = _pick_first(direction_dict, ["d_ts_hat", "gap_hat", "distance_hat", "d_true_hat", "d_eff_hat", "d_hat"])
    A_fd = _pick_first(direction_dict, ["A_hat", "A_meas_hat", "A_meas", "A_true_hat", "A_true", "amp_hat", "amp"])
    phi_fd = _pick_first(direction_dict, ["phi_deg", "phi_hat_deg", "phi_meas_deg", "phi_meas", "phi_true_deg", "phi_true", "phase_deg", "phase"])

    if d_dt is not None and fd_table is not None and (A_fd is None or phi_fd is None):
        A_i, phi_i = interp_fd_table(fd_table, d_dt)
        if A_fd is None:
            A_fd = A_i
        if phi_fd is None:
            phi_fd = phi_i

    candidates = [x for x in [h_dt, z_dt, d_dt, A_fd, phi_fd] if x is not None]
    if not candidates:
        raise ValueError("Could not extract arrays from scanner output. Check output keys.")
    n = min(len(x) for x in candidates)

    def fix(x):
        if x is None:
            return np.full(n, np.nan)
        return np.asarray(x, dtype=float).ravel()[:n]

    return {"h_dt": fix(h_dt), "z_dt": fix(z_dt), "d_dt": fix(d_dt),
            "A_fd": fix(A_fd), "phi_fd": fix(phi_fd)}


def extract_dt_state_from_out(out, fd_table=None):
    return {
        "trace": extract_dt_direction_state(out["trace"], fd_table=fd_table),
        "retrace": extract_dt_direction_state(out["retrace"], fd_table=fd_table),
    }


def add_history_features(state):
    out = dict(state)

    def diff_pad(x):
        x = np.asarray(x, dtype=float).ravel()
        y = np.empty_like(x)
        if x.size == 0:
            return y
        y[0] = 0.0
        y[1:] = np.diff(x)
        return y

    n = len(out["A_fd"])
    out["dd_dt"] = diff_pad(out["d_dt"])
    out["dA_fd"] = diff_pad(out["A_fd"])
    out["dphi_fd"] = diff_pad(out["phi_fd"])
    out["dh_dt"] = diff_pad(out["h_dt"])
    out["dz_dt"] = diff_pad(out["z_dt"])
    out["x_norm"] = np.linspace(0.0, 1.0, n)
    return out


# =============================================================================
# Pairing DT samples with experimental samples
# =============================================================================

def _pair_indices_by_quantile(sim_key, exp_key, max_points, rng):
    n = min(len(sim_key), len(exp_key))
    if n < 5:
        return None, None
    sim_order = np.argsort(sim_key)
    exp_order = np.argsort(exp_key)
    qidx = _subsample_indices(n, max_points, rng)
    return sim_order[qidx], exp_order[qidx]


def pair_sim_exp_samples(sim_state, exp_h, exp_A, exp_phi, *, pairing: str, max_points: int, rng, trim_edges: int = 0):
    exp_h = _trim(exp_h, trim_edges)
    exp_A = _trim(exp_A, trim_edges)
    exp_phi = _trim(exp_phi, trim_edges)
    sim_state = {k: _trim(v, trim_edges) for k, v in sim_state.items()}

    n_sim = min(len(v) for v in sim_state.values())
    n_exp = min(len(exp_h), len(exp_A), len(exp_phi))
    n = min(n_sim, n_exp)
    if n < 5:
        return None

    sim_state = {k: np.asarray(v, dtype=float).ravel()[:n] for k, v in sim_state.items()}
    exp_h = np.asarray(exp_h, dtype=float).ravel()[:n]
    exp_A = np.asarray(exp_A, dtype=float).ravel()[:n]
    exp_phi = np.asarray(exp_phi, dtype=float).ravel()[:n]

    if pairing == "pixel":
        idx = _subsample_indices(n, max_points, rng)
        sim_idx = idx
        exp_idx = idx
    elif pairing == "quantile_by_A":
        sim_idx, exp_idx = _pair_indices_by_quantile(sim_state["A_fd"], exp_A, max_points, rng)
    elif pairing == "quantile_by_h":
        sim_idx, exp_idx = _pair_indices_by_quantile(sim_state["h_dt"], exp_h, max_points, rng)
    else:
        raise ValueError("pairing must be 'pixel', 'quantile_by_A', or 'quantile_by_h'.")

    if sim_idx is None:
        return None

    out = {k: np.asarray(v, dtype=float)[sim_idx] for k, v in sim_state.items()}
    out["exp_h"] = exp_h[exp_idx]
    out["exp_A"] = exp_A[exp_idx]
    out["exp_phi"] = exp_phi[exp_idx]
    return out


# =============================================================================
# Build residual dataset
# =============================================================================

def make_all_conditions(traces_exp_height, speed_indices=None, drive_indices=None, setpoint_indices=None, gain_indices=None):
    arr = np.asarray(traces_exp_height)
    n_speed, n_drive, n_sp, n_gain, two, n_pix = arr.shape

    def ids(x, n):
        return np.arange(n, dtype=int) if x is None else np.asarray(x, dtype=int)

    conds = []
    for si in ids(speed_indices, n_speed):
        for di in ids(drive_indices, n_drive):
            for spi in ids(setpoint_indices, n_sp):
                for gi in ids(gain_indices, n_gain):
                    conds.append((int(si), int(di), int(spi), int(gi)))
    return conds


def get_PI_for_condition(cond, *, P_grid=None, I_grid=None, controller_fn=None, controls=None):
    if controller_fn is not None:
        return controller_fn(cond, controls)
    if P_grid is None or I_grid is None:
        raise ValueError("Provide either P_grid/I_grid or controller_fn.")
    si, di, spi, gi = cond
    return float(P_grid[si, di, spi, gi]), float(I_grid[si, di, spi, gi])


def _pixel_stability_mask(A_fd, exp_A, phi_fd, exp_phi, cfg: ResidualDatasetConfig):
    m = _finite_mask(A_fd, exp_A, phi_fd, exp_phi)
    if not cfg.stable_only:
        return m

    A_all = np.r_[A_fd[np.isfinite(A_fd)], exp_A[np.isfinite(exp_A)]]
    if A_all.size > 5:
        A95 = np.nanpercentile(A_all, 95)
        if np.isfinite(A95) and A95 > 0:
            m &= A_fd > cfg.min_A_frac_of_A95 * A95
            m &= exp_A > cfg.min_A_frac_of_A95 * A95

    if cfg.max_abs_phi_jump_deg is not None:
        dphi = wrap_phase_diff_deg(exp_phi - phi_fd, cfg.phase_period_deg)
        m &= np.abs(dphi) <= float(cfg.max_abs_phi_jump_deg)
    return m


def build_residual_dataset(scanner, traces_exp_height, traces_exp_amp, traces_exp_phase, synthetic_lines,
                           scan_speeds_hat, drives_nm, setpoints, i_gains_exp, *, scanner_cfg,
                           P_grid=None, I_grid=None, controller_fn: Optional[Callable] = None,
                           conds: Optional[Sequence[Tuple[int, int, int, int]]] = None,
                           fd_cache: Optional[FDTableCache] = None, fd_tables=None,
                           cfg: Optional[ResidualDatasetConfig] = None, return_rows: bool = False):
    """
    Build per-pixel residual dataset.

    Experimental arrays must have shape:
        (speed, drive, setpoint, gain, 2, pixels)
    where direction index 0=trace and 1=retrace.
    """
    if run_scanner_line is None:
        raise ImportError("Could not import run_scanner_line from scaffold v3.")
    if cfg is None:
        cfg = ResidualDatasetConfig()

    rng = np.random.default_rng(cfg.random_state)
    traces_exp_height = np.asarray(traces_exp_height, dtype=float)
    traces_exp_amp = np.asarray(traces_exp_amp, dtype=float)
    traces_exp_phase = np.asarray(traces_exp_phase, dtype=float)

    if conds is None:
        conds = make_all_conditions(traces_exp_height)
    if fd_cache is None:
        fd_cache = FDTableCache(scanner=scanner, fd_tables=fd_tables, n_d=scanner_cfg.fd_n_d)

    rows = []
    n_lines_total = len(synthetic_lines)

    for cond in conds:
        si, di, spi, gi = cond
        speed = float(scan_speeds_hat[si])
        drive = float(drives_nm[di])
        setpoint = float(setpoints[spi])
        I_exp = float(i_gains_exp[gi])
        P_sim, I_sim = get_PI_for_condition(
            cond, P_grid=P_grid, I_grid=I_grid, controller_fn=controller_fn,
            controls={"scan_speed_hat": speed, "drive_nm": drive, "setpoint": setpoint, "I_exp": I_exp},
        )
        fd_table = fd_cache.get(drive, drive_index=di)

        for q in range(int(cfg.n_synthetic_lines_per_condition)):
            line_idx = q % n_lines_total
            h_line = np.asarray(synthetic_lines[line_idx], dtype=float).ravel()
            out = run_scanner_line(
                scanner, h_line, drive_nm=drive, setpoint=setpoint,
                scan_speed_hat=speed, P=P_sim, I=I_sim, cfg=scanner_cfg, fd_table=fd_table,
            )
            states = extract_dt_state_from_out(out, fd_table=fd_table)
            directions = ["trace", "retrace"] if cfg.include_retrace else ["trace"]

            for dir_name in directions:
                dir_idx = 0 if dir_name == "trace" else 1
                direction_sign = 1.0 if dir_name == "trace" else -1.0
                state = add_history_features(states[dir_name])

                paired = pair_sim_exp_samples(
                    state,
                    traces_exp_height[si, di, spi, gi, dir_idx],
                    traces_exp_amp[si, di, spi, gi, dir_idx],
                    traces_exp_phase[si, di, spi, gi, dir_idx],
                    pairing=cfg.pairing,
                    max_points=cfg.max_points_per_direction,
                    rng=rng,
                    trim_edges=cfg.trim_edges,
                )
                if paired is None:
                    continue

                m = _pixel_stability_mask(paired["A_fd"], paired["exp_A"], paired["phi_fd"], paired["exp_phi"], cfg)
                if np.sum(m) < 5:
                    continue

                d_from_A_exp = invert_fd_A_to_d(fd_table, paired["exp_A"][m])
                delta_A_raw = paired["exp_A"][m] - paired["A_fd"][m]
                delta_phi_raw = wrap_phase_diff_deg(paired["exp_phi"][m] - paired["phi_fd"][m], cfg.phase_period_deg)
                delta_h_raw = paired["exp_h"][m] - paired["h_dt"][m]
                delta_d_from_A = d_from_A_exp - paired["d_dt"][m]

                n_pts = np.sum(m)
                pm = {k: paired[k][m] for k in ["x_norm", "h_dt", "z_dt", "d_dt", "A_fd", "phi_fd", "dd_dt", "dA_fd", "dphi_fd", "dh_dt", "dz_dt", "exp_h", "exp_A", "exp_phi"]}
                for idx_local in range(n_pts):
                    rows.append({
                        "si": int(si), "di": int(di), "spi": int(spi), "gi": int(gi),
                        "synthetic_line_index": int(line_idx),
                        "direction": dir_name, "direction_sign": float(direction_sign),
                        "scan_speed_hat": speed, "log_scan_speed": float(np.log10(max(speed, 1e-30))),
                        "drive_nm": drive, "setpoint": setpoint,
                        "I_exp": I_exp, "log_I_exp": float(np.log10(max(I_exp, 1e-30))),
                        "P_sim": float(P_sim), "I_sim": float(I_sim),
                        "log_P_sim": float(np.log10(max(P_sim, 1e-30))),
                        "log_I_sim": float(np.log10(max(I_sim, 1e-30))),
                        "x_norm": float(pm["x_norm"][idx_local]),
                        "h_dt": float(pm["h_dt"][idx_local]),
                        "z_dt": float(pm["z_dt"][idx_local]),
                        "d_dt": float(pm["d_dt"][idx_local]),
                        "A_fd": float(pm["A_fd"][idx_local]),
                        "phi_fd": float(pm["phi_fd"][idx_local]),
                        "dd_dt": float(pm["dd_dt"][idx_local]),
                        "dA_fd": float(pm["dA_fd"][idx_local]),
                        "dphi_fd": float(pm["dphi_fd"][idx_local]),
                        "dh_dt": float(pm["dh_dt"][idx_local]),
                        "dz_dt": float(pm["dz_dt"][idx_local]),
                        "exp_h": float(pm["exp_h"][idx_local]),
                        "exp_A": float(pm["exp_A"][idx_local]),
                        "exp_phi": float(pm["exp_phi"][idx_local]),
                        "d_from_A_exp": float(d_from_A_exp[idx_local]),
                        "delta_d_from_A": float(delta_d_from_A[idx_local]),
                        "delta_A_raw": float(delta_A_raw[idx_local]),
                        "delta_phi_raw": float(delta_phi_raw[idx_local]),
                        "delta_h_raw": float(delta_h_raw[idx_local]),
                    })

    if return_rows:
        return rows
    return _as_dataframe(rows)


# =============================================================================
# Regression models
# =============================================================================

def _make_regressor(model_type: str, cfg):
    try:
        from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
        from sklearn.multioutput import MultiOutputRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        raise ImportError("Install scikit-learn to use residual layers.") from exc

    model_type = str(model_type).lower()
    if model_type == "histgb":
        base = HistGradientBoostingRegressor(
            max_iter=int(cfg.max_iter), learning_rate=float(cfg.learning_rate),
            max_leaf_nodes=int(cfg.max_leaf_nodes), min_samples_leaf=int(cfg.min_samples_leaf),
            random_state=int(cfg.random_state), l2_regularization=1e-4,
        )
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), MultiOutputRegressor(base))
    if model_type == "extratrees":
        return make_pipeline(SimpleImputer(strategy="median"), ExtraTreesRegressor(
            n_estimators=int(cfg.n_estimators), max_depth=cfg.max_depth,
            min_samples_leaf=int(cfg.min_samples_leaf), random_state=int(cfg.random_state), n_jobs=-1))
    if model_type == "randomforest":
        return make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(
            n_estimators=int(cfg.n_estimators), max_depth=cfg.max_depth,
            min_samples_leaf=int(cfg.min_samples_leaf), random_state=int(cfg.random_state), n_jobs=-1))
    raise ValueError("model_type must be 'histgb', 'extratrees', or 'randomforest'.")


def _sample_dataframe(df, max_points, random_state):
    _require_pandas(df)
    if max_points is None or len(df) <= int(max_points):
        return df
    return df.sample(n=int(max_points), random_state=int(random_state), replace=False)


def _finite_training_mask(df, feature_cols, target_cols):
    X = df[list(feature_cols)].to_numpy(dtype=float)
    Y = df[list(target_cols)].to_numpy(dtype=float)
    return np.isfinite(X).all(axis=1) & np.isfinite(Y).all(axis=1)


class StaticFDResidualLayer:
    def __init__(self, model, feature_cols, target_cols, config):
        self.model = model
        self.feature_cols = tuple(feature_cols)
        self.target_cols = tuple(target_cols)
        self.config = config

    def predict(self, data):
        if pd is not None and hasattr(data, "columns"):
            X = data[list(self.feature_cols)].to_numpy(dtype=float)
        elif isinstance(data, dict):
            X = np.column_stack([np.asarray(data[k], dtype=float).ravel() for k in self.feature_cols])
        else:
            X = np.asarray(data, dtype=float)
        Y = self.model.predict(X)
        return Y[:, 0], Y[:, 1]


class DynamicResidualLayer:
    def __init__(self, model, feature_cols, target_cols, config):
        self.model = model
        self.feature_cols = tuple(feature_cols)
        self.target_cols = tuple(target_cols)
        self.config = config

    def predict(self, data):
        if pd is not None and hasattr(data, "columns"):
            X = data[list(self.feature_cols)].to_numpy(dtype=float)
        elif isinstance(data, dict):
            X = np.column_stack([np.asarray(data[k], dtype=float).ravel() for k in self.feature_cols])
        else:
            X = np.asarray(data, dtype=float)
        Y = self.model.predict(X)
        return Y[:, 0], Y[:, 1], Y[:, 2]


def fit_static_fd_residual_layer(df_base, *, cfg: Optional[StaticFDResidualConfig] = None, extra_mask=None):
    _require_pandas(df_base)
    if cfg is None:
        cfg = StaticFDResidualConfig()
    df = df_base.copy()
    mask = _finite_training_mask(df, cfg.feature_cols, cfg.target_cols)
    if extra_mask is not None:
        mask &= np.asarray(extra_mask, dtype=bool)
    df = df.loc[mask].copy()
    df = _sample_dataframe(df, cfg.max_train_points, cfg.random_state)
    X = df[list(cfg.feature_cols)].to_numpy(dtype=float)
    Y = df[list(cfg.target_cols)].to_numpy(dtype=float)
    model = _make_regressor(cfg.model_type, cfg)
    model.fit(X, Y)
    layer = StaticFDResidualLayer(model, cfg.feature_cols, cfg.target_cols, asdict(cfg))
    info = {"n_train": int(len(df)), "feature_cols": cfg.feature_cols, "target_cols": cfg.target_cols, "model_type": cfg.model_type}
    return layer, info


def add_static_predictions_and_dynamic_targets(df_base, static_layer: StaticFDResidualLayer, fd_cache: FDTableCache,
                                               *, phase_period_deg: float = 360.0,
                                               use_target_deff_for_dynamic_targets: bool = True):
    """
    Create dynamic targets after applying the static layer.

    delta_d_dyn_target = d_from_A_exp - d_dt

    If use_target_deff_for_dynamic_targets=True, A/phi dynamic residuals are
    computed after shifting to the target effective distance.
    """
    _require_pandas(df_base)
    df = df_base.copy()

    delta_A0, delta_phi0 = static_layer.predict({
        "drive_nm": df["drive_nm"].to_numpy(dtype=float),
        "d_dt": df["d_dt"].to_numpy(dtype=float),
    })
    df["delta_A0"] = delta_A0
    df["delta_phi0"] = delta_phi0
    df["A_static_orig"] = df["A_fd"].to_numpy(dtype=float) + delta_A0
    df["phi_static_orig"] = df["phi_fd"].to_numpy(dtype=float) + delta_phi0
    df["delta_d_dyn_target"] = df["delta_d_from_A"].to_numpy(dtype=float)

    if use_target_deff_for_dynamic_targets:
        d_eff_target = df["d_dt"].to_numpy(dtype=float) + df["delta_d_dyn_target"].to_numpy(dtype=float)
        df["d_eff_target"] = d_eff_target
        A_eff = np.empty(len(df), dtype=float)
        phi_eff = np.empty(len(df), dtype=float)

        for (di, drive), idx_obj in df.groupby(["di", "drive_nm"]).groups.items():
            idx = np.asarray(list(idx_obj), dtype=int)
            fd_table = fd_cache.get(float(drive), drive_index=int(di))
            A_i, phi_i = interp_fd_table(fd_table, d_eff_target[idx])
            A_eff[idx] = A_i
            phi_eff[idx] = phi_i

        delta_A0_eff, delta_phi0_eff = static_layer.predict({
            "drive_nm": df["drive_nm"].to_numpy(dtype=float),
            "d_dt": d_eff_target,
        })
        df["A_fd_eff_target"] = A_eff
        df["phi_fd_eff_target"] = phi_eff
        df["delta_A0_eff"] = delta_A0_eff
        df["delta_phi0_eff"] = delta_phi0_eff
        df["A_static"] = A_eff + delta_A0_eff
        df["phi_static"] = phi_eff + delta_phi0_eff
    else:
        df["d_eff_target"] = df["d_dt"].to_numpy(dtype=float)
        df["A_static"] = df["A_static_orig"].to_numpy(dtype=float)
        df["phi_static"] = df["phi_static_orig"].to_numpy(dtype=float)

    df["delta_A_dyn_target"] = df["exp_A"].to_numpy(dtype=float) - df["A_static"].to_numpy(dtype=float)
    df["delta_phi_dyn_target"] = wrap_phase_diff_deg(
        df["exp_phi"].to_numpy(dtype=float) - df["phi_static"].to_numpy(dtype=float),
        period=phase_period_deg,
    )
    return df


def fit_dynamic_residual_layer(df_dyn, *, cfg: Optional[DynamicResidualConfig] = None, extra_mask=None):
    _require_pandas(df_dyn)
    if cfg is None:
        cfg = DynamicResidualConfig()
    df = df_dyn.copy()
    mask = _finite_training_mask(df, cfg.feature_cols, cfg.target_cols)
    if extra_mask is not None:
        mask &= np.asarray(extra_mask, dtype=bool)
    df = df.loc[mask].copy()
    df = _sample_dataframe(df, cfg.max_train_points, cfg.random_state)
    X = df[list(cfg.feature_cols)].to_numpy(dtype=float)
    Y = df[list(cfg.target_cols)].to_numpy(dtype=float)
    model = _make_regressor(cfg.model_type, cfg)
    model.fit(X, Y)
    layer = DynamicResidualLayer(model, cfg.feature_cols, cfg.target_cols, asdict(cfg))
    info = {"n_train": int(len(df)), "feature_cols": cfg.feature_cols, "target_cols": cfg.target_cols, "model_type": cfg.model_type}
    return layer, info


# =============================================================================
# Apply layers to new DT output
# =============================================================================

def _state_to_prediction_dataframe(state, *, controls, direction: str):
    if pd is None:
        raise ImportError("Prediction helper requires pandas.")
    state = add_history_features(state)
    n = len(state["A_fd"])
    direction_sign = 1.0 if direction == "trace" else -1.0
    speed = float(controls["scan_speed_hat"])
    drive = float(controls["drive_nm"])
    setpoint = float(controls["setpoint"])
    I_exp = float(controls.get("I_exp", np.nan))
    P_sim = float(controls["P_sim"])
    I_sim = float(controls["I_sim"])
    df = pd.DataFrame({
        "scan_speed_hat": np.full(n, speed),
        "log_scan_speed": np.full(n, np.log10(max(speed, 1e-30))),
        "drive_nm": np.full(n, drive),
        "setpoint": np.full(n, setpoint),
        "I_exp": np.full(n, I_exp),
        "log_I_exp": np.full(n, np.log10(max(I_exp, 1e-30))),
        "P_sim": np.full(n, P_sim),
        "I_sim": np.full(n, I_sim),
        "log_P_sim": np.full(n, np.log10(max(P_sim, 1e-30))),
        "log_I_sim": np.full(n, np.log10(max(I_sim, 1e-30))),
        "direction": [direction] * n,
        "direction_sign": np.full(n, direction_sign),
    })
    for k, v in state.items():
        df[k] = np.asarray(v, dtype=float).ravel()[:n]
    return df


def predict_corrected_channels_for_out(out, *, controls: Dict[str, float], fd_table,
                                       static_layer: StaticFDResidualLayer,
                                       dynamic_layer: DynamicResidualLayer,
                                       static_at_deff: bool = True):
    """
    Apply static + dynamic residual layers to one scanner output.

    controls must contain:
        scan_speed_hat, drive_nm, setpoint, P_sim, I_sim
    Optional:
        I_exp
    """
    if pd is None:
        raise ImportError("This helper requires pandas.")

    states = extract_dt_state_from_out(out, fd_table=fd_table)
    result = {}

    for direction in ["trace", "retrace"]:
        state = states[direction]
        df = _state_to_prediction_dataframe(state, controls=controls, direction=direction)

        delta_A0, delta_phi0 = static_layer.predict({
            "drive_nm": df["drive_nm"].to_numpy(dtype=float),
            "d_dt": df["d_dt"].to_numpy(dtype=float),
        })
        df["delta_A0"] = delta_A0
        df["delta_phi0"] = delta_phi0
        df["A_static"] = df["A_fd"].to_numpy(dtype=float) + delta_A0
        df["phi_static"] = df["phi_fd"].to_numpy(dtype=float) + delta_phi0

        delta_d_dyn, delta_A_dyn, delta_phi_dyn = dynamic_layer.predict(df)
        d_eff = df["d_dt"].to_numpy(dtype=float) + delta_d_dyn
        A_eff, phi_eff = interp_fd_table(fd_table, d_eff)

        if static_at_deff:
            delta_A0_eff, delta_phi0_eff = static_layer.predict({
                "drive_nm": df["drive_nm"].to_numpy(dtype=float),
                "d_dt": d_eff,
            })
        else:
            delta_A0_eff, delta_phi0_eff = delta_A0, delta_phi0

        A_pred = A_eff + delta_A0_eff + delta_A_dyn
        phi_pred = phi_eff + delta_phi0_eff + delta_phi_dyn

        result[direction] = {
            "h_dt": df["h_dt"].to_numpy(dtype=float),
            "z_dt": df["z_dt"].to_numpy(dtype=float),
            "d_dt": df["d_dt"].to_numpy(dtype=float),
            "A_fd": df["A_fd"].to_numpy(dtype=float),
            "phi_fd": df["phi_fd"].to_numpy(dtype=float),
            "delta_A0": delta_A0_eff,
            "delta_phi0": delta_phi0_eff,
            "delta_d_dyn": delta_d_dyn,
            "delta_A_dyn": delta_A_dyn,
            "delta_phi_dyn": delta_phi_dyn,
            "d_eff": d_eff,
            "A_pred": A_pred,
            "phi_pred": phi_pred,
        }
    return result


# =============================================================================
# Diagnostics
# =============================================================================

def residual_summary(df, cols=None):
    _require_pandas(df)
    if cols is None:
        cols = [
            "delta_A_raw", "delta_phi_raw", "delta_d_from_A",
            "delta_A_dyn_target", "delta_phi_dyn_target", "delta_d_dyn_target",
        ]
        cols = [c for c in cols if c in df.columns]
    rows = []
    for c in cols:
        x = df[c].to_numpy(dtype=float)
        x = x[np.isfinite(x)]
        if x.size == 0:
            continue
        rows.append({
            "column": c,
            "n": int(x.size),
            "mean": float(np.mean(x)),
            "std": float(np.std(x)),
            "mad": robust_mad(x),
            "p05": float(np.percentile(x, 5)),
            "p50": float(np.percentile(x, 50)),
            "p95": float(np.percentile(x, 95)),
        })
    return pd.DataFrame(rows) if pd is not None else rows


def train_test_split_conditions(conds, test_frac=0.2, seed=0):
    rng = np.random.default_rng(seed)
    conds = list(conds)
    idx = rng.permutation(len(conds))
    n_test = int(round(len(conds) * float(test_frac)))
    test = [conds[i] for i in idx[:n_test]]
    train = [conds[i] for i in idx[n_test:]]
    return train, test
