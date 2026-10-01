from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import gridspec
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from codes.nature_statement_figures import (
    NATURE_DIRNAME,
    PALETTE,
    _controller_data,
    _fd_data,
    _project,
    _strict_holdout_arrays,
    panel_label,
    save_pub,
    setup_style,
)


def _box(ax, xy, wh, text, color, fc="white", fontsize=7.1, lw=1.1):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        fc=fc,
        ec=color,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, color=PALETTE["ink"])
    return patch


def _arrow(ax, start, end, color=None, lw=0.9):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            lw=lw,
            color=color or PALETTE["muted"],
            shrinkA=3,
            shrinkB=3,
        )
    )


def _mini_table(ax, rows, col_x, y0=0.84, dy=0.14, header=None, fontsize=6.4):
    ax.axis("off")
    if header:
        for x, h in zip(col_x, header):
            ax.text(x, y0, h, fontsize=fontsize, fontweight="bold", ha="left", va="top", color=PALETTE["ink"])
        y0 -= dy * 0.75
    for i, row in enumerate(rows):
        y = y0 - i * dy
        fill = "#F8FAFC" if i % 2 == 0 else "white"
        ax.add_patch(FancyBboxPatch((0.0, y - dy + 0.015), 0.98, dy - 0.02, boxstyle="round,pad=0.004,rounding_size=0.01", fc=fill, ec="#E5E7EB", lw=0.4))
        for x, cell in zip(col_x, row):
            ax.text(x, y - 0.012, cell, fontsize=fontsize, ha="left", va="top", color=PALETTE["ink"], wrap=True)


