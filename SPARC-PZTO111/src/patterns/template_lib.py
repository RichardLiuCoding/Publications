# -*- coding: utf-8 -*-
"""template_lib.py -- charge-balanced write templates, and the geometry maths.

Separated from the driver so the geometry can be unit-tested offline without an
instrument, which is where every template bug so far has been catchable.

Three kinds, all returning [(x_um, y_um, volts), ...] with EXACTLY zero net DC
(C13) and every site inside the panel:

  parallel(ang)        the campaign's lattice: lines of one sign running ALONG
                       `ang`, alternating sign every sp = Lambda/2 across it, so
                       the sign period is Lambda perpendicular to `ang`. One
                       template wavevector, Q = (2 pi / Lambda) n_perp(ang).
                       This is what lattice_panel() builds; reimplemented here
                       so all three kinds share one clipping and balancing path.

  crossed(a_red, a_blue)
                       two NON-parallel families: + sites on lines along a_red,
                       - sites on lines along a_blue, each family spaced Lambda
                       perpendicular to itself. TWO template wavevectors at
                       once. This is the competition experiment: the film is
                       offered two commensurate directors and has to choose.

  solid()              a raster at one polarity -- no periodicity, hence no
                       wavevector. Drive without selection. Written as a +/-
                       PAIR of squares so the panel as a whole is balanced.

WHY THE SIGN CONVENTION MATTERS. In `parallel`, sign depends on the row index
alone, so one polarity runs the full length of a line. An earlier schematic drew
it as a checkerboard; that has power at (+-pi/sp, +-pi/sp), diagonal and at the
wrong magnitude, and it destroys the single commensurate wavevector the geometry
exists to provide.
"""
from __future__ import annotations

import numpy as np

MIN_SEP_UM = 0.045      # two sites closer than this would over-dose one spot


def _dirs(ang_deg):
    t = np.deg2rad(float(ang_deg))
    u = np.array([np.cos(t), np.sin(t)])          # along the line
    n = np.array([-np.sin(t), np.cos(t)])         # across the lines
    return u, n


def _line_family(centre, ang_deg, line_pitch, site_pitch, half, offset=0.0,
                 along=0.0):
    """Sites on parallel lines along `ang_deg`, clipped to a square panel.

    `line_pitch`  perpendicular distance between successive lines
    `site_pitch`  distance between sites along a line
    `half`        half-side of the square panel, in um
    `offset`      perpendicular shift of the whole family, in um
    `along`       shift of the whole family ALONG its own lines, in um. Needed
                  for the second family of a crossed panel: without it, at a
                  90 deg crossing half its sites coincide exactly with the
                  first family's and are deduped away, which halves the site
                  count and therefore DOUBLES the per-site charge at fixed
                  areal dose.
    """
    u, n = _dirs(ang_deg)
    c = np.asarray(centre, float)
    _hmax = max(half) if isinstance(half, (tuple, list)) else half
    reach = _hmax * np.sqrt(2.0) + line_pitch
    nj = int(np.ceil(reach / line_pitch))
    ni = int(np.ceil(reach / site_pitch))
    out = []
    hx, hy = (half if isinstance(half, (tuple, list)) else (half, half))
    for j in range(-nj, nj + 1):
        base = c + (j * line_pitch + offset) * n + along * u
        for i in range(-ni, ni + 1):
            p = base + i * site_pitch * u
            if abs(p[0] - c[0]) <= hx and abs(p[1] - c[1]) <= hy:
                out.append((float(p[0]), float(p[1]), j))
    return out


def _balance(pos, neg, v):
    """Trim to equal counts so the panel carries exactly zero net DC."""
    k = min(len(pos), len(neg))
    pos, neg = pos[:k], neg[:k]
    sites = ([(x, y, +float(v)) for (x, y) in pos]
             + [(x, y, -float(v)) for (x, y) in neg])
    m = float(np.mean([s[2] for s in sites])) if sites else 0.0
    assert abs(m) < 1e-9, 'net DC %.3e' % m
    return sites


def _dedupe(a, b, min_sep=MIN_SEP_UM):
    """Drop members of `b` that sit on top of a member of `a`."""
    if not a or not b:
        return list(b)
    A = np.array([(x, y) for (x, y, *_r) in a])
    keep = []
    for s in b:
        d = np.hypot(A[:, 0] - s[0], A[:, 1] - s[1])
        if d.min() >= min_sep:
            keep.append(s)
    return keep


def _serpentine(sites, ang_deg):
    """Order along the line direction, alternating, so travel stays short."""
    u, n = _dirs(ang_deg)
    def key(s):
        p = np.array([s[0], s[1]])
        row = round(float(p @ n), 4)
        col = float(p @ u)
        return (row, col)
    rows = {}
    for s in sites:
        p = np.array([s[0], s[1]])
        rows.setdefault(round(float(p @ n), 4), []).append(s)
    out = []
    for k, (r, group) in enumerate(sorted(rows.items())):
        group.sort(key=lambda s: float(np.array([s[0], s[1]]) @ u),
                   reverse=bool(k % 2))
        out.extend(group)
    return out


