"""Fold-clean recomputation of the Fig. 5 mechanism quantities (revision 2026-09).

Blocked (speed, drive) 5-fold scheme. For every held-out condition:
  - deterministic twin with GP gains calibrated outside the held-out block,
  - global-gain re-simulation (one P0, I0 = median of the allowed local PI fits),
  - zero-fit operating-point amplification factor 1/|dA/dd|(d_op) from the FD library,
  - controls-only kNN prediction (from the benchmark run).
Spearman rho with the experimental Q_align, with 95% block-bootstrap intervals.
Writes output/mechanism_block5.npz and output/mechanism_block5.json.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.stats import spearmanr

from rv_benchmark import block_folds
from rv_common import OUT, center_line, q_align, simulate
from rv_tap300 import PhysicsPrior, allowed_from_heldout, build_table


def line_sd(lines, trim=8):
    out = np.full(len(lines), np.nan)
    for i, l in enumerate(lines):
        t = l[0] - np.nanmedian(l[0][trim:-trim]); out[i] = np.nanstd(t[trim:-trim])
    return out


def boot_rho(y, p, blocks, n=2000, seed=11):
    rng = np.random.default_rng(seed); ub = np.unique(blocks)
    ib = {b: np.where(blocks == b)[0] for b in ub}; r = []
    for _ in range(n):
        ii = np.concatenate([ib[b] for b in rng.choice(ub, ub.size)])
        m = np.isfinite(p[ii]) & np.isfinite(y[ii])
        r.append(spearmanr(y[ii][m], p[ii][m]).statistic)
    return [float(np.nanpercentile(r, 2.5)), float(np.nanpercentile(r, 97.5))]


def main():
    T = build_table(); pp = PhysicsPrior(T); raw = T["raw"]
    folds = block_folds(T["group"], 5)
    N = T["N"]
    Q_twin = np.full(N, np.nan); Q_glob = np.full(N, np.nan)
    L_twin = np.full((N, 2, 256), np.nan)
    for te in folds:
        allowed = allowed_from_heldout(T, te, "speed_drive")
        r = pp.run(allowed, return_lines=True)
        Q_twin[te] = r["Q_sim"][te]; L_twin[te] = r["lines"][te]
        use = [x for x in pp.local if allowed[tuple(int(v) for v in x["cond"])]]
        P0 = 10 ** np.median([x["log10_P"] for x in use]); I0 = 10 ** np.median([x["log10_I"] for x in use])
        for c in te:
            a, b_, cc = T["si"][c], T["di"][c], T["spi"][c]
            out = simulate(pp.scanner, pp._fd_table(b_), r["h_ref"], raw["drive_exp"][b_],
                           raw["setpoint_exp"][cc], raw["scan_rate"][a], P0, I0)
            Q_glob[c] = q_align(center_line(out["trace"]["d_hat"]), center_line(out["retrace"]["d_hat"]))
    amp = 1.0 / np.clip(T["slope"], 1e-4, None)
    bench = np.load(OUT / "tap300_benchmark_block5.npz")
    knn = 10 ** bench["Q_align__knn_ctrl"]
    y = T["Q_align"]; g = T["group"]
    res = {}
    for name, p in [("controls_kNN", knn), ("deterministic_twin", Q_twin),
                    ("global_gain_resim", Q_glob), ("amplification_factor", amp),
                    ("setpoint", T["setpoint"])]:
        m = np.isfinite(p)
        res[name] = dict(rho=float(spearmanr(y[m], p[m]).statistic), CI=boot_rho(y, p, g), n=int(m.sum()))
    sd_exp = line_sd(T["exp_lines"]); sd_twin = line_sd(L_twin)
    by_sp = {f"{s:.1f}": dict(exp_median_sd=float(np.nanmedian(sd_exp[T['setpoint'] == s])),
                              exp_p90_sd=float(np.nanpercentile(sd_exp[T['setpoint'] == s], 90)),
                              twin_median_sd=float(np.nanmedian(sd_twin[T['setpoint'] == s])),
                              twin_p90_sd=float(np.nanpercentile(sd_twin[T['setpoint'] == s], 90)),
                              exp_median_Qalign=float(np.nanmedian(y[T['setpoint'] == s])),
                              exp_p90_Qalign=float(np.nanpercentile(y[T['setpoint'] == s], 90)))
             for s in np.unique(T["setpoint"])}
    res["line_sd_by_setpoint"] = by_sp
    np.savez(OUT / "mechanism_block5.npz", Q_twin=Q_twin, Q_glob=Q_glob, amp=amp, knn=knn,
             sd_exp=sd_exp, sd_twin=sd_twin, Q_align=y, setpoint=T["setpoint"], group=g)
    json.dump(res, open(OUT / "mechanism_block5.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
