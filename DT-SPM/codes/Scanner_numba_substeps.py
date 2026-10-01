"""
Scanner_fixed.py
================

Bug-fixed version of Scanner.py.

The original file failed at two places that are critical for evaluating FD
curves at different drives:

1. `ScannerFD.get_A0_hat` had broken indentation (its body was at the same
   indent as `def`), which prevented the whole module from importing.
2. `ScannerFD.scan_line_pi` and `ScannerFD.scan_line_substepped` tried to
   compute `A0_i = self.get_A0_hat(drive_i)` *before the per-pixel loop*,
   while `drive_i` is only assigned *inside* that loop. They also fell back
   to a stale `A0` variable that was either commented out or still equal to
   the function-default `None`.
3. `scan_line_trace_retrace_pi_drive` did not reverse `drive_nm` /
   `setpoint` when those were arrays, so the retrace was driven by the
   wrong drive at the wrong pixel.

All three issues meant that the simulator never actually evaluated FD
curves at the per-pixel drive — it either crashed, or it used a single A0
fixed at the start of the line.

The fixes preserve the original structure and method signatures. The
controller is unchanged.

Conventions
-----------
- d_act, d_cmd, d_eff are in scanner-normalized units.
- drive_nm is in nm (physical), and the FD model is responsible for
  returning amplitudes already in scanner-normalized units. Use
  NormalizedDriveFD if you need a physical->normalized adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MethodType
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
from scipy.interpolate import PchipInterpolator, RegularGridInterpolator, interp1d
from scipy.optimize import differential_evolution, minimize


ArrayLike = Union[float, np.ndarray, Iterable[float]]


# =============================================================================
# Filters
# =============================================================================

def _lpf1_step(y, x, dt, tau):
    """
    First-order LPF: dy/dt = (x - y) / tau.
    Uses alpha = dt / (tau + dt), stable for all dt.
    """
    if tau is None or tau <= 0.0:
        return float(x)
    alpha = dt / (tau + dt)
    return float(y + alpha * (x - y))


def _lpf2_step(y, ydot, x, dt, wn, zeta):
    """
    Exact discrete step for y'' + 2*zeta*wn*y' + wn^2 y = wn^2 x.
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
        e_new = decay * (e * c + (edot + zeta * wn * e) * s / wd)
        edot_new = decay * (
            edot * c - (wn * wn * e + zeta * wn * edot) * s / wd
        )
    elif zeta > 1.0:
        wd = wn * np.sqrt(zeta * zeta - 1.0)
        decay = np.exp(-zeta * wn * dt)
        ch = np.cosh(wd * dt)
        sh = np.sinh(wd * dt)
        e_new = decay * (e * ch + (edot + zeta * wn * e) * sh / wd)
        edot_new = decay * (
            edot * ch - (wn * wn * e + zeta * wn * edot) * sh / wd
        )
    else:
        decay = np.exp(-wn * dt)
        e_new = decay * (e + (edot + wn * e) * dt)
        edot_new = decay * (edot - wn * (edot + wn * e) * dt)

    return float(x + e_new), float(edot_new)


_BW4_ZETAS = (np.sin(np.pi / 8), np.sin(3 * np.pi / 8))


def _lpf4_step(s1, s1_dot, s2, s2_dot, x, dt, tau):
    """4th-order Butterworth LPF: cascade of two 2nd-order sections."""
    if tau is None or tau <= 0.0:
        return float(x), float(x), 0.0, float(x), 0.0

    wn = 1.0 / tau
    z1, z2 = _BW4_ZETAS

    s1_new, s1_dot_new = _lpf2_step(s1, s1_dot, x, dt, wn, z1)
    s2_new, s2_dot_new = _lpf2_step(s2, s2_dot, s1_new, dt, wn, z2)

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
    """Broadcast scalar or 1D array to length n."""
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

