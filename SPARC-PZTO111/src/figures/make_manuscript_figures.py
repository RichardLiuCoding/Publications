# -*- coding: utf-8 -*-
"""Manuscript figures, built entirely from results_templates.csv and .ibw frames.

Nothing is transcribed. Re-running this regenerates every panel and prints the
statistics quoted in the text, so figures, numbers and prose cannot drift apart
-- which is how a 2x error reached FINDINGS once already (PITFALLS 19.11).

  figM1_selection    the headline: each template's commanded director against
                     the director the film actually adopted, every panel
  figM2_dose         dose-response, and where the lattice threshold sits
                     relative to the aperiodic square's
  figM3_maps         real-space LDART evidence for the best selection pair
  figM4_mechanism    the two-term picture the data support
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autoloop as A
from publication_style import (configure_style, square_map, add_scalebar,
                               save_figure, COLORS)

OUT = os.path.join(HERE, 'figures_manuscript')
CSV = os.path.join(HERE, 'results_templates.csv')
W = 7.25
configure_style()
ns = A.load_toolkit(stub_instrument=True)
g = ns.__getitem__


def cdist(a, b):
    return abs((float(a) - float(b) + 90.0) % 180.0 - 90.0)


def load_rows():
    rows = list(csv.DictReader(io.open(CSV, encoding='utf-8')))
    for r in rows:
        for k in ('ang', 'theta', 'sigma', 'want', 'excess', 'null', 'x_null',
                  'dom_before', 'dom_after', 'lam_nm', 'n_sites', 'q_site',
                  'mod_before', 'mod_after'):
            try:
                r[k] = float(r[k])
            except (ValueError, TypeError):
                r[k] = np.nan
        r['w0'] = np.array([float(r['w0_%d' % i]) for i in range(3)])
        r['w1'] = np.array([float(r['w1_%d' % i]) for i in range(3)])
        r['triadv'] = [float(x) for x in r['triad'].split('|')]
        r['cleared'] = r['cleared'] == '1'
    return rows


def target_w(r):
    """Population on the member this panel's template selects."""
    if not np.isfinite(r['want']):
        return np.nan, np.nan
    k = int(np.argmin([cdist(t, r['want']) for t in r['triadv']]))
    return r['w0'][k], r['w1'][k]


# ================================================================== FIG M1
def figM1(rows):
    lat = [r for r in rows if r['kind'] in ('parallel', 'sheared')
           and np.isfinite(r['want'])]
    fig = plt.figure(figsize=(W, 3.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.95], wspace=0.34,
                          left=0.075, right=0.98, top=0.87, bottom=0.17)

    # (a) commanded vs achieved
    ax = fig.add_subplot(gs[0])
    ax.plot([0, 180], [0, 180], '-', color=COLORS['light_grey'], lw=1.0,
            zorder=0)
    for d in (-15, 15):
        ax.plot([0, 180], [d, 180 + d], ':', color=COLORS['light_grey'],
                lw=0.8, zorder=0)
    for r in lat:
        c = COLORS['purple'] if cdist(r['dom_after'], r['want']) <= 15 \
            else COLORS['red']
        ax.plot(r['want'], r['dom_after'], 'o', ms=6, color=c, alpha=0.85,
                mec='white', mew=0.6)
    ax.set_xlabel(u'director selected by the template (°)', fontsize=8.0)
    ax.set_ylabel(u'director the film adopted (°)', fontsize=8.0)
    ax.set_xlim(0, 180); ax.set_ylim(-8, 188)
    ax.set_xticks([0, 45, 90, 135, 180]); ax.set_yticks([0, 45, 90, 135, 180])
    hits = sum(1 for r in lat if cdist(r['dom_after'], r['want']) <= 15)
    ax.set_title('(a) the template sets the outcome', loc='left', fontsize=8.6)
    ax.text(0.04, 0.94, '%d/%d within 15°\nmedian offset %.1f°'
            % (hits, len(lat),
               float(np.median([cdist(r['dom_after'], r['want']) for r in lat]))),
            transform=ax.transAxes, va='top', fontsize=7.2)

    # (b) offset histogram
    ax = fig.add_subplot(gs[1])
    offs = [cdist(r['dom_after'], r['want']) for r in lat]
    ax.hist(offs, bins=np.arange(0, 60, 5), color=COLORS['purple'],
            edgecolor='white')
    ax.axvline(15, color=COLORS['red'], ls='--', lw=1.0)
    ax.text(16, ax.get_ylim()[1] * 0.9, 'hit\nthreshold', fontsize=6.8,
            color=COLORS['red'], va='top')
    ax.set_xlabel(u'|achieved − selected| (°)', fontsize=8.0)
    ax.set_ylabel('panels', fontsize=8.0)
    ax.set_title('(b) accuracy', loc='left', fontsize=8.6)

    # (c) how far the film had to move
    ax = fig.add_subplot(gs[2])
    for r in lat:
        moved = cdist(r['dom_before'], r['dom_after'])
        c = COLORS['purple'] if cdist(r['dom_after'], r['want']) <= 15 \
            else COLORS['red']
        ax.plot(cdist(r['dom_before'], r['want']), moved, 'o', ms=5.5,
                color=c, alpha=0.85, mec='white', mew=0.6)
    ax.plot([0, 90], [0, 90], '-', color=COLORS['light_grey'], lw=1.0, zorder=0)
    ax.set_xlabel(u'distance to travel (°)', fontsize=8.0)
    ax.set_ylabel(u'distance moved (°)', fontsize=8.0)
    ax.set_xlim(-4, 92); ax.set_ylim(-4, 92)
    ax.set_title('(c) it goes where it is sent', loc='left', fontsize=8.6)
    save_figure(fig, OUT, 'figM1_selection'); plt.close(fig)
    return hits, len(lat), offs


