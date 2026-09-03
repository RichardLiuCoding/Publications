# -*- coding: utf-8 -*-
"""Point-pulse lattice generator for isotropic erasure of the in-plane texture.

Rationale
---------
Every write tried so far is a moving-tip raster. A raster necessarily carries a
direction, so it cannot erase directional order - it can only replace one
direction with another. AC + DC rastering was tried three times on 7 August and
never randomised the state; it relaxed toward the local attractor instead
(w90 0.575 -> 0.382, anisotropy 76 -> 37).

A stationary pulse has no in-plane direction: the field under the apex is
radially symmetric, so it destroys directional order rather than imposing it.
It also decouples field amplitude from areal coverage, so a much larger local
field-time product is reachable than a 0.5 um/s raster can deliver, without
poling a large area.

Two design rules follow from the campaign data and are enforced here:

1. ZERO NET CHARGE. A DC offset re-poles: +3 V DC drove the up-orbit fraction to
   28 % and -3 V DC to 66 % on 6 August, and poling closes the reachability
   gate. The sign therefore alternates across the lattice and the residual
   imbalance is reported.

2. NO TWO-FOLD SYMMETRY. The eraser must not be a template. A square lattice
   has 0/90 deg axes and would bias the 90 deg family exactly as the same-sign
   raster does. Use 'tri' (three-fold, compatible with all three families
   equally) or 'jitter' (no symmetry at all). 'square' is provided only as the
   deliberate control that should FAIL to erase.

Requires the two TrajectoryBuilder patches already in the notebook: .dwell()
for stationary points and the travel-aware .to_arrays().
"""

from __future__ import annotations
import numpy as np


