# -*- coding: utf-8 -*-
"""Raster against point-pulse lattice, on the allowed directions only.

The off-triad discrimination is contested (three runs, two of them below the
four-period readout floor). This figure avoids it entirely and compares the two
tools where both have plenty of data: commands aimed at an allowed direction.
Lattice numbers come from results_templates.csv, raster numbers from the twelve
landings tabulated in the manuscript.
"""
import csv
import io

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

import publication_style as ps

OUT = Path('figures_ms')
RAS, LAT = '#C0392B', '#2B6CB0'
WIN, MINP, V = 1.4, 4.0, 10.0


def cd(a, b):
    return abs((a - b + 90.0) % 180.0 - 90.0)


def lattice():
    rows = []
    for r in csv.DictReader(io.open('results_templates.csv', encoding='utf-8')):
        try:
            want, lam = float(r['want']), float(r['lam_nm'])
        except (ValueError, TypeError):
            continue
        if WIN * 1000.0 / lam < MINP:
            continue
        tri = [float(x) for x in r['triad'].split('|')]
        i = int(np.argmin([cd(want, t) for t in tri]))
        rows.append((i, cd(float(r['dom_after']), want), float(r['sigma'])))
    return rows


# the twelve raster landings, with the member each was aimed at
RASTER = [(0, 2.2), (0, 5.2), (2, 0.2), (0, 2.2), (0, 2.2), (1, 2.8),
          (0, 3.1), (0, 1.1), (0, 1.1), (0, 2.7), (2, 0.8), (0, 1.1)]


def main():
    L = lattice()
    fig, ax = plt.subplots(1, 3, figsize=(6.9, 2.55))

    # (a) does the tool reach all three allowed directions?
    a = ax[0]
    for k, (nm, col, data) in enumerate((('raster', RAS, RASTER),
                                         ('lattice', LAT,
                                          [(m, o) for m, o, _ in L]))):
        for m in range(3):
            g = [o for mm, o in data if mm == m]
            if not g:
                continue
            hits = sum(1 for o in g if o <= 15.0)
            a.bar(m + (k - 0.5) * 0.36, 100.0 * hits / len(g), 0.32,
                  color=col, edgecolor='none', label=nm if m == 0 else None)
            a.text(m + (k - 0.5) * 0.36,
                   100.0 * hits / len(g) + (3.5 if k == 0 else 13.5),
                   '%d/%d' % (hits, len(g)), ha='center', fontsize=6.4,
                   color=col)
    a.set_xticks(range(3))
    a.set_xticklabels(['1', '2', '3'], fontsize=8.4)
    a.set_xlabel('allowed direction asked for')
    a.set_ylabel('reached it (%)')
    a.set_ylim(0, 126)
    a.set_yticks([0, 50, 100])
    ps.boxed_legend(a, loc='lower left', fontsize=6.8, handlelength=0.9,
                    borderpad=0.24, labelspacing=0.2)
    ps.close_frame(a)

    # (b) how close to the command
    b = ax[1]
    rng = np.random.default_rng(0)
    for k, (nm, col, offs) in enumerate((('raster', RAS, [o for _, o in RASTER]),
                                         ('lattice', LAT,
                                          [o for _, o, _ in L]))):
        y = np.full(len(offs), k) + rng.normal(0, 0.05, len(offs))
        b.plot(np.clip(offs, 0, 70), y, ls='none', marker='o', ms=3.2,
               mfc=col, mec='none', alpha=0.75)
        b.plot(np.median([o for o in offs if o <= 15]), k, ls='none',
               marker='|', ms=12, mew=1.8, color='#222222')
    b.axvline(15, color='#888888', lw=0.9, ls='--')
    b.text(17.5, 0.52, 'hit criterion', fontsize=6.6, color='#666666')
    b.set_yticks([0, 1])
    b.set_yticklabels(['raster', 'lattice'], fontsize=8.0)
    b.set_ylim(-0.55, 1.55)
    b.set_xlabel('distance from command ($\\degree$)')
    b.set_xlim(-3, 73)
    b.set_xticks([0, 25, 50])
    ps.close_frame(b)

    # (c) area written per hour, for the configurations actually run
    c = ax[2]
    cfg = [('raster\n0.5', 333, RAS), ('raster\n1.0', 167, RAS),
           ('lattice\nsolid', 133 * 2.03, LAT),
           ('lattice\nmasked', 133 * 2.33, LAT)]
    for i2, (nm, tpa_num, col) in enumerate(cfg):
        rate = 3600.0 / (tpa_num / V)
        c.bar(i2, rate, 0.62, color=col, edgecolor='none')
        c.text(i2, rate + 7, '%.0f' % rate, ha='center', fontsize=6.8,
               color=col)
    c.set_xticks(range(4))
    c.set_xticklabels([n for n, _, _ in cfg], fontsize=6.6)
    c.set_xlabel('configuration')
    c.set_ylabel('written per hour ($\\mu$m$^2$/h)')
    c.set_ylim(0, 268)
    c.set_yticks([0, 100, 200])
    ps.close_frame(c)

    fig.subplots_adjust(left=0.082, right=0.988, top=0.885, bottom=0.275,
                        wspace=0.42)
    fig.canvas.draw()
    for axx, lab in zip(ax, 'abc'):
        pos = axx.get_position()
        fig.text(pos.x0 - 0.055, pos.y1 + 0.030, lab, fontsize=9.4,
                 fontweight='bold', ha='left', va='bottom')
    ps.save_figure(fig, OUT, 'F8_tool_compare',
                   formats=('png', 'pdf', 'svg'), pad_inches=0.02)
    hits = [o for _, o, _ in L if o <= 15]
    print('lattice: %d panels, %d hits, median offset %.1f deg'
          % (len(L), len(hits), np.median(hits)))
    print('raster : %d landings, all within %.1f deg'
          % (len(RASTER), max(o for _, o in RASTER)))


if __name__ == '__main__':
    main()