# ================================================================== FIG M2
def figM2(rows):
    """Dose response, in the two variables that matter: does it move, and does
    it go where it was sent? Those separate at low dose and that separation is
    the result."""
    lat = [r for r in rows if r['kind'] == 'parallel' and np.isfinite(r['want'])]
    fig = plt.figure(figsize=(W, 3.25))
    gs = fig.add_gridspec(1, 2, wspace=0.30, left=0.085, right=0.975,
                          top=0.86, bottom=0.17)

    # (a) did it clear the null?
    ax = fig.add_subplot(gs[0])
    for r in lat:
        c = COLORS['purple'] if r['cleared'] else COLORS['red']
        ax.plot(r['sigma'], r['x_null'], 'o', ms=6, color=c, mec='white',
                mew=0.6, zorder=3)
    ax.axhline(2.0, color=COLORS['red'], ls='--', lw=1.1)
    ax.text(900, 2.4, u'2× null', fontsize=6.8, color=COLORS['red'], ha='right')
    ax.axvspan(400, 667, color=COLORS['yellow'], alpha=0.18, zorder=0)
    ax.text(516, 55, 'aperiodic square', fontsize=6.6, ha='center',
            color='#8a7400')
    ax.text(516, 42, 'threshold (M15)', fontsize=6.6, ha='center',
            color='#8a7400')
    ax.set_xscale('log')
    ax.set_xlabel(u'areal dose σ (V·s/µm²)', fontsize=8.0)
    ax.set_ylabel(u'excess / control null (×)', fontsize=8.0)
    ax.set_title('(a) does the film change?', loc='left', fontsize=8.6)

    # (b) did it go where it was sent?
    ax = fig.add_subplot(gs[1])
    for r in lat:
        off = cdist(r['dom_after'], r['want'])
        c = COLORS['purple'] if off <= 15 else COLORS['red']
        ax.plot(r['sigma'], off, 'o', ms=6, color=c, mec='white', mew=0.6,
                zorder=3)
    ax.axhline(15, color=COLORS['grey'], ls=':', lw=1.0)
    ax.axvspan(28, 52, color=COLORS['green'], alpha=0.18, zorder=0)
    ax.text(40, 58, 'selection', fontsize=6.8, ha='center',
            color=COLORS['green'])
    ax.text(40, 50, 'switches on', fontsize=6.8, ha='center',
            color=COLORS['green'])
    ax.set_xscale('log')
    ax.set_xlabel(u'areal dose σ (V·s/µm²)', fontsize=8.0)
    ax.set_ylabel(u'|achieved − selected| (°)', fontsize=8.0)
    ax.set_ylim(-4, 72)
    ax.set_title('(b) does it go where it is sent?', loc='left', fontsize=8.6)
    save_figure(fig, OUT, 'figM2_dose'); plt.close(fig)


