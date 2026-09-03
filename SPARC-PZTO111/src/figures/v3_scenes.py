# -*- coding: utf-8 -*-
"""Figures 1 and 2 of the v3 manuscript, described once as Scenes.

Both are emitted to matplotlib for the document and to native PowerPoint
shapes for the editable deck. Text is kept to labels and keywords: the figures
carry the structure, the captions carry the sentences.
"""
import itertools

import numpy as np

from scene import Scene
import v3_glyphs as G

W = 6.70
MEM, HUM, HYP = "#2A9D8F", "#C93612", "#AA3377"
EXP, RES, INS = "#4477AA", "#EE7733", "#6E7A86"
PHY, CTL = "#1F6F63", "#31558C"
INK, GREY, PALE = "#12293F", "#5E6873", "#9AA7B4"


def _rot(th):
    c, s = np.cos(th), np.sin(th)
    return np.array([[c, -s], [s, c]])


def _nano_stack(sc, x, y, w, nlam, ang, pol, fills=("#F5E7CE", "#E0D2EA")):
    """A magnified laminate at `ang`, built with the rule used by _laminate.

    Walls run along `ang`. The two polarization variants sit at ang-30 and
    ang-150, which are 120 deg apart and straddle the wall normal at ang-90,
    so their average lies on that normal. Each lamella is subdivided into
    sheared nanodomain cells, as the hierarchy actually looks.
    """
    th = np.deg2rad(ang)
    R = _rot(th)

    def fr(px, py):
        p = R @ np.array([px, py])
        return (x + w / 2 + p[0], y + w / 2 + p[1])

    for k in range(nlam):
        y0 = -w / 2 + k * w / nlam
        y1 = y0 + w / nlam
        sc.poly([fr(-w / 2, y0), fr(w / 2, y0), fr(w / 2, y1), fr(-w / 2, y1)],
                fill=fills[k % 2], line="#8A7A5C", lw=0.8, z=3)
        # sheared cell walls inside the lamella
        for q in range(1, 4):
            xq = -w / 2 + q * w / 4
            sh = 0.26 * (w / nlam)
            sc.line(*fr(xq - sh, y0), *fr(xq + sh, y1), color="#A29170",
                    lw=0.5, z=4)
        a = np.deg2rad(pol[k % 2])
        col = "#2F2A22" if k % 2 == 0 else C_TEAL
        L = 0.072
        for q in (0.28, 0.72):
            bx, by = fr(-w / 2 + q * w, (y0 + y1) / 2)
            sc.arrow(bx - L * np.cos(a), by - L * np.sin(a),
                     bx + L * np.cos(a), by + L * np.sin(a),
                     color=col, lw=1.2, head=7.0, z=6)


# A (111) rhombohedral film has ONE set of three in-plane polarization
# projections per out-of-plane sign, 120 deg apart. Every superdomain is a
# laminate of a PAIR drawn from that one set, so the three superdomains share
# their variants rather than each inventing its own. Deriving the pair from
# the director alone, as an earlier version did, produced five distinct
# variants instead of three and left the three averages 60 deg apart.
def _variant_triad(tri):
    """The three in-plane variants whose pairwise walls give the directors."""
    best = None
    for phi in np.arange(0.0, 120.0, 0.25):
        V = [phi, phi + 120.0, phi + 240.0]
        walls = sorted(_axis(_ang(_u(a) - _u(b)))
                       for a, b in itertools.combinations(V, 2))
        err = sum(min(abs(w - t), 180.0 - abs(w - t))
                  for w, t in zip(walls, sorted(tri)))
        if best is None or err < best[0]:
            best = (err, V)
    return best[1]


def _laminate_of(director, variants):
    """The variant pair whose wall runs along `director`, and their average.

    The sum of two unit vectors 120 deg apart points opposite the third, which
    is why the three superdomain averages come out 120 deg apart while their
    walls are only 60 deg apart.
    """
    for a, b in itertools.combinations(variants, 2):
        if abs(_axis(_ang(_u(a) - _u(b))) - _axis(director)) < 0.6:
            return (a, b), _ang(_u(a) + _u(b))
    raise ValueError("no variant pair builds a wall along %.1f" % director)


def _u(a):
    return np.array([np.cos(np.deg2rad(a)), np.sin(np.deg2rad(a))])


def _ang(v):
    return (np.degrees(np.arctan2(v[1], v[0])) + 360.0) % 360.0


def _axis(a):
    return a % 180.0


def _laminate(sc, cx, cy, ang, size, fill, nstripe=14, lw=0.9, avg=None):
    """A superdomain: a dense stack of nano lamellae with its average arrow.

    `ang` is the wall direction, which is what the angular power spectrum
    measures. `avg` is the polarization average, which is normal to the walls
    but whose sense is set by which variant pair builds this laminate.
    """
    R = _rot(np.deg2rad(ang - 90.0))
    half = size / 2.0

    def f(p):
        v = R @ np.asarray(p, float)
        return (cx + v[0], cy + v[1])

    sc.poly([f((-half, -half)), f((half, -half)), f((half, half)),
             f((-half, half))], fill=fill, line="#4A4335", lw=lw, z=2)
    for k in range(1, nstripe):
        x0 = -half + k * size / nstripe
        sc.line(*f((x0, -half)), *f((x0, half)), color="#6E6250", lw=0.45, z=3)
    aa = np.deg2rad(ang - 90.0 if avg is None else avg)
    v = np.array([np.cos(aa), np.sin(aa)]) * size * 0.60
    sc.arrow(cx - v[0] / 2, cy - v[1] / 2, cx + v[0] / 2, cy + v[1] / 2,
             color=HUM, lw=2.0, z=6)


# soft palette: pale fill, mid stroke, saturated text, after the visual
# grammar of the recent Nature agentic-science figures
PAL = {
 "phy": ("#EDF5F3", "#7FB3A8", "#1F6F63"),
 "ctl": ("#EEF2FA", "#8FA6C8", "#31558C"),
 "hum": ("#FBEFE9", "#D9906F", "#C0562F"),
 "hyp": ("#F6EBF4", "#C193BB", "#8E4585"),
 "exp": ("#EAF0F8", "#93AED2", "#3E6DA6"),
 "res": ("#FCF1E6", "#E4AE79", "#D2762A"),
 "mem": ("#E6F3F0", "#7FC2B6", "#2A9D8F"),
 "ins": ("#F1F3F5", "#B6BFC7", "#6E7A86"),
}
HAIR = "#C8D2D8"
C_TEAL = "#2A9D8F"


def _group(sc, x, y, w, h, key, title, note=None):
    """A pale container with a centred title, Robin style."""
    fill, stroke, ink = PAL[key]
    sc.rect(x, y, w, h, fill=fill, line=stroke, lw=1.0, radius=0.07, z=0)
    sc.text(x + w / 2, y + h - 0.15, title, size=9.2, color=ink, bold=True,
            ha="center", z=5)
    if note:
        sc.text(x + w / 2, y + h - 0.31, note, size=7.2, color=ink,
                ha="center", italic=True, z=5)
    return ink


def _card(sc, x, y, w, h, key, head, sub=None, radius=0.045, hs=7.4, ss=6.7):
    """A pale rounded card with centred text."""
    fill, stroke, ink = PAL[key]
    sc.rect(x, y, w, h, fill=fill, line=stroke, lw=0.9, radius=radius, z=3)
    if sub:
        sc.text(x + w / 2, y + h * 0.68, head, size=hs, color=ink, bold=True,
                ha="center", z=5)
        sc.text(x + w / 2, y + h * 0.22, sub, size=ss, color="#5E6873",
                ha="center", z=5)
    else:
        sc.text(x + w / 2, y + h / 2, head, size=hs, color=ink, bold=True,
                ha="center", z=5)
    return ink


