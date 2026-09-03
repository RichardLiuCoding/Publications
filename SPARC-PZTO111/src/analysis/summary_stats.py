# -*- coding: utf-8 -*-
"""summary_stats.py -- every number quoted in the summary document.

The document is generated from this script's output, so prose and data cannot
drift (the failure mode of PITFALLS 19.11 and 19.15). Run it, read it, and if a
number in the .docx does not appear here it does not belong in the .docx.

The 4-Lambda rule (PITFALLS 19.15) is applied FIRST and visibly: a panel whose
1.4 um readout window holds fewer than 4 lamellar periods is not a measurement,
so it is separated out rather than silently averaged in.
"""
from __future__ import annotations

import csv
import io
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, 'results_templates.csv')
WIN_UM = 1.4
MIN_PERIODS = 4.0
LAM_MAX_NM = WIN_UM * 1000.0 / MIN_PERIODS      # 350 nm


def cdist(a, b):
    """Separation of two directors, mod 180 deg."""
    return abs((float(a) - float(b) + 90.0) % 180.0 - 90.0)


def load():
    rows = list(csv.DictReader(io.open(CSV, encoding='utf-8')))
    for r in rows:
        for k in ('ang', 'theta', 'sigma', 'want', 'excess', 'null', 'x_null',
                  'dom_before', 'dom_after', 'lam_nm', 'n_sites', 'q_site',
                  'mod_before', 'mod_after'):
            try:
                r[k] = float(r[k])
            except (ValueError, TypeError):
                r[k] = np.nan
        r['triadv'] = [float(x) for x in r['triad'].split('|')]
        r['cleared'] = r['cleared'] == '1'
        r['periods'] = WIN_UM * 1000.0 / r['lam_nm']
        r['valid'] = r['periods'] >= MIN_PERIODS
        r['targeted'] = np.isfinite(r['want'])
        r['offset'] = (cdist(r['dom_after'], r['want']) if r['targeted']
                       else np.nan)
        r['travel'] = (cdist(r['dom_before'], r['want']) if r['targeted']
                       else np.nan)
        r['moved'] = cdist(r['dom_after'], r['dom_before'])
    return rows


def q(name, val):
    print('  %-56s %s' % (name, val))


