"""
spm_fd_rk45_extended_calibration.py

Full RK45-based calibration utilities for SPM approach/FD curves.

Main workflow
-------------
1. Fit individual FD curves with the RK45 steady-state solver:
       individual_fits = fit_individual_fd_curves_rk45(...)

2. Fit all curves jointly with shared physics and smooth drive-dependent C3:
       global_fit = fit_global_drive_dependent_C3_extended_rk45(...)

Physics included
----------------
- Smoothed DMT-like conservative tip-sample force
- Distance-dependent long-range and contact damping
- Adaptive Dormand-Prince RK45 integration
- Windowed lock-in demodulation
- Global drive-frequency detuning
- Smooth C3(drive) calibration
- Per-curve distance offsets
- Automatic far-field phase alignment
- Optional per-curve residual phase offsets
- Optional amplitude-dependent phase weighting
- Optional measurement-chain low-pass filtering along approach direction

Expected curve format
---------------------
Each curve is a dict:
    {
        "drive_nm": float,
        "d_hat": np.ndarray,      # normalized height/gap coordinate
        "A_hat": np.ndarray,      # normalized amplitude
        "phi_deg": np.ndarray,    # measured phase in degrees
        "A0_hat": float,          # normalized far-field amplitude
        "omega_drive_hat": float, # optional, default 1.0
        "omega_ref_hat": float,   # optional, default omega_drive_hat
    }

If your input arrays are in nm, use build_measured_fd_curves(..., conv_L=...).
If you are already in normalized units, set conv_L=1.0.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt

from numba import njit
from scipy.optimize import least_squares


# =============================================================================
# 0. Phase and filtering utilities
# =============================================================================

def angle_diff_period_deg(a, b, period_deg: float = 360.0):
    """
    Circular difference a - b in degrees.

    period_deg=360 for normal phase.
    period_deg=180 if your lock-in phase is folded into [0, 180].
    """
    p = float(period_deg)
    return (np.asarray(a) - np.asarray(b) + 0.5 * p) % p - 0.5 * p


def circular_mean_period_deg(phi_deg, period_deg: float = 360.0):
    """
    Circular mean for an angle with arbitrary period.
    """
    p = float(period_deg)
    theta = 2.0 * np.pi * np.asarray(phi_deg, dtype=float) / p
    s = np.nanmean(np.sin(theta))
    c = np.nanmean(np.cos(theta))
    mean_theta = np.arctan2(s, c)
    return (p * mean_theta / (2.0 * np.pi)) % p


def far_field_indices(d_hat, frac: float = 0.15):
    """
    Indices corresponding to the largest-distance part of the approach curve.
    """
    d_hat = np.asarray(d_hat, dtype=float)
    n_far = max(3, int(frac * len(d_hat)))
    return np.argsort(d_hat)[::-1][:n_far]


def estimate_phase_offset_far_field(
    phi_sim,
    phi_exp,
    d_hat,
    frac: float = 0.15,
    period_deg: float = 360.0,
):
    """
    Offset to add to phi_sim so its far-field phase matches experiment.
    """
    idx = far_field_indices(d_hat, frac=frac)
    diff = angle_diff_period_deg(phi_exp[idx], phi_sim[idx], period_deg=period_deg)
    return circular_mean_period_deg(diff, period_deg=period_deg)


def transform_phase_deg(phi_deg, mode: str = "raw"):
    """
    Try different lock-in phase conventions.

    Common options:
        raw
        neg
        plus180
        minus_from_180
        minus_from_360
    """
    phi_deg = np.asarray(phi_deg, dtype=float)

    if mode == "raw":
        return phi_deg
    if mode == "neg":
        return -phi_deg
    if mode == "plus180":
        return phi_deg + 180.0
    if mode == "minus_from_180":
        return 180.0 - phi_deg
    if mode == "minus_from_360":
        return 360.0 - phi_deg

    raise ValueError(f"Unknown phase mode: {mode}")


def lowpass_real_by_d(y, d_hat, alpha: Optional[float]):
    """
    First-order low-pass filtering along approach direction, from far to near.

    alpha=1 or None means no filtering.
    Smaller alpha gives stronger lag/smoothing.
    """
    y = np.asarray(y, dtype=float)
    if alpha is None or alpha >= 1.0:
        return y.copy()

    alpha = float(np.clip(alpha, 1e-8, 1.0))
    order = np.argsort(np.asarray(d_hat, dtype=float))[::-1]

    y_sorted = y[order]
    out_sorted = np.empty_like(y_sorted)
    out_sorted[0] = y_sorted[0]

    for i in range(1, len(y_sorted)):
        out_sorted[i] = out_sorted[i - 1] + alpha * (y_sorted[i] - out_sorted[i - 1])

    out = np.empty_like(y)
    out[order] = out_sorted
    return out


def lowpass_phase_by_d(phi_deg, d_hat, alpha: Optional[float], period_deg: float = 360.0):
    """
    Circular first-order low-pass filtering along approach direction.
    """
    phi_deg = np.asarray(phi_deg, dtype=float)
    if alpha is None or alpha >= 1.0:
        return phi_deg.copy()

    alpha = float(np.clip(alpha, 1e-8, 1.0))
    period_deg = float(period_deg)
    order = np.argsort(np.asarray(d_hat, dtype=float))[::-1]

    phi_sorted = phi_deg[order]
    out_sorted = np.empty_like(phi_sorted)
    out_sorted[0] = phi_sorted[0]

    for i in range(1, len(phi_sorted)):
        dphi = angle_diff_period_deg(phi_sorted[i], out_sorted[i - 1], period_deg=period_deg)
        out_sorted[i] = out_sorted[i - 1] + alpha * dphi

    out = np.empty_like(phi_deg)
    out[order] = out_sorted
    return out


def phase_convention_score(
    phi_sim,
    phi_exp,
    d_hat,
    modes=("raw", "neg", "plus180", "minus_from_180", "minus_from_360"),
    far_field_frac: float = 0.15,
    period_deg: float = 360.0,
):
    """
    Diagnostic: compare possible lock-in phase conventions after far-field alignment.
    """
    scores = {}
    for mode in modes:
        phi_try = transform_phase_deg(phi_sim, mode=mode)
        offset = estimate_phase_offset_far_field(
            phi_try, phi_exp, d_hat, frac=far_field_frac, period_deg=period_deg
        )
        phi_aligned = phi_try + offset
        err = angle_diff_period_deg(phi_aligned, phi_exp, period_deg=period_deg)
        scores[mode] = {
            "rmse_deg": float(np.sqrt(np.nanmean(err**2))),
            "offset_deg": float(offset),
        }
    return scores


# =============================================================================
# 1. Input data preparation
# =============================================================================

def build_measured_fd_curves(
    drives_nm,
    height_nm,
    amplitude_nm,
    phase_deg,
    conv_L: float = 1.0,
    A0_method: str = "far_field_median",
    far_field_frac: float = 0.10,
    omega_drive_hat: float = 1.0,
    omega_ref_hat: Optional[float] = None,
):
    """
    Build measured curve dictionaries from arrays.

    Parameters
    ----------
    drives_nm : shape (n_drive,)
    height_nm : shape (n_drive, n_point) or (n_point,)
    amplitude_nm : shape (n_drive, n_point)
    phase_deg : shape (n_drive, n_point)
    conv_L : conversion from nm to normalized length.
             Use scanner.conversion["A"] if you have it.
             Use 1.0 if arrays are already normalized.
    A0_method : "far_field_median" or "drive"
    """
    drives_nm = np.asarray(drives_nm, dtype=float).ravel()
    amplitude_nm = np.asarray(amplitude_nm, dtype=float)
    phase_deg = np.asarray(phase_deg, dtype=float)

    n_drive = len(drives_nm)

    height_nm = np.asarray(height_nm, dtype=float)
    if height_nm.ndim == 1:
        height_nm = np.tile(height_nm[None, :], (n_drive, 1))

    if amplitude_nm.shape != height_nm.shape:
        raise ValueError(
            f"amplitude_nm shape {amplitude_nm.shape} does not match "
            f"height_nm shape {height_nm.shape}"
        )

    if phase_deg.shape != height_nm.shape:
        raise ValueError(
            f"phase_deg shape {phase_deg.shape} does not match "
            f"height_nm shape {height_nm.shape}"
        )

    if omega_ref_hat is None:
        omega_ref_hat = omega_drive_hat

    curves = []

    for j, drive in enumerate(drives_nm):
        d_nm = height_nm[j].astype(float).ravel()
        A_nm = amplitude_nm[j].astype(float).ravel()
        phi = phase_deg[j].astype(float).ravel()

        mask = np.isfinite(d_nm) & np.isfinite(A_nm) & np.isfinite(phi)
        d_nm = d_nm[mask]
        A_nm = A_nm[mask]
        phi = phi[mask]

        if d_nm.size < 8:
            raise ValueError(f"Drive {drive}: too few finite points.")

        if A0_method == "far_field_median":
            n_far = max(2, int(far_field_frac * d_nm.size))
            far_idx = np.argsort(d_nm)[::-1][:n_far]
            A0_nm = float(np.median(A_nm[far_idx]))
        elif A0_method == "drive":
            A0_nm = float(drive)
        else:
            raise ValueError("A0_method must be 'far_field_median' or 'drive'.")

        curves.append(
            {
                "drive_nm": float(drive),
                "d_hat": d_nm * conv_L,
                "A_hat": A_nm * conv_L,
                "phi_deg": phi,
                "A0_hat": A0_nm * conv_L,
                "omega_drive_hat": float(omega_drive_hat),
                "omega_ref_hat": float(omega_ref_hat),
            }
        )

    return curves


def build_measured_fd_curves_from_dict(
    measured_fd: Dict[float, Dict[str, np.ndarray]],
    conv_L: float = 1.0,
    A0_method: str = "far_field_median",
    far_field_frac: float = 0.10,
    omega_drive_hat: float = 1.0,
    omega_ref_hat: Optional[float] = None,
):
    """
    Input format:
        measured_fd = {
            20.0: {"d": h20, "A": A20, "phi": phi20},
            30.0: {"d": h30, "A": A30, "phi": phi30},
            ...
        }
    """
    drives = sorted([float(k) for k in measured_fd.keys()])

    height = []
    amp = []
    phase = []

    for d0 in drives:
        c = measured_fd[d0]
        height.append(np.asarray(c["d"], dtype=float))
        amp.append(np.asarray(c["A"], dtype=float))
        phase.append(np.asarray(c["phi"], dtype=float))

    return build_measured_fd_curves(
        np.asarray(drives),
        np.asarray(height),
        np.asarray(amp),
        np.asarray(phase),
        conv_L=conv_L,
        A0_method=A0_method,
        far_field_frac=far_field_frac,
        omega_drive_hat=omega_drive_hat,
        omega_ref_hat=omega_ref_hat,
    )


# =============================================================================
# 2. Numba RK45 solver: smoothed DMT + distance-dependent damping
# =============================================================================

@njit(cache=True)
def angle_diff_period_deg_numba(a, b, period_deg):
    return (a - b + 0.5 * period_deg) % period_deg - 0.5 * period_deg


@njit(cache=True)
def smooth_relu_numba(x, w):
    """
    Smooth approximation to max(x, 0).
    """
    return 0.5 * (x + np.sqrt(x * x + w * w))


@njit(cache=True)
def F_DMT_smooth_hat(delta_hat, C1, C2, a0, w_contact):
    """
    Smoothed DMT-like force.

    Convention:
        delta_hat > 0 : non-contact gap
        delta_hat < 0 : indentation/contact

    Force:
        attraction = -C1 / (gap + a0)^2
        repulsion  =  C2 * indentation^1.5
    """
    gap = smooth_relu_numba(delta_hat, w_contact)
    indentation = smooth_relu_numba(-delta_hat, w_contact)

    F_attr = -C1 / (gap + a0) ** 2
    F_rep = C2 * indentation ** 1.5

    return F_attr + F_rep


@njit(cache=True)
def gamma_ts_hat(delta_hat, gamma_lr, lambda_lr, gamma_contact, w_contact):
    """
    Distance-dependent extra damping.

    gamma_lr:
        long-range damping that decays with positive gap.

    gamma_contact:
        additional damping in contact/intermittent-contact regime.
    """
    gap = smooth_relu_numba(delta_hat, w_contact)
    indentation = smooth_relu_numba(-delta_hat, w_contact)

    gamma_long = gamma_lr * np.exp(-gap / lambda_lr)

    contact_gate = indentation / (indentation + w_contact + 1e-12)
    gamma_cont = gamma_contact * contact_gate

    return gamma_long + gamma_cont


@njit(cache=True)
def rhs_hat_extended(
    t_hat,
    z_hat,
    v_hat,
    d_hat,
    Q,
    C1,
    C2,
    C3,
    a0,
    omega_drive_hat,
    w_contact,
    gamma_lr,
    lambda_lr,
    gamma_contact,
):
    """
    Extended normalized oscillator RHS.

    dz/dt = v
    dv/dt = F_cons + F_drive - [1/Q + gamma_ts(delta)] v - z
    """
    delta_hat = z_hat + d_hat

    F_contact = F_DMT_smooth_hat(
        delta_hat, C1, C2, a0, w_contact
    )

    F_drive = -C3 * np.cos(omega_drive_hat * t_hat)

    damping = 1.0 / Q + gamma_ts_hat(
        delta_hat, gamma_lr, lambda_lr, gamma_contact, w_contact
    )

    dz = v_hat
    dv = F_contact + F_drive - damping * v_hat - z_hat

    return dz, dv


@njit(cache=True)
def rk45_step_dopri_extended(
    t,
    z,
    v,
    dt,
    d_hat,
    Q,
    C1,
    C2,
    C3,
    a0,
    omega_drive_hat,
    w_contact,
    gamma_lr,
    lambda_lr,
    gamma_contact,
    rtol,
    atol,
):
    """
    One adaptive Dormand-Prince RK45 step with scalar error estimate.

    This is the RK45 version of the extended RHS.
    """
    c2 = 1.0 / 5.0
    c3 = 3.0 / 10.0
    c4 = 4.0 / 5.0
    c5 = 8.0 / 9.0
    c6 = 1.0

    a21 = 1.0 / 5.0

    a31 = 3.0 / 40.0
    a32 = 9.0 / 40.0

    a41 = 44.0 / 45.0
    a42 = -56.0 / 15.0
    a43 = 32.0 / 9.0

    a51 = 19372.0 / 6561.0
    a52 = -25360.0 / 2187.0
    a53 = 64448.0 / 6561.0
    a54 = -212.0 / 729.0

    a61 = 9017.0 / 3168.0
    a62 = -355.0 / 33.0
    a63 = 46732.0 / 5247.0
    a64 = 49.0 / 176.0
    a65 = -5103.0 / 18656.0

    b1 = 35.0 / 384.0
    b3 = 500.0 / 1113.0
    b4 = 125.0 / 192.0
    b5 = -2187.0 / 6784.0
    b6 = 11.0 / 84.0

    b1s = 5179.0 / 57600.0
    b3s = 7571.0 / 16695.0
    b4s = 393.0 / 640.0
    b5s = -92097.0 / 339200.0
    b6s = 187.0 / 2100.0
    b7s = 1.0 / 40.0

    dz1, dv1 = rhs_hat_extended(
        t, z, v, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z2 = z + dt * a21 * dz1
    v2 = v + dt * a21 * dv1
    dz2, dv2 = rhs_hat_extended(
        t + c2 * dt, z2, v2, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z3 = z + dt * (a31 * dz1 + a32 * dz2)
    v3 = v + dt * (a31 * dv1 + a32 * dv2)
    dz3, dv3 = rhs_hat_extended(
        t + c3 * dt, z3, v3, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z4 = z + dt * (a41 * dz1 + a42 * dz2 + a43 * dz3)
    v4 = v + dt * (a41 * dv1 + a42 * dv2 + a43 * dv3)
    dz4, dv4 = rhs_hat_extended(
        t + c4 * dt, z4, v4, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z5i = z + dt * (a51 * dz1 + a52 * dz2 + a53 * dz3 + a54 * dz4)
    v5i = v + dt * (a51 * dv1 + a52 * dv2 + a53 * dv3 + a54 * dv4)
    dz5, dv5 = rhs_hat_extended(
        t + c5 * dt, z5i, v5i, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z6 = z + dt * (a61 * dz1 + a62 * dz2 + a63 * dz3 + a64 * dz4 + a65 * dz5)
    v6 = v + dt * (a61 * dv1 + a62 * dv2 + a63 * dv3 + a64 * dv4 + a65 * dv5)
    dz6, dv6 = rhs_hat_extended(
        t + c6 * dt, z6, v6, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z5 = z + dt * (b1 * dz1 + b3 * dz3 + b4 * dz4 + b5 * dz5 + b6 * dz6)
    v5 = v + dt * (b1 * dv1 + b3 * dv3 + b4 * dv4 + b5 * dv5 + b6 * dv6)

    dz7, dv7 = rhs_hat_extended(
        t + dt, z5, v5, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
        w_contact, gamma_lr, lambda_lr, gamma_contact
    )

    z4s = z + dt * (b1s * dz1 + b3s * dz3 + b4s * dz4 + b5s * dz5 + b6s * dz6 + b7s * dz7)
    v4s = v + dt * (b1s * dv1 + b3s * dv3 + b4s * dv4 + b5s * dv5 + b6s * dv6 + b7s * dv7)

    ez = z5 - z4s
    ev = v5 - v4s

    sz = atol + rtol * max(abs(z), abs(z5))
    sv = atol + rtol * max(abs(v), abs(v5))
    err = np.sqrt(0.5 * ((ez / sz) ** 2 + (ev / sv) ** 2))

    return z5, v5, err


@njit(cache=True)
def demod_add_segment(X, Y, z0, z1, t0, t1, omega_ref_hat):
    """
    Trapezoidal accumulation of lock-in X/Y components over one segment.
    """
    c0 = np.cos(omega_ref_hat * t0)
    s0 = np.sin(omega_ref_hat * t0)
    c1 = np.cos(omega_ref_hat * t1)
    s1 = np.sin(omega_ref_hat * t1)

    X += 0.5 * (z0 * c0 + z1 * c1) * (t1 - t0)
    Y += 0.5 * (z0 * s0 + z1 * s1) * (t1 - t0)
    return X, Y


@njit(cache=True)
def run_one_window_rk45_extended(
    t_start,
    z_start,
    v_start,
    d_hat,
    Q,
    C1,
    C2,
    C3,
    a0,
    omega_drive_hat,
    omega_ref_hat,
    w_contact,
    gamma_lr,
    lambda_lr,
    gamma_contact,
    T_win,
    demod_dt_hat,
    rtol,
    atol,
    dt0,
    dt_min,
    dt_max,
    max_steps,
):
    """
    Integrate one demodulation window using adaptive RK45.
    """
    t = t_start
    z = z_start
    v = v_start
    t_end = t_start + T_win

    X = 0.0
    Y = 0.0

    if demod_dt_hat <= 0.0:
        demod_dt_hat = T_win

    t_s = t_start
    z_s = z_start
    next_s = t_s + demod_dt_hat

    F0 = F_DMT_smooth_hat(z + d_hat, C1, C2, a0, w_contact)
    F_int = 0.0
    F_min = F0
    F_max = F0

    safety = 0.9
    fac_min = 0.2
    fac_max = 5.0
    p_order = 5.0

    dt = dt0
    steps = 0

    while t < t_end and steps < max_steps:
        if dt < dt_min:
            dt = dt_min
        if dt > dt_max:
            dt = dt_max
        if t + dt > t_end:
            dt = t_end - t

        t_prev = t
        z_prev = z
        F_prev = F_DMT_smooth_hat(z_prev + d_hat, C1, C2, a0, w_contact)

        z_new, v_new, err = rk45_step_dopri_extended(
            t, z, v, dt, d_hat, Q, C1, C2, C3, a0, omega_drive_hat,
            w_contact, gamma_lr, lambda_lr, gamma_contact,
            rtol, atol
        )

        accept = (err <= 1.0) or (dt <= dt_min * 1.0001)
        if accept:
            t = t + dt
            z = z_new
            v = v_new

            F_cur = F_DMT_smooth_hat(z + d_hat, C1, C2, a0, w_contact)
            F_int += 0.5 * (F_prev + F_cur) * (t - t_prev)

            if F_cur < F_min:
                F_min = F_cur
            if F_cur > F_max:
                F_max = F_cur

            while next_s <= t:
                denom = t - t_prev
                if denom <= 0.0:
                    z_b = z
                else:
                    frac = (next_s - t_prev) / denom
                    if frac < 0.0:
                        frac = 0.0
                    elif frac > 1.0:
                        frac = 1.0
                    z_b = z_prev + frac * (z - z_prev)

                X, Y = demod_add_segment(X, Y, z_s, z_b, t_s, next_s, omega_ref_hat)
                t_s = next_s
                z_s = z_b
                next_s = next_s + demod_dt_hat

            steps += 1

        if err == 0.0:
            fac = fac_max
        else:
            fac = safety * (1.0 / err) ** (1.0 / p_order)
            if fac < fac_min:
                fac = fac_min
            elif fac > fac_max:
                fac = fac_max

        dt = dt * fac

    if t_end > t_s:
        X, Y = demod_add_segment(X, Y, z_s, z, t_s, t_end, omega_ref_hat)

    F_mean = F_int / T_win
    return X, Y, F_mean, F_min, F_max, steps, z, v


@njit(cache=True)
def wrap_phase_numba(phi_deg, phase_wrap_mode):
    """
    phase_wrap_mode:
        180 -> fold phase into [0, 180]
        360 -> wrap phase into [0, 360]
    """
    if phase_wrap_mode == 180:
        while phi_deg < 0.0:
            phi_deg += 180.0
        while phi_deg >= 180.0:
            phi_deg -= 180.0
        return phi_deg
    else:
        while phi_deg < 0.0:
            phi_deg += 360.0
        while phi_deg >= 360.0:
            phi_deg -= 360.0
        return phi_deg


@njit(cache=True)
def simulate_steady_state_rk45_extended(
    z0_hat,
    v0_hat,
    d_hat,
    Q,
    C1,
    C2,
    C3,
    a0,
    omega_drive_hat,
    omega_ref_hat,
    w_contact,
    gamma_lr,
    lambda_lr,
    gamma_contact,
    N_cycles,
    max_windows,
    settle_windows,
    tol_A,
    tol_phi_deg,
    consecutive,
    demod_per_ref_cycle,
    rtol,
    atol,
    dt0,
    dt_min,
    dt_max,
    max_steps_per_window,
    phase_wrap_mode,
):
    """
    Run repeated demodulation windows until amplitude/phase convergence.
    """
    T_ref = 2.0 * np.pi / omega_ref_hat
    T_win = N_cycles * T_ref

    if demod_per_ref_cycle < 5:
        demod_per_ref_cycle = 5
    demod_dt_hat = T_ref / demod_per_ref_cycle

    if phase_wrap_mode == 180:
        phase_period = 180.0
    else:
        phase_period = 360.0

    t = 0.0
    z = z0_hat
    v = v0_hat

    last_A = 1e30
    last_phi = 1e30
    stable = 0

    A_last = 0.0
    phi_last = 0.0
    F_mean_last = 0.0
    F_min_last = 0.0
    F_max_last = 0.0

    for widx in range(max_windows):
        X, Y, F_mean, F_min, F_max, _, z, v = run_one_window_rk45_extended(
            t, z, v,
            d_hat, Q, C1, C2, C3, a0,
            omega_drive_hat, omega_ref_hat,
            w_contact, gamma_lr, lambda_lr, gamma_contact,
            T_win, demod_dt_hat,
            rtol, atol, dt0, dt_min, dt_max, max_steps_per_window,
        )
        t = t + T_win

        A = (2.0 / T_win) * np.sqrt(X * X + Y * Y)
        phi = np.degrees(np.arctan2(Y, X))
        phi = wrap_phase_numba(phi, phase_wrap_mode)

        A_last = A
        phi_last = phi
        F_mean_last = F_mean
        F_min_last = F_min
        F_max_last = F_max

        if widx >= settle_windows:
            dA = abs(A - last_A)
            dphi = abs(angle_diff_period_deg_numba(phi, last_phi, phase_period))
            if dA < tol_A and dphi < tol_phi_deg:
                stable += 1
            else:
                stable = 0

            if stable >= consecutive:
                return A, phi, F_mean, F_min, F_max, (widx + 1), z, v

        last_A = A
        last_phi = phi

    return A_last, phi_last, F_mean_last, F_min_last, F_max_last, max_windows, z, v


@njit(cache=True)
def simulate_curve_rk45_extended_numba(
    d_hat_input,
    Q,
    C1,
    C2,
    C3,
    a0,
    omega_drive_hat,
    omega_ref_hat,
    d_offset_hat,
    w_contact,
    gamma_lr,
    lambda_lr,
    gamma_contact,
    N_cycles,
    max_windows,
    settle_windows,
    tol_A,
    tol_phi_deg,
    consecutive,
    demod_per_ref_cycle,
    rtol,
    atol,
    dt0,
    dt_min,
    dt_max,
    max_steps_per_window,
    phase_wrap_mode,
    use_warm_start,
):
    """
    Simulate a full approach curve using the RK45 steady-state solver.

    The returned arrays preserve input order. Internally, the solver goes
    from far to near for stable warm-starting.
    """
    n = d_hat_input.size

    A_out = np.empty(n)
    phi_out = np.empty(n)
    F_mean_out = np.empty(n)
    F_min_out = np.empty(n)
    F_max_out = np.empty(n)
    nwin_out = np.empty(n)

    order = np.argsort(d_hat_input)[::-1]

    z_cur = 0.0
    v_cur = 0.0

    for kk in range(n):
        idx = order[kk]
        d_eff = d_hat_input[idx] + d_offset_hat

        if use_warm_start == 0:
            z0 = 0.0
            v0 = 0.0
        else:
            z0 = z_cur
            v0 = v_cur

        A, phi, F_mean, F_min, F_max, nwin, z_cur, v_cur = simulate_steady_state_rk45_extended(
            z0,
            v0,
            d_eff,
            Q,
            C1,
            C2,
            C3,
            a0,
            omega_drive_hat,
            omega_ref_hat,
            w_contact,
            gamma_lr,
            lambda_lr,
            gamma_contact,
            N_cycles,
            max_windows,
            settle_windows,
            tol_A,
            tol_phi_deg,
            consecutive,
            demod_per_ref_cycle,
            rtol,
            atol,
            dt0,
            dt_min,
            dt_max,
            max_steps_per_window,
            phase_wrap_mode,
        )

        A_out[idx] = A
        phi_out[idx] = phi
        F_mean_out[idx] = F_mean
        F_min_out[idx] = F_min
        F_max_out[idx] = F_max
        nwin_out[idx] = nwin

    return A_out, phi_out, F_mean_out, F_min_out, F_max_out, nwin_out


def simulate_curve_rk45_extended_python(
    d_hat,
    C1,
    C2,
    a0,
    Q,
    C3,
    omega_drive_hat: float = 1.0,
    omega_ref_hat: Optional[float] = None,
    d_offset_hat: float = 0.0,
    w_contact: float = 0.1,
    gamma_lr: float = 1e-4,
    lambda_lr: float = 5.0,
    gamma_contact: float = 1e-3,
    N_cycles: int = 4,
    max_windows: int = 40,
    settle_windows: int = 3,
    tol_A: float = 1e-5,
    tol_phi_deg: float = 0.02,
    consecutive: int = 2,
    demod_per_ref_cycle: int = 48,
    rtol: float = 1e-6,
    atol: float = 1e-8,
    dt0: float = 0.02,
    dt_min: float = 1e-5,
    dt_max: float = 0.15,
    max_steps_per_window: int = 200000,
    phase_wrap_mode: int = 180,
    use_warm_start: bool = True,
    alpha_A: Optional[float] = None,
    alpha_phi: Optional[float] = None,
):
    """
    Python wrapper around the Numba RK45 curve simulator.
    """
    d_hat = np.asarray(d_hat, dtype=float).ravel()

    if omega_ref_hat is None:
        omega_ref_hat = omega_drive_hat

    A_sim, phi_sim, F_mean, F_min, F_max, nwin = simulate_curve_rk45_extended_numba(
        d_hat,
        float(Q),
        float(C1),
        float(C2),
        float(C3),
        float(a0),
        float(omega_drive_hat),
        float(omega_ref_hat),
        float(d_offset_hat),
        float(w_contact),
        float(gamma_lr),
        float(lambda_lr),
        float(gamma_contact),
        int(N_cycles),
        int(max_windows),
        int(settle_windows),
        float(tol_A),
        float(tol_phi_deg),
        int(consecutive),
        int(demod_per_ref_cycle),
        float(rtol),
        float(atol),
        float(dt0),
        float(dt_min),
        float(dt_max),
        int(max_steps_per_window),
        int(phase_wrap_mode),
        int(1 if use_warm_start else 0),
    )

    phase_period = 180.0 if int(phase_wrap_mode) == 180 else 360.0

    if alpha_A is not None:
        A_sim = lowpass_real_by_d(A_sim, d_hat, alpha_A)

    if alpha_phi is not None:
        phi_sim = lowpass_phase_by_d(phi_sim, d_hat, alpha_phi, period_deg=phase_period)

    return A_sim, phi_sim, F_mean, F_min, F_max, nwin


# =============================================================================
# 3. Individual FD curve fitting with RK45
# =============================================================================

def make_single_x0(
    C1: float,
    C2: float,
    a0: float,
    Q: float,
    C3: float,
    d_offset_hat: float = 0.0,
    phi_offset_deg: float = 0.0,
):
    return np.array(
        [
            np.log(C1),
            np.log(C2),
            np.log(a0),
            np.log(Q),
            np.log(C3),
            d_offset_hat,
            phi_offset_deg,
        ],
        dtype=float,
    )


def unpack_single_x(x):
    C1 = np.exp(x[0])
    C2 = np.exp(x[1])
    a0 = np.exp(x[2])
    Q = np.exp(x[3])
    C3 = np.exp(x[4])
    d_offset_hat = x[5]
    phi_offset_deg = x[6]
    return C1, C2, a0, Q, C3, d_offset_hat, phi_offset_deg


def make_single_bounds(
    x0,
    log_decades: float = 3.0,
    max_abs_d_offset_hat: float = np.inf,
    max_abs_phi_offset_deg: float = 180.0,
):
    lower = np.asarray(x0, dtype=float).copy()
    upper = np.asarray(x0, dtype=float).copy()

    lower[:5] -= log_decades * np.log(10.0)
    upper[:5] += log_decades * np.log(10.0)

    lower[5] = -max_abs_d_offset_hat
    upper[5] = +max_abs_d_offset_hat

    lower[6] = -max_abs_phi_offset_deg
    upper[6] = +max_abs_phi_offset_deg

    return lower, upper


def residual_single_curve_rk45(
    x,
    curve,
    fixed_extra=None,
    w_amp: float = 1.0,
    w_phi: float = 0.02,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    use_amp_weighted_phase: bool = True,
    sigma_phi0_deg: float = 8.0,
    A_floor_frac: float = 0.15,
    d_offset_prior_hat: Optional[float] = None,
    phi_offset_prior_deg: Optional[float] = 90.0,
    rk45_options: Optional[Dict] = None,
):
    fixed_extra = dict(fixed_extra or {})
    rk45_options = dict(rk45_options or {})

    C1, C2, a0, Q, C3, d_offset_hat, phi_offset_deg = unpack_single_x(x)

    omega_drive = curve.get("omega_drive_hat", 1.0) * fixed_extra.get("omega_scale", 1.0)
    omega_ref = curve.get("omega_ref_hat", omega_drive)

    A_sim, phi_sim, *_ = simulate_curve_rk45_extended_python(
        curve["d_hat"],
        C1=C1,
        C2=C2,
        a0=a0,
        Q=Q,
        C3=C3,
        omega_drive_hat=omega_drive,
        omega_ref_hat=omega_ref,
        d_offset_hat=d_offset_hat,
        w_contact=fixed_extra.get("w_contact", 0.1),
        gamma_lr=fixed_extra.get("gamma_lr", 1e-4),
        lambda_lr=fixed_extra.get("lambda_lr", 5.0),
        gamma_contact=fixed_extra.get("gamma_contact", 1e-3),
        **rk45_options,
    )

    A_exp = curve["A_hat"]
    phi_exp = curve["phi_deg"]
    A0 = float(curve["A0_hat"])

    res_A = w_amp * (A_sim - A_exp) / A0

    phi_use = transform_phase_deg(phi_sim, mode=phase_mode)

    if far_field_phase_align:
        phi_auto = estimate_phase_offset_far_field(
            phi_use, phi_exp, curve["d_hat"], frac=far_field_frac, period_deg=phase_period_deg
        )
    else:
        phi_auto = 0.0

    phi_use = phi_use + phi_auto + phi_offset_deg
    dphi = angle_diff_period_deg(phi_use, phi_exp, period_deg=phase_period_deg)

    if use_amp_weighted_phase:
        A_floor = A_floor_frac * A0
        sigma_phi = sigma_phi0_deg * A0 / np.maximum(np.abs(A_exp), A_floor)
        res_phi = w_phi * dphi / sigma_phi
    else:
        res_phi = w_phi * dphi / phase_period_deg

    residuals = [res_A.ravel(), res_phi.ravel()]

    if d_offset_prior_hat is not None and np.isfinite(d_offset_prior_hat):
        residuals.append(np.array([d_offset_hat / d_offset_prior_hat]))

    if phi_offset_prior_deg is not None and np.isfinite(phi_offset_prior_deg):
        residuals.append(np.array([phi_offset_deg / phi_offset_prior_deg]))

    return np.concatenate(residuals)


def fit_one_fd_curve_rk45(
    curve,
    x0,
    bounds=None,
    fixed_extra=None,
    w_amp: float = 1.0,
    w_phi: float = 0.02,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    use_amp_weighted_phase: bool = True,
    sigma_phi0_deg: float = 8.0,
    A_floor_frac: float = 0.15,
    d_offset_prior_hat: Optional[float] = None,
    phi_offset_prior_deg: Optional[float] = 90.0,
    rk45_options: Optional[Dict] = None,
    max_nfev: int = 150,
    verbose: int = 0,
):
    if bounds is None:
        bounds = make_single_bounds(x0)

    result = least_squares(
        residual_single_curve_rk45,
        x0,
        bounds=bounds,
        args=(curve,),
        kwargs=dict(
            fixed_extra=fixed_extra,
            w_amp=w_amp,
            w_phi=w_phi,
            phase_mode=phase_mode,
            far_field_phase_align=far_field_phase_align,
            far_field_frac=far_field_frac,
            phase_period_deg=phase_period_deg,
            use_amp_weighted_phase=use_amp_weighted_phase,
            sigma_phi0_deg=sigma_phi0_deg,
            A_floor_frac=A_floor_frac,
            d_offset_prior_hat=d_offset_prior_hat,
            phi_offset_prior_deg=phi_offset_prior_deg,
            rk45_options=rk45_options,
        ),
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=max_nfev,
        verbose=verbose,
    )

    C1, C2, a0, Q, C3, d_offset_hat, phi_offset_deg = unpack_single_x(result.x)

    return {
        "drive_nm": curve["drive_nm"],
        "success": result.success,
        "cost": result.cost,
        "x": result.x,
        "result": result,
        "C1": C1,
        "C2": C2,
        "a0": a0,
        "Q": Q,
        "C3": C3,
        "d_offset_hat": d_offset_hat,
        "phi_offset_deg": phi_offset_deg,
    }


def fit_individual_fd_curves_rk45(
    curves: List[Dict],
    C1_init: float,
    C2_init: float,
    a0_init: float,
    Q_init: float,
    C3_init_mode: str = "from_A0_over_Q",
    C3_init_value: Optional[float] = None,
    conv_L: float = 1.0,
    fixed_extra: Optional[Dict] = None,
    log_decades: float = 3.0,
    max_abs_d_offset_nm: float = 5.0,
    max_abs_phi_offset_deg: float = 180.0,
    w_amp: float = 1.0,
    w_phi: float = 0.02,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    use_amp_weighted_phase: bool = True,
    sigma_phi0_deg: float = 8.0,
    A_floor_frac: float = 0.15,
    rk45_options: Optional[Dict] = None,
    max_nfev: int = 150,
    verbose: bool = True,
):
    """
    Fit each drive independently using the RK45 extended solver.

    This is mainly diagnostic. For physical interpretation, prefer the global
    fit with shared C1, C2, a0, Q and smooth C3(drive).
    """
    fits = []

    for j, curve in enumerate(curves):
        if C3_init_value is not None:
            C3_init = C3_init_value
        elif C3_init_mode == "from_A0_over_Q":
            C3_init = max(curve["A0_hat"] / Q_init, 1e-15)
        elif C3_init_mode == "from_drive_over_Q":
            C3_init = max(curve["drive_nm"] * conv_L / Q_init, 1e-15)
        else:
            raise ValueError("Unknown C3_init_mode.")

        x0 = make_single_x0(
            C1=C1_init,
            C2=C2_init,
            a0=a0_init,
            Q=Q_init,
            C3=C3_init,
        )

        bounds = make_single_bounds(
            x0,
            log_decades=log_decades,
            max_abs_d_offset_hat=max_abs_d_offset_nm * conv_L,
            max_abs_phi_offset_deg=max_abs_phi_offset_deg,
        )

        fit = fit_one_fd_curve_rk45(
            curve,
            x0,
            bounds=bounds,
            fixed_extra=fixed_extra,
            w_amp=w_amp,
            w_phi=w_phi,
            phase_mode=phase_mode,
            far_field_phase_align=far_field_phase_align,
            far_field_frac=far_field_frac,
            phase_period_deg=phase_period_deg,
            use_amp_weighted_phase=use_amp_weighted_phase,
            sigma_phi0_deg=sigma_phi0_deg,
            A_floor_frac=A_floor_frac,
            d_offset_prior_hat=2.0 * conv_L,
            phi_offset_prior_deg=90.0,
            rk45_options=rk45_options,
            max_nfev=max_nfev,
            verbose=0,
        )

        fits.append(fit)

        if verbose:
            print(
                f"[{j+1:02d}/{len(curves):02d}] "
                f"drive={fit['drive_nm']:.4g}, "
                f"cost={fit['cost']:.4g}, "
                f"C1={fit['C1']:.3e}, C2={fit['C2']:.3e}, "
                f"a0={fit['a0']:.3e}, Q={fit['Q']:.3e}, "
                f"C3={fit['C3']:.3e}"
            )

    return fits


# =============================================================================
# 4. Global shared-physics fit with smooth C3(drive)
# =============================================================================

def normalized_log_drive(drives):
    drives = np.asarray(drives, dtype=float)
    u = np.log(np.maximum(drives, 1e-300))
    s = np.std(u)
    if s == 0:
        return np.zeros_like(u)
    return (u - np.mean(u)) / s


def initialize_extended_global_x_from_individual_fits(
    curves,
    individual_fits,
    conv_L: float = 1.0,
    w_contact_init_nm: float = 0.2,
    gamma_lr_init: float = 1e-4,
    lambda_lr_init_nm: float = 5.0,
    gamma_contact_init: float = 1e-3,
    domega_init: float = 0.0,
):
    """
    x =
        log_C1, log_C2, log_a0, log_Q,
        log_gamma_C3, b1, b2,
        log_w_contact, log_gamma_lr, log_lambda_lr, log_gamma_contact,
        domega,
        d_offset_0 ... d_offset_n-1,
        phi_offset_0 ... phi_offset_n-1
    """
    n = len(curves)

    log_C1_0 = np.median(np.log([f["C1"] for f in individual_fits]))
    log_C2_0 = np.median(np.log([f["C2"] for f in individual_fits]))
    log_a0_0 = np.median(np.log([f["a0"] for f in individual_fits]))
    log_Q_0 = np.median(np.log([f["Q"] for f in individual_fits]))

    drives_nm = np.array([c["drive_nm"] for c in curves], dtype=float)
    drive_scale = np.array(
        [c.get("A0_hat", c["drive_nm"] * conv_L) for c in curves],
        dtype=float,
    )
    u = normalized_log_drive(drives_nm)

    C3_ind = np.array([f["C3"] for f in individual_fits], dtype=float)

    y = np.log(np.maximum(C3_ind, 1e-300)) - np.log(np.maximum(drive_scale, 1e-300))
    X = np.column_stack([np.ones_like(u), u, u**2])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)

    log_gamma_0, b1_0, b2_0 = coef

    w_contact_init = max(w_contact_init_nm * conv_L, 1e-12)
    lambda_lr_init = max(lambda_lr_init_nm * conv_L, 1e-12)

    d_offsets_0 = np.array([f.get("d_offset_hat", 0.0) for f in individual_fits], dtype=float)

    # We use automatic far-field phase alignment, so keep extra phase offsets small initially.
    phi_offsets_0 = np.zeros(n, dtype=float)

    x0 = np.concatenate(
        [
            np.array(
                [
                    log_C1_0,
                    log_C2_0,
                    log_a0_0,
                    log_Q_0,
                    log_gamma_0,
                    b1_0,
                    b2_0,
                    np.log(w_contact_init),
                    np.log(gamma_lr_init),
                    np.log(lambda_lr_init),
                    np.log(gamma_contact_init),
                    domega_init,
                ],
                dtype=float,
            ),
            d_offsets_0,
            phi_offsets_0,
        ]
    )

    return x0


def unpack_extended_global_x(x, curves, conv_L: float = 1.0):
    n = len(curves)

    log_C1, log_C2, log_a0, log_Q = x[:4]
    log_gamma, b1, b2 = x[4:7]

    log_w_contact = x[7]
    log_gamma_lr = x[8]
    log_lambda_lr = x[9]
    log_gamma_contact = x[10]
    domega = x[11]

    d0 = 12
    d1 = d0 + n
    p0 = d1
    p1 = p0 + n

    d_offsets = x[d0:d1]
    phi_offsets = x[p0:p1]

    drives_nm = np.array([c["drive_nm"] for c in curves], dtype=float)
    drive_scale = np.array(
        [c.get("A0_hat", c["drive_nm"] * conv_L) for c in curves],
        dtype=float,
    )
    u = normalized_log_drive(drives_nm)

    C1 = np.exp(log_C1)
    C2 = np.exp(log_C2)
    a0 = np.exp(log_a0)
    Q = np.exp(log_Q)

    C3_all = np.exp(log_gamma) * drive_scale * np.exp(b1 * u + b2 * u**2)

    w_contact = np.exp(log_w_contact)
    gamma_lr = np.exp(log_gamma_lr)
    lambda_lr = np.exp(log_lambda_lr)
    gamma_contact = np.exp(log_gamma_contact)

    return {
        "C1": C1,
        "C2": C2,
        "a0": a0,
        "Q": Q,
        "C3_all": C3_all,
        "w_contact": w_contact,
        "gamma_lr": gamma_lr,
        "lambda_lr": lambda_lr,
        "gamma_contact": gamma_contact,
        "domega": domega,
        "d_offsets_hat": d_offsets,
        "phi_offsets_deg": phi_offsets,
        "drives_nm": drives_nm,
    }


def make_extended_global_bounds(
    x0,
    n_curves: int,
    conv_L: float = 1.0,
    log_decades_physics: float = 2.0,
    log_decades_C3: float = 3.0,
    log_decades_damping: float = 4.0,
    max_abs_beta: float = 4.0,
    max_abs_d_offset_nm: float = 5.0,
    max_abs_phi_offset_deg: float = 180.0,
    domega_bounds: Tuple[float, float] = (-0.03, 0.03),
):
    lower = np.asarray(x0, dtype=float).copy()
    upper = np.asarray(x0, dtype=float).copy()

    # shared log C1, C2, a0, Q
    lower[:4] -= log_decades_physics * np.log(10.0)
    upper[:4] += log_decades_physics * np.log(10.0)

    # log_gamma_C3
    lower[4] -= log_decades_C3 * np.log(10.0)
    upper[4] += log_decades_C3 * np.log(10.0)

    # b1, b2 for smooth C3(drive)
    lower[5] = -max_abs_beta
    upper[5] = +max_abs_beta
    lower[6] = -max_abs_beta
    upper[6] = +max_abs_beta

    # w_contact, gamma_lr, lambda_lr, gamma_contact
    lower[7:11] -= log_decades_damping * np.log(10.0)
    upper[7:11] += log_decades_damping * np.log(10.0)

    # global frequency detuning
    lower[11] = domega_bounds[0]
    upper[11] = domega_bounds[1]

    # per-curve distance offsets
    d0 = 12
    d1 = d0 + n_curves
    lower[d0:d1] = -max_abs_d_offset_nm * conv_L
    upper[d0:d1] = +max_abs_d_offset_nm * conv_L

    # per-curve phase offsets
    p0 = d1
    p1 = p0 + n_curves
    lower[p0:p1] = -max_abs_phi_offset_deg
    upper[p0:p1] = +max_abs_phi_offset_deg

    return lower, upper


def residual_extended_global_C3_rk45(
    x,
    curves,
    conv_L: float = 1.0,
    w_amp: float = 1.0,
    w_phi: float = 0.02,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    use_amp_weighted_phase: bool = True,
    sigma_phi0_deg: float = 8.0,
    A_floor_frac: float = 0.15,
    rk45_options: Optional[Dict] = None,
    d_offset_prior_nm: Optional[float] = 2.0,
    phi_offset_prior_deg: Optional[float] = 90.0,
    beta_prior: Optional[float] = 2.0,
    damping_log_prior: Optional[float] = 3.0,
):
    p = unpack_extended_global_x(x, curves, conv_L=conv_L)
    rk45_options = dict(rk45_options or {})

    residuals = []

    omega_base = 1.0 + p["domega"]
    if omega_base <= 0:
        return np.ones(100) * 1e6

    for j, curve in enumerate(curves):
        omega_drive = omega_base * curve.get("omega_drive_hat", 1.0)
        omega_ref = curve.get("omega_ref_hat", omega_drive)

        A_sim, phi_sim, *_ = simulate_curve_rk45_extended_python(
            curve["d_hat"],
            C1=p["C1"],
            C2=p["C2"],
            a0=p["a0"],
            Q=p["Q"],
            C3=p["C3_all"][j],
            omega_drive_hat=omega_drive,
            omega_ref_hat=omega_ref,
            d_offset_hat=p["d_offsets_hat"][j],
            w_contact=p["w_contact"],
            gamma_lr=p["gamma_lr"],
            lambda_lr=p["lambda_lr"],
            gamma_contact=p["gamma_contact"],
            **rk45_options,
        )

        A_exp = curve["A_hat"]
        phi_exp = curve["phi_deg"]
        A0 = float(curve["A0_hat"])

        # Amplitude residual
        residuals.append(w_amp * (A_sim - A_exp) / A0)

        # Phase convention transform
        phi_use = transform_phase_deg(phi_sim, mode=phase_mode)

        # Automatic far-field phase alignment
        if far_field_phase_align:
            phi_auto = estimate_phase_offset_far_field(
                phi_use,
                phi_exp,
                curve["d_hat"],
                frac=far_field_frac,
                period_deg=phase_period_deg,
            )
        else:
            phi_auto = 0.0

        # Extra optimized per-curve offset
        phi_use = phi_use + phi_auto + p["phi_offsets_deg"][j]
        dphi = angle_diff_period_deg(phi_use, phi_exp, period_deg=phase_period_deg)

        if use_amp_weighted_phase:
            A_floor = A_floor_frac * A0
            sigma_phi = sigma_phi0_deg * A0 / np.maximum(np.abs(A_exp), A_floor)
            residuals.append(w_phi * dphi / sigma_phi)
        else:
            residuals.append(w_phi * dphi / phase_period_deg)

    # Regularization
    if d_offset_prior_nm is not None:
        residuals.append(p["d_offsets_hat"] / (d_offset_prior_nm * conv_L))

    if phi_offset_prior_deg is not None:
        residuals.append(p["phi_offsets_deg"] / phi_offset_prior_deg)

    if beta_prior is not None:
        # Avoid unnecessary curvature in C3(drive)
        residuals.append(np.array([x[5] / beta_prior, x[6] / beta_prior]))

    if damping_log_prior is not None:
        # Weakly discourage huge damping unless phase requires it.
        residuals.append(
            np.array(
                [
                    x[8] / damping_log_prior,   # log_gamma_lr
                    x[10] / damping_log_prior,  # log_gamma_contact
                ]
            )
        )

    return np.concatenate([np.ravel(r) for r in residuals])


def compute_auto_phase_offsets_at_solution_rk45(
    global_fit,
    curves,
    phase_mode: str = "raw",
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    rk45_options: Optional[Dict] = None,
):
    rk45_options = dict(rk45_options or {})
    auto_offsets = []

    omega_base = 1.0 + global_fit["domega"]

    for j, curve in enumerate(curves):
        omega_drive = omega_base * curve.get("omega_drive_hat", 1.0)
        omega_ref = curve.get("omega_ref_hat", omega_drive)

        A_sim, phi_sim, *_ = simulate_curve_rk45_extended_python(
            curve["d_hat"],
            C1=global_fit["C1"],
            C2=global_fit["C2"],
            a0=global_fit["a0"],
            Q=global_fit["Q"],
            C3=global_fit["C3_all"][j],
            omega_drive_hat=omega_drive,
            omega_ref_hat=omega_ref,
            d_offset_hat=global_fit["d_offsets_hat"][j],
            w_contact=global_fit["w_contact"],
            gamma_lr=global_fit["gamma_lr"],
            lambda_lr=global_fit["lambda_lr"],
            gamma_contact=global_fit["gamma_contact"],
            **rk45_options,
        )

        phi_use = transform_phase_deg(phi_sim, mode=phase_mode)
        phi_auto = estimate_phase_offset_far_field(
            phi_use,
            curve["phi_deg"],
            curve["d_hat"],
            frac=far_field_frac,
            period_deg=phase_period_deg,
        )
        auto_offsets.append(phi_auto)

    return np.asarray(auto_offsets, dtype=float)


def fit_global_drive_dependent_C3_extended_rk45(
    curves,
    individual_fits,
    conv_L: float = 1.0,
    w_amp: float = 1.0,
    w_phi: float = 0.02,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    use_amp_weighted_phase: bool = True,
    sigma_phi0_deg: float = 8.0,
    A_floor_frac: float = 0.15,
    rk45_options: Optional[Dict] = None,
    max_nfev: int = 300,
    verbose: int = 2,
    log_decades_physics: float = 2.0,
    log_decades_C3: float = 3.0,
    log_decades_damping: float = 4.0,
    max_abs_d_offset_nm: float = 5.0,
    max_abs_phi_offset_deg: float = 180.0,
    domega_bounds: Tuple[float, float] = (-0.03, 0.03),
):
    """
    Global fit using:
        shared: C1, C2, a0, Q, w_contact, gamma_lr, lambda_lr, gamma_contact, domega
        drive-dependent: smooth C3(drive)
        per curve: d_offset_j, phi_offset_j
    """
    x0 = initialize_extended_global_x_from_individual_fits(
        curves,
        individual_fits,
        conv_L=conv_L,
    )

    bounds = make_extended_global_bounds(
        x0,
        n_curves=len(curves),
        conv_L=conv_L,
        log_decades_physics=log_decades_physics,
        log_decades_C3=log_decades_C3,
        log_decades_damping=log_decades_damping,
        max_abs_d_offset_nm=max_abs_d_offset_nm,
        max_abs_phi_offset_deg=max_abs_phi_offset_deg,
        domega_bounds=domega_bounds,
    )

    result = least_squares(
        residual_extended_global_C3_rk45,
        x0,
        bounds=bounds,
        args=(curves,),
        kwargs=dict(
            conv_L=conv_L,
            w_amp=w_amp,
            w_phi=w_phi,
            phase_mode=phase_mode,
            far_field_phase_align=far_field_phase_align,
            far_field_frac=far_field_frac,
            phase_period_deg=phase_period_deg,
            use_amp_weighted_phase=use_amp_weighted_phase,
            sigma_phi0_deg=sigma_phi0_deg,
            A_floor_frac=A_floor_frac,
            rk45_options=rk45_options,
        ),
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=max_nfev,
        verbose=verbose,
    )

    p = unpack_extended_global_x(result.x, curves, conv_L=conv_L)
    p["success"] = result.success
    p["cost"] = result.cost
    p["x"] = result.x
    p["result"] = result
    p["phase_mode"] = phase_mode
    p["phase_period_deg"] = phase_period_deg

    p["phase_auto_offsets_deg"] = compute_auto_phase_offsets_at_solution_rk45(
        p,
        curves,
        phase_mode=phase_mode,
        far_field_frac=far_field_frac,
        phase_period_deg=phase_period_deg,
        rk45_options=rk45_options,
    )

    return p


# =============================================================================
# 5. Plotting
# =============================================================================

def plot_individual_parameter_trends(individual_fits):
    drives = np.array([f["drive_nm"] for f in individual_fits])
    keys = ["C1", "C2", "a0", "Q", "C3"]

    fig, ax = plt.subplots(1, len(keys), figsize=(3.2 * len(keys), 3.0))

    for k, key in enumerate(keys):
        y = np.array([f[key] for f in individual_fits])
        ax[k].plot(drives, y, "o-")
        ax[k].set_xlabel("Drive amplitude")
        ax[k].set_title(key)
        ax[k].set_yscale("log")

    plt.tight_layout()
    return fig, ax


def plot_one_fit_overlay_rk45(
    curve,
    fit,
    conv_L: float = 1.0,
    fixed_extra: Optional[Dict] = None,
    phase_mode: str = "raw",
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: float = 180.0,
    rk45_options: Optional[Dict] = None,
):
    fixed_extra = dict(fixed_extra or {})
    rk45_options = dict(rk45_options or {})

    omega_drive = curve.get("omega_drive_hat", 1.0) * fixed_extra.get("omega_scale", 1.0)
    omega_ref = curve.get("omega_ref_hat", omega_drive)

    A_sim, phi_sim, *_ = simulate_curve_rk45_extended_python(
        curve["d_hat"],
        C1=fit["C1"],
        C2=fit["C2"],
        a0=fit["a0"],
        Q=fit["Q"],
        C3=fit["C3"],
        omega_drive_hat=omega_drive,
        omega_ref_hat=omega_ref,
        d_offset_hat=fit.get("d_offset_hat", 0.0),
        w_contact=fixed_extra.get("w_contact", 0.1),
        gamma_lr=fixed_extra.get("gamma_lr", 1e-4),
        lambda_lr=fixed_extra.get("lambda_lr", 5.0),
        gamma_contact=fixed_extra.get("gamma_contact", 1e-3),
        **rk45_options,
    )

    phi_use = transform_phase_deg(phi_sim, mode=phase_mode)
    if far_field_phase_align:
        phi_auto = estimate_phase_offset_far_field(
            phi_use, curve["phi_deg"], curve["d_hat"], frac=far_field_frac,
            period_deg=phase_period_deg
        )
    else:
        phi_auto = 0.0

    phi_use = phi_use + phi_auto + fit.get("phi_offset_deg", 0.0)

    d_nm = curve["d_hat"] / conv_L

    fig, ax = plt.subplots(1, 2, figsize=(8.5, 3.4))

    ax[0].plot(d_nm, curve["A_hat"] / conv_L, "o", ms=4, label="exp")
    ax[0].plot(d_nm, A_sim / conv_L, "-", lw=2, label="fit")
    ax[0].set_xlabel("Height (nm)")
    ax[0].set_ylabel("Amplitude (nm)")
    ax[0].set_title(f"Drive = {curve['drive_nm']:.4g}")
    ax[0].legend()

    ax[1].plot(d_nm, curve["phi_deg"], "o", ms=4, label="exp")
    ax[1].plot(d_nm, phi_use, "-", lw=2, label="fit + phase offset")
    ax[1].set_xlabel("Height (nm)")
    ax[1].set_ylabel("Phase (deg)")
    ax[1].legend()

    plt.tight_layout()
    print(f"auto phase offset = {phi_auto:.3f} deg")
    return fig, ax


def plot_global_fit_overlays_rk45(
    curves,
    global_fit,
    conv_L: float = 1.0,
    phase_mode: Optional[str] = None,
    far_field_phase_align: bool = True,
    far_field_frac: float = 0.15,
    phase_period_deg: Optional[float] = None,
    rk45_options: Optional[Dict] = None,
):
    rk45_options = dict(rk45_options or {})

    if phase_mode is None:
        phase_mode = global_fit.get("phase_mode", "raw")

    if phase_period_deg is None:
        phase_period_deg = global_fit.get("phase_period_deg", 180.0)

    omega_base = 1.0 + global_fit["domega"]

    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))

    for j, curve in enumerate(curves):
        omega_drive = omega_base * curve.get("omega_drive_hat", 1.0)
        omega_ref = curve.get("omega_ref_hat", omega_drive)

        A_sim, phi_sim, *_ = simulate_curve_rk45_extended_python(
            curve["d_hat"],
            C1=global_fit["C1"],
            C2=global_fit["C2"],
            a0=global_fit["a0"],
            Q=global_fit["Q"],
            C3=global_fit["C3_all"][j],
            omega_drive_hat=omega_drive,
            omega_ref_hat=omega_ref,
            d_offset_hat=global_fit["d_offsets_hat"][j],
            w_contact=global_fit["w_contact"],
            gamma_lr=global_fit["gamma_lr"],
            lambda_lr=global_fit["lambda_lr"],
            gamma_contact=global_fit["gamma_contact"],
            **rk45_options,
        )

        d_nm = curve["d_hat"] / conv_L
        phi_use = transform_phase_deg(phi_sim, mode=phase_mode)

        if far_field_phase_align:
            if "phase_auto_offsets_deg" in global_fit:
                phi_auto = global_fit["phase_auto_offsets_deg"][j]
            else:
                phi_auto = estimate_phase_offset_far_field(
                    phi_use, curve["phi_deg"], curve["d_hat"],
                    frac=far_field_frac, period_deg=phase_period_deg
                )
        else:
            phi_auto = 0.0

        phi_use = phi_use + phi_auto + global_fit["phi_offsets_deg"][j]

        ax[0].plot(d_nm, curve["A_hat"] / conv_L, "o", ms=3, alpha=0.45)
        ax[0].plot(d_nm, A_sim / conv_L, "-", lw=1.5)

        ax[1].plot(d_nm, curve["phi_deg"], "o", ms=3, alpha=0.45)
        ax[1].plot(d_nm, phi_use, "-", lw=1.5)

    ax[0].set_xlabel("Height (nm)")
    ax[0].set_ylabel("Amplitude (nm)")
    ax[0].set_title("RK45 extended global fit: amplitude")

    ax[1].set_xlabel("Height (nm)")
    ax[1].set_ylabel("Phase (deg)")
    ax[1].set_title("RK45 extended global fit: phase + offset correction")

    plt.tight_layout()
    return fig, ax


def plot_C3_drive_dependence(global_fit, individual_fits=None):
    drives = global_fit["drives_nm"]
    C3 = global_fit["C3_all"]

    fig, ax = plt.subplots(figsize=(4.8, 3.5))

    if individual_fits is not None:
        drives_ind = np.array([f["drive_nm"] for f in individual_fits])
        C3_ind = np.array([f["C3"] for f in individual_fits])
        ax.plot(drives_ind, C3_ind, "o", label="individual C3")

    ax.plot(drives, C3, "s-", label="global smooth C3(drive)")
    ax.set_xlabel("Drive amplitude")
    ax.set_ylabel("C3")
    ax.set_yscale("log")
    ax.legend()
    plt.tight_layout()

    return fig, ax


def plot_phase_offsets(global_fit):
    drives = global_fit["drives_nm"]

    auto = global_fit.get("phase_auto_offsets_deg", np.zeros_like(drives))
    extra = global_fit["phi_offsets_deg"]
    total = auto + extra

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(drives, auto, "o-", label="far-field auto offset")
    ax.plot(drives, extra, "s-", label="fitted extra offset")
    ax.plot(drives, total, "^-", label="total offset")
    ax.axhline(0, color="k", lw=0.8, alpha=0.4)
    ax.set_xlabel("Drive amplitude")
    ax.set_ylabel("Phase offset (deg)")
    ax.legend()
    plt.tight_layout()

    return fig, ax


# =============================================================================
# 6. Recommended usage
# =============================================================================

if __name__ == "__main__":
    print(
        "This file defines RK45-based SPM FD calibration functions.\n"
        "Import it into your notebook/script and run the example below with your data.\n"
    )

    example = r"""