class ScannerFD:
    """
    FD-lookup scanner with drive-dependent FD evaluation.

    Key convention:
        d_eff = d_act - h_hat[i]

    The FD model should implement:
        fd_model.evaluate(d_hat, drive_nm=drive_nm)

    If drive_nm is provided but fd_model cannot accept it, the wrapper raises
    rather than silently using a drive-independent FD curve.
    """

    def __init__(self, params: Dict, conversions: Dict, fd_model):
        self.param = dict(params)
        self.conversion = dict(conversions)
        self.fd_model = fd_model

        self.param_norm: Dict[str, float] = {}
        for key in self.param:
            self.param_norm[key] = self.param[key] * self.conversion[key]

        if all(k in self.param_norm for k in ["H", "R"]):
            self.param_norm["C1"] = (
                self.param_norm["H"] * self.param_norm["R"] / 6.0
            )
        if all(k in self.param_norm for k in ["E_star", "R"]):
            self.param_norm["C2"] = (
                (4.0 / 3.0)
                * self.param_norm["E_star"]
                * np.sqrt(self.param_norm["R"])
            )
        if all(k in self.param_norm for k in ["A", "Q"]):
            self.param_norm["C3"] = (
                self.param_norm["A"] / self.param_norm["Q"]
            )

    # -------------------------------------------------------------------------
    # FD model queries
    # -------------------------------------------------------------------------

    def get_A0_hat(self, drive_nm=None):
        """
        Return free amplitude A0 in scanner-normalized units.

        Priority:
            1. fd_model.A0_at_drive(drive_nm)
            2. fd_model.free_amplitude(drive_nm)
            3. fd_model.A0
            4. self.param_norm["A"]
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
        """Return FD calibrated distance range in scanner-normalized units."""
        if hasattr(self.fd_model, "distance_range"):
            return self.fd_model.distance_range(drive_nm)
        if hasattr(self.fd_model, "d"):
            return float(self.fd_model.d[0]), float(self.fd_model.d[-1])
        return None, None

    def measure_from_fd(self, d_hat: float, drive_nm=None, return_flags: bool = False):
        """
        Evaluate FD response.

        If drive_nm is provided, the fd_model must support drive-dependent
        evaluation. This avoids silently using the wrong drive-independent curve.
        """
        d_hat = float(d_hat)

        if drive_nm is None:
            try:
                return self.fd_model.evaluate(d_hat, return_flags=return_flags)
            except TypeError:
                if return_flags:
                    A, phi, F = self.fd_model.evaluate(d_hat)
                    d_min, d_max = self.distance_range(None)
                    flags = {
                        "below_fd_range": False if d_min is None else d_hat < d_min,
                        "above_fd_range": False if d_max is None else d_hat > d_max,
                        "d_min": d_min,
                        "d_max": d_max,
                    }
                    return float(A), float(phi), float(F), flags
                A, phi, F = self.fd_model.evaluate(d_hat)
                return float(A), float(phi), float(F)

        try:
            return self.fd_model.evaluate(
                d_hat,
                drive_nm=float(drive_nm),
                return_flags=return_flags,
            )
        except TypeError:
            if return_flags:
                try:
                    A, phi, F, flags = self.fd_model.evaluate(
                        d_hat,
                        drive_nm=float(drive_nm),
                        return_flags=True,
                    )
                    return float(A), float(phi), float(F), flags
                except TypeError as e:
                    raise TypeError(
                        "fd_model.evaluate does not support "
                        "evaluate(d_hat, drive_nm=..., return_flags=True)."
                    ) from e

            try:
                A, phi, F = self.fd_model.evaluate(
                    d_hat,
                    drive_nm=float(drive_nm),
                )
            except TypeError as e:
                raise TypeError(
                    "fd_model.evaluate does not accept drive_nm. "
                    "Use the NormalizedDriveFD wrapper or implement "
                    "evaluate(d_hat, drive_nm=...)."
                ) from e

            return float(A), float(phi), float(F)

    # -------------------------------------------------------------------------
    # Single line scan, one controller update per pixel
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

        # Amplitude / phase filters
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

        # Initial state
        d_init_hat: Optional[float] = 500.0,
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

        # ----- Bug fix: A0 for initial state must come from the first pixel's
        # drive, not from a stale undefined `A0` or a hoisted `drive_i`.
        if drive_arr is not None:
            A0_init = self.get_A0_hat(float(drive_arr[0]))
        else:
            A0_init = self.get_A0_hat(None)

        if d_cmd_init_hat is not None:
            d_cmd = float(d_cmd_init_hat)
        elif d_init_hat is not None:
            d_cmd = float(d_init_hat)
        else:
            d_cmd = float(self.param_norm.get("d0", 0.0))

        d_act = float(d_cmd if d_act_init_hat is None else d_act_init_hat)
        d_act_dot = 0.0

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
        out_A_true = np.empty(n)
        out_A_meas = np.empty(n)
        out_phi_true = np.empty(n)
        out_phi_meas = np.empty(n)
        out_F = np.empty(n)
        out_err = np.empty(n)
        out_d_eff = np.empty(n)
        out_A0 = np.empty(n)

        # 4th-order filter states
        A1, A1d, A2, A2d = A_meas, 0.0, A_meas, 0.0
        phi1, phi1d, phi2, phi2d = phi_meas, 0.0, phi_meas, 0.0

        for i in range(n):
            h_i = float(h_hat[i])
            drive_i = None if drive_arr is None else float(drive_arr[i])

            # ----- Bug fix: A0 must be re-evaluated per pixel because drive
            # can vary along the line. The corresponding A_set follows.
            A0_i = self.get_A0_hat(drive_i)
            A_set = float(setpoint_arr[i] * A0_i)

            d_eff = d_act - h_i

            A_true, phi_true, F_peak = self.measure_from_fd(
                d_eff,
                drive_nm=drive_i,
            )

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

            # PI controller
            err = A_set - A_meas

            if use_leak:
                integ = decay * integ + err * dt
            else:
                integ = integ + err * dt

            if integ_clip is not None:
                integ = float(np.clip(integ, -integ_clip, integ_clip))

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
                    d_act, d_act_dot, d_cmd, dt, wn_z, zeta_z,
                )
            else:
                raise ValueError("z_filter_order must be None, 1, or 2.")

            out_d_cmd[i] = d_cmd
            out_d_act[i] = d_act
            out_A_true[i] = A_true
            out_A_meas[i] = A_meas
            out_phi_true[i] = phi_true
            out_phi_meas[i] = phi_meas
            out_F[i] = F_peak
            out_err[i] = err
            out_d_eff[i] = d_eff
            out_A0[i] = A0_i

        return {
            "d_cmd_hat": out_d_cmd,
            "d_hat": out_d_act,
            "d_eff_hat": out_d_eff,

            "A_true_hat": out_A_true,
            "A_hat": out_A_meas,
            "A0_hat": out_A0,

            "phi_true_deg": out_phi_true,
            "phi_deg": out_phi_meas,

            "F_peak": out_F,
            "err": out_err,

            "dt_pixel": dt,

            "d_cmd_final_hat": float(d_cmd),
            "d_final_hat": float(d_act),
            "A_meas_final_hat": float(A_meas),
            "phi_meas_final_deg": float(phi_meas),
            "integ_final": float(integ),
        }

    # -------------------------------------------------------------------------
    # Single line scan with substeps
    # -------------------------------------------------------------------------

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
        """
        One line scan with inner feedback substeps.

        - drive_i is passed into measure_from_fd(..., drive_nm=drive_i)
        - controller update uses dt_inner directly:
              dd_cmd = (P*err + I*integ) * dt_inner
        - A0 is reevaluated per pixel from the per-pixel drive.
        """
        h_hat = np.asarray(h_hat, dtype=float).ravel()
        n = h_hat.size

        if scan_speed_hat <= 0:
            raise ValueError("scan_speed_hat must be positive.")
        if dx_hat <= 0:
            raise ValueError("dx_hat must be positive.")

        dt_pixel = float(dx_hat / scan_speed_hat)

        drive_arr = _broadcast_1d(drive_nm, n, "drive_nm")
        sp_arr = _broadcast_1d(setpoint, n, "setpoint")

        # ----- Bug fix: initial A0 uses the first pixel's drive.
        A0_init = self.get_A0_hat(float(drive_arr[0]))

        # Decide inner timestep.
        tau_candidates = []

        if not _filter_disabled(A_filter_order, tau_A):
            tau_candidates.append(float(tau_A))

        if not _filter_disabled(phi_filter_order, tau_phi):
            tau_candidates.append(float(tau_phi))

        if z_filter_order is not None and tau_z is not None and tau_z > 0:
            tau_candidates.append(float(tau_z))
            
        tau_min = min(tau_candidates) if tau_candidates else dt_pixel

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
                "phi_meas",
                "A_true",
                "A_true_hat",
                "phi_true",
                "phi_true_deg",
                "phi_deg",
                "F",
                "F_peak",
                "err",
                "A0_hat",
            )
        }

        for i in range(n):
            h_i = float(h_hat[i])
            drive_i = float(drive_arr[i])
            sp_i = float(sp_arr[i])

            # ----- Bug fix: per-pixel A0 and A_set.
            A0_i = self.get_A0_hat(drive_i)
            A_set = sp_i * A0_i

            for _ in range(n_substeps):
                d_eff = d_act - h_i

                A_true, phi_true, F_peak = self.measure_from_fd(
                    d_eff,
                    drive_nm=drive_i,
                )

                # Amplitude filter
                # Amplitude measurement filter
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


                # PI controller
                err = A_set - A_meas

                if use_leak:
                    integ = decay_inner * integ + err * dt_inner
                else:
                    integ = integ + err * dt_inner

                if integ_clip is not None:
                    integ = float(np.clip(integ, -integ_clip, integ_clip))

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
                        d_act, d_act_dot, d_cmd,
                        dt_inner, 1.0 / tau_z, np.sqrt(0.5),
                    )
                else:
                    raise ValueError("z_filter_order must be None, 1, or 2.")

            # Sample once per pixel
            out["d_cmd"][i] = d_cmd
            out["d_act"][i] = d_act
            out["d_hat"][i] = d_act
            out["d_eff_hat"][i] = d_eff

            out["A_hat"][i] = A_meas
            out["A_meas"][i] = A_meas

            out["phi_meas"][i] = phi_meas
            out["phi_deg"][i] = phi_meas

            out["A_true"][i] = A_true
            out["A_true_hat"][i] = A_true

            out["phi_true"][i] = phi_true
            out["phi_true_deg"][i] = phi_true

            out["F"][i] = F_peak
            out["F_peak"][i] = F_peak

            out["err"][i] = err
            out["A0_hat"][i] = A0_i

        out["dt_pixel"] = dt_pixel
        out["dt_inner"] = dt_inner
        out["n_substeps"] = n_substeps

        out["d_cmd_final_hat"] = float(d_cmd)
        out["d_final_hat"] = float(d_act)
        out["A_meas_final_hat"] = float(A_meas)
        out["phi_meas_final_deg"] = float(phi_meas)
        out["integ_final"] = float(integ)

        return out

    # -------------------------------------------------------------------------
    # Trace/retrace convenience wrapper
    # -------------------------------------------------------------------------

    @staticmethod
    def _reverse_if_array(value, n):
        """Reverse a per-pixel array; pass scalars through."""
        if value is None:
            return None
        arr = np.asarray(value)
        if arr.ndim == 0:
            return value
        if arr.size == n:
            return arr[::-1].copy()
        return value

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

        Retrace runs on h_hat[::-1]. If drive_nm or setpoint are arrays they
        are also reversed so that pixel i of the retrace sees the same x as
        pixel n-1-i of the trace. Its output arrays are then flipped back into
        forward x-order.
        """
        h_hat = np.asarray(h_hat, dtype=float).ravel()
        n = h_hat.size

        # ----- Bug fix: reverse per-pixel inputs for retrace.
        drive_rev = self._reverse_if_array(drive_nm, n)
        sp_rev = self._reverse_if_array(setpoint, n)

        if not use_substeps:
            trace = self.scan_line_pi(
                h_hat=h_hat,
                drive_nm=drive_nm,
                setpoint=setpoint,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P, I=I,
                A_filter_order=A_filter_order,
                tau_A=tau_A, wn_A=wn_A, zeta_A=zeta_A,
                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi, wn_phi=wn_phi, zeta_phi=zeta_phi,
                z_filter_order=z_filter_order,
                tau_z=tau_z, wn_z=wn_z, zeta_z=zeta_z,
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
                drive_nm=drive_rev,
                setpoint=sp_rev,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P, I=I,
                A_filter_order=A_filter_order,
                tau_A=tau_A, wn_A=wn_A, zeta_A=zeta_A,
                phi_filter_order=phi_filter_order,
                tau_phi=tau_phi, wn_phi=wn_phi, zeta_phi=zeta_phi,
                z_filter_order=z_filter_order,
                tau_z=tau_z, wn_z=wn_z, zeta_z=zeta_z,
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
                P=P, I=I, T_I=T_I,
                A_filter_order=A_filter_order, tau_A=tau_A,
                phi_filter_order=phi_filter_order, tau_phi=tau_phi,
                z_filter_order=z_filter_order, tau_z=tau_z,
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
                drive_nm=drive_rev,
                setpoint=sp_rev,
                scan_speed_hat=scan_speed_hat,
                dx_hat=dx_hat,
                P=P, I=I, T_I=T_I,
                A_filter_order=A_filter_order, tau_A=tau_A,
                phi_filter_order=phi_filter_order, tau_phi=tau_phi,
                z_filter_order=z_filter_order, tau_z=tau_z,
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

        # Flip retrace arrays back to forward x-order.
        retrace = {}
        for k, v in retrace_raw.items():
            if isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == n:
                retrace[k] = v[::-1].copy()
            else:
                retrace[k] = v

        return {
            "trace": trace,
            "retrace": retrace,
            "raw_retrace": retrace_raw,
        }

    # -------------------------------------------------------------------------
    # 2D map
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
        phi_map = np.empty((ny, nx))
        F_map = np.empty((ny, nx))
        A_map = np.empty((ny, nx))
        err_map = np.empty((ny, nx))
        d_eff_map = np.empty((ny, nx))

        carry = dict(
            d_cmd_init_hat=line_kwargs.pop("d_cmd_init_hat", None),
            d_act_init_hat=line_kwargs.pop("d_act_init_hat", None),
            A_meas_init_hat=line_kwargs.pop("A_meas_init_hat", None),
            phi_meas_init_deg=line_kwargs.pop("phi_meas_init_deg", 0.0),
            integ_init=line_kwargs.pop("integ_init", 0.0),
        )

        drive_full = line_kwargs.pop("drive_nm", None)
        setpoint_full = line_kwargs.pop("setpoint", 0.8)

        for iy in range(ny):
            reverse = bool(serpentine and (iy % 2 == 1))
            row = h_map_hat[iy, ::-1] if reverse else h_map_hat[iy, :]

            # If drive_nm/setpoint are 1D arrays (per-x) or 2D (per-pixel),
            # extract the right slice for this row.
            row_drive = self._row_slice(drive_full, iy, nx, reverse)
            row_sp = self._row_slice(setpoint_full, iy, nx, reverse)

            out = self.scan_line_pi(
                row,
                drive_nm=row_drive,
                setpoint=row_sp,
                **carry,
                **line_kwargs,
            )

            d_row = out["d_hat"]
            phi_row = out["phi_deg"]
            F_row = out["F_peak"]
            A_row = out["A_hat"]
            err_row = out["err"]
            d_eff_row = out["d_eff_hat"]

            if reverse:
                d_row = d_row[::-1]
                phi_row = phi_row[::-1]
                F_row = F_row[::-1]
                A_row = A_row[::-1]
                err_row = err_row[::-1]
                d_eff_row = d_eff_row[::-1]

            d_map[iy, :] = d_row
            phi_map[iy, :] = phi_row
            F_map[iy, :] = F_row
            A_map[iy, :] = A_row
            err_map[iy, :] = err_row
            d_eff_map[iy, :] = d_eff_row

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
        }

    @staticmethod
    def _row_slice(value, iy, nx, reverse):
        """
        Extract the per-row slice of `value` for use by scan_line_pi.

        - None or scalar: pass through unchanged.
        - 1D length nx: per-x array, reversed if needed.
        - 2D (ny, nx):  row iy.
        """
        if value is None:
            return None
        arr = np.asarray(value)
        if arr.ndim == 0:
            return value
        if arr.ndim == 1 and arr.size == nx:
            return arr[::-1] if reverse else arr
        if arr.ndim == 2 and arr.shape[1] == nx:
            row = arr[iy, :]
            return row[::-1] if reverse else row
        return value


# =============================================================================
# Stage-2 FD-curve surface interpolation for ScannerFD.
# =============================================================================

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
    if x.size >= 3:
        return PchipInterpolator(x, y, extrapolate=False)
    return interp1d(x, y, kind="linear", bounds_error=False, fill_value=(left, right))


@dataclass
class FDCurve1D:
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
            raise ValueError("d, A, phi, and F must have the same shape")

        mask = _finite_mask(d, A, phi, F)
        d, A, phi, F = d[mask], A[mask], phi[mask], F[mask]

        if d.size < 2:
            raise ValueError("Need at least two finite samples for FDCurve1D")

        d, A, phi, F = _average_duplicate_x(d, A, phi, F)

        if d.size < 2 or not np.all(np.diff(d) > 0):
            raise ValueError("d must contain at least two unique increasing values")

        self.d = d
        self.A = A
        self.phi = phi
        self.F = F
        self.A0 = float(A[-1] if self.A0 is None else self.A0)

        phi_unwrapped = _unwrap_phase_deg(phi)

        if self.kind == "pchip":
            self._A_interp = _safe_pchip(d, A, left=A[0], right=self.A0)
            self._phi_interp = _safe_pchip(d, phi_unwrapped,
                                           left=phi_unwrapped[0],
                                           right=phi_unwrapped[-1])
            self._F_interp = _safe_pchip(d, F, left=F[0], right=0.0)
        else:
            self._A_interp = interp1d(d, A, kind=self.kind, bounds_error=False,
                                      fill_value=(A[0], self.A0))
            self._phi_interp = interp1d(d, phi_unwrapped, kind=self.kind,
                                        bounds_error=False,
                                        fill_value=(phi_unwrapped[0],
                                                    phi_unwrapped[-1]))
            self._F_interp = interp1d(d, F, kind=self.kind, bounds_error=False,
                                      fill_value=(F[0], 0.0))

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

    def __call__(self, d_query):
        return self.evaluate(d_query)