def main():
    rows = load()
    out = {}
    print('=' * 78)
    print('1. THE DATASET')
    print('=' * 78)
    q('panel rows', len(rows))
    q('distinct runs', len(set(r['stamp'] for r in rows)))
    q('distinct areas', len(set((r['area_x'], r['area_y']) for r in rows)))
    q('Lambda range (nm)', '%.0f - %.0f' % (min(r['lam_nm'] for r in rows),
                                            max(r['lam_nm'] for r in rows)))
    q('dose range (V.s/um^2)', '%.0f - %.0f' % (min(r['sigma'] for r in rows),
                                                max(r['sigma'] for r in rows)))
    out['n_rows'] = len(rows)
    out['n_areas'] = len(set((r['area_x'], r['area_y']) for r in rows))

    print()
    print('=' * 78)
    print('2. THE 4-LAMBDA READOUT GATE (PITFALLS 19.15)')
    print('=' * 78)
    bad = [r for r in rows if not r['valid']]
    q('window', '%.1f um; needs >= %.0f periods, i.e. Lambda <= %.0f nm'
      % (WIN_UM, MIN_PERIODS, LAM_MAX_NM))
    q('panels FAILING the gate', '%d of %d' % (len(bad), len(rows)))
    for r in bad:
        print('      %s %s  Lambda %.0f nm = %.2f periods  (sigma %.0f)'
              % (r['stamp'], r['panel'], r['lam_nm'], r['periods'], r['sigma']))
    rows = [r for r in rows if r['valid']]
    q('panels carried forward', len(rows))
    out['n_valid'] = len(rows)
    out['n_gated'] = len(bad)

    print()
    print('=' * 78)
    print('3. SELECTION: DOES A PANEL REACH THE DIRECTOR IT WAS COMMANDED?')
    print('=' * 78)
    tg = [r for r in rows if r['targeted']]
    hits = [r for r in tg if r['offset'] <= 15.0]
    offs = np.array([r['offset'] for r in tg])
    q('targeted panels on valid film', len(tg))
    q('within 15 deg of the commanded director', '%d  (%.0f %%)'
      % (len(hits), 100.0 * len(hits) / len(tg)))
    q('median |offset| over ALL targeted panels', '%.1f deg' % np.median(offs))
    q('median |offset| over the hits', '%.1f deg'
      % np.median([r['offset'] for r in hits]))
    q('90th percentile |offset| over the hits', '%.1f deg'
      % np.percentile([r['offset'] for r in hits], 90))
    out['n_targeted'] = len(tg)
    out['n_hit'] = len(hits)
    out['hit_pct'] = 100.0 * len(hits) / len(tg)
    out['median_offset_all'] = float(np.median(offs))
    out['median_offset_hits'] = float(np.median([r['offset'] for r in hits]))
    print('   misses:')
    for r in sorted(tg, key=lambda r: -r['offset'])[:6]:
        if r['offset'] > 15.0:
            print('      %s %s  want %.0f got %.0f  off %.0f deg  sigma %.0f'
                  % (r['stamp'], r['panel'], r['want'], r['dom_after'],
                     r['offset'], r['sigma']))

    # the film moves as far as it is sent
    tv = np.array([r['travel'] for r in tg])
    mv = np.array([r['moved'] for r in tg])
    k = tv > 5.0
    cc = float(np.corrcoef(tv[k], mv[k])[0, 1])
    q('distance commanded vs distance moved, Pearson r (travel > 5 deg)',
      '%.3f  on n = %d' % (cc, int(k.sum())))
    out['travel_r'] = cc
    out['travel_n'] = int(k.sum())

    print()
    print('=' * 78)
    print('4. EFFECT SIZE AGAINST THE PER-FRAME NULL')
    print('=' * 78)
    xn = np.array([r['x_null'] for r in tg])
    q('excess / null, median', '%.1f x' % np.median(xn))
    q('excess / null, range', '%.1f - %.1f x' % (xn.min(), xn.max()))
    q('panels clearing their own frame null', '%d of %d'
      % (sum(1 for r in tg if r['cleared']), len(tg)))
    out['xnull_median'] = float(np.median(xn))

    print()
    print('=' * 78)
    print('5. DOSE')
    print('=' * 78)
    lat = [r for r in tg if r['kind'] in ('parallel', 'sheared')]
    on = [r for r in lat if r['offset'] <= 15.0]
    off = [r for r in lat if r['offset'] > 15.0]
    q('commensurate-template panels', len(lat))
    q('on target', '%d' % len(on))
    q('LOWEST dose on target (V.s/um^2)', '%.0f' % min(r['sigma'] for r in on))
    q('off-target doses', sorted(int(r['sigma']) for r in off))
    out['sigma_min_ontarget'] = float(min(r['sigma'] for r in on))
    sol = [r for r in rows if r['kind'] == 'solid']
    q('aperiodic solid squares in the set', len(sol))
    for r in sol:
        print('      %s sigma %.0f  dominant %.0f -> %.0f  excess %.3f'
              ' = %.1f x null'
              % (r['stamp'], r['sigma'], r['dom_before'], r['dom_after'],
                 r['excess'], r['x_null']))
    # above-threshold flatness: does the outcome improve with more dose?
    hi = [r for r in on if r['sigma'] >= 100.0]
    if len(hi) > 4:
        s = np.array([r['sigma'] for r in hi])
        e = np.array([r['excess'] for r in hi])
        rr = float(np.corrcoef(np.log(s), e)[0, 1])
        q('above 100: correlation of final excess with log(dose)',
          '%.3f  on n = %d' % (rr, len(hi)))
        q('final excess above 100, range', '%.2f - %.2f' % (e.min(), e.max()))
        out['flat_r'] = rr

    print()
    print('=' * 78)
    print('6. GEOMETRY: SQUARE vs TRIANGULAR LATTICE AT THE SAME Q')
    print('=' * 78)
    sh = [r for r in rows if r['exp'] == 'shear']
    for r in sh:
        print('      %s theta %.0f deg  want %.0f  %.0f -> %.0f'
              '   excess %.3f = %.1f x null'
              % (r['stamp'], r['theta'], r['want'], r['dom_before'],
                 r['dom_after'], r['excess'], r['x_null']))
    if sh:
        q('every sheared panel reached its commanded member',
          all(r['offset'] <= 15.0 for r in sh))
        out['shear_all_hit'] = bool(all(r['offset'] <= 15.0 for r in sh))
        out['shear_n'] = len(sh)

    print()
    print('=' * 78)
    print('7. STARTING STATE DOES NOT DECIDE THE OUTCOME')
    print('=' * 78)
    same = {}
    for r in tg:
        same.setdefault(round(r['want']), []).append(r)
    for w, v in sorted(same.items()):
        if len(v) >= 3:
            befores = sorted(set(int(r['dom_before']) for r in v))
            afters = sorted(set(int(r['dom_after']) for r in v))
            print('      commanded %3d deg, n=%2d : started from %s -> ended %s'
                  % (w, len(v), befores, afters))

    print()
    print('=' * 78)
    print('7b. WHERE THE MISSES ARE: hit rate by which triad member was')
    print('    commanded. All four misses are on the SAME member index.')
    print('=' * 78)
    from math import comb
    by_idx = {}
    for r in tg:
        k = int(np.argmin([cdist(r['want'], t) for t in r['triadv']]))
        r['want_idx'] = k
        by_idx.setdefault(k, []).append(r)
    for k in sorted(by_idx):
        v = by_idx[k]
        h = sum(1 for r in v if r['offset'] <= 15.0)
        print('      member %d (approx %3.0f deg in the pinned triad): '
              '%2d panels, %2d hit, %d miss'
              % (k, np.mean([r['triadv'][k] for r in v]), len(v), h,
                 len(v) - h))
    nmiss = sum(1 for r in tg if r['offset'] > 15.0)
    worst = max(by_idx, key=lambda k: sum(1 for r in by_idx[k]
                                          if r['offset'] > 15.0))
    nw = len(by_idx[worst])
    # if misses were spread over panels at random, P(all of them in this member)
    p_all = (nw / float(len(tg))) ** nmiss
    print('      all %d misses fall in member %d (%d of %d panels).'
          % (nmiss, worst, nw, len(tg)))
    print('      P(that by chance, misses placed at random) = %.4f' % p_all)
    print('      NOT a controlled result: member index is confounded with')
    print('      panel position (member 2 is always the P2 panel) and with')
    print('      the lab-frame scan direction. Reported as a lead, not a')
    print('      finding.')
    out['miss_member'] = worst
    out['miss_p_all'] = float(p_all)

    print()
    print('=' * 78)
    print('8. WHAT IS NOT ESTABLISHED')
    print('=' * 78)
    print('   * no lattice failure was observed on VALID film at any dose down')
    print('     to sigma 52, so the lattice threshold is a BOUND, not a')
    print('     measurement.')
    print('   * the crosstalk hypothesis (M21) is graded C and its one')
    print('     controlled test was underpowered: Fisher p = 1.000.')
    print('   * the crystallographic identity of the nano-domains is NOT')
    print('     claimed; this work measures orientation, not lattice vectors.')

    io.open(os.path.join(HERE, 'summary_stats.json'), 'w',
            encoding='utf-8').write(json.dumps(out, indent=1))
    print()
    print('numbers cached to summary_stats.json')


if __name__ == '__main__':
    main()