# -------------------------------------------------------------------------
# Example usage
# -------------------------------------------------------------------------

from spm_fd_rk45_extended_calibration import *

# Build curves from arrays:
# curves = build_measured_fd_curves(
#     drives_nm=drive,
#     height_nm=height,
#     amplitude_nm=amp,
#     phase_deg=phase,
#     conv_L=conv_L,
#     A0_method="far_field_median",
#     far_field_frac=0.10,
#     omega_drive_hat=1.0,
#     omega_ref_hat=1.0,
# )

# Or from a measured_fd dictionary:
# curves = build_measured_fd_curves_from_dict(
#     measured_fd,
#     conv_L=conv_L,
#     A0_method="far_field_median",
#     far_field_frac=0.10,
#     omega_drive_hat=1.0,
#     omega_ref_hat=1.0,
# )

# RK45 options. Start coarse for fitting, then use stricter settings for plotting.
rk45_fit_options = dict(
    N_cycles=3,
    max_windows=30,
    settle_windows=3,
    tol_A=1e-4,
    tol_phi_deg=0.05,
    consecutive=2,
    demod_per_ref_cycle=32,
    rtol=1e-5,
    atol=1e-7,
    dt0=0.03,
    dt_min=1e-5,
    dt_max=0.20,
    max_steps_per_window=150000,
    phase_wrap_mode=180,      # matches the uploaded RK45 style
    use_warm_start=True,
    alpha_A=None,
    alpha_phi=None,
)