class FDDriveSurface:
    """Continuous FD surface over drive and distance."""

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
                raise ValueError(
                    "far_field_side must be largest_d, smallest_d, start, or end"
                )
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
            raise ValueError(
                "Need at least two drives for continuous drive interpolation"
            )

        x_mins: List[float] = []
        x_maxs: List[float] = []
        prepared: List[Tuple[float, np.ndarray, np.ndarray,
                             np.ndarray, np.ndarray, float]] = []

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
                    "No overlapping distance range across curves. "
                    "Use common_range='union', trim curves, or align d-offsets."
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
            a_left = float(a[0])
            a_right = 1.0 if self.right_fill_free else float(a[-1])
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
                phi_grid[i] = np.interp(self._x_grid, x, phi,
                                        left=phi_left, right=phi_right)
                F_grid[i] = np.interp(self._x_grid, x, F,
                                      left=F_left, right=F_right)

            A0_by_drive[i] = A0

        self._drives = drives
        self._A0_by_drive = A0_by_drive
        self._a_grid = a_grid
        self._phi_grid = phi_grid
        self._F_grid = F_grid

        self._a_rgi = RegularGridInterpolator(
            (drives, self._x_grid), a_grid,
            method="linear", bounds_error=False, fill_value=None,
        )
        self._phi_rgi = RegularGridInterpolator(
            (drives, self._x_grid), phi_grid,
            method="linear", bounds_error=False, fill_value=None,
        )
        self._F_rgi = RegularGridInterpolator(
            (drives, self._x_grid), F_grid,
            method="linear", bounds_error=False, fill_value=None,
        )
        self._A0_rgi = interp1d(
            drives, A0_by_drive, kind="linear", bounds_error=False,
            fill_value=(A0_by_drive[0], A0_by_drive[-1]),
        )
        self._built = True
        return self

    def _require_built(self) -> None:
        if not self._built:
            self.build()

    def evaluate(self, d_nm: ArrayLike, drive_nm: float):
        self._require_built()
        scalar = np.isscalar(d_nm)
        d_arr = np.atleast_1d(np.asarray(d_nm, dtype=float))
        drv = float(drive_nm)
        drv_clip = float(np.clip(drv, self._drives[0], self._drives[-1]))

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
        self._require_built()
        n = self.n_x if n_points is None else int(n_points)
        x = (self._x_grid if n == self._x_grid.size else
             np.linspace(self._x_grid[0], self._x_grid[-1], n))
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
        self._require_built()
        drive_nm = float(drive_nm)
        drive_clip = float(np.clip(drive_nm, self._drives[0], self._drives[-1]))
        return float(self._A0_rgi(drive_clip))

    def distance_range(self, drive_nm: Optional[float] = None):
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
    Adapter from physical FDDriveSurface units to ScannerFD normalized units.
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
                "Call evaluate(d_hat, drive_nm=...)."
            )

        scalar = np.isscalar(d_hat)
        d_hat_arr = np.atleast_1d(np.asarray(d_hat, dtype=float))
        d_nm_arr = d_hat_arr / self.conv_L

        d_min_hat, d_max_hat = self.distance_range(float(drive_nm))
        below = d_hat_arr < d_min_hat
        above = d_hat_arr > d_max_hat

        A_nm, phi_deg, F_raw = self.surface.evaluate(d_nm_arr, float(drive_nm))

        A_hat = np.asarray(A_nm, dtype=float) * self.conv_A
        F_hat = np.asarray(F_raw, dtype=float) * self.conv_F
        phi_deg = np.asarray(phi_deg, dtype=float)

        if scalar:
            if return_flags:
                flags = {
                    "below_fd_range": bool(below[0]),
                    "above_fd_range": bool(above[0]),
                    "d_min": float(d_min_hat),
                    "d_max": float(d_max_hat),
                }
                return (float(A_hat[0]), float(phi_deg[0]),
                        float(F_hat[0]), flags)
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
    surface,
    *,
    conv_L: float,
    conv_A: Optional[float] = None,
    conv_F: float = 1.0,
):
    """
    Adapter factory: return a drive-dependent FD model in scanner-normalized units.

        fd_model = make_normalized_fd_lookup(surface, conv_L=conv_L)
        scanner = ScannerFD(params, conversions, fd_model)
        scanner.measure_from_fd(d_hat, drive_nm=drive_nm)
    """
    return NormalizedDriveFD(
        surface=surface, conv_L=conv_L, conv_A=conv_A, conv_F=conv_F,
    )


# =============================================================================
# Builders + helpers
# =============================================================================

def detect_bad_curves(
    measured_fd: Dict[float, Dict[str, ArrayLike]],
    *,
    phase_jump_threshold_deg: float = 30.0,
    amp_jump_threshold_rel: float = 0.20,
) -> Dict[float, Dict[str, float]]:
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
        A0 = float(
            c.get("A0_nm",
                  np.nanmedian(A[np.argsort(d)[-max(1, int(0.1 * d.size)):]]))
        )
        dphi = np.abs(np.diff(_unwrap_phase_deg(phi)))
        da = np.abs(np.diff(A / max(A0, 1e-30)))
        if (np.nanmax(dphi) > phase_jump_threshold_deg
                or np.nanmax(da) > amp_jump_threshold_rel):
            score_phi = np.nanmax(dphi) / phase_jump_threshold_deg
            score_da = np.nanmax(da) / amp_jump_threshold_rel
            i = (int(np.nanargmax(dphi)) if score_phi >= score_da
                 else int(np.nanargmax(da)))
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
# Helper functions used by the scoring / fitting routines
# =============================================================================

def huber_loss(r, delta=1.0):
    """Element-wise Huber loss. Quadratic for |r|<=delta, linear beyond."""
    r = np.asarray(r, dtype=float)
    abs_r = np.abs(r)
    quad = np.minimum(abs_r, delta)
    lin = abs_r - quad
    return 0.5 * quad ** 2 + delta * lin


def parse_h_exp(h_exp):
    """
    Parse an experimental trace/retrace pair.

    Accepts:
        - dict with keys 'trace' and 'retrace'
        - tuple (trace, retrace)
        - 2xN array
    """
    if isinstance(h_exp, dict):
        return (np.asarray(h_exp["trace"], dtype=float),
                np.asarray(h_exp["retrace"], dtype=float))
    if isinstance(h_exp, tuple) and len(h_exp) == 2:
        return (np.asarray(h_exp[0], dtype=float),
                np.asarray(h_exp[1], dtype=float))
    arr = np.asarray(h_exp, dtype=float)
    if arr.ndim == 2 and arr.shape[0] == 2:
        return arr[0], arr[1]
    raise ValueError("Cannot parse h_exp; expected dict, tuple, or 2xN array.")


def crop_to_common_length(*arrays):
    n = min(len(a) for a in arrays)
    return tuple(np.asarray(a, dtype=float)[:n] for a in arrays)


def apply_common_height_offset(sim_tr, sim_rt, exp_tr, exp_rt):
    """Subtract a single offset so the simulated and experimental medians match."""
    sim_mid = 0.5 * (np.asarray(sim_tr) + np.asarray(sim_rt))
    exp_mid = 0.5 * (np.asarray(exp_tr) + np.asarray(exp_rt))
    offset = float(np.nanmedian(sim_mid) - np.nanmedian(exp_mid))
    return np.asarray(sim_tr) - offset, np.asarray(sim_rt) - offset, offset