def gen_pulse_lattice(w_um=3.0, h_um=3.0, spacing_um=0.175, angle_deg=0.0,
                      center_um=(2.5, 2.5), v=9.0, dwell_pts=3,
                      lattice='tri', jitter_frac=0.0, sign='checker',
                      field_um=5.0, step_um=0.02, speed_um_s=0.5,
                      travel_v=0.0, seed=0, verbose=True):
    """Build a zero-net-charge lattice of stationary bias pulses.

    Parameters
    ----------
    w_um, h_um     : extent of the erased region.
    spacing_um     : nearest-neighbour pulse spacing. Set from the lamellar
                     period: Lambda/2 to Lambda, i.e. 0.15-0.35 um for
                     Lambda = 300-400 nm. Denser than Lambda/2 risks merging
                     into a uniform pole; sparser leaves the skeleton intact.
    angle_deg      : rotation of the lattice. Only meaningful for 'square'.
    v              : pulse amplitude, magnitude. Sign alternates per `sign`.
    dwell_pts      : stationary points per pulse. Dwell time is
                     dwell_pts * step_um / speed_um_s, so 3 points at
                     step 0.02 um and 0.5 um/s is 120 ms.
    lattice        : 'tri' (three-fold), 'jitter' (randomised), or 'square'
                     (two-fold; the negative control).
    jitter_frac    : extra random displacement as a fraction of spacing,
                     applied to any lattice. 0.35 fully decorrelates 'tri'.
    sign           : 'checker' (alternate by lattice parity, the default),
                     'alternate' (alternate along the visiting order), or
                     'const' (single polarity; poles the area, for reference).
    speed_um_s     : only used to report timing; the panel sets the real speed.

    Returns
    -------
    xs, ys, vs : float arrays in um, um, V - feed to TrajectoryBuilder, or use
                 build_pulse_trajectory() below to get a saved file directly.
    """
    rng = np.random.default_rng(seed)
    cx, cy = center_um
    d = float(spacing_um)

    # --- lattice sites in the region frame ---------------------------------
    if lattice == 'tri':
        dy = d * np.sqrt(3.0) / 2.0
        ny = int(np.floor(h_um / dy)) + 1
        pts = []
        for i in range(ny):
            y = -h_um / 2 + i * dy
            off = 0.0 if i % 2 == 0 else d / 2.0
            nx = int(np.floor((w_um - off) / d)) + 1
            for j in range(nx):
                pts.append((-w_um / 2 + off + j * d, y, i, j))
    elif lattice in ('square', 'jitter'):
        nx = int(np.floor(w_um / d)) + 1
        ny = int(np.floor(h_um / d)) + 1
        pts = [(-w_um / 2 + j * d, -h_um / 2 + i * d, i, j)
               for i in range(ny) for j in range(nx)]
    else:
        raise ValueError("lattice must be 'tri', 'square' or 'jitter'")

    jf = jitter_frac + (0.35 if lattice == 'jitter' and jitter_frac == 0.0 else 0.0)
    P = []
    for (x, y, i, j) in pts:
        if jf:
            x = x + rng.uniform(-jf, jf) * d
            y = y + rng.uniform(-jf, jf) * d
        P.append((x, y, i, j))

    # --- rotate and translate ---------------------------------------------
    t = np.deg2rad(angle_deg); ct, st = np.cos(t), np.sin(t)
    site = []
    for (x, y, i, j) in P:
        X = cx + x * ct - y * st
        Y = cy + x * st + y * ct
        site.append((X, Y, i, j))

    # --- serpentine visiting order, to keep travel short -------------------
    rows = {}
    for s in site:
        rows.setdefault(s[2], []).append(s)
    order = []
    for k, i in enumerate(sorted(rows)):
        r = sorted(rows[i], key=lambda s: s[0], reverse=bool(k % 2))
        order.extend(r)

    # --- polarity ----------------------------------------------------------
    n = int(dwell_pts)
    sgn = np.empty(len(order))
    for k, (X, Y, i, j) in enumerate(order):
        if sign == 'checker':
            sgn[k] = 1.0 if (i + j) % 2 == 0 else -1.0
        elif sign == 'alternate':
            sgn[k] = 1.0 if k % 2 == 0 else -1.0
        elif sign == 'const':
            sgn[k] = 1.0
        else:
            raise ValueError("sign must be 'checker', 'alternate' or 'const'")

    # Exact balance. A triangular lattice has unequal row lengths, so parity
    # alone leaves a residual: 170 plus against 180 minus at 175 nm spacing,
    # a mean bias of -0.26 V over the path. A residual DC is precisely what
    # re-poles the area, so flip the minimum number of majority-sign pulses,
    # chosen at even intervals through the visiting order to stay spread out.
    if sign != 'const':
        imb = int(sgn.sum())
        take = abs(imb) // 2
        if take:
            maj = 1.0 if imb > 0 else -1.0
            idx = np.where(sgn == maj)[0]
            pick = np.unique(idx[np.round(np.linspace(0, len(idx) - 1,
                                                      take)).astype(int)])
            sgn[pick] = -maj
        # An odd pulse count cannot balance exactly; one pulse of residual is
        # left, which is 1/N of a single pulse and far below the DC that poled.

    xs, ys, vs = [], [], []
    for k, (X, Y, i, j) in enumerate(order):
        xs.append(np.full(n, X)); ys.append(np.full(n, Y))
        vs.append(np.full(n, sgn[k] * float(v)))

    X = np.concatenate(xs); Y = np.concatenate(ys); V = np.concatenate(vs)

    # --- report ------------------------------------------------------------
    npulse = len(order)
    npos = int((sgn > 0).sum())
    travel = float(np.sum(np.hypot(np.diff([s[0] for s in order]),
                                   np.diff([s[1] for s in order]))))
    dwell_s = n * step_um / speed_um_s
    t_total = (npulse * n * step_um + travel) / speed_um_s
    ext = (X.min(), X.max(), Y.min(), Y.max())
    if verbose:
        print(f"gen_pulse_lattice  {lattice}"
              f"{f' + jitter {jf:.2f}d' if jf else ''}, sign={sign}")
        print(f"  {npulse} pulses at |V| = {v:.1f} V, spacing {d*1000:.0f} nm, "
              f"dwell {dwell_s*1000:.0f} ms each")
        print(f"  polarity {npos} plus / {npulse-npos} minus  ->  "
              f"net charge imbalance {abs(2*npos-npulse)/npulse*100:.1f} % of one pulse")
        print(f"  mean bias over the path = {V.mean():+.4f} V")
        print(f"  extent X[{ext[0]:.3f},{ext[1]:.3f}] Y[{ext[2]:.3f},{ext[3]:.3f}] um")
        print(f"  travel {travel:.0f} um, total time {t_total/60:.1f} min at "
              f"{speed_um_s} um/s")
        eff = npulse * (np.pi * (d / 2) ** 2) / (w_um * h_um)
        print(f"  pulse areal fill (disc of radius spacing/2) = {eff:.2f}")
    if min(ext[0], ext[2]) < 0 or max(ext[1], ext[3]) > field_um:
        raise ValueError(f"lattice leaves the {field_um} um field: {ext}")
    return X, Y, V


def build_pulse_trajectory(TrajectoryBuilder, fname, **kw):
    """Convenience wrapper: build, save, and return the builder for preview.

    Travel between pulses is inserted by the patched .to_arrays(), so the tip
    is at travel_v (0 V by default) while it moves and only at +-v while
    stationary.
    """
    step = kw.get('step_um', 0.02)
    field = kw.get('field_um', 5.0)
    tv = kw.pop('travel_v', 0.0)
    X, Y, V = gen_pulse_lattice(travel_v=tv, **kw)
    tb = TrajectoryBuilder(field_um=field, step_um=step)
    tb.travel_v = tv
    n = int(kw.get('dwell_pts', 3))
    for k in range(0, len(X), n):
        tb.dwell((X[k], Y[k]), V[k], n=n)
    tb.save(fname)
    return tb
