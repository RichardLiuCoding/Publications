# -*- coding: utf-8 -*-
"""make_today_figures.py -- the 29 August results, built to the figure skill.

Closed frames, no panel subtitles, bold lowercase letters aligned from final
axes positions, statistics in the caption, colorbars outside the data, and
export in png/pdf/svg/tiff through one function.

  figT1_imprint    the incommensurate control and the no-write null: what the
                   before/after changes actually measure
  figT2_uniform    a spatially uniform write orders the film onto a member
"""
from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
import scale_tools as ST
from publication_style import (configure_style, close_frame, square_map,
                               top_colorbar, boxed_legend, add_scalebar,
                               align_panel_letters, save_figure, COLORS, FONT)

OUT = os.path.join(HERE, 'figures_today')
W2 = 7.25
SUPER = (150.0, 500.0)
configure_style()
ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__

# area, commanded, template Lambda, sigma, frame stems
PANELS = [
    ('( 0, 0)', 16.5, 219.0, 133, '0000', '0001'),
    ('(+4, 0)', 4.0, 225.0, 122, '0002', '0003'),
    ('(-4, 0)', 19.0, 328.0, 130, '0004', '0005'),
    ('( 0,+4)', 21.5, 242.0, 53, '0006', '0007'),
    ('( 0,-4)', 16.5, 251.0, 263, '0008', '0009'),
    ('(+4,+4)', 16.5, 300.0, 17, '0010', '0011'),
    ('(-4,-4)', 24.0, 155.0, 133, '0012', '0013'),
]
INCOMM = ('(-4,-4)', 24.0, 155.0, 326.0, '0012', '0013')


def load(tag):
    d, h = g('ibw')(tag)
    S, _, r12 = g('signed')(d)
    return S, float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0


def interior(S, px, h=0.5):
    n = S.shape[0]
    hp = int(round(h * 1000.0 / px))
    c = n // 2
    return S[c - hp:c + hp, c - hp:c + hp]


def corners(S, px, size=0.62):
    n = S.shape[0]
    k = int(round(size * 1000.0 / px))
    return [S[0:k, 0:k], S[0:k, n - k:n], S[n - k:n, 0:k], S[n - k:n, n - k:n]]


