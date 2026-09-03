# -*- coding: utf-8 -*-
"""scale_tools.py -- separate the SUPER-domain and NANO-domain scales.

Every angular readout in this campaign so far (`pops`, `ospec`) integrates over
all spatial frequencies. With the previous probe that was harmless: only one
scale was resolved. With a probe that resolves ~45 nm structure inside ~300 nm
bands, an all-frequency angular spectrum MIXES THE TWO, and a change in the
nano-domains would show up as a change in "the director" with no way to tell
which scale moved.

These helpers band-limit first, then ask for the direction.

CONVENTION, taken from the toolkit and not re-invented. `period(S, px, fam)`
masks FFT angles near `fam - 90`, so throughout the campaign an angle names the
DIRECTOR -- the direction the stripes RUN -- and the wavevector is
perpendicular to it:

    Q = (2*pi/Lambda) * n_perp        n_perp _|_ director

Everything here returns director angles, mod 180, to stay compatible with the
pinned triad.
"""
from __future__ import annotations

import numpy as np


def _prep(S):
    a = np.nan_to_num(np.asarray(S, float))
    n = min(a.shape)
    a = a[:n, :n]
    a = a - a.mean()
    w = np.hanning(n)
    return a * w[:, None] * w[None, :], n


def power_map(S, px_nm):
    """Windowed 2-D power spectrum with the q and director-angle grids.

    `ang` is the DIRECTOR angle each FFT pixel reports, i.e. the FFT angle
    rotated by 90 deg, so it can be compared with a triad member directly.
    """
    Z, n = _prep(S)
    P = np.abs(np.fft.fftshift(np.fft.fft2(Z))) ** 2
    yy, xx = np.indices(P.shape)
    dy, dx = yy - n // 2, xx - n // 2
    q_inv_um = np.hypot(dy, dx) / (n * px_nm / 1000.0)      # 1/um
    with np.errstate(divide='ignore'):
        per_nm = np.where(q_inv_um > 0, 1000.0 / np.maximum(q_inv_um, 1e-12),
                          np.inf)
    ang = np.mod(np.rad2deg(np.arctan2(dy, dx)) + 90.0, 180.0)
    # HALF-PLANE MASK. The FFT of a real image is Hermitian: P(k) = P(-k), so
    # every pixel has an identical twin at angle+180 which folds into the SAME
    # angular bin once angles are taken mod 180. In the data the twins reinforce
    # each other; under any permutation they are scattered to different bins.
    # That alone makes the null flatter than the data and returns p ~ 0 for
    # everything, including pure noise -- which is exactly how the first two
    # versions of the significance test failed. Keeping one representative of
    # each pair removes the artefact and changes no profile SHAPE, only counts.
    half = (dy > 0) | ((dy == 0) & (dx >= 0))
    return P, per_nm, ang, q_inv_um, half


MIN_PER_BIN = 12.0        # FFT pixels per angular bin, see _nang
N_PERM = 200              # permutations for the significance test


def _nang(npix):
    """Angular bins, chosen so each holds enough FFT pixels to mean anything.

    THIS IS NOT COSMETIC. The super-domain band (150-500 nm at 4.9 nm/px) is a
    thin low-q annulus holding only ~800 FFT pixels. Split into 180 bins that is
    ~4 per bin, and peak/median then measures BINNING NOISE: the first version
    of this function reported anisotropy 10.3 and "direction found" on a field
    of pure Gaussian noise. Bins are sized to the band, not fixed.
    """
    return int(np.clip(round(npix / MIN_PER_BIN), 24, 180))


def _smooth_circ(p, w=2):
    """Circular moving average; the profile wraps at 180 deg."""
    if w < 1:
        return p
    k = np.ones(2 * w + 1) / float(2 * w + 1)
    return np.convolve(np.r_[p[-w:], p, p[:w]], k, mode='valid')


def band_angular_power(S, px_nm, lo_nm, hi_nm, nang=None, q2=True):
    """Director-angle power spectrum restricted to one band of periods.

    q2 compensation matches `period()`: raw FFT power falls steeply with q, so
    without it every band comparison is dominated by its long-period edge.
    """
    P, per, ang, q, half = power_map(S, px_nm)
    band = (per >= lo_nm) & (per <= hi_nm) & np.isfinite(per) & half
    npix = int(band.sum())
    if nang is None:
        nang = _nang(npix)
    if npix < 40:
        return np.linspace(0, 180, nang, endpoint=False), np.zeros(nang), 0.0
    W = P * (q ** 2 if q2 else 1.0)
    edges = np.linspace(0.0, 180.0, nang + 1)
    idx = np.clip(np.digitize(ang[band], edges) - 1, 0, nang - 1)
    v = W[band]
    prof = (np.bincount(idx, v, minlength=nang)
            / np.maximum(np.bincount(idx, minlength=nang), 1))
    centres = 0.5 * (edges[1:] + edges[:-1])
    return centres, _smooth_circ(prof), float(np.nansum(v))