rk45_plot_options = dict(
    N_cycles=4,
    max_windows=50,
    settle_windows=4,
    tol_A=3e-5,
    tol_phi_deg=0.02,
    consecutive=2,
    demod_per_ref_cycle=48,
    rtol=3e-6,
    atol=1e-8,
    dt0=0.02,
    dt_min=1e-5,
    dt_max=0.15,
    max_steps_per_window=250000,
    phase_wrap_mode=180,
    use_warm_start=True,
    alpha_A=None,
    alpha_phi=None,
)

# Initial guesses. Adjust these to your normalized units.
C1_init = 1e-3
C2_init = 1e-2
a0_init = 0.1
Q_init  = 80.0

# Fixed extra physics for individual diagnostic fits.
# The global fit will refine these shared damping parameters.
fixed_extra = dict(
    w_contact=0.2 * conv_L,
    gamma_lr=1e-4,
    lambda_lr=5.0 * conv_L,
    gamma_contact=1e-3,
    omega_scale=1.0,
)

# -------------------------------------------------------------------------
# Step 1: individual RK45 FD fits
# -------------------------------------------------------------------------
individual_fits = fit_individual_fd_curves_rk45(
    curves,
    C1_init=C1_init,
    C2_init=C2_init,
    a0_init=a0_init,
    Q_init=Q_init,
    C3_init_mode="from_A0_over_Q",
    conv_L=conv_L,
    fixed_extra=fixed_extra,
    log_decades=3.0,
    max_abs_d_offset_nm=5.0,
    max_abs_phi_offset_deg=180.0,
    w_amp=1.0,
    w_phi=0.01,                  # keep small until phase convention is stable
    phase_mode="raw",
    far_field_phase_align=True,
    far_field_frac=0.15,
    phase_period_deg=180.0,      # use 360.0 if your phase is not folded
    use_amp_weighted_phase=True,
    sigma_phi0_deg=8.0,
    A_floor_frac=0.15,
    rk45_options=rk45_fit_options,
    max_nfev=100,
    verbose=True,
)

