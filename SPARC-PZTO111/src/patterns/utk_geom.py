# -*- coding: utf-8 -*-
"""The IT10b letter geometry, copied verbatim from run_it10.py.

Kept in its own module so the manuscript figure and the offline check use the
same mask the instrument was actually sent, not a redrawn approximation.
"""
import numpy as np

LET_H, LET_W, STROKE, LET_GAP = 2.6, 2.4, 1.2, 1.2
FRAME, WORD_ANG = 12.0, 62.0
TRIAD = [2.0, 62.0, 122.0]
CMD, BG = 2.0, 62.0
WIN = 1.219
BEFORE, AFTER = "PZTO_LDART_0125.ibw", "PZTO_LDART_0126.ibw"
TOTAL_W = 3 * LET_W + 2 * LET_GAP
LAYOUT = [(ch, i * (LET_W + LET_GAP), LET_W, LET_H)
          for i, ch in enumerate("UTK")]


def letter_segments(ch, w, h):
    if ch == 'U':
        return [((0.0, h), (0.0, 0.0)), ((w, h), (w, 0.0)),
                ((0.0, 0.0), (w, 0.0))]
    if ch == 'T':
        return [((0.0, h), (w, h)), ((w / 2, h), (w / 2, 0.0))]
    if ch == 'K':
        return [((0.0, h), (0.0, 0.0)),
                ((0.0, h / 2), (w, h)), ((0.0, h / 2), (w, 0.0))]
    raise ValueError(ch)


def word_frame(phi_deg=WORD_ANG, total_w=TOTAL_W, let_h=LET_H, frame=FRAME):
    t = np.deg2rad(phi_deg)
    e1 = np.array([np.cos(t), np.sin(t)])
    e2 = np.array([-np.sin(t), np.cos(t)])
    O = np.array([frame / 2.0, frame / 2.0]) - e1 * (total_w / 2.0) \
        - e2 * (let_h / 2.0)
    return O, e1, e2


def in_letter(px, py, segs, sw=STROKE):
    r = sw / 2.0
    for (x0, y0), (x1, y1) in segs:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else ((px - x0) * dx + (py - y0) * dy) / L2
        t = min(1.0, max(0.0, t))
        if (px - (x0 + t * dx)) ** 2 + (py - (y0 + t * dy)) ** 2 <= r * r:
            return True
    return False


def hit_word(px, py, O=None, e1=None, e2=None, sw=STROKE):
    if O is None:
        O, e1, e2 = word_frame()
    d = np.array([px, py]) - O
    a, b = float(d @ e1), float(d @ e2)
    for (ch, x0, w, h) in LAYOUT:
        if in_letter(a - x0, b, letter_segments(ch, w, h), sw):
            return True
    return False


def stroke_lines():
    """Every stroke centre-line, in scan-frame micrometres."""
    O, e1, e2 = word_frame()
    out = []
    for (ch, x0, w, h) in LAYOUT:
        for (p0, p1) in letter_segments(ch, w, h):
            a = O + (x0 + p0[0]) * e1 + p0[1] * e2
            b = O + (x0 + p1[0]) * e1 + p1[1] * e2
            out.append((a, b))
    return out
