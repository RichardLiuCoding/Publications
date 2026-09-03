# -*- coding: utf-8 -*-
"""Local director field for the UTK frames, coloured by triad member.

Panels a and b of Figure 9 were a single diverging ramp on the raw signed
response, which shows that the stripes break along the strokes but does not
show which direction anything points. Here the local orientation is measured
with a structure tensor and then rendered with one colour ramp per allowed
member, so a stroke written to 2 degrees reads blue against a background the
raster left at 62 degrees.
"""
import numpy as np
from scipy import ndimage as ndi

TRIAD = (2.0, 62.0, 122.0)
# the same three colours the triad carries in every other figure
RAMP = ((0x44, 0x77, 0xAA), (0x2A, 0x9D, 0x8F), (0xC9, 0x36, 0x12))


def director_field(S, um, win_um=0.55):
    """Return (theta in degrees over [0,180), coherence in [0,1])."""
    px = um / S.shape[0]
    sig = max(1.0, win_um / px / 2.355)
    F = ndi.gaussian_filter(S.astype(float), 1.0)
    gy, gx = np.gradient(F)
    Jxx = ndi.gaussian_filter(gx * gx, sig)
    Jyy = ndi.gaussian_filter(gy * gy, sig)
    Jxy = ndi.gaussian_filter(gx * gy, sig)
    # the gradient is normal to a stripe, so the stripe runs 90 degrees off
    th = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)
    th = np.rad2deg(th) + 90.0
    tr = Jxx + Jyy
    coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / np.maximum(tr, 1e-12)
    return np.mod(th, 180.0), np.clip(coh, 0, 1), tr


def _rank(x):
    """Map an array onto its own percentile rank, which is robust to the very
    uneven gradient energy of a piezoresponse frame."""
    flat = x.ravel()
    order = np.argsort(flat)
    r = np.empty_like(flat, dtype=float)
    r[order] = np.linspace(0.0, 1.0, flat.size)
    return r.reshape(x.shape)


def rgb(S, um, triad=TRIAD, win_um=0.45, lo=0.12, hi=0.55):
    """One colour ramp per triad member, brightness from local order.

    A pixel is assigned to the member it is closest to in angle, wrapped at
    180 degrees, and then drawn from white towards that member's colour in
    proportion to how well ordered the stripes are there. Both coherence and
    gradient energy are taken as percentile ranks, so the two frames are
    rendered on the same footing without a shared absolute scale.
    """
    th, coh, tr = director_field(S, um, win_um)
    d = np.stack([np.abs((th - t + 90.0) % 180.0 - 90.0) for t in triad])
    who = np.argmin(d, axis=0)
    w = np.clip((coh - lo) / (hi - lo), 0, 1) ** 0.8 * _rank(tr) ** 0.5
    out = np.ones(S.shape + (3,))
    for k, col in enumerate(RAMP):
        m = who == k
        for c in range(3):
            out[..., c] = np.where(m, 1.0 - w * (1.0 - col[c] / 255.0),
                                   out[..., c])
    return out, who, w