def build_figure_1(project_root: str | Path = ".") -> dict[str, str]:
    """Framework figure: what must be calibrated, by whom, and what the DT enables."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME

    fig = plt.figure(figsize=(7.2, 4.7), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1.35, 1.0, 1.05], height_ratios=[1.08, 0.92])
    fig.subplots_adjust(left=0.055, right=0.985, bottom=0.10, top=0.84, wspace=0.42, hspace=0.48)
    fig.suptitle("DT-SPM becomes useful when experiment calibrates a modular microscope twin", x=0.055, y=0.965, ha="left", fontsize=9.8, fontweight="bold")

    ax = fig.add_subplot(gs[:, 0])
    ax.axis("off")
    panel_label(ax, "a", x=-0.02, y=1.02)
    ax.text(0.02, 0.98, "Calibration architecture", fontsize=7.8, fontweight="bold", va="top")
    _box(ax, (0.04, 0.78), (0.31, 0.12), "Vendor\nhardware DT", PALETTE["blue"], fc="#EFF6FF")
    _box(ax, (0.42, 0.78), (0.31, 0.12), "Known-physics\nreference samples", PALETTE["teal"], fc="#ECFDF5")
    _box(ax, (0.23, 0.56), (0.31, 0.12), "User sample\nFD + grid scans", PALETTE["orange"], fc="#FFF7ED")
    _box(ax, (0.04, 0.34), (0.25, 0.11), "Predict\nsafe settings", PALETTE["purple"], fc="#F5F3FF")
    _box(ax, (0.36, 0.34), (0.25, 0.11), "Interpret\nresiduals", PALETTE["red"], fc="#FEF2F2")
    _box(ax, (0.68, 0.34), (0.25, 0.11), "Update\nlatent state", PALETTE["grey"], fc="#F9FAFB")
    _arrow(ax, (0.35, 0.84), (0.42, 0.84))
    _arrow(ax, (0.57, 0.78), (0.43, 0.68))
    _arrow(ax, (0.22, 0.78), (0.33, 0.68))
    _arrow(ax, (0.38, 0.56), (0.18, 0.45))
    _arrow(ax, (0.38, 0.56), (0.48, 0.45))
    _arrow(ax, (0.38, 0.56), (0.80, 0.45))
    _arrow(ax, (0.80, 0.34), (0.47, 0.62), color=PALETTE["muted"], lw=0.7)
    ax.text(0.04, 0.16, "Core principle", fontsize=7.2, fontweight="bold", color=PALETTE["ink"])
    ax.text(0.04, 0.08, "Do not ask each experiment to rediscover the microscope.\nPre-calibrate hardware; update sample physics and state.", fontsize=6.5, color=PALETTE["muted"], va="top")

    ax = fig.add_subplot(gs[0, 1:])
    panel_label(ax, "b", x=-0.06, y=1.02)
    _mini_table(
        ax,
        rows=[
            ("Hardware", "Vendor", "actuator, detector,\nlock-in, filters, latency"),
            ("Sample physics", "User + standards", "FD curves, force law,\ndissipation, contact"),
            ("Controller", "Experiment", "P/I map, safe regimes,\ntrace/retrace response"),
            ("Residual state", "Online DT", "drift, tip change,\nphase offsets, instability"),
        ],
        col_x=[0.02, 0.31, 0.55],
        y0=0.90,
        dy=0.18,
        header=("Module", "Owner", "Calibration target"),
        fontsize=6.6,
    )

    ax = fig.add_subplot(gs[1, 1])
    panel_label(ax, "c", x=-0.18, y=1.05)
    ax.axis("off")
    metrics = [("FD prior", "0.44 nm\nheld-out RMSE"), ("Controller grid", "2,200\nsettings"), ("Prediction", "2.03 nm\nmedian RMSE")]
    for i, (name, val) in enumerate(metrics):
        y = 0.73 - i * 0.27
        _box(ax, (0.06, y), (0.32, 0.17), name, [PALETTE["teal"], PALETTE["orange"], PALETTE["blue"]][i], fontsize=6.6)
        ax.text(0.45, y + 0.085, val, fontsize=8.2, fontweight="bold", va="center", color=PALETTE["ink"])
    ax.set_title("This study calibrates two user-facing modules", fontsize=7.7)

    ax = fig.add_subplot(gs[1, 2])
    panel_label(ax, "d", x=-0.18, y=1.05)
    ax.axis("off")
    rows = [
        ("predict", "scan quality before acquisition", PALETTE["blue"], "#EFF6FF"),
        ("interpret", "which module caused residuals", PALETTE["red"], "#FEF2F2"),
        ("standardize", "known-physics sample audits", PALETTE["teal"], "#ECFDF5"),
    ]
    for i, (verb, desc, color, fill) in enumerate(rows):
        y = 0.72 - i * 0.25
        ax.add_patch(FancyBboxPatch((0.04, y), 0.88, 0.16, boxstyle="round,pad=0.014,rounding_size=0.018", fc=fill, ec=color, lw=0.75))
        ax.text(0.08, y + 0.105, verb, fontsize=7.7, fontweight="bold", color=color, va="center")
        ax.text(0.08, y + 0.045, desc, fontsize=6.5, color=PALETTE["ink"], va="center")
    ax.set_title("What the framework enables", fontsize=7.7)
    return save_pub(fig, out_dir, "figure_1_fd_calibration_nature")


def build_figure_2(project_root: str | Path = ".") -> dict[str, str]:
    """Experiment calibrates sample physics and controller modules."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    drive, height, amp, *_ = _fd_data(root)
    pi, _ = _controller_data(root)
    P, I = pi["P_grid"], pi["I_grid"]
    drive_exp, setpoint = np.asarray(pi["drive_exp"]), np.asarray(pi["setpoint_exp"])
    scan, gain = np.asarray(pi["scan_rate"]), np.asarray(pi["igain_exp"])
    gp_fit = pi["gp_fit"]
    si = int(np.argmin(np.abs(scan - 1.0)))
    gi = int(np.argmin(np.abs(gain - 50)))

    fig = plt.figure(figsize=(7.2, 4.75), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1.1, 0.9, 1.15], height_ratios=[1, 1])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.10, top=0.84, wspace=0.48, hspace=0.58)
    fig.suptitle("Experiments calibrate the sample-interaction and controller modules", x=0.055, y=0.965, ha="left", fontsize=9.8, fontweight="bold")

    ax = fig.add_subplot(gs[:, 0])
    panel_label(ax, "a")
    idx = np.linspace(0, len(drive) - 1, 9, dtype=int)
    cmap = mpl.colormaps["viridis"]
    norm = mpl.colors.Normalize(vmin=float(np.nanmin(drive[idx])), vmax=float(np.nanmax(drive[idx])))
    for i in idx:
        A0 = np.nanmedian(amp[i, -60:])
        ax.plot(height[i], amp[i] / A0, lw=1.0, color=cmap(norm(drive[i])), alpha=0.95)
    ax.set_title("Sample-interaction prior\nfrom FD curves")
    ax.set_xlabel("tip-sample distance (nm)")
    ax.set_ylabel("normalized amplitude, A/A0")
    ax.set_xlim(0, 36)
    ax.set_ylim(-0.02, 1.18)
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("drive (nm)")

    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "b")
    aicc = {"capillary": -823.52, "Morse": -786.76, "DMT": -442.25, "JKR": -435.88, "LJ": 51318.31}
    names = list(aicc)
    delta = np.minimum(np.array([aicc[n] - min(aicc.values()) for n in names]), 430)
    ax.barh(np.arange(len(names)), delta, color=[PALETTE["teal"]] + [PALETTE["grey"]] * 4, height=0.58)
    ax.set_yticks(np.arange(len(names)), names)
    ax.invert_yaxis()
    ax.set_xlabel("Delta AICc")
    ax.set_title("Force law is selected,\nnot assumed")
    ax.text(430, 4, ">50,000", ha="right", va="center", fontsize=6.0, color=PALETTE["muted"])

    ax = fig.add_subplot(gs[1, 1])
    panel_label(ax, "c")
    train_rmse = np.array([0.86, 0.75, 0.68, 0.43, 0.51, 0.35, 0.21, 0.07])
    held_rmse = np.array([0.950, 0.697, 0.325, 0.154, 0.067])
    ax.bar([0, 1], [train_rmse.mean(), held_rmse.mean()], yerr=[train_rmse.std(), held_rmse.std()], color=[PALETTE["blue"], PALETTE["orange"]], alpha=0.75, capsize=2)
    ax.set_xticks([0, 1], ["training\nFD", "held-out\nFD"])
    ax.set_ylabel("amplitude RMSE (nm)")
    ax.set_title("FD calibration transfers\nto unseen drives")
    ax.set_ylim(0, 1.05)

    for lab, title, grid, cmap, col in [
        ("d", "Controller P map", np.log10(P[si, :, :, gi]).T, "YlGnBu", 2),
        ("e", "Controller I map", np.log10(I[si, :, :, gi]).T, "magma", 2),
    ]:
        ax = fig.add_subplot(gs[0 if lab == "d" else 1, col])
        panel_label(ax, lab)
        im = ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap, extent=[drive_exp.min(), drive_exp.max(), setpoint.min(), setpoint.max()])
        ax.set_xlabel("drive (nm)")
        ax.set_ylabel("setpoint")
        ax.set_title(f"{title}\nfrom sparse local fits")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
        cb.set_label("log10 gain")
    return save_pub(fig, out_dir, "figure_2_controller_map_nature")