# ------------------------------------------------------------------ kinds
def parallel(centre, half, lam_um, ang_deg, v):
    """Lines along ang_deg, sign alternating every Lambda/2 across them."""
    sp = lam_um / 2.0
    fam = _line_family(centre, ang_deg, sp, sp, half)
    pos = [(x, y) for (x, y, j) in fam if j % 2 == 0]
    neg = [(x, y) for (x, y, j) in fam if j % 2 != 0]
    sites = _balance(pos, neg, v)
    return _serpentine(sites, ang_deg)


def crossed(centre, half, lam_um, ang_red, ang_blue, v):
    """+ lines along ang_red, - lines along ang_blue; two wavevectors."""
    sp = lam_um / 2.0
    red = _line_family(centre, ang_red, lam_um, sp, half)
    blu = _line_family(centre, ang_blue, lam_um, sp, half,
                       offset=lam_um / 2.0, along=lam_um / 4.0)
    red_xy = [(x, y) for (x, y, _j) in red]
    blu_xy = [(x, y) for (x, y, _j) in blu]
    blu_xy = [s for s in _dedupe([(x, y) for (x, y) in red_xy],
                                 [(x, y) for (x, y) in blu_xy])]
    sites = _balance(red_xy, blu_xy, v)
    # order each family separately: crossing families interleaved would make
    # the tip traverse the panel between every pulse
    p = _serpentine([s for s in sites if s[2] > 0], ang_red)
    m = _serpentine([s for s in sites if s[2] < 0], ang_blue)
    return p + m


def solid(centre, half, lam_um, ang_deg, v, raster_pitch=0.06, gap=0.10):
    """A +/- pair of solid rasters, side by side with a gap between them.

    The gap is not cosmetic: edge to edge, the outermost + column and the
    outermost - column sat `raster_pitch` apart or less, putting opposite
    polarities within 40 nm of each other.
    """
    c = np.asarray(centre, float)
    sub = (half - gap / 2.0) / 2.0
    out = []
    for k, sgn in ((-1, +1), (+1, -1)):
        cc = c + np.array([k * (sub + gap / 2.0), 0.0])
        nlines = int(round(2 * sub / raster_pitch)) + 1
        for i in range(nlines):
            y = cc[1] - sub + i * raster_pitch
            xs = np.arange(cc[0] - sub, cc[0] + sub + 1e-9, raster_pitch)
            if i % 2:
                xs = xs[::-1]
            for x in xs:
                out.append((float(x), float(y), sgn * float(v)))
    m = float(np.mean([s[2] for s in out]))
    assert abs(m) < 1e-9, 'net DC %.3e' % m
    return out



def oblique_basis(lam_um, theta_deg):
    """Basis for an oblique lattice whose perpendicular sign period is Lambda.

    Returns (a_um, s_um, d_um): equal basis length, along-line offset per line,
    perpendicular line spacing. theta = 90 -> square of side Lambda/2.
    """
    th = np.deg2rad(float(theta_deg))
    st = np.sin(th)
    if st < 1e-6:
        raise ValueError('theta %.1f deg is degenerate' % theta_deg)
    d = lam_um / 2.0
    a = d / st
    return float(a), float(a * np.cos(th)), float(d)


def shear_charge_ratio(theta_deg):
    """Per-site charge relative to the square lattice, at fixed areal dose.

    Density is 4 sin(theta) / Lambda^2, so charge per site scales as
    1 / sin(theta). This is the quantity that puts theta = 30 over C21.
    """
    return 1.0 / max(1e-6, np.sin(np.deg2rad(float(theta_deg))))


def sheared(centre, half, lam_um, ang_deg, theta_deg, v):
    """Parallel lines along `ang_deg`, alternating sign, successive lines
    offset along themselves so the lattice is oblique with basis angle
    `theta_deg`.

    theta = 90 is the square lattice; theta = 60 is triangular. The
    perpendicular sign period is Lambda for every theta, so the commensurate
    wavevector Q = (2 pi / Lambda) n_perp is identical across the series.
    """
    a, s_off, d = oblique_basis(lam_um, theta_deg)
    u, n = _dirs(ang_deg)
    c = np.asarray(centre, float)
    reach = half * np.sqrt(2.0) + 2 * max(a, d)
    nj = int(np.ceil(reach / d))
    ni = int(np.ceil(reach / a)) + int(np.ceil(nj * abs(s_off) / a)) + 2
    pos, neg = [], []
    for j in range(-nj, nj + 1):
        base = c + (j * d) * n + (j * s_off) * u
        for i in range(-ni, ni + 1):
            p = base + i * a * u
            if abs(p[0] - c[0]) <= half and abs(p[1] - c[1]) <= half:
                (pos if j % 2 == 0 else neg).append((float(p[0]), float(p[1])))
    sites = _balance(pos, neg, v)
    return _serpentine(sites, ang_deg)



