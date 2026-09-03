# -*- coding: utf-8 -*-
"""Two provenance checks on the R6 result.

1. Is every frame we call LDART actually acquired on the lateral contact
   resonance?  The filename is set by `exp.execute('ChangeName', ...)` inside
   goto_ldart(), so it records an intent, not a measurement.  The campaign has
   already been bitten once by this (a GATE cell scored an LDART frame with
   orbit_balance and reported an in-plane sign balance as an out-of-plane one).

2. Did anything other than the two pulse lattices run in the R6 area between
   the baseline and the final frame?

Writes aug_provenance.json.
"""

import glob
import json
import os
from pathlib import Path

import aespm as ae
import numpy as np

PROJ = Path(__file__).resolve().parent
DATA = PROJ / "260813" / "PZTO"

LATERAL = (450e3, 850e3)     # contact resonance band, lateral (torsional)
VERTICAL = (150e3, 450e3)    # contact resonance band, vertical (flexural)

R6_FRAMES = ["PZTO_LDART_0033.ibw", "PZTO_LDART_0034.ibw",
             "PZTO_LDART_0035.ibw", "PZTO_LDART_0036.ibw"]
R6_WRITES = ["260814_R6_writeA.txt", "260814_R6_writeB.txt"]


def band(f):
    if LATERAL[0] <= f <= LATERAL[1]:
        return "lateral"
    if VERTICAL[0] <= f <= VERTICAL[1]:
        return "vertical"
    return "out of band"


def check_channels():
    """Filename vs commanded drive vs the tracked resonance actually measured."""
    rows = []
    for path in sorted(glob.glob(str(DATA / "PZTO_*DART_*.ibw"))):
        im = ae.tools.load_ibw(path)
        d = [np.asarray(x, float) for x in im.data]
        h = im.header
        tag = os.path.basename(path)
        label = "LDART" if "LDART" in tag else "VDART"
        drive = float(h["DriveFrequency"])
        tracked = float(np.median(d[5]))          # index 5 is the frequency channel
        want = "lateral" if label == "LDART" else "vertical"
        rows.append(dict(
            tag=tag, label=label, drive_hz=drive, tracked_hz=tracked,
            drive_band=band(drive), tracked_band=band(tracked),
            agrees=(band(drive) == want and band(tracked) == want),
            setpoint=float(h.get("DeflectionSetpointVolts", float("nan"))),
            lateral_input=str(h.get("Lateral", "?")),
            dual_ac=int(float(h.get("DualACMode", -1))),
        ))
    return rows


def identify_channels(tag="PZTO_LDART_0034.ibw"):
    """Confirm the array order aespm returns, from the data itself."""
    d = [np.asarray(x, float) for x in ae.tools.load_ibw(str(DATA / tag)).data]
    out = []
    for i, a in enumerate(d):
        med, mx, mn, sd = np.median(a), a.max(), a.min(), a.std()
        if 1e5 < med < 1e6:
            kind = "frequency (Hz)"
        elif mx < 1e-8 and mn >= 0:
            kind = "amplitude (m)"
        elif -180 <= mn and mx <= 360 and sd > 20:
            kind = "phase (deg)"
        else:
            kind = "height (m)"
        out.append(dict(index=i, kind=kind, median=float(med), std=float(sd)))
    return out


def check_sequence():
    """Every biased operation in the R6 area, and what kind it was."""
    out = []
    for fn in R6_WRITES:
        a = np.loadtxt(PROJ / "output" / fn)
        x, y, v = a[:, 0] * 1e6, a[:, 1] * 1e6, a[:, 2]
        live = np.abs(v) > 1e-9
        pulses = strokes = 0
        i, n = 0, len(v)
        while i < n:
            if not live[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and live[j + 1]:
                j += 1
            sl = slice(i, j + 1)
            moved = float(np.hypot(np.ptp(x[sl]), np.ptp(y[sl])))
            if moved < 1e-4:
                pulses += 1
            else:
                strokes += 1
            i = j + 1
        out.append(dict(file=fn, points=int(len(a)), stationary_pulses=pulses,
                        biased_strokes=strokes, mean_V=float(v.mean()),
                        Vmax=float(np.abs(v).max())))
    return out


def main():
    ch = check_channels()
    bad = [r for r in ch if not r["agrees"]]
    r6 = [r for r in ch if r["tag"] in R6_FRAMES]
    seq = check_sequence()
    ident = identify_channels()

    print(f"1. CHANNEL — {len(ch)} DART frames checked, "
          f"{len(bad)} disagree with their filename")
    for r in r6:
        print(f"     {r['tag']:22s} drive {r['drive_hz']/1e3:6.1f} kHz  "
              f"tracked {r['tracked_hz']/1e3:6.1f} kHz  -> {r['tracked_band']}  "
              f"setpoint {r['setpoint']:.2f} V")
    print(f"     header: Lateral = {r6[0]['lateral_input']}, "
          f"DualACMode = {r6[0]['dual_ac']}")
    print("     array order returned by aespm:")
    for e in ident:
        print(f"       [{e['index']}] {e['kind']}")

    print("\n2. SEQUENCE — every biased operation in the R6 area")
    for s in seq:
        print(f"     {s['file']:24s} {s['stationary_pulses']:4d} pulses, "
              f"{s['biased_strokes']:3d} strokes, mean V {s['mean_V']:+.5f}")

    (PROJ / "aug_provenance.json").write_text(json.dumps(
        dict(channels=ch, r6_frames=r6, r6_writes=seq, array_order=ident), indent=1))
    print("\nwrote aug_provenance.json")


if __name__ == "__main__":
    main()