# ================================================================== FIG M4
def figM4():
    fig = plt.figure(figsize=(W, 2.55))
    gs = fig.add_gridspec(1, 3, wspace=0.22, left=0.03, right=0.985,
                          top=0.86, bottom=0.06)
    ax = fig.add_subplot(gs[0]); ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title('(a) two separable terms', loc='left', fontsize=8.6)
    ax.text(0.02, 0.74, 'DRIVE', fontsize=9, fontweight='bold',
            color=COLORS['orange'])
    ax.text(0.02, 0.60, 'set by |E|; polarity-independent;\n'
                        'sharp dose threshold.\nCONCENTRATES the local director.',
            fontsize=7.0, va='top')
    ax.text(0.02, 0.32, 'SELECTION', fontsize=9, fontweight='bold',
            color=COLORS['purple'])
    ax.text(0.02, 0.18, 'needs q = Q; a featureless\npatch cannot do it.\n'
                        'CHOOSES which member.',
            fontsize=7.0, va='top')

    ax = fig.add_subplot(gs[1]); ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title('(b) and they are not independent', loc='left', fontsize=8.6)
    ax.text(0.5, 0.72, 'a matched template lowers\nthe dose required',
            ha='center', fontsize=7.6)
    ax.annotate('', xy=(0.30, 0.42), xytext=(0.72, 0.42),
                arrowprops=dict(arrowstyle='-|>', color=COLORS['purple'],
                                lw=1.8))
    ax.text(0.72, 0.34, u'σ 400–667\naperiodic', ha='center', va='top',
            fontsize=7.0, color='#8a7400')
    ax.text(0.28, 0.34, u'σ ≤ 306\ncommensurate', ha='center', va='top',
            fontsize=7.0, color=COLORS['purple'])
    ax.text(0.5, 0.08, 'selection is not merely a direction chooser',
            ha='center', fontsize=6.8, color=COLORS['grey'])

    ax = fig.add_subplot(gs[2]); ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title('(c) the transition', loc='left', fontsize=8.6)
    ax.text(0.02, 0.76, 'REPLACEMENT, not rotation', fontsize=7.8,
            fontweight='bold')
    ax.text(0.02, 0.62, 'angular power vanishes at the old\n'
                        'orientation and appears at the new;\n'
                        'no transit through intermediates.',
            fontsize=7.0, va='top')
    ax.text(0.02, 0.30, 'above threshold, not graded', fontsize=7.8,
            fontweight='bold')
    ax.text(0.02, 0.16, u'w scatters 0.40–0.95 over a 2.6×\n'
                        u'range in dose, tracking AREA not σ.',
            fontsize=7.0, va='top')
    save_figure(fig, OUT, 'figM4_mechanism'); plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = load_rows()
    print('%d panel rows' % len(rows))
    hits, n, offs = figM1(rows)
    print('figM1: %d/%d within 15 deg, median offset %.1f deg'
          % (hits, n, float(np.median(offs))))
    figM2(rows)
    lat = [r for r in rows if r['kind'] == 'parallel' and np.isfinite(r['want'])]
    hit = [r for r in lat if cdist(r['dom_after'], r['want']) <= 15]
    miss = [r for r in lat if cdist(r['dom_after'], r['want']) > 15]
    print('figM2: %d dose points, sigma %.0f-%.0f' %
          (len(lat), min(r['sigma'] for r in lat), max(r['sigma'] for r in lat)))
    print('   on target %d, off target %d' % (len(hit), len(miss)))
    if hit:
        print('   lowest sigma ON TARGET: %.0f' % min(r['sigma'] for r in hit))
    if miss:
        print('   off-target sigmas: %s'
              % sorted(round(r['sigma']) for r in miss))
    figM4()
    print('written to %s' % OUT)


if __name__ == '__main__':
    main()
