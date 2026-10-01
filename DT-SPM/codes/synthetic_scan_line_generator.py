"""
synthetic_scan_line_generator.py
================================

Standalone utilities to generate synthetic SPM scan lines whose height-change-rate
distribution matches a full height map, then test them with either:

1. a simple toy SPM feedback simulator included here, or
2. your existing ScannerFD object from Scanner_numba_substeps.py.

The purpose is to avoid estimating the exact ground-truth line profile. Instead,
you generate statistically matched scan excitations and compare simulated scan
statistics with experimental scan statistics.

Author: ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Literal, Any
import numpy as np
import matplotlib.pyplot as plt

try:
    from scipy.ndimage import gaussian_filter1d
    from scipy.stats import wasserstein_distance
except Exception as exc:
    raise ImportError(
        "This script requires scipy. Install with: pip install scipy"
    ) from exc


# =============================================================================
# Robust utilities
# =============================================================================

def robust_mad(x: np.ndarray, eps: float = 1e-12) -> float:
    """Median absolute deviation scaled to Gaussian sigma."""
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return eps
    med = np.nanmedian(x)
    return float(1.4826 * np.nanmedian(np.abs(x - med)) + eps)


def finite_flatten(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    return x[np.isfinite(x)]


def detrend_line_linear(h: np.ndarray) -> np.ndarray:
    """Remove a linear trend from a 1D line."""
    h = np.asarray(h, dtype=float).ravel()
    n = h.size
    x = np.arange(n, dtype=float)
    mask = np.isfinite(h)
    if np.sum(mask) < 3:
        return h - np.nanmedian(h)

    p = np.polyfit(x[mask], h[mask], deg=1)
    return h - np.polyval(p, x)


def match_robust_roughness(h: np.ndarray, target_mad: float) -> np.ndarray:
    """Rescale a line so its robust roughness matches target_mad."""
    h = np.asarray(h, dtype=float).ravel()
    h = h - np.nanmedian(h)
    s = robust_mad(h)
    return h * (float(target_mad) / max(s, 1e-12))


def _safe_quantile_trim(x: np.ndarray, q: Optional[float]) -> np.ndarray:
    x = finite_flatten(x)
    if q is None or q <= 0:
        return x
    q = float(q)
    lo, hi = np.quantile(x, [q, 1.0 - q])
    return x[(x >= lo) & (x <= hi)]


# =============================================================================
# Rate distribution extraction
# =============================================================================

@dataclass
class RateDistribution:
    """
    Empirical distribution of local height slopes and scan-rate-scaled slopes.

    slope_pool:
        Samples of dh/dx from the map.

    rate_pool:
        Samples of scan_speed_hat_ref * dh/dx.

    The same slope distribution can be reused for different scan speeds.
    """
    slope_pool: np.ndarray
    rate_pool: np.ndarray
    dx_hat: float
    scan_speed_hat_ref: float
    direction: str
    map_roughness_mad: float
    map_height_range: Tuple[float, float]
    slope_mad: float
    rate_mad: float


def extract_rate_distribution_from_map(
    h_map: np.ndarray,
    *,
    dx_hat: float = 1.0,
    scan_speed_hat_ref: float = 1.0,
    direction: Literal["x", "y", "both"] = "x",
    remove_row_offsets: bool = True,
    remove_col_offsets: bool = False,
    trim_quantile: Optional[float] = 0.001,
) -> RateDistribution:
    """
    Extract empirical dh/dx and scan_speed * dh/dx distributions from a full map.

    Parameters
    ----------
    h_map:
        2D height map, shape (ny, nx).
    dx_hat:
        Pixel size in scanner-normalized length units.
    scan_speed_hat_ref:
        Reference scan speed used to define rate_pool.
    direction:
        "x" uses horizontal scan direction.
        "y" uses vertical scan direction.
        "both" combines both.
    remove_row_offsets:
        Remove median row offset before extracting statistics.
    remove_col_offsets:
        Remove median column offset before extracting statistics.
    trim_quantile:
        Optional tail trimming to suppress spikes. Use None to disable.

    Returns
    -------
    RateDistribution
    """
    h = np.asarray(h_map, dtype=float)
    if h.ndim != 2:
        raise ValueError("h_map must be 2D.")

    h_clean = h.copy()

    if remove_row_offsets:
        h_clean = h_clean - np.nanmedian(h_clean, axis=1, keepdims=True)

    if remove_col_offsets:
        h_clean = h_clean - np.nanmedian(h_clean, axis=0, keepdims=True)

    slope_chunks = []

    if direction in ("x", "both"):
        slope_chunks.append(np.diff(h_clean, axis=1).ravel() / float(dx_hat))

    if direction in ("y", "both"):
        slope_chunks.append(np.diff(h_clean, axis=0).ravel() / float(dx_hat))

    if len(slope_chunks) == 0:
        raise ValueError("direction must be 'x', 'y', or 'both'.")

    slope_pool = np.concatenate(slope_chunks)
    slope_pool = _safe_quantile_trim(slope_pool, trim_quantile)

    if slope_pool.size < 10:
        raise ValueError("Too few finite slope samples extracted from map.")

    rate_pool = float(scan_speed_hat_ref) * slope_pool

    return RateDistribution(
        slope_pool=slope_pool,
        rate_pool=rate_pool,
        dx_hat=float(dx_hat),
        scan_speed_hat_ref=float(scan_speed_hat_ref),
        direction=str(direction),
        map_roughness_mad=robust_mad(h_clean),
        map_height_range=(float(np.nanmin(h_clean)), float(np.nanmax(h_clean))),
        slope_mad=robust_mad(slope_pool),
        rate_mad=robust_mad(rate_pool),
    )


# =============================================================================
# Synthetic height line generation
# =============================================================================

def generate_line_filtered_iid_rate(
    rate_dist: RateDistribution,
    *,
    n_pixels: int,
    scan_speed_hat_target: float,
    dx_hat_target: Optional[float] = None,
    corr_sigma_px: float = 2.0,
    target_roughness_mad: Optional[float] = None,
    remove_net_slope: bool = True,
    h0: float = 0.0,
    random_state: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Generate a synthetic line by sampling the empirical slope distribution,
    smoothing it to impose finite correlation length, and integrating.

    This is usually the best default generator.
    """
    rng = np.random.default_rng(random_state)

    if dx_hat_target is None:
        dx_hat_target = rate_dist.dx_hat

    n_pixels = int(n_pixels)
    if n_pixels < 2:
        raise ValueError("n_pixels must be >= 2.")

    # Sample slope directly. This keeps the physical topographic difficulty fixed.
    slope = rng.choice(rate_dist.slope_pool, size=n_pixels - 1, replace=True)

    if corr_sigma_px is not None and corr_sigma_px > 0:
        slope = gaussian_filter1d(
            slope,
            sigma=float(corr_sigma_px),
            mode="reflect",
        )

    # Re-center and re-match robust slope scale after smoothing.
    slope = slope - np.nanmedian(slope)
    slope = slope * (rate_dist.slope_mad / max(robust_mad(slope), 1e-12))

    if remove_net_slope:
        slope = slope - np.nanmean(slope)

    dh = slope * float(dx_hat_target)

    h = np.empty(n_pixels, dtype=float)
    h[0] = float(h0)
    h[1:] = h[0] + np.cumsum(dh)

    h = detrend_line_linear(h)

    if target_roughness_mad is None:
        target_roughness_mad = rate_dist.map_roughness_mad

    h = match_robust_roughness(h, float(target_roughness_mad))

    # Recompute after final detrend/roughness normalization.
    slope_final = np.diff(h) / float(dx_hat_target)
    rate_final = float(scan_speed_hat_target) * slope_final

    return {
        "h_hat": h,
        "slope": slope_final,
        "rate": rate_final,
        "dh": np.diff(h),
        "mode": np.array(["filtered_iid"], dtype=object),
    }


