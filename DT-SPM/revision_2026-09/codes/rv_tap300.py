"""Tap-300/AlScN analysis table and fold-clean physics prior (revision 2026-09).

Inference contract for a candidate condition c (pre-acquisition):
  allowed : candidate controls (scan speed, drive, setpoint, integral gain);
            the measured FD library (a separate spectroscopic acquisition);
            instrument calibration fitted ONLY on conditions outside the held-out
            block (local PI fits -> GP gain map, reference topography, RMS scale).
  never   : any height/amplitude/phase line of c or of any condition in c's
            held-out block, and any quantity derived from them (Q_align, Q_safety,
            fitted PI gains of c, normalisation statistics that include c).

`physics_prior(allowed)` rebuilds the deterministic-scanner prediction from these
inputs only; it reproduces the submitted cached traces exactly when `allowed`
is set to the submitted (leaky) calibration universe (see rv_audit.py).
"""
from __future__ import annotations

import numpy as np
from joblib import load

from rv_common import (CACHE_DIR, CACHE_TAG, OUT, ROOT, build_tap300_scanner,
                       center_line, load_tap300_raw, q_align, rms_match,
                       simulate, trace_rms)

BUNDLE = ROOT / "output" / "dt_controller_fit_figures" / "figure_45_expscan_data_bundle.npz"


# ---------------------------------------------------------------- FD operating point
def wrap_deg(p):
    p = np.mod(p, 360.0)
    return np.where(p > 180, p - 360, p)


def fd_op_features(V, s, fd_height, fd_amp, fd_phase, fd_A0):
    """Operating-point features read from the measured FD library only."""
    i = int(np.argmin(np.abs(fd_A0 - V)))
    d, A, phi = (np.asarray(x, float) for x in (fd_height[i], fd_amp[i], fd_phase[i]))
    o = np.argsort(d); d, A, phi = d[o], A[o], phi[o]
    m = np.isfinite(d) & np.isfinite(A) & np.isfinite(phi)
    d, A, phi = d[m], A[m], phi[m]
    A0 = float(np.nanmean(A[-10:])); At = s * A0
    c = np.where(np.diff(np.sign(A - At)) != 0)[0]
    if c.size == 0:
        return dict(d_op=np.nan, slope=np.nan, phi_op=np.nan, A0_fd=A0)
    k = c[0]
    dop = d[k] + (At - A[k]) / (A[k + 1] - A[k] + 1e-12) * (d[k + 1] - d[k])
    k2, k1 = min(k + 4, len(d) - 1), max(k - 4, 0)
    slope = abs((A[k2] - A[k1]) / (d[k2] - d[k1] + 1e-12))
    return dict(d_op=float(dop), slope=float(slope),
                phi_op=float(wrap_deg(np.interp(dop, d, phi))), A0_fd=A0)


def qsafety_prior_submitted(V, s, fd_amp, fd_phase, fd_A0):
    """Deterministic force prior exactly as in codes/_qsafety_ap.py (causal)."""
    i = int(np.argmin(np.abs(fd_A0 - V)))
    A = fd_amp[i]; mm = np.isfinite(A); A = A[mm]
    At = s * fd_A0[i]
    c = np.where(np.diff(np.sign(A - At)) != 0)[0]
    if c.size == 0:
        return np.nan
    return float(fd_phase[i][mm][c[0]])


def force_line(A, phi, a0):
    m = np.isfinite(A) & np.isfinite(phi)
    return (a0 - A[m]) / a0 + 0.5 * np.maximum(0.0, np.clip((90.0 - wrap_deg(phi[m])) / 90.0, -1, 1))