def diff_shifted(a, b):
    """Subtract the common median so a-b is centered."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    shift = float(np.nanmedian(a) - np.nanmedian(b))
    return a - shift, b


# =============================================================================
# Fitting controller params against experiment
# =============================================================================

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
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,
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
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,
    maxiter_global=80,
    maxiter_local=300,
    global_tol=0.02,
    local_xatol=1e-3,
    local_fatol=1e-4,
    loss_target=None,
    seed=0,
    popsize=10,
    bounds=None,
    verbose=True,
):
    if bounds is None:
        bounds = [
            (-4.0, 2.0),
            (-4.0, 2.0),
            (-4.0, 1.0),
            (-4.0, 1.0),
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
        best_x, return_full=True,
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


def unpack_controller_params_PI_fixed_tau(x, tau_A_fixed, tau_phi_fixed):
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
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,
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
        x4 = np.array([log10_P, log10_I, log10_tau_A_fixed, log10_tau_phi_fixed],
                      dtype=float)

        if return_full:
            loss, details, out, params = base_objective(x4, return_full=True)
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
    tau_z=1e-5,
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-3,
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    huber_delta=2.0,
    mse_floor_frac=0.03,
    maxiter_global=200,
    maxiter_local=300,
    global_tol=0.02,
    local_xatol=1e-3,
    local_fatol=1e-4,
    loss_target=None,
    seed=0,
    popsize=8,
    bounds=None,
    verbose=True,
):
    if bounds is None:
        bounds = [(-4.0, 2.0), (-4.0, 2.0)]

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

    best_seen = {"loss": np.inf, "x": None}

    def callback(xk, convergence):
        loss = objective(xk)
        if loss < best_seen["loss"]:
            best_seen["loss"] = float(loss)
            best_seen["x"] = np.array(xk, dtype=float)
            if verbose:
                p = unpack_controller_params_PI_fixed_tau(
                    xk, tau_A_fixed=tau_A_fixed, tau_phi_fixed=tau_phi_fixed,
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
        best_x, return_full=True,
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
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    drive=20,
    setpoint=0.6,
    huber_delta=2.0,
    mse_floor_frac=0.03,
):
    """
    1. Simulated trace/retrace height lines agree with experimental ones.
    2. Simulated trace-retrace MSE is close to experimental trace-retrace MSE.
    """
    exp_tr, exp_rt = parse_h_exp(h_exp)

    sim_tr = np.asarray(out["trace"]["d_hat"], dtype=float)
    sim_rt = np.asarray(out["retrace"]["d_hat"], dtype=float)

    sim_tr_use = sim_tr
    sim_rt_use = sim_rt
    exp_tr_use = exp_tr
    exp_rt_use = exp_rt

    h_scale = 1.0

    r_height = np.r_[
        (sim_tr_use - exp_tr_use) / h_scale,
        (sim_rt_use - exp_rt_use) / h_scale,
    ]
    loss_height_match = np.nanmean(huber_loss(r_height, delta=huber_delta))

    diff_sim = sim_tr_use - sim_rt_use
    diff_exp = exp_tr_use - exp_rt_use

    mse_sim = np.nanmean(diff_sim ** 2)
    mse_exp = np.nanmean(diff_exp ** 2)

    mse_floor = (mse_floor_frac * h_scale) ** 2

    loss_mse_match = (
        np.log((mse_sim + mse_floor) / (mse_exp + mse_floor))
    ) ** 2

    loss_noise = np.abs(np.std(exp_tr_use) - np.std(sim_tr_use))

    total = (
        w_height_match * loss_height_match
        + w_mse_match * loss_mse_match
        + loss_noise
    )

    details = {
        "total": total,
        "loss_height_match": loss_height_match,
        "loss_mse_match": loss_mse_match,
        "mse_sim": mse_sim,
        "mse_exp": mse_exp,
        "mse_ratio": mse_sim / (mse_exp + 1e-12),
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

# =============================================================================
# Fast Numba substep simulation and parallel PI fitting
# =============================================================================
# This section is intentionally appended after the original implementation so the
# original ScannerFD API remains unchanged.  It adds:
#   - FD table precomputation for one drive
#   - optional effective height smoothing
#   - fast subpixel trace/retrace simulation using Numba
#   - parallel P/I grid fitting over candidate gains
#   - convenience methods attached to ScannerFD
#
# Limitations of the fast Numba path:
#   - FD lookup is precomputed for a single drive. For arrays of drive values,
#     use the original Python scanner or run one FD table per drive.
#   - Measurement and z filters support disabled mode or first-order LPF.
#     The original Python path still supports higher-order filters.

try:
    from numba import njit, prange
    _NUMBA_AVAILABLE = True
except Exception:  # pragma: no cover
    njit = None
    prange = range
    _NUMBA_AVAILABLE = False


def gaussian_kernel1d(sigma_px: float, truncate: float = 4.0) -> np.ndarray:
    """Return a normalized 1D Gaussian kernel."""
    sigma_px = float(0.0 if sigma_px is None else sigma_px)
    if sigma_px <= 0.0:
        return np.array([1.0], dtype=float)
    radius = int(truncate * sigma_px + 0.5)
    x = np.arange(-radius, radius + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma_px) ** 2)
    k /= np.sum(k)
    return k


def smooth_height_profile(h, sigma_px: float = 0.0, mode: str = "edge") -> np.ndarray:
    """
    Smooth a 1D height profile to mimic effective tip/edge broadening.

    sigma_px=0 returns a copy of the input.  For substep simulations, interpolation
    is always used inside the fast kernel; smoothing is optional and should be
    treated as an effective tip-convolution parameter, not a numerical necessity.
    """
    h = np.asarray(h, dtype=float).ravel()
    if sigma_px is None or float(sigma_px) <= 0.0:
        return h.copy()
    k = gaussian_kernel1d(float(sigma_px))
    pad = len(k) // 2
    hp = np.pad(h, pad, mode=mode)
    return np.convolve(hp, k, mode="valid")


def prepare_fd_table_for_drive(scanner, drive_nm, n_d: int = 4096, d_pad_frac: float = 0.05):
    """
    Precompute A(d), phi(d), and F(d) for one drive on a dense uniform d-grid.

    The Numba kernels interpolate this table instead of calling scanner.measure_from_fd()
    inside the inner substep loop.
    """
    d_min, d_max = scanner.distance_range(float(drive_nm))
    if d_min is None or d_max is None:
        raise ValueError("scanner.distance_range(drive_nm) must return finite limits.")
    d_min = float(d_min)
    d_max = float(d_max)
    if not np.isfinite(d_min) or not np.isfinite(d_max) or d_max <= d_min:
        raise ValueError(f"Invalid FD distance range: {(d_min, d_max)}")

    span = d_max - d_min
    d_grid = np.linspace(d_min - d_pad_frac * span, d_max + d_pad_frac * span, int(n_d))

    A_grid = np.empty_like(d_grid)
    phi_grid = np.empty_like(d_grid)
    F_grid = np.empty_like(d_grid)
    for i, d in enumerate(d_grid):
        A, phi, F = scanner.measure_from_fd(float(d), drive_nm=float(drive_nm))[:3]
        A_grid[i] = float(A)
        phi_grid[i] = float(phi)
        F_grid[i] = float(F)

    return {
        "drive_nm": float(drive_nm),
        "d_grid": np.asarray(d_grid, dtype=np.float64),
        "A_grid": np.asarray(A_grid, dtype=np.float64),
        "phi_grid": np.asarray(phi_grid, dtype=np.float64),
        "F_grid": np.asarray(F_grid, dtype=np.float64),
        "A0": float(scanner.get_A0_hat(float(drive_nm))),
        "d_min": float(d_grid[0]),
        "d_max": float(d_grid[-1]),
    }


if _NUMBA_AVAILABLE:

    @njit(cache=True)
    def _interp_uniform_grid_numba(x_grid, y_grid, x):
        n = x_grid.shape[0]
        x0 = x_grid[0]
        x1 = x_grid[n - 1]
        if x <= x0:
            return y_grid[0]
        if x >= x1:
            return y_grid[n - 1]
        t = (x - x0) / (x1 - x0) * (n - 1)
        i = int(np.floor(t))
        if i < 0:
            i = 0
        if i > n - 2:
            i = n - 2
        f = t - i
        return (1.0 - f) * y_grid[i] + f * y_grid[i + 1]


    @njit(cache=True)
    def _interp_height_line_numba(h, x):
        n = h.shape[0]
        if x <= 0.0:
            return h[0]
        if x >= n - 1:
            return h[n - 1]
        i = int(np.floor(x))
        f = x - i
        return (1.0 - f) * h[i] + f * h[i + 1]


    @njit(cache=True)
    def _lpf1_step_numba(y, x, dt, tau):
        if tau <= 0.0:
            return x
        alpha = dt / (tau + dt)
        return y + alpha * (x - y)


    @njit(cache=True)
    def _simulate_one_line_substeps_numba(
        h,
        d_grid,
        A_grid,
        phi_grid,
        F_grid,
        A0,
        setpoint,
        scan_speed_hat,
        dx_hat,
        P,
        I,
        use_A_filter,
        tau_A,
        use_phi_filter,
        tau_phi,
        use_z_filter,
        tau_z,
        z_rate_limit_hat,
        use_z_rate_limit,
        d_cmd_init_hat,
        d_act_init_hat,
        phi_meas_init_deg,
        A_meas_init_hat,
        use_A_meas_init,
        T_I,
        use_leaky_I,
        integ_init,
        integ_clip,
        use_integ_clip,
        n_substeps,
        antiwindup,
        contact_A_frac,
        saturation_A_frac,
        reverse_scan,
        record_mean,
    ):
        n_pix = h.shape[0]
        dt_pixel = dx_hat / scan_speed_hat
        dt_inner = dt_pixel / n_substeps

        d_cmd = d_cmd_init_hat
        d_act = d_act_init_hat

        if reverse_scan:
            h0 = h[n_pix - 1]
        else:
            h0 = h[0]
        d_eff0 = d_act - h0
        A_true0 = _interp_uniform_grid_numba(d_grid, A_grid, d_eff0)
        phi_true0 = _interp_uniform_grid_numba(d_grid, phi_grid, d_eff0)
        A_meas = A_meas_init_hat if use_A_meas_init else A_true0
        phi_meas = phi_meas_init_deg if np.isfinite(phi_meas_init_deg) else phi_true0
        integ = integ_init
        A_set = setpoint * A0

        out_d_cmd = np.empty(n_pix)
        out_d_act = np.empty(n_pix)
        out_d_eff = np.empty(n_pix)
        out_A_true = np.empty(n_pix)
        out_A_meas = np.empty(n_pix)
        out_A0 = np.empty(n_pix)
        out_A_set = np.empty(n_pix)
        out_phi_true = np.empty(n_pix)
        out_phi_meas = np.empty(n_pix)
        out_F = np.empty(n_pix)
        out_err = np.empty(n_pix)
        out_integ = np.empty(n_pix)
        out_low_sat = np.zeros(n_pix)
        out_high_sat = np.zeros(n_pix)

        for pix in range(n_pix):
            sum_d_cmd = 0.0
            sum_d_act = 0.0
            sum_d_eff = 0.0
            sum_A_true = 0.0
            sum_A_meas = 0.0
            sum_phi_true = 0.0
            sum_phi_meas = 0.0
            sum_F = 0.0
            sum_err = 0.0
            sum_integ = 0.0
            any_low_sat = 0.0
            any_high_sat = 0.0

            for sub in range(n_substeps):
                frac = sub / n_substeps
                if reverse_scan:
                    x = (n_pix - 1) - (pix + frac)
                else:
                    x = pix + frac
                if x < 0.0:
                    x = 0.0
                if x > n_pix - 1:
                    x = n_pix - 1.0

                h_now = _interp_height_line_numba(h, x)
                d_eff = d_act - h_now
                A_true = _interp_uniform_grid_numba(d_grid, A_grid, d_eff)
                phi_true = _interp_uniform_grid_numba(d_grid, phi_grid, d_eff)
                F_peak = _interp_uniform_grid_numba(d_grid, F_grid, d_eff)

                if use_A_filter:
                    A_meas = _lpf1_step_numba(A_meas, A_true, dt_inner, tau_A)
                else:
                    A_meas = A_true
                if use_phi_filter:
                    phi_meas = _lpf1_step_numba(phi_meas, phi_true, dt_inner, tau_phi)
                else:
                    phi_meas = phi_true

                err = A_set - A_meas
                low_sat = A_meas <= contact_A_frac * max(A0, 1e-12)
                high_sat = A_meas >= saturation_A_frac * max(A0, 1e-12)

                update_integrator = True
                if antiwindup:
                    if low_sat and err > 0.0:
                        update_integrator = False
                    if high_sat and err < 0.0:
                        update_integrator = False

                if update_integrator:
                    if use_leaky_I:
                        decay = np.exp(-dt_inner / T_I)
                        integ = decay * integ + err * dt_inner
                    else:
                        integ = integ + err * dt_inner
                    if use_integ_clip:
                        if integ > integ_clip:
                            integ = integ_clip
                        elif integ < -integ_clip:
                            integ = -integ_clip

                dd_cmd = (P * err + I * integ) * dt_inner
                if use_z_rate_limit:
                    max_dd = z_rate_limit_hat * dt_inner
                    if dd_cmd > max_dd:
                        dd_cmd = max_dd
                    elif dd_cmd < -max_dd:
                        dd_cmd = -max_dd
                d_cmd = d_cmd + dd_cmd

                if use_z_filter:
                    d_act = _lpf1_step_numba(d_act, d_cmd, dt_inner, tau_z)
                else:
                    d_act = d_cmd

                if record_mean:
                    sum_d_cmd += d_cmd
                    sum_d_act += d_act
                    sum_d_eff += d_eff
                    sum_A_true += A_true
                    sum_A_meas += A_meas
                    sum_phi_true += phi_true
                    sum_phi_meas += phi_meas
                    sum_F += F_peak
                    sum_err += err
                    sum_integ += integ
                else:
                    sum_d_cmd = d_cmd
                    sum_d_act = d_act
                    sum_d_eff = d_eff
                    sum_A_true = A_true
                    sum_A_meas = A_meas
                    sum_phi_true = phi_true
                    sum_phi_meas = phi_meas
                    sum_F = F_peak
                    sum_err = err
                    sum_integ = integ

                if low_sat:
                    any_low_sat = 1.0
                if high_sat:
                    any_high_sat = 1.0

            inv = 1.0 / n_substeps if record_mean else 1.0
            out_d_cmd[pix] = sum_d_cmd * inv
            out_d_act[pix] = sum_d_act * inv
            out_d_eff[pix] = sum_d_eff * inv
            out_A_true[pix] = sum_A_true * inv
            out_A_meas[pix] = sum_A_meas * inv
            out_A0[pix] = A0
            out_A_set[pix] = A_set
            out_phi_true[pix] = sum_phi_true * inv
            out_phi_meas[pix] = sum_phi_meas * inv
            out_F[pix] = sum_F * inv
            out_err[pix] = sum_err * inv
            out_integ[pix] = sum_integ * inv
            out_low_sat[pix] = any_low_sat
            out_high_sat[pix] = any_high_sat

        return (
            out_d_cmd,
            out_d_act,
            out_d_eff,
            out_A_true,
            out_A_meas,
            out_A0,
            out_A_set,
            out_phi_true,
            out_phi_meas,
            out_F,
            out_err,
            out_integ,
            out_low_sat,
            out_high_sat,
            d_cmd,
            d_act,
            A_meas,
            phi_meas,
            integ,
            dt_pixel,
            dt_inner,
        )


    @njit(cache=True)
    def _quality_loss_from_trace_retrace_numba(
        tr,
        rt,
        h_ref,
        sat_trace,
        sat_retrace,
        trim,
        w_align,
        w_ring,
        w_sat,
    ):
        n = tr.shape[0]
        i0 = trim
        i1 = n - trim
        if i1 <= i0 + 5:
            i0 = 0
            i1 = n
        m = i1 - i0

        offset = 0.0
        for i in range(i0, i1):
            offset += tr[i] - rt[i]
        offset /= m

        h_min = h_ref[i0]
        h_max = h_ref[i0]
        for i in range(i0, i1):
            if h_ref[i] < h_min:
                h_min = h_ref[i]
            if h_ref[i] > h_max:
                h_max = h_ref[i]
        h_scale = h_max - h_min
        if h_scale < 1e-12:
            h_scale = 1.0

        s_align = 0.0
        for i in range(i0, i1):
            diff = tr[i] - (rt[i] + offset)
            s_align += diff * diff
        align = np.sqrt(s_align / m) / h_scale

        s_ring = 0.0
        count = 0
        for i in range(i0 + 1, i1 - 1):
            curv_tr = tr[i + 1] - 2.0 * tr[i] + tr[i - 1]
            curv_rt = rt[i + 1] - 2.0 * rt[i] + rt[i - 1]
            s_ring += 0.5 * (curv_tr * curv_tr + curv_rt * curv_rt)
            count += 1
        ring = np.sqrt(s_ring / count) / h_scale if count > 0 else 0.0

        s_sat = 0.0
        for i in range(i0, i1):
            if sat_trace[i] > 0.5:
                s_sat += 0.5
            if sat_retrace[i] > 0.5:
                s_sat += 0.5
        sat_frac = s_sat / m

        return w_align * align + w_ring * ring + w_sat * sat_frac, align, ring, sat_frac


    @njit(parallel=True, cache=True)
    def _grid_fit_PI_substeps_numba(
        h,
        d_grid,
        A_grid,
        phi_grid,
        F_grid,
        A0,
        setpoint,
        scan_speed_hat,
        dx_hat,
        P_values,
        I_values,
        use_A_filter,
        tau_A,
        use_phi_filter,
        tau_phi,
        use_z_filter,
        tau_z,
        z_rate_limit_hat,
        use_z_rate_limit,
        d_init_hat,
        phi_meas_init_deg,
        T_I,
        use_leaky_I,
        integ_clip,
        use_integ_clip,
        n_substeps,
        antiwindup,
        contact_A_frac,
        saturation_A_frac,
        trim,
        w_align,
        w_ring,
        w_sat,
    ):
        nP = P_values.shape[0]
        nI = I_values.shape[0]
        loss_grid = np.empty((nP, nI))
        align_grid = np.empty((nP, nI))
        ring_grid = np.empty((nP, nI))
        sat_grid = np.empty((nP, nI))

        for idx in prange(nP * nI):
            ip = idx // nI
            ii = idx - ip * nI
            P = P_values[ip]
            I = I_values[ii]

            trace = _simulate_one_line_substeps_numba(
                h, d_grid, A_grid, phi_grid, F_grid, A0,
                setpoint, scan_speed_hat, dx_hat, P, I,
                use_A_filter, tau_A, use_phi_filter, tau_phi,
                use_z_filter, tau_z, z_rate_limit_hat, use_z_rate_limit,
                d_init_hat, d_init_hat, phi_meas_init_deg, 0.0, False,
                T_I, use_leaky_I, 0.0, integ_clip, use_integ_clip,
                n_substeps, antiwindup, contact_A_frac, saturation_A_frac,
                False, False,
            )
            retrace = _simulate_one_line_substeps_numba(
                h, d_grid, A_grid, phi_grid, F_grid, A0,
                setpoint, scan_speed_hat, dx_hat, P, I,
                use_A_filter, tau_A, use_phi_filter, tau_phi,
                use_z_filter, tau_z, z_rate_limit_hat, use_z_rate_limit,
                trace[14], trace[15], trace[17], trace[16], True,
                T_I, use_leaky_I, trace[18], integ_clip, use_integ_clip,
                n_substeps, antiwindup, contact_A_frac, saturation_A_frac,
                True, False,
            )

            tr = trace[1]
            rt_scan = retrace[1]
            sat_tr = np.maximum(trace[12], trace[13])
            sat_rt_scan = np.maximum(retrace[12], retrace[13])
            n = tr.shape[0]
            rt = np.empty(n)
            sat_rt = np.empty(n)
            for k in range(n):
                rt[k] = rt_scan[n - 1 - k]
                sat_rt[k] = sat_rt_scan[n - 1 - k]

            loss, align, ring, sat_frac = _quality_loss_from_trace_retrace_numba(
                tr, rt, h, sat_tr, sat_rt, trim, w_align, w_ring, w_sat
            )
            loss_grid[ip, ii] = loss
            align_grid[ip, ii] = align
            ring_grid[ip, ii] = ring
            sat_grid[ip, ii] = sat_frac

        return loss_grid, align_grid, ring_grid, sat_grid

else:
    # Stubs used only when numba is not importable.
    def _simulate_one_line_substeps_numba(*args, **kwargs):  # pragma: no cover
        raise ImportError("numba is required for the fast substep simulation.")

    def _grid_fit_PI_substeps_numba(*args, **kwargs):  # pragma: no cover
        raise ImportError("numba is required for the fast parallel PI fit.")


def _tuple_to_fast_scan_dict(tup, n_substeps: int) -> Dict[str, np.ndarray]:
    (
        out_d_cmd,
        out_d_act,
        out_d_eff,
        out_A_true,
        out_A_meas,
        out_A0,
        out_A_set,
        out_phi_true,
        out_phi_meas,
        out_F,
        out_err,
        out_integ,
        out_low_sat,
        out_high_sat,
        d_cmd_final,
        d_final,
        A_meas_final,
        phi_meas_final,
        integ_final,
        dt_pixel,
        dt_inner,
    ) = tup
    low = out_low_sat > 0.5
    high = out_high_sat > 0.5
    sat = low | high
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
        "integ": out_integ,
        "low_sat": low,
        "high_sat": high,
        "sat": sat,
        "low_sat_frac": float(np.mean(low)),
        "high_sat_frac": float(np.mean(high)),
        "sat_frac": float(np.mean(sat)),
        "dt_pixel": float(dt_pixel),
        "dt_inner": float(dt_inner),
        "n_substeps": int(n_substeps),
        "d_cmd_final_hat": float(d_cmd_final),
        "d_final_hat": float(d_final),
        "A_meas_final_hat": float(A_meas_final),
        "phi_meas_final_deg": float(phi_meas_final),
        "integ_final": float(integ_final),
    }


def simulate_trace_retrace_substeps_fast(
    scanner,
    h_hat,
    *,
    drive_nm=20.0,
    setpoint=0.6,
    scan_speed_hat=1.0,
    dx_hat=1.0,
    P=0.1,
    I=0.01,
    A_filter_order=None,
    tau_A=None,
    phi_filter_order=None,
    tau_phi=None,
    z_filter_order=None,
    tau_z=None,
    z_rate_limit_hat=None,
    d_init_hat=250.0,
    phi_meas_init_deg=120.0,
    A_meas_init_hat=None,
    T_I=None,
    integ_clip=None,
    n_substeps=50,
    dt_inner_max=None,
    antiwindup=True,
    contact_A_frac=0.02,
    saturation_A_frac=0.98,
    record_mode="last",
    carry_state_to_retrace=True,
    h_smooth_sigma_px=0.0,
    fd_table=None,
    fd_n_d=4096,
):
    """Fast Numba trace/retrace simulation with subpixel feedback updates."""
    if not _NUMBA_AVAILABLE:
        raise ImportError("numba is required for simulate_trace_retrace_substeps_fast().")

    h_sim = smooth_height_profile(h_hat, sigma_px=h_smooth_sigma_px)
    h_sim = np.asarray(h_sim, dtype=np.float64).ravel()
    if fd_table is None:
        fd_table = prepare_fd_table_for_drive(scanner, drive_nm=drive_nm, n_d=fd_n_d)

    if dt_inner_max is not None and dt_inner_max > 0:
        dt_pixel = float(dx_hat) / float(scan_speed_hat)
        n_substeps = max(int(n_substeps), int(np.ceil(dt_pixel / float(dt_inner_max))))
    n_substeps = int(max(1, n_substeps))

    use_A_filter = (A_filter_order is not None) and (tau_A is not None) and (float(tau_A) > 0.0)
    use_phi_filter = (phi_filter_order is not None) and (tau_phi is not None) and (float(tau_phi) > 0.0)
    use_z_filter = (z_filter_order is not None) and (tau_z is not None) and (float(tau_z) > 0.0)
    use_z_rate_limit = z_rate_limit_hat is not None
    use_leaky_I = (T_I is not None) and (float(T_I) > 0.0)
    use_integ_clip = integ_clip is not None
    use_A_meas_init = A_meas_init_hat is not None
    record_mean = str(record_mode).lower() == "mean"

    trace_tuple = _simulate_one_line_substeps_numba(
        h_sim,
        fd_table["d_grid"], fd_table["A_grid"], fd_table["phi_grid"], fd_table["F_grid"], float(fd_table["A0"]),
        float(setpoint), float(scan_speed_hat), float(dx_hat), float(P), float(I),
        bool(use_A_filter), 0.0 if tau_A is None else float(tau_A),
        bool(use_phi_filter), 0.0 if tau_phi is None else float(tau_phi),
        bool(use_z_filter), 0.0 if tau_z is None else float(tau_z),
        0.0 if z_rate_limit_hat is None else float(z_rate_limit_hat), bool(use_z_rate_limit),
        float(d_init_hat), float(d_init_hat), float(phi_meas_init_deg),
        0.0 if A_meas_init_hat is None else float(A_meas_init_hat), bool(use_A_meas_init),
        0.0 if T_I is None else float(T_I), bool(use_leaky_I), 0.0,
        0.0 if integ_clip is None else float(integ_clip), bool(use_integ_clip),
        int(n_substeps), bool(antiwindup), float(contact_A_frac), float(saturation_A_frac),
        False, bool(record_mean),
    )
    trace = _tuple_to_fast_scan_dict(trace_tuple, n_substeps)

    if carry_state_to_retrace:
        d_cmd_init_rt = trace["d_cmd_final_hat"]
        d_act_init_rt = trace["d_final_hat"]
        A_init_rt = trace["A_meas_final_hat"]
        phi_init_rt = trace["phi_meas_final_deg"]
        integ_init_rt = trace["integ_final"]
        use_A_init_rt = True
    else:
        d_cmd_init_rt = float(d_init_hat)
        d_act_init_rt = float(d_init_hat)
        A_init_rt = 0.0 if A_meas_init_hat is None else float(A_meas_init_hat)
        phi_init_rt = float(phi_meas_init_deg)
        integ_init_rt = 0.0
        use_A_init_rt = A_meas_init_hat is not None

    retrace_tuple = _simulate_one_line_substeps_numba(
        h_sim,
        fd_table["d_grid"], fd_table["A_grid"], fd_table["phi_grid"], fd_table["F_grid"], float(fd_table["A0"]),
        float(setpoint), float(scan_speed_hat), float(dx_hat), float(P), float(I),
        bool(use_A_filter), 0.0 if tau_A is None else float(tau_A),
        bool(use_phi_filter), 0.0 if tau_phi is None else float(tau_phi),
        bool(use_z_filter), 0.0 if tau_z is None else float(tau_z),
        0.0 if z_rate_limit_hat is None else float(z_rate_limit_hat), bool(use_z_rate_limit),
        float(d_cmd_init_rt), float(d_act_init_rt), float(phi_init_rt), float(A_init_rt), bool(use_A_init_rt),
        0.0 if T_I is None else float(T_I), bool(use_leaky_I), float(integ_init_rt),
        0.0 if integ_clip is None else float(integ_clip), bool(use_integ_clip),
        int(n_substeps), bool(antiwindup), float(contact_A_frac), float(saturation_A_frac),
        True, bool(record_mean),
    )
    retrace_scan_order = _tuple_to_fast_scan_dict(retrace_tuple, n_substeps)

    n = h_sim.size
    retrace = {}
    for k, v in retrace_scan_order.items():
        arr = np.asarray(v)
        if arr.ndim == 1 and arr.size == n:
            retrace[k] = arr[::-1].copy()
        else:
            retrace[k] = v

    return {
        "trace": trace,
        "retrace": retrace,
        "raw_retrace": retrace_scan_order,
        "settings": {
            "drive_nm": float(drive_nm),
            "setpoint": float(setpoint),
            "scan_speed_hat": float(scan_speed_hat),
            "dx_hat": float(dx_hat),
            "P": float(P),
            "I": float(I),
            "n_substeps": int(n_substeps),
            "record_mode": str(record_mode),
            "h_smooth_sigma_px": float(0.0 if h_smooth_sigma_px is None else h_smooth_sigma_px),
        },
        "fd_table": fd_table,
        "h_sim": h_sim,
    }


def grid_fit_PI_substeps_fast_parallel(
    scanner,
    h_truth,
    *,
    drive_nm=20.0,
    setpoint=0.6,
    scan_speed_hat=1.0,
    dx_hat=1.0,
    P_values=None,
    I_values=None,
    A_filter_order=None,
    tau_A=None,
    phi_filter_order=None,
    tau_phi=None,
    z_filter_order=None,
    tau_z=None,
    z_rate_limit_hat=1e6,
    d_init_hat=250.0,
    phi_meas_init_deg=120.0,
    T_I=3e-1,
    integ_clip=2.0,
    n_substeps=50,
    antiwindup=True,
    contact_A_frac=0.02,
    saturation_A_frac=0.98,
    trim=10,
    w_align=1.0,
    w_ring=3.0,
    w_sat=20.0,
    h_smooth_sigma_px=0.0,
    fd_table=None,
    fd_n_d=4096,
):
    """Parallel Numba grid search over P and I for the fast substep model."""
    if not _NUMBA_AVAILABLE:
        raise ImportError("numba is required for grid_fit_PI_substeps_fast_parallel().")
    if P_values is None:
        P_values = np.logspace(-2, 0, 31)
    if I_values is None:
        I_values = np.r_[0.0, np.logspace(-4, 0, 31)]
    P_values = np.asarray(P_values, dtype=np.float64)
    I_values = np.asarray(I_values, dtype=np.float64)

    h_sim = smooth_height_profile(h_truth, sigma_px=h_smooth_sigma_px)
    h_sim = np.asarray(h_sim, dtype=np.float64).ravel()
    if fd_table is None:
        fd_table = prepare_fd_table_for_drive(scanner, drive_nm=drive_nm, n_d=fd_n_d)

    use_A_filter = (A_filter_order is not None) and (tau_A is not None) and (float(tau_A) > 0.0)
    use_phi_filter = (phi_filter_order is not None) and (tau_phi is not None) and (float(tau_phi) > 0.0)
    use_z_filter = (z_filter_order is not None) and (tau_z is not None) and (float(tau_z) > 0.0)
    use_z_rate_limit = z_rate_limit_hat is not None
    use_leaky_I = (T_I is not None) and (float(T_I) > 0.0)
    use_integ_clip = integ_clip is not None

    loss_grid, align_grid, ring_grid, sat_grid = _grid_fit_PI_substeps_numba(
        h_sim,
        fd_table["d_grid"], fd_table["A_grid"], fd_table["phi_grid"], fd_table["F_grid"], float(fd_table["A0"]),
        float(setpoint), float(scan_speed_hat), float(dx_hat),
        P_values, I_values,
        bool(use_A_filter), 0.0 if tau_A is None else float(tau_A),
        bool(use_phi_filter), 0.0 if tau_phi is None else float(tau_phi),
        bool(use_z_filter), 0.0 if tau_z is None else float(tau_z),
        0.0 if z_rate_limit_hat is None else float(z_rate_limit_hat), bool(use_z_rate_limit),
        float(d_init_hat), float(phi_meas_init_deg),
        0.0 if T_I is None else float(T_I), bool(use_leaky_I),
        0.0 if integ_clip is None else float(integ_clip), bool(use_integ_clip),
        int(max(1, n_substeps)), bool(antiwindup), float(contact_A_frac), float(saturation_A_frac),
        int(trim), float(w_align), float(w_ring), float(w_sat),
    )

    best_idx = np.unravel_index(np.nanargmin(loss_grid), loss_grid.shape)
    iP, iI = best_idx
    best_P = float(P_values[iP])
    best_I = float(I_values[iI])

    best_out = simulate_trace_retrace_substeps_fast(
        scanner,
        h_sim,
        drive_nm=drive_nm,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        P=best_P,
        I=best_I,
        A_filter_order=A_filter_order,
        tau_A=tau_A,
        phi_filter_order=phi_filter_order,
        tau_phi=tau_phi,
        z_filter_order=z_filter_order,
        tau_z=tau_z,
        z_rate_limit_hat=z_rate_limit_hat,
        d_init_hat=d_init_hat,
        phi_meas_init_deg=phi_meas_init_deg,
        T_I=T_I,
        integ_clip=integ_clip,
        n_substeps=n_substeps,
        antiwindup=antiwindup,
        contact_A_frac=contact_A_frac,
        saturation_A_frac=saturation_A_frac,
        h_smooth_sigma_px=0.0,
        fd_table=fd_table,
    )

    return {
        "P_values": P_values,
        "I_values": I_values,
        "loss_grid": loss_grid,
        "align_grid": align_grid,
        "ring_grid": ring_grid,
        "sat_grid": sat_grid,
        "best": {
            "P": best_P,
            "I": best_I,
            "loss": float(loss_grid[iP, iI]),
            "align": float(align_grid[iP, iI]),
            "ring": float(ring_grid[iP, iI]),
            "sat_frac": float(sat_grid[iP, iI]),
            "out": best_out,
        },
        "fd_table": fd_table,
        "h_sim": h_sim,
        "h_smooth_sigma_px": float(0.0 if h_smooth_sigma_px is None else h_smooth_sigma_px),
    }


def plot_fast_substep_result(fit_or_out, title: Optional[str] = None):
    """Quick diagnostic plot for fast substep simulations or fit results."""
    import matplotlib.pyplot as plt
    if isinstance(fit_or_out, dict) and "best" in fit_or_out:
        out = fit_or_out["best"]["out"]
        if title is None:
            title = (
                f"P={fit_or_out['best']['P']:.3g}, I={fit_or_out['best']['I']:.3g}, "
                f"loss={fit_or_out['best']['loss']:.3g}"
            )
    else:
        out = fit_or_out

    fig, ax = plt.subplots(1, 3, figsize=(11, 3.2))
    ax[0].plot(out["trace"]["d_hat"], label="trace")
    ax[0].plot(out["retrace"]["d_hat"], label="retrace")
    ax[0].set_title("Height")
    ax[1].plot(out["trace"]["A_hat"], label="trace")
    ax[1].plot(out["retrace"]["A_hat"], label="retrace")
    if "A_set_hat" in out["trace"]:
        ax[1].axhline(np.nanmedian(out["trace"]["A_set_hat"]), color="k", ls="--", label="A_set")
    if "A0_hat" in out["trace"]:
        ax[1].axhline(np.nanmedian(out["trace"]["A0_hat"]), color="k", ls=":", label="A0")
    ax[1].set_title("Amplitude")
    ax[2].plot(out["trace"]["phi_deg"], label="trace")
    ax[2].plot(out["retrace"]["phi_deg"], label="retrace")
    ax[2].set_title("Phase")
    for a in ax:
        a.legend(fontsize=8)
    if title is not None:
        fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def plot_PI_substep_search(fit):
    """Plot loss/alignment/ringing/saturation maps from grid_fit_PI_substeps_fast_parallel."""
    import matplotlib.pyplot as plt
    P = np.asarray(fit["P_values"], dtype=float)
    I = np.asarray(fit["I_values"], dtype=float).copy()
    if np.any(I == 0):
        pos = I[I > 0]
        I[I == 0] = (np.min(pos) * 0.3) if pos.size else 1e-12
    X, Y = np.meshgrid(I, P)
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.2))
    panels = [
        ("loss", fit["loss_grid"]),
        ("alignment", fit["align_grid"]),
        ("ringing", fit["ring_grid"]),
        ("saturation", fit["sat_grid"]),
    ]
    for a, (name, Z) in zip(ax, panels):
        im = a.pcolormesh(X, Y, Z, shading="auto")
        a.set_xscale("log")
        a.set_yscale("log")
        a.set_xlabel("I")
        a.set_ylabel("P")
        a.set_title(name)
        a.plot(fit["best"]["I"], fit["best"]["P"], "rx", ms=8, mew=2)
        plt.colorbar(im, ax=a)
    plt.tight_layout()
    plt.show()


# Convenience methods on ScannerFD. These do not override the existing methods.
def _scanner_prepare_fd_table_for_drive(self, drive_nm, n_d: int = 4096, d_pad_frac: float = 0.05):
    return prepare_fd_table_for_drive(self, drive_nm=drive_nm, n_d=n_d, d_pad_frac=d_pad_frac)


def _scanner_simulate_trace_retrace_substeps_fast(self, h_hat, **kwargs):
    return simulate_trace_retrace_substeps_fast(self, h_hat, **kwargs)


def _scanner_grid_fit_PI_substeps_fast_parallel(self, h_truth, **kwargs):
    return grid_fit_PI_substeps_fast_parallel(self, h_truth, **kwargs)


ScannerFD.prepare_fd_table_for_drive = _scanner_prepare_fd_table_for_drive
ScannerFD.simulate_trace_retrace_substeps_fast = _scanner_simulate_trace_retrace_substeps_fast
ScannerFD.grid_fit_PI_substeps_fast_parallel = _scanner_grid_fit_PI_substeps_fast_parallel

import numpy as np
from scipy.optimize import differential_evolution, minimize


def _is_enabled_tau(tau):
    return tau is not None and np.isfinite(float(tau)) and float(tau) > 0


def unpack_controller_params_PI_fixed_tau(
    x,
    tau_A_fixed=None,
    tau_phi_fixed=None,
    tau_z_fixed=None,
):
    """
    x = [log10_P, log10_I]
    """
    x = np.asarray(x, dtype=float).ravel()

    return {
        "P": 10.0 ** x[0],
        "I": 10.0 ** x[1],
        "tau_A": tau_A_fixed,
        "tau_phi": tau_phi_fixed,
        "tau_z": tau_z_fixed,
    }


def parse_h_exp(h_exp):
    """
    Flexible parser for experimental height trace/retrace.

    Accepts:
        h_exp shape (2, N): [trace, retrace]
        h_exp shape (>=2, N): first two are height trace/retrace
        tuple/list: (trace, retrace)
    """
    if isinstance(h_exp, (tuple, list)) and len(h_exp) == 2:
        return np.asarray(h_exp[0], dtype=float), np.asarray(h_exp[1], dtype=float)

    arr = np.asarray(h_exp, dtype=float)

    if arr.ndim == 2:
        if arr.shape[0] >= 2:
            return arr[0].astype(float), arr[1].astype(float)
        if arr.shape[1] >= 2:
            return arr[:, 0].astype(float), arr[:, 1].astype(float)

    raise ValueError(
        "Cannot parse h_exp. Expected (trace, retrace), shape (2, N), or shape (N, 2)."
    )


def crop_to_common_length(*arrays):
    n = min(len(np.asarray(a).ravel()) for a in arrays)
    return [np.asarray(a, dtype=float).ravel()[:n] for a in arrays]


def robust_mad(x, eps=1e-12):
    x = np.asarray(x, dtype=float).ravel()
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    return 1.4826 * mad + eps


def huber_loss(r, delta=2.0):
    r = np.asarray(r, dtype=float)
    a = np.abs(r)
    return np.where(a <= delta, 0.5 * r**2, delta * (a - 0.5 * delta))


def moving_average_1d(y, window=9):
    y = np.asarray(y, dtype=float).ravel()

    if window is None or window <= 1:
        return y.copy()

    window = int(window)
    if window % 2 == 0:
        window += 1

    pad = window // 2
    yp = np.pad(y, pad, mode="edge")
    ker = np.ones(window, dtype=float) / window

    return np.convolve(yp, ker, mode="valid")


def highpass_1d(y, window=9):
    return np.asarray(y, dtype=float).ravel() - moving_average_1d(y, window=window)


def common_offset_align(sim_tr, sim_rt, exp_tr, exp_rt):
    """
    Apply one common vertical offset to simulation so absolute z-origin
    mismatch does not dominate the loss.
    """
    sim_mid = 0.5 * (sim_tr + sim_rt)
    exp_mid = 0.5 * (exp_tr + exp_rt)

    offset = np.nanmedian(exp_mid - sim_mid)

    return sim_tr + offset, sim_rt + offset, offset
    
def make_scan_objective_exp_PI_fixed_tau(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    # Fixed time constants. Default None means disabled.
    tau_A_fixed=None,
    tau_phi_fixed=None,
    tau_z_fixed=None,

    # Fixed scanner parameters
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-1,
    integ_clip=None,

    # Substep controls
    n_substeps=50,
    dt_inner_max=None,
    antiwindup=True,
    contact_A_frac=0.02,
    saturation_A_frac=0.98,
    record_mode="last",
    carry_state_to_retrace=True,

    # Optional precomputed FD table
    fd_table=None,
    fd_n_d=4096,

    # Optional effective tip/edge smoothing
    h_smooth_sigma_px=0.0,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    w_saturation=2.0,
    huber_delta=2.0,
    mse_floor_frac=0.03,
    hp_window=9,

    verbose=False,
):
    """
    Objective for fitting only P and I while keeping time constants fixed.

    Optimized vector:
        x = [log10_P, log10_I]

    Fixed/optional time constants:
        tau_A_fixed=None   -> amplitude filter disabled
        tau_phi_fixed=None -> phase filter disabled
        tau_z_fixed=None   -> z actuator filter disabled
        T_I=None           -> pure integrator
        T_I>0              -> leaky integrator
    """

    h_input = np.asarray(h_input, dtype=float).ravel()
    exp_tr, exp_rt = parse_h_exp(h_exp)

    use_A_filter = _is_enabled_tau(tau_A_fixed)
    use_phi_filter = _is_enabled_tau(tau_phi_fixed)
    use_z_filter = _is_enabled_tau(tau_z_fixed)

    A_filter_order = 1 if use_A_filter else None
    phi_filter_order = 1 if use_phi_filter else None
    z_filter_order = 1 if use_z_filter else None

    if fd_table is None and hasattr(scanner, "prepare_fd_table_for_drive"):
        fd_table = scanner.prepare_fd_table_for_drive(
            drive_nm=drive,
            n_d=fd_n_d,
        )

    def objective(x, return_full=False):
        p = unpack_controller_params_PI_fixed_tau(
            x,
            tau_A_fixed=tau_A_fixed,
            tau_phi_fixed=tau_phi_fixed,
            tau_z_fixed=tau_z_fixed,
        )

        try:
            if hasattr(scanner, "simulate_trace_retrace_substeps_fast"):
                out = scanner.simulate_trace_retrace_substeps_fast(
                    h_input,
                    drive_nm=drive,
                    setpoint=setpoint,

                    scan_speed_hat=scan_speed_hat,
                    dx_hat=dx_hat,

                    P=p["P"],
                    I=p["I"],

                    A_filter_order=A_filter_order,
                    tau_A=tau_A_fixed,

                    phi_filter_order=phi_filter_order,
                    tau_phi=tau_phi_fixed,

                    z_filter_order=z_filter_order,
                    tau_z=tau_z_fixed,
                    z_rate_limit_hat=z_rate_limit_hat,

                    d_init_hat=d_init_hat,
                    phi_meas_init_deg=phi_meas_init_deg,
                    T_I=T_I,
                    integ_clip=integ_clip,

                    n_substeps=n_substeps,
                    dt_inner_max=dt_inner_max,

                    antiwindup=antiwindup,
                    contact_A_frac=contact_A_frac,
                    saturation_A_frac=saturation_A_frac,

                    record_mode=record_mode,
                    carry_state_to_retrace=carry_state_to_retrace,

                    fd_table=fd_table,
                    fd_n_d=fd_n_d,
                    h_smooth_sigma_px=h_smooth_sigma_px,
                )
            else:
                # Fallback to older non-numba scanner method.
                out = scanner.scan_line_trace_retrace_pi_drive(
                    h_hat=h_input,
                    drive_nm=drive,
                    setpoint=setpoint,

                    scan_speed_hat=scan_speed_hat,
                    dx_hat=dx_hat,

                    P=p["P"],
                    I=p["I"],

                    A_filter_order=A_filter_order,
                    tau_A=tau_A_fixed,

                    phi_filter_order=phi_filter_order,
                    tau_phi=tau_phi_fixed,

                    z_filter_order=z_filter_order,
                    tau_z=tau_z_fixed,
                    z_rate_limit_hat=z_rate_limit_hat,

                    d_init_hat=d_init_hat,
                    phi_meas_init_deg=phi_meas_init_deg,
                    T_I=T_I,
                    integ_clip=integ_clip,
                )

            sim_tr = np.asarray(out["trace"]["d_hat"], dtype=float)
            sim_rt = np.asarray(out["retrace"]["d_hat"], dtype=float)

            sim_tr, sim_rt, e_tr, e_rt = crop_to_common_length(
                sim_tr,
                sim_rt,
                exp_tr,
                exp_rt,
            )

            if trim is not None and trim > 0 and len(sim_tr) > 2 * trim:
                sl = slice(trim, -trim)
                sim_tr = sim_tr[sl]
                sim_rt = sim_rt[sl]
                e_tr = e_tr[sl]
                e_rt = e_rt[sl]

            sim_tr_a, sim_rt_a, offset = common_offset_align(
                sim_tr,
                sim_rt,
                e_tr,
                e_rt,
            )

            exp_scale = robust_mad(np.r_[e_tr, e_rt])

            # ------------------------------------------------------------
            # 1. Height match: sim trace/retrace should match experiment.
            # ------------------------------------------------------------
            r_tr = (sim_tr_a - e_tr) / exp_scale
            r_rt = (sim_rt_a - e_rt) / exp_scale

            L_height = np.nanmean(huber_loss(r_tr, huber_delta)) + np.nanmean(
                huber_loss(r_rt, huber_delta)
            )

            # ------------------------------------------------------------
            # 2. Match trace/retrace misalignment level.
            #    This does not force perfect alignment; it tries to match
            #    the experimental trace-retrace MSE.
            # ------------------------------------------------------------
            diff_exp = e_tr - e_rt
            diff_sim = sim_tr_a - sim_rt_a

            mse_exp = np.nanmean(diff_exp**2)
            mse_sim = np.nanmean(diff_sim**2)

            mse_floor = (mse_floor_frac * exp_scale) ** 2
            mse_ratio = mse_sim / max(mse_exp, mse_floor)

            L_mse = (np.log(mse_ratio + 1e-12)) ** 2

            # ------------------------------------------------------------
            # 3. Match trace-retrace difference profile.
            # ------------------------------------------------------------
            diff_scale = robust_mad(diff_exp)
            r_diff = (diff_sim - diff_exp) / diff_scale
            L_diff = np.nanmean(huber_loss(r_diff, huber_delta))

            # ------------------------------------------------------------
            # 4. Ringing/high-frequency penalty.
            #    Penalize excess high-frequency content in sim relative to exp.
            # ------------------------------------------------------------
            hp_sim_tr = highpass_1d(sim_tr_a, window=hp_window)
            hp_sim_rt = highpass_1d(sim_rt_a, window=hp_window)
            hp_exp_tr = highpass_1d(e_tr, window=hp_window)
            hp_exp_rt = highpass_1d(e_rt, window=hp_window)

            ring_sim = 0.5 * (
                np.nanmean(hp_sim_tr**2) + np.nanmean(hp_sim_rt**2)
            )
            ring_exp = 0.5 * (
                np.nanmean(hp_exp_tr**2) + np.nanmean(hp_exp_rt**2)
            )

            L_ringing = ring_sim / max(ring_exp, mse_floor)

            # ------------------------------------------------------------
            # 5. Amplitude-setpoint penalty.
            #    Useful when the scan goes into A=0 or A=A0 saturation.
            # ------------------------------------------------------------
            L_amp = 0.0

            try:
                A_tr = np.asarray(out["trace"]["A_hat"], dtype=float)
                A_rt = np.asarray(out["retrace"]["A_hat"], dtype=float)
                Aset_tr = np.asarray(out["trace"]["A_set_hat"], dtype=float)
                Aset_rt = np.asarray(out["retrace"]["A_set_hat"], dtype=float)
                A0_tr = np.asarray(out["trace"]["A0_hat"], dtype=float)
                A0_rt = np.asarray(out["retrace"]["A0_hat"], dtype=float)

                A_tr, A_rt, Aset_tr, Aset_rt, A0_tr, A0_rt = crop_to_common_length(
                    A_tr,
                    A_rt,
                    Aset_tr,
                    Aset_rt,
                    A0_tr,
                    A0_rt,
                )

                if trim is not None and trim > 0 and len(A_tr) > 2 * trim:
                    A_tr = A_tr[sl]
                    A_rt = A_rt[sl]
                    Aset_tr = Aset_tr[sl]
                    Aset_rt = Aset_rt[sl]
                    A0_tr = A0_tr[sl]
                    A0_rt = A0_rt[sl]

                A_scale = max(np.nanmedian(np.r_[A0_tr, A0_rt]), 1e-12)

                L_amp = 0.5 * (
                    np.nanmean(((A_tr - Aset_tr) / A_scale) ** 2)
                    + np.nanmean(((A_rt - Aset_rt) / A_scale) ** 2)
                )

            except Exception:
                L_amp = 0.0

            # ------------------------------------------------------------
            # 6. Saturation penalty.
            # ------------------------------------------------------------
            sat_frac = 0.0

            try:
                sat_frac = 0.5 * (
                    float(out["trace"].get("sat_frac", 0.0))
                    + float(out["retrace"].get("sat_frac", 0.0))
                )
            except Exception:
                sat_frac = 0.0

            L_sat = sat_frac

            loss_noise = np.abs(np.std(e_tr) - np.std(sim_tr_a))

            loss = (
                w_height_match * L_height
                + loss_noise * 0.2
                + w_mse_match * 0.2
                + w_diff_profile * 0.2
                # + w_mse_match * L_mse
                # + w_diff_profile * L_diff
                # + w_ringing * L_ringing
                # + w_amp * L_amp
                # + w_saturation * L_sat
            )

            details = {
                "L_height": float(L_height),
                "L_mse": float(L_mse),
                "L_diff": float(L_diff),
                "L_ringing": float(L_ringing),
                "L_amp": float(L_amp),
                "L_sat": float(L_sat),
                "mse_exp": float(mse_exp),
                "mse_sim": float(mse_sim),
                "mse_ratio": float(mse_ratio),
                "ring_sim": float(ring_sim),
                "ring_exp": float(ring_exp),
                "sat_frac": float(sat_frac),
                "offset": float(offset),
                "A_filter_enabled": bool(use_A_filter),
                "phi_filter_enabled": bool(use_phi_filter),
                "z_filter_enabled": bool(use_z_filter),
                "n_substeps": int(n_substeps),
            }

            if return_full:
                return float(loss), details, out, p

            return float(loss)

        except Exception as e:
            if verbose:
                print("Objective failed:", e)

            if return_full:
                return np.inf, {"error": str(e)}, None, p

            return np.inf

    return objective
    
    
def fit_controller_to_experiment_PI_fixed_tau(
    scanner,
    h_input,
    h_exp,

    drive=20,
    setpoint=0.6,
    scan_speed_hat=1e3,
    dx_hat=1.0,

    # Fixed time constants.
    # Default None means disabled.
    tau_A_fixed=None,
    tau_phi_fixed=None,
    tau_z_fixed=None,

    # Backward-compatible alias. If tau_z is provided, it overrides tau_z_fixed.
    tau_z=None,

    # Fixed scanner parameters
    z_rate_limit_hat=1e6,
    d_init_hat=250,
    phi_meas_init_deg=120,
    T_I=3e-1,
    integ_clip=None,

    # Substep controls
    n_substeps=50,
    dt_inner_max=None,
    antiwindup=True,
    contact_A_frac=0.02,
    saturation_A_frac=0.98,
    record_mode="last",
    carry_state_to_retrace=True,

    # Optional precomputed FD table
    fd_table=None,
    fd_n_d=4096,

    # Optional effective tip/edge smoothing
    h_smooth_sigma_px=0.0,

    # Loss parameters
    trim=20,
    w_height_match=1.0,
    w_mse_match=0.5,
    w_diff_profile=0.1,
    w_ringing=0.05,
    w_amp=0.02,
    w_saturation=2.0,
    huber_delta=2.0,
    mse_floor_frac=0.03,
    hp_window=9,

    # Optimizer controls
    maxiter_global=200,
    maxiter_local=300,
    global_tol=0.02,
    local_xatol=1e-3,
    local_fatol=1e-4,
    loss_target=None,
    seed=0,
    popsize=8,

    # Optional: use coarse grid instead of differential evolution
    use_grid_init=False,
    n_grid_P=25,
    n_grid_I=25,

    # Bounds in log10-space
    bounds=None,

    verbose=True,
):
    """
    Fit only P and I while keeping all time constants fixed.

    Optimized vector:
        x = [log10_P, log10_I]

    Default behavior:
        tau_A_fixed=None   -> amplitude detector filter disabled
        tau_phi_fixed=None -> phase detector filter disabled
        tau_z_fixed=None   -> z actuator filter disabled
        T_I=0.3            -> leaky integrator memory enabled

    To enable fixed filters:
        tau_A_fixed=0.01
        tau_phi_fixed=0.01
        tau_z_fixed=0.05
    """

    if tau_z is not None:
        tau_z_fixed = tau_z

    if bounds is None:
        bounds = [
            (-4.0, 2.0),   # log10_P
            (-5.0, 2.0),   # log10_I
        ]

    if fd_table is None and hasattr(scanner, "prepare_fd_table_for_drive"):
        fd_table = scanner.prepare_fd_table_for_drive(
            drive_nm=drive,
            n_d=fd_n_d,
        )

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
        tau_z_fixed=tau_z_fixed,

        z_rate_limit_hat=z_rate_limit_hat,
        d_init_hat=d_init_hat,
        phi_meas_init_deg=phi_meas_init_deg,
        T_I=T_I,
        integ_clip=integ_clip,

        n_substeps=n_substeps,
        dt_inner_max=dt_inner_max,
        antiwindup=antiwindup,
        contact_A_frac=contact_A_frac,
        saturation_A_frac=saturation_A_frac,
        record_mode=record_mode,
        carry_state_to_retrace=carry_state_to_retrace,

        fd_table=fd_table,
        fd_n_d=fd_n_d,
        h_smooth_sigma_px=h_smooth_sigma_px,

        trim=trim,
        w_height_match=w_height_match,
        w_mse_match=w_mse_match,
        w_diff_profile=w_diff_profile,
        w_ringing=w_ringing,
        w_amp=w_amp,
        w_saturation=w_saturation,
        huber_delta=huber_delta,
        mse_floor_frac=mse_floor_frac,
        hp_window=hp_window,

        verbose=False,
    )

    best_seen = {
        "loss": np.inf,
        "x": None,
    }

    # ------------------------------------------------------------
    # Optional grid initialization.
    # For 2D P/I fitting, this is often faster and more transparent.
    # ------------------------------------------------------------
    res_grid = None

    if use_grid_init:
        logP_grid = np.linspace(bounds[0][0], bounds[0][1], int(n_grid_P))
        logI_grid = np.linspace(bounds[1][0], bounds[1][1], int(n_grid_I))

        loss_grid = np.full((len(logP_grid), len(logI_grid)), np.nan)

        for i, logP in enumerate(logP_grid):
            for j, logI in enumerate(logI_grid):
                x = np.array([logP, logI], dtype=float)
                loss = objective(x)
                loss_grid[i, j] = loss

                if np.isfinite(loss) and loss < best_seen["loss"]:
                    best_seen["loss"] = float(loss)
                    best_seen["x"] = x.copy()

                    if verbose:
                        p = unpack_controller_params_PI_fixed_tau(
                            x,
                            tau_A_fixed=tau_A_fixed,
                            tau_phi_fixed=tau_phi_fixed,
                            tau_z_fixed=tau_z_fixed,
                        )

                        # print(
                        #     f"[grid] loss={loss:.5g}, "
                        #     f"P={p['P']:.4g}, I={p['I']:.4g}, "
                        #     f"tau_A={p['tau_A']}, "
                        #     f"tau_phi={p['tau_phi']}, "
                        #     f"tau_z={p['tau_z']}"
                        # )

                if loss_target is not None and np.isfinite(loss) and loss <= loss_target:
                    if verbose:
                        print(f"Stopping early in grid because loss <= {loss_target}")

                    best_loss, best_details, best_out, best_params = objective(
                        best_seen["x"],
                        return_full=True,
                    )

                    return {
                        "best_x": best_seen["x"],
                        "best_params": best_params,
                        "best_loss": best_loss,
                        "best_details": best_details,
                        "best_out": best_out,
                        "best_source": "grid_early_stop",
                        "res_global": None,
                        "res_local": None,
                        "res_grid": {
                            "logP_grid": logP_grid,
                            "logI_grid": logI_grid,
                            "loss_grid": loss_grid,
                        },
                        "objective": objective,
                        "tau_A_fixed": tau_A_fixed,
                        "tau_phi_fixed": tau_phi_fixed,
                        "tau_z_fixed": tau_z_fixed,
                        "T_I": T_I,
                        "fd_table": fd_table,
                    }

        res_grid = {
            "logP_grid": logP_grid,
            "logI_grid": logI_grid,
            "loss_grid": loss_grid,
        }

        x0 = best_seen["x"]

        if x0 is None:
            x0 = np.array(
                [
                    0.5 * (bounds[0][0] + bounds[0][1]),
                    0.5 * (bounds[1][0] + bounds[1][1]),
                ],
                dtype=float,
            )

        res_global = None

    else:
        # ------------------------------------------------------------
        # Differential evolution global search.
        # ------------------------------------------------------------
        def callback(xk, convergence):
            loss = objective(xk)

            if np.isfinite(loss) and loss < best_seen["loss"]:
                best_seen["loss"] = float(loss)
                best_seen["x"] = np.array(xk, dtype=float)

                if verbose:
                    p = unpack_controller_params_PI_fixed_tau(
                        xk,
                        tau_A_fixed=tau_A_fixed,
                        tau_phi_fixed=tau_phi_fixed,
                        tau_z_fixed=tau_z_fixed,
                    )

                    # # Avoid expensive return_full every callback.
                    # print(
                    #     f"loss={loss:.5g}, "
                    #     f"P={p['P']:.4g}, I={p['I']:.4g}, "
                    #     f"tau_A={p['tau_A']}, "
                    #     f"tau_phi={p['tau_phi']}, "
                    #     f"tau_z={p['tau_z']}"
                    # )

            if loss_target is not None and np.isfinite(loss) and loss <= loss_target:
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

    # ------------------------------------------------------------
    # Local refinement.
    # ------------------------------------------------------------
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

    # Decide best source.
    candidates = []

    if best_seen["x"] is not None:
        candidates.append(("best_seen", best_seen["x"], best_seen["loss"]))

    if res_global is not None:
        candidates.append(("global", res_global.x, res_global.fun))

    if res_local is not None and np.isfinite(res_local.fun):
        candidates.append(("local", res_local.x, res_local.fun))

    best_source, best_x, best_fun = min(candidates, key=lambda t: t[2])

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
        "res_grid": res_grid,

        "objective": objective,

        "tau_A_fixed": tau_A_fixed,
        "tau_phi_fixed": tau_phi_fixed,
        "tau_z_fixed": tau_z_fixed,
        "T_I": T_I,

        "n_substeps": n_substeps,
        "dt_inner_max": dt_inner_max,
        "h_smooth_sigma_px": h_smooth_sigma_px,

        "fd_table": fd_table,
        "bounds": bounds,
    }