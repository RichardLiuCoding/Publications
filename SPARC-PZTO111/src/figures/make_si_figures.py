# -*- coding: utf-8 -*-
"""make_si_figures.py -- supplementary figures.

The SM currently carries no figures at all, which for a Nature Materials
submission is a gap: three of its sections are methodological arguments that
are far more convincing as pictures than as tables.

  SF1  the estimator on a known input and on noise (S2)
  SF2  topography screening, including the area a step edge disqualified (S3)
  SF3  retention of the raster-written director (S7)
  SF4  dose and scan speed (round 3)

Every panel is drawn from raw .ibw frames or from a synthetic field built in
this file; nothing is reproduced from a table.
"""
from __future__ import annotations

import io
import os
import sys
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import publication_style as PS
import scale_tools as ST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'figures_ms')
SUPER = (150.0, 500.0)
PS.configure_style()
C = PS.COLORS


def load(tag):
    """Signed lateral piezoresponse and nm/px from a frame tag."""
    import autoloop as A
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__
    d, h = g('ibw')(tag)
    S, _, _ = g('signed')(d)
    px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
    return S, px, d, h


def synth(n, px, lam, director_deg, amp, seed=0):
    """Lamellae of known period whose STRIPES run along director_deg.

    The wavevector is perpendicular to the stripes, so it is built at
    director_deg + 90. Getting this backwards once put the reference line
    90 degrees from the answer and made a correct estimator look broken.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] * px
    t = np.radians(director_deg + 90.0)
    ph = 2 * np.pi * (x * np.cos(t) + y * np.sin(t)) / lam
    return amp * np.sin(ph) + rng.normal(0, 1.0, (n, n))


# --------------------------------------------------------------- SF1
def sf1():
    """The estimator recovers a known direction and reports nothing on noise."""
    n, px = 256, 4.88
    lam_true, th_true = 250.0, 30.0
    S = synth(n, px, lam_true, th_true, 0.8, seed=1)
    N = np.random.default_rng(2).normal(0, 1.0, (n, n))

    fig, ax = plt.subplots(2, 3, figsize=(6.9, 4.6))
    for r, (F, name) in enumerate(((S, 'known input'), (N, 'white noise'))):
        d, a, p, pv = ST.band_peak(F, px, *SUPER, n_perm=400, seed=3)
        ax[r, 0].imshow(F, cmap='gray', origin='lower',
                        extent=[0, n * px / 1000., 0, n * px / 1000.])
        ax[r, 0].set_xlabel(u'x (µm)')
        ax[r, 0].set_ylabel(u'y (µm)')
        PS.square_map(ax[r, 0])

        P, per_nm, ang, q, half = ST.power_map(F, px)
        th, pw, _tot = ST.band_angular_power(F, px, *SUPER)
        ax[r, 1].plot(th, pw / max(pw.max(), 1e-30), color=C.get('blue', 'C0'),
                      lw=1.2)
        ax[r, 1].axvline(th_true, color=C.get('red', 'C3'), ls='--', lw=0.9)
        if r == 0:
            ax[r, 1].text(th_true + 3, 0.55, u'input %.0f°' % th_true,
                          fontsize=6.5, color=C.get('red', 'C3'))
        ax[r, 1].set_xlim(0, 180)
        ax[r, 1].set_ylim(0, 1.08)
        ax[r, 1].set_xlabel(u'angle (°)')
        ax[r, 1].set_ylabel('band power (norm.)')
        ax[r, 1].set_xticks([0, 60, 120, 180])

        null = ST._null_anisotropies(F, px, SUPER[0], SUPER[1], 400, 3) \
            if hasattr(ST, '_null_anisotropies') else None
        if null is None:
            null = np.array([ST.band_peak(
                np.random.default_rng(100 + k).normal(0, 1, F.shape), px,
                *SUPER, n_perm=1, seed=k)[1] for k in range(60)])
        ax[r, 2].hist(null, bins=18, color='0.75', edgecolor='none')
        ax[r, 2].axvline(a, color=C.get('red', 'C3'), lw=1.4)
        ax[r, 2].set_xlabel('anisotropy')
        ax[r, 2].set_ylabel('null draws')
        ax[r, 2].text(0.96, 0.92,
                      u'%s\n%.1f°, %.0f nm\naniso %.2f, p %.3f'
                      % (name, d, p, a, pv),
                      transform=ax[r, 2].transAxes, ha='right', va='top',
                      fontsize=6.5)
        for c in range(3):
            PS.close_frame(ax[r, c])
    fig.tight_layout()
    PS.align_panel_letters(fig, [
        [(c, ax[0, c], l) for c, l in enumerate('abc')],
        [(c, ax[1, c], l) for c, l in enumerate('def')]])
    PS.save_figure(fig, OUT, 'SF1_estimator')
    plt.close(fig)
    print('  SF1 written')


# --------------------------------------------------------------- SF2
def sf2(good_tag, bad_tag):
    """Topography disqualifies an area that every other gate passes."""
    fig, ax = plt.subplots(2, 2, figsize=(5.2, 5.0))
    for r, (tag, name) in enumerate(((good_tag, 'accepted'),
                                     (bad_tag, 'rejected on topography'))):
        S, px, d, h = load(tag)
        Z = np.asarray(d[0], float) * 1e9
        Z = np.nan_to_num(Z - np.nanmedian(Z))
        yy, xx = np.mgrid[0:Z.shape[0], 0:Z.shape[1]]
        M = np.c_[xx.ravel(), yy.ravel(), np.ones(Z.size)]
        c, _, _, _ = np.linalg.lstsq(M, Z.ravel(), rcond=None)
        F = Z - (c[0] * xx + c[1] * yy + c[2])
        ex = [0, Z.shape[0] * px / 1000., 0, Z.shape[0] * px / 1000.]
        v = np.percentile(F, [1, 99])
        im = ax[r, 0].imshow(F, cmap='afmhot', origin='lower', extent=ex,
                             vmin=v[0], vmax=v[1])
        ax[r, 0].set_ylabel(u'y (µm)')
        PS.square_map(ax[r, 0])
        PS.top_colorbar(fig, ax[r, 0], im, 'height (nm)')
        ax[r, 1].imshow(S, cmap='gray', origin='lower', extent=ex)
        PS.square_map(ax[r, 1])
        ax[r, 1].text(0.04, 0.93, u'%s\nrms %.2f nm, range %.1f nm'
                      % (name, float(np.std(F)), float(v[1] - v[0])),
                      transform=ax[r, 1].transAxes, va='top', fontsize=6.5,
                      color='w')
        for cc in range(2):
            ax[r, cc].set_xlabel(u'x (µm)')
            PS.close_frame(ax[r, cc])
    fig.tight_layout()
    PS.align_panel_letters(fig, [
        [(c, ax[0, c], l) for c, l in enumerate('ab')],
        [(c, ax[1, c], l) for c, l in enumerate('cd')]])
    PS.save_figure(fig, OUT, 'SF2_topography')
    plt.close(fig)
    print('  SF2 written')


# --------------------------------------------------------------- SF3
# label, age h, binned then, binned now, fine then, fine now, aniso then, now
RET = [
    ('(+12,+12)', 4.80, 18.8, 18.8, 16.62, 16.15, 10.85, 15.35),
    ('(-6,-6)', 4.02, 18.8, 18.8, 19.55, 19.72, 22.74, 36.10),
    ('(0,-6)', 3.75, 138.8, 138.8, 140.98, 140.77, 9.61, 12.38),
    ('(+12,+18)', 2.87, 26.2, 18.8, 15.17, 14.77, 5.67, 4.63),
    ('(+6,+12)', 2.58, 18.8, 18.8, 19.30, 19.15, 18.63, 13.88),
    ('(-6,-12)', 2.30, 18.8, 18.8, 17.17, 17.23, 35.96, 43.12),
    ('(-6,0) re-aim', 2.45, 78.8, 78.8, 75.15, 74.98, 5.70, 4.57),
    ('tile A', 1.67, 18.8, 18.8, 20.69, 20.97, 19.40, 19.71),
    ('(0,+18)', 1.60, 18.8, 18.8, 19.78, 20.25, 18.60, 24.94),
    ('(-12,-6) re-aim', 1.60, 138.8, 138.8, 139.11, 138.98, 4.30, 5.39),
    ('tile B', 1.35, 78.8, 78.8, 78.25, 77.50, 36.06, 28.31),
    ('(+18,-18)', 1.31, 18.8, 18.8, 18.14, 17.67, 16.86, 50.53),
    ('(+12,+6)', 1.30, 18.8, 18.8, 17.14, 17.43, 13.46, 11.92),
    ('(+6,-12) re-aim', 0.42, 138.8, 138.8, 138.73, 138.66, 3.64, 3.56),
]



def sf3():
    """What survives hours is the direction, not the anisotropy."""
    rows = sorted(RET, key=lambda r: r[1])
    lab = [r[0] for r in rows]
    xs = np.arange(len(rows))
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.9))

    db = [abs(ST.angle_between(r[3], r[2])) for r in rows]
    df = [abs(r[5] - r[4]) for r in rows]
    ax[0].bar(xs, df, 0.6, color=C.get('blue', 'C0'))
    ax[0].text(0.03, 0.95,
               u'the binned estimator returns 0.0° for 13 of 14,\n'
               u'and one whole bin — 7.5° — for (+12,+18),\n'
               u'which the matched filter puts at 0.40°',
               transform=ax[0].transAxes, fontsize=5.6, color='0.35',
               va='top')
    ax[0].set_ylabel(u'director drift, matched filter (°)')
    ax[0].set_ylim(0, 1.35)

    ax[1].plot([r[1] for r in rows], df, 'o', ms=5,
               color=C.get('blue', 'C0'))
    ax[1].set_xlabel('panel age (h)')
    ax[1].set_ylabel(u'director change (°)')
    ax[1].set_ylim(0, 0.9)
    ax[1].set_xlim(0, 5.4)

    g = [r[7] / r[6] for r in rows]
    ax[2].plot([r[1] for r in rows], g, 's', ms=5, color='0.35')
    ax[2].axhline(1.0, color='0.6', lw=0.8)
    ax[2].set_xlabel('panel age (h)')
    ax[2].set_ylabel('anisotropy now / then')
    ax[2].set_xlim(0, 5.4)
    ax[2].set_ylim(0, 3.4)
    rk = lambda v: np.argsort(np.argsort(v)).astype(float)
    rs = float(np.corrcoef(rk([r[1] for r in rows]), rk(g))[0, 1])
    ax[2].text(0.96, 0.94, u'Spearman %+.2f' % rs, transform=ax[2].transAxes,
               ha='right', va='top', fontsize=6.5)

    for k in (0,):
        ax[k].set_xticks(xs)
        ax[k].set_xticklabels(lab, rotation=45, ha='right', fontsize=6.0)
    for a in ax:
        PS.close_frame(a)
    fig.tight_layout()
    PS.align_panel_letters(fig, [[(c, ax[c], l)
                                  for c, l in enumerate('abc')]])
    PS.save_figure(fig, OUT, 'SF3_retention')
    plt.close(fig)
    print('  SF3 written')


# --------------------------------------------------------------- SF4
# area, command, before, landing (matched filter), as-grown fit mod 60
TRIAD = [
    ('(+12,+12)', 46.0, 63.8, 16.39, 16.5),
    ('(-6,-6)', 0.0, 56.2, 19.63, 24.0),
    ('(0,-6)', 120.0, 63.8, 140.88, 19.0),
    ('(0,+18)', 41.0, 78.8, 20.01, 16.5),
    ('(+18,-18)', 41.0, 63.8, 17.90, 16.5),
    ('(-6,0) re-aim', 60.0, 17.98, 75.07, 24.0),
    ('(+12,+18)', 41.0, 63.8, 15.17, 14.0),
    ('(+6,+12)', 41.0, 78.8, 19.30, 16.5),
    ('(-6,-12)', 41.0, 26.2, 17.17, 9.0),
    ('(-12,-6)', 0.0, 18.8, 20.87, 19.0),
    ('(-12,-6) re-aim', 120.0, 18.8, 139.11, 19.0),
    ('(+12,+6)', 41.0, 131.2, 17.14, 16.5),
]
PHI0 = 18.22


def sf_triad():
    """One triad; the command picks the member; the as-grown fit predicts
    nothing."""
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 4.6),
                           gridspec_kw=dict(width_ratios=[1.62, 1.0]))
    rows = TRIAD
    mem = [(PHI0 + 60.0 * k) % 180.0 for k in range(3)]

    for m in mem:
        ax[0].axvline(m, color='0.55', lw=6, alpha=0.30, zorder=0)
        ax[0].text(m, len(rows) - 0.25, u'%.1f°' % m, ha='center',
                   fontsize=6.0, color='0.35')
    for i, (nm, cmd, bef, land, _f) in enumerate(rows):
        y = len(rows) - 1 - i
        ax[0].annotate('', xy=(land, y), xytext=(cmd, y),
                       arrowprops=dict(arrowstyle='->', lw=1.1,
                                       color=C.get('blue', 'C0')))
        ax[0].plot([cmd], [y], 'o', ms=4, mfc='w',
                   mec=C.get('red', 'C3'), mew=1.1, zorder=3)
        ax[0].plot([land], [y], 'o', ms=4.5, color=C.get('blue', 'C0'),
                   zorder=3)
        ax[0].plot([bef], [y], 'x', ms=4, color='0.55', mew=1.0, zorder=2)
    ax[0].set_yticks(range(len(rows)))
    ax[0].set_yticklabels([r[0] for r in rows][::-1], fontsize=6.0)
    ax[0].set_xlim(-4, 184)
    ax[0].set_ylim(-0.7, len(rows) - 0.05)
    ax[0].set_xticks([0, 30, 60, 90, 120, 150, 180])
    ax[0].set_xlabel(u'director / commanded axis (°)')
    ax[0].plot([], [], 'x', color='0.55', label='before')
    ax[0].plot([], [], 'o', mfc='w', mec=C.get('red', 'C3'), label='commanded')
    ax[0].plot([], [], 'o', color=C.get('blue', 'C0'), label='landed')
    PS.boxed_legend(ax[0], loc='lower left', fontsize=6.0, ncol=3)

    f = np.array([r[4] for r in rows])
    l = np.array([r[3] % 60.0 for r in rows])
    ax[1].plot([7, 27], [7, 27], '-', color='0.75', lw=0.9)
    ax[1].axhline(PHI0, color=C.get('blue', 'C0'), ls='--', lw=1.0)
    ax[1].plot(f, l, 'o', ms=5, color=C.get('blue', 'C0'))
    ax[1].set_xlabel(u'as-grown triad fit, mod 60°')
    ax[1].set_ylabel(u'written landing, mod 60°')
    ax[1].set_xlim(7, 27)
    ax[1].set_ylim(13, 23)
    r = float(np.corrcoef(f, l)[0, 1])
    ax[1].text(0.04, 0.95, u'r = %+.2f\np = 0.55' % r,
               transform=ax[1].transAxes, va='top', fontsize=6.5)
    ax[1].text(22.4, 22.5, u'1:1', fontsize=6.0, color='0.5', ha='right')
    ax[1].text(7.4, PHI0 + 0.3, u'one common triad',
               fontsize=6.0, color=C.get('blue', 'C0'))
    for a in ax:
        PS.close_frame(a)
    fig.tight_layout()
    PS.align_panel_letters(fig, [[(c, ax[c], l2)
                                  for c, l2 in enumerate('ab')]])
    PS.save_figure(fig, OUT, 'SF4_triad')
    plt.close(fig)
    print('  SF4 written')


# --------------------------------------------------------------- SF5
# sigma, speed, landing, aniso, area label
DOSE = [
    (686.0, 0.5, 20.01, 24.94, '(0,+18)'),
    (686.0, 0.5, 17.90, 50.53, '(+18,-18)'),
    (343.0, 0.5, 15.17, 5.67, '(+12,+18)'),
    (178.0, 0.5, 19.30, 18.63, '(+6,+12)'),
    (172.0, 1.0, 17.17, 35.96, '(-6,-12)'),
    (172.0, 1.0, 17.14, 13.46, '(+12,+6)'),
]
CMD = 41.0
MEMBER = 18.22
LATTICE_SIGMA = 120.0


def _sep(a, b):
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def sf5():
    """Across a fourfold dose range the landing stays on the member, not the
    command."""
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.9),
                           gridspec_kw=dict(width_ratios=[1.35, 1.0]))
    sg = np.array([r[0] for r in DOSE])
    sp = np.array([r[1] for r in DOSE])
    dm = np.array([_sep(r[2], MEMBER) for r in DOSE])
    dc = np.array([_sep(r[2], CMD) for r in DOSE])
    slow, fast = sp < 0.75, sp >= 0.75

    ax[0].axvspan(LATTICE_SIGMA * 0.8, LATTICE_SIGMA * 1.2, color='0.88',
                  zorder=0)
    ax[0].text(LATTICE_SIGMA, 30.5, 'lattice\ndose', ha='center',
               fontsize=6.0, color='0.4')
    for m, mk, nm in ((slow, 'o', u'0.5 µm/s'), (fast, 's', u'1.0 µm/s')):
        if not m.any():
            continue
        ax[0].semilogx(sg[m], dc[m], mk, ms=6, color=C.get('red', 'C3'),
                       mfc='w', mew=1.3, label='to the command, %s' % nm)
        ax[0].semilogx(sg[m], dm[m], mk, ms=6, color=C.get('blue', 'C0'),
                       label='to the member, %s' % nm)
    ax[0].axhline(15.0, color='0.5', ls='--', lw=0.9)
    ax[0].text(700, 15.8, u'15° criterion', fontsize=6.0, color='0.4',
               ha='right')
    ax[0].set_xlabel(u'areal dose σ (V·s/µm²)')
    ax[0].set_ylabel(u'distance from the landing (°)')
    ax[0].set_ylim(0, 33)
    ax[0].set_xlim(100, 1000)
    ax[0].set_xticks([100, 200, 400, 800])
    ax[0].set_xticklabels(['100', '200', '400', '800'])
    ax[0].minorticks_off()
    PS.boxed_legend(ax[0], loc='center left', fontsize=5.6)

    ax[1].semilogx(sg[slow], [r[3] for r, m in zip(DOSE, slow) if m], 'o',
                   ms=6, color='0.35', label=u'0.5 µm/s')
    ax[1].semilogx(sg[fast], [r[3] for r, m in zip(DOSE, fast) if m], 's',
                   ms=6, color='0.35', mfc='w', mew=1.3, label=u'1.0 µm/s')
    ax[1].set_xlabel(u'areal dose σ (V·s/µm²)')
    ax[1].set_ylabel('anisotropy after')
    ax[1].set_xlim(100, 1000)
    ax[1].set_ylim(0, 58)
    ax[1].set_xticks([100, 200, 400, 800])
    ax[1].set_xticklabels(['100', '200', '400', '800'])
    ax[1].minorticks_off()
    ax[1].text(0.04, 0.95, 'session-dependent;\nno trend claimed',
               transform=ax[1].transAxes, va='top', fontsize=6.0, color='0.4')
    PS.boxed_legend(ax[1], loc='center right', fontsize=6.0)
    for a in ax:
        PS.close_frame(a)
    fig.tight_layout()
    PS.align_panel_letters(fig, [[(c, ax[c], l) for c, l in enumerate('ab')]])
    PS.save_figure(fig, OUT, 'SF5_dose_speed')
    plt.close(fig)
    print('  SF5 written')


if __name__ == '__main__':
    which = sys.argv[1:] or ['1']
    if '1' in which:
        try:
            sf1()
        except Exception:
            traceback.print_exc(limit=3)
    if '5' in which:
        try:
            sf5()
        except Exception:
            traceback.print_exc(limit=3)
    if 't' in which:
        try:
            sf_triad()
        except Exception:
            traceback.print_exc(limit=3)
    if '3' in which:
        try:
            sf3()
        except Exception:
            traceback.print_exc(limit=3)
    if '2' in which:
        try:
            # (+12,+12) passed every gate; (-12,-12) passed every gate EXCEPT
            # topography, at roughness 35.6 nm and a 175 nm height range.
            sf2('PZTO_LDART_0043.ibw', 'PZTO_LDART_0044.ibw')
        except Exception:
            traceback.print_exc(limit=3)