# ---------------------------------------------------------------- analysis table
def build_table():
    raw = load_tap300_raw()
    b = np.load(BUNDLE, allow_pickle=False)
    si, di, spi, gi = (b[k].astype(int) for k in ("si", "di", "spi", "gi"))
    N = si.size
    H = raw["traces_height"][si, di, spi, gi]            # (N,2,256)
    A = raw["traces_A"][si, di, spi, gi]
    PHI = raw["traces_phi"][si, di, spi, gi]
    exp_lines = np.stack([[center_line(H[c, k]) for k in (0, 1)] for c in range(N)])
    assert np.allclose(exp_lines, b["traces_exp"], equal_nan=True), "bundle traces != raw grid"

    drive = b["drive"].astype(float); sp = b["setpoint"].astype(float)
    ig = b["igain"].astype(float); speed = b["scan_speed"].astype(float)
    Qa = np.array([q_align(exp_lines[c, 0], exp_lines[c, 1]) for c in range(N)])
    assert np.allclose(Qa, b["q_exp"], equal_nan=True)
    Qs = np.array([np.nanmean([np.nanpercentile(force_line(A[c, k], PHI[c, k], drive[c]), 90)
                               for k in (0, 1)]) for c in range(N)])

    fd_A0 = np.nanmean(raw["fd_amp"][:, -10:], axis=1)
    feats = [fd_op_features(drive[c], sp[c], raw["fd_height"], raw["fd_amp"],
                            raw["fd_phase"], fd_A0) for c in range(N)]
    d_op = np.array([f["d_op"] for f in feats]); slope = np.array([f["slope"] for f in feats])
    phi_op = np.array([f["phi_op"] for f in feats])
    phi_sub = np.array([qsafety_prior_submitted(drive[c], sp[c], raw["fd_amp"],
                                                raw["fd_phase"], fd_A0) for c in range(N)])
    phi_sub = np.where(np.isfinite(phi_sub), phi_sub, np.nanmedian(phi_sub))
    Qs_prior = (1.0 - sp) + 0.5 * np.maximum(0.0, (90.0 - wrap_deg(phi_sub)) / 90.0)

    is_test = np.zeros(N, bool); is_test[b["test_idx"]] = True
    return dict(raw=raw, N=N, si=si, di=di, spi=spi, gi=gi, drive=drive, setpoint=sp,
                igain=ig, speed=speed, exp_lines=exp_lines, A_lines=A, PHI_lines=PHI,
                Q_align=Qa, Q_safety=Qs, Qs_prior=Qs_prior, d_op=d_op, slope=slope,
                phi_op=phi_op, is_test_submitted=is_test, group=si * 11 + di,
                gp_train_idx=b["gp_train_idx"])


def feature_matrix(T, which):
    """Pre-acquisition feature blocks (all available before scanning c)."""
    ctrl = np.c_[np.log10(T["speed"]), T["drive"], T["setpoint"], np.log10(T["igain"])]
    if which == "controls":
        return ctrl
    slope = T["slope"]
    eng = np.isfinite(slope).astype(float)
    slope_f = np.where(np.isfinite(slope), slope, np.nanmedian(slope))
    dop = np.where(np.isfinite(T["d_op"]), T["d_op"], np.nanmedian(T["d_op"]))
    phi = np.where(np.isfinite(T["phi_op"]), T["phi_op"], np.nanmedian(T["phi_op"]))
    fd = np.c_[np.log10(1.0 / np.clip(slope_f, 1e-4, None)), dop, phi, eng]
    if which == "controls+fd":
        return np.c_[ctrl, fd]
    raise KeyError(which)


# ---------------------------------------------------------------- physics prior
class PhysicsPrior:
    """Deterministic scanner whose every calibration input respects `allowed`."""

    def __init__(self, T):
        self.T = T
        self.raw = T["raw"]
        self.scanner = build_tap300_scanner(self.raw)
        self.fd_tables = {}
        p = load(CACHE_DIR / f"physics_guided_PI_grid_{CACHE_TAG}.joblib")
        self.local = p["gp_fit"]["train_local"]          # 80 per-condition PI fits
        self.gp_cfg = p["gp_fit"]["cfg"]

    def _fd_table(self, di):
        if di not in self.fd_tables:
            self.fd_tables[di] = self.scanner.prepare_fd_table_for_drive(
                float(self.raw["drive_exp"][di]), n_d=4096)
        return self.fd_tables[di]

    def _gp(self):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        k = (ConstantKernel(1.0, (1e-3, 1e3)) *
             Matern(length_scale=np.ones(4), length_scale_bounds=(1e-2, 1e2), nu=2.5) +
             WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-8, 1e0)))
        gp = GaussianProcessRegressor(kernel=k, alpha=self.gp_cfg["gp_alpha"],
                                      normalize_y=self.gp_cfg["normalize_y"],
                                      n_restarts_optimizer=self.gp_cfg["gp_n_restarts_optimizer"],
                                      random_state=self.gp_cfg["seed"])
        return Pipeline([("scaler", StandardScaler()), ("gp", gp)])

    def _x(self, conds):
        r = self.raw
        return np.array([[np.log10(r["scan_rate"][a]), r["drive_exp"][b], r["setpoint_exp"][c],
                          np.log10(r["igain_exp"][d])] for a, b, c, d in conds], float)

    def run(self, allowed, return_lines=False):
        """allowed: bool array (5,11,8,3) over the full measured grid."""
        r, T = self.raw, self.T
        use = [x for x in self.local if allowed[tuple(int(v) for v in x["cond"])]]
        X = self._x([tuple(int(v) for v in x["cond"]) for x in use])
        yP = np.array([x["log10_P"] for x in use]); yI = np.array([x["log10_I"] for x in use])
        gpP, gpI = self._gp(), self._gp()
        gpP.fit(X, yP); gpI.fit(X, yI)
        conds = list(zip(T["si"], T["di"], T["spi"], T["gi"]))
        Xc = self._x(conds)
        logP, logI = gpP.predict(Xc), gpI.predict(Xc)

        H = r["traces_height"]
        rms = [trace_rms(H[a, b_, c, d, k]) for a, b_, c, d in zip(*np.where(allowed)) for k in (0, 1)]
        rms = np.array([v for v in rms if np.isfinite(v) and v > 0])
        target_rms = float(np.nanmedian(rms))
        h_med = np.nanmedian(H[allowed][:, 0, :], axis=0)
        h_ref = rms_match(h_med, target_rms)

        Qsim = np.full(T["N"], np.nan); lines = np.full((T["N"], 2, H.shape[-1]), np.nan)
        for c, (a, b_, cc, d) in enumerate(conds):
            out = simulate(self.scanner, self._fd_table(b_), h_ref, r["drive_exp"][b_],
                           r["setpoint_exp"][cc], r["scan_rate"][a], 10 ** logP[c], 10 ** logI[c])
            tr, rt = center_line(out["trace"]["d_hat"]), center_line(out["retrace"]["d_hat"])
            lines[c] = (tr, rt)
            Qsim[c] = q_align(tr, rt)
        res = dict(Q_sim=Qsim, logP=logP, logI=logI, n_local=len(use),
                   target_rms=target_rms, h_ref=h_ref)
        if return_lines:
            res["lines"] = lines
        return res


def allowed_from_heldout(T, heldout_idx, how):
    """Calibration universe on the full 1320-condition grid for one outer fold."""
    raw = T["raw"]
    S, D, P, G = raw["traces_height"].shape[:4]
    allowed = np.ones((S, D, P, G), bool)
    ho = np.asarray(heldout_idx, int)
    if how == "condition":                    # exclude exactly the held-out conditions
        allowed[T["si"][ho], T["di"][ho], T["spi"][ho], T["gi"][ho]] = False
    elif how == "speed_drive":                # exclude whole (speed, drive) blocks
        for a, b_ in set(zip(T["si"][ho], T["di"][ho])):
            allowed[a, b_] = False
    elif how == "speed":
        allowed[np.unique(T["si"][ho])] = False
    elif how == "setpoint":
        allowed[:, :, np.unique(T["spi"][ho])] = False
    else:
        raise KeyError(how)
    return allowed
