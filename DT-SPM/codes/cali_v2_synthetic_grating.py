"""Synthetic calibration-grating ground-truth profile.

The calibration sample is a periodic step grating with 100-nm-high
plateaus.  The v2 notebook's original `h_truth` was the median of the
cleanest experimental traces, which carries instrument/controller
artefacts (rounded plateaus, controller hysteresis, baseline drift).
For a true *ground-truth* DT input we want a clean square-wave grating
with the correct period and 100 nm plateau height, optionally with a
small Gaussian smoothing to model finite tip-radius convolution.

`build_synthetic_grating` is the new generator.  `detect_period_pixels`
estimates the spatial period from an experimentally-derived reference
line via autocorrelation, so the synthetic grating stays phase-aligned
with the experimental scan direction.
"""
from __future__ import annotations

import numpy as np


def detect_period_pixels(line, min_period=8, max_period=128):
    """Estimate spatial period (in pixels) via the largest autocorrelation peak.

    Parameters
    ----------
    line : 1-D array
        Reference height trace from which to read the period.
    min_period, max_period : int
        Search bounds for the period.

    Returns
    -------
    int
        Estimated period.  Falls back to 64 if no peak is found.
    """
    y = np.asarray(line, dtype=float).ravel()
    y = y - np.nanmean(y)
    y[~np.isfinite(y)] = 0.0
    ac = np.correlate(y, y, mode='full')
    ac = ac[ac.size // 2:]
    # find first significant peak after lag 0
    best_lag, best_val = -1, -np.inf
    for i in range(min_period, min(max_period, ac.size - 1)):
        if ac[i] > ac[i-1] and ac[i] > ac[i+1] and ac[i] > best_val:
            best_lag, best_val = i, float(ac[i])
    return int(best_lag) if best_lag > 0 else 64


def detect_phase_pixels(line, period_px):
    """Estimate the rising-edge phase (pixel index of the first low→high
    transition).  Falls back to 0 if no edge is detected."""
    y = np.asarray(line, dtype=float).ravel()
    y = y - np.nanmedian(y)
    rising = np.where(np.diff((y > 0).astype(int)) > 0)[0]
    if rising.size == 0:
        return 0
    return int(rising[0]) % period_px


def build_synthetic_grating(n_pix=256, plateau_height=100.0,
                              period_px=64, duty_cycle=0.5,
                              phase_px=0, edge_smooth_sigma=1.5):
    """Clean square-wave grating with 100 nm plateaus.

    Parameters
    ----------
    n_pix : int
        Output length in pixels.
    plateau_height : float
        Height of the high plateaus (nm).  Low plateaus are at 0.
    period_px : int
        Spatial period in pixels.
    duty_cycle : float in (0, 1)
        Fraction of each period spent at the high plateau.
    phase_px : int
        Pixel index where the first rising edge sits.
    edge_smooth_sigma : float
        Gaussian smoothing sigma (pixels) applied to soften the
        idealized vertical edges — models tip-radius convolution.  Set
        to 0 for a perfectly sharp square wave.

    Returns
    -------
    1-D ndarray of length n_pix, dtype float
    """
    x = np.arange(n_pix, dtype=float)
    phase = ((x - phase_px) % period_px) / period_px
    profile = (phase < duty_cycle).astype(float) * float(plateau_height)
    if edge_smooth_sigma and edge_smooth_sigma > 0:
        # Tiny Gaussian smoothing for tip-radius convolution.
        # Implemented inline to avoid a scipy dependency at call sites that
        # may not have it loaded.
        sigma = float(edge_smooth_sigma)
        half = int(np.ceil(3 * sigma))
        k = np.arange(-half, half + 1)
        kernel = np.exp(-0.5 * (k / sigma) ** 2)
        kernel /= kernel.sum()
        # Reflect-pad
        pad = np.empty(profile.size + 2 * half)
        pad[:half] = profile[0]
        pad[half:half + profile.size] = profile
        pad[half + profile.size:] = profile[-1]
        profile = np.convolve(pad, kernel, mode='valid')
    # Re-baseline so the low plateau sits at 0 exactly
    profile = profile - float(np.nanmin(profile))
    return profile


def build_phase_aligned_grating(reference_line, *, plateau_height=100.0,
                                  duty_cycle=0.5, edge_smooth_sigma=1.5):
    """Convenience helper: detect period and phase from `reference_line`,
    then build the synthetic grating at the same period/phase with
    `plateau_height` and `duty_cycle` enforced.
    """
    n_pix = int(np.asarray(reference_line).size)
    period = detect_period_pixels(reference_line)
    phase  = detect_phase_pixels(reference_line, period)
    return build_synthetic_grating(
        n_pix=n_pix, plateau_height=plateau_height, period_px=period,
        duty_cycle=duty_cycle, phase_px=phase,
        edge_smooth_sigma=edge_smooth_sigma,
    ), {'period_px': period, 'phase_px': phase,
        'duty_cycle': duty_cycle, 'plateau_height': plateau_height}
