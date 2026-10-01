from __future__ import annotations

import numpy as np
from typing import Dict, Optional

def _broadcast_1d(value, n, name):
    arr = np.asarray(value, dtype=float)

    if arr.ndim == 0:
        return np.full(n, float(arr), dtype=float)

    arr = np.ravel(arr)

    if arr.size != n:
        raise ValueError(
            f"{name} must be scalar or length {n}, got shape {arr.shape}."
        )

    return arr.astype(float)


def compute_height_change_metrics(h_hat, scan_speed_hat, dx_hat):
    h_hat = np.asarray(h_hat, dtype=float).ravel()

    if h_hat.size < 2:
        return {
            "dh_dx_max": 0.0,
            "dh_dx_mean": 0.0,
            "dh_dt_max": 0.0,
            "dh_dt_mean": 0.0,
            "height_ptp": 0.0,
            "height_rms_slope": 0.0,
        }

    dh_dx = np.gradient(h_hat, float(dx_hat))
    dh_dt = dh_dx * float(scan_speed_hat)

    return {
        "dh_dx_max": float(np.max(np.abs(dh_dx))),
        "dh_dx_mean": float(np.mean(np.abs(dh_dx))),
        "dh_dt_max": float(np.max(np.abs(dh_dt))),
        "dh_dt_mean": float(np.mean(np.abs(dh_dt))),
        "height_ptp": float(np.ptp(h_hat)),
        "height_rms_slope": float(np.sqrt(np.mean(dh_dx**2))),
    }


def add_height_change_metrics(out, h_hat, scan_speed_hat, dx_hat):
    out["height_change_metrics"] = compute_height_change_metrics(
        h_hat=h_hat,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
    )
    return out


def fd_range_penalty_from_out(out, w_below=1e3, w_above=10.0):
    """
    Penalize entering uncalibrated FD range.

    below_fd_range is usually more dangerous than above_fd_range.
    """
    if out is None:
        return 0.0

    penalty = 0.0

    for key in ["trace", "retrace"]:
        if key in out:
            penalty += w_below * float(out[key].get("frac_below_fd_range", 0.0))
            penalty += w_above * float(out[key].get("frac_above_fd_range", 0.0))

    penalty += w_below * float(out.get("frac_below_fd_range", 0.0))
    penalty += w_above * float(out.get("frac_above_fd_range", 0.0))

    return float(penalty)

# =============================================================================
# Filters
# =============================================================================

def _lpf1_step(y, x, dt, tau):
    """
    First-order LPF:
        dy/dt = (x - y) / tau

    Uses alpha = dt / (tau + dt), stable for all dt.
    """
    if tau is None or tau <= 0.0:
        return float(x)

    alpha = dt / (tau + dt)
    return float(y + alpha * (x - y))


def _lpf2_step(y, ydot, x, dt, wn, zeta):
    """
    Exact discrete step for:
        y'' + 2*zeta*wn*y' + wn^2*y = wn^2*x

    Assumes x is constant during [t, t+dt].
    """
    if wn is None or wn <= 0.0:
        return float(x), 0.0

    y = float(y)
    ydot = float(ydot)
    x = float(x)
    dt = float(dt)
    wn = float(wn)
    zeta = float(zeta)

    e = y - x
    edot = ydot

    if zeta < 1.0:
        wd = wn * np.sqrt(1.0 - zeta * zeta)
        decay = np.exp(-zeta * wn * dt)
        c = np.cos(wd * dt)
        s = np.sin(wd * dt)

        e_new = decay * (
            e * c + (edot + zeta * wn * e) * s / wd
        )

        edot_new = decay * (
            edot * c
            - (wn * wn * e + zeta * wn * edot) * s / wd
        )

    elif zeta > 1.0:
        wd = wn * np.sqrt(zeta * zeta - 1.0)
        decay = np.exp(-zeta * wn * dt)
        ch = np.cosh(wd * dt)
        sh = np.sinh(wd * dt)

        e_new = decay * (
            e * ch + (edot + zeta * wn * e) * sh / wd
        )

        edot_new = decay * (
            edot * ch
            - (wn * wn * e + zeta * wn * edot) * sh / wd
        )

    else:
        decay = np.exp(-wn * dt)

        e_new = decay * (
            e + (edot + wn * e) * dt
        )

        edot_new = decay * (
            edot - wn * (edot + wn * e) * dt
        )

    return float(x + e_new), float(edot_new)


_BW4_ZETAS = (np.sin(np.pi / 8), np.sin(3 * np.pi / 8))


def _lpf4_step(s1, s1_dot, s2, s2_dot, x, dt, tau):
    """
    Fourth-order Butterworth LPF implemented as two second-order sections.
    """
    if tau is None or tau <= 0.0:
        return float(x), float(x), 0.0, float(x), 0.0

    wn = 1.0 / tau
    z1, z2 = _BW4_ZETAS

    s1_new, s1_dot_new = _lpf2_step(
        s1, s1_dot, x, dt, wn, z1
    )

    s2_new, s2_dot_new = _lpf2_step(
        s2, s2_dot, s1_new, dt, wn, z2
    )

    return (
        float(s2_new),
        float(s1_new),
        float(s1_dot_new),
        float(s2_new),
        float(s2_dot_new),
    )

def _filter_disabled(filter_order, tau):
    """
    Return True when a measurement filter should be disabled.

    Disable if:
        filter_order is None
        tau is None
        tau <= 0
    """
    if filter_order is None:
        return True

    if tau is None:
        return True

    try:
        if float(tau) <= 0:
            return True
    except Exception:
        return True

    return False
    
def _broadcast_1d(value, n, name):
    """
    Broadcast scalar or 1D array to length n.
    """
    arr = np.asarray(value, dtype=float)

    if arr.ndim == 0:
        return np.full(n, float(arr), dtype=float)

    arr = np.ravel(arr)

    if arr.size != n:
        raise ValueError(
            f"{name} must be scalar or length {n}, got shape {arr.shape}"
        )

    return arr.astype(float)


# =============================================================================
# ScannerFD
# =============================================================================


"""
ScannerFD — FD-lookup digital twin with controller dynamics aligned to the
full ODE-based Scanner (no noise injection).

Differences from the ODE Scanner:
  - measure_from_fd(d_eff) replaces measure_amp_phase_force_fast(...).
    The FD lookup returns the steady-state (A, phi, F) for the given d.
    The cantilever's natural amplitude time constant (~Q / (2 omega0)) is
    NOT modeled by the lookup — set tau_A and tau_phi explicitly to mimic
    the lock-in averaging behavior of the ODE version.
  - No ODE-specific kwargs (omega_*, tau_li_hat, N_cycles, ...).
  - No cantilever state (z, v) is propagated — replaced by A_meas_init_hat
    and phi_meas_init_deg so the trace -> retrace handoff still works.

Identical to the ODE Scanner's scan_line_pi:
  - dt = dx_hat / scan_speed_hat
  - first/second-order LPFs on A, phi, and z
  - PI controller with optional integrator leak (T_I) and rate limit
  - same operation order: measure -> filter -> err -> integ -> PI -> dcmd -> Z LPF
"""

import numpy as np
from typing import Dict, Optional


# -----------------------------------------------------------------------------
# Filters (must match the ODE Scanner's helpers)
# -----------------------------------------------------------------------------

def _lpf1_step(y, x, dt, tau):
    """1st-order LPF, alpha = dt / (tau + dt). Unconditionally stable."""
    if tau is None or tau <= 0.0:
        return x
    alpha = dt / (tau + dt)
    return y + alpha * (x - y)

import numpy as np

def _lpf2_step(y, ydot, x, dt, wn, zeta):
    """
    Exact discrete step for the 2nd-order low-pass:
        y'' + 2*zeta*wn*y' + wn**2 * y = wn**2 * x,
    assuming x is held constant over [t, t+dt].

    Unconditionally stable; reduces to identity as dt -> 0,
    and to y -> x as dt -> infinity (for zeta > 0).
    """
    # Work in transient coordinates: e = y - x_ss, x_ss = x for unit-gain LPF
    e = y - x
    edot = ydot

    if zeta < 1.0:
        wd = wn * np.sqrt(1.0 - zeta * zeta)
        decay = np.exp(-zeta * wn * dt)
        c = np.cos(wd * dt)
        s = np.sin(wd * dt)
        e_new    = decay * (c * e + (s / wd) * (edot + zeta * wn * e))
        edot_new = decay * (c * edot - (s / wd) * (wn * wn * e + zeta * wn * edot))
    elif zeta > 1.0:
        wd = wn * np.sqrt(zeta * zeta - 1.0)
        decay = np.exp(-zeta * wn * dt)
        ch = np.cosh(wd * dt)
        sh = np.sinh(wd * dt)
        e_new    = decay * (ch * e + (sh / wd) * (edot + zeta * wn * e))
        edot_new = decay * (ch * edot - (sh / wd) * (wn * wn * e + zeta * wn * edot))
    else:  # critically damped
        decay = np.exp(-wn * dt)
        e_new    = decay * (e + (edot + wn * e) * dt)
        edot_new = decay * (edot - wn * (edot + wn * e) * dt)

    return x + e_new, edot_new
    

import numpy as np

# 4th-order Butterworth = cascade of two 2nd-order sections
_BW4_ZETAS = (np.sin(np.pi / 8), np.sin(3 * np.pi / 8))

def _lpf4_step(s1, s1_dot, s2, s2_dot, x, dt, tau):
    """
    One step of a 4th-order Butterworth low-pass at corner 1/tau.
    State: (s1, s1_dot, s2, s2_dot) — 4 floats per filtered channel.
    Returns: (y, s1_new, s1_dot_new, s2_new, s2_dot_new)  where y = s2_new.
    """
    wn = 1.0 / tau
    z1, z2 = _BW4_ZETAS
    # First (lightly damped) section: input = x, output = s1
    s1_new, s1_dot_new = _lpf2_step(s1, s1_dot, x, dt, wn, z1)
    # Second (heavily damped) section: input = s1_new, output = s2
    s2_new, s2_dot_new = _lpf2_step(s2, s2_dot, s1_new, dt, wn, z2)
    return s2_new, s1_new, s1_dot_new, s2_new, s2_dot_new
    
# -----------------------------------------------------------------------------
# ScannerFD
# -----------------------------------------------------------------------------

