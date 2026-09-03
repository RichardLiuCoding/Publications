# -*- coding: utf-8 -*-
"""Recompute every number quoted in the 14-15 Aug summary from the raw .ibw files.

Writes aug_numbers.json so the figure and document scripts never hard-code a
quantity that was not re-derived from data.
"""

import json
from pathlib import Path

import numpy as np

import aug_toolkit as T

PROJ = Path(__file__).resolve().parent
OUT = PROJ / "aug_numbers.json"

NS = T.load_toolkit()
ibw, signed, dp, fit = NS["ibw"], NS["signed"], NS["dir_power"], NS["fit_triad"]
period, angular_power = NS["period"], NS["angular_power"]

# --------------------------------------------------------------- geometry
R6 = dict(
    frames=dict(base1="PZTO_LDART_0033.ibw", base="PZTO_LDART_0034.ibw",
                afterA="PZTO_LDART_0035.ibw", afterB="PZTO_LDART_0036.ibw"),
    centres=dict(P1=1.6, P2=4.0, P3=6.4), box=2.0, y=4.0,
)
R5 = dict(base="PZTO_LDART_0031.ibw", after="PZTO_LDART_0032.ibw",
          centres=dict(test=2.2, ctrl=5.8), box=2.94, y=4.0)
R7 = dict(frames=["PZTO_LDART_0038.ibw", "PZTO_LDART_0039.ibw",
                  "PZTO_LDART_0040.ibw", "PZTO_LDART_0041.ibw"],
          centres=dict(Q1=(2.2, 5.8), Q2=(5.8, 5.8), Q3=(2.2, 2.2), Q4=(5.8, 2.2)),
          box=2.0)


def lam_nm(tag, triad):
    d, h = ibw(tag)
    n = d[0].shape[0]
    px = float(h["ScanSize"]) * 1e6 / n * 1000.0
    S, _, _ = signed(d)
    vals = []
    for f in triad:
        v = period(S, px, f)
        vals.append(float(v[0]) if isinstance(v, (tuple, list, np.ndarray)) else float(v))
    return float(np.nanmedian(vals)), [float(v) for v in vals]


def sites_from(path):
    """Pulse sites = runs of consecutive live-bias points at one coordinate."""
    a = np.loadtxt(path)
    x, y, v = a[:, 0] * 1e6, a[:, 1] * 1e6, a[:, 2]
    live = np.abs(v) > 1e-9
    out, i, n = [], 0, len(v)
    while i < n:
        if not live[i]:
            i += 1
            continue
        j = i
        while (j + 1 < n and live[j + 1]
               and abs(x[j + 1] - x[i]) < 1e-6 and abs(y[j + 1] - y[i]) < 1e-6):
            j += 1
        out.append((x[i], y[i], v[i], j - i + 1))
        i = j + 1
    return np.array(out), a