def trace_lines(centre, half, lam_um, ang_deg, v):
    """Continuous alternating-sign lines: same Q as parallel(), but strokes.

    Returns [(pts, volts), ...] where pts is a list of (x, y) endpoints for a
    stroke. The caller draws each stroke n_pass times to reach the target dose.
    """
    d = lam_um / 2.0
    u, n = _dirs(ang_deg)
    c = np.asarray(centre, float)
    reach = half * np.sqrt(2.0) + d
    nj = int(np.ceil(reach / d))
    out = []
    for j in range(-nj, nj + 1):
        base = c + (j * d) * n
        # clip the infinite line to the square panel
        ts = []
        for sgn in (-1.0, 1.0):
            for axis in (0, 1):
                denom = u[axis]
                if abs(denom) < 1e-12:
                    continue
                t = (c[axis] + sgn * half - base[axis]) / denom
                p = base + t * u
                if (abs(p[0] - c[0]) <= half + 1e-9
                        and abs(p[1] - c[1]) <= half + 1e-9):
                    ts.append(t)
        if len(ts) < 2:
            continue
        t0, t1 = min(ts), max(ts)
        if t1 - t0 < 0.02:
            continue
        p0, p1 = base + t0 * u, base + t1 * u
        out.append(([(float(p0[0]), float(p0[1])),
                     (float(p1[0]), float(p1[1]))],
                    (+1.0 if j % 2 == 0 else -1.0) * float(v), j))
    # Charge balance by TRIMMING length, never by dropping lines. Popping
    # strokes until the + and - totals matched exactly reduced a 9-line panel
    # to 2 and silently gutted the template's commensurate content while still
    # passing every gate.
    if not out:
        return []

    def length(o):
        (a, b), _v, _j = o
        return float(np.hypot(b[0] - a[0], b[1] - a[1]))

    pos = [o for o in out if o[1] > 0]
    neg = [o for o in out if o[1] < 0]
    if not pos or not neg:
        return []
    lp, ln = sum(map(length, pos)), sum(map(length, neg))
    maj, f = (pos, ln / lp) if lp > ln else (neg, lp / ln)
    trimmed = []
    for o in out:
        (a, b), vv, jj = o
        if any(o is m for m in maj) and f < 1.0:
            a_ = np.asarray(a, float)
            b_ = np.asarray(b, float)
            mid = 0.5 * (a_ + b_)
            a_ = mid + (a_ - mid) * f
            b_ = mid + (b_ - mid) * f
            a = (float(a_[0]), float(a_[1]))
            b = (float(b_[0]), float(b_[1]))
        trimmed.append(([a, b], vv, jj))
    lp2 = sum(length(o) for o in trimmed if o[1] > 0)
    ln2 = sum(length(o) for o in trimmed if o[1] < 0)
    assert abs(lp2 - ln2) < 1e-6 * max(1.0, lp2), \
        'trace not charge balanced: %+.3e' % (lp2 - ln2)

    keep = sorted(trimmed, key=lambda o: o[2])
    # serpentine: reverse every other stroke so the tip does not fly back
    res = []
    for k, (pts, vv, _j) in enumerate(keep):
        res.append((pts[::-1] if k % 2 else pts, vv))
    return res


def trace_passes(sigma, lam_um, v, speed_um_s):
    """How many passes of a continuous trace reach the target areal dose."""
    d = lam_um / 2.0
    per_pass = abs(v) / (d * speed_um_s)
    return max(1, int(round(sigma / per_pass))), per_pass

BUILDERS = {'parallel': parallel, 'crossed': crossed,
            'sheared': sheared, 'solid': solid}


def build(kind, centre, half, lam_um, v, **kw):
    if kind == 'parallel':
        return parallel(centre, half, lam_um, kw['ang'], v)
    if kind == 'crossed':
        return crossed(centre, half, lam_um, kw['ang_red'], kw['ang_blue'], v)
    if kind == 'sheared':
        return sheared(centre, half, lam_um, kw['ang'], kw['theta'], v)
    if kind == 'solid':
        return solid(centre, half, lam_um, kw.get('ang', 0.0), v)
    raise ValueError('unknown kind %r' % kind)


def dose(sites, v, dwell_s, half):
    """Areal dose in V.s/um^2 and per-site charge in V.s."""
    q_site = abs(v) * dwell_s
    area = (2 * half) ** 2
    return len(sites) * q_site / area, q_site


def dwell_for_sigma(sigma, sites, v, half):
    """Dwell per site that puts this panel at the requested areal dose."""
    area = (2 * half) ** 2
    return sigma * area / (max(1, len(sites)) * abs(v))
