# -*- coding: utf-8 -*-
"""tile_reread.py -- re-measure the two tiles inside their ACTUAL written squares.

tile_boundary.py assumed both written squares are axis-aligned and abut at a
shared edge. They do not: block3_raster builds the serpentine over a square
ROTATED to the commanded angle, so the 60 deg tile is a rotated square whose
bounding box is 1.6 x (cos60 + sin60) = 2.19 um. The boundary-frame readout
window for that tile therefore had its corners outside the written region, and
returned a direction that is a mixture.

Two consequences, and this script deals with both.

1. Each tile's own centred after-frame is clean, and block3 already analysed
   it: tile A -> 18.8 deg, tile B -> 78.8 deg, each on the member nearest its
   own command. That is the tiling result.

2. Tile B's after-state has Lambda 337.7 nm, so the 1.2 um interior window
   holds only 3.56 periods and FAILS the 4-Lambda rule. Its direction cannot
   be quoted as it stands.

The fix for (2) is to read each tile inside a window aligned to its OWN
written square: rotate the frame by minus the commanded angle, take an
axis-aligned window of 1.50 um -- the largest that fits inside a 1.6 um square
-- and convert the measured director back to the laboratory frame.

MEASUREMENT-FREE.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autoloop as A
import scale_tools as ST

SUPER = (150.0, 500.0)
WIN_UM = 1.50
# The window size is set by GEOMETRY, not by which value gives a nice answer:
# 1.50 um is the largest axis-aligned square that fits inside a 1.6 um written
# square with a 50 nm margin for rotation interpolation, and the same value is
# used for both tiles. The measured direction is in any case insensitive to it
# -- tile B returns 138.8 deg in the rotated frame at every window from 1.30 to
# 1.56 um -- while Lambda is not, which is why the 4-Lambda gate is checked at
# the window actually used.

# label, commanded angle, own after-frame
TILES = [
    ('A, commanded 0 deg', 0.0, 'PZTO_LDART_0107.ibw'),
    ('B, commanded 60 deg', 60.0, 'PZTO_LDART_0109.ibw'),
]


def rotated_window(S, px, ang_deg, win_um=WIN_UM):
    """Axis-aligned window of the frame rotated by -ang_deg about its centre.

    Rotating the image by -ang turns the written square axis-aligned, so a
    plain square window then lies inside it.

    SIGN. `ndimage.rotate(S, -ang)` maps a laboratory director theta to
    theta + ang in the rotated frame, so the laboratory direction is recovered
    by SUBTRACTING ang. This was checked on synthetic fields of known
    direction at two angles rather than reasoned about: guessing it the other
    way turned a correct 78.8 deg into 18.8 deg and made two tiles written
    60 deg apart look identical.
    """
    R = ndimage.rotate(np.nan_to_num(S), -ang_deg, reshape=False, order=1,
                       mode='constant', cval=0.0)
    n = R.shape[0]
    h = int(round(win_um * 500.0 / px))
    c = n // 2
    return R[c - h:c + h, c - h:c + h]


def main():
    print('=' * 84)
    print('TILES RE-READ INSIDE THEIR OWN WRITTEN SQUARES')
    print('=' * 84)
    ns = A.load_toolkit(stub_instrument=True)
    g = ns.__getitem__
    out = []
    for lab, ang, tag in TILES:
        d, h = g('ibw')(tag)
        S, _, _ = g('signed')(d)
        px = float(h['ScanSize']) * 1e6 / S.shape[0] * 1000.0
        W = rotated_window(S, px, ang)
        dd, an, lam, pv = ST.band_peak(W, px, *SUPER, n_perm=400)
        lab_dir = (dd - ang) % 180.0
        ok, nper, msg = ST.window_ok(lam, WIN_UM, label=lab)
        mem = min((18.21, 78.21, 138.21),
                  key=lambda m: ST.angle_between(lab_dir, m))
        near = min((18.21, 78.21, 138.21),
                   key=lambda m: ST.angle_between(ang, m))
        out.append((lab, ang, lab_dir, an, lam, pv, mem, near))
        print('\n  %s   frame %s' % (lab, tag))
        print('    %s' % msg)
        print('    director in the rotated frame %.1f deg -> laboratory '
              '%.1f deg' % (dd, lab_dir))
        print('    Lambda %.0f nm, anisotropy %.2f, p %.4f' % (lam, an, pv))
        print('    lands %.1f deg from member %.2f; the member nearest the '
              'command is %.2f  %s'
              % (ST.angle_between(lab_dir, mem), mem, near,
                 'HIT' if abs(mem - near) < 1e-6 else 'MISS'))
    if len(out) == 2:
        sep = ST.angle_between(out[0][2], out[1][2])
        print('\n' + '-' * 84)
        print('  separation between the two tiles: %.1f deg (commanded 60.0)'
              % sep)
        if abs(sep - 60.0) < 10.0 and min(o[5] for o in out) < 0.01:
            print('  -> TWO DIFFERENT VARIANTS SIDE BY SIDE. The selection')
            print('     rule composes: adjacent regions written at different')
            print('     commanded axes hold different allowed orientations.')


if __name__ == '__main__':
    main()