plot_individual_parameter_trends(individual_fits)

# Inspect one curve
# plot_one_fit_overlay_rk45(
#     curves[0],
#     individual_fits[0],
#     conv_L=conv_L,
#     fixed_extra=fixed_extra,
#     phase_mode="raw",
#     far_field_phase_align=True,
#     phase_period_deg=180.0,
#     rk45_options=rk45_plot_options,
# )

# -------------------------------------------------------------------------
# Step 2: global shared-physics fit with smooth C3(drive)
# -------------------------------------------------------------------------
global_fit = fit_global_drive_dependent_C3_extended_rk45(
    curves,
    individual_fits,
    conv_L=conv_L,

    w_amp=1.0,
    w_phi=0.02,

    phase_mode="raw",            # try "minus_from_180" or "minus_from_360" if needed
    far_field_phase_align=True,
    far_field_frac=0.15,
    phase_period_deg=180.0,
    use_amp_weighted_phase=True,
    sigma_phi0_deg=8.0,
    A_floor_frac=0.15,

    rk45_options=rk45_fit_options,
    max_nfev=300,
    verbose=2,

    log_decades_physics=2.0,
    log_decades_C3=3.0,
    log_decades_damping=4.0,
    max_abs_d_offset_nm=5.0,
    max_abs_phi_offset_deg=180.0,
    domega_bounds=(-0.03, 0.03),
)

print("RK45 extended global shared parameters:")
print("C1             =", global_fit["C1"])
print("C2             =", global_fit["C2"])
print("a0             =", global_fit["a0"])
print("Q              =", global_fit["Q"])
print("w_contact      =", global_fit["w_contact"])
print("gamma_lr       =", global_fit["gamma_lr"])
print("lambda_lr      =", global_fit["lambda_lr"])
print("gamma_contact  =", global_fit["gamma_contact"])
print("domega         =", global_fit["domega"])

plot_global_fit_overlays_rk45(
    curves,
    global_fit,
    conv_L=conv_L,
    rk45_options=rk45_plot_options,
)

plot_C3_drive_dependence(global_fit, individual_fits)
plot_phase_offsets(global_fit)
"""
    print(example)
