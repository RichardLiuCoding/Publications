"""Multi-objective PI fit loss for the calibration-grating v2 pipeline.

Why the v2 loss fails at large I gain (unstable feedback regime):
- The v2 loss is pure pixel MSE between sim and experiment after latency
  alignment.  When the experiment oscillates (high I gain → feedback
  instability), a *quiet* DT output has a lower pixel MSE than an
  oscillating one, even when matching the oscillation amplitude is the
  whole point.  The optimizer therefore picks a small DT I and the
  instability signature is thrown away.

This module redefines the loss as a weighted sum of four behavioural
mismatch statistics so the optimizer must match three distinct regimes:

  1.  shape MSE           — pixel-wise height match (slow tracking)
  2.  trace–retrace RMSE  — controller hysteresis (slow-I signature)
  3.  high-frequency RMS  — oscillation amplitude (large-I signature)
  4.  gradient MAD        — texture roughness (large-I micro-signature)

With weights set so that each term contributes a comparable fraction of
the median informative-condition loss, the fitted (P, I) reproduces:
  * slow / large trace–retrace mismatch when the experiment is slow
  * quiet, well-aligned scan when the experiment is well-tuned
  * oscillatory output when the experiment is unstable
"""
from __future__ import annotations

import numpy as np


def _interior_center(line, trim=10):
    line = np.asarray(line, float).ravel()
    if line.size <= 2*trim+4:
        return line - np.nanmean(line) if line.size else line
    inner = line[trim:-trim]
    return line - np.nanmean(inner)


def _moving_median(line, smooth=11):
    """Centered moving-median smoother (vectorized via stride tricks)."""
    line = np.asarray(line, float).ravel()
    n = line.size
    half = smooth // 2
    if n < smooth:
        return np.full(n, np.nanmedian(line))
    # Reflect-pad so the output has the same length
    pad = np.empty(n + 2*half, float)
    pad[:half] = line[0]; pad[half:half+n] = line; pad[half+n:] = line[-1]
    # Use numpy stride_tricks to build a (n, smooth) view, then take median
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(pad, smooth)
    return np.nanmedian(win, axis=1)


def hf_rms(line, smooth=11, trim=10):
    """High-frequency residual RMS — proxy for oscillation amplitude.

    Subtract a small-window moving median (smooths slow grating shape) and
    take the standard deviation of the residual on the interior.
    """
    line = np.asarray(line, float).ravel()
    if line.size <= 2*trim + smooth + 4:
        return float('nan')
    sm = _moving_median(line, smooth=smooth)
    res = line - sm
    inner = res[trim:-trim]
    inner = inner[np.isfinite(inner)]
    if inner.size < 5: return float('nan')
    return float(np.sqrt(np.nanmean(inner**2)))


def grad_mad(line, trim=10):
    """Robust gradient MAD — texture roughness."""
    line = np.asarray(line, float).ravel()
    if line.size <= 2*trim+4:
        return float('nan')
    inner = line[trim:-trim]
    dy = np.diff(inner[np.isfinite(inner)])
    if dy.size < 4: return float('nan')
    med = np.nanmedian(dy)
    return float(1.4826 * np.nanmedian(np.abs(dy - med)))


def trace_retrace_rmse(tr, rt, trim=10):
    """Trace–retrace alignment RMSE — controller hysteresis."""
    n = min(len(tr), len(rt))
    if n <= 2*trim+4: return float('nan')
    a = tr[trim:n-trim] - np.nanmean(tr[trim:n-trim])
    b = rt[trim:n-trim] - np.nanmean(rt[trim:n-trim])
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 5: return float('nan')
    return float(np.sqrt(np.nanmean((a[m]-b[m])**2)))


# ---------------------------------------------------------------------------
# Default weights — tuned so each component contributes O(1) of the total
# loss at the informative-condition median. Tunable from the caller.
#
# The behavioural terms (trrt / hf / grad) compare statistics in log-1+ space
# so that very large experimental signatures (e.g. 50 nm HF residual under
# unstable feedback, which the DT cannot fully match) do not dominate the
# fit by sheer magnitude.  The fit only needs to put the DT in the right
# *regime*, not exactly match the absolute oscillation amplitude.
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS = dict(
    w_shape   = 1.0,
    w_trrt    = 80.0,
    w_hf      = 300.0,
    w_grad    = 300.0,
)