class ScannerFD:
    """FD-lookup scanner. Controller code path matches the ODE Scanner."""

    def __init__(self, params: Dict, conversions: Dict, fd_model):
        self.param = dict(params)
        self.conversion = dict(conversions)
        self.fd_model = fd_model

        self.param_norm: Dict[str, float] = {}
        for key in self.param:
            self.param_norm[key] = self.param[key] * self.conversion[key]

        # Derived constants kept for parity with the ODE Scanner; unused here.
        self.param_norm['C1'] = self.param_norm['H'] * self.param_norm['R'] / 6.0
        self.param_norm['C2'] = (4.0 / 3.0) * self.param_norm['E_star'] * np.sqrt(self.param_norm['R'])
        self.param_norm['C3'] = self.param_norm['A'] / self.param_norm['Q']

    # -------------------------------------------------------------------------
    # Measurement
    # -------------------------------------------------------------------------

    def get_A0_hat(self, drive_nm=None):
        """
        Return free amplitude A0 in scanner-normalized units.

        For drive-dependent FD models, this returns A0(drive).
        """
        if drive_nm is not None:
            if hasattr(self.fd_model, "A0_at_drive"):
                return float(self.fd_model.A0_at_drive(float(drive_nm)))

            if hasattr(self.fd_model, "free_amplitude"):
                try:
                    return float(self.fd_model.free_amplitude(float(drive_nm)))
                except TypeError:
                    return float(self.fd_model.free_amplitude())

        if hasattr(self.fd_model, "A0"):
            return float(self.fd_model.A0)

        return float(self.param_norm["A"])


    def distance_range(self, drive_nm=None):
        """
        Return calibrated FD distance range in scanner-normalized units.
        """
        if hasattr(self.fd_model, "distance_range"):
            return self.fd_model.distance_range(drive_nm)

        if hasattr(self.fd_model, "d"):
            return float(self.fd_model.d[0]), float(self.fd_model.d[-1])

        return None, None


    def measure_from_fd(self, d_hat: float, drive_nm=None, return_flags: bool = False):
        """
        Evaluate FD response.

        If drive_nm is provided, fd_model must support drive-dependent evaluation.
        """
        d_hat = float(d_hat)

        if drive_nm is None:
            try:
                return self.fd_model.evaluate(d_hat, return_flags=return_flags)
            except TypeError:
                A, phi, F = self.fd_model.evaluate(d_hat)

                if return_flags:
                    d_min, d_max = self.distance_range(None)
                    flags = {
                        "below_fd_range": False if d_min is None else d_hat < d_min,
                        "above_fd_range": False if d_max is None else d_hat > d_max,
                        "d_min": d_min,
                        "d_max": d_max,
                    }
                    return float(A), float(phi), float(F), flags

                return float(A), float(phi), float(F)

        try:
            return self.fd_model.evaluate(
                d_hat,
                drive_nm=float(drive_nm),
                return_flags=return_flags,
            )
        except TypeError:
            if return_flags:
                raise TypeError(
                    "fd_model.evaluate does not support "
                    "evaluate(d_hat, drive_nm=..., return_flags=True)."
                )

            try:
                A, phi, F = self.fd_model.evaluate(
                    d_hat,
                    drive_nm=float(drive_nm),
                )
            except TypeError as e:
                raise TypeError(
                    "fd_model.evaluate does not accept drive_nm. "
                    "Use NormalizedDriveFD or implement evaluate(d_hat, drive_nm=...)."
                ) from e

            return float(A), float(phi), float(F)

    # -------------------------------------------------------------------------
    # Single line scan
    # -------------------------------------------------------------------------

    def scan_line_pi(
        self,
        h_hat,
        drive_nm=None,
        setpoint: float = 0.8,
        scan_speed_hat: float = 1.0,
        dx_hat: float = 1.0,

        # PI gains
        P: float = 0.1,
        I: float = 0.01,

        # Amplitude / phase measurement filters
        A_filter_order: Optional[int] = None,
        tau_A: float = 1e-2,
        wn_A: float = 1e3,
        zeta_A: float = 0.7,

        phi_filter_order: Optional[int] = None,
        tau_phi: float = 1e-2,
        wn_phi: float = 1e3,
        zeta_phi: float = 0.7,

        # Z actuator dynamics
        z_filter_order: Optional[int] = None,
        tau_z: float = 1e-2,
        wn_z: float = 1e3,
        zeta_z: float = 0.7,
        z_rate_limit_hat: Optional[float] = None,

        # Integrator memory
        T_I: Optional[float] = 0.0,
        integ_clip: Optional[float] = None,

        # Initial controller state
        d_init_hat: Optional[float] = 500,
        d_cmd_init_hat: Optional[float] = None,
        d_act_init_hat: Optional[float] = None,
        A_meas_init_hat: Optional[float] = None,
        phi_meas_init_deg: float = 0.0,
        integ_init: float = 0.0,
    ):
        h_hat = np.asarray(h_hat, dtype=np.float64).ravel()
        n = h_hat.size

        if scan_speed_hat <= 0:
            raise ValueError("scan_speed_hat must be positive.")
        if dx_hat <= 0:
            raise ValueError("dx_hat must be positive.")

        dt = float(dx_hat / scan_speed_hat)

        drive_arr = None
        if drive_nm is not None:
            drive_arr = _broadcast_1d(drive_nm, n, "drive_nm")

        setpoint_arr = _broadcast_1d(setpoint, n, "setpoint")

        # Initial d command
        if d_cmd_init_hat is not None:
            d_cmd = float(d_cmd_init_hat)
        elif d_init_hat is not None:
            d_cmd = float(d_init_hat)
        else:
            d_cmd = float(self.param_norm.get("d0", 0.0))

        d_act = float(d_cmd if d_act_init_hat is None else d_act_init_hat)
        d_act_dot = 0.0

        # Initial measured amplitude uses drive-specific A0 if available.
        first_drive = None if drive_arr is None else float(drive_arr[0])
        A0_init = self.get_A0_hat(first_drive)
        A_meas = float(A0_init if A_meas_init_hat is None else A_meas_init_hat)
        A_meas_dot = 0.0

        phi_meas = float(phi_meas_init_deg)
        phi_meas_dot = 0.0

        integ = float(integ_init)

        if T_I is None or T_I <= 0.0:
            use_leak = False
            decay = 1.0
        else:
            use_leak = True
            decay = float(np.exp(-dt / T_I))

        out_d_cmd = np.empty(n)
        out_d_act = np.empty(n)
        out_d_eff = np.empty(n)

        out_A_true = np.empty(n)
        out_A_meas = np.empty(n)
        out_A0 = np.empty(n)
        out_A_set = np.empty(n)

        out_phi_true = np.empty(n)
        out_phi_meas = np.empty(n)

        out_F = np.empty(n)
        out_err = np.empty(n)

        out_below_fd = np.zeros(n, dtype=bool)
        out_above_fd = np.zeros(n, dtype=bool)

        # 4th-order filter states
        A1, A1d, A2, A2d = A_meas, 0.0, A_meas, 0.0
        phi1, phi1d, phi2, phi2d = phi_meas, 0.0, phi_meas, 0.0

        for i in range(n):
            h_i = float(h_hat[i])
            drive_i = None if drive_arr is None else float(drive_arr[i])
            setpoint_i = float(setpoint_arr[i])

            A0_i = self.get_A0_hat(drive_i)
            A_set = setpoint_i * A0_i

            d_eff = d_act - h_i

            A_true, phi_true, F_peak, fd_flags = self.measure_from_fd(
                d_eff,
                drive_nm=drive_i,
                return_flags=True,
            )

            # Amplitude filter
            # Amplitude measurement filter
            # Disable by setting A_filter_order=None or tau_A=None or tau_A<=0.
            if _filter_disabled(A_filter_order, tau_A):
                A_meas = A_true

            elif A_filter_order == 1:
                A_meas = _lpf1_step(
                    A_meas,
                    A_true,
                    dt,
                    float(tau_A),
                )

            elif A_filter_order == 2:
                A_meas, A_meas_dot = _lpf2_step(
                    A_meas,
                    A_meas_dot,
                    A_true,
                    dt,
                    wn_A,
                    zeta_A,
                )

            elif A_filter_order == 4:
                A_meas, A1, A1d, A2, A2d = _lpf4_step(
                    A1,
                    A1d,
                    A2,
                    A2d,
                    A_true,
                    dt,
                    float(tau_A),
                )

            else:
                raise ValueError("A_filter_order must be None, 1, 2, or 4.")

            # Phase filter
            # Phase measurement filter
            # Disable by setting phi_filter_order=None or tau_phi=None or tau_phi<=0.
            if _filter_disabled(phi_filter_order, tau_phi):
                phi_meas = phi_true

            elif phi_filter_order == 1:
                phi_meas = _lpf1_step(
                    phi_meas,
                    phi_true,
                    dt,
                    float(tau_phi),
                )

            elif phi_filter_order == 2:
                phi_meas, phi_meas_dot = _lpf2_step(
                    phi_meas,
                    phi_meas_dot,
                    phi_true,
                    dt,
                    wn_phi,
                    zeta_phi,
                )

            elif phi_filter_order == 4:
                phi_meas, phi1, phi1d, phi2, phi2d = _lpf4_step(
                    phi1,
                    phi1d,
                    phi2,
                    phi2d,
                    phi_true,
                    dt,
                    float(tau_phi),
                )

            else:
                raise ValueError("phi_filter_order must be None, 1, 2, or 4.")

            # PI update
            err = A_set - A_meas

            if use_leak:
                integ = decay * integ + err * dt
            else:
                integ = integ + err * dt

            if integ_clip is not None:
                integ = float(np.clip(integ, -integ_clip, integ_clip))

            # Physical velocity-form PI
            dd_cmd = (P * err + I * integ) * dt

            if z_rate_limit_hat is not None:
                max_dd = float(z_rate_limit_hat) * dt
                dd_cmd = float(np.clip(dd_cmd, -max_dd, max_dd))

            d_cmd = d_cmd + dd_cmd

            # Z actuator dynamics
            if z_filter_order is None:
                d_act = d_cmd
            elif z_filter_order == 1:
                d_act = _lpf1_step(d_act, d_cmd, dt, tau_z)
            elif z_filter_order == 2:
                d_act, d_act_dot = _lpf2_step(
                    d_act,
                    d_act_dot,
                    d_cmd,
                    dt,
                    wn_z,
                    zeta_z,
                )
            else:
                raise ValueError("z_filter_order must be None, 1, or 2.")

            out_d_cmd[i] = d_cmd
            out_d_act[i] = d_act
            out_d_eff[i] = d_eff

            out_A_true[i] = A_true
            out_A_meas[i] = A_meas
            out_A0[i] = A0_i
            out_A_set[i] = A_set

            out_phi_true[i] = phi_true
            out_phi_meas[i] = phi_meas

            out_F[i] = F_peak
            out_err[i] = err

            out_below_fd[i] = bool(fd_flags.get("below_fd_range", False))
            out_above_fd[i] = bool(fd_flags.get("above_fd_range", False))

        return {
            "d_cmd_hat": out_d_cmd,
            "d_hat": out_d_act,
            "d_eff_hat": out_d_eff,

            "A_true_hat": out_A_true,
            "A_hat": out_A_meas,
            "A0_hat": out_A0,
            "A_set_hat": out_A_set,

            "phi_true_deg": out_phi_true,
            "phi_deg": out_phi_meas,

            "F_peak": out_F,
            "err": out_err,

            "below_fd_range": out_below_fd,
            "above_fd_range": out_above_fd,
            "frac_below_fd_range": float(np.mean(out_below_fd)),
            "frac_above_fd_range": float(np.mean(out_above_fd)),

            "dt_pixel": dt,

            "d_cmd_final_hat": float(d_cmd),
            "d_final_hat": float(d_act),
            "A_meas_final_hat": float(A_meas),
            "phi_meas_final_deg": float(phi_meas),
            "integ_final": float(integ),
        }
    
    def scan_line_substepped(
        self,
        h_hat,
        drive_nm,
        setpoint,
        *,
        scan_speed_hat,
        dx_hat,
        P=0.0,
        I=1.0,
        T_I=None,

        A_filter_order=4,
        tau_A=3.2e-5,

        phi_filter_order=4,
        tau_phi=3.2e-5,

        z_filter_order=1,
        tau_z=3.2e-5,

        d_init_hat=30.0,
        d_cmd_init_hat=None,
        d_act_init_hat=None,
        A_meas_init_hat=None,
        phi_meas_init_deg=113.0,
        integ_init=0.0,

        integ_clip=None,
        z_rate_limit_hat=None,

        n_substeps=None,
        dt_inner_max=None,
        safety=10.0,
    ):
        h_hat = np.asarray(h_hat, dtype=float).ravel()
        n = h_hat.size

        if scan_speed_hat <= 0:
            raise ValueError("scan_speed_hat must be positive.")
        if dx_hat <= 0:
            raise ValueError("dx_hat must be positive.")

        dt_pixel = float(dx_hat / scan_speed_hat)

        drive_arr = _broadcast_1d(drive_nm, n, "drive_nm")
        sp_arr = _broadcast_1d(setpoint, n, "setpoint")

        # Choose inner timestep
        tau_candidates = []

        if not _filter_disabled(A_filter_order, tau_A):
            tau_candidates.append(float(tau_A))

        if not _filter_disabled(phi_filter_order, tau_phi):
            tau_candidates.append(float(tau_phi))

        if z_filter_order is not None and tau_z is not None and tau_z > 0:
            tau_candidates.append(float(tau_z))

        tau_min = min(tau_candidates) if len(tau_candidates) > 0 else dt_pixel

        if n_substeps is None:
            if dt_inner_max is None:
                dt_inner_max = tau_min / safety
            n_substeps = max(1, int(np.ceil(dt_pixel / dt_inner_max)))

        n_substeps = int(n_substeps)
        dt_inner = dt_pixel / n_substeps

        if T_I is None or T_I <= 0:
            use_leak = False
            decay_inner = 1.0
        else:
            use_leak = True
            decay_inner = float(np.exp(-dt_inner / T_I))

        if d_cmd_init_hat is not None:
            d_cmd = float(d_cmd_init_hat)
        else:
            d_cmd = float(d_init_hat)

        if d_act_init_hat is not None:
            d_act = float(d_act_init_hat)
        else:
            d_act = float(d_init_hat)

        d_act_dot = 0.0

        first_drive = float(drive_arr[0])
        A0_init = self.get_A0_hat(first_drive)

        if A_meas_init_hat is None:
            A_meas = float(A0_init)
        else:
            A_meas = float(A_meas_init_hat)

        phi_meas = float(phi_meas_init_deg)
        integ = float(integ_init)

        A_meas_dot = 0.0
        phi_meas_dot = 0.0

        A1, A1d, A2, A2d = A_meas, 0.0, A_meas, 0.0
        p1, p1d, p2, p2d = phi_meas, 0.0, phi_meas, 0.0

        out = {
            k: np.empty(n)
            for k in (
                "d_cmd",
                "d_act",
                "d_hat",
                "d_eff_hat",

                "A_hat",
                "A_meas",
                "A0_hat",
                "A_set_hat",

                "phi_meas",
                "phi_deg",

                "A_true",
                "A_true_hat",
                "phi_true",
                "phi_true_deg",

                "F",
                "F_peak",
                "err",
            )
        }

        out_below_fd = np.zeros(n, dtype=bool)
        out_above_fd = np.zeros(n, dtype=bool)

        for i in range(n):
            h_i = float(h_hat[i])
            drive_i = float(drive_arr[i])
            sp_i = float(sp_arr[i])

            A0_i = self.get_A0_hat(drive_i)
            A_set = sp_i * A0_i

            fd_flags = {
                "below_fd_range": False,
                "above_fd_range": False,
            }

            for _ in range(n_substeps):
                d_eff = d_act - h_i

                A_true, phi_true, F_peak, fd_flags = self.measure_from_fd(
                    d_eff,
                    drive_nm=drive_i,
                    return_flags=True,
                )

                # Amplitude filter
                if _filter_disabled(A_filter_order, tau_A):
                    A_meas = A_true

                elif A_filter_order == 1:
                    A_meas = _lpf1_step(
                        A_meas,
                        A_true,
                        dt_inner,
                        float(tau_A),
                    )

                elif A_filter_order == 2:
                    A_meas, A_meas_dot = _lpf2_step(
                        A_meas,
                        A_meas_dot,
                        A_true,
                        dt_inner,
                        1.0 / float(tau_A),
                        np.sqrt(0.5),
                    )

                elif A_filter_order == 4:
                    wn = 1.0 / float(tau_A)

                    A1, A1d = _lpf2_step(
                        A1,
                        A1d,
                        A_true,
                        dt_inner,
                        wn,
                        _BW4_ZETAS[0],
                    )

                    A2, A2d = _lpf2_step(
                        A2,
                        A2d,
                        A1,
                        dt_inner,
                        wn,
                        _BW4_ZETAS[1],
                    )

                    A_meas = A2

                else:
                    raise ValueError("A_filter_order must be None, 1, 2, or 4.")


                # Phase filter
                # Phase measurement filter
                if _filter_disabled(phi_filter_order, tau_phi):
                    phi_meas = phi_true

                elif phi_filter_order == 1:
                    phi_meas = _lpf1_step(
                        phi_meas,
                        phi_true,
                        dt_inner,
                        float(tau_phi),
                    )

                elif phi_filter_order == 2:
                    phi_meas, phi_meas_dot = _lpf2_step(
                        phi_meas,
                        phi_meas_dot,
                        phi_true,
                        dt_inner,
                        1.0 / float(tau_phi),
                        np.sqrt(0.5),
                    )

                elif phi_filter_order == 4:
                    wn = 1.0 / float(tau_phi)

                    p1, p1d = _lpf2_step(
                        p1,
                        p1d,
                        phi_true,
                        dt_inner,
                        wn,
                        _BW4_ZETAS[0],
                    )

                    p2, p2d = _lpf2_step(
                        p2,
                        p2d,
                        p1,
                        dt_inner,
                        wn,
                        _BW4_ZETAS[1],
                    )

                    phi_meas = p2

                else:
                    raise ValueError("phi_filter_order must be None, 1, 2, or 4.")

                # PI update
                err = A_set - A_meas

                if use_leak:
                    integ = decay_inner * integ + err * dt_inner
                else:
                    integ = integ + err * dt_inner

                if integ_clip is not None:
                    integ = float(np.clip(integ, -integ_clip, integ_clip))

                # Correct physical-time velocity-form update
                dd_cmd = (P * err + I * integ) * dt_inner

                if z_rate_limit_hat is not None:
                    max_dd = float(z_rate_limit_hat) * dt_inner
                    dd_cmd = float(np.clip(dd_cmd, -max_dd, max_dd))

                d_cmd = d_cmd + dd_cmd

                # Z actuator
                if z_filter_order is None:
                    d_act = d_cmd
                elif z_filter_order == 1:
                    d_act = _lpf1_step(d_act, d_cmd, dt_inner, tau_z)
                elif z_filter_order == 2:
                    d_act, d_act_dot = _lpf2_step(
                        d_act,
                        d_act_dot,
                        d_cmd,
                        dt_inner,
                        1.0 / tau_z,
                        np.sqrt(0.5),
                    )
                else:
                    raise ValueError("z_filter_order must be None, 1, or 2.")

            out["d_cmd"][i] = d_cmd
            out["d_act"][i] = d_act
            out["d_hat"][i] = d_act
            out["d_eff_hat"][i] = d_eff

            out["A_hat"][i] = A_meas
            out["A_meas"][i] = A_meas
            out["A0_hat"][i] = A0_i
            out["A_set_hat"][i] = A_set

            out["phi_meas"][i] = phi_meas
            out["phi_deg"][i] = phi_meas

            out["A_true"][i] = A_true
            out["A_true_hat"][i] = A_true

            out["phi_true"][i] = phi_true
            out["phi_true_deg"][i] = phi_true

            out["F"][i] = F_peak
            out["F_peak"][i] = F_peak

            out["err"][i] = err

            out_below_fd[i] = bool(fd_flags.get("below_fd_range", False))
            out_above_fd[i] = bool(fd_flags.get("above_fd_range", False))

        out["below_fd_range"] = out_below_fd
        out["above_fd_range"] = out_above_fd
        out["frac_below_fd_range"] = float(np.mean(out_below_fd))
        out["frac_above_fd_range"] = float(np.mean(out_above_fd))

        out["dt_pixel"] = dt_pixel
        out["dt_inner"] = dt_inner
        out["n_substeps"] = n_substeps

        out["d_cmd_final_hat"] = float(d_cmd)
        out["d_final_hat"] = float(d_act)
        out["A_meas_final_hat"] = float(A_meas)
        out["phi_meas_final_deg"] = float(phi_meas)
        out["integ_final"] = float(integ)

        return out

    def scan_line_trace_retrace_pi_drive(
        self,
        h_hat,
        drive_nm,
        setpoint,
        *,
        scan_speed_hat,
        dx_hat,
        P=0.0,
        I=1.0,

        A_filter_order=1,
        tau_A=1e-4,
        wn_A=1e3,
        zeta_A=0.7,

        phi_filter_order=1,
        tau_phi=1e-4,
        wn_phi=1e3,
        zeta_phi=0.7,

        z_filter_order=1,
        tau_z=1e-5,
        wn_z=1e3,
        zeta_z=0.7,
        z_rate_limit_hat=None,

        d_init_hat=250.0,
        phi_meas_init_deg=0.0,
        A_meas_init_hat=None,
        T_I=None,
        integ_clip=None,

        use_substeps=False,
        n_substeps=None,
        dt_inner_max=None,
        safety=10.0,

        reset_between_trace_retrace=False,
    ):
        """
        Bidirectional trace/retrace scan.

        Trace scans h_hat forward.
        Retrace scans h_hat[::-1], then retrace arrays are flipped back into
        forward x-order.
        """
        h_hat = np.asarray(h_hat, dtype=float).ravel()

        if not use_substeps:
            trace = self.scan_line_pi(
                h_hat=h_hat,
                drive_nm=drive_nm,
                setpoint=setpoint,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P,
                I=I,

                A_filter_order=A_filter_order,
                tau_A=tau_A,
                wn_A=wn_A,
                zeta_A=zeta_A,

                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi,
                wn_phi=wn_phi,
                zeta_phi=zeta_phi,

                z_filter_order=z_filter_order,
                tau_z=tau_z,
                wn_z=wn_z,
                zeta_z=zeta_z,
                z_rate_limit_hat=z_rate_limit_hat,

                T_I=T_I,
                integ_clip=integ_clip,

                d_init_hat=d_init_hat,
                A_meas_init_hat=A_meas_init_hat,
                phi_meas_init_deg=phi_meas_init_deg,
            )

            if reset_between_trace_retrace:
                rt_d_cmd_init = None
                rt_d_act_init = None
                rt_A_init = A_meas_init_hat
                rt_phi_init = phi_meas_init_deg
                rt_integ_init = 0.0
            else:
                rt_d_cmd_init = trace["d_cmd_final_hat"]
                rt_d_act_init = trace["d_final_hat"]
                rt_A_init = trace["A_meas_final_hat"]
                rt_phi_init = trace["phi_meas_final_deg"]
                rt_integ_init = trace["integ_final"]

            retrace_raw = self.scan_line_pi(
                h_hat=h_hat[::-1],
                drive_nm=drive_nm,
                setpoint=setpoint,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P,
                I=I,

                A_filter_order=A_filter_order,
                tau_A=tau_A,
                wn_A=wn_A,
                zeta_A=zeta_A,

                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi,
                wn_phi=wn_phi,
                zeta_phi=zeta_phi,

                z_filter_order=z_filter_order,
                tau_z=tau_z,
                wn_z=wn_z,
                zeta_z=zeta_z,
                z_rate_limit_hat=z_rate_limit_hat,

                T_I=T_I,
                integ_clip=integ_clip,

                d_init_hat=d_init_hat,
                d_cmd_init_hat=rt_d_cmd_init,
                d_act_init_hat=rt_d_act_init,
                A_meas_init_hat=rt_A_init,
                phi_meas_init_deg=rt_phi_init,
                integ_init=rt_integ_init,
            )

        else:
            trace = self.scan_line_substepped(
                h_hat=h_hat,
                drive_nm=drive_nm,
                setpoint=setpoint,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P,
                I=I,
                T_I=T_I,

                A_filter_order=A_filter_order,
                tau_A=tau_A,

                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi,

                z_filter_order=z_filter_order,
                tau_z=tau_z,

                d_init_hat=d_init_hat,
                A_meas_init_hat=A_meas_init_hat,
                phi_meas_init_deg=phi_meas_init_deg,
                integ_clip=integ_clip,
                z_rate_limit_hat=z_rate_limit_hat,

                n_substeps=n_substeps,
                dt_inner_max=dt_inner_max,
                safety=safety,
            )

            if reset_between_trace_retrace:
                rt_d_cmd_init = None
                rt_d_act_init = None
                rt_A_init = A_meas_init_hat
                rt_phi_init = phi_meas_init_deg
                rt_integ_init = 0.0
            else:
                rt_d_cmd_init = trace["d_cmd_final_hat"]
                rt_d_act_init = trace["d_final_hat"]
                rt_A_init = trace["A_meas_final_hat"]
                rt_phi_init = trace["phi_meas_final_deg"]
                rt_integ_init = trace["integ_final"]

            retrace_raw = self.scan_line_substepped(
                h_hat=h_hat[::-1],
                drive_nm=drive_nm,
                setpoint=setpoint,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P,
                I=I,
                T_I=T_I,

                A_filter_order=A_filter_order,
                tau_A=tau_A,

                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi,

                z_filter_order=z_filter_order,
                tau_z=tau_z,

                d_init_hat=d_init_hat,
                d_cmd_init_hat=rt_d_cmd_init,
                d_act_init_hat=rt_d_act_init,
                A_meas_init_hat=rt_A_init,
                phi_meas_init_deg=rt_phi_init,
                integ_init=rt_integ_init,
                integ_clip=integ_clip,
                z_rate_limit_hat=z_rate_limit_hat,

                n_substeps=n_substeps,
                dt_inner_max=dt_inner_max,
                safety=safety,
            )

        retrace = {}

        for k, v in retrace_raw.items():
            if isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == len(h_hat):
                retrace[k] = v[::-1].copy()
            else:
                retrace[k] = v

        result = {
            "trace": trace,
            "retrace": retrace,
            "raw_retrace": retrace_raw,
        }

        add_height_change_metrics(
            result,
            h_hat=h_hat,
            scan_speed_hat=scan_speed_hat,
            dx_hat=dx_hat,
        )

        result["frac_below_fd_range"] = 0.5 * (
            float(trace.get("frac_below_fd_range", 0.0))
            + float(retrace.get("frac_below_fd_range", 0.0))
        )

        result["frac_above_fd_range"] = 0.5 * (
            float(trace.get("frac_above_fd_range", 0.0))
            + float(retrace.get("frac_above_fd_range", 0.0))
        )

        return result
    # -------------------------------------------------------------------------
    # 2D map (serpentine, optional state carry across rows)
    # -------------------------------------------------------------------------

    def scan_map_pi(
        self,
        h_map_hat,
        serpentine: bool = True,
        carry_state: bool = True,
        **line_kwargs,
    ):
        h_map_hat = np.asarray(h_map_hat, dtype=float)

        if h_map_hat.ndim != 2:
            raise ValueError("h_map_hat must be 2D.")

        ny, nx = h_map_hat.shape

        d_map = np.empty((ny, nx))
        d_eff_map = np.empty((ny, nx))
        phi_map = np.empty((ny, nx))
        F_map = np.empty((ny, nx))
        A_map = np.empty((ny, nx))
        err_map = np.empty((ny, nx))

        below_map = np.zeros((ny, nx), dtype=bool)
        above_map = np.zeros((ny, nx), dtype=bool)

        carry = dict(
            d_cmd_init_hat=line_kwargs.pop("d_cmd_init_hat", None),
            d_act_init_hat=line_kwargs.pop("d_act_init_hat", None),
            A_meas_init_hat=line_kwargs.pop("A_meas_init_hat", None),
            phi_meas_init_deg=line_kwargs.pop("phi_meas_init_deg", 0.0),
            integ_init=line_kwargs.pop("integ_init", 0.0),
        )

        for iy in range(ny):
            reverse = bool(serpentine and (iy % 2 == 1))
            row = h_map_hat[iy, ::-1] if reverse else h_map_hat[iy, :]

            out = self.scan_line_pi(
                row,
                **carry,
                **line_kwargs,
            )

            d_row = out["d_hat"]
            d_eff_row = out["d_eff_hat"]
            phi_row = out["phi_deg"]
            F_row = out["F_peak"]
            A_row = out["A_hat"]
            err_row = out["err"]
            below_row = out["below_fd_range"]
            above_row = out["above_fd_range"]

            if reverse:
                d_row = d_row[::-1]
                d_eff_row = d_eff_row[::-1]
                phi_row = phi_row[::-1]
                F_row = F_row[::-1]
                A_row = A_row[::-1]
                err_row = err_row[::-1]
                below_row = below_row[::-1]
                above_row = above_row[::-1]

            d_map[iy, :] = d_row
            d_eff_map[iy, :] = d_eff_row
            phi_map[iy, :] = phi_row
            F_map[iy, :] = F_row
            A_map[iy, :] = A_row
            err_map[iy, :] = err_row
            below_map[iy, :] = below_row
            above_map[iy, :] = above_row

            if carry_state:
                carry = dict(
                    d_cmd_init_hat=out["d_cmd_final_hat"],
                    d_act_init_hat=out["d_final_hat"],
                    A_meas_init_hat=out["A_meas_final_hat"],
                    phi_meas_init_deg=out["phi_meas_final_deg"],
                    integ_init=out["integ_final"],
                )

        return {
            "d_hat_map": d_map,
            "d_eff_hat_map": d_eff_map,
            "phi_deg_map": phi_map,
            "F_peak_map": F_map,
            "A_hat_map": A_map,
            "err_map": err_map,

            "below_fd_range_map": below_map,
            "above_fd_range_map": above_map,
            "frac_below_fd_range": float(np.mean(below_map)),
            "frac_above_fd_range": float(np.mean(above_map)),
        }
    
