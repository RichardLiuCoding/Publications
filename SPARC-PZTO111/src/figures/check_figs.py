# -*- coding: utf-8 -*-
"""check_figs.py -- every figure on disk is referenced, every reference exists.

PITFALLS 21.15: make_ms_figures.py built six panels, MS_main.md carried five
image directives, and the converter reported "5 figures" and exited 0. A count
is not a check. Run this before any document build.
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = ('MS_main.md', 'MS_supp.md')
PAT = re.compile(r'\]\(([^)]+\.png)\)\{width')


def main():
    ref = {}
    for f in DOCS:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for m in PAT.findall(io.open(p, encoding='utf-8').read()):
            ref.setdefault(m.replace('\\', '/'), []).append(f)
    disk = set(p.replace(os.sep, '/')[len(HERE) + 1:]
               for p in glob.glob(os.path.join(HERE, 'figures_ms', '*.png')))
    orphan = sorted(disk - set(ref))
    broken = sorted(set(ref) - disk)
    dup = sorted(k for k, v in ref.items() if len(v) > 1)

    print('%d figures on disk, %d referenced' % (len(disk), len(ref)))
    for k in sorted(ref):
        print('  %-40s %s' % (k, ','.join(ref[k])))
    if orphan:
        print('\nORPHAN (built but never placed in the text):')
        for k in orphan:
            print('  ' + k)
    if broken:
        print('\nBROKEN (referenced but not on disk):')
        for k in broken:
            print('  ' + k)
    if dup:
        print('\nreferenced more than once: %s' % ', '.join(dup))
    ok = not orphan and not broken
    print('\n%s' % ('OK' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