def main():
    res = {}

    # ---------------------------------------------------------- R6 rewrite
    tri6 = fit(R6["frames"]["base"], verbose=False)
    triad6 = [float(x) for x in sorted(tri6["fam"])]
    lam6, lam6_fam = lam_nm(R6["frames"]["base"], triad6)
    A_DEG, B_DEG = triad6[0], triad6[2]
    res["R6"] = dict(triad=triad6, mod=float(tri6["mod"]), lam_nm=lam6,
                     lam_per_family=lam6_fam, A=A_DEG, B=B_DEG,
                     spacing_nm=0.5 * lam6, panels={})
    order = [("virgin", R6["frames"]["base"]), ("afterA", R6["frames"]["afterA"]),
             ("afterB", R6["frames"]["afterB"])]
    for nm, cx in R6["centres"].items():
        rg = T.region(cx, R6["y"], R6["box"])
        rec = dict(powA=[], powB=[], peak=[], w=[])
        for _, f in order:
            wa, pk, _ = dp(f, rg, A_DEG)
            wb, _, _ = dp(f, rg, B_DEG)
            rec["powA"].append(float(wa))
            rec["powB"].append(float(wb))
            rec["peak"].append(float(pk))
            rec["w"].append([float(v) for v in T.popvec(dp, f, rg, triad6)])
        res["R6"]["panels"][nm] = rec

    # temporal floor: two baseline frames, nothing done between them
    floor = []
    for nm, cx in R6["centres"].items():
        rg = T.region(cx, R6["y"], R6["box"])
        for tgt in (A_DEG, B_DEG):
            a, _, _ = dp(R6["frames"]["base1"], rg, tgt)
            b, _, _ = dp(R6["frames"]["base"], rg, tgt)
            floor.append(abs(b - a))
    res["R6"]["floor_mean"] = float(np.mean(floor))
    res["R6"]["floor_max"] = float(np.max(floor))

    # ---------------------------------------------------------- lattices
    res["lattice"] = {}
    cen = {"P1": (1.6, 4.0), "P2": (4.0, 4.0), "P3": (6.4, 4.0)}
    for key, fn in (("A", "260814_R6_writeA.txt"), ("B", "260814_R6_writeB.txt")):
        s, raw = sites_from(PROJ / "output" / fn)
        d = np.stack([np.hypot(s[:, 0] - c[0], s[:, 1] - c[1]) for c in cen.values()])
        lab = np.array(list(cen))[np.argmin(d, 0)]
        panels = {}
        for k in cen:
            m = lab == k
            if m.sum() == 0:
                continue
            P = s[m]
            D = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1])
            np.fill_diagonal(D, 9e9)
            panels[k] = dict(n=int(m.sum()), n_pos=int((P[:, 2] > 0).sum()),
                             n_neg=int((P[:, 2] < 0).sum()),
                             mean_V=float(P[:, 2].mean()),
                             nn_nm=float(np.median(D.min(1)) * 1000),
                             side=int(round(np.sqrt(m.sum()))))
        res["lattice"][key] = dict(
            n_sites=int(len(s)), pts_per_pulse=int(np.median(s[:, 3])),
            V=float(np.abs(s[:, 2]).max()), path_pts=int(len(raw)),
            mean_V_path=float(raw[:, 2].mean()),
            dwell_s=float(np.median(s[:, 3]) * 0.02 / 0.5),
            charge_Vs=float(np.abs(s[:, 2]).max() * np.median(s[:, 3]) * 0.02 / 0.5),
            minutes=float(len(raw) * 0.02 / 0.5 / 60.0),
            panels=panels)

    # ---------------------------------------------------------- R5 allowed/forbidden
    tri5 = fit(R5["base"], verbose=False)
    triad5 = [float(x) for x in sorted(tri5["fam"])]
    res["R5"] = dict(triad=triad5, mod=float(tri5["mod"]), cmd_test=30.0,
                     cmd_ctrl=float(min(triad5, key=lambda t: abs((t - 2.0 + 90) % 180 - 90))),
                     panels={})
    for nm, cx in R5["centres"].items():
        rg = T.region(cx, R5["y"], R5["box"])
        rec = dict(angles=[30.0] + triad5, before=[], after=[], peak=[])
        for tgt in rec["angles"]:
            b, _, _ = dp(R5["base"], rg, tgt)
            a, _, _ = dp(R5["after"], rg, tgt)
            rec["before"].append(float(b))
            rec["after"].append(float(a))
        _, pb, _ = dp(R5["base"], rg, 0.0)
        _, pa, _ = dp(R5["after"], rg, 0.0)
        rec["peak"] = [float(pb), float(pa)]
        res["R5"]["panels"][nm] = rec

    # ---------------------------------------------------------- R7 raster / lattice
    tri7 = fit(R7["frames"][0], verbose=False)
    triad7 = [float(x) for x in sorted(tri7["fam"])]
    M = triad7[0]
    LAT = float(np.mod(M + 60.0, 180.0))
    res["R7"] = dict(triad=triad7, M=M, LAT=LAT, panels={})
    for k, c in R7["centres"].items():
        rg = T.region(c[0], c[1], R7["box"])
        res["R7"]["panels"][k] = dict(
            pow_LAT=[float(dp(f, rg, LAT)[0]) for f in R7["frames"]],
            pow_M=[float(dp(f, rg, M)[0]) for f in R7["frames"]],
            w=[[float(v) for v in T.popvec(dp, f, rg, triad7)] for f in R7["frames"]],
        )

    OUT.write_text(json.dumps(res, indent=1))
    print("wrote", OUT)

    # ------------------------------------------------------------ summary
    p = res["R6"]["panels"]
    print(f"\nR6 triad {triad6}  Lambda {lam6:.0f} nm  spacing {0.5*lam6:.0f} nm")
    print(f"  floor mean {res['R6']['floor_mean']:.3f} max {res['R6']['floor_max']:.3f}")
    for k in ("P1", "P2", "P3"):
        r = p[k]
        print(f"  {k}: peak {r['peak'][0]:.0f} -> {r['peak'][1]:.0f} -> {r['peak'][2]:.0f}"
              f"   powA {r['powA'][0]:.3f}/{r['powA'][1]:.3f}/{r['powA'][2]:.3f}"
              f"   powB {r['powB'][0]:.3f}/{r['powB'][1]:.3f}/{r['powB'][2]:.3f}")
    for key in ("A", "B"):
        L = res["lattice"][key]
        print(f"  write {key}: {L['n_sites']} pulses, {L['charge_Vs']:.0f} V.s each, "
              f"{L['minutes']:.1f} min, panels "
              + ", ".join(f"{k}:{v['side']}x{v['side']}@{v['nn_nm']:.0f}nm"
                          for k, v in L["panels"].items()))


if __name__ == "__main__":
    main()