import numpy as np
from types import MethodType



# Stage-2 FD-curve surface interpolation for ScannerFD.

"""
Stage-2 FD-curve surface interpolation for ScannerFD.

Purpose
-------
Start from measured force-distance / amplitude-distance / phase-distance curves
at discrete drive amplitudes and build a smooth lookup that supports continuous
changes of drive amplitude and setpoint during scanning.

Main objects
------------
FDCurve1D
    Single-drive interpolator, evaluate(d) -> (A, phi, F).

FDDriveSurface
    2D surface over (drive, distance_coordinate). It is built once from the
    measured FD curves, then queried cheaply at arbitrary drive.

make_normalized_fd_lookup
    Adapter from physical nm/degree units to the normalized units used inside
    ScannerFD.

attach_continuous_fd_to_scanner
    Monkey-patch helper for an existing ScannerFD instance. It adds
    scanner.set_drive(...), scanner.scan_line_pi_drive(...), and
    scanner.scan_line_trace_retrace_pi_drive(...). If you prefer permanent
    changes, copy these methods into your ScannerFD class.

Conventions
-----------
- d increases away from the sample. Large d is far field.
- The measured d origin can be arbitrary; if needed, pre-shift each measured
  curve before adding it, or pass d_offset_nm in add_curve().
- A0 is the free amplitude for each curve. By default it is estimated from the
  largest-d tail, which matches separation-like FD curves.
- The recommended interpolation coordinate is x = d / A0, because AM-AFM
  amplitude/phase curves often collapse better in drive-normalized distance.
  For fixed calibrated absolute separation axes, use x_mode='absolute_d'.
"""