# ===================================================== Figure 1
def fig1():
    HF = 5.72
    sc = Scene(W, HF)
    PT_ = PAL["phy"][2]
    CT_ = PAL["ctl"][2]

    # ---------------------------------------------- physics plane
    _group(sc, 0.14, 3.54, W - 0.28, 2.00, "phy", "PHYSICS PLANE",
           "what the material allows")
    sc.text(0.18, 5.16, "a", size=9.4, color=INK, bold=True)
    sc.text(3.62, 5.10, "b", size=9.4, color=INK, bold=True)
    sc.line(3.50, 3.66, 3.50, 5.06, color=HAIR, lw=0.9, dash="--", z=1)

    # (a) nanodomains average into a superdomain, and three are allowed
    # The magnified laminate is built from the SAME rule as the blocks it
    # magnifies, so the two can never drift apart: walls run along `ang`, the
    # two variants sit 120 deg apart straddling the wall normal, and their
    # average therefore lands on that normal. Hard coding the arrows here is
    # what put the previous version 90 deg out.
    TRI = [2.0, 62.0, 122.0]
    VAR = _variant_triad(TRI)
    LAM = {d: _laminate_of(d, VAR) for d in TRI}
    D1 = TRI[0]
    NX, NY, NS, NLAM = 0.36, 4.18, 0.64, 5
    _nano_stack(sc, NX, NY, NS, NLAM, D1, LAM[D1][0])
    sc.text(NX + NS / 2, NY - 0.07, "nanodomains", size=7.4, color=INK,
            ha="center", va="top")
    sc.text(NX + NS / 2, NY - 0.22, "\u039b \u2248 300 nm", size=6.8,
            color=GREY, ha="center", va="top")

    # the two levels, drawn once so the reader can see where each arrow lives
    wn, DY = LAM[D1][1], NY + NS + 0.13
    cd, sd = np.cos(np.deg2rad(D1)), np.sin(np.deg2rad(D1))
    sc.arrow(NX + NS * 0.5 - 0.30 * cd, DY - 0.30 * sd,
             NX + NS * 0.5 + 0.30 * cd, DY + 0.30 * sd, color=GREY, lw=1.4,
             head=7.0, z=7)
    sc.arrow(NX + NS * 0.5 + 0.30 * cd, DY + 0.30 * sd,
             NX + NS * 0.5 - 0.30 * cd, DY - 0.30 * sd, color=GREY, lw=1.4,
             head=7.0, z=7)
    sc.text(NX + NS * 0.5, DY + 0.06, "director", size=6.8, color=GREY,
            ha="center", va="bottom", z=8)
    AVX, AVY = NX + NS + 0.20, NY + NS * 0.80
    sc.arrow(AVX, AVY, AVX + 0.26 * np.cos(np.deg2rad(wn)),
             AVY + 0.26 * np.sin(np.deg2rad(wn)), color=PAL["hum"][2],
             lw=2.2, head=10.0, z=7)
    sc.text(AVX + 0.07, AVY - 0.13, "average", size=6.8,
            color=PAL["hum"][2], ha="left", z=8)
    sc.line(AVX, AVY - 0.062, AVX + 0.062, AVY - 0.062, color=GREY,
            lw=0.8, z=8)
    sc.line(AVX + 0.062, AVY - 0.062, AVX + 0.062, AVY, color=GREY,
            lw=0.8, z=8)

    CX0, CY0, BS = 2.14, 4.58, 0.46
    for k, (t, fc) in enumerate(zip(TRI,
                                    ["#D9CBE8", "#C6D8E4", "#EED4C6"])):
        cx = CX0 + k * 0.60
        _laminate(sc, cx, CY0, t, BS, fc, nstripe=9, lw=0.7, avg=LAM[t][1])
        sc.text(cx, CY0 - BS * 0.98, "d%d" % (k + 1), size=8.6,
                color=PAL["hum"][2], ha="center", va="top", italic=True)
    sc.rect(CX0 - 0.10, CY0 - 0.10, 0.20, 0.20, fill=None, line=GREY, lw=0.7,
            dash="--", z=7)
    sc.line(NX + NS + 0.01, NY + NS, CX0 - 0.10, CY0 + 0.10, color=GREY,
            lw=0.6, dash="--", z=2)
    sc.line(NX + NS + 0.01, NY - 0.02, CX0 - 0.10, CY0 - 0.10, color=GREY,
            lw=0.6, dash="--", z=2)
    sc.text(CX0 + 0.60, CY0 - BS * 0.98 - 0.17, "superdomains", size=7.4,
            color=INK, ha="center", va="top")
    sc.text(CX0 + 0.60, CY0 - BS * 0.98 - 0.32,
            "directors 60\u00b0 apart, averages 120\u00b0 apart", size=6.8,
            color=GREY, ha="center", va="top")

    # (b) the variant graph and two routes
    cx, cy, R = 4.26, 4.44, 0.40
    up, dn = [30.0, 150.0, 270.0], [90.0, 210.0, 330.0]
    pos = {a: (cx + R * np.cos(np.deg2rad(a)), cy + R * np.sin(np.deg2rad(a)))
           for a in up + dn}
    anti = {30.0: 210.0, 150.0: 330.0, 270.0: 90.0}
    anti.update({v: k for k, v in anti.items()})
    seen = set()
    for a in up + dn:
        for b in up + dn:
            if a == b or (b, a) in seen:
                continue
            seen.add((a, b))
            sc.line(*pos[a], *pos[b], color="#B9C6CE", lw=0.6,
                    dash=None if anti[a] != b else ":", z=2)
    sc.line(*pos[30.0], *pos[150.0], color=PT_, lw=2.1, z=4)
    sc.line(*pos[30.0], *pos[90.0], color="#C77CB0", lw=1.7, z=4)
    sc.line(*pos[90.0], *pos[150.0], color="#C77CB0", lw=1.7, z=4)
    for a in up:
        sc.ellipse(*pos[a], 0.062, fill=PT_, line="#FFFFFF", lw=1.0, z=6)
    for a in dn:
        sc.ellipse(*pos[a], 0.062, fill="#FFFFFF", line=PT_, lw=1.2, z=6)
    sc.text(pos[30.0][0], pos[30.0][1] + 0.09, "start", size=6.8, color=INK,
            ha="center", va="bottom", z=7)
    sc.text(pos[150.0][0], pos[150.0][1] + 0.09, "end", size=6.8, color=INK,
            ha="center", va="bottom", z=7)
    LX = 4.94
    for yy, col, lab in ((4.76, PT_, "one 90\u00b0 step"),
                         (4.56, "#C77CB0", "two 90\u00b0 steps")):
        sc.line(LX, yy, LX + 0.20, yy, color=col, lw=2.0, z=6)
        sc.text(LX + 0.27, yy, lab, size=7.0, color=col)
    for yy, dash, lab in ((4.32, None, "90\u00b0 ferroelastic"),
                          (4.16, ":", "180\u00b0 reversal")):
        sc.line(LX, yy, LX + 0.20, yy, color="#B9C6CE", lw=0.8, dash=dash, z=6)
        sc.text(LX + 0.27, yy, lab, size=6.8, color=INK)
    for yy, fill, lab in ((3.96, PT_, "out-of-plane up"),
                          (3.80, "#FFFFFF", "out-of-plane down")):
        sc.ellipse(LX + 0.10, yy, 0.052, fill=fill, line=PT_, lw=1.1, z=6)
        sc.text(LX + 0.27, yy, lab, size=6.8, color=INK)
    sc.text(4.26, 3.80, "same measured director,\ndifferent route",
            size=7.0, color=PAL["hum"][2], ha="center", lead=1.38)

    # ---------------------------------------------- the map, as a matrix
    sc.text(W / 2, 3.38, "THESE TWO PLANES DO NOT MAP ONE TO ONE", size=9.0,
            color=INK, bold=True, ha="center")
    COLS = [(2.98, "carries an axis\nof its own"),
            (4.14, "selects a\ndirector"),
            (5.22, "moves the\nOP sign")]
    ROWS = [(2.76, "uniform DC", ["x", "x", "v"]),
            (2.55, "DC + motion", ["v", "v", "?"]),
            (2.34, "AC bias", ["x", "x", "v"]),
            (2.13, "pulse lattice", ["v", "v", "?"])]
    sc.text(2.34, 3.10, "control", size=6.8, color=GREY,
            ha="right", bold=True)
    for xc, lab in COLS:
        sc.text(xc, 3.10, lab, size=6.8, color=GREY, ha="center", lead=1.30)
    for k, (yy, lab, marks) in enumerate(ROWS):
        if k % 2 == 0:
            sc.rect(0.86, yy - 0.082, 4.94, 0.164, fill="#F5F7F8", z=0)
        sc.text(2.34, yy, lab, size=7.2, color=INK, ha="right")
        for (xc, _), m in zip(COLS, marks):
            if m == "v":
                G.tick(sc, xc, yy)
            elif m == "x":
                G.cross(sc, xc, yy)
            else:
                G.query(sc, xc, yy)
    sc.line(0.86, 2.98, 5.80, 2.98, color=HAIR, lw=0.8, z=1)
    sc.rect(2.44, 2.03, 2.28, 0.90, fill=None, line=PAL["phy"][1], lw=0.9,
            dash="--", radius=0.03, z=1)
    sc.text(3.58, 1.99, "no axis, no choice: a drive that commutes with the "
            "120\u00b0 rotation cannot select", size=6.6,
            color=PAL["phy"][2], ha="center", va="top")

    # ---------------------------------------------- control plane
    _group(sc, 0.14, 0.16, W - 0.28, 1.72, "ctl", "CONTROL PLANE",
           "what the probe can do")
    PANELS = [("c", "uniform DC", "no axis of its own"),
              ("d", "DC + motion", "trailing field"),
              ("e", "AC bias", "flips the OP sign"),
              ("f", "pulse lattice", "structured, alternating")]
    for k, (lt, ttl, key) in enumerate(PANELS):
        x0 = 0.30 + k * 1.545
        sc.rect(x0, 0.30, 1.42, 1.06, fill="#FFFFFF", line=PAL["ctl"][1],
                lw=0.9, radius=0.045, z=2)
        sc.text(x0 + 0.06, 1.28, lt, size=8.2, color=INK, bold=True, z=6)
        sc.text(x0 + 1.42 / 2, 1.28, ttl, size=7.8, color=CT_, bold=True,
                ha="center", z=6)
        sc.text(x0 + 1.42 / 2, 0.40, key, size=6.8, color=GREY, ha="center",
                z=6)
        m = x0 + 1.42 / 2
        if k < 3:
            sc.line(m - 0.50, 0.66, m + 0.50, 0.66, color="#D8C79E", lw=2.4,
                    z=3)
        if k == 0:
            for sx in (-0.30, 0.0, 0.30):
                sc.arrow(m + sx, 1.08, m + sx, 0.74, color="#9FB0BC", lw=1.4,
                         z=5)
        elif k == 1:
            G.cantilever(sc, m - 0.10, 0.68, 0.40, col="#4A4335", z=6)
            sc.arrow(m + 0.06, 1.02, m + 0.44, 1.02, color=CT_, lw=1.5, z=7)
            for sx in (0.16, 0.30, 0.44):
                sc.arrow(m - sx, 0.62, m - sx + 0.09, 0.53, color=PAL["res"][2],
                         lw=0.9, z=5)
        elif k == 2:
            G.cantilever(sc, m - 0.08, 0.68, 0.38, col="#4A4335", z=6)
            tt = np.linspace(0, 1, 42)
            xs = m + 0.10 + 0.30 * tt
            ys = 1.00 + 0.045 * np.sin(6 * np.pi * tt)
            for q in range(len(tt) - 1):
                sc.line(xs[q], ys[q], xs[q + 1], ys[q + 1],
                        color=PAL["hyp"][2], lw=1.1, z=7)
            sc.arrow(m - 0.26, 0.60, m - 0.26, 0.48, color=PAL["hyp"][2],
                     lw=1.3, z=5)
            sc.arrow(m + 0.10, 0.48, m + 0.10, 0.60, color=PAL["hyp"][2],
                     lw=1.3, z=5)
        else:
            sc.rect(m - 0.44, 0.54, 0.88, 0.62, fill="#FCFCFD", line="#D8DEE4",
                    lw=0.8, z=3)
            R2 = _rot(np.deg2rad(22.0))
            for iy in range(4):
                for ix in range(4):
                    p = R2 @ np.array([(ix - 1.5) * 0.125,
                                       (iy - 1.5) * 0.125])
                    sc.ellipse(m + p[0], 0.85 + p[1], 0.026,
                               fill=PAL["hum"][2] if iy % 2 == 0
                               else PAL["exp"][2], z=6)
            sc.arrow(m - 0.34, 0.85 - 0.34 * np.tan(np.deg2rad(22)),
                     m + 0.34, 0.85 + 0.34 * np.tan(np.deg2rad(22)),
                     color=PAL["hum"][2], lw=1.3, z=7)
    return sc


