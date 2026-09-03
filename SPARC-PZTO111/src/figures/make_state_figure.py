# -*- coding: utf-8 -*-
"""Fig 0 — what the state variable is, on real data from the R6 baseline area."""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJ = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJ.parent.parent / "Styles"))
import publication_style as ps
import aug_toolkit as T

ps.configure_style()
C = ps.COLORS
N = json.loads((PROJ / "aug_numbers.json").read_text())
NS = T.load_toolkit()
angular_power = NS["angular_power"]

TRI = N["R6"]["triad"]
P = N["R6"]["panels"]

fig = plt.figure(figsize=(7.4, 2.30))
gs = fig.add_gridspec(1, 3, left=0.045, right=0.988, bottom=0.20, top=0.86,
                      width_ratios=[0.92, 1.35, 1.0], wspace=0.42)

# (a) the three allowed directors
ax = fig.add_subplot(gs[0, 0])
for t, col in zip(TRI, (C["blue"], C["orange"], C["green"])):
    a = np.deg2rad(t)
    ax.plot([-np.cos(a), np.cos(a)], [-np.sin(a), np.sin(a)], lw=2.2, color=col)
    ax.text(1.16 * np.cos(a), 1.16 * np.sin(a), f"{t:.0f}°", ha="center",
            va="center", fontsize=7.4, color=col)
ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.45, 1.45)
ax.set_xticks([]); ax.set_yticks([])
ax.set_box_aspect(1)
ps.close_frame(ax)
ax.set_xlabel("three directors, 60° apart")

# (b) angular power spectrum with the wedges shaded
ax = fig.add_subplot(gs[0, 1])
ctr, pw = angular_power("PZTO_LDART_0034.ibw")
ax.plot(ctr, pw * 100, lw=1.3, color=C["grey"])
for t, col in zip(TRI, (C["blue"], C["orange"], C["green"])):
    for lo in (t - 15, t - 15 + 180, t - 15 - 180):   # the wedge wraps mod 180
        ax.axvspan(lo, lo + 30, color=col, alpha=0.14, lw=0)
    ax.axvline(t, color=col, lw=0.8, ls=":")
ax.set_xlim(0, 180); ax.set_xticks([0, 60, 120, 180])
ax.set_xlabel("stripe director (deg)")
ax.set_ylabel("angular power (%)")
ax.set_ylim(0, None)
ps.close_frame(ax)

# (c) population vector, virgin vs written
ax = fig.add_subplot(gs[0, 2])
x = np.arange(3); w = 0.36
ax.bar(x - w / 2, P["P3"]["w"][0], w, color=C["light_grey"], edgecolor="none",
       label="virgin")
ax.bar(x + w / 2, P["P3"]["w"][1], w, color=C["blue"], edgecolor="none",
       label="after write")
ax.axhline(1 / 3, color=C["grey"], lw=0.8, ls=":")
ax.text(2.44, 1 / 3 + 0.03, "equal", fontsize=6.2, ha="right", color=C["grey"])
ax.set_xticks(x); ax.set_xticklabels([f"{t:.0f}°" for t in TRI], fontsize=7.4)
ax.set_ylabel("population $w$")
ax.set_ylim(0, 1.05)
ps.boxed_legend(ax, loc="upper center", fontsize=6.4, labelspacing=0.2,
                handlelength=0.9, borderpad=0.25)
ps.close_frame(ax)

ps.align_panel_letters(fig, [[(0, fig.axes[0], "a"), (1, fig.axes[1], "b"),
                             (2, fig.axes[2], "c")]])
ps.save_figure(fig, PROJ / "figures_aug", "Fig0_state_variable",
               formats=("png", "pdf", "svg"), pad_inches=0.05)
print("ok")
