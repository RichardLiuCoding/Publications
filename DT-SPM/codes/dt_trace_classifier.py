"""
dt_trace_classifier.py
======================

Trace usability classifier for SPM digital-twin calibration.

Purpose
-------
Flat/no-response height traces are degenerate for static P/I controller
calibration: P=I≈0 can reproduce a flat height line, so they should be
excluded from the static controller fit.

However, those traces should NOT be discarded. They are useful labels for
dynamic quality/safety prediction.

Typical usage
-------------
Static calibration:
    train_conds, test_conds, informative, rejected = split_informative_conditions(...)

Dynamic calibration:
    info = classify_height_trace_pair(...)
    row["trace_class"] = info["class"]
    row["use_for_static_calibration"] = int(info["use_for_static_calibration"])
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Sequence, Tuple, List, Dict, Any
import numpy as np


@dataclass
class TraceUsabilityConfig:
    """
    Thresholds are in the same units as traces_exp.

    If traces_exp is in nm, defaults mean:
        min_mad=0.02 nm
        min_range=0.10 nm
        min_grad_mad=0.002 nm/pixel
    """
    trim: int = 10

    min_mad: float = 0.02
    min_range: float = 0.10
    min_grad_mad: float = 0.002
    min_nonzero_frac: float = 0.05

    flat_eps: float = 1e-12

    # Optional upper bound to reject obviously broken/saturated traces from
    # static calibration. Leave None to disable.
    max_mad: Optional[float] = None
    max_range: Optional[float] = None
    max_grad_mad: Optional[float] = None

    # If True, reject traces containing too many NaN/inf values.
    min_finite_frac: float = 0.90


def robust_mad(x, eps: float = 1e-12) -> float:
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return eps
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)) + eps)


def trim_1d(x, trim: int = 10):
    x = np.asarray(x, dtype=float).ravel()
    trim = int(trim)
    if trim <= 0 or len(x) <= 2 * trim + 4:
        return x
    return x[trim:-trim]


def _finite_fraction(x):
    x = np.asarray(x, dtype=float).ravel()
    if x.size == 0:
        return 0.0
    return float(np.mean(np.isfinite(x)))


def classify_height_trace_pair(
    h_tr,
    h_rt,
    cfg: Optional[TraceUsabilityConfig] = None,
    **overrides,
) -> Dict[str, Any]:
    """
    Classify trace/retrace height pair.

    Returns a dict with:
        use_for_static_calibration: bool
        class: "informative", "flat_or_uninformative", "unstable_or_outlier", "invalid"
        reason: text
        height_mad
        height_range_p99_p01
        grad_mad
        nonzero_frac
        finite_frac
    """
    if cfg is None:
        cfg = TraceUsabilityConfig()

    # Allow quick overrides such as classify_height_trace_pair(..., min_mad=0.05).
    if overrides:
        d = asdict(cfg)
        d.update(overrides)
        cfg = TraceUsabilityConfig(**d)

    h_tr_raw = np.asarray(h_tr, dtype=float).ravel()
    h_rt_raw = np.asarray(h_rt, dtype=float).ravel()

    finite_frac = min(_finite_fraction(h_tr_raw), _finite_fraction(h_rt_raw))

    if finite_frac < cfg.min_finite_frac:
        return {
            "use_for_static_calibration": False,
            "class": "invalid",
            "reason": "too_many_nonfinite_points",
            "finite_frac": finite_frac,
        }

    h_tr = trim_1d(h_tr_raw, cfg.trim)
    h_rt = trim_1d(h_rt_raw, cfg.trim)

    n = min(len(h_tr), len(h_rt))
    if n < 10:
        return {
            "use_for_static_calibration": False,
            "class": "invalid",
            "reason": "too_few_points",
            "finite_frac": finite_frac,
        }

    h_tr = h_tr[:n]
    h_rt = h_rt[:n]

    mask = np.isfinite(h_tr) & np.isfinite(h_rt)
    if np.sum(mask) < 10:
        return {
            "use_for_static_calibration": False,
            "class": "invalid",
            "reason": "too_few_common_finite_points",
            "finite_frac": finite_frac,
        }

    h_tr = h_tr[mask]
    h_rt = h_rt[mask]

    h_all = np.r_[h_tr, h_rt]
    h_med = np.nanmedian(h_all)

    height_mad = robust_mad(h_all)
    height_range = float(np.nanpercentile(h_all, 99) - np.nanpercentile(h_all, 1))

    dh_tr = np.diff(h_tr)
    dh_rt = np.diff(h_rt)
    dh_all = np.r_[dh_tr, dh_rt]
    grad_mad = robust_mad(dh_all)

    nonzero_frac = float(np.mean(np.abs(h_all - h_med) > cfg.flat_eps))

    flat_reasons = []
    if height_mad < cfg.min_mad:
        flat_reasons.append("height_mad_below_threshold")
    if height_range < cfg.min_range:
        flat_reasons.append("height_range_below_threshold")
    if grad_mad < cfg.min_grad_mad:
        flat_reasons.append("gradient_mad_below_threshold")
    if nonzero_frac < cfg.min_nonzero_frac:
        flat_reasons.append("nonzero_fraction_below_threshold")

    if flat_reasons:
        return {
            "use_for_static_calibration": False,
            "class": "flat_or_uninformative",
            "reason": ",".join(flat_reasons),
            "height_mad": float(height_mad),
            "height_range_p99_p01": float(height_range),
            "grad_mad": float(grad_mad),
            "nonzero_frac": float(nonzero_frac),
            "finite_frac": float(finite_frac),
        }

    outlier_reasons = []
    if cfg.max_mad is not None and height_mad > cfg.max_mad:
        outlier_reasons.append("height_mad_above_max")
    if cfg.max_range is not None and height_range > cfg.max_range:
        outlier_reasons.append("height_range_above_max")
    if cfg.max_grad_mad is not None and grad_mad > cfg.max_grad_mad:
        outlier_reasons.append("gradient_mad_above_max")

    if outlier_reasons:
        return {
            "use_for_static_calibration": False,
            "class": "unstable_or_outlier",
            "reason": ",".join(outlier_reasons),
            "height_mad": float(height_mad),
            "height_range_p99_p01": float(height_range),
            "grad_mad": float(grad_mad),
            "nonzero_frac": float(nonzero_frac),
            "finite_frac": float(finite_frac),
        }

    return {
        "use_for_static_calibration": True,
        "class": "informative",
        "reason": "ok",
        "height_mad": float(height_mad),
        "height_range_p99_p01": float(height_range),
        "grad_mad": float(grad_mad),
        "nonzero_frac": float(nonzero_frac),
        "finite_frac": float(finite_frac),
    }


def make_condition_list(
    traces_exp_height,
    *,
    speed_indices=None,
    drive_indices=None,
    setpoint_indices=None,
    gain_indices=None,
):
    traces_exp_height = np.asarray(traces_exp_height)
    n_speed, n_drive, n_sp, n_gain, two, n_pix = traces_exp_height.shape
    if two != 2:
        raise ValueError("traces_exp_height must have shape (..., 2, pixels).")

    def ids(x, n):
        return np.arange(n, dtype=int) if x is None else np.asarray(x, dtype=int)

    conds = []
    for si in ids(speed_indices, n_speed):
        for di in ids(drive_indices, n_drive):
            for spi in ids(setpoint_indices, n_sp):
                for gi in ids(gain_indices, n_gain):
                    conds.append((int(si), int(di), int(spi), int(gi)))
    return conds


def classify_conditions(
    traces_exp_height,
    conds,
    cfg: Optional[TraceUsabilityConfig] = None,
):
    """
    Classify a list of condition tuples.
    """
    if cfg is None:
        cfg = TraceUsabilityConfig()

    rows = []
    for cond in conds:
        si, di, spi, gi = cond
        info = classify_height_trace_pair(
            traces_exp_height[si, di, spi, gi, 0],
            traces_exp_height[si, di, spi, gi, 1],
            cfg=cfg,
        )
        row = {"cond": tuple(int(v) for v in cond)}
        row.update(info)
        rows.append(row)
    return rows


def split_informative_conditions(
    traces_exp_height,
    *,
    n_train: int = 100,
    n_test: int = 50,
    seed: int = 0,
    cfg: Optional[TraceUsabilityConfig] = None,
    speed_indices=None,
    drive_indices=None,
    setpoint_indices=None,
    gain_indices=None,
):
    """
    Randomly split only informative conditions into train/test.

    Returns
    -------
    train_conds, test_conds, informative_conds, rejected_rows
    """
    if cfg is None:
        cfg = TraceUsabilityConfig()

    all_conds = make_condition_list(
        traces_exp_height,
        speed_indices=speed_indices,
        drive_indices=drive_indices,
        setpoint_indices=setpoint_indices,
        gain_indices=gain_indices,
    )

    classified = classify_conditions(traces_exp_height, all_conds, cfg=cfg)

    informative = [r["cond"] for r in classified if r["use_for_static_calibration"]]
    rejected = [r for r in classified if not r["use_for_static_calibration"]]

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(informative))

    n_train = min(int(n_train), len(informative))
    n_test = min(int(n_test), max(0, len(informative) - n_train))

    train = [informative[i] for i in perm[:n_train]]
    test = [informative[i] for i in perm[n_train:n_train + n_test]]

    return train, test, informative, rejected


def summarize_classification_rows(rows):
    """
    Summarize classifier rows from classify_conditions or rejected rows.
    """
    summary = {}
    for r in rows:
        cls = r.get("class", "unknown")
        summary[cls] = summary.get(cls, 0) + 1
    return summary