# ===================================================== Figure 2
def fig2():
    """The cycle, drawn as three groups: the supervised campaign, the shared
    memory, the autonomous campaign, with the triage as its own panel."""
    HF = 5.66
    sc = Scene(W, HF)
    AW2, BW2, CW2 = 1.94, 2.06, 1.94
    AX2, BX2, CX2 = 0.14, 2.32, 4.62
    TOP2, ABOT = 5.24, 2.28

    # ---------------- group shells
    _group(sc, AX2, ABOT, AW2, TOP2 - ABOT, "hum", "CAMPAIGN 1",
           "operator supervises")
    _group(sc, CX2, ABOT, CW2, TOP2 - ABOT, "exp", "CAMPAIGN 2",
           "agent drives")
    sc.text(AX2 - 0.10, TOP2 + 0.10, "a", size=9.4, color=INK, bold=True)
    G.person(sc, AX2 + AW2 - 0.20, TOP2 - 0.22, s=1.0, col=PAL["hum"][1])
    G.chip(sc, CX2 + CW2 - 0.20, TOP2 - 0.22, s=1.0, col=PAL["exp"][1])

    # The two columns are the SAME seven steps. Only the actor at steps 1, 4
    # and 7 changes, which is the whole point of the figure, so the rows are
    # laid out on a shared grid and the reader can read across.
    ROWS1 = [("hum", "read the papers", "what is already known"),
             ("hyp", "propose a mechanism", "and what it predicts"),
             ("exp", "design the write", "pattern, dose, controls"),
             ("hum", "operator checks it", "controls? safe? fresh area?"),
             ("ins", "write and image", None),
             ("res", "measure the change", "domain populations"),
             ("hum", "operator checks that", "right quantity? artefact?")]
    ROWS2 = [("hum", "operator gives a target", "but no recipe"),
             ("hyp", "propose a mechanism", "and what would disprove it"),
             ("exp", "design the write", "predict both outcomes"),
             ("exp", "checks run first", "any failure blocks the write"),
             ("ins", "write and image", None),
             ("res", "measure the change", "against an untouched area"),
             ("exp", "keep going, or stop", "and record why")]

    # a shared row grid, so step k lines up across the two columns
    RH, RHP, RGAP = 0.28, 0.22, 0.075
    ROWY, yy = [], TOP2 - 0.46
    for k in range(7):
        h = RHP if k == 4 else RH
        ROWY.append((yy, h))
        yy -= h + RGAP

    def stack(x, w, rows):
        for k, ((key, head, sub), (ytop_k, h)) in enumerate(zip(rows, ROWY)):
            _card(sc, x + 0.10, ytop_k - h, w - 0.20, h, key, head, sub,
                  hs=7.2, ss=6.5)
            if k < len(rows) - 1:
                sc.arrow(x + w / 2, ytop_k - h, x + w / 2,
                         ROWY[k + 1][0], color="#A9B4BC", lw=1.1, z=4)

    stack(AX2, AW2, ROWS1)
    stack(CX2, CW2, ROWS2)

    sc.text(W / 2, ABOT - 0.06, "the same seven steps: the operator's two "
            "checks become the agent's own", size=7.2, color=GREY,
            ha="center", va="top", italic=True)

    # ---------------- the shared memory
    MT, MB = TOP2 - 0.02, ABOT + 0.02
    sc.rect(BX2, MB, BW2, MT - MB, fill=PAL["mem"][0], line=PAL["mem"][1],
            lw=1.0, radius=0.07, z=0)
    sc.text(BX2 + BW2 / 2, MT - 0.15, "PERSISTENT MEMORY", size=9.2,
            color=PAL["mem"][2], bold=True, ha="center", z=5)
    sc.text(BX2 + BW2 / 2, MT - 0.31, "carried across both campaigns",
            size=7.2, color=PAL["mem"][2], ha="center", italic=True, z=5)
    G.document(sc, BX2 + 0.24, MT - 1.16, BW2 - 0.48, 0.66, "#FFFFFF",
               PAL["mem"][2], "FINDINGS.md", "what we know", lw=1.0)
    G.document(sc, BX2 + 0.24, MT - 1.94, BW2 - 0.48, 0.66, "#FFFFFF",
               PAL["phy"][2], "PITFALLS.md", "how we were wrong", lw=1.0)
    sc.text(BX2 + BW2 / 2, MT - 2.06, "28  \u2192  54 findings", size=7.6,
            color=PAL["mem"][2], ha="center", va="top", bold=True, z=5)
    sc.text(BX2 + BW2 / 2, MT - 2.22, "each graded A, B or C", size=6.8,
            color=GREY, ha="center", va="top", z=5)

    ymem = [ROWY[1][0] - ROWY[1][1] / 2, ROWY[5][0] - ROWY[5][1] / 2]
    for k, ym in enumerate(ymem):
        sc.arrow(AX2 + AW2 - 0.02, ym, BX2 + 0.02, ym, color=PAL["mem"][2],
                 lw=1.3, z=5)
        sc.arrow(BX2 + BW2 - 0.02, ym, CX2 + 0.02, ym, color=PAL["mem"][2],
                 lw=1.3, z=5)
        if k == 0:
            sc.text((AX2 + AW2 + BX2) / 2, ym + 0.05, "write", size=6.4,
                    color=PAL["mem"][2], ha="center", va="bottom", z=6)
            sc.text((BX2 + BW2 + CX2) / 2, ym + 0.05, "read", size=6.4,
                    color=PAL["mem"][2], ha="center", va="bottom", z=6)
    ylast = ROWY[6][0] - ROWY[6][1] / 2
    sc.arrow(CX2 + 0.02, ylast, BX2 + BW2 - 0.02, ylast, color=PAL["mem"][2],
             lw=1.3, z=5)
    sc.text((BX2 + BW2 + CX2) / 2, ylast + 0.05, "write back", size=6.4,
            color=PAL["mem"][2], ha="center", va="bottom", z=6)

    # ---------------- the triage panel
    sc.line(0.14, 2.06, W - 0.14, 2.06, color=HAIR, lw=0.9, dash="--", z=1)
    sc.text(0.04, 1.88, "b", size=9.4, color=INK, bold=True)
    sc.text(0.26, 1.88, "when a result looks surprising", size=8.8,
            color=INK, bold=True)
    sc.text(2.62, 1.88, "rule out the measurement before believing the "
            "material", size=7.2, color=GREY, italic=True)
    TY2, TH2 = 1.62, 0.30
    _card(sc, 0.14, TY2 - TH2, 1.02, TH2, "res", "surprise", None, hs=7.4)
    xs2 = []
    for k, nm in enumerate(("the tip", "the sample", "the microscope",
                            "the analysis")):
        x0 = 1.42 + k * 1.20
        xs2.append(x0 + 0.50)
        _card(sc, x0, TY2 - TH2, 1.00, TH2, "exp", nm, None, hs=7.4)
        prev = 1.16 if k == 0 else 1.42 + (k - 1) * 1.20 + 1.00
        sc.arrow(prev + 0.03, TY2 - TH2 / 2, x0 - 0.03, TY2 - TH2 / 2,
                 color=PAL["res"][2] if k == 0 else "#A9B4BC", lw=1.1, z=4)
    BUS2, OT2 = 1.06, 0.80
    for x0 in xs2:
        sc.line(x0, TY2 - TH2, x0, BUS2, color="#A9B4BC", lw=0.8, z=3)
    sc.line(xs2[0], BUS2, xs2[-1], BUS2, color="#A9B4BC", lw=1.0, z=3)
    sc.line(xs2[0], BUS2, 1.02, BUS2, color=PAL["phy"][2], lw=1.2, z=3)
    sc.arrow(1.02, BUS2, 1.02, OT2, color=PAL["phy"][2], lw=1.2, z=3)
    sc.text(1.08, BUS2 + 0.03, "one of them moved", size=6.6,
            color=PAL["phy"][2], va="bottom")
    sc.line(xs2[-1], BUS2, xs2[-1], 0.94, color=PAL["mem"][2], lw=1.2, z=3)
    sc.line(xs2[-1], 0.94, 3.96, 0.94, color=PAL["mem"][2], lw=1.2, z=3)
    sc.arrow(3.96, 0.94, 3.96, OT2, color=PAL["mem"][2], lw=1.2, z=3)
    sc.text(4.62, 0.90, "none of them moved", size=6.6,
            color=PAL["mem"][2], va="top")
    G.document(sc, 0.14, OT2 - 0.52, 2.34, 0.52, PAL["phy"][0],
               PAL["phy"][2], "a measurement artefact",
               "write it into PITFALLS.md", fold=0.09)
    G.document(sc, 2.86, OT2 - 0.52, 2.34, 0.52, PAL["mem"][0],
               PAL["mem"][2], "a real effect", "update FINDINGS.md",
               fold=0.09)
    sc.text(5.32, OT2 - 0.26, "the old entry stays,\nmarked superseded",
            size=6.6, color=GREY, ha="left", lead=1.36)

    # ---------------- legend
    LG = [("memory", "mem"), ("human", "hum"), ("hypothesis", "hyp"),
          ("experiment", "exp"), ("result", "res"), ("instrument", "ins")]
    x = 0.14
    for lab, key in LG:
        fill, stroke, ink = PAL[key]
        sc.rect(x, HF - 0.19, 0.15, 0.105, fill=fill, line=stroke, lw=0.9,
                radius=0.02, z=5)
        sc.text(x + 0.20, HF - 0.138, lab, size=7.2, color=ink, z=6)
        x += 0.20 + 0.0455 * len(lab) + 0.20
    return sc