def behaviour_signature(tr, rt, *, smooth=11, trim=10):
    """Return (trrt, hf_tr, hf_rt, gm_tr, gm_rt) for one (trace, retrace) pair."""
    return {
        'trrt':  trace_retrace_rmse(tr, rt, trim=trim),
        'hf_tr': hf_rms(tr, smooth=smooth, trim=trim),
        'hf_rt': hf_rms(rt, smooth=smooth, trim=trim),
        'gm_tr': grad_mad(tr, trim=trim),
        'gm_rt': grad_mad(rt, trim=trim),
    }


def multi_objective_loss(sim_tr, sim_rt, exp_tr, exp_rt,
                          *, weights=None, trim=10, smooth=11,
                          aligned_pairs=None, exp_sig=None,
                          return_components=False):
    """Multi-objective behavioural loss.

    Parameters
    ----------
    sim_tr, sim_rt, exp_tr, exp_rt : 1-D arrays, same length conceptually
    weights : dict of w_shape / w_trrt / w_hf / w_grad (overrides defaults)
    trim    : pixels excluded at each end before stats are computed
    smooth  : moving-median window for HF separation
    aligned_pairs : optional ((sim_tr_a, exp_tr_a), (sim_rt_a, exp_rt_a))
                    already produced by `diff_shifted`; if None, alignment
                    happens inside.
    return_components : if True, also returns dict with each term value
    """
    w = dict(DEFAULT_WEIGHTS); w.update(weights or {})

    # Latency-aligned arrays for the shape MSE
    if aligned_pairs is None:
        from codes.dt_gp_static_calibration_v3 import diff_shifted
        sim_tr_a, exp_tr_a = diff_shifted(sim_tr, exp_tr)
        sim_rt_a, exp_rt_a = diff_shifted(sim_rt, exp_rt)
    else:
        (sim_tr_a, exp_tr_a), (sim_rt_a, exp_rt_a) = aligned_pairs

    def _shape(a, b):
        n = min(len(a), len(b))
        if n <= 2*trim+4: return float('nan')
        ac = a[trim:n-trim] - np.nanmean(a[trim:n-trim])
        bc = b[trim:n-trim] - np.nanmean(b[trim:n-trim])
        m = np.isfinite(ac) & np.isfinite(bc)
        if m.sum() < 5: return float('nan')
        return float(np.nanmean((ac[m]-bc[m])**2))

    shape_mse = _shape(sim_tr_a, exp_tr_a) + _shape(sim_rt_a, exp_rt_a)

    sim_sig = behaviour_signature(sim_tr, sim_rt, smooth=smooth, trim=trim)
    if exp_sig is None:
        exp_sig = behaviour_signature(exp_tr, exp_rt, smooth=smooth, trim=trim)

    def _sqdiff_log(a, b):
        """Squared difference in log(1+x) space — relative-magnitude sensitive."""
        if not (np.isfinite(a) and np.isfinite(b)): return 0.0
        return float((np.log1p(max(a, 0)) - np.log1p(max(b, 0)))**2)

    trrt_term = _sqdiff_log(sim_sig['trrt'], exp_sig['trrt'])
    hf_term   = 0.5*(_sqdiff_log(sim_sig['hf_tr'], exp_sig['hf_tr'])
                     + _sqdiff_log(sim_sig['hf_rt'], exp_sig['hf_rt']))
    gm_term   = 0.5*(_sqdiff_log(sim_sig['gm_tr'], exp_sig['gm_tr'])
                     + _sqdiff_log(sim_sig['gm_rt'], exp_sig['gm_rt']))

    total = (w['w_shape'] * (shape_mse if np.isfinite(shape_mse) else 0.0)
             + w['w_trrt'] * trrt_term
             + w['w_hf']   * hf_term
             + w['w_grad'] * gm_term)

    if return_components:
        return total, dict(shape_mse=shape_mse, trrt=trrt_term,
                            hf=hf_term, grad=gm_term,
                            sim_sig=sim_sig, exp_sig=exp_sig, weights=w)
    return total