from dataclasses import dataclass
from types import MethodType
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
from scipy.interpolate import PchipInterpolator, RegularGridInterpolator, interp1d

ArrayLike = Union[float, np.ndarray, Iterable[float]]


def _as_1d(x: ArrayLike, name: str) -> np.ndarray:
    arr = np.asarray(x, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError(f"{name} is empty")
    return arr


def _finite_mask(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones_like(arrays[0], dtype=bool)
    for a in arrays:
        mask &= np.isfinite(a)
    return mask


def _average_duplicate_x(x: np.ndarray, *ys: np.ndarray) -> Tuple[np.ndarray, ...]:
    """Sort by x and average duplicate x values for stable interpolation."""
    order = np.argsort(x)
    x = x[order]
    ys = [np.asarray(y)[order] for y in ys]

    xu, inv = np.unique(x, return_inverse=True)
    if xu.size == x.size:
        return (x, *ys)

    y_out = []
    for y in ys:
        accum = np.zeros_like(xu, dtype=float)
        count = np.zeros_like(xu, dtype=float)
        np.add.at(accum, inv, y)
        np.add.at(count, inv, 1.0)
        y_out.append(accum / np.maximum(count, 1.0))
    return (xu, *y_out)


def _unwrap_phase_deg(phi_deg: np.ndarray) -> np.ndarray:
    return np.rad2deg(np.unwrap(np.deg2rad(phi_deg)))


def _safe_pchip(x: np.ndarray, y: np.ndarray, left: float, right: float):
    """PCHIP when possible; linear fallback for very short curves."""
    if x.size >= 3:
        return PchipInterpolator(x, y, extrapolate=False)
    return interp1d(x, y, kind="linear", bounds_error=False, fill_value=(left, right))


from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class FDCurve1D:
    """
    Single-drive FD evaluator.

    d, A, and F use the same unit system supplied at construction.
    phi is in degrees.

    Out-of-range behavior:
        d < d_min:
            clamp to nearest measured near-field point.
            This is numerically stable but should be treated as unsafe.

        d > d_max:
            clamp to far-field response:
                A   = A0
                phi = phi_far
                F   = 0
    """

    d: np.ndarray
    A: np.ndarray
    phi: np.ndarray
    F: Optional[np.ndarray] = None
    A0: Optional[float] = None
    kind: str = "pchip"

    def __post_init__(self) -> None:
        d = _as_1d(self.d, "d")
        A = _as_1d(self.A, "A")
        phi = _as_1d(self.phi, "phi")
        F = np.zeros_like(d) if self.F is None else _as_1d(self.F, "F")

        if not (d.shape == A.shape == phi.shape == F.shape):
            raise ValueError("d, A, phi, and F must have the same shape.")

        mask = _finite_mask(d, A, phi, F)
        d, A, phi, F = d[mask], A[mask], phi[mask], F[mask]

        if d.size < 2:
            raise ValueError("Need at least two finite samples for FDCurve1D.")

        d, A, phi, F = _average_duplicate_x(d, A, phi, F)

        if d.size < 2 or not np.all(np.diff(d) > 0):
            raise ValueError("d must contain at least two unique increasing values.")

        self.d = d
        self.A = A
        self.phi = phi
        self.F = F
        self.A0 = float(A[-1] if self.A0 is None else self.A0)

        phi_unwrapped = _unwrap_phase_deg(phi)

        if self.kind == "pchip":
            self._A_interp = _safe_pchip(
                d,
                A,
                left=A[0],
                right=self.A0,
            )
            self._phi_interp = _safe_pchip(
                d,
                phi_unwrapped,
                left=phi_unwrapped[0],
                right=phi_unwrapped[-1],
            )
            self._F_interp = _safe_pchip(
                d,
                F,
                left=F[0],
                right=0.0,
            )
        else:
            self._A_interp = interp1d(
                d,
                A,
                kind=self.kind,
                bounds_error=False,
                fill_value=(A[0], self.A0),
            )
            self._phi_interp = interp1d(
                d,
                phi_unwrapped,
                kind=self.kind,
                bounds_error=False,
                fill_value=(phi_unwrapped[0], phi_unwrapped[-1]),
            )
            self._F_interp = interp1d(
                d,
                F,
                kind=self.kind,
                bounds_error=False,
                fill_value=(F[0], 0.0),
            )

    def distance_range(self):
        return float(self.d[0]), float(self.d[-1])

    def A0_at_drive(self, drive_nm=None):
        return float(self.A0)

    def evaluate(self, d_query, return_flags: bool = False):
        
        scalar = np.isscalar(d_query)

        dq = np.atleast_1d(np.asarray(d_query, dtype=float))
        dq_clip = np.clip(dq, self.d[0], self.d[-1])

        A = np.asarray(self._A_interp(dq_clip), dtype=float)
        phi = np.asarray(self._phi_interp(dq_clip), dtype=float)
        F = np.asarray(self._F_interp(dq_clip), dtype=float)

        below = dq < self.d[0]
        above = dq > self.d[-1]

        # For d below the extrapolated zero-amplitude point:
        # A remains zero, not finite-clamped.
        if np.any(below):
            A[below] = 0.0
            phi[below] = self.phi[0]
            F[below] = self.F[0]

        # Far field.
        if np.any(above):
            A[above] = self.A0
            phi[above] = self.phi[-1]
            F[above] = 0.0

        # Prevent unphysical negative amplitude from interpolation overshoot.
        A = np.maximum(A, 0.0)

        if scalar:
            if return_flags:
                flags = {
                    "below_fd_range": bool(below[0]),
                    "above_fd_range": bool(above[0]),
                    "d_min": float(self.d[0]),
                    "d_max": float(self.d[-1]),
                }
                return float(A[0]), float(phi[0]), float(F[0]), flags

            return float(A[0]), float(phi[0]), float(F[0])

        if return_flags:
            flags = {
                "below_fd_range": below,
                "above_fd_range": above,
                "d_min": float(self.d[0]),
                "d_max": float(self.d[-1]),
            }
            return A, phi, F, flags

        return A, phi, F

    def __call__(self, d_query):
        return self.evaluate(d_query)


class FDDriveSurface:
    """Continuous FD surface over drive and distance.

    The surface stores normalized amplitude a=A/A0 and unwrapped phase. The
    drive interpolation is linear. The per-curve resampling along distance is
    PCHIP by default.
    """

    def __init__(
        self,
        *,
        x_mode: str = "d_over_A0",
        far_field_frac: float = 0.10,
        common_range: str = "intersection",
        n_x: int = 512,
        interp_kind_1d: str = "pchip",
        right_fill_free: bool = True,
    ) -> None:
        if x_mode not in {"d_over_A0", "absolute_d"}:
            raise ValueError("x_mode must be 'd_over_A0' or 'absolute_d'")
        if common_range not in {"intersection", "union"}:
            raise ValueError("common_range must be 'intersection' or 'union'")

        self.x_mode = x_mode
        self.far_field_frac = float(far_field_frac)
        self.common_range = common_range
        self.n_x = int(n_x)
        self.interp_kind_1d = interp_kind_1d
        self.right_fill_free = bool(right_fill_free)

        self._raw: Dict[float, Dict[str, np.ndarray]] = {}
        self._built = False

    @property
    def drives(self) -> np.ndarray:
        return np.array(sorted(self._raw.keys()), dtype=float)

    @property
    def x_grid(self) -> np.ndarray:
        self._require_built()
        return self._x_grid

    def add_curve(
        self,
        drive_nm: float,
        d_nm: ArrayLike,
        A_nm: ArrayLike,
        phi_deg: ArrayLike,
        F: Optional[ArrayLike] = None,
        *,
        A0_nm: Optional[float] = None,
        d_offset_nm: float = 0.0,
        far_field_side: str = "largest_d",
    ) -> None:
        """Add one measured curve.

        Parameters
        ----------
        drive_nm
            Commanded or calibrated drive/free-amplitude label in nm.
        d_nm
            Separation-like coordinate. Larger d should mean farther from the
            surface. If your measured origin is arbitrary, use d_offset_nm.
        A_nm, phi_deg
            Measured amplitude and phase.
        A0_nm
            Optional explicit free amplitude. If omitted, it is estimated from
            the far-field tail specified by far_field_side.
        far_field_side
            'largest_d', 'smallest_d', 'start', or 'end'. For your screenshot,
            use 'largest_d' or the default.
        """
        drv = float(drive_nm)
        d = _as_1d(d_nm, "d_nm") + float(d_offset_nm)
        A = _as_1d(A_nm, "A_nm")
        phi = _as_1d(phi_deg, "phi_deg")
        F_arr = np.zeros_like(d) if F is None else _as_1d(F, "F")
        if not (d.shape == A.shape == phi.shape == F_arr.shape):
            raise ValueError("d, A, phi, and F must have the same shape")

        mask = _finite_mask(d, A, phi, F_arr)
        d, A, phi, F_arr = d[mask], A[mask], phi[mask], F_arr[mask]
        if d.size < 3:
            raise ValueError(f"drive {drv}: need at least 3 finite samples")

        d, A, phi, F_arr = _average_duplicate_x(d, A, phi, F_arr)

        if A0_nm is None:
            n_far = max(1, int(round(self.far_field_frac * d.size)))
            if far_field_side == "largest_d":
                idx_far = np.argsort(d)[-n_far:]
            elif far_field_side == "smallest_d":
                idx_far = np.argsort(d)[:n_far]
            elif far_field_side == "start":
                idx_far = np.arange(n_far)
            elif far_field_side == "end":
                idx_far = np.arange(d.size - n_far, d.size)
            else:
                raise ValueError("far_field_side must be largest_d, smallest_d, start, or end")
            A0 = float(np.nanmedian(A[idx_far]))
        else:
            A0 = float(A0_nm)

        if not np.isfinite(A0) or A0 <= 0:
            raise ValueError(f"drive {drv}: invalid A0={A0}")

        self._raw[drv] = {
            "d": d,
            "A": A,
            "phi": phi,
            "F": F_arr,
            "A0": np.array([A0], dtype=float),
        }
        self._built = False

    @classmethod
    def from_measured_fd(
        cls,
        measured_fd: Dict[float, Dict[str, ArrayLike]],
        *,
        x_mode: str = "d_over_A0",
        far_field_frac: float = 0.10,
        common_range: str = "intersection",
        n_x: int = 512,
        far_field_side: str = "largest_d",
        drive_key_is_A0: bool = False,
    ) -> "FDDriveSurface":
        """Build from {drive: {'d':..., 'A':..., 'phi':..., optional 'F':...}}."""
        surf = cls(
            x_mode=x_mode,
            far_field_frac=far_field_frac,
            common_range=common_range,
            n_x=n_x,
        )
        for drv, c in measured_fd.items():
            A0 = float(drv) if drive_key_is_A0 else c.get("A0_nm", None)
            surf.add_curve(
                float(drv), c["d"], c["A"], c["phi"], F=c.get("F"),
                A0_nm=A0, far_field_side=far_field_side,
            )
        surf.build()
        return surf

    def build(self) -> "FDDriveSurface":
        drives = self.drives
        if drives.size < 1:
            raise ValueError("No curves have been added")
        if drives.size < 2:
            raise ValueError("Need at least two drives for continuous drive interpolation")

        x_mins: List[float] = []
        x_maxs: List[float] = []
        prepared: List[Tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = []

        for drv in drives:
            c = self._raw[float(drv)]
            d = c["d"]
            A = c["A"]
            phi = _unwrap_phase_deg(c["phi"])
            F = c["F"]
            A0 = float(c["A0"][0])

            x = d / A0 if self.x_mode == "d_over_A0" else d.copy()
            a = A / A0

            x, a, phi, F = _average_duplicate_x(x, a, phi, F)
            x_mins.append(float(x[0]))
            x_maxs.append(float(x[-1]))
            prepared.append((float(drv), x, a, phi, F, A0))

        if self.common_range == "intersection":
            x_min = max(x_mins)
            x_max = min(x_maxs)
            if not x_max > x_min:
                raise ValueError(
                    "No overlapping distance range across curves. Use common_range='union', "
                    "trim curves, or align d-offsets first."
                )
        else:
            x_min = min(x_mins)
            x_max = max(x_maxs)

        self._x_grid = np.linspace(x_min, x_max, self.n_x)
        nD, nX = drives.size, self._x_grid.size
        a_grid = np.empty((nD, nX), dtype=float)
        phi_grid = np.empty((nD, nX), dtype=float)
        F_grid = np.empty((nD, nX), dtype=float)
        A0_by_drive = np.empty(nD, dtype=float)

        for i, (drv, x, a, phi, F, A0) in enumerate(prepared):
            # Far-field fill: a -> 1, phase -> far-field phase, F -> 0.
            a_left, a_right = float(a[0]), 1.0 if self.right_fill_free else float(a[-1])
            phi_left, phi_right = float(phi[0]), float(phi[-1])
            F_left, F_right = float(F[0]), 0.0

            if self.interp_kind_1d == "pchip":
                a_interp = _safe_pchip(x, a, a_left, a_right)
                p_interp = _safe_pchip(x, phi, phi_left, phi_right)
                f_interp = _safe_pchip(x, F, F_left, F_right)
                xq = np.clip(self._x_grid, x[0], x[-1])
                a_grid[i] = a_interp(xq)
                phi_grid[i] = p_interp(xq)
                F_grid[i] = f_interp(xq)
                # Manual edge fill after clipping.
                left = self._x_grid < x[0]
                right = self._x_grid > x[-1]
                a_grid[i, left] = a_left
                phi_grid[i, left] = phi_left
                F_grid[i, left] = F_left
                a_grid[i, right] = a_right
                phi_grid[i, right] = phi_right
                F_grid[i, right] = F_right
            else:
                a_grid[i] = np.interp(self._x_grid, x, a, left=a_left, right=a_right)
                phi_grid[i] = np.interp(self._x_grid, x, phi, left=phi_left, right=phi_right)
                F_grid[i] = np.interp(self._x_grid, x, F, left=F_left, right=F_right)

            A0_by_drive[i] = A0

        self._drives = drives
        self._A0_by_drive = A0_by_drive
        self._a_grid = a_grid
        self._phi_grid = phi_grid
        self._F_grid = F_grid

        self._a_rgi = RegularGridInterpolator((drives, self._x_grid), a_grid,
                                               method="linear", bounds_error=False, fill_value=None)
        self._phi_rgi = RegularGridInterpolator((drives, self._x_grid), phi_grid,
                                                 method="linear", bounds_error=False, fill_value=None)
        self._F_rgi = RegularGridInterpolator((drives, self._x_grid), F_grid,
                                               method="linear", bounds_error=False, fill_value=None)
        self._A0_rgi = interp1d(drives, A0_by_drive, kind="linear", bounds_error=False,
                                fill_value=(A0_by_drive[0], A0_by_drive[-1]))
        self._built = True
        return self

    def _require_built(self) -> None:
        if not self._built:
            self.build()

    def evaluate(self, d_nm: ArrayLike, drive_nm: float):
        """Evaluate the FD surface at arbitrary physical drive and distance.

        Returns A_nm, phi_deg, F. Scalar input returns scalars; array input
        returns arrays.
        """
        self._require_built()
        scalar = np.isscalar(d_nm)
        d_arr = np.atleast_1d(np.asarray(d_nm, dtype=float))
        drv = float(drive_nm)
        drv_clip = float(np.clip(drv, self._drives[0], self._drives[-1]))

        # Use the target drive as A0 scaling. This lets the nearest normalized
        # curve scale reasonably if drive is slightly outside the measured range.
        A0_target = float(self._A0_rgi(drv_clip))
        if self.x_mode == "d_over_A0":
            xq = d_arr / max(A0_target, 1e-30)
        else:
            xq = d_arr
        xq = np.clip(xq, self._x_grid[0], self._x_grid[-1])

        pts = np.column_stack([np.full_like(xq, drv_clip, dtype=float), xq])
        a = np.asarray(self._a_rgi(pts), dtype=float)
        phi = np.asarray(self._phi_rgi(pts), dtype=float)
        F = np.asarray(self._F_rgi(pts), dtype=float)

        A = a * A0_target
        if scalar:
            return float(A[0]), float(phi[0]), float(F[0])
        return A, phi, F

    def fd_at_drive(self, drive_nm: float, n_points: Optional[int] = None) -> FDCurve1D:
        """Return a single-drive FDCurve1D at any target drive."""
        self._require_built()
        n = self.n_x if n_points is None else int(n_points)
        x = self._x_grid if n == self._x_grid.size else np.linspace(self._x_grid[0], self._x_grid[-1], n)
        drv = float(drive_nm)
        drv_clip = float(np.clip(drv, self._drives[0], self._drives[-1]))
        A0_target = float(self._A0_rgi(drv_clip))

        d = x * A0_target if self.x_mode == "d_over_A0" else x.copy()
        A, phi, F = self.evaluate(d, drv)
        return FDCurve1D(d=d, A=A, phi=phi, F=F, A0=A0_target, kind="pchip")

    def __call__(self, drive_nm: float) -> FDCurve1D:
        return self.fd_at_drive(drive_nm)

    def diagnostics(self) -> Dict[str, np.ndarray]:
        self._require_built()
        return {
            "drives": self._drives.copy(),
            "A0_by_drive": self._A0_by_drive.copy(),
            "x_grid": self._x_grid.copy(),
            "a_grid": self._a_grid.copy(),
            "phi_grid": self._phi_grid.copy(),
            "F_grid": self._F_grid.copy(),
        }

    def A0_at_drive(self, drive_nm: float) -> float:
        """
        Interpolate free amplitude A0 at arbitrary drive.

        Returns A0 in the same amplitude units used by FDDriveSurface,
        usually nm before Scanner normalization.
        """
        self._require_built()

        drive_nm = float(drive_nm)
        drive_clip = float(np.clip(drive_nm, self._drives[0], self._drives[-1]))

        return float(self._A0_rgi(drive_clip))


    def distance_range(self, drive_nm: Optional[float] = None):
        """
        Return calibrated distance range in FDDriveSurface units.

        If x_mode == "absolute_d":
            distance range is independent of drive.

        If x_mode == "d_over_A0":
            internal coordinate is d/A0, so physical distance range depends on A0(drive).
        """
        self._require_built()

        x_min = float(self._x_grid[0])
        x_max = float(self._x_grid[-1])

        if self.x_mode == "absolute_d":
            return x_min, x_max

        if drive_nm is None:
            A0_min = float(np.min(self._A0_by_drive))
            A0_max = float(np.max(self._A0_by_drive))
            return x_min * A0_min, x_max * A0_max

        A0 = self.A0_at_drive(float(drive_nm))
        return x_min * A0, x_max * A0


class NormalizedDriveFD:
    """
    Adapter from FDDriveSurface physical units to ScannerFD normalized units.

    Underlying FDDriveSurface expects:
        d_nm, drive_nm

    ScannerFD uses:
        d_hat

    Conversion:
        d_hat = d_nm * conv_L
        A_hat = A_nm * conv_A
        F_hat = F_raw * conv_F
    """

    def __init__(
        self,
        surface,
        *,
        conv_L: float,
        conv_A: Optional[float] = None,
        conv_F: float = 1.0,
    ):
        self.surface = surface
        self.conv_L = float(conv_L)
        self.conv_A = float(conv_L if conv_A is None else conv_A)
        self.conv_F = float(conv_F)

    def A0_at_drive(self, drive_nm: float) -> float:
        return float(self.surface.A0_at_drive(float(drive_nm)) * self.conv_A)

    def distance_range(self, drive_nm: Optional[float] = None):
        d_min_nm, d_max_nm = self.surface.distance_range(drive_nm)
        return float(d_min_nm * self.conv_L), float(d_max_nm * self.conv_L)

    def evaluate(self, d_hat, drive_nm=None, return_flags: bool = False):
        if drive_nm is None:
            raise ValueError(
                "NormalizedDriveFD.evaluate requires drive_nm. "
                "Use evaluate(d_hat, drive_nm=...)."
            )

        scalar = np.isscalar(d_hat)

        d_hat_arr = np.atleast_1d(np.asarray(d_hat, dtype=float))
        d_nm_arr = d_hat_arr / self.conv_L

        d_min_hat, d_max_hat = self.distance_range(float(drive_nm))
        below = d_hat_arr < d_min_hat
        above = d_hat_arr > d_max_hat

        A_nm, phi_deg, F_raw = self.surface.evaluate(
            d_nm_arr,
            float(drive_nm),
        )

        A_hat = np.asarray(A_nm, dtype=float) * self.conv_A
        phi_deg = np.asarray(phi_deg, dtype=float)
        F_hat = np.asarray(F_raw, dtype=float) * self.conv_F

        if scalar:
            if return_flags:
                flags = {
                    "below_fd_range": bool(below[0]),
                    "above_fd_range": bool(above[0]),
                    "d_min": float(d_min_hat),
                    "d_max": float(d_max_hat),
                }
                return (
                    float(A_hat[0]),
                    float(phi_deg[0]),
                    float(F_hat[0]),
                    flags,
                )

            return float(A_hat[0]), float(phi_deg[0]), float(F_hat[0])

        if return_flags:
            flags = {
                "below_fd_range": below,
                "above_fd_range": above,
                "d_min": float(d_min_hat),
                "d_max": float(d_max_hat),
            }
            return A_hat, phi_deg, F_hat, flags

        return A_hat, phi_deg, F_hat


def make_normalized_fd_lookup(
    surface: FDDriveSurface,
    *,
    conv_L: float,
    conv_A: Optional[float] = None,
    conv_F: float = 1.0,
    n_points: Optional[int] = None,
):
    """
    Return a drive-dependent FD model in ScannerFD normalized units.

    Preferred usage:
        fd_model = make_normalized_fd_lookup(surface, conv_L=conv_L)
        scanner = ScannerFD(params, conversions, fd_model)

    The returned object supports:
        fd_model.evaluate(d_hat, drive_nm=drive_nm)
        fd_model.A0_at_drive(drive_nm)
        fd_model.distance_range(drive_nm)

    n_points is kept for backward compatibility but is not used in this wrapper.
    """
    return NormalizedDriveFD(
        surface=surface,
        conv_L=conv_L,
        conv_A=conv_A,
        conv_F=conv_F,
    )


import numpy as np
from types import MethodType


def attach_continuous_fd_to_scanner(
    scanner,
    fd_lookup,
    conv_A=None,
):
    """
    Attach continuous-drive FD lookup to an existing ScannerFD instance.

    This works even if scanner only has scan_line_pi() and does not already
    have scan_line_trace_retrace_pi().

    Parameters
    ----------
    scanner : existing ScannerFD-like object
        Must have scan_line_pi().
    fd_lookup : callable
        fd_lookup(drive_nm) -> FDCurve1D in normalized units.
    conv_A : float
        Conversion from drive_nm to scanner-normalized amplitude.
        Usually scanner.conversion["A"].
    """

    if conv_A is None:
        conv_A = scanner.conversion.get("A", 1.0)

    scanner._continuous_fd_lookup = fd_lookup
    scanner._continuous_fd_conv_A = float(conv_A)

    def set_drive(self, drive_nm=None, drive_hat=None):
        if drive_nm is None and drive_hat is None:
            raise ValueError("Pass either drive_nm or drive_hat.")

        if drive_nm is None:
            drive_hat = float(drive_hat)
            drive_nm = drive_hat / self._continuous_fd_conv_A
        else:
            drive_nm = float(drive_nm)
            drive_hat = drive_nm * self._continuous_fd_conv_A

        fd_model = self._continuous_fd_lookup(drive_nm)

        # Classic ScannerFD expects fd_model directly.
        self.fd_model = fd_model

        # Keep amplitude bookkeeping consistent.
        if hasattr(self, "param"):
            self.param["A"] = drive_nm

        if hasattr(self, "param_norm"):
            self.param_norm["A"] = drive_hat
            if "Q" in self.param_norm:
                self.param_norm["C3"] = self.param_norm["A"] / self.param_norm["Q"]

        self.drive_nm_current = drive_nm
        self.drive_hat_current = drive_hat

        return fd_model

    def _pack_carry_state_from_trace(out):
        """
        Convert final state from trace into initial state for retrace.
        Only includes keys that actually exist in your scan_line_pi output.
        """
        pairs = {
            "d_cmd_init_hat": "d_cmd_final_hat",
            "d_act_init_hat": "d_final_hat",
            "A_meas_init_hat": "A_meas_final_hat",
            "phi_meas_init_deg": "phi_meas_final_deg",
            "integ_init": "integ_final",
            "drift_init_hat": "drift_final_hat",
        }

        carry = {}
        for init_key, final_key in pairs.items():
            if final_key in out:
                carry[init_key] = out[final_key]

        return carry

    def _flip_line_output(out):
        """
        Reverse 1D pixel arrays so retrace is returned in the same x-order
        as trace.
        """
        flipped = {}
        for k, v in out.items():
            if isinstance(v, np.ndarray) and v.ndim == 1:
                flipped[k] = v[::-1].copy()
            else:
                flipped[k] = v
        return flipped

    def scan_line_trace_retrace_pi_fallback(
        self,
        h_hat,
        retrace_carry_state=True,
        retrace_use_reversed_topography=True,
        **line_kwargs,
    ):
        h_hat = np.asarray(h_hat, dtype=float)

        # Trace
        out_trace = self.scan_line_pi(
            h_hat=h_hat,
            **line_kwargs,
        )

        # Retrace topography
        if retrace_use_reversed_topography:
            h_retrace = h_hat[::-1]
        else:
            h_retrace = h_hat.copy()

        # Carry state if available
        retrace_kwargs = dict(line_kwargs)
        if retrace_carry_state:
            retrace_kwargs.update(_pack_carry_state_from_trace(out_trace))

        out_retrace_raw = self.scan_line_pi(
            h_hat=h_retrace,
            **retrace_kwargs,
        )

        out_retrace = _flip_line_output(out_retrace_raw)

        return {
            "trace": out_trace,
            "retrace": out_retrace,
        }

    def scan_line_trace_retrace_pi_drive(
        self,
        h_hat,
        drive_nm=None,
        drive_hat=None,
        setpoint=None,
        setpoint_hat=None,
        **kwargs,
    ):
        fd_model = self.set_drive(drive_nm=drive_nm, drive_hat=drive_hat)

        if setpoint is None:
            if setpoint_hat is None:
                raise ValueError("Pass either setpoint fraction or setpoint_hat.")

            if hasattr(fd_model, "A0"):
                A0_hat = float(fd_model.A0)
            elif hasattr(fd_model, "free_amplitude"):
                A0_hat = float(fd_model.free_amplitude())
            else:
                A0_hat = float(self.param_norm["A"])

            setpoint = float(setpoint_hat) / A0_hat

        # If your scanner already has a native trace/retrace method, use it.
        # Otherwise use the fallback we attach below.
        return self.scan_line_trace_retrace_pi(
            h_hat=h_hat,
            setpoint=float(setpoint),
            **kwargs,
        )

    scanner.set_drive = MethodType(set_drive, scanner)

    if not hasattr(scanner, "scan_line_trace_retrace_pi"):
        scanner.scan_line_trace_retrace_pi = MethodType(
            scan_line_trace_retrace_pi_fallback,
            scanner,
        )

    scanner.scan_line_trace_retrace_pi_drive = MethodType(
        scan_line_trace_retrace_pi_drive,
        scanner,
    )

    return scanner


def detect_bad_curves(
    measured_fd: Dict[float, Dict[str, ArrayLike]],
    *,
    phase_jump_threshold_deg: float = 30.0,
    amp_jump_threshold_rel: float = 0.20,
) -> Dict[float, Dict[str, float]]:
    """Flag curves with abrupt phase or normalized-amplitude jumps."""
    flags: Dict[float, Dict[str, float]] = {}
    for drv, c in measured_fd.items():
        d = _as_1d(c["d"], "d")
        A = _as_1d(c["A"], "A")
        phi = _as_1d(c["phi"], "phi")
        mask = _finite_mask(d, A, phi)
        d, A, phi = d[mask], A[mask], phi[mask]
        if d.size < 3:
            continue
        order = np.argsort(d)
        d, A, phi = d[order], A[order], phi[order]
        A0 = float(c.get("A0_nm", np.nanmedian(A[np.argsort(d)[-max(1, int(0.1 * d.size)):]])))
        dphi = np.abs(np.diff(_unwrap_phase_deg(phi)))
        da = np.abs(np.diff(A / max(A0, 1e-30)))
        if np.nanmax(dphi) > phase_jump_threshold_deg or np.nanmax(da) > amp_jump_threshold_rel:
            i = int(np.nanargmax(dphi)) if np.nanmax(dphi) / phase_jump_threshold_deg >= np.nanmax(da) / amp_jump_threshold_rel else int(np.nanargmax(da))
            flags[float(drv)] = {
                "max_dphi_deg": float(np.nanmax(dphi)),
                "max_da_rel": float(np.nanmax(da)),
                "d_at_jump_nm": float(d[i]),
            }
    return flags


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

def unpack_controller_params_4(x):
    log10_P, log10_I, log10_tau_A, log10_tau_phi = x

    return {
        "P": 10.0 ** log10_P,
        "I": 10.0 ** log10_I,
        "tau_A": 10.0 ** log10_tau_A,
        "tau_phi": 10.0 ** log10_tau_phi,
    }


def make_scan_objective_exp_4param(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    # Fixed scanner parameters
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,

    verbose=False,
):
    h_input = np.asarray(h_input, dtype=float)

    def objective(x, return_full=False):
        p = unpack_controller_params_4(x)

        try:
            out = scanner.scan_line_trace_retrace_pi_drive(
                h_hat=h_input,
                drive_nm=drive,
                setpoint=setpoint,

                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,

                P=p["P"],
                I=p["I"],

                A_filter_order=1,
                tau_A=p["tau_A"],

                phi_filter_order=1,
                tau_phi=p["tau_phi"],

                z_filter_order=1,
                tau_z=tau_z,

                z_rate_limit_hat=z_rate_limit_hat,

                d_init_hat=d_init_hat,
                phi_meas_init_deg=phi_meas_init_deg,
                T_I=T_I,
            )

            loss, details = score_scan_against_experiment(
                out=out,
                h_exp=h_exp,
                trim=trim,
                w_height_match=w_height_match,
                w_mse_match=w_mse_match,
                w_diff_profile=w_diff_profile,
                w_ringing=w_ringing,
                w_amp=w_amp,
                drive=drive,
                setpoint=setpoint,
                huber_delta=huber_delta,
                mse_floor_frac=mse_floor_frac,
            )

            if not np.isfinite(loss):
                loss = 1e12

        except Exception as e:
            if verbose:
                print("Simulation failed:", e)

            loss = 1e12
            details = {"error": str(e)}
            out = None

        if return_full:
            return loss, details, out, p
        else:
            return loss

    return objective

def fit_controller_to_experiment_4param(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    # Fixed scanner parameters
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,

    # Optimizer controls
    maxiter_global=80,
    maxiter_local=300,
    global_tol=0.02,
    local_xatol=1e-3,
    local_fatol=1e-4,
    loss_target=None,
    seed=0,
    popsize=10,

    # Bounds in log10-space
    bounds=None,

    verbose=True,
):
    if bounds is None:
        bounds = [
            (-4.0, 2.0),    # log10_P:     1e-2 to ~32
            (-4.0, 2.0),   # log10_I:     effectively 0 to 1e4
            (-4.0, 1.0),   # log10_tau_A: 3e-6 to 1e-2
            (-4.0, 1.0),   # log10_tau_phi: 1e-7 to 1e-3
        ]

    objective = make_scan_objective_exp_4param(
        scanner=scanner,
        h_input=h_input,
        h_exp=h_exp,
        drive=drive,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        tau_z=tau_z,
        z_rate_limit_hat=z_rate_limit_hat,
        d_init_hat=d_init_hat,
        phi_meas_init_deg=phi_meas_init_deg,
        T_I=T_I,
        trim=trim,
        w_height_match=w_height_match,
        w_mse_match=w_mse_match,
        w_diff_profile=w_diff_profile,
        w_ringing=w_ringing,
        w_amp=w_amp,
        huber_delta=huber_delta,
        mse_floor_frac=mse_floor_frac,
        verbose=verbose,
    )

    best_seen = {"loss": np.inf, "x": None}

    def callback(xk, convergence):
        loss = objective(xk)

        if loss < best_seen["loss"]:
            best_seen["loss"] = loss
            best_seen["x"] = np.array(xk, dtype=float)

            if verbose:
                p = unpack_controller_params_4(xk)
                _, details, _, _ = objective(xk, return_full=True)

                print(
                    f"loss={loss:.5g}, "
                    f"P={p['P']:.4g}, I={p['I']:.4g}, "
                    f"tau_A={p['tau_A']:.4g}, tau_phi={p['tau_phi']:.4g}, "
                    f"mse_ratio={details.get('mse_ratio', np.nan):.4g}"
                )

        if loss_target is not None and loss <= loss_target:
            if verbose:
                print(f"Stopping early because loss <= loss_target = {loss_target}")
            return True

        return False

    res_global = differential_evolution(
        objective,
        bounds=bounds,
        seed=seed,
        maxiter=maxiter_global,
        popsize=popsize,
        tol=global_tol,
        polish=False,
        updating="immediate",
        workers=1,
        callback=callback,
    )

    if best_seen["x"] is not None and best_seen["loss"] < res_global.fun:
        x0 = best_seen["x"]
    else:
        x0 = res_global.x

    res_local = minimize(
        objective,
        x0,
        method="Nelder-Mead",
        options={
            "maxiter": maxiter_local,
            "xatol": local_xatol,
            "fatol": local_fatol,
        },
    )

    if res_local.fun < res_global.fun:
        best_x = res_local.x
        best_source = "local"
    else:
        best_x = res_global.x
        best_source = "global"

    best_loss, best_details, best_out, best_params = objective(
        best_x,
        return_full=True,
    )

    return {
        "best_x": best_x,
        "best_params": best_params,
        "best_loss": best_loss,
        "best_details": best_details,
        "best_out": best_out,
        "best_source": best_source,
        "res_global": res_global,
        "res_local": res_local,
        "objective": objective,
    }

def plot_fit_to_experiment(fit, h_exp):
    out = fit["best_out"]

    exp_tr, exp_rt = parse_h_exp(h_exp)

    sim_tr = np.asarray(out["trace"]["d_hat"], dtype=float)
    sim_rt = np.asarray(out["retrace"]["d_hat"], dtype=float)

    sim_tr, sim_rt, exp_tr, exp_rt = crop_to_common_length(
        sim_tr, sim_rt, exp_tr, exp_rt
    )

    sim_tr_aligned, sim_rt_aligned, offset = apply_common_height_offset(
        sim_tr,
        sim_rt,
        exp_tr,
        exp_rt,
    )

    x = np.arange(len(exp_tr))

    fig, ax = plt.subplots(1, 4, figsize=(15, 3.3))

    ax[0].plot(x, exp_tr, "k--", label="exp trace")
    ax[0].plot(x, exp_rt, "k:", label="exp retrace")
    ax[0].plot(x, sim_tr_aligned, label="sim trace")
    ax[0].plot(x, sim_rt_aligned, label="sim retrace")
    ax[0].set_title("Height lines")
    ax[0].set_ylabel("Height")
    ax[0].legend()

    ax[1].plot(x, sim_tr_aligned - exp_tr, label="trace residual")
    ax[1].plot(x, sim_rt_aligned - exp_rt, label="retrace residual")
    ax[1].axhline(0, color="k", lw=1)
    ax[1].set_title("Residuals")
    ax[1].legend()

    diff_exp = exp_tr - exp_rt
    diff_sim = sim_tr_aligned - sim_rt_aligned

    ax[2].plot(x, diff_exp, "k--", label="exp trace-retrace")
    ax[2].plot(x, diff_sim, label="sim trace-retrace")
    ax[2].set_title("Trace-retrace difference")
    ax[2].legend()

    mse_exp = np.mean(diff_exp**2)
    mse_sim = np.mean(diff_sim**2)

    ax[3].bar([0, 1], [mse_exp, mse_sim])
    ax[3].set_xticks([0, 1])
    ax[3].set_xticklabels(["exp", "sim"])
    ax[3].set_title("Trace-retrace MSE")

    title = (
        f"loss={fit['best_loss']:.4g}, "
        f"P={fit['best_params']['P']:.3g}, "
        f"I={fit['best_params']['I']:.3g}, "
        f"tau_A={fit['best_params']['tau_A']:.3g}, "
        f"tau_phi={fit['best_params']['tau_phi']:.3g}, "
        f"MSE ratio={fit['best_details']['mse_ratio']:.3g}"
    )

    fig.suptitle(title, y=1.06)
    plt.tight_layout()
    plt.show()


# unpack_controller_params_PI_fixed_tau
import numpy as np
from scipy.optimize import differential_evolution, minimize


def unpack_controller_params_PI_fixed_tau(x, tau_A_fixed, tau_phi_fixed):
    """
    x = [log10_P, log10_I]
    """

    log10_P, log10_I = np.asarray(x, dtype=float)

    return {
        "P": 10.0 ** log10_P,
        "I": 10.0 ** log10_I,
        "tau_A": float(tau_A_fixed),
        "tau_phi": float(tau_phi_fixed),
        "log10_P": float(log10_P),
        "log10_I": float(log10_I),
        "log10_tau_A": float(np.log10(tau_A_fixed)),
        "log10_tau_phi": float(np.log10(tau_phi_fixed)),
    }


def make_scan_objective_exp_PI_fixed_tau(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    tau_A_fixed=1e-4,
    tau_phi_fixed=1e-4,

    # Fixed scanner parameters
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,

    verbose=False,
):
    """
    Wrapper around your existing 4-parameter objective.

    The original objective expects:

        x4 = [log10_P, log10_I, log10_tau_A, log10_tau_phi]

    This wrapper exposes only:

        x2 = [log10_P, log10_I]

    while keeping tau_A and tau_phi fixed.
    """

    if tau_A_fixed <= 0:
        raise ValueError("tau_A_fixed must be positive.")
    if tau_phi_fixed <= 0:
        raise ValueError("tau_phi_fixed must be positive.")

    log10_tau_A_fixed = np.log10(tau_A_fixed)
    log10_tau_phi_fixed = np.log10(tau_phi_fixed)

    base_objective = make_scan_objective_exp_4param(
        scanner=scanner,
        h_input=h_input,
        h_exp=h_exp,
        drive=drive,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        tau_z=tau_z,
        z_rate_limit_hat=z_rate_limit_hat,
        d_init_hat=d_init_hat,
        phi_meas_init_deg=phi_meas_init_deg,
        T_I=T_I,
        trim=trim,
        w_height_match=w_height_match,
        w_mse_match=w_mse_match,
        w_diff_profile=w_diff_profile,
        w_ringing=w_ringing,
        w_amp=w_amp,
        huber_delta=huber_delta,
        mse_floor_frac=mse_floor_frac,
        verbose=verbose,
    )

    def objective(x2, return_full=False):
        x2 = np.asarray(x2, dtype=float)

        log10_P = x2[0]
        log10_I = x2[1]

        x4 = np.array([
            log10_P,
            log10_I,
            log10_tau_A_fixed,
            log10_tau_phi_fixed,
        ], dtype=float)

        if return_full:
            loss, details, out, params = base_objective(
                x4,
                return_full=True,
            )

            # Make sure the returned params explicitly show fixed tau values.
            params = dict(params)
            params["tau_A"] = float(tau_A_fixed)
            params["tau_phi"] = float(tau_phi_fixed)
            params["log10_tau_A"] = float(log10_tau_A_fixed)
            params["log10_tau_phi"] = float(log10_tau_phi_fixed)

            return loss, details, out, params

        return base_objective(x4)

    return objective

def fit_controller_to_experiment_PI_fixed_tau(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    tau_A_fixed=1e-4,
    tau_phi_fixed=1e-4,

    # Fixed scanner parameters
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,

    # Optimizer controls
    maxiter_global=200,
    maxiter_local=300,
    global_tol=0.02,
    local_xatol=1e-3,
    local_fatol=1e-4,
    loss_target=None,
    seed=0,
    popsize=8,

    # Bounds in log10-space
    bounds=None,

    verbose=True,
):
    """
    Refit only P and I while keeping tau_A and tau_phi fixed.

    Optimized vector:

        x = [log10_P, log10_I]
    """

    if bounds is None:
        bounds = [
            (-4.0, 2.0),   # log10_P
            (-4.0, 2.0),   # log10_I
        ]

    objective = make_scan_objective_exp_PI_fixed_tau(
        scanner=scanner,
        h_input=h_input,
        h_exp=h_exp,
        drive=drive,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        tau_A_fixed=tau_A_fixed,
        tau_phi_fixed=tau_phi_fixed,
        tau_z=tau_z,
        z_rate_limit_hat=z_rate_limit_hat,
        d_init_hat=d_init_hat,
        phi_meas_init_deg=phi_meas_init_deg,
        T_I=T_I,
        trim=trim,
        w_height_match=w_height_match,
        w_mse_match=w_mse_match,
        w_diff_profile=w_diff_profile,
        w_ringing=w_ringing,
        w_amp=w_amp,
        huber_delta=huber_delta,
        mse_floor_frac=mse_floor_frac,
        verbose=False,
    )

    best_seen = {
        "loss": np.inf,
        "x": None,
    }

    def callback(xk, convergence):
        loss = objective(xk)

        if loss < best_seen["loss"]:
            best_seen["loss"] = float(loss)
            best_seen["x"] = np.array(xk, dtype=float)

            if verbose:
                p = unpack_controller_params_PI_fixed_tau(
                    xk,
                    tau_A_fixed=tau_A_fixed,
                    tau_phi_fixed=tau_phi_fixed,
                )

                _, details, _, _ = objective(xk, return_full=True)

                print(
                    f"loss={loss:.5g}, "
                    f"P={p['P']:.4g}, "
                    f"I={p['I']:.4g}, "
                    f"tau_A_fixed={p['tau_A']:.4g}, "
                    f"tau_phi_fixed={p['tau_phi']:.4g}, "
                    f"mse_ratio={details.get('mse_ratio', np.nan):.4g}"
                )

        if loss_target is not None and loss <= loss_target:
            if verbose:
                print(f"Stopping early because loss <= loss_target = {loss_target}")
            return True

        return False

    res_global = differential_evolution(
        objective,
        bounds=bounds,
        seed=seed,
        maxiter=maxiter_global,
        popsize=popsize,
        tol=global_tol,
        polish=False,
        updating="immediate",
        workers=1,
        callback=callback,
    )

    if best_seen["x"] is not None and best_seen["loss"] < res_global.fun:
        x0 = best_seen["x"]
    else:
        x0 = res_global.x

    res_local = minimize(
        objective,
        x0,
        method="Nelder-Mead",
        options={
            "maxiter": maxiter_local,
            "xatol": local_xatol,
            "fatol": local_fatol,
        },
    )

    if np.isfinite(res_local.fun) and res_local.fun < res_global.fun:
        best_x = res_local.x
        best_source = "local"
    else:
        best_x = res_global.x
        best_source = "global"

    best_loss, best_details, best_out, best_params = objective(
        best_x,
        return_full=True,
    )

    return {
        "best_x": best_x,
        "best_params": best_params,
        "best_loss": best_loss,
        "best_details": best_details,
        "best_out": best_out,
        "best_source": best_source,
        "res_global": res_global,
        "res_local": res_local,
        "objective": objective,
        "tau_A_fixed": tau_A_fixed,
        "tau_phi_fixed": tau_phi_fixed,
    }


def score_scan_against_experiment(
    out,
    h_exp,
    trim=20,

    # Main loss weights
    w_height_match=1.0,
    w_mse_match=0.5,

    # Optional regularizers
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,

    drive=20,
    setpoint=0.6,
    huber_delta=2.0,
    mse_floor_frac=0.03,
):
    """
    Objective:
    1. simulated trace/retrace height lines agree with experimental trace/retrace;
    2. simulated trace-retrace MSE is close to experimental trace-retrace MSE.

    No retrace reversal is applied.
    """

    exp_tr, exp_rt = parse_h_exp(h_exp)

    sim_tr = np.asarray(out["trace"]["d_hat"], dtype=float)
    sim_rt = np.asarray(out["retrace"]["d_hat"], dtype=float)

    # sim_tr, exp_tr = diff_shifted(sim_tr, exp_tr)
    # sim_rt, exp_rt = diff_shifted(sim_rt, exp_rt)

    sim_tr_use = sim_tr
    sim_rt_use = sim_rt
    exp_tr_use = exp_tr
    exp_rt_use = exp_rt

    exp_all = np.r_[exp_tr_use, exp_rt_use]
    exp_mid = 0.5 * (exp_tr_use + exp_rt_use)

    h_scale = 1

    # --------------------------------------------------------
    # 1. Height matching loss
    # --------------------------------------------------------
    r_height = np.r_[
        (sim_tr_use - exp_tr_use) / h_scale,
        (sim_rt_use - exp_rt_use) / h_scale,
    ]

    loss_height_match = np.nanmean(
        huber_loss(r_height, delta=huber_delta)
    )

    # --------------------------------------------------------
    # 2. Trace-retrace MSE matching loss
    # --------------------------------------------------------
    diff_sim = sim_tr_use - sim_rt_use
    diff_exp = exp_tr_use - exp_rt_use

    mse_sim = np.nanmean(diff_sim**2)
    mse_exp = np.nanmean(diff_exp**2)

    mse_floor = (mse_floor_frac * h_scale) ** 2

    # Log-ratio loss is better than raw MSE difference because MSE is positive
    # and can span orders of magnitude.
    loss_mse_match = (
        np.log((mse_sim + mse_floor) / (mse_exp + mse_floor))
    ) ** 2

    loss_noise = np.abs(np.std(exp_tr_use)-np.std(sim_tr_use))

    total = (
        w_height_match * loss_height_match
        + w_mse_match * loss_mse_match
        + loss_noise
        # + w_diff_profile * loss_diff_profile
        # + w_ringing * loss_ringing
        # + w_amp * loss_amp
    )
    
    # total = (
    #     w_height_match * loss_height_match
    #     + w_mse_match * loss_mse_match
    #     + w_diff_profile * loss_diff_profile
    #     + w_ringing * loss_ringing
    #     + w_amp * loss_amp
    # )

    details = {
        "total": total,
        "loss_height_match": loss_height_match,
        "loss_mse_match": loss_mse_match,
        # "loss_diff_profile": loss_diff_profile,
        # "loss_ringing": loss_ringing,
        # "loss_amp": loss_amp,
        "mse_sim": mse_sim,
        "mse_exp": mse_exp,
        "mse_ratio": mse_sim / (mse_exp + 1e-12),
        # "common_offset": common_offset,
        "h_scale": h_scale,
    }

    return total, details
    
import numpy as np


def estimate_zero_amplitude_distance_linear(
    d,
    A,
    *,
    n_fit=5,
    min_slope_abs=1e-12,
    max_back_extrap_factor=5.0,
):
    """
    Estimate the distance where A linearly extrapolates to zero
    from the near-contact side of an FD curve.

    Assumes d is increasing toward far field.
    Uses the first n_fit points after sorting by d.

    Returns
    -------
    d_zero : float
        Extrapolated distance where A = 0.
    fit_info : dict
    """
    d = np.asarray(d, dtype=float).ravel()
    A = np.asarray(A, dtype=float).ravel()

    mask = np.isfinite(d) & np.isfinite(A)
    d = d[mask]
    A = A[mask]

    order = np.argsort(d)
    d = d[order]
    A = A[order]

    if len(d) < 2:
        raise ValueError("Need at least two points to estimate zero-amplitude distance.")

    n_fit = int(min(max(2, n_fit), len(d)))

    d_fit = d[:n_fit]
    A_fit = A[:n_fit]

    # Linear fit: A = m d + b
    m, b = np.polyfit(d_fit, A_fit, deg=1)

    if abs(m) < min_slope_abs:
        # Fallback: use first two points.
        m = (A[1] - A[0]) / (d[1] - d[0] + 1e-12)
        b = A[0] - m * d[0]

    if abs(m) < min_slope_abs:
        # Still too flat; fallback to d=0.
        d_zero = 0.0
    else:
        d_zero = -b / m

    d_min = float(d[0])
    d_span = float(d[-1] - d[0])

    # Require the zero-amplitude point to be on the near-contact side.
    # If extrapolation gives a zero point inside or beyond measured data,
    # fallback to a short extrapolation below d_min.
    if not np.isfinite(d_zero) or d_zero >= d_min:
        A_min = float(A[0])
        slope = abs(m) + min_slope_abs
        d_zero = d_min - A_min / slope

    # Avoid absurdly far extrapolation.
    max_back = max_back_extrap_factor * max(d_span, 1e-12)
    if d_min - d_zero > max_back:
        d_zero = d_min - max_back

    return float(d_zero), {
        "slope": float(m),
        "intercept": float(b),
        "d_min": float(d_min),
        "A_min": float(A[0]),
        "n_fit": int(n_fit),
    }

def extend_fd_curve_linear_to_zero_amplitude(
    d,
    A,
    phi,
    F=None,
    *,
    n_fit=5,
    n_bridge=30,
    d_zero=None,
    phi_mode="linear",       # "linear" or "nearest"
    F_mode="nearest",        # "linear", "nearest", or "zero"
    max_back_extrap_factor=5.0,
):
    """
    Linearly extrapolate near-contact FD amplitude to A=0.

    Behavior:
        measured curve starts at d_min with finite A_min
        construct synthetic segment:
            d_zero <= d <= d_min
            A(d_zero) = 0
            A(d_min) = measured A_min
        for d < d_zero, later evaluator will return A=0.

    This does not clamp to finite near-contact amplitude.
    """
    d = np.asarray(d, dtype=float).ravel()
    A = np.asarray(A, dtype=float).ravel()
    phi = np.asarray(phi, dtype=float).ravel()

    if F is not None:
        F = np.asarray(F, dtype=float).ravel()

    if not (len(d) == len(A) == len(phi)):
        raise ValueError("d, A, and phi must have the same length.")

    if F is not None and len(F) != len(d):
        raise ValueError("F must have the same length as d.")

    mask = np.isfinite(d) & np.isfinite(A) & np.isfinite(phi)
    if F is not None:
        mask &= np.isfinite(F)

    d = d[mask]
    A = A[mask]
    phi = phi[mask]
    if F is not None:
        F = F[mask]

    order = np.argsort(d)
    d = d[order]
    A = A[order]
    phi = phi[order]
    if F is not None:
        F = F[order]

    if len(d) < 2:
        raise ValueError("Need at least two points.")

    d_min = float(d[0])
    A_min = float(A[0])
    phi_min = float(phi[0])

    if d_zero is None:
        d_zero, fit_info = estimate_zero_amplitude_distance_linear(
            d,
            A,
            n_fit=n_fit,
            max_back_extrap_factor=max_back_extrap_factor,
        )
    else:
        d_zero = float(d_zero)
        fit_info = {
            "d_zero_user": d_zero,
            "d_min": d_min,
            "A_min": A_min,
        }

    if d_zero >= d_min:
        raise ValueError(
            f"d_zero={d_zero} must be smaller than measured d_min={d_min}."
        )

    # Build dense linear bridge excluding d_min because measured curve already has it.
    n_bridge = int(max(2, n_bridge))
    d_bridge = np.linspace(d_zero, d_min, n_bridge, endpoint=False)

    # Strictly linear amplitude bridge.
    A_bridge = A_min * (d_bridge - d_zero) / (d_min - d_zero)
    A_bridge = np.maximum(A_bridge, 0.0)

    # Phase bridge.
    if phi_mode == "nearest":
        phi_bridge = np.full_like(d_bridge, phi_min)
    elif phi_mode == "linear":
        # Extrapolate phase from first few points, but keep it conservative.
        n_phi = int(min(max(2, n_fit), len(d)))
        m_phi, b_phi = np.polyfit(d[:n_phi], phi[:n_phi], deg=1)
        phi_bridge = m_phi * d_bridge + b_phi
    else:
        raise ValueError("phi_mode must be 'linear' or 'nearest'.")

    # Force bridge.
    if F is not None:
        F_min = float(F[0])

        if F_mode == "nearest":
            F_bridge = np.full_like(d_bridge, F_min)
        elif F_mode == "zero":
            F_bridge = np.zeros_like(d_bridge)
        elif F_mode == "linear":
            n_F = int(min(max(2, n_fit), len(d)))
            m_F, b_F = np.polyfit(d[:n_F], F[:n_F], deg=1)
            F_bridge = m_F * d_bridge + b_F
        else:
            raise ValueError("F_mode must be 'linear', 'nearest', or 'zero'.")
    else:
        F_bridge = None

    d_new = np.r_[d_bridge, d]
    A_new = np.r_[A_bridge, A]
    phi_new = np.r_[phi_bridge, phi]

    if F is not None:
        F_new = np.r_[F_bridge, F]
    else:
        F_new = None

    # Remove duplicates just in case.
    order = np.argsort(d_new)
    d_new = d_new[order]
    A_new = A_new[order]
    phi_new = phi_new[order]
    if F_new is not None:
        F_new = F_new[order]

    keep = np.r_[True, np.diff(d_new) > 1e-12]
    d_new = d_new[keep]
    A_new = A_new[keep]
    phi_new = phi_new[keep]
    if F_new is not None:
        F_new = F_new[keep]

    fit_info.update({
        "d_zero": float(d_zero),
        "d_min_original": float(d_min),
        "A_min_original": float(A_min),
    })

    return d_new, A_new, phi_new, F_new, fit_info

def extend_measured_fd_dict_linear_to_zero_amplitude(
    measured_fd,
    *,
    n_fit=5,
    n_bridge=30,
    d_zero=None,
    phi_mode="linear",
    F_mode="nearest",
    max_back_extrap_factor=5.0,
):
    """
    Apply linear A -> 0 extrapolation to every measured FD curve.

    measured_fd[drive] = {
        "d": ...,
        "A": ...,
        "phi": ...,
        optional "F": ...
    }
    """
    measured_fd_ext = {}
    diagnostics = {}

    for drive, curve in measured_fd.items():
        d_new, A_new, phi_new, F_new, info = extend_fd_curve_linear_to_zero_amplitude(
            d=curve["d"],
            A=curve["A"],
            phi=curve["phi"],
            F=curve.get("F", None),
            n_fit=n_fit,
            n_bridge=n_bridge,
            d_zero=d_zero,
            phi_mode=phi_mode,
            F_mode=F_mode,
            max_back_extrap_factor=max_back_extrap_factor,
        )

        new_curve = {
            "d": d_new,
            "A": A_new,
            "phi": phi_new,
        }

        if F_new is not None:
            new_curve["F"] = F_new

        measured_fd_ext[float(drive)] = new_curve
        diagnostics[float(drive)] = info

    return measured_fd_ext, diagnostics