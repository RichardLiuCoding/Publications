"""Shared loaders for the 2026-09 causal re-analysis (DD-ART-07-2026-000467).

Everything here mirrors the data preparation of
`Fit DT controller parameters to experimental scans_v2.ipynb` (cells 1, 3, 5, 8)
so that the re-analysis reads exactly the same raw arrays, but it never touches
held-out scans when building a model input.

Inputs (raw):
  data/260507-300kHz-AlScN.npz   grid-scan archive (speed, drive, setpoint, gain, ch, line, px)
  data/Image0002.ibw              separate topography image (AmpInvOLS header only)
  output/Tap300_AlScN.npz          measured FD library (30 curves)
  calibration_cache/dt_controller_fit/physics_guided_PI_grid_balanced_g3_rms.joblib
                                   80 local PI fits (per-condition controller calibration)
  calibration_cache/dt_controller_fit/data_driven_records_balanced_g3_rms.joblib
                                   the 900-condition subset and the submitted DT traces
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
import os
REV = Path(os.environ.get("DTSPM_RUN_DIR", str(ROOT / "runs" / "latest"))).resolve()
REV.mkdir(parents=True, exist_ok=True)
OUT = REV / "output"
FIG = REV / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
(REV / "manuscript").mkdir(parents=True, exist_ok=True)
for _p in (ROOT, ROOT / "codes"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

CACHE_DIR = ROOT / "calibration_cache" / "dt_controller_fit"
CACHE_TAG = "balanced_g3_rms"
N_GAINS_KEEP = 3
RANDOM_SEED = 35


def load_tap300_raw():
    """Return the gain-filtered Tap-300 grid exactly as the submitted notebook built it."""
    import aespm as ae

    fd = np.load(ROOT / "output" / "Tap300_AlScN.npz")
    grid = np.load(ROOT / "data" / "260507-300kHz-AlScN.npz")
    topo = ae.tools.load_ibw(ROOT / "data" / "Image0002.ibw")

    fd_height, fd_amp, fd_phase = fd["height"], fd["amp"], fd["phase"]
    fd_drive_nm = 0.8 * np.nanmean(fd_amp[:, -10:], axis=1)

    raw = grid["data"]
    scan_rate = grid["scan_rate"].astype(float)
    drive_exp = grid["drives"].astype(float) * (258.8 / 2.14) * topo.header["AmpInvOLS"] * 1e9
    setpoint_exp = grid["setpoints"].astype(float)
    igain_exp = grid["i_gain"].astype(float)[:N_GAINS_KEEP]

    ch = 1
    h = raw[:, :, :, :N_GAINS_KEEP, ch, 0:2, :]
    h = (h - np.nanmin(h, axis=-1, keepdims=True)) * 1e9
    A = raw[:, :, :, :N_GAINS_KEEP, ch, 2:4, :] * 1e9
    phi = raw[:, :, :, :N_GAINS_KEEP, ch, 4:6, :]
    h_map = (topo.data[0] - np.nanmin(topo.data[0])) * 1e9
    return dict(fd_height=fd_height, fd_amp=fd_amp, fd_phase=fd_phase,
                fd_drive_nm=fd_drive_nm, scan_rate=scan_rate, drive_exp=drive_exp,
                setpoint_exp=setpoint_exp, igain_exp=igain_exp,
                traces_height=h, traces_A=A, traces_phi=phi, h_map=h_map)


def build_tap300_scanner(raw):
    """FD-prior scanner, identical to notebook cell 8."""
    import importlib
    import codes.Scanner_fixed_extended_fd as sfe
    import codes.Scanner_numba_substeps_v3 as sn
    importlib.reload(sfe); importlib.reload(sn)
    sn.install_numba_substep_methods(sfe.ScannerFD, verbose=False)
    measured_fd = {float(raw["fd_drive_nm"][i]): {"d": raw["fd_height"][i],
                                                  "A": raw["fd_amp"][i],
                                                  "phi": raw["fd_phase"][i]}
                   for i in range(len(raw["fd_drive_nm"]))}
    surface = sfe.FDDriveSurface.from_measured_fd(
        measured_fd, x_mode="d_over_A0", common_range="union", n_x=1024,
        extend_to_zero_amplitude=True, extension_n_fit=5, extension_n_bridge=30,
        extension_phi_mode="linear", extension_F_mode="nearest")
    params = {"k": 25, "A": float(np.nanmedian(raw["fd_amp"])),
              "d0": float(np.nanmax(raw["fd_height"]) * 0.8), "R": 10, "H": 1e-19,
              "E_star": 1e9, "Q": 250}
    return sfe.ScannerFD(params=params, conversions={k: 1.0 for k in params},
                         fd_model=sfe.make_normalized_fd_lookup(surface, conv_L=1.0,
                                                                conv_A=1.0, conv_F=1.0))


SCANNER_CFG = dict(dx_hat=1.0, n_substeps=50, z_rate_limit_hat=1e6, d_init_hat=0.0,
                   A_meas_init_hat=1.0, phi_meas_init_deg=120.0, T_I=0.3,
                   integ_clip=None, antiwindup=True, contact_A_frac=0.02,
                   saturation_A_frac=0.98, record_mode="last",
                   carry_state_to_retrace=True, h_smooth_sigma_px=0.0, fd_n_d=4096)


def simulate(scanner, fd_table, h_line, drive, setpoint, speed, P, I):
    c = SCANNER_CFG
    return scanner.simulate_trace_retrace_substeps_fast(
        h_line, drive_nm=float(drive), setpoint=float(setpoint),
        scan_speed_hat=float(speed), dx_hat=c["dx_hat"], P=float(P), I=float(I),
        A_filter_order=None, tau_A=None, phi_filter_order=None, tau_phi=None,
        z_filter_order=None, tau_z=None, z_rate_limit_hat=c["z_rate_limit_hat"],
        d_init_hat=c["d_init_hat"], A_meas_init_hat=c["A_meas_init_hat"],
        phi_meas_init_deg=c["phi_meas_init_deg"], T_I=c["T_I"],
        integ_clip=c["integ_clip"], n_substeps=c["n_substeps"],
        antiwindup=c["antiwindup"], contact_A_frac=c["contact_A_frac"],
        saturation_A_frac=c["saturation_A_frac"], record_mode=c["record_mode"],
        carry_state_to_retrace=c["carry_state_to_retrace"],
        h_smooth_sigma_px=c["h_smooth_sigma_px"], fd_table=fd_table,
        fd_n_d=c["fd_n_d"])


# ---------------------------------------------------------------- line helpers
def detrend(line):
    line = np.asarray(line, float).ravel()
    x = np.arange(line.size, dtype=float)
    f = np.isfinite(line)
    if f.sum() < 4:
        return line - np.nanmin(line)
    s, b = np.polyfit(x[f], line[f], 1)
    d = line - (s * x + b)
    return d - np.nanmin(d)


def trace_rms(line):
    line = np.asarray(line, float).ravel()
    line = line[np.isfinite(line)]
    if line.size < 4:
        return np.nan
    x = np.arange(line.size, dtype=float)
    s, b = np.polyfit(x, line, 1)
    c = line - (s * x + b)
    c = c - np.nanmean(c)
    return float(np.sqrt(np.nanmean(c ** 2)))


def rms_match(line, target_rms, min_floor_frac=0.05):
    d = detrend(line)
    c = d - np.nanmean(d)
    r = float(np.sqrt(np.nanmean(c ** 2)))
    if not np.isfinite(r) or r < min_floor_frac * target_rms:
        return detrend(line)
    s = c * (target_rms / r)
    return s - np.nanmin(s)


def center_line(y):
    y = np.asarray(y, float).ravel()
    return y - np.nanmedian(y)


def q_align(tr, rt, trim=10):
    """Trace-retrace RMS on centred interior pixels (the manuscript Q_align)."""
    tr = np.asarray(tr, float); rt = np.asarray(rt, float)
    n = min(len(tr), len(rt))
    t = tr[trim:n - trim] - np.nanmean(tr[trim:n - trim])
    r = rt[trim:n - trim] - np.nanmean(rt[trim:n - trim])
    m = np.isfinite(t) & np.isfinite(r)
    if m.sum() < 5:
        return np.nan
    return float(np.sqrt(np.nanmean((t[m] - r[m]) ** 2)))


def line_rmse(pred, exp, trim=10):
    pred = np.asarray(pred, float); exp = np.asarray(exp, float)
    n = min(len(pred), len(exp))
    sc = pred[trim:n - trim] - np.nanmean(pred[trim:n - trim])
    ec = exp[trim:n - trim] - np.nanmean(exp[trim:n - trim])
    m = np.isfinite(sc) & np.isfinite(ec)
    if m.sum() < 5:
        return np.nan
    return float(np.sqrt(np.nanmean((sc[m] - ec[m]) ** 2)))


def file_sha256(path, chunk=1 << 20):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
