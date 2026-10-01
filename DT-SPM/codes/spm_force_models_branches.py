"""
spm_force_models_branches.py

Companion module to `spm_fd_rk45_extended_calibration.py` that adds:

    1.  A *registry of force models* (DMT, Hertz, Lennard-Jones, Morse,
        JKR-like adhesion, capillary bridge) sharing the same numba RK45 +
        windowed lock-in machinery.  Selection is done via a single integer
        `model_id` so all force evaluations live inside one njit function and
        the hot loop is not duplicated per model.

    2.  An *automatic force-model selector* that fits each candidate model to
        a measured approach (and optional retract) FD curve and ranks them by
        corrected Akaike information (AICc) plus physical signatures
        (hysteresis area, pull-off force, attraction-decay shape).

    3.  An *all-stable-branches solver*: at each tip-sample distance, run the
        steady-state oscillator from several initial conditions, cluster the
        converged (A, phi) endpoints, verify each by perturb-and-reconverge,
        and stitch branches across distance to identify the attractive and
        repulsive branches and any third (rare) branch.

Design
------
* The unified force function `F_unified(delta, model_id, p, w)` takes a length-7
  parameter vector `p` whose meaning depends on `model_id` (see
  `FORCE_PARAM_SCHEMA`).  This avoids duplicating the RK45 stepper per model.
* The unified RK45/demod/steady-state machinery is implemented locally for
  numba friendliness, mirroring the structure of the existing module.
* The selector reuses scipy.optimize.least_squares with a small per-model
  parameter wrapper.

Conventions
-----------
* `delta > 0` is the non-contact gap, `delta < 0` is indentation (same as
  the existing module).
* All quantities are in normalised (hat) units.  Convert nm <-> hat with the
  same `conv_L` you already use.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from numba import njit
    _HAS_NUMBA = True
except ImportError:  # pragma: no cover
    _HAS_NUMBA = False

    def njit(*args, **kwargs):  # type: ignore
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def deco(f):
            return f
        return deco

try:
    from scipy.optimize import least_squares
    from scipy.cluster.hierarchy import fcluster, linkage
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    _HAS_SCIPY = False


# =============================================================================
# 1.  Force-model registry
# =============================================================================
#
# Each model has a stable integer id used by the numba dispatcher and a small
# schema documenting which entries of the parameter vector are used.  The
# dispatcher always receives a length-7 vector; entries marked "_" are
# ignored.

DMT_ID       = 0
HERTZ_ID     = 1
LJ_ID        = 2
MORSE_ID     = 3
JKR_ID       = 4
CAPILLARY_ID = 5

FORCE_MODELS: Dict[str, int] = {
    "dmt":       DMT_ID,
    "hertz":     HERTZ_ID,
    "lj":        LJ_ID,
    "morse":     MORSE_ID,
    "jkr":       JKR_ID,
    "capillary": CAPILLARY_ID,
}

# Parameter-slot meanings per model.  Used by selector + plotter, not by JIT.
FORCE_PARAM_SCHEMA: Dict[str, List[str]] = {
    "dmt":       ["C1", "C2", "a0", "_", "_", "_", "_"],
    "hertz":     ["_",  "C2", "_",  "_", "_", "_", "_"],
    "lj":        ["eps", "_", "sigma", "_", "_", "_", "_"],
    "morse":     ["De", "a_morse", "r_eq", "_", "_", "_", "_"],
    "jkr":       ["C1", "C2", "a0", "F_adh", "d_adh", "_", "_"],
    "capillary": ["C1", "C2", "a0", "F_men", "lambda_men", "d_break", "_"],
}

# Names of free parameters for fitting (subset of length-7 schema).
FORCE_FIT_PARAMS: Dict[str, List[str]] = {
    name: [n for n in schema if n != "_"]
    for name, schema in FORCE_PARAM_SCHEMA.items()
}

# Sensible initial values for each free parameter, in hat units.  The user
# should override these for their normalisation.
FORCE_DEFAULTS: Dict[str, Dict[str, float]] = {
    "dmt":       dict(C1=1e-3, C2=1e-2, a0=0.1),
    "hertz":     dict(C2=1e-2),
    "lj":        dict(eps=1e-3, sigma=0.2),
    "morse":     dict(De=1e-3, a_morse=5.0, r_eq=0.2),
    "jkr":       dict(C1=1e-3, C2=1e-2, a0=0.1, F_adh=2e-3, d_adh=0.05),
    "capillary": dict(C1=1e-3, C2=1e-2, a0=0.1, F_men=5e-3, lambda_men=0.3,
                      d_break=0.5),
}


def make_force_params(model: str, **values) -> np.ndarray:
    """Return a length-7 parameter vector for the named force model.

    Unspecified free parameters use the defaults in FORCE_DEFAULTS.  Unused
    slots are filled with 1.0 (the dispatcher ignores them).
    """
    if model not in FORCE_MODELS:
        raise ValueError(f"unknown model {model!r}; available: "
                         f"{list(FORCE_MODELS)}")
    schema = FORCE_PARAM_SCHEMA[model]
    defaults = FORCE_DEFAULTS[model]
    p = np.ones(7, dtype=np.float64)
    for k, slot in enumerate(schema):
        if slot == "_":
            continue
        p[k] = float(values.get(slot, defaults[slot]))
    return p


# =============================================================================
# 2.  Numba-jit force functions and unified dispatcher
# =============================================================================

@njit(cache=True)
def _smooth_relu(x, w):
    return 0.5 * (x + np.sqrt(x * x + w * w))


@njit(cache=True)
def _F_DMT(delta, C1, C2, a0, w_contact):
    gap = _smooth_relu(delta, w_contact)
    ind = _smooth_relu(-delta, w_contact)
    return -C1 / (gap + a0) ** 2 + C2 * ind ** 1.5


@njit(cache=True)
def _F_Hertz(delta, C2, w_contact):
    ind = _smooth_relu(-delta, w_contact)
    return C2 * ind ** 1.5


@njit(cache=True)
def _F_LJ(delta, eps, sigma, w_contact):
    # Avoid singularity at delta = -sigma by smoothing the gap, then
    # floor the gap at a fraction of sigma and cap the dimensionless
    # ratio (sigma/gap) so the 13th-power repulsion cannot blow up.
    #
    # Without these clips the optimizer could drive sigma/gap to ~1e8
    # giving (sigma/gap)^13 ~ 1e104 and amplitudes of order 1e+187 in
    # the lock-in demodulator, which is exactly what fails the
    # auto_select_force_model step.
    gap_raw   = _smooth_relu(delta + sigma, w_contact)
    gap_floor = 0.10 * sigma                   # 10 % of sigma absolute floor
    gap       = gap_raw + gap_floor + 1e-9
    s_over_r  = sigma / gap
    # Hard cap on the ratio: (S_CAP)^13 stays in O(1e9), which is the
    # largest LJ excursion any realistic AFM scan can ever see.
    S_CAP = 5.0
    if s_over_r > S_CAP:
        s_over_r = S_CAP
    s6  = s_over_r ** 6
    s12 = s6 * s6
    # F_LJ = 24 eps/sigma [2 (sigma/r)^13 - (sigma/r)^7]  (attractive at large r)
    F = -24.0 * eps / sigma * (2.0 * s12 * s_over_r - s6 * s_over_r)
    # Final safety clamp on the force magnitude itself, so a degenerate
    # eps or sigma cannot blow up downstream solvers.
    F_MAX = 1.0e6
    if F >  F_MAX:
        F =  F_MAX
    elif F < -F_MAX:
        F = -F_MAX
    return F


@njit(cache=True)
def _F_Morse(delta, De, a_morse, r_eq, w_contact):
    # r is the smoothed gap, anchored so equilibrium sits at delta = r_eq.
    r = _smooth_relu(delta, w_contact) + 1e-12
    e1 = np.exp(-a_morse * (r - r_eq))
    # F = -dV/dr with V = De (1 - e1)^2; F = -2 De a_morse e1 (1 - e1)
    F_attr = -2.0 * De * a_morse * e1 * (1.0 - e1)
    # Add a soft Hertz-like repulsion in the indentation regime so the
    # cantilever cannot pass through the surface.
    ind = _smooth_relu(-delta, w_contact)
    F_rep = 1e2 * De * a_morse * ind ** 1.5
    return F_attr + F_rep


@njit(cache=True)
def _F_JKR(delta, C1, C2, a0, F_adh, d_adh, w_contact):
    gap = _smooth_relu(delta, w_contact)
    ind = _smooth_relu(-delta, w_contact)
    F_dmt = -C1 / (gap + a0) ** 2 + C2 * ind ** 1.5
    # Adhesion: strong negative force that turns on in contact, decays as the
    # tip is pulled away.  This is the heuristic JKR-like asymmetry that
    # produces snap-off hysteresis in dynamic FD curves.
    F_adhesion = -F_adh * np.exp(-(gap / d_adh) ** 2)
    return F_dmt + F_adhesion


@njit(cache=True)
def _F_Capillary(delta, C1, C2, a0, F_men, lambda_men, d_break, w_contact):
    gap = _smooth_relu(delta, w_contact)
    ind = _smooth_relu(-delta, w_contact)
    F_dmt = -C1 / (gap + a0) ** 2 + C2 * ind ** 1.5
    # Meniscus: deep narrow well centred near zero gap, smoothly cut off
    # beyond d_break.
    bump = -F_men * np.exp(-(gap / lambda_men) ** 2)
    gate = 0.5 * (1.0 - np.tanh((gap - d_break) / (0.25 * d_break + 1e-9)))
    return F_dmt + bump * gate


@njit(cache=True)
def F_unified(delta, model_id, p0, p1, p2, p3, p4, p5, p6, w_contact):
    """Dispatch to the right force model.  All seven parameter slots are
    received as scalars so numba can inline the chosen branch."""
    if model_id == 0:
        return _F_DMT(delta, p0, p1, p2, w_contact)
    elif model_id == 1:
        return _F_Hertz(delta, p1, w_contact)
    elif model_id == 2:
        return _F_LJ(delta, p0, p2, w_contact)
    elif model_id == 3:
        return _F_Morse(delta, p0, p1, p2, w_contact)
    elif model_id == 4:
        return _F_JKR(delta, p0, p1, p2, p3, p4, w_contact)
    elif model_id == 5:
        return _F_Capillary(delta, p0, p1, p2, p3, p4, p5, w_contact)
    # default: zero force, prevents crashes if a bad id is passed
    return 0.0


@njit(cache=True)
def _gamma_ts(delta, gamma_lr, lambda_lr, gamma_contact, w_contact):
    gap = _smooth_relu(delta, w_contact)
    ind = _smooth_relu(-delta, w_contact)
    g_long = gamma_lr * np.exp(-gap / lambda_lr)
    contact_gate = ind / (ind + w_contact + 1e-12)
    return g_long + gamma_contact * contact_gate


# =============================================================================
# 3.  Unified RHS, RK45 stepper, demod window, steady-state solver
#     Mirrors the structure of spm_fd_rk45_extended_calibration but with
#     F_unified instead of the DMT-only force.
# =============================================================================

@njit(cache=True)
def _rhs(t, z, v, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
         C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact):
    delta = z + d
    F_cons = F_unified(delta, model_id, p0, p1, p2, p3, p4, p5, p6, w_contact)
    F_drive = -C3 * np.cos(omega_d * t)
    damp = 1.0 / Q + _gamma_ts(delta, gamma_lr, lambda_lr, gamma_contact, w_contact)
    return v, F_cons + F_drive - damp * v - z


@njit(cache=True)
def _rk45_step(t, z, v, dt, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
               C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact,
               rtol, atol):
    # Dormand-Prince RK45 (same coefficients as the existing module)
    c2 = 1.0/5.0; c3c = 3.0/10.0; c4 = 4.0/5.0; c5 = 8.0/9.0; c6 = 1.0
    a21 = 1.0/5.0
    a31 = 3.0/40.0; a32 = 9.0/40.0
    a41 = 44.0/45.0; a42 = -56.0/15.0; a43 = 32.0/9.0
    a51 = 19372.0/6561.0; a52 = -25360.0/2187.0; a53 = 64448.0/6561.0; a54 = -212.0/729.0
    a61 = 9017.0/3168.0; a62 = -355.0/33.0; a63 = 46732.0/5247.0; a64 = 49.0/176.0; a65 = -5103.0/18656.0
    b1 = 35.0/384.0; b3 = 500.0/1113.0; b4 = 125.0/192.0; b5 = -2187.0/6784.0; b6 = 11.0/84.0
    b1s = 5179.0/57600.0; b3s = 7571.0/16695.0; b4s = 393.0/640.0
    b5s = -92097.0/339200.0; b6s = 187.0/2100.0; b7s = 1.0/40.0

    dz1, dv1 = _rhs(t, z, v, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z2 = z + dt*a21*dz1; v2 = v + dt*a21*dv1
    dz2, dv2 = _rhs(t+c2*dt, z2, v2, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z3 = z + dt*(a31*dz1 + a32*dz2); v3 = v + dt*(a31*dv1 + a32*dv2)
    dz3, dv3 = _rhs(t+c3c*dt, z3, v3, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z4 = z + dt*(a41*dz1 + a42*dz2 + a43*dz3); v4 = v + dt*(a41*dv1 + a42*dv2 + a43*dv3)
    dz4, dv4 = _rhs(t+c4*dt, z4, v4, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z5i = z + dt*(a51*dz1 + a52*dz2 + a53*dz3 + a54*dz4); v5i = v + dt*(a51*dv1 + a52*dv2 + a53*dv3 + a54*dv4)
    dz5, dv5 = _rhs(t+c5*dt, z5i, v5i, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z6 = z + dt*(a61*dz1 + a62*dz2 + a63*dz3 + a64*dz4 + a65*dz5)
    v6 = v + dt*(a61*dv1 + a62*dv2 + a63*dv3 + a64*dv4 + a65*dv5)
    dz6, dv6 = _rhs(t+c6*dt, z6, v6, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z5 = z + dt*(b1*dz1 + b3*dz3 + b4*dz4 + b5*dz5 + b6*dz6)
    v5 = v + dt*(b1*dv1 + b3*dv3 + b4*dv4 + b5*dv5 + b6*dv6)
    dz7, dv7 = _rhs(t+dt, z5, v5, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6, C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact)
    z4s = z + dt*(b1s*dz1 + b3s*dz3 + b4s*dz4 + b5s*dz5 + b6s*dz6 + b7s*dz7)
    v4s = v + dt*(b1s*dv1 + b3s*dv3 + b4s*dv4 + b5s*dv5 + b6s*dv6 + b7s*dv7)
    sz = atol + rtol*max(abs(z), abs(z5))
    sv = atol + rtol*max(abs(v), abs(v5))
    err = np.sqrt(0.5*((z5 - z4s)/sz)**2 + 0.5*((v5 - v4s)/sv)**2)
    return z5, v5, err


@njit(cache=True)
def _wrap_phase(phi, mode):
    if mode == 180:
        while phi < 0.0:
            phi += 180.0
        while phi >= 180.0:
            phi -= 180.0
    else:
        while phi < 0.0:
            phi += 360.0
        while phi >= 360.0:
            phi -= 360.0
    return phi


@njit(cache=True)
def _run_window(t0, z0, v0, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
                C3, omega_d, omega_r, w_contact, gamma_lr, lambda_lr,
                gamma_contact, T_win, demod_dt, rtol, atol, dt0, dt_min,
                dt_max, max_steps):
    t = t0; z = z0; v = v0
    t_end = t0 + T_win
    X = 0.0; Y = 0.0
    if demod_dt <= 0.0:
        demod_dt = T_win
    t_s = t0; z_s = z0; next_s = t_s + demod_dt
    safety = 0.9; fac_min = 0.2; fac_max = 5.0; p_order = 5.0
    dt = dt0; steps = 0
    while t < t_end and steps < max_steps:
        if dt < dt_min:
            dt = dt_min
        if dt > dt_max:
            dt = dt_max
        if t + dt > t_end:
            dt = t_end - t
        t_prev = t; z_prev = z
        z_n, v_n, err = _rk45_step(t, z, v, dt, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
                                   C3, omega_d, w_contact, gamma_lr, lambda_lr, gamma_contact,
                                   rtol, atol)
        accept = (err <= 1.0) or (dt <= dt_min * 1.0001)
        if accept:
            t = t + dt; z = z_n; v = v_n
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
                c0 = np.cos(omega_r * t_s); s0 = np.sin(omega_r * t_s)
                c1 = np.cos(omega_r * next_s); s1 = np.sin(omega_r * next_s)
                X += 0.5 * (z_s * c0 + z_b * c1) * (next_s - t_s)
                Y += 0.5 * (z_s * s0 + z_b * s1) * (next_s - t_s)
                t_s = next_s; z_s = z_b; next_s = next_s + demod_dt
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
        c0 = np.cos(omega_r * t_s); s0 = np.sin(omega_r * t_s)
        c1 = np.cos(omega_r * t_end); s1 = np.sin(omega_r * t_end)
        X += 0.5 * (z_s * c0 + z * c1) * (t_end - t_s)
        Y += 0.5 * (z_s * s0 + z * s1) * (t_end - t_s)
    return X, Y, steps, z, v


@njit(cache=True)
def _steady_state(z0, v0, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
                  C3, omega_d, omega_r, w_contact, gamma_lr, lambda_lr,
                  gamma_contact, N_cycles, max_windows, settle_windows,
                  tol_A, tol_phi, consecutive, demod_per_cycle, rtol, atol,
                  dt0, dt_min, dt_max, max_steps_win, phase_wrap):
    T_ref = 2.0 * np.pi / omega_r
    T_win = N_cycles * T_ref
    if demod_per_cycle < 5:
        demod_per_cycle = 5
    demod_dt = T_ref / demod_per_cycle
    period = 180.0 if phase_wrap == 180 else 360.0
    t = 0.0; z = z0; v = v0
    last_A = 1e30; last_phi = 1e30; stable = 0
    A_last = 0.0; phi_last = 0.0
    for widx in range(max_windows):
        X, Y, _, z, v = _run_window(t, z, v, d, Q, model_id, p0, p1, p2, p3, p4, p5, p6,
                                    C3, omega_d, omega_r, w_contact, gamma_lr,
                                    lambda_lr, gamma_contact, T_win, demod_dt,
                                    rtol, atol, dt0, dt_min, dt_max, max_steps_win)
        t = t + T_win
        A = (2.0 / T_win) * np.sqrt(X * X + Y * Y)
        phi = np.degrees(np.arctan2(Y, X))
        phi = _wrap_phase(phi, phase_wrap)
        A_last = A; phi_last = phi
        if widx >= settle_windows:
            dA = abs(A - last_A)
            dphi_raw = phi - last_phi
            dphi = (dphi_raw + 0.5 * period) % period - 0.5 * period
            if dA < tol_A and abs(dphi) < tol_phi:
                stable += 1
            else:
                stable = 0
            if stable >= consecutive:
                return A, phi, (widx + 1), z, v
        last_A = A; last_phi = phi
    return A_last, phi_last, max_windows, z, v


# =============================================================================
# 4.  Python-level curve simulator (one branch via warm-start)
# =============================================================================

@dataclass
class SimOptions:
    Q: float = 80.0
    C3: float = 0.05
    omega_drive_hat: float = 1.0
    omega_ref_hat: Optional[float] = None
    d_offset_hat: float = 0.0
    w_contact: float = 0.1
    gamma_lr: float = 1e-4
    lambda_lr: float = 5.0
    gamma_contact: float = 1e-3
    N_cycles: int = 4
    max_windows: int = 40
    settle_windows: int = 3
    tol_A: float = 1e-5
    tol_phi_deg: float = 0.02
    consecutive: int = 2
    demod_per_ref_cycle: int = 48
    rtol: float = 1e-6
    atol: float = 1e-8
    dt0: float = 0.02
    dt_min: float = 1e-5
    dt_max: float = 0.15
    max_steps_per_window: int = 200000
    phase_wrap_mode: int = 180
    use_warm_start: bool = True

    def omega_ref(self) -> float:
        return self.omega_ref_hat if self.omega_ref_hat is not None else self.omega_drive_hat


def simulate_curve(d_hat: np.ndarray, model: str, force_params: np.ndarray,
                   opts: Optional[SimOptions] = None) -> Dict[str, np.ndarray]:
    """Simulate one branch of an FD curve under any of the registered models.

    Returns dict with keys A, phi, n_windows.
    """
    if opts is None:
        opts = SimOptions()
    model_id = FORCE_MODELS[model]
    p = np.asarray(force_params, dtype=np.float64).reshape(-1)
    if p.size != 7:
        raise ValueError("force_params must be length 7 (use make_force_params).")
    d_hat = np.asarray(d_hat, dtype=np.float64).ravel()
    n = d_hat.size
    A_out = np.empty(n); phi_out = np.empty(n); nwin_out = np.empty(n)
    order = np.argsort(d_hat)[::-1]
    z_cur = 0.0; v_cur = 0.0
    for kk in range(n):
        idx = order[kk]
        d_eff = d_hat[idx] + opts.d_offset_hat
        if opts.use_warm_start:
            z0 = z_cur; v0 = v_cur
        else:
            z0 = 0.0; v0 = 0.0
        A, phi, nw, z_cur, v_cur = _steady_state(
            z0, v0, d_eff, opts.Q, model_id, p[0], p[1], p[2], p[3], p[4], p[5], p[6],
            opts.C3, opts.omega_drive_hat, opts.omega_ref(),
            opts.w_contact, opts.gamma_lr, opts.lambda_lr, opts.gamma_contact,
            opts.N_cycles, opts.max_windows, opts.settle_windows,
            opts.tol_A, opts.tol_phi_deg, opts.consecutive, opts.demod_per_ref_cycle,
            opts.rtol, opts.atol, opts.dt0, opts.dt_min, opts.dt_max,
            opts.max_steps_per_window, opts.phase_wrap_mode,
        )
        A_out[idx] = A; phi_out[idx] = phi; nwin_out[idx] = nw
    return {"A": A_out, "phi": phi_out, "n_windows": nwin_out}


def static_force_curve(d_hat: np.ndarray, model: str,
                       force_params: np.ndarray, w_contact: float = 0.1) -> np.ndarray:
    """Evaluate the conservative force F(delta=d) statically (no oscillation).

    Useful for quick model diagnostics and for the auto-selector to read off
    pull-off force, snap-in distance, etc.
    """
    model_id = FORCE_MODELS[model]
    p = np.asarray(force_params, dtype=np.float64).reshape(-1)
    d = np.asarray(d_hat, dtype=np.float64).ravel()
    F = np.empty_like(d)
    for i in range(d.size):
        F[i] = F_unified(d[i], model_id, p[0], p[1], p[2], p[3], p[4], p[5], p[6],
                         w_contact)
    return F


# =============================================================================
# 5.  Approach/retract diagnostic metrics
# =============================================================================

def diagnostic_metrics(d_app: np.ndarray, A_app: np.ndarray, phi_app: np.ndarray,
                       d_ret: Optional[np.ndarray] = None,
                       A_ret: Optional[np.ndarray] = None,
                       phi_ret: Optional[np.ndarray] = None,
                       A0: Optional[float] = None) -> Dict[str, float]:
    """Compute model-selection-friendly scalar features from FD data.

    Inputs may be either FD-style amplitude/phase traces or static-force
    F vs d.  For the auto-selector we use the *amplitude* trace as a proxy
    for force severity; the metrics encode shape, not absolute scale.
    """
    d_app = np.asarray(d_app, float); A_app = np.asarray(A_app, float)
    phi_app = np.asarray(phi_app, float)
    if A0 is None:
        n_far = max(3, int(0.10 * d_app.size))
        A0 = float(np.median(A_app[np.argsort(d_app)[::-1][:n_far]]))

    # Amplitude-suppression depth (proxy for adhesion / contact strength)
    A_min = float(np.min(A_app))
    drop = (A0 - A_min) / max(A0, 1e-12)

    # Sharpness of amplitude transition (sharp -> JKR/capillary, smooth -> DMT/LJ/Morse)
    order = np.argsort(d_app)
    A_s = A_app[order]; d_s = d_app[order]
    dAdd = np.gradient(A_s, d_s)
    sharpness = float(np.nanmax(np.abs(dAdd)) / (drop / (np.ptp(d_s) + 1e-12)))

    # Phase deviation at maximum suppression (sign of regime)
    j_min = int(np.argmin(A_app))
    phi_at_min = float(phi_app[j_min])

    # Far-field attraction decay slope (estimated from amplitude rise back to A0)
    far_mask = (A_app < 0.95 * A0) & (A_app > 0.6 * A0)
    decay_slope = np.nan
    decay_ratio = np.nan
    if int(far_mask.sum()) >= 5:
        dd = d_app[far_mask]
        suppression = (A0 - A_app[far_mask]) / A0
        # Test power-law: log(suppression) vs log(d - d0) with d0 = min(d)
        d0_ref = float(np.min(dd)) - 1e-3
        try:
            slope, _ = np.polyfit(np.log(dd - d0_ref + 1e-9),
                                  np.log(suppression + 1e-12), 1)
            decay_slope = float(slope)
        except Exception:
            decay_slope = np.nan
        # Test exponential: log(suppression) vs dd
        try:
            slope_e, _ = np.polyfit(dd, np.log(suppression + 1e-12), 1)
            decay_ratio = float(slope_e)
        except Exception:
            decay_ratio = np.nan

    metrics = {
        "A0": A0,
        "A_drop_frac": drop,
        "amp_sharpness": sharpness,
        "phase_at_Amin_deg": phi_at_min,
        "decay_powerlaw_slope": decay_slope,
        "decay_exp_slope": decay_ratio,
    }

    # Hysteresis: only meaningful if both branches are present.
    if d_ret is not None and A_ret is not None:
        d_ret = np.asarray(d_ret, float); A_ret = np.asarray(A_ret, float)
        # Resample retract onto approach grid (linear interp)
        order_r = np.argsort(d_ret)
        A_ret_on_app = np.interp(d_app, d_ret[order_r], A_ret[order_r])
        diff = A_app - A_ret_on_app
        hyst_area = float(np.trapz(np.abs(diff), d_app))
        hyst_signed = float(np.trapz(diff, d_app))
        metrics["hysteresis_area"] = hyst_area
        metrics["hysteresis_signed"] = hyst_signed
        # Pull-off proxy: deepest retract suppression beyond approach contact
        if A_ret is not None:
            j_pull = int(np.argmin(A_ret))
            metrics["pulloff_distance_hat"] = float(d_ret[j_pull])
            metrics["pulloff_depth_frac"] = float((A0 - A_ret[j_pull]) / max(A0, 1e-12))
    else:
        metrics["hysteresis_area"] = 0.0
        metrics["hysteresis_signed"] = 0.0
        metrics["pulloff_distance_hat"] = np.nan
        metrics["pulloff_depth_frac"] = np.nan

    return metrics


# =============================================================================
# 6.  Auto model selector
# =============================================================================

_POSITIVE_SIM_FIT_PARAMS = {
    "Q", "C3", "w_contact", "gamma_lr", "lambda_lr", "gamma_contact",
}
_LINEAR_SIM_FIT_PARAMS = {"d_offset_hat", "omega_drive_hat", "omega_ref_hat"}
_SIM_FIT_PARAMS = _POSITIVE_SIM_FIT_PARAMS | _LINEAR_SIM_FIT_PARAMS


def _default_sim_param_bounds(name: str, value: float,
                              d_hat: np.ndarray) -> Tuple[float, float]:
    """Conservative default bounds for optional SimOptions parameters."""
    value = float(value)
    if name == "d_offset_hat":
        half_width = max(0.05 * float(np.ptp(d_hat)), 1e-3)
        return value - half_width, value + half_width
    if name in ("omega_drive_hat", "omega_ref_hat"):
        return max(1e-6, value - 0.03), value + 0.03
    if name == "Q":
        return max(value / 4.0, 1e-6), max(value * 4.0, 1e-6)
    if name == "C3":
        return max(value / 4.0, 1e-12), max(value * 4.0, 1e-12)
    if name == "w_contact":
        return max(value / 10.0, 1e-12), max(value * 10.0, 1e-12)
    if name in ("gamma_lr", "gamma_contact"):
        return max(value / 100.0, 1e-12), max(value * 100.0, 1e-12)
    if name == "lambda_lr":
        return max(value / 10.0, 1e-12), max(value * 10.0, 1e-12)
    raise ValueError(f"unsupported fit_sim_params entry {name!r}")


def _normalise_sim_fit_params(fit_d_offset: bool,
                              fit_sim_params: Sequence[str]) -> List[str]:
    names: List[str] = []
    if fit_d_offset:
        names.append("d_offset_hat")
    for name in fit_sim_params:
        if name not in _SIM_FIT_PARAMS:
            raise ValueError(
                f"unsupported fit_sim_params entry {name!r}; "
                f"allowed: {sorted(_SIM_FIT_PARAMS)}"
            )
        if name not in names:
            names.append(name)
    return names


def _fit_one_model(model: str, d_hat: np.ndarray, A_exp: np.ndarray,
                   phi_exp: np.ndarray, A0: float,
                   sim_opts: SimOptions, w_amp: float = 1.0,
                   w_phi: float = 0.01, max_nfev: int = 60,
                   init_overrides: Optional[Dict[str, float]] = None,
                   fit_d_offset: bool = False,
                   d_offset_bounds: Optional[Tuple[float, float]] = None,
                   fit_sim_params: Sequence[str] = (),
                   sim_param_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
                   sim_init_overrides: Optional[Dict[str, float]] = None,
                   drive_A_far: Optional[float] = None,
                   tie_C3_to_A_far: bool = False) -> Dict:
    """Fit one model's free parameters to (A, phi) data with least_squares.

    Returns a dict with the converged force_params (length-7), residual cost,
    SSR, and n_params (used for AICc).
    """
    if not _HAS_SCIPY:
        raise ImportError("scipy is required for the model selector.")
    fit_params = FORCE_FIT_PARAMS[model]
    sim_fit_params = _normalise_sim_fit_params(fit_d_offset, fit_sim_params)
    if tie_C3_to_A_far and "C3" in sim_fit_params:
        raise ValueError("Cannot fit C3 directly when tie_C3_to_A_far=True.")
    if tie_C3_to_A_far:
        if drive_A_far is None:
            drive_A_far = A0
        if drive_A_far is None or not np.isfinite(drive_A_far) or drive_A_far <= 0:
            raise ValueError("drive_A_far must be positive when tie_C3_to_A_far=True.")
    defaults = dict(FORCE_DEFAULTS[model])
    if init_overrides:
        defaults.update({k: v for k, v in init_overrides.items() if k in fit_params})

    sim_param_bounds = dict(sim_param_bounds or {})
    if d_offset_bounds is not None:
        sim_param_bounds["d_offset_hat"] = d_offset_bounds
    sim_init_overrides = dict(sim_init_overrides or {})

    x0_force = np.log(np.array([defaults[k] for k in fit_params], dtype=float))
    # Allow +/- 3 decades around defaults
    lower_force = x0_force - 3.0 * np.log(10.0)
    upper_force = x0_force + 3.0 * np.log(10.0)

    x0_extra: List[float] = []
    lower_extra: List[float] = []
    upper_extra: List[float] = []
    for name in sim_fit_params:
        base_value = sim_init_overrides.get(name, getattr(sim_opts, name))
        if base_value is None:
            base_value = sim_opts.omega_drive_hat
        base_value = float(base_value)
        lo, hi = sim_param_bounds.get(
            name, _default_sim_param_bounds(name, base_value, d_hat)
        )
        lo = float(lo); hi = float(hi)
        if not lo < hi:
            raise ValueError(f"bad bounds for {name}: {lo} >= {hi}")
        if name in _POSITIVE_SIM_FIT_PARAMS:
            base_value = min(max(base_value, lo), hi)
            x0_extra.append(np.log(max(base_value, 1e-300)))
            lower_extra.append(np.log(max(lo, 1e-300)))
            upper_extra.append(np.log(max(hi, 1e-300)))
        else:
            x0_extra.append(min(max(base_value, lo), hi))
            lower_extra.append(lo)
            upper_extra.append(hi)

    x0 = np.concatenate([x0_force, np.asarray(x0_extra, dtype=float)])
    lower = np.concatenate([lower_force, np.asarray(lower_extra, dtype=float)])
    upper = np.concatenate([upper_force, np.asarray(upper_extra, dtype=float)])

    n_force = len(fit_params)

    def unpack_x(x):
        vals = {k: float(np.exp(v)) for k, v in zip(fit_params, x[:n_force])}
        opts_fit = replace(sim_opts)
        sim_vals = {}
        for name, raw in zip(sim_fit_params, x[n_force:]):
            if name in _POSITIVE_SIM_FIT_PARAMS:
                value = float(np.exp(raw))
            else:
                value = float(raw)
            setattr(opts_fit, name, value)
            sim_vals[name] = value
        if tie_C3_to_A_far:
            opts_fit.C3 = float(drive_A_far) / max(float(opts_fit.Q), 1e-12)
            sim_vals["C3_tied_to_A_far"] = opts_fit.C3
        return vals, opts_fit, sim_vals

    def residual(x):
        vals, opts_fit, _ = unpack_x(x)
        p = make_force_params(model, **vals)
        try:
            out = simulate_curve(d_hat, model, p, opts_fit)
        except Exception:
            return np.ones(d_hat.size * 2) * 1e6
        rA = w_amp * (out["A"] - A_exp) / max(A0, 1e-12)
        # Use small phase weight by default — most discriminating signal is
        # amplitude shape, and phase has wrap ambiguity.
        period = 180.0 if sim_opts.phase_wrap_mode == 180 else 360.0
        dphi = (out["phi"] - phi_exp + 0.5 * period) % period - 0.5 * period
        rP = w_phi * dphi / period
        return np.concatenate([rA, rP])

    res = least_squares(residual, x0, bounds=(lower, upper),
                        loss="soft_l1", f_scale=1.0, max_nfev=max_nfev)
    vals, opts_best, sim_values = unpack_x(res.x)
    p_best = make_force_params(model, **vals)
    ssr = float(np.sum(residual(res.x) ** 2))
    n_obs = 2 * d_hat.size
    k = len(fit_params) + len(sim_fit_params)
    # AICc (Gaussian residuals proxy)
    if n_obs - k - 1 > 0:
        aicc = n_obs * np.log(ssr / n_obs + 1e-300) + 2 * k + \
               (2 * k * (k + 1)) / (n_obs - k - 1)
    else:
        aicc = float("inf")
    return {
        "model": model,
        "success": bool(res.success),
        "values": vals,
        "sim_values": sim_values,
        "sim_opts": opts_best,
        "force_params": p_best,
        "cost": float(res.cost),
        "ssr": ssr,
        "n_params": k,
        "n_obs": n_obs,
        "aicc": float(aicc),
    }


def auto_select_force_model(d_hat: np.ndarray, A_exp: np.ndarray, phi_exp: np.ndarray,
                            d_ret_hat: Optional[np.ndarray] = None,
                            A_ret: Optional[np.ndarray] = None,
                            phi_ret: Optional[np.ndarray] = None,
                            A0: Optional[float] = None,
                            sim_opts: Optional[SimOptions] = None,
                            candidates: Sequence[str] = ("dmt", "hertz", "lj",
                                                          "morse", "jkr",
                                                          "capillary"),
                            init_overrides: Optional[Dict[str, Dict[str, float]]] = None,
                            fit_d_offset: bool = False,
                            d_offset_bounds: Optional[Tuple[float, float]] = None,
                            fit_sim_params: Sequence[str] = (),
                            sim_param_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
                            sim_init_overrides: Optional[Dict[str, float]] = None,
                            drive_A_far: Optional[float] = None,
                            tie_C3_to_A_far: bool = False,
                            w_amp: float = 1.0, w_phi: float = 0.01,
                            max_nfev_per_model: int = 60,
                            verbose: bool = True) -> Dict:
    """Fit every candidate to the approach curve, score by AICc, optionally
    add a bonus for matching observed approach/retract hysteresis.

    Optional nuisance/flexible simulator parameters can be fitted together
    with each force model.  Use ``fit_d_offset=True`` to fit
    ``SimOptions.d_offset_hat``.  Use ``fit_sim_params`` for additional
    ``SimOptions`` entries such as ``("Q", "C3", "w_contact",
    "gamma_lr", "lambda_lr", "gamma_contact", "omega_drive_hat")``.
    Every added flexible parameter is counted in the AICc penalty.
    If ``tie_C3_to_A_far=True``, ``SimOptions.C3`` is set to
    ``drive_A_far / Q`` at every residual evaluation, so flexible Q still
    preserves the measured free-air amplitude.

    Returns dict with keys:
        ranking: list of dicts (one per model) sorted best -> worst
        best: name of the chosen model
        metrics: diagnostic metrics from the data
        details: per-model fit result
    """
    if sim_opts is None:
        sim_opts = SimOptions()
    if A0 is None:
        n_far = max(3, int(0.10 * len(d_hat)))
        A0 = float(np.median(A_exp[np.argsort(d_hat)[::-1][:n_far]]))

    init_overrides = init_overrides or {}
    metrics = diagnostic_metrics(d_hat, A_exp, phi_exp,
                                 d_ret_hat, A_ret, phi_ret, A0=A0)

    details = []
    for m in candidates:
        if verbose:
            print(f"  fitting {m} ...")
        try:
            res = _fit_one_model(m, d_hat, A_exp, phi_exp, A0, sim_opts,
                                 w_amp=w_amp, w_phi=w_phi,
                                 max_nfev=max_nfev_per_model,
                                 init_overrides=init_overrides.get(m),
                                 fit_d_offset=fit_d_offset,
                                 d_offset_bounds=d_offset_bounds,
                                 fit_sim_params=fit_sim_params,
                                 sim_param_bounds=sim_param_bounds,
                                 sim_init_overrides=sim_init_overrides,
                                 drive_A_far=drive_A_far,
                                 tie_C3_to_A_far=tie_C3_to_A_far)
        except Exception as e:
            if verbose:
                print(f"    failed: {e}")
            continue
        # Score adjustment from physical signatures
        bonus = 0.0
        if metrics.get("hysteresis_area", 0.0) > 0.05 * A0 * abs(np.ptp(d_hat)):
            if m in ("jkr", "capillary"):
                bonus -= 4.0  # AICc improvement
            elif m in ("dmt", "lj", "morse", "hertz"):
                bonus += 4.0  # penalty for ignoring hysteresis
        if metrics.get("A_drop_frac", 0.0) < 0.05 and m != "hertz":
            bonus += 1.0  # weak interaction -> prefer Hertz
        res["aicc_adjusted"] = res["aicc"] + bonus
        details.append(res)

    if not details:
        raise RuntimeError("All candidate models failed to fit.")

    details.sort(key=lambda r: r["aicc_adjusted"])
    if verbose:
        print("\nRanking (lower AICc better):")
        print(f"  {'model':<10} {'AICc':>10} {'adj':>10} {'SSR':>10} {'k':>3}  flexible")
        for r in details:
            print(f"  {r['model']:<10} {r['aicc']:>10.2f} "
                  f"{r['aicc_adjusted']:>10.2f} {r['ssr']:>10.3e} "
                  f"{r['n_params']:>3d}  {r.get('sim_values', {})}")

    return {
        "ranking": [r["model"] for r in details],
        "best": details[0]["model"],
        "metrics": metrics,
        "details": details,
    }


# =============================================================================
# 7.  All-stable-branches solver
# =============================================================================

def _multistart_initial_conditions(A0: float, n_starts: int = 5) -> List[Tuple[float, float]]:
    """Spread of (z0, v0) initial conditions that tend to land on different
    steady-state branches.

    * far branch:     small z, v=0  (free oscillation)
    * contact branch: large positive z, v=0 (tip pre-pushed into surface)
    * mid branches:   intermediate amplitudes with different velocity phases
    """
    starts = [(0.0, 0.0), (1.5 * A0, 0.0), (-1.5 * A0, 0.0)]
    extra = max(0, n_starts - 3)
    for k in range(extra):
        ang = 2.0 * np.pi * (k + 0.5) / max(extra, 1)
        starts.append((A0 * 0.5 * np.cos(ang), A0 * 0.5 * np.sin(ang)))
    return starts[:n_starts]


def _cluster_branches(A: np.ndarray, phi: np.ndarray, period_deg: float,
                      tol_A: float, tol_phi: float) -> List[List[int]]:
    """Hierarchical single-link clustering of (A, phi) endpoints.

    Uses (A/tol_A, dphi/tol_phi) as a normalised distance, with phi treated
    circularly.
    """
    if not _HAS_SCIPY:
        # Fallback: greedy clustering
        clusters: List[List[int]] = []
        for i in range(len(A)):
            placed = False
            for c in clusters:
                Ar = A[c[0]]; phir = phi[c[0]]
                dphi = (phi[i] - phir + 0.5 * period_deg) % period_deg - 0.5 * period_deg
                if abs(A[i] - Ar) < tol_A and abs(dphi) < tol_phi:
                    c.append(i); placed = True; break
            if not placed:
                clusters.append([i])
        return clusters

    n = len(A)
    if n <= 1:
        return [list(range(n))]
    pts = np.zeros((n, 2))
    pts[:, 0] = A / max(tol_A, 1e-12)
    # Map phi to a 2D unit-circle to handle wrap; scale by tol
    theta = 2 * np.pi * phi / period_deg
    pts_y = np.column_stack([np.cos(theta), np.sin(theta)]) / max(tol_phi / period_deg, 1e-12)
    pts_full = np.column_stack([pts[:, 0], pts_y])
    Z = linkage(pts_full, method="single")
    labels = fcluster(Z, t=1.0, criterion="distance")
    clusters_d: Dict[int, List[int]] = {}
    for i, lab in enumerate(labels):
        clusters_d.setdefault(int(lab), []).append(i)
    return list(clusters_d.values())


def find_all_branches_at_d(d: float, model: str, force_params: np.ndarray,
                           opts: Optional[SimOptions] = None,
                           n_starts: int = 7, tol_A: float = 1e-3,
                           tol_phi_deg: float = 1.0,
                           perturb_test: bool = True) -> List[Dict]:
    """Return a list of distinct stable steady-state branches at distance d.

    Each entry: {"A": ..., "phi": ..., "z_end": ..., "v_end": ..., "score": ...}.
    Stability is verified by perturbing and reconverging when perturb_test=True.
    """
    if opts is None:
        opts = SimOptions()
    model_id = FORCE_MODELS[model]
    p = np.asarray(force_params, dtype=np.float64).reshape(-1)
    A0_guess = max(opts.C3 * opts.Q, 1e-3)
    starts = _multistart_initial_conditions(A0_guess, n_starts=n_starts)
    A_l = []; phi_l = []; z_l = []; v_l = []
    for (z0, v0) in starts:
        A, phi, _, z_end, v_end = _steady_state(
            z0, v0, d + opts.d_offset_hat, opts.Q, model_id,
            p[0], p[1], p[2], p[3], p[4], p[5], p[6],
            opts.C3, opts.omega_drive_hat, opts.omega_ref(),
            opts.w_contact, opts.gamma_lr, opts.lambda_lr, opts.gamma_contact,
            opts.N_cycles, opts.max_windows, opts.settle_windows,
            opts.tol_A, opts.tol_phi_deg, opts.consecutive,
            opts.demod_per_ref_cycle, opts.rtol, opts.atol,
            opts.dt0, opts.dt_min, opts.dt_max, opts.max_steps_per_window,
            opts.phase_wrap_mode,
        )
        A_l.append(A); phi_l.append(phi); z_l.append(z_end); v_l.append(v_end)

    period = 180.0 if opts.phase_wrap_mode == 180 else 360.0
    clusters = _cluster_branches(np.asarray(A_l), np.asarray(phi_l), period,
                                 tol_A, tol_phi_deg)
    branches = []
    for c in clusters:
        Ac = float(np.mean([A_l[i] for i in c]))
        # Circular mean for phi
        theta = np.deg2rad(np.array([phi_l[i] for i in c]) * 360.0 / period)
        phic = float((np.rad2deg(np.arctan2(np.mean(np.sin(theta)),
                                            np.mean(np.cos(theta))))
                      * period / 360.0) % period)
        z_end = float(np.mean([z_l[i] for i in c]))
        v_end = float(np.mean([v_l[i] for i in c]))
        score = len(c)  # how many starts landed here -> basin size proxy
        ok = True
        if perturb_test:
            # Perturb and re-converge to verify stability
            for (dz, dv) in [(0.05 * A0_guess, 0.0), (-0.05 * A0_guess, 0.0)]:
                A2, phi2, _, _, _ = _steady_state(
                    z_end + dz, v_end + dv, d + opts.d_offset_hat, opts.Q, model_id,
                    p[0], p[1], p[2], p[3], p[4], p[5], p[6],
                    opts.C3, opts.omega_drive_hat, opts.omega_ref(),
                    opts.w_contact, opts.gamma_lr, opts.lambda_lr, opts.gamma_contact,
                    opts.N_cycles, opts.max_windows, opts.settle_windows,
                    opts.tol_A, opts.tol_phi_deg, opts.consecutive,
                    opts.demod_per_ref_cycle, opts.rtol, opts.atol,
                    opts.dt0, opts.dt_min, opts.dt_max, opts.max_steps_per_window,
                    opts.phase_wrap_mode,
                )
                dphi = (phi2 - phic + 0.5 * period) % period - 0.5 * period
                if abs(A2 - Ac) > 5 * tol_A or abs(dphi) > 5 * tol_phi_deg:
                    ok = False
                    break
        if ok:
            branches.append({"A": Ac, "phi": phic, "z_end": z_end, "v_end": v_end,
                             "basin_count": score})
    # Sort by amplitude (low -> high), so attractive branch comes first
    branches.sort(key=lambda b: b["A"])
    return branches


def simulate_curve_all_branches(d_hat: np.ndarray, model: str,
                                force_params: np.ndarray,
                                opts: Optional[SimOptions] = None,
                                n_starts: int = 7, tol_A: float = 1e-3,
                                tol_phi_deg: float = 1.0,
                                stitch_tol_A: float = 5e-3,
                                stitch_tol_phi_deg: float = 5.0,
                                verbose: bool = False) -> Dict:
    """Find all stable branches at every d in `d_hat` and stitch them across
    distance into named tracks.

    Returns dict with:
        d:       length-n array (input order)
        n_branches_at_d: length-n int array
        tracks:  list of dicts, each a contiguous branch with arrays
                 {"d": ..., "A": ..., "phi": ..., "label": "attractive"|"repulsive"|"branch_k"}
        raw:     list (per d) of branch lists from find_all_branches_at_d
    """
    if opts is None:
        opts = SimOptions()
    d_hat = np.asarray(d_hat, dtype=np.float64).ravel()
    n = d_hat.size
    raw_per_d: List[List[Dict]] = []
    for i, d in enumerate(d_hat):
        if verbose:
            print(f"  d = {d:.4g}  ({i+1}/{n})")
        branches = find_all_branches_at_d(d, model, force_params, opts,
                                          n_starts=n_starts, tol_A=tol_A,
                                          tol_phi_deg=tol_phi_deg)
        raw_per_d.append(branches)

    # Across-d stitching: greedy nearest-neighbour
    tracks: List[Dict] = []
    open_tracks: List[Dict] = []  # those that received a point in the previous d
    period = 180.0 if opts.phase_wrap_mode == 180 else 360.0
    for i, branches in enumerate(raw_per_d):
        used = [False] * len(branches)
        new_open: List[Dict] = []
        for tr in open_tracks:
            # Match to closest unused branch
            best_j = -1; best_dist = float("inf")
            for j, b in enumerate(branches):
                if used[j]:
                    continue
                dA = abs(b["A"] - tr["A"][-1])
                dphi = abs((b["phi"] - tr["phi"][-1] + 0.5 * period) % period - 0.5 * period)
                if dA < stitch_tol_A and dphi < stitch_tol_phi_deg:
                    score = (dA / stitch_tol_A) ** 2 + (dphi / stitch_tol_phi_deg) ** 2
                    if score < best_dist:
                        best_dist = score; best_j = j
            if best_j >= 0:
                tr["d"].append(d_hat[i])
                tr["A"].append(branches[best_j]["A"])
                tr["phi"].append(branches[best_j]["phi"])
                used[best_j] = True
                new_open.append(tr)
            else:
                tracks.append(tr)
        for j, b in enumerate(branches):
            if not used[j]:
                new_open.append({"d": [d_hat[i]], "A": [b["A"]],
                                 "phi": [b["phi"]], "label": ""})
        open_tracks = new_open
    tracks.extend(open_tracks)

    # Label tracks: lowest mean amplitude -> attractive; highest -> repulsive
    if tracks:
        mean_A = np.array([np.mean(t["A"]) for t in tracks])
        for k, t in enumerate(np.argsort(mean_A)):
            tracks[t]["label"] = ("attractive" if k == 0
                                  else "repulsive" if k == len(mean_A) - 1
                                  else f"branch_{k}")
    for t in tracks:
        t["d"] = np.asarray(t["d"]); t["A"] = np.asarray(t["A"])
        t["phi"] = np.asarray(t["phi"])

    n_branches = np.array([len(b) for b in raw_per_d], dtype=int)
    return {"d": d_hat, "n_branches_at_d": n_branches, "tracks": tracks,
            "raw": raw_per_d}


# =============================================================================
# 8.  Plot helpers (matplotlib optional)
# =============================================================================

def plot_force_curves(d_hat: np.ndarray, models: Sequence[str] = ("dmt", "lj",
                                                                    "morse", "jkr",
                                                                    "capillary"),
                       w_contact: float = 0.1, axes=None):
    import matplotlib.pyplot as plt
    if axes is None:
        fig, axes = plt.subplots(figsize=(6, 4))
    else:
        fig = axes.figure
    for m in models:
        p = make_force_params(m)
        F = static_force_curve(d_hat, m, p, w_contact=w_contact)
        axes.plot(d_hat, F, label=m)
    axes.axhline(0, color="k", lw=0.5)
    axes.set_xlabel(r"$\delta$ (gap, hat units)")
    axes.set_ylabel("Static force")
    axes.legend()
    return fig, axes


def plot_branches(branch_result: Dict, A0: Optional[float] = None, axes=None):
    import matplotlib.pyplot as plt
    if axes is None:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    else:
        fig = axes[0].figure
    colours = {"attractive": "tab:blue", "repulsive": "tab:red"}
    for t in branch_result["tracks"]:
        c = colours.get(t["label"], "tab:green")
        axes[0].plot(t["d"], t["A"], "o-", color=c, ms=3, label=t["label"])
        axes[1].plot(t["d"], t["phi"], "o-", color=c, ms=3, label=t["label"])
    if A0 is not None:
        axes[0].axhline(A0, color="k", lw=0.5, ls="--")
    axes[0].set_xlabel("d (hat)"); axes[0].set_ylabel("Amplitude")
    axes[1].set_xlabel("d (hat)"); axes[1].set_ylabel("Phase (deg)")
    axes[0].legend(); axes[1].legend()
    return fig, axes


# =============================================================================
# 9.  Self-contained demo (uses small Python-level loops; no real scanner)
# =============================================================================

def _demo():
    print("=" * 70)
    print("Multi-force-model + all-branches demo")
    print("=" * 70)

    d = np.linspace(0.05, 3.0, 16)[::-1]
    opts = SimOptions(Q=80.0, C3=0.05, w_contact=0.1, N_cycles=2,
                      max_windows=20, settle_windows=2, tol_A=2e-4,
                      tol_phi_deg=0.2, demod_per_ref_cycle=24,
                      rtol=1e-4, atol=1e-6, dt0=0.05, dt_max=0.25,
                      max_steps_per_window=20000)

    print("\n[1] Single-branch simulation under each force model:")
    for m in ("dmt", "hertz", "lj", "morse", "jkr", "capillary"):
        p = make_force_params(m)
        out = simulate_curve(d, m, p, opts)
        print(f"  {m:<10} A[far]={out['A'][0]:+.3f}  A[near]={out['A'][-1]:+.3f}  "
              f"phi[near]={out['phi'][-1]:+.1f}")

    print("\n[2] Synthetic 'experiment' from JKR; selector should recover it.")
    p_true = make_force_params("jkr", C1=1e-3, C2=1e-2, a0=0.1, F_adh=3e-3, d_adh=0.07)
    truth = simulate_curve(d, "jkr", p_true, opts)
    A_exp = truth["A"] + 0.002 * np.random.default_rng(0).standard_normal(d.size)
    phi_exp = truth["phi"] + 0.5 * np.random.default_rng(1).standard_normal(d.size)

    if _HAS_SCIPY:
        print("\nRunning auto_select_force_model (this is slow without numba) ...")
        sel = auto_select_force_model(
            d, A_exp, phi_exp, sim_opts=opts,
            candidates=("dmt", "lj", "morse", "jkr"),
            max_nfev_per_model=30, verbose=True,
        )
        print(f"\n  best model: {sel['best']}")
        print(f"  ranking   : {sel['ranking']}")
    else:
        print("scipy not available - skipping selector demo")

    print("\n[3] All stable branches at a small set of d values:")
    p = make_force_params("jkr", C1=1e-3, C2=1e-2, a0=0.1, F_adh=3e-3, d_adh=0.07)
    d_few = np.array([2.5, 1.0, 0.5, 0.2])
    br = simulate_curve_all_branches(d_few, "jkr", p, opts, n_starts=5, verbose=True)
    print(f"  branches per d: {br['n_branches_at_d']}")
    for t in br["tracks"]:
        print(f"    track '{t['label']}': d={t['d']}  A={np.round(t['A'], 3)}  "
              f"phi={np.round(t['phi'], 1)}")
    print("\nDone.")


if __name__ == "__main__":
    _demo()
