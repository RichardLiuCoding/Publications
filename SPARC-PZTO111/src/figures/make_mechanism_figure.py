# -*- coding: utf-8 -*-
"""The symmetry and energy-landscape figure.

Panel b is drawn from the measured triad and the measured acceptance window;
panels a and c are schematics of the argument the measurements constrain.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle
from pathlib import Path

import publication_style as ps

OUT = Path('figures_ms')
TRI = (18.2, 78.2, 138.2)          # the measured film-wide triad
INK, GREY, RED, BLUE, TEAL = '#12293F', '#5E6873', '#C0392B', '#2B6CB0', '#2A9D8F'


def bare(ax):
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect('equal')
    for s in ax.spines.values():
        s.set_visible(False)


def letter(ax, s, x=-0.02):
    ax.text(x, 1.04, s, transform=ax.transAxes, fontsize=9.6,
            fontweight='bold', va='bottom', ha='left')


def main():
    fig = plt.figure(figsize=(6.9, 2.62))
    gs = fig.add_gridspec(1, 3, left=0.045, right=0.988, bottom=0.175,
                          top=0.845, width_ratios=[1.02, 1.16, 1.02],
                          wspace=0.30)

    # ---------------- a: what a drive must not commute with
    ax = fig.add_subplot(gs[0, 0]); bare(ax)
    ax.set_xlim(-1.20, 1.20); ax.set_ylim(-1.30, 1.10)
    for k, t in enumerate(TRI):
        r = np.deg2rad(t)
        ax.plot([-np.cos(r), np.cos(r)], [-np.sin(r), np.sin(r)], lw=2.6,
                color=(BLUE, TEAL, RED)[k], solid_capstyle='round', zorder=3)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec='#C8D2D8', lw=0.9))
    ax.annotate('', xy=(0.60, 0.86), xytext=(0.16, 0.98),
                arrowprops=dict(arrowstyle='-|>', lw=1.2, color=GREY,
                                connectionstyle='arc3,rad=0.42'))
    ax.text(0.52, 1.00, r'$C_3$', fontsize=8.6, color=GREY, ha='center')
    # a uniform field: invariant, so it cannot choose
    ax.text(-1.14, -0.72, 'uniform field', fontsize=7.6, color=GREY, ha='left')
    for dx in (-0.86, -0.60, -0.34):
        ax.add_patch(FancyArrowPatch((dx, -0.84), (dx, -1.10),
                                     arrowstyle='-|>', mutation_scale=7,
                                     lw=1.1, color=GREY, shrinkA=0, shrinkB=0))
    ax.text(-0.60, -1.24, 'commutes with $C_3$\ncannot select', fontsize=7.0,
            color=GREY, ha='center', va='top', linespacing=1.3)
    # a structured drive: carries an axis
    ax.text(0.16, -0.72, 'raster axis', fontsize=7.6, color=RED, ha='left')
    for dy in (-0.86, -0.96, -1.06):
        ax.add_patch(FancyArrowPatch((0.16, dy), (1.06, dy), arrowstyle='-|>',
                                     mutation_scale=7, lw=1.1, color=RED,
                                     shrinkA=0, shrinkB=0))
    ax.text(0.61, -1.24, 'breaks $C_3$\nselects', fontsize=7.0, color=RED,
            ha='center', va='top', linespacing=1.3)
    letter(ax, 'a')
    ax.text(0.5, 1.045, 'the symmetry constraint', transform=ax.transAxes,
            ha='center', va='bottom', fontsize=8.4, color=INK)

    # ---------------- b: the landscape, tilted by the write
    ax = fig.add_subplot(gs[0, 1])
    phi = np.linspace(-25, 205, 900)
    # three minima 60 deg apart in an axis coordinate, so 6 theta
    base = -np.cos(np.deg2rad(6 * (phi - TRI[0])))
    axis_deg = TRI[1]                                  # a raster along member 2
    tilt = -0.55 * np.cos(np.deg2rad(2 * (phi - axis_deg)))
    ax.plot(phi, base, lw=1.8, color=GREY, ls='--', label='no write')
    ax.plot(phi, base + tilt, lw=2.2, color=RED,
            label='raster along an axis')
    for t in TRI:
        ax.axvline(t, color='#E2E8EC', lw=0.9, zorder=0)
    ax.axvspan(axis_deg - 30, axis_deg + 30, color=RED, alpha=0.07, lw=0)
    ax.annotate('', xy=(axis_deg - 28, -2.02), xytext=(axis_deg + 28, -2.02),
                arrowprops=dict(arrowstyle='<|-|>', lw=0.9, color=RED))
    ax.text(axis_deg, -1.92, r'$\pm30\degree$ acceptance', fontsize=7.0,
            color=RED, ha='center', va='bottom')
    ax.plot(axis_deg, min(base + tilt), marker='v', ms=6.0, mfc=RED,
            mec='none', zorder=5)
    ax.set_xlim(-25, 205); ax.set_ylim(-2.25, 1.85)
    ax.set_xticks(list(TRI))
    ax.set_xticklabels(['%.0f' % t for t in TRI], fontsize=8.0)
    ax.set_yticks([])
    ax.set_xlabel(r'in-plane director ($\degree$)')
    ax.set_ylabel('free energy (a.u.)')
    ps.boxed_legend(ax, loc='upper right', fontsize=6.8, handlelength=1.1,
                    borderpad=0.26, labelspacing=0.22)
    ps.close_frame(ax)
    letter(ax, 'b')
    ax.text(0.5, 1.045, 'the write tilts the landscape',
            transform=ax.transAxes, ha='center', va='bottom', fontsize=8.4,
            color=INK)

    # ---------------- c: replacement, not rotation
    ax = fig.add_subplot(gs[0, 2]); bare(ax)
    ax.set_xlim(-0.08, 1.08); ax.set_ylim(-0.30, 1.06)
    for row, (lab, col) in enumerate((('rotation', GREY),
                                      ('replacement', RED))):
        y = 0.74 - row * 0.46
        ax.text(-0.04, y + 0.20, lab, fontsize=7.8, color=col, ha='left')
        for k, f in enumerate((0.0, 0.5, 1.0)):
            x = 0.10 + k * 0.34
            ax.add_patch(Rectangle((x, y - 0.10), 0.24, 0.28, fill=False,
                                   ec='#B9C6CE', lw=0.8))
            if row == 0:                       # continuous rotation
                a = np.deg2rad(90 - 60 * f)
                for q in (-0.06, 0.0, 0.06):
                    ax.plot([x + 0.12 - 0.08 * np.cos(a) + q,
                             x + 0.12 + 0.08 * np.cos(a) + q],
                            [y + 0.04 - 0.08 * np.sin(a),
                             y + 0.04 + 0.08 * np.sin(a)],
                            lw=1.3, color=col)
            else:                              # two populations, mixing
                nb = int(round(3 * (1 - f)))
                for q, ang in zip((-0.07, 0.0, 0.07),
                                  [90] * nb + [30] * (3 - nb)):
                    a = np.deg2rad(ang)
                    ax.plot([x + 0.12 - 0.075 * np.cos(a) + q,
                             x + 0.12 + 0.075 * np.cos(a) + q],
                            [y + 0.04 - 0.075 * np.sin(a),
                             y + 0.04 + 0.075 * np.sin(a)],
                            lw=1.3, color=col if ang == 30 else GREY)
            if k < 2:
                ax.add_patch(FancyArrowPatch((x + 0.26, y + 0.04),
                                             (x + 0.32, y + 0.04),
                                             arrowstyle='-|>',
                                             mutation_scale=6, lw=0.9,
                                             color='#A9B4BC', shrinkA=0,
                                             shrinkB=0))
    ax.text(0.5, -0.12, 'an incomplete write is seen at\nreduced order, not at an '
            'intermediate angle', fontsize=7.0, color=INK, ha='center',
            va='top', linespacing=1.34)
    letter(ax, 'c')
    ax.text(0.5, 1.045, 'incomplete writes',
            transform=ax.transAxes, ha='center', va='bottom', fontsize=8.4,
            color=INK)

    ps.save_figure(fig, OUT, 'F6_mechanism', formats=('png', 'pdf', 'svg'),
                   pad_inches=0.02)
    print('mechanism figure written')


if __name__ == '__main__':
    main()