def generate_line_block_bootstrap_from_map(
    h_map: np.ndarray,
    *,
    n_pixels: int,
    dx_hat: float = 1.0,
    scan_speed_hat_target: float = 1.0,
    block_len: int = 32,
    direction: Literal["x", "y"] = "x",
    target_roughness_mad: Optional[float] = None,
    random_state: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Generate synthetic line by sampling real contiguous slope blocks from map rows
    or columns. This preserves local spatial correlation better than IID sampling.
    """
    rng = np.random.default_rng(random_state)

    h = np.asarray(h_map, dtype=float)
    if h.ndim != 2:
        raise ValueError("h_map must be 2D.")

    if direction == "x":
        slope_map = np.diff(h, axis=1) / float(dx_hat)
        n_rows, n_slopes = slope_map.shape
    elif direction == "y":
        slope_map = np.diff(h, axis=0) / float(dx_hat)
        n_slopes, n_rows = slope_map.shape
    else:
        raise ValueError("direction must be 'x' or 'y'.")

    needed = int(n_pixels) - 1
    blocks = []

    while sum(len(b) for b in blocks) < needed:
        if direction == "x":
            row = rng.integers(0, slope_map.shape[0])
            max_start = max(1, slope_map.shape[1] - int(block_len))
            start = rng.integers(0, max_start)
            block = slope_map[row, start:start + int(block_len)]
        else:
            col = rng.integers(0, slope_map.shape[1])
            max_start = max(1, slope_map.shape[0] - int(block_len))
            start = rng.integers(0, max_start)
            block = slope_map[start:start + int(block_len), col]

        block = block[np.isfinite(block)]
        if block.size > 0:
            blocks.append(block)

    slope = np.concatenate(blocks)[:needed]
    slope = slope - np.nanmean(slope)

    dh = slope * float(dx_hat)

    h_line = np.empty(int(n_pixels), dtype=float)
    h_line[0] = 0.0
    h_line[1:] = np.cumsum(dh)

    h_line = detrend_line_linear(h_line)

    if target_roughness_mad is None:
        target_roughness_mad = robust_mad(h - np.nanmedian(h))

    h_line = match_robust_roughness(h_line, float(target_roughness_mad))

    slope_final = np.diff(h_line) / float(dx_hat)
    rate_final = float(scan_speed_hat_target) * slope_final

    return {
        "h_hat": h_line,
        "slope": slope_final,
        "rate": rate_final,
        "dh": np.diff(h_line),
        "mode": np.array(["block_bootstrap"], dtype=object),
    }


def generate_synthetic_scan_line(
    h_map: np.ndarray,
    *,
    n_pixels: int = 256,
    dx_hat: float = 1.0,
    scan_speed_hat: float = 1e3,
    mode: Literal["filtered_iid", "block"] = "filtered_iid",
    direction: Literal["x", "y", "both"] = "x",
    corr_sigma_px: float = 2.0,
    block_len: int = 32,
    random_state: Optional[int] = 0,
) -> Dict[str, Any]:
    """
    One-shot convenience wrapper.

    Returns
    -------
    dict with:
        rate_dist
        generated
        comparison
    """
    rate_dist = extract_rate_distribution_from_map(
        h_map,
        dx_hat=dx_hat,
        scan_speed_hat_ref=1.0,
        direction=direction,
    )

    if mode == "filtered_iid":
        gen = generate_line_filtered_iid_rate(
            rate_dist,
            n_pixels=n_pixels,
            scan_speed_hat_target=scan_speed_hat,
            dx_hat_target=dx_hat,
            corr_sigma_px=corr_sigma_px,
            random_state=random_state,
        )
    elif mode == "block":
        block_direction = "x" if direction == "both" else direction
        gen = generate_line_block_bootstrap_from_map(
            h_map,
            n_pixels=n_pixels,
            dx_hat=dx_hat,
            scan_speed_hat_target=scan_speed_hat,
            block_len=block_len,
            direction=block_direction,
            target_roughness_mad=rate_dist.map_roughness_mad,
            random_state=random_state,
        )
    else:
        raise ValueError("mode must be 'filtered_iid' or 'block'.")

    comp = compare_rate_distribution(
        rate_dist,
        gen["h_hat"],
        dx_hat=dx_hat,
        scan_speed_hat=scan_speed_hat,
    )

    return {
        "rate_dist": rate_dist,
        "generated": gen,
        "comparison": comp,
    }


# =============================================================================
# Diagnostics and plotting
# =============================================================================

def compare_rate_distribution(
    rate_dist: RateDistribution,
    h_line: np.ndarray,
    *,
    dx_hat: float,
    scan_speed_hat: float,
) -> Dict[str, float]:
    """
    Compare generated line's rate distribution with the target map distribution.
    """
    h_line = np.asarray(h_line, dtype=float).ravel()

    slope_line = np.diff(h_line) / float(dx_hat)
    rate_line = float(scan_speed_hat) * slope_line
    rate_target = float(scan_speed_hat) * rate_dist.slope_pool

    a = finite_flatten(rate_target)
    b = finite_flatten(rate_line)

    scale = robust_mad(np.r_[a, b])

    return {
        "rate_target_mad": robust_mad(a),
        "rate_line_mad": robust_mad(b),
        "rate_target_p01": float(np.quantile(a, 0.01)),
        "rate_line_p01": float(np.quantile(b, 0.01)),
        "rate_target_p50": float(np.quantile(a, 0.50)),
        "rate_line_p50": float(np.quantile(b, 0.50)),
        "rate_target_p99": float(np.quantile(a, 0.99)),
        "rate_line_p99": float(np.quantile(b, 0.99)),
        "wasserstein_rate_scaled": float(wasserstein_distance(a / scale, b / scale)),
    }


def plot_generated_line_and_rate(
    h_map: np.ndarray,
    h_line: np.ndarray,
    rate_dist: RateDistribution,
    *,
    dx_hat: float = 1.0,
    scan_speed_hat: float = 1.0,
    bins: int = 80,
    title: str = "Synthetic scan line",
):
    """
    Plot:
        1. original map
        2. generated height line
        3. rate-distribution comparison
    """
    h_map = np.asarray(h_map, dtype=float)
    h_line = np.asarray(h_line, dtype=float).ravel()

    rate_target = float(scan_speed_hat) * rate_dist.slope_pool
    rate_line = float(scan_speed_hat) * np.diff(h_line) / float(dx_hat)

    fig = plt.figure(figsize=(12, 7))

    ax1 = fig.add_subplot(2, 2, 1)
    im = ax1.imshow(h_map, origin="lower", aspect="auto")
    ax1.set_title("Input height map")
    ax1.set_xlabel("x pixel")
    ax1.set_ylabel("y pixel")
    plt.colorbar(im, ax=ax1, fraction=0.046)

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(h_line, lw=1.5)
    ax2.set_title("Generated synthetic height line")
    ax2.set_xlabel("x pixel")
    ax2.set_ylabel("height")

    ax3 = fig.add_subplot(2, 2, 3)
    ax3.hist(rate_target, bins=bins, density=True, alpha=0.5, label="map target")
    ax3.hist(rate_line, bins=bins, density=True, alpha=0.5, label="synthetic line")
    ax3.set_title("Height-change-rate distribution")
    ax3.set_xlabel("scan_speed × dh/dx")
    ax3.set_ylabel("density")
    ax3.legend()

    ax4 = fig.add_subplot(2, 2, 4)
    q = np.linspace(0.001, 0.999, 300)
    ax4.plot(
        np.quantile(rate_target, q),
        np.quantile(rate_line, q),
        ".",
        ms=3,
    )
    lo = min(np.quantile(rate_target, 0.001), np.quantile(rate_line, 0.001))
    hi = max(np.quantile(rate_target, 0.999), np.quantile(rate_line, 0.999))
    ax4.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax4.set_title("Q-Q check")
    ax4.set_xlabel("target map rate quantile")
    ax4.set_ylabel("synthetic line rate quantile")

    fig.suptitle(title)
    fig.tight_layout()
    return fig


# =============================================================================
# Toy SPM feedback simulator
# =============================================================================

def _lpf1_step(y: float, x: float, dt: float, tau: Optional[float]) -> float:
    if tau is None or tau <= 0:
        return float(x)
    alpha = float(dt) / (float(tau) + float(dt))
    return float(y + alpha * (x - y))


def toy_fd_response(
    d_eff: np.ndarray | float,
    *,
    A0: float = 50.0,
    d0: float = 30.0,
    width: float = 5.0,
    phi_far: float = 120.0,
    phi_contact_shift: float = -45.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    A simple monotonic toy FD relation for testing only.

    A decreases as effective distance d_eff approaches contact.
    Phase shifts in the same transition region.
    """
    d = np.asarray(d_eff, dtype=float)

    # sigmoid transition: far field -> A0; near contact -> small A
    s = 1.0 / (1.0 + np.exp(-(d - d0) / max(width, 1e-9)))
    A = A0 * (0.08 + 0.92 * s)
    phi = phi_far + phi_contact_shift * (1.0 - s)

    return A, phi


def toy_scan_line_pi(
    h_hat: np.ndarray,
    *,
    drive_nm: float = 50.0,
    setpoint: float = 0.6,
    scan_speed_hat: float = 1e3,
    dx_hat: float = 1.0,
    P: float = 0.0,
    I: float = 10.0,
    tau_A: Optional[float] = 5e-4,
    tau_phi: Optional[float] = 2e-3,
    tau_z: Optional[float] = 1e-4,
    d_init_hat: float = 60.0,
    phi_meas_init_deg: float = 120.0,
    T_I: Optional[float] = 3e-3,
    z_rate_limit_hat: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """
    Minimal toy PI scan simulator.

    This is not a replacement for your calibrated ScannerFD. It is only included
    so this standalone script can be tested without external dependencies.
    """
    h = np.asarray(h_hat, dtype=float).ravel()
    n = h.size
    dt = float(dx_hat) / float(scan_speed_hat)

    # For toy model, free amplitude scales with drive.
    A0 = float(drive_nm)
    A_set = float(setpoint) * A0

    d_cmd = float(d_init_hat)
    d_act = float(d_init_hat)
    A_meas = A0
    phi_meas = float(phi_meas_init_deg)
    integ = 0.0

    if T_I is not None and T_I > 0:
        leak = np.exp(-dt / float(T_I))
    else:
        leak = None

    out = {
        "d_hat": np.empty(n),
        "d_eff_hat": np.empty(n),
        "A_hat": np.empty(n),
        "A_true_hat": np.empty(n),
        "phi_deg": np.empty(n),
        "phi_true_deg": np.empty(n),
        "err": np.empty(n),
    }

    for i in range(n):
        d_eff = d_act - h[i]
        A_true, phi_true = toy_fd_response(d_eff, A0=A0)

        A_meas = _lpf1_step(A_meas, float(A_true), dt, tau_A)
        phi_meas = _lpf1_step(phi_meas, float(phi_true), dt, tau_phi)

        err = A_set - A_meas

        if leak is None:
            integ = integ + err * dt
        else:
            integ = leak * integ + err * dt

        dd_cmd = (P * err + I * integ) * dt

        if z_rate_limit_hat is not None:
            dd_max = float(z_rate_limit_hat) * dt
            dd_cmd = float(np.clip(dd_cmd, -dd_max, dd_max))

        d_cmd = d_cmd + dd_cmd
        d_act = _lpf1_step(d_act, d_cmd, dt, tau_z)

        out["d_hat"][i] = d_act
        out["d_eff_hat"][i] = d_eff
        out["A_hat"][i] = A_meas
        out["A_true_hat"][i] = float(A_true)
        out["phi_deg"][i] = phi_meas
        out["phi_true_deg"][i] = float(phi_true)
        out["err"][i] = err

    return out


def toy_trace_retrace_scan(
    h_hat: np.ndarray,
    **kwargs,
) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Toy trace/retrace wrapper.

    Retrace is simulated on reversed h and flipped back to forward x-order.
    """
    h = np.asarray(h_hat, dtype=float).ravel()

    trace = toy_scan_line_pi(h, **kwargs)

    retrace_raw = toy_scan_line_pi(
        h[::-1],
        # use same initial state for simplicity in this toy version
        **kwargs,
    )

    retrace = {}
    for k, v in retrace_raw.items():
        if isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == len(h):
            retrace[k] = v[::-1].copy()
        else:
            retrace[k] = v

    return {
        "trace": trace,
        "retrace": retrace,
        "raw_retrace": retrace_raw,
    }


def plot_simulated_scan(out: Dict[str, Dict[str, np.ndarray]], title: str = "Simulated scan"):
    """Plot trace/retrace height, amplitude, phase, and amplitude error."""
    tr = out["trace"]
    rt = out["retrace"]

    fig, axes = plt.subplots(4, 1, figsize=(9, 8), sharex=True)

    axes[0].plot(tr["d_hat"], label="trace")
    axes[0].plot(rt["d_hat"], label="retrace")
    axes[0].set_ylabel("z / d_hat")
    axes[0].legend()

    axes[1].plot(tr["A_hat"], label="trace")
    axes[1].plot(rt["A_hat"], label="retrace")
    axes[1].set_ylabel("A_meas")

    axes[2].plot(tr["phi_deg"], label="trace")
    axes[2].plot(rt["phi_deg"], label="retrace")
    axes[2].set_ylabel("phase")

    axes[3].plot(tr["err"], label="trace")
    axes[3].plot(rt["err"], label="retrace")
    axes[3].set_ylabel("A_set - A")
    axes[3].set_xlabel("pixel")

    fig.suptitle(title)
    fig.tight_layout()
    return fig


# =============================================================================
# Adapter for your existing ScannerFD object
# =============================================================================

def simulate_with_existing_scanner(
    scanner: Any,
    h_line: np.ndarray,
    *,
    drive_nm: float,
    setpoint: float,
    scan_speed_hat: float,
    dx_hat: float = 1.0,
    P: float = 0.0,
    I: float = 10.0,
    tau_A: Optional[float] = None,
    tau_phi: Optional[float] = None,
    tau_z: Optional[float] = None,
    z_rate_limit_hat: Optional[float] = 1e6,
    d_init_hat: float = 250.0,
    phi_meas_init_deg: float = 120.0,
    T_I: Optional[float] = 3e-3,
    integ_clip: Optional[float] = None,
    use_fast: bool = True,
    n_substeps: int = 50,
    fd_table: Optional[Any] = None,
    fd_n_d: int = 4096,
) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Run generated h_line through your existing ScannerFD object.

    It first tries scanner.simulate_trace_retrace_substeps_fast if available.
    Otherwise it uses scanner.scan_line_trace_retrace_pi_drive.
    """
    h_line = np.asarray(h_line, dtype=float).ravel()

    A_filter_order = 1 if tau_A is not None and tau_A > 0 else None
    phi_filter_order = 1 if tau_phi is not None and tau_phi > 0 else None
    z_filter_order = 1 if tau_z is not None and tau_z > 0 else None

    if (
        fd_table is None
        and hasattr(scanner, "prepare_fd_table_for_drive")
        and use_fast
    ):
        fd_table = scanner.prepare_fd_table_for_drive(
            drive_nm=drive_nm,
            n_d=fd_n_d,
        )

    if use_fast and hasattr(scanner, "simulate_trace_retrace_substeps_fast"):
        return scanner.simulate_trace_retrace_substeps_fast(
            h_line,
            drive_nm=drive_nm,
            setpoint=setpoint,
            scan_speed_hat=scan_speed_hat,
            dx_hat=dx_hat,
            P=P,
            I=I,
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
            record_mode="last",
            fd_table=fd_table,
            fd_n_d=fd_n_d,
        )

    return scanner.scan_line_trace_retrace_pi_drive(
        h_hat=h_line,
        drive_nm=drive_nm,
        setpoint=setpoint,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        P=P,
        I=I,
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
        use_substeps=True,
        n_substeps=n_substeps,
    )


# =============================================================================
# Demo map generator
# =============================================================================

def make_demo_height_map(
    ny: int = 128,
    nx: int = 256,
    *,
    roughness: float = 10.0,
    corr_sigma_px: float = 4.0,
    step_height: float = 25.0,
    random_state: int = 0,
) -> np.ndarray:
    """
    Make a synthetic test map with correlated roughness and a few step edges.
    """
    rng = np.random.default_rng(random_state)

    h = rng.normal(size=(ny, nx))

    # Smooth along both axes using scipy through gaussian_filter1d.
    h = gaussian_filter1d(h, sigma=corr_sigma_px, axis=0, mode="reflect")
    h = gaussian_filter1d(h, sigma=corr_sigma_px, axis=1, mode="reflect")

    h = h - np.nanmedian(h)
    h = h * (roughness / max(robust_mad(h), 1e-12))

    # Add terraces/steps.
    for _ in range(5):
        x0 = rng.integers(nx // 8, 7 * nx // 8)
        amp = rng.choice([-1.0, 1.0]) * step_height * rng.uniform(0.3, 1.0)
        h[:, x0:] += amp

    # Remove global median.
    h = h - np.nanmedian(h)
    return h


# =============================================================================
# Main demo
# =============================================================================

if __name__ == "__main__":
    # -------------------------------------------------------------------------
    # 1. Build or load a full height map.
    # Replace this with your measured full map:
    #
    #     h_map = your_height_map
    #
    # Units can be nm or scanner-normalized units, as long as dx_hat and scanner
    # parameters are consistent.
    # -------------------------------------------------------------------------
    h_map = make_demo_height_map(
        ny=128,
        nx=256,
        roughness=8.0,
        corr_sigma_px=4.0,
        step_height=20.0,
        random_state=1,
    )

    dx_hat = 1.0
    scan_speed_hat = 1e3

    # -------------------------------------------------------------------------
    # 2. Generate a synthetic scan line with matched height-change-rate stats.
    # -------------------------------------------------------------------------
    pack = generate_synthetic_scan_line(
        h_map,
        n_pixels=256,
        dx_hat=dx_hat,
        scan_speed_hat=scan_speed_hat,
        mode="filtered_iid",      # "filtered_iid" or "block"
        direction="x",
        corr_sigma_px=2.0,
        random_state=2,
    )

    rate_dist = pack["rate_dist"]
    gen = pack["generated"]

    print("\nRate-distribution comparison:")
    for k, v in pack["comparison"].items():
        print(f"  {k:24s}: {v:.6g}")

    fig1 = plot_generated_line_and_rate(
        h_map,
        gen["h_hat"],
        rate_dist,
        dx_hat=dx_hat,
        scan_speed_hat=scan_speed_hat,
        title="Synthetic line matched to full-map height-change-rate distribution",
    )

    # -------------------------------------------------------------------------
    # 3. Run a toy scanner simulation.
    # Replace this with simulate_with_existing_scanner(scanner, ...) when ready.
    # -------------------------------------------------------------------------
    toy_out = toy_trace_retrace_scan(
        gen["h_hat"],
        drive_nm=50.0,
        setpoint=0.6,
        scan_speed_hat=scan_speed_hat,
        dx_hat=dx_hat,
        P=0.0,
        I=80.0,
        tau_A=5e-4,
        tau_phi=2e-3,
        tau_z=1e-4,
        d_init_hat=60.0,
        phi_meas_init_deg=120.0,
        T_I=3e-3,
        z_rate_limit_hat=1e6,
    )

    fig2 = plot_simulated_scan(
        toy_out,
        title="Toy simulated trace/retrace scan on generated line",
    )

    plt.show()

    # -------------------------------------------------------------------------
    # 4. To use your real ScannerFD object, do something like:
    #
    # real_out = simulate_with_existing_scanner(
    #     scanner,
    #     gen["h_hat"],
    #     drive_nm=40.0,
    #     setpoint=0.6,
    #     scan_speed_hat=1e3,
    #     dx_hat=1.0,
    #     P=0.0,
    #     I=10.0,
    #     tau_A=8e-4,
    #     tau_phi=5e-3,
    #     tau_z=1e-5,
    #     z_rate_limit_hat=1e6,
    #     d_init_hat=250.0,
    #     phi_meas_init_deg=120.0,
    #     T_I=3e-3,
    #     use_fast=True,
    #     n_substeps=50,
    # )
    #
    # plot_simulated_scan(real_out, title="Real ScannerFD simulation")
    # plt.show()
    # -------------------------------------------------------------------------