def _ring_profile(A):
    """Angle-averaged radial profile of an array, and the ring index map."""
    n = A.shape[0]
    yy, xx = np.indices(A.shape)
    r = np.round(np.hypot(xx - n // 2, yy - n // 2)).astype(int)
    prof = (np.bincount(r.ravel(), A.ravel())
            / np.maximum(np.bincount(r.ravel()), 1))
    return prof[r]                      # broadcast back to the 2-D grid


def _surrogate_aniso(amp_map, shape, px_nm, lo_nm, hi_nm, nang, rng):
    """Anisotropy of an ISOTROPIC field with the data's radial spectrum.

    Built as white noise shaped to `amp_map` in Fourier space, taken back to
    real space, then analysed by exactly the same function the data goes
    through -- window included.
    """
    n = shape[0]
    w = rng.normal(size=(n, n))
    F = np.fft.fftshift(np.fft.fft2(w))
    g = np.real(np.fft.ifft2(np.fft.ifftshift(F * amp_map)))
    _a, prof, _t = band_angular_power(g, px_nm, lo_nm, hi_nm, nang)
    if not np.any(prof > 0):
        return 0.0
    return float(prof.max() / max(np.median(prof), 1e-30))


def band_peak(S, px_nm, lo_nm, hi_nm, nang=None, n_perm=N_PERM, seed=0):
    """Dominant direction in a band, WITH a significance test.

    Returns (director_deg, anisotropy, period_nm, p_value).

    The p-value comes from permuting the angular labels of the band's FFT
    pixels while keeping their power values, which destroys angular structure
    and preserves everything else. It is the only part of this that separates
    "there is a direction here" from "this band is too sparse to tell".
    """
    P, per, ang, q, half = power_map(S, px_nm)
    band = (per >= lo_nm) & (per <= hi_nm) & np.isfinite(per) & half
    npix = int(band.sum())
    if npix < 40:
        return float('nan'), float('nan'), float('nan'), float('nan')
    if nang is None:
        nang = _nang(npix)
    a, prof, _ = band_angular_power(S, px_nm, lo_nm, hi_nm, nang)
    if not np.any(prof > 0):
        return float('nan'), float('nan'), float('nan'), float('nan')
    i = int(np.argmax(prof))
    aniso = float(prof[i] / max(np.median(prof), 1e-30))

    # THE SURROGATE IS BUILT IN IMAGE SPACE AND PUSHED THROUGH THE SAME
    # PIPELINE. Two earlier versions permuted the FFT instead and both were
    # wrong: shuffling across the band destroys the radial fall-off, and
    # shuffling within q-rings destroys the ANGULAR CORRELATION that the
    # Hanning window's spectral leakage puts between neighbouring FFT pixels.
    # Either way the null comes out slightly too flat, and "slightly" is
    # enough -- on pure noise the ring-shuffle null sat 7 % below the observed
    # value and returned p = 0.005 every time.
    #
    # An isotropic Gaussian field with the SAME radial spectrum, analysed by
    # the identical code path, carries every artefact the data carries:
    # window leakage, the square grid's angular sampling, the q^2 weighting,
    # the binning and the smoothing. What it does not carry is a direction.
    rng = np.random.default_rng(seed)
    amp = _ring_profile(np.sqrt(P))
    null = np.empty(n_perm)
    for k in range(n_perm):
        null[k] = _surrogate_aniso(amp, S.shape, px_nm, lo_nm, hi_nm, nang, rng)
    p = float((1.0 + np.sum(null >= aniso)) / (n_perm + 1.0))
    return float(a[i]), aniso, band_period(S, px_nm, float(a[i]),
                                           lo_nm, hi_nm), p


def band_period(S, px_nm, director_deg, lo_nm, hi_nm, dth=12.0):
    """Period of the structure running along `director_deg`, within a band.

    The wavevector sits at director - 90, which is the same mask `period()`
    uses; the only addition is the band restriction.
    """
    P, per, ang, q, half = power_map(S, px_nm)
    m = (np.abs((ang - director_deg + 90.0) % 180.0 - 90.0) < dth)
    m &= (per >= lo_nm) & (per <= hi_nm) & np.isfinite(per) & half
    if m.sum() < 8:
        return float('nan')
    # PEAK, NOT CENTROID. A power-weighted centroid over the whole band is
    # dragged toward the short-period end by the broadband noise floor, which
    # occupies most of the band's area. On synthetic data with a true 45 nm
    # modulation the centroid returned 28 nm at moderate SNR -- a 38 % error
    # that looked like a physical result. The peak of a binned, smoothed
    # q-profile is unbiased over the same SNR range.
    qq, ww = q[m], (P * q ** 2)[m]
    nb = int(np.clip(np.sqrt(m.sum()) * 1.5, 12, 60))
    lo_q, hi_q = 1000.0 / hi_nm, 1000.0 / lo_nm
    edges = np.linspace(lo_q, hi_q, nb + 1)
    i = np.clip(np.digitize(qq, edges) - 1, 0, nb - 1)
    prof = (np.bincount(i, ww, minlength=nb)
            / np.maximum(np.bincount(i, minlength=nb), 1))
    if nb >= 5:
        prof = np.convolve(prof, np.ones(3) / 3.0, mode='same')
    k = int(np.argmax(prof))
    c = 0.5 * (edges[1:] + edges[:-1])
    # parabolic refinement, so the answer is not quantised to the bin width
    if 0 < k < nb - 1:
        y0, y1, y2 = prof[k - 1], prof[k], prof[k + 1]
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if abs(den) > 1e-30 else 0.0
        qc = float(c[k] + np.clip(d, -1.0, 1.0) * (c[1] - c[0]))
    else:
        qc = float(c[k])
    return 1000.0 / qc if qc > 0 else float('nan')


def angle_between(a, b):
    """Separation of two DIRECTORS, mod 180, in [0, 90]."""
    return float(abs((float(a) - float(b) + 90.0) % 180.0 - 90.0))


def describe(S, px_nm, super_band=(150.0, 500.0), nano_band=(18.0, 120.0),
             aniso_min=2.0):
    """Both scales of one frame, as a dict."""
    ds, As, ps = band_peak(S, px_nm, *super_band)
    dn, An, pn = band_peak(S, px_nm, *nano_band)
    return dict(
        super_dir=ds, super_aniso=As, super_period=ps,
        super_ok=bool(As == As and As >= aniso_min),
        nano_dir=dn, nano_aniso=An, nano_period=pn,
        nano_ok=bool(An == An and An >= aniso_min),
        px_nm=px_nm,
        cross_angle=angle_between(ds, dn) if (ds == ds and dn == dn)
        else float('nan'))


def matched_amplitude(S, px_nm, director_deg, period_nm):
    """Amplitude of a modulation at a KNOWN direction and period, in the units
    of S. Projection onto the complex carrier, so it is phase-insensitive."""
    Z, n = _prep(S)
    yy, xx = np.mgrid[0:n, 0:n]
    a = np.deg2rad(director_deg)
    qx, qy = -np.sin(a), np.cos(a)
    ph = 2.0 * np.pi * (qx * xx + qy * yy) * px_nm / period_nm
    w = np.hanning(n)
    W = w[:, None] * w[None, :]
    norm = float(np.sum(W ** 2))
    c = float(np.sum(Z * np.cos(ph)))
    s = float(np.sum(Z * np.sin(ph)))
    return 2.0 * np.hypot(c, s) / max(norm, 1e-30)


def matched_test(S, px_nm, director_deg, period_nm, n_null=180, dmin=25.0):
    """Matched-filter detection of a modulation whose direction and period are
    already known from ANOTHER channel.

    Sensitivity comes from not searching: the blind band scan spends its power
    over every angle and every period in the band, while here both are fixed by
    the LDART fit and only the amplitude is unknown.

    The null is the same projection at the SAME |q| and many other directions,
    at least `dmin` degrees away from the one being tested. That keeps the
    radial spectrum, the window and the grid identical between test and null --
    only the direction changes.

    Returns (amplitude, z, p, null_sd).
    """
    amp = matched_amplitude(S, px_nm, director_deg, period_nm)
    null = []
    for d in np.linspace(0.0, 180.0, n_null, endpoint=False):
        if angle_between(d, director_deg) < dmin:
            continue
        null.append(matched_amplitude(S, px_nm, float(d), period_nm))
    null = np.asarray(null)
    sd = float(null.std())
    med = float(np.median(null))
    z = (amp - med) / max(sd, 1e-30)
    p = float((1.0 + np.sum(null >= amp)) / (len(null) + 1.0))
    return float(amp), float(z), p, sd


MIN_PERIODS_FFT = 4.0


def window_ok(lam_nm, window_um, min_periods=MIN_PERIODS_FFT, label=''):
    """Does a window of `window_um` hold enough periods to read a direction?

    THE GATE BELONGS HERE, not in each driver. It was implemented in
    block1_write.py and not in block2_pole.py, and the last write of 29 August
    went into a Lambda 369 nm area with a 1.0 um window -- 2.7 periods -- and
    returned p = 0.28 on a pre-registered prediction. A validity rule that
    lives per-driver silently vanishes the next time a driver is written.

    Returns (ok, n_periods, message). Callers decide whether to warn or abort;
    what they must not do is fail to ask.
    """
    lam_um = float(lam_nm) / 1000.0
    n = float(window_um) / max(lam_um, 1e-9)
    ok = n >= min_periods
    msg = ('%s%.2f um window holds %.2f Lambda at %.0f nm (need >= %.1f) -> %s'
           % (label + ': ' if label else '', window_um, n, lam_nm,
              min_periods, 'OK' if ok else 'TOO FEW PERIODS'))
    return ok, n, msg


def largest_lambda_for(window_um, min_periods=MIN_PERIODS_FFT):
    """The coarsest film a given window can read a direction from, in nm."""
    return 1000.0 * float(window_um) / float(min_periods)