def figT1():
    # ---- (a) the incommensurate control
    _, w, lam_t, lam_f, b, aa = INCOMM
    vals = {}
    for ch, pre in (('LDART', 'PZTO_LDART_'), ('VDART', 'PZTO_VDART_')):
        Sb, px = load(pre + b + '.ibw')
        Sa, _ = load(pre + aa + '.ibw')
        for nm, lam in (('template', lam_t), ('film', lam_f)):
            vals[(ch, nm)] = (
                ST.matched_amplitude(interior(Sb, px), px, w, lam),
                ST.matched_amplitude(interior(Sa, px), px, w, lam))

    # ---- (b) null vs signal
    nulls, sigs, lows = [], [], []
    for area, ww, lam, sg, b2, a2 in PANELS:
        for ch, pre in (('LDART', 'PZTO_LDART_'), ('VDART', 'PZTO_VDART_')):
            Sb, px = load(pre + b2 + '.ibw')
            Sa, _ = load(pre + a2 + '.ibw')
            ib = ST.matched_amplitude(interior(Sb, px), px, ww, lam)
            ia = ST.matched_amplitude(interior(Sa, px), px, ww, lam)
            cb = np.mean([ST.matched_amplitude(c, px, ww, lam)
                          for c in corners(Sb, px)])
            ca = np.mean([ST.matched_amplitude(c, px, ww, lam)
                          for c in corners(Sa, px)])
            nulls.append(ca / max(cb, 1e-9))
            sigs.append((sg, ch, ia / max(ib, 1e-9)))
    nulls = np.asarray(nulls)

    fig = plt.figure(figsize=(W2, 2.55))
    gs = fig.add_gridspec(1, 3, left=0.085, right=0.985, bottom=0.215,
                          top=0.90, wspace=0.46, width_ratios=[1.0, 1.0, 1.15])

    ax = fig.add_subplot(gs[0, 0])
    x = np.arange(2)
    wd = 0.34
    for k, ch in enumerate(('LDART', 'VDART')):
        bef = [vals[(ch, 'template')][0], vals[(ch, 'film')][0]]
        aft = [vals[(ch, 'template')][1], vals[(ch, 'film')][1]]
        ax.bar(x + (k - 0.5) * wd, aft, wd * 0.92,
               color=(COLORS['red'] if k == 0 else COLORS['blue']),
               edgecolor='black', lw=0.6, label=ch)
        ax.plot(x + (k - 0.5) * wd, bef, 'k_', ms=9, mew=1.2, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(['template\n%.0f nm' % lam_t, 'film\n%.0f nm' % lam_f])
    ax.set_ylabel('modulation at that\nwavevector (pm)')
    ax.set_ylim(0, 178)
    hs = [plt.Rectangle((0, 0), 1, 1, color=COLORS['red'], label='LDART'),
          plt.Rectangle((0, 0), 1, 1, color=COLORS['blue'], label='VDART'),
          plt.Line2D([], [], ls='', marker='_', ms=9, mew=1.2, color='black',
                     label='before')]
    lg = ax.legend(handles=hs, loc='upper right', fontsize=6.8, frameon=True,
                   fancybox=False, handlelength=1.2, handletextpad=0.4,
                   borderpad=0.3)
    lg.get_frame().set_edgecolor('black')
    lg.get_frame().set_linewidth(0.7)
    close_frame(ax)
    a1 = ax

    ax = fig.add_subplot(gs[0, 1])
    bins = np.linspace(0, 2.2, 18)
    ax.hist(nulls, bins=bins, color=COLORS['light_grey'], edgecolor='black',
            lw=0.6)
    ax.axvline(1.0, color=COLORS['grey'], lw=0.9, ls=(0, (3, 2)))
    ax.set_xlabel('after / before ratio')
    ax.set_ylabel('unwritten corner\npatches')
    ax.set_xlim(0, 2.2)
    close_frame(ax)
    a2 = ax

    ax = fig.add_subplot(gs[0, 2])
    nmax = nulls.max()
    ax.axhspan(0, nmax, color=COLORS['light_grey'], alpha=0.6, zorder=0)
    for sg, ch, r in sigs:
        ax.plot(sg, r, 'o' if ch == 'LDART' else '^', ms=5.6,
                color=(COLORS['red'] if ch == 'LDART' else COLORS['blue']),
                mec='black', mew=0.5, zorder=3)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(10, 400)
    ax.set_ylim(0.7, 30)
    ax.set_xlabel(u'dose σ (V·s/µm$^2$)')
    ax.set_ylabel('interior after / before')
    hs = [plt.Line2D([], [], ls='', marker='o', color=COLORS['red'],
                     mec='black', mew=0.5, label='LDART'),
          plt.Line2D([], [], ls='', marker='^', color=COLORS['blue'],
                     mec='black', mew=0.5, label='VDART')]
    ax.legend(handles=hs, loc='lower right', fontsize=7.0, frameon=True,
              fancybox=False)
    close_frame(ax)

    align_panel_letters(fig, [[(0, a1, 'a'), (1, a2, 'b'), (2, ax, 'c')]])
    save_figure(fig, OUT, 'figT1_imprint')
    plt.close(fig)
    print('figT1: null median %.2f max %.2f; %d of %d interiors above the null max'
          % (np.median(nulls), nmax,
             int(np.sum([r > nmax for _, _, r in sigs])), len(sigs)))


def figT2():
    Sb, px = load('PZTO_LDART_0014.ibw')
    Sa, _ = load('PZTO_LDART_0015.ibw')
    tri, _ = g('pin_triad')('PZTO_LDART_0014.ibw', ref_fam=g('FAM_FILM'))
    tri = [float(t) for t in tri]
    L = px * Sb.shape[0] / 1000.0

    fig = plt.figure(figsize=(W2, 2.75))
    gs = fig.add_gridspec(1, 3, left=0.045, right=0.985, bottom=0.10,
                          top=0.86, wspace=0.30, width_ratios=[1, 1, 1.25])
    v = float(np.nanpercentile(np.abs(np.r_[Sb.ravel(), Sa.ravel()]), 98))
    axes = []
    for k, (S, lab) in enumerate(((Sb, 'before'), (Sa, 'after'))):
        ax = fig.add_subplot(gs[0, k])
        im = ax.imshow(S, origin='lower', extent=[0, L, 0, L], cmap='RdBu_r',
                       clim=(-v, v))
        h = 0.7
        ax.add_patch(plt.Rectangle((L / 2 - h, L / 2 - h), 2 * h, 2 * h,
                                   fill=False, ec='black', lw=1.0))
        ax.set_xticks([]); ax.set_yticks([]); square_map(ax)
        ax.set_xlabel(lab, fontsize=FONT['axis'], labelpad=2.0)
        if k == 0:
            add_scalebar(ax, length=0.5, label=u'0.5 µm', x=0.14, y=0.16,
                         label_offset=0.09, fontsize=7.4)
        axes.append(ax)
    vt = float(np.floor(v / 25.0) * 25.0)
    cb = top_colorbar(fig, axes[0], im, u'in-plane response (a.u.)',
                      ticks=[-vt, 0, vt], width=0.80, y=1.07)
    cb.ax.set_xticklabels(['%d' % -vt, '0', '%d' % vt])

    ax = fig.add_subplot(gs[0, 2])
    for lab, S, c in (('before', Sb, COLORS['grey']),
                      ('after', Sa, COLORS['red'])):
        a, prof, _ = ST.band_angular_power(interior(S, px), px, *SUPER)
        ax.plot(a, prof / prof.max(), color=c, lw=1.4, label=lab,
                ls='--' if lab == 'before' else '-')
    for t in tri:
        ax.axvline(t, color=COLORS['light_grey'], lw=0.8, zorder=0)
    ax.set_xlim(0, 180)
    ax.set_xticks([0, 60, 120, 180])
    ax.set_ylim(0, 1.15)
    ax.set_xlabel(u'director (°)')
    ax.set_ylabel('angular power (norm.)')
    boxed_legend(ax, loc='upper right', fontsize=7.2)
    close_frame(ax)

    align_panel_letters(fig, [[(0, axes[0], 'a'), (1, axes[1], 'b'),
                               (2, ax, 'c')]])
    save_figure(fig, OUT, 'figT2_uniform')
    plt.close(fig)
    db, _, _, pb = ST.band_peak(interior(Sb, px), px, *SUPER, n_perm=200)
    da, _, _, pa = ST.band_peak(interior(Sa, px), px, *SUPER, n_perm=200)
    print('figT2: interior %.1f deg (p %.3f) -> %.1f deg (p %.3f); triad %s'
          % (db, pb, da, pa, [int(t) for t in tri]))


def main():
    os.makedirs(OUT, exist_ok=True)
    figT1()
    figT2()
    figT3()
    figT4()
    print('\nfigures written to %s' % OUT)




# area, commanded, triad, template Lambda, L/V before, L/V after
OFFTRIAD = [
    ('(-8, 0)', 56.5, [26.0, 86.0, 146.0], 300.0, '0016', '0017'),
    ('(+8,-8)', 46.5, [16.0, 76.0, 136.0], 338.0, '0020', '0021'),
]


def figT3():
    """The off-triad diagnostic: commanded between two members."""
    fig = plt.figure(figsize=(W2, 2.6))
    gs = fig.add_gridspec(1, 3, left=0.055, right=0.985, bottom=0.215,
                          top=0.90, wspace=0.36, width_ratios=[1.0, 1.25, 1.0])

    # (a) the after-frame, with the commanded direction drawn on it
    area, want, tri, lam, b, aa = OFFTRIAD[0]
    S, px = load('PZTO_LDART_' + aa + '.ibw')
    L = px * S.shape[0] / 1000.0
    ax = fig.add_subplot(gs[0, 0])
    v = float(np.nanpercentile(np.abs(S), 98))
    ax.imshow(S, origin='lower', extent=[0, L, 0, L], cmap='RdBu_r',
              clim=(-v, v))
    h = 0.6
    ax.add_patch(plt.Rectangle((L / 2 - h, L / 2 - h), 2 * h, 2 * h,
                               fill=False, ec='black', lw=1.0))
    u = np.array([np.cos(np.deg2rad(want)), np.sin(np.deg2rad(want))])
    ax.plot([L / 2 - 0.4 * u[0], L / 2 + 0.4 * u[0]],
            [L / 2 - 0.4 * u[1], L / 2 + 0.4 * u[1]],
            color='black', lw=2.0, solid_capstyle='round')
    ax.set_xticks([]); ax.set_yticks([]); square_map(ax)
    add_scalebar(ax, length=0.5, label=u'0.5 µm', x=0.13, y=0.15,
                 label_offset=0.09, fontsize=7.4)
    ax.set_xlabel(u'commanded %.1f°' % want, fontsize=FONT['axis'],
                  labelpad=2.0)
    a1 = ax

    # (b) matched filter at the command and at each member, both runs
    ax = fig.add_subplot(gs[0, 1])
    xs, lbl = [], []
    k = 0
    for area, want, tri, lam, b, aa in OFFTRIAD:
        for ch, pre in (('LDART', 'PZTO_LDART_'), ('VDART', 'PZTO_VDART_')):
            Sb, px = load(pre + b + '.ibw')
            Sa, _ = load(pre + aa + '.ibw')
            tests = [('cmd', want)] + [('m%d' % (i + 1), t)
                                       for i, t in enumerate(tri)]
            for nm, d in tests:
                ib = ST.matched_amplitude(interior(Sb, px, 0.6), px, d, lam)
                ia = ST.matched_amplitude(interior(Sa, px, 0.6), px, d, lam)
                xs.append((k, ia / max(ib, 1e-9), nm == 'cmd', ch))
                k += 1
            k += 1
    for x, r, iscmd, ch in xs:
        ax.bar(x, r, 0.85,
               color=(COLORS['red'] if iscmd else COLORS['light_grey']),
               edgecolor='black', lw=0.5)
    ax.axhline(1.81, color=COLORS['black'], lw=0.9, ls=(0, (3, 2)))
    ax.set_xticks([])
    ax.set_ylabel('after / before at\nthat direction')
    ax.set_yscale('log')
    ax.set_ylim(0.05, 30)
    ax.set_xlabel('commanded (red) vs the three triad members (grey),\n'
                  'two runs x two channels', fontsize=7.4, linespacing=1.3)
    close_frame(ax)
    a2 = ax

    # (c) angular power of the after-frame, showing where the power sits
    ax = fig.add_subplot(gs[0, 2])
    for area, want, tri, lam, b, aa in OFFTRIAD[:1]:
        for lab, stem, c, ls in (('before', b, COLORS['grey'], '--'),
                                 ('after', aa, COLORS['red'], '-')):
            S, px = load('PZTO_LDART_' + stem + '.ibw')
            a, prof, _ = ST.band_angular_power(interior(S, px, 0.6), px, *SUPER)
            ax.plot(a, prof / prof.max(), ls, color=c, lw=1.4, label=lab)
        for t in tri:
            ax.axvline(t, color=COLORS['light_grey'], lw=0.9, zorder=0)
        ax.axvline(want, color=COLORS['red'], lw=0.9, ls=(0, (2, 2)), zorder=0)
    ax.set_xlim(0, 180); ax.set_xticks([0, 60, 120, 180])
    ax.set_ylim(0, 1.15)
    ax.set_xlabel(u'director (°)')
    ax.set_ylabel('angular power (norm.)')
    boxed_legend(ax, loc='upper right', fontsize=7.0)
    close_frame(ax)

    align_panel_letters(fig, [[(0, a1, 'a'), (1, a2, 'b'), (2, ax, 'c')]])
    save_figure(fig, OUT, 'figT3_offtriad')
    plt.close(fig)
    n_cmd = [r for _, r, c, _ in xs if c]
    n_mem = [r for _, r, c, _ in xs if not c]
    print('figT3: commanded-direction ratios %s; member ratios median %.2f'
          % (['%.1f' % r for r in n_cmd], np.median(n_mem)))


# retention: (area, sigma, hours, LDART then/now, VDART then/now)
RETAIN = [
    ('(0,0)', 133, 5.0, 150.27, 97.12, 122.28, 112.30),
    ('(+4,0)', 122, 4.7, 124.96, 99.64, 179.26, 115.59),
    ('(0,-4)', 263, 3.7, 208.94, 156.97, None, None),
]
# structure-tensor sweep on the off-triad panel, against the random null
SWEEP = [(60, 22.4, 7.9), (40, 19.8, 11.5), (25, 16.3, 18.7),
         (15, 15.9, 23.2), (10, 15.7, 26.0)]
SWEEP_CTRL = [(60, 10.9), (40, 13.4), (25, 13.4), (15, 13.3), (10, 13.5)]
NULL_MEMBER, NULL_CMD = 14.94, 44.95


def figT4():
    """Retention, and the null comparison that decides what was written."""
    fig = plt.figure(figsize=(W2, 2.5))
    gs = fig.add_gridspec(1, 2, left=0.085, right=0.985, bottom=0.215,
                          top=0.90, wspace=0.34, width_ratios=[1.0, 1.35])

    ax = fig.add_subplot(gs[0, 0])
    for i, (a, sg, hrs, lt, ln, vt, vn) in enumerate(RETAIN):
        ax.plot([0, hrs], [100, 100 * ln / lt], 'o-', color=COLORS['red'],
                ms=5, mec='black', mew=0.5, lw=1.1)
        if vt:
            ax.plot([0, hrs], [100, 100 * vn / vt], '^--', color=COLORS['blue'],
                    ms=5, mec='black', mew=0.5, lw=1.1)
    ax.axhline(100, color=COLORS['grey'], lw=0.8, ls=(0, (3, 2)))
    ax.set_xlim(-0.3, 5.6); ax.set_ylim(0, 118)
    ax.set_xlabel('hours after writing')
    ax.set_ylabel('modulation retained (%)')
    hs = [plt.Line2D([], [], marker='o', color=COLORS['red'], mec='black',
                     mew=0.5, label='LDART'),
          plt.Line2D([], [], marker='^', ls='--', color=COLORS['blue'],
                     mec='black', mew=0.5, label='VDART')]
    ax.legend(handles=hs, loc='lower left', fontsize=7.0, frameon=True,
              fancybox=False)
    close_frame(ax)
    a1 = ax

    ax = fig.add_subplot(gs[0, 1])
    sm = [s_ for s_, _, _ in SWEEP]
    ax.axhline(NULL_MEMBER, color=COLORS['grey'], lw=1.0, ls=(0, (4, 2)))
    ax.axhline(NULL_CMD, color=COLORS['grey'], lw=1.0, ls=(0, (1, 2)))
    ax.plot(sm, [m for _, m, _ in SWEEP], 'o-', color=COLORS['grey'],
            ms=5, mec='black', mew=0.5, lw=1.2, label='written: to member')
    ax.plot(sm, [c for _, _, c in SWEEP], 'o-', color=COLORS['red'],
            ms=5, mec='black', mew=0.5, lw=1.4, label='written: to command')
    ax.plot([s_ for s_, _ in SWEEP_CTRL], [m for _, m in SWEEP_CTRL], 's--',
            color=COLORS['green'], ms=4.6, mec='black', mew=0.5, lw=1.2,
            label='unwritten: to member')
    ax.text(58, NULL_MEMBER + 1.6, 'random null, member', fontsize=6.6,
            color=COLORS['grey'])
    ax.text(58, NULL_CMD + 1.6, 'random null, command', fontsize=6.6,
            color=COLORS['grey'])
    ax.invert_xaxis()
    ax.set_xlabel('structure-tensor smoothing (nm)')
    ax.set_ylabel(u'median angular distance (°)')
    ax.set_ylim(0, 52)
    ax.legend(loc='center right', fontsize=6.8, frameon=True, fancybox=False)
    close_frame(ax)

    align_panel_letters(fig, [[(0, a1, 'a'), (1, ax, 'b')]])
    save_figure(fig, OUT, 'figT4_retention_null')
    plt.close(fig)
    r = [100 * ln / lt for _, _, _, lt, ln, _, _ in RETAIN]
    print('figT4: LDART retention %s %%; command clustering beats the null at '
          'every smoothing' % ['%.0f' % x for x in r])


if __name__ == '__main__':
    main()
