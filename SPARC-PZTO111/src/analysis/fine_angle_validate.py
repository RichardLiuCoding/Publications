# -*- coding: utf-8 -*-
"""fine_angle_validate.py -- is the matched-filter peak ACCURATE, not just
repeatable?

fine_angle.py finds that two independent images of the same panel give peak
directions agreeing to 0.19 deg. That is precision. It says nothing about
bias: a systematic error that is the same in both images -- from the square
window, from the Hermitian half-plane, from the parabolic interpolation, or
from the pixel grid itself -- would repeat perfectly and still be wrong.

Before any claim rests on a sub-degree angle, the estimator has to recover
directions it was given. This builds lamellar fields at known directions
spanning a full 60 deg, at the periods, window size and signal-to-noise of the
real panels, and measures what comes back.

PITFALLS 21.1-21.4 are all cases where an estimator returned a confident
number that was an artefact of its own machinery.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scale_tools as ST
from fine_angle import peak_angle, wrap180

PX = 4.88                      # nm/px, as imaged
WIN_UM = 1.2                   # readout window
N = int(round(WIN_UM * 1000.0 / PX))


def synth(n, px, lam, director_deg, amp, seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] * px
    t = np.radians(director_deg + 90.0)
    ph = 2 * np.pi * (x * np.cos(t) + y * np.sin(t)) / lam
    return amp * np.sin(ph) + rng.normal(0, 1.0, (n, n))


def main():
    print('=' * 78)
    print('FINE-ANGLE ACCURACY  (%d x %d px window = %.2f um at %.2f nm/px)'
          % (N, N, WIN_UM, PX))
    print('=' * 78)
    print('%8s %8s %8s %9s %9s' % ('true', 'lambda', 'snr', 'measured', 'error'))
    err = []
    for lam in (210.0, 253.0, 295.0):
        for snr in (0.5, 1.0, 2.0):
            for k, true in enumerate(np.arange(0.0, 60.0, 7.5)):
                S = synth(N, PX, lam, true, snr, seed=1000 + k)
                d0, an, per, pv = ST.band_peak(S, PX, 150.0, 500.0, n_perm=1)
                pk, _, _ = peak_angle(S, PX, d0, lam)
                e = wrap180(pk - true)
                err.append(e)
                if k == 0:
                    print('%8.1f %8.0f %8.1f %9.2f %+9.2f'
                          % (true, lam, snr, pk % 180.0, e))
    err = np.array(err)
    print('\n  %d cases: bias %+.3f deg, rms %.3f deg, max |error| %.2f deg'
          % (len(err), err.mean(), err.std(), np.abs(err).max()))
    if np.abs(err.mean()) < 0.2 and np.abs(err).max() < 1.0:
        print('  -> accurate at the sub-degree level; no systematic bias with')
        print('     direction, period or signal-to-noise in this range.')
    else:
        print('  -> BIASED. Sub-degree angles from this estimator are not safe.')

    # does the error depend on where the stripes sit relative to the pixel
    # grid? that is the classic source of an angle-dependent bias.
    print('\n  error vs true direction, averaged over period and snr:')
    for k, true in enumerate(np.arange(0.0, 60.0, 7.5)):
        sub = []
        for lam in (210.0, 253.0, 295.0):
            for snr in (0.5, 1.0, 2.0):
                S = synth(N, PX, lam, true, snr, seed=1000 + k)
                d0, an, per, pv = ST.band_peak(S, PX, 150.0, 500.0, n_perm=1)
                sub.append(wrap180(peak_angle(S, PX, d0, lam)[0] - true))
        print('    %5.1f deg : %+6.2f +/- %.2f'
              % (true, np.mean(sub), np.std(sub)))


if __name__ == '__main__':
    main()