def build_figure_3(project_root: str | Path = ".") -> dict[str, str]:
    """Prediction figure with benchmark statistics that are readable at a glance."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    pi, dd = _controller_data(root)
    rmse, eligible_local, eligible_indices = _strict_holdout_arrays(pi, dd)
    labels = list(rmse)
    colors = [PALETTE["blue"], PALETTE["teal"], PALETTE["orange"]]
    test_mask = dd["test_mask"]
    record_df = dd["record_df"]
    Y_exp_test = dd["Y_exp"][test_mask]
    Y_dt_test = dd["Y_dt"][test_mask]
    Y_direct_test = dd["Y_direct_test"]

    fig = plt.figure(figsize=(7.2, 4.75), constrained_layout=False)
    gs = gridspec.GridSpec(2, 4, figure=fig, width_ratios=[1.05, 1.15, 1.0, 1.0], height_ratios=[0.95, 1.05])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.10, top=0.84, wspace=0.58, hspace=0.62)
    fig.suptitle("The experiment-calibrated DT predicts unseen scan lines at nanometre-scale median error", x=0.055, y=0.965, ha="left", fontsize=9.7, fontweight="bold")

    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "a")
    med = np.array([np.nanmedian(rmse[k]) for k in labels])
    mean = np.array([np.nanmean(rmse[k]) for k in labels])
    x = np.arange(3)
    ax.bar(x - 0.16, med, width=0.30, color=colors, label="median")
    ax.bar(x + 0.16, mean, width=0.30, color=colors, alpha=0.25, edgecolor=colors, label="mean")
    ax.set_yscale("log")
    ax.set_xticks(x, ["physics\nDT", "direct\ndata", "DT+\nresidual"])
    ax.set_ylabel("RMSE (nm)")
    ax.set_title("Central accuracy and tail risk")
    ax.legend(frameon=False, loc="upper left", fontsize=6.0)

    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "b")
    ax.axis("off")
    ax.set_title(f"Strict held-out set: n={len(next(iter(rmse.values())))} lines", fontsize=7.4)
    ax.text(0.02, 0.80, "model", fontsize=6.4, fontweight="bold")
    ax.text(0.52, 0.80, "med.", fontsize=6.2, fontweight="bold", ha="center")
    ax.text(0.70, 0.80, "<5", fontsize=6.2, fontweight="bold", ha="center")
    ax.text(0.88, 0.80, ">10", fontsize=6.2, fontweight="bold", ha="center")
    for i, k in enumerate(labels):
        vals = rmse[k]
        y = 0.64 - i * 0.20
        ax.add_patch(FancyBboxPatch((0.01, y - 0.055), 0.96, 0.13, boxstyle="round,pad=0.004,rounding_size=0.01", fc="#F8FAFC" if i % 2 == 0 else "white", ec="#E5E7EB", lw=0.4))
        name = k.replace("Physics-anchored DT", "physics DT").replace("Direct data-driven", "direct data").replace("DT + residual", "DT residual")
        ax.text(0.02, y, name, fontsize=6.25, va="center")
        ax.text(0.52, y, f"{np.nanmedian(vals):.2f}", fontsize=6.25, va="center", ha="center")
        ax.text(0.70, y, f"{np.mean(vals < 5)*100:.0f}%", fontsize=6.25, va="center", ha="center")
        ax.text(0.88, y, f"{np.mean(vals > 10)*100:.1f}%", fontsize=6.25, va="center", ha="center")

    ax = fig.add_subplot(gs[0, 2:])
    panel_label(ax, "c", x=-0.07, y=1.06)
    for k, c in zip(labels, colors):
        vals = np.sort(rmse[k][np.isfinite(rmse[k])])
        ax.plot(vals, np.arange(1, vals.size + 1) / vals.size, color=c, lw=1.25, label=k.replace("Physics-anchored DT", "physics DT").replace("Direct data-driven", "direct data"))
    ax.axvline(5, color="black", lw=0.65, ls=":")
    ax.axvline(10, color=PALETTE["red"], lw=0.65, ls="--")
    ax.set_xscale("log")
    ax.set_xlabel("line RMSE (nm)")
    ax.set_ylabel("cumulative fraction")
    ax.set_title("Most lines are accurate; the mean is tail-dominated")
    ax.legend(frameon=False, loc="lower right", ncol=1)

    phys = rmse["Physics-anchored DT"]
    order = np.argsort(phys)
    quantiles = [0.12, 0.50, 0.88]
    for j, q in enumerate(quantiles):
        loc = int(order[int(q * (len(order) - 1))])
        global_idx = eligible_indices[loc]
        row = record_df.iloc[global_idx]
        local_test_pos = np.where(np.where(test_mask)[0] == global_idx)[0][0]
        exp = Y_exp_test[local_test_pos] - np.nanmedian(Y_exp_test[local_test_pos])
        pred = Y_dt_test[local_test_pos] - np.nanmedian(Y_dt_test[local_test_pos])
        direct = Y_direct_test[local_test_pos] - np.nanmedian(Y_direct_test[local_test_pos])
        ax = fig.add_subplot(gs[1, j])
        panel_label(ax, chr(ord("d") + j))
        px = np.arange(exp.size)
        ax.plot(px, exp, color="black", lw=1.0, label="experiment")
        ax.plot(px, pred, color=PALETTE["blue"], lw=0.95, label="physics DT")
        ax.plot(px, direct, color=PALETTE["teal"], lw=0.9, label="direct data")
        ax.set_title(["low-error", "median", "tail"][j] + f" line\nphysics RMSE={phys[loc]:.2f} nm")
        ax.set_xlabel("pixel")
        ax.set_ylabel("centered height (nm)")
        ax.text(0.02, 0.04, f"drive {row.drive_nm:.1f} nm, sp {row.setpoint:.1f}", transform=ax.transAxes, fontsize=5.9, color=PALETTE["muted"])
        if j == 0:
            ax.legend(frameon=False, loc="upper left", fontsize=5.8)

    ax = fig.add_subplot(gs[1, 3])
    panel_label(ax, "g")
    ax.scatter(rmse["Physics-anchored DT"], rmse["Direct data-driven"], s=12, color=PALETTE["muted"], alpha=0.55, lw=0)
    lim = np.nanpercentile(np.r_[rmse["Physics-anchored DT"], rmse["Direct data-driven"]], 96)
    ax.plot([0.7, lim], [0.7, lim], color="black", lw=0.7, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.7, lim)
    ax.set_ylim(0.7, lim)
    ax.set_xlabel("physics DT RMSE (nm)")
    ax.set_ylabel("direct data RMSE (nm)")
    ax.set_title("Model complementarity")
    return save_pub(fig, out_dir, "figure_3_held_out_prediction_nature")


def build_figure_4(project_root: str | Path = ".") -> dict[str, str]:
    """Interpretation figure: residuals become hypotheses and calibration actions."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    pi, dd = _controller_data(root)
    rmse, _, eligible_indices = _strict_holdout_arrays(pi, dd)
    rows = dd["record_df"].iloc[eligible_indices].reset_index(drop=True)
    phys = rmse["Physics-anchored DT"]
    tail = phys > 10

    fig = plt.figure(figsize=(7.2, 4.75), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1.0, 1.0, 1.25], height_ratios=[1, 1])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.10, top=0.84, wspace=0.50, hspace=0.58)
    fig.suptitle("Residual structure turns prediction errors into microscope-state hypotheses", x=0.055, y=0.965, ha="left", fontsize=9.7, fontweight="bold")

    drive = np.asarray(pi["drive_exp"])
    setpoint = np.asarray(pi["setpoint_exp"])
    scan = np.asarray(pi["scan_rate"])
    gain = np.asarray(pi["igain_exp"])

    def frac_grid(x_attr, y_attr, shape):
        count = np.zeros(shape, dtype=int)
        bad = np.zeros(shape, dtype=int)
        for r, b in zip(rows.itertuples(), tail):
            x = int(getattr(r, x_attr))
            y = int(getattr(r, y_attr))
            count[y, x] += 1
            bad[y, x] += int(b)
        out = np.full(shape, np.nan)
        mask = count > 0
        out[mask] = bad[mask] / count[mask]
        return out

    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "a")
    im = ax.imshow(frac_grid("di", "spi", (len(setpoint), len(drive))), origin="lower", aspect="auto", cmap="OrRd", vmin=0, vmax=0.5, extent=[drive.min(), drive.max(), setpoint.min(), setpoint.max()])
    ax.set_xlabel("drive (nm)")
    ax.set_ylabel("setpoint")
    ax.set_title("Tail risk localizes\nin operating space")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("fraction >10 nm")

    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "b")
    im = ax.imshow(frac_grid("si", "gi", (len(gain), len(scan))), origin="lower", aspect="auto", cmap="OrRd", vmin=0, vmax=0.35, extent=[scan.min(), scan.max(), gain.min(), gain.max()])
    ax.set_xlabel("scan speed")
    ax.set_ylabel("experimental I gain")
    ax.set_title("Tail risk also follows\ncontroller state")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("fraction >10 nm")

    grid_data = np.load(root / "data" / "260507-300kHz-AlScN.npz")
    raw = grid_data["data"]
    channel = 1
    h = (raw[:, :, :, :, channel, 0:2, :] - np.nanmin(raw[:, :, :, :, channel, 0:2, :], axis=-1, keepdims=True)) * 1e9
    A = raw[:, :, :, :, channel, 2:4, :] * 1e9
    phi = raw[:, :, :, :, channel, 4:6, :]
    mismatches = [
        np.nanmedian(np.abs(h[..., 0, :] - h[..., 1, :]), axis=-1).ravel(),
        np.nanmedian(np.abs(A[..., 0, :] - A[..., 1, :]), axis=-1).ravel(),
        np.nanmedian(np.abs(phi[..., 0, :] - phi[..., 1, :]), axis=-1).ravel(),
    ]
    ax = fig.add_subplot(gs[1, 0])
    panel_label(ax, "c")
    parts = ax.violinplot([v[np.isfinite(v)] for v in mismatches], positions=[0, 1, 2], widths=0.75, showmedians=True, showextrema=False)
    for body, c in zip(parts["bodies"], [PALETTE["blue"], PALETTE["teal"], PALETTE["orange"]]):
        body.set_facecolor(c)
        body.set_alpha(0.55)
        body.set_edgecolor("none")
    parts["cmedians"].set_color("black")
    ax.set_xticks([0, 1, 2], ["height", "amplitude", "phase"])
    ax.set_ylabel("trace-retrace mismatch")
    ax.set_title("Residuals are channel-specific")

    ax = fig.add_subplot(gs[1, 1])
    panel_label(ax, "d")
    line_iqr = np.clip(rows["line_iqr"].to_numpy(float), None, np.nanpercentile(rows["line_iqr"], 98))
    ax.scatter(np.maximum(line_iqr, 1e-3), phys, s=13, c=np.where(tail, PALETTE["red"], PALETTE["grey"]), alpha=0.65, lw=0)
    ax.axhline(10, color=PALETTE["red"], lw=0.75, ls="--")
    ax.axhline(np.nanmedian(phys), color="black", lw=0.65, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("line IQR (nm)")
    ax.set_ylabel("physics-DT RMSE (nm)")
    ax.set_title("Roughness and state changes\nseparate central cloud from tail")

    ax = fig.add_subplot(gs[:, 2])
    panel_label(ax, "e", x=-0.08, y=1.02)
    ax.axis("off")
    ax.set_title("Interpretation layer: residuals prescribe next calibration", fontsize=7.6)
    cards = [
        ("drive/setpoint tail", "controller/contact regime", "targeted grid calibration", PALETTE["orange"], "#FFF7ED"),
        ("gain/speed tail", "feedback latency or saturation", "hardware/controller audit", PALETTE["blue"], "#EFF6FF"),
        ("phase mismatch", "lock-in reference or dissipation", "phase + FD recalibration", PALETTE["teal"], "#ECFDF5"),
        ("rough-line outlier", "drift, tip change or intermittent contact", "online state classifier", PALETTE["red"], "#FEF2F2"),
    ]
    for i, (resid, hyp, action, color, fill) in enumerate(cards):
        y = 0.78 - i * 0.21
        ax.add_patch(FancyBboxPatch((0.02, y), 0.94, 0.16, boxstyle="round,pad=0.014,rounding_size=0.018", fc=fill, ec=color, lw=0.65))
        ax.text(0.05, y + 0.112, resid, fontsize=6.7, fontweight="bold", color=color, va="center")
        ax.text(0.05, y + 0.070, f"Hypothesis: {hyp}", fontsize=6.05, color=PALETTE["ink"], va="center")
        ax.text(0.05, y + 0.032, f"Action: {action}", fontsize=6.05, color=PALETTE["ink"], va="center")
    return save_pub(fig, out_dir, "figure_4_amp_phase_alignment_nature")


def build_nature_figure_package(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    return {
        "figure_1_framework": build_figure_1(project_root),
        "figure_2_experimental_calibration": build_figure_2(project_root),
        "figure_3_predictive_power": build_figure_3(project_root),
        "figure_4_interpretation_power": build_figure_4(project_root),
    }


def build_fd_calibration_figures(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    return {"figure_1_framework": build_figure_1(project_root)}


def build_controller_fit_figures(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    return {
        "figure_2_experimental_calibration": build_figure_2(project_root),
        "figure_3_predictive_power": build_figure_3(project_root),
        "figure_4_interpretation_power": build_figure_4(project_root),
    }
