# -*- coding: utf-8 -*-
"""Small icon glyphs, built from Scene primitives so they stay native shapes.

Modelled on the visual grammar of the recent Nature agentic-science figures:
a person silhouette for the human, a chip badge for the agent, a document for
a persistent file, and a cantilever for the instrument.
"""
import numpy as np


def person(sc, cx, cy, s=1.0, col="#7E8B99", z=6):
    """Head and shoulders, the scientist glyph."""
    sc.ellipse(cx, cy + 0.055 * s, 0.038 * s, fill=col, z=z)
    sc.poly([(cx - 0.072 * s, cy - 0.058 * s),
             (cx - 0.058 * s, cy - 0.002 * s),
             (cx - 0.020 * s, cy + 0.018 * s),
             (cx + 0.020 * s, cy + 0.018 * s),
             (cx + 0.058 * s, cy - 0.002 * s),
             (cx + 0.072 * s, cy - 0.058 * s)], fill=col, z=z)


def chip(sc, cx, cy, s=1.0, col="#7E8B99", label="AI", z=6):
    """A small processor badge, the agent glyph."""
    w, h = 0.150 * s, 0.110 * s
    sc.rect(cx - w / 2, cy - h / 2, w, h, fill="#FFFFFF", line=col, lw=1.0,
            radius=0.018 * s, z=z)
    for k in (-1, 0, 1):
        sc.line(cx + k * 0.040 * s, cy + h / 2, cx + k * 0.040 * s,
                cy + h / 2 + 0.030 * s, color=col, lw=0.8, z=z)
        sc.line(cx + k * 0.040 * s, cy - h / 2, cx + k * 0.040 * s,
                cy - h / 2 - 0.030 * s, color=col, lw=0.8, z=z)
    sc.text(cx, cy, label, size=5.6 * s, color=col, bold=True, ha="center",
            z=z + 1)


def document(sc, x, y, w, h, fill, line, label=None, sub=None, lw=1.0,
             fold=0.13, z=4):
    """A file with a folded corner, plus its name and one keyword line."""
    sc.poly([(x, y), (x + w, y), (x + w, y + h - fold * h),
             (x + w - fold * w, y + h), (x, y + h)],
            fill=fill, line=line, lw=lw, z=z)
    sc.line(x + w - fold * w, y + h, x + w - fold * w, y + h - fold * h,
            color=line, lw=lw * 0.8, z=z + 1)
    sc.line(x + w - fold * w, y + h - fold * h, x + w, y + h - fold * h,
            color=line, lw=lw * 0.8, z=z + 1)
    if label:
        sc.text(x + w / 2, y + h * 0.62, label, size=7.4, color=line,
                bold=True, ha="center", z=z + 2)
    if sub:
        sc.text(x + w / 2, y + h * 0.30, sub, size=6.6, color="#5E6873",
                ha="center", z=z + 2)


def cantilever(sc, tipx, tipy, length=0.46, col="#4A4335", z=6, flip=False):
    """A cantilever beam with a tip, pointing down at (tipx, tipy)."""
    d = -1.0 if flip else 1.0
    sc.poly([(tipx - d * 0.046, tipy + 0.118), (tipx + d * length, tipy + 0.175),
             (tipx + d * length, tipy + 0.225),
             (tipx - d * 0.046, tipy + 0.168)], fill=col, z=z)
    sc.poly([(tipx - 0.048, tipy + 0.140), (tipx + 0.048, tipy + 0.140),
             (tipx, tipy)], fill=col, z=z)


def tick(sc, cx, cy, s=0.052, col="#2A9D8F", lw=1.7, z=6):
    sc.line(cx - s, cy + 0.10 * s, cx - 0.20 * s, cy - 0.72 * s, color=col,
            lw=lw, z=z)
    sc.line(cx - 0.20 * s, cy - 0.72 * s, cx + s, cy + 0.86 * s, color=col,
            lw=lw, z=z)


def cross(sc, cx, cy, s=0.048, col="#C0562F", lw=1.7, z=6):
    sc.line(cx - s, cy - s, cx + s, cy + s, color=col, lw=lw, z=z)
    sc.line(cx - s, cy + s, cx + s, cy - s, color=col, lw=lw, z=z)


def query(sc, cx, cy, col="#C99A22", size=9.0, z=6):
    sc.text(cx, cy, "?", size=size, color=col, bold=True, ha="center",
            va="center", z=z)
