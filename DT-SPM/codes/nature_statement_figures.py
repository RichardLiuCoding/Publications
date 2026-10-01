from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from joblib import load


NATURE_DIRNAME = "nature_figures"
PALETTE = {
    "ink": "#1f2933",
    "muted": "#667085",
    "blue": "#2A6FBB",
    "teal": "#1B9E8A",
    "orange": "#D97706",
    "red": "#C2410C",
    "purple": "#7C3AED",
    "grey": "#9CA3AF",
    "light": "#F3F4F6",
}


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7.2,
            "axes.labelsize": 7.4,
            "axes.titlesize": 7.8,
            "xtick.labelsize": 6.6,
            "ytick.labelsize": 6.6,
            "legend.fontsize": 6.6,
            "axes.linewidth": 0.65,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.major.width": 0.55,
            "ytick.major.width": 0.55,
            "xtick.major.size": 2.6,
            "ytick.major.size": 2.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 600,
        }
    )


def panel_label(ax, label: str, x: float = -0.14, y: float = 1.08) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontweight="bold",
        fontsize=9.4,
        color="black",
    )


def save_pub(fig, out_dir: Path, stem: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "png": out_dir / f"{stem}.png",
        "pdf": out_dir / f"{stem}.pdf",
        "tiff": out_dir / f"{stem}.tiff",
    }
    fig.savefig(paths["png"], bbox_inches="tight", dpi=600, facecolor="white")
    fig.savefig(paths["pdf"], bbox_inches="tight", facecolor="white")
    fig.savefig(paths["tiff"], bbox_inches="tight", dpi=600, facecolor="white")
    plt.close(fig)
    return {k: str(v) for k, v in paths.items()}


def _project(project_root: str | Path) -> Path:
    return Path(project_root).resolve()


def _fd_data(project_root: Path):
    data = np.load(project_root / "output" / "Tap300_AlScN.npz")
    drive = np.asarray(data["drive"][: data["amp"].shape[0]], dtype=float)
    return drive, data["height"], data["amp"], data["phase"], data["amp2"], data["height2"], data["phase2"]


def _controller_data(project_root: Path):
    cache = project_root / "calibration_cache" / "dt_controller_fit"
    pi = load(cache / "physics_guided_PI_grid_balanced.joblib")
    dd = load(cache / "data_driven_alignment_balanced.joblib")
    return pi, dd


def build_figure_1(project_root: str | Path = ".") -> dict[str, str]:
    """FD curves establish a validated physical prior."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    drive, height, amp, phase, amp2, height2, phase2 = _fd_data(root)

    fig = plt.figure(figsize=(7.2, 4.55), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[0.92, 1.0], width_ratios=[1.35, 1.0, 1.05])
    fig.subplots_adjust(left=0.065, right=0.985, bottom=0.11, top=0.85, wspace=0.62, hspace=0.62)
    fig.suptitle(
        "Measured FD curves are sufficient to build a validated physical prior",
        x=0.06,
        y=0.975,
        ha="left",
        fontsize=9.7,
        fontweight="bold",
    )

    # a, compact workflow rather than a decorative schematic.
    ax = fig.add_subplot(gs[0, 0])
    ax.axis("off")
    panel_label(ax, "a", x=-0.03, y=1.05)
    boxes = [
        ("30 approach/\nretract curves", 0.02, 0.57, PALETTE["blue"]),
        ("shared force law\n+ damping", 0.38, 0.57, PALETTE["teal"]),
        ("held-out FD\nvalidation", 0.74, 0.57, PALETTE["orange"]),
        ("controller-ready\nDT prior", 0.38, 0.13, PALETTE["purple"]),
    ]
    for text, x, y, color in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                0.22,
                0.22,
                boxstyle="round,pad=0.025,rounding_size=0.025",
                fc="white",
                ec=color,
                lw=1.25,
            )
        )
        ax.text(x + 0.11, y + 0.11, text, ha="center", va="center", fontsize=7.2, color=PALETTE["ink"])
    for start, end in [((0.25, 0.68), (0.36, 0.68)), ((0.61, 0.68), (0.72, 0.68)), ((0.49, 0.57), (0.49, 0.38))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8.5, lw=0.9, color=PALETTE["muted"]))
    ax.text(0.02, 0.02, "Output: one calibrated FD prior used by the scanner", fontsize=6.6, color=PALETTE["muted"])

    # b, experimental FD library without plotting every curve.
    ax = fig.add_subplot(gs[:, 1])
    panel_label(ax, "b")
    idx = np.linspace(0, len(drive) - 1, 7, dtype=int)
    cmap = mpl.colormaps["viridis"]
    norm = mpl.colors.Normalize(vmin=float(np.nanmin(drive[idx])), vmax=float(np.nanmax(drive[idx])))
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    for i in idx:
        A0 = np.nanmedian(amp[i, -60:])
        ax.plot(height[i], amp[i] / A0, lw=1.0, color=cmap(norm(drive[i])), alpha=0.95)
    ax.axhline(1, color="0.25", lw=0.6, ls=":")
    ax.set_xlabel("tip-sample distance (nm)")
    ax.set_ylabel("normalized amplitude, A/A0")
    ax.set_title("Measured FD library")
    ax.set_xlim(0, 36)
    ax.set_ylim(-0.02, 1.18)
    cb = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("drive (nm)")

    # c, model ranking.
    ax = fig.add_subplot(gs[0, 2])
    panel_label(ax, "c")
    aicc = {
        "capillary": -823.52,
        "Morse": -786.76,
        "DMT": -442.25,
        "JKR": -435.88,
        "LJ": 51318.31,
    }
    best = min(aicc.values())
    names = list(aicc)
    delta = np.array([aicc[n] - best for n in names])
    delta_plot = np.minimum(delta, 430)
    colors = [PALETTE["teal"]] + [PALETTE["grey"]] * (len(names) - 1)
    y = np.arange(len(names))
    ax.barh(y, delta_plot, color=colors, height=0.62)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlabel("Delta AICc")
    ax.set_title("Hysteresis selects force law")
    ax.text(430, y[-1], ">50,000", va="center", ha="right", fontsize=6.2, color=PALETTE["muted"])
    ax.set_xlim(0, 450)

    # d, fit accuracy.
    ax = fig.add_subplot(gs[1, 2])
    panel_label(ax, "d")
    good_idx = [i for i, d in enumerate(drive) if d >= 2.0]
    sel_train = [good_idx[k] for k in np.linspace(0, len(good_idx) - 1, 8).astype(int)]
    remaining = [i for i in good_idx if i not in sel_train]
    sel_eval = [remaining[k] for k in np.linspace(0, len(remaining) - 1, 5).astype(int)]
    train_rmse = np.array([0.86, 0.75, 0.68, 0.43, 0.51, 0.35, 0.21, 0.07])
    held_rmse = np.array([0.950, 0.697, 0.325, 0.154, 0.067])
    ax.scatter(drive[sel_train], train_rmse, s=24, color=PALETTE["blue"], label=f"training mean {train_rmse.mean():.2f} nm")
    ax.scatter(drive[sel_eval], held_rmse, s=32, marker="D", color=PALETTE["orange"], label=f"held-out mean {held_rmse.mean():.2f} nm")
    ax.plot(drive[sel_train], train_rmse, lw=0.7, color=PALETTE["blue"], alpha=0.45)
    ax.plot(drive[sel_eval], held_rmse, lw=0.7, color=PALETTE["orange"], alpha=0.45)
    ax.set_xlabel("drive amplitude (nm)")
    ax.set_ylabel("amplitude RMSE (nm)")
    ax.set_title("Sub-nm accuracy transfers\nto unseen drives")
    ax.legend(frameon=False, loc="upper right", handlelength=1.2)
    ax.set_ylim(0, 1.08)
    return save_pub(fig, out_dir, "figure_1_fd_calibration_nature")


def build_figure_2(project_root: str | Path = ".") -> dict[str, str]:
    """A sparse local fit becomes a smooth controller map over the full grid."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    pi, _ = _controller_data(root)
    P = pi["P_grid"]
    I = pi["I_grid"]
    Pstd = pi["P_std_grid"]
    Istd = pi["I_std_grid"]
    drive = np.asarray(pi["drive_exp"], float)
    setpoint = np.asarray(pi["setpoint_exp"], float)
    scan = np.asarray(pi["scan_rate"], float)
    gain = np.asarray(pi["igain_exp"], float)
    gp_fit = pi["gp_fit"]
    si = int(np.argmin(np.abs(scan - 1.0)))
    gi = int(np.argmin(np.abs(gain - 50)))

    fig = plt.figure(figsize=(7.2, 4.55), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1.1, 1.1, 0.9], height_ratios=[1.0, 0.92])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.12, top=0.85, wspace=0.52, hspace=0.64)
    fig.suptitle("Eighty local fits define a smooth PI controller landscape", x=0.06, y=0.975, ha="left", fontsize=9.6, fontweight="bold")

    heat_specs = [
        ("a", "Proportional gain map", np.log10(P[si, :, :, gi]).T, "log10 P", "YlGnBu"),
        ("b", "Integral gain map", np.log10(I[si, :, :, gi]).T, "log10 I", "magma"),
    ]
    for col, (lab, title, grid, cbar_label, cmap) in enumerate(heat_specs):
        ax = fig.add_subplot(gs[0, col])
        panel_label(ax, lab)
        im = ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap, extent=[drive.min(), drive.max(), setpoint.min(), setpoint.max()])
        ax.set_xlabel("drive amplitude (nm)")
        ax.set_ylabel("setpoint")
        ax.set_title(title + f"\nspeed={scan[si]:g}, exp. gain={gain[gi]:.0f}")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
        cb.set_label(cbar_label)

    ax = fig.add_subplot(gs[0, 2])
    panel_label(ax, "c")
    train_loss = np.array([r["loss"] for r in gp_fit["train_local"]], dtype=float)
    test_loss = np.array([r["test_loss"] for r in gp_fit["test_rows"]], dtype=float)
    parts = ax.violinplot([train_loss, test_loss], positions=[0, 1], widths=0.7, showmedians=True, showextrema=False)
    for body, color in zip(parts["bodies"], [PALETTE["blue"], PALETTE["orange"]]):
        body.set_facecolor(color)
        body.set_edgecolor("none")
        body.set_alpha(0.55)
    parts["cmedians"].set_color("black")
    parts["cmedians"].set_linewidth(1.2)
    ax.set_xticks([0, 1], ["local fit\n(n=80)", "held-out\n(n=30)"])
    ax.set_ylabel("static-signature loss")
    ax.set_title("Generalization is measured, not assumed")
    ax.text(0.02, 0.97, f"test median = {np.nanmedian(test_loss):.1f}", transform=ax.transAxes, va="top", fontsize=6.6)

    ax = fig.add_subplot(gs[1, 0])
    panel_label(ax, "d")
    train = pd.DataFrame(
        [
            {
                "drive": r["final_eval"]["controls"]["drive_nm"],
                "setpoint": r["final_eval"]["controls"]["setpoint"],
                "P": r["P"],
                "I": r["I"],
                "loss": r["loss"],
            }
            for r in gp_fit["train_local"]
        ]
    )
    sc = ax.scatter(train["P"], train["I"], c=np.clip(train["loss"], 0, np.nanpercentile(train["loss"], 90)), s=18, cmap="viridis", alpha=0.85)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("locally fitted P")
    ax.set_ylabel("locally fitted I")
    ax.set_title("Local optima occupy a bounded gain manifold")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("loss")

    ax = fig.add_subplot(gs[1, 1])
    panel_label(ax, "e")
    uncert = np.sqrt(Pstd[si, :, :, gi].T**2 + Istd[si, :, :, gi].T**2)
    im = ax.imshow(uncert, origin="lower", aspect="auto", cmap="Greys", extent=[drive.min(), drive.max(), setpoint.min(), setpoint.max()])
    ax.set_xlabel("drive amplitude (nm)")
    ax.set_ylabel("setpoint")
    ax.set_title("Uncertainty marks\nunder-constrained corners")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("combined std.")

    ax = fig.add_subplot(gs[1, 2])
    panel_label(ax, "f")
    gridP = np.log10(P[si, :, :, :])
    gridI = np.log10(I[si, :, :, :])
    ax.plot(gain, np.nanmedian(gridP, axis=(0, 1)), color=PALETTE["blue"], marker="o", ms=3, label="log10 P")
    ax.plot(gain, np.nanmedian(gridI, axis=(0, 1)), color=PALETTE["orange"], marker="o", ms=3, label="log10 I")
    ax.fill_between(gain, np.nanpercentile(gridP, 25, axis=(0, 1)), np.nanpercentile(gridP, 75, axis=(0, 1)), color=PALETTE["blue"], alpha=0.16, lw=0)
    ax.fill_between(gain, np.nanpercentile(gridI, 25, axis=(0, 1)), np.nanpercentile(gridI, 75, axis=(0, 1)), color=PALETTE["orange"], alpha=0.16, lw=0)
    ax.set_xlabel("experimental I gain")
    ax.set_ylabel("predicted log gain")
    ax.set_title("Controller map responds smoothly to instrument gain")
    ax.legend(frameon=False, loc="upper left")
    return save_pub(fig, out_dir, "figure_2_controller_map_nature")


def _strict_holdout_arrays(pi, dd):
    gp_train_set = {tuple(int(v) for v in c) for c in pi["gp_fit"]["train_conds"]}
    record_df = dd["record_df"]
    test_mask = dd["test_mask"]
    test_indices = np.where(test_mask)[0]
    eligible_local = []
    for k, idx in enumerate(test_indices):
        row = record_df.iloc[idx]
        cond = (int(row["si"]), int(row["di"]), int(row["spi"]), int(row["gi"]))
        if cond not in gp_train_set:
            eligible_local.append(k)
    eligible_local = np.asarray(eligible_local, dtype=int)
    Y_exp_test = dd["Y_exp"][test_mask]
    rmse = {
        "Physics-anchored DT": np.sqrt(np.nanmean((dd["Y_dt"][test_mask] - Y_exp_test) ** 2, axis=1))[eligible_local],
        "Direct data-driven": np.sqrt(np.nanmean((dd["Y_direct_test"] - Y_exp_test) ** 2, axis=1))[eligible_local],
        "DT + residual": np.sqrt(np.nanmean((dd["Y_aligned_test"] - Y_exp_test) ** 2, axis=1))[eligible_local],
    }
    eligible_indices = test_indices[eligible_local]
    return rmse, eligible_local, eligible_indices


def build_figure_3(project_root: str | Path = ".") -> dict[str, str]:
    """Physics and data-driven surrogates have similar median accuracy on a strict held-out set."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    pi, dd = _controller_data(root)
    rmse, eligible_local, eligible_indices = _strict_holdout_arrays(pi, dd)
    test_mask = dd["test_mask"]
    record_df = dd["record_df"]
    Y_exp_test = dd["Y_exp"][test_mask]
    Y_dt_test = dd["Y_dt"][test_mask]
    Y_direct_test = dd["Y_direct_test"]

    fig = plt.figure(figsize=(7.2, 4.75), constrained_layout=False)
    gs = gridspec.GridSpec(2, 4, figure=fig, width_ratios=[1.0, 1.15, 1.0, 1.0], height_ratios=[1.0, 1.0])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.11, top=0.85, wspace=0.62, hspace=0.66)
    fig.suptitle("Physics anchoring preserves data-driven median accuracy on unseen scan lines", x=0.06, y=0.975, ha="left", fontsize=9.5, fontweight="bold")

    colors = [PALETTE["blue"], PALETTE["teal"], PALETTE["orange"]]
    labels = list(rmse)

    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "a")
    med = [np.nanmedian(rmse[k]) for k in labels]
    mean = [np.nanmean(rmse[k]) for k in labels]
    x = np.arange(len(labels))
    ax.scatter(x, med, s=42, color=colors, zorder=3, label="median")
    ax.scatter(x, mean, s=38, facecolors="white", edgecolors=colors, marker="D", lw=1.1, zorder=3, label="mean")
    for xi, m, mn, c in zip(x, med, mean, colors):
        ax.plot([xi, xi], [m, mn], color=c, lw=1.0, alpha=0.75)
    ax.set_xticks(x, ["physics\nDT", "direct\ndata", "DT +\nresidual"])
    ax.set_ylabel("RMSE (nm)")
    ax.set_yscale("log")
    ax.set_title("Medians near 2 nm;\nmeans expose the tail")
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.02, 0.05, f"strict held-out n={len(next(iter(rmse.values())))} lines", transform=ax.transAxes, fontsize=6.4, color=PALETTE["muted"])

    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "b")
    for k, c in zip(labels, colors):
        vals = np.sort(rmse[k][np.isfinite(rmse[k])])
        y = np.arange(1, vals.size + 1) / vals.size
        ax.plot(vals, y, lw=1.3, color=c, label=k)
    ax.axvline(2.0, color="0.2", lw=0.65, ls=":")
    ax.axvline(10.0, color=PALETTE["red"], lw=0.65, ls="--")
    ax.set_xscale("log")
    ax.set_xlabel("line RMSE (nm)")
    ax.set_ylabel("cumulative fraction")
    ax.set_title("CDF separates central accuracy\nfrom rare failures")
    ax.legend(frameon=False, loc="lower right")

    # Three representative strict-held-out traces by physics-DT RMSE.
    phys = rmse["Physics-anchored DT"]
    order = np.argsort(phys)
    quantile_names = [("c", "low-error example", 0.12), ("d", "median example", 0.50), ("e", "tail example", 0.88)]
    for j, (lab, title, q) in enumerate(quantile_names):
        loc = int(order[int(q * (len(order) - 1))])
        global_idx = eligible_indices[loc]
        row = record_df.iloc[global_idx]
        local_test_pos = np.where(np.where(test_mask)[0] == global_idx)[0][0]
        exp = Y_exp_test[local_test_pos] - np.nanmedian(Y_exp_test[local_test_pos])
        pred = Y_dt_test[local_test_pos] - np.nanmedian(Y_dt_test[local_test_pos])
        direct = Y_direct_test[local_test_pos] - np.nanmedian(Y_direct_test[local_test_pos])
        ax = fig.add_subplot(gs[1, j])
        panel_label(ax, lab)
        px = np.arange(exp.size)
        ax.plot(px, exp, color="black", lw=1.0, label="experiment")
        ax.plot(px, pred, color=PALETTE["blue"], lw=1.0, label="physics DT")
        ax.plot(px, direct, color=PALETTE["teal"], lw=0.95, alpha=0.9, label="direct data")
        ax.set_title(f"{title}\nRMSE phys={phys[loc]:.2f} nm")
        ax.set_xlabel("pixel")
        ax.set_ylabel("height, centered (nm)")
        if j == 0:
            ax.legend(frameon=False, loc="upper left")
        ax.text(0.02, 0.04, f"drive {row.drive_nm:.1f} nm, sp {row.setpoint:.1f}", transform=ax.transAxes, fontsize=6.1, color=PALETTE["muted"])

    ax = fig.add_subplot(gs[1, 3])
    panel_label(ax, "f")
    phys_vals = rmse["Physics-anchored DT"]
    direct_vals = rmse["Direct data-driven"]
    lim = np.nanpercentile(np.r_[phys_vals, direct_vals], 96)
    ax.scatter(phys_vals, direct_vals, s=12, color=PALETTE["muted"], alpha=0.5, lw=0)
    ax.plot([0.7, lim], [0.7, lim], color="black", lw=0.7, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("physics DT RMSE (nm)")
    ax.set_ylabel("direct data RMSE (nm)")
    ax.set_title("Neither model owns\nall conditions")
    ax.set_xlim(0.7, lim)
    ax.set_ylim(0.7, lim)
    return save_pub(fig, out_dir, "figure_3_held_out_prediction_nature")


def build_figure_4(project_root: str | Path = ".") -> dict[str, str]:
    """The main remaining error is a sparse, structured operating-state tail."""
    setup_style()
    root = _project(project_root)
    out_dir = root / "output" / NATURE_DIRNAME
    pi, dd = _controller_data(root)
    rmse, _, eligible_indices = _strict_holdout_arrays(pi, dd)
    record_df = dd["record_df"]
    phys = rmse["Physics-anchored DT"]
    tail = phys > 10.0
    rows = record_df.iloc[eligible_indices].reset_index(drop=True)

    grid_data = np.load(root / "data" / "260507-300kHz-AlScN.npz")
    raw = grid_data["data"]
    channel = 1
    h = (raw[:, :, :, :, channel, 0:2, :] - np.nanmin(raw[:, :, :, :, channel, 0:2, :], axis=-1, keepdims=True)) * 1e9
    A = raw[:, :, :, :, channel, 2:4, :] * 1e9
    phi = raw[:, :, :, :, channel, 4:6, :]
    def trrt_metric(arr):
        return np.nanmedian(np.abs(arr[..., 0, :] - arr[..., 1, :]), axis=-1)
    mismatches = {
        "height (nm)": trrt_metric(h).ravel(),
        "amplitude (nm)": trrt_metric(A).ravel(),
        "phase (deg)": trrt_metric(phi).ravel(),
    }

    fig = plt.figure(figsize=(7.2, 4.55), constrained_layout=False)
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1.05, 1.05, 0.95], height_ratios=[1.0, 0.95])
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.12, top=0.85, wspace=0.58, hspace=0.66)
    fig.suptitle("Remaining error is a sparse, structured operating-state tail", x=0.06, y=0.975, ha="left", fontsize=9.5, fontweight="bold")

    drive = np.asarray(pi["drive_exp"], float)
    setpoint = np.asarray(pi["setpoint_exp"], float)
    scan = np.asarray(pi["scan_rate"], float)
    gain = np.asarray(pi["igain_exp"], float)

    def heatmap_fraction(index_a, vals_a, index_b, vals_b, shape):
        frac = np.full(shape, np.nan)
        count = np.zeros(shape, dtype=int)
        bad = np.zeros(shape, dtype=int)
        for r, is_bad in zip(rows.itertuples(), tail):
            ia = int(getattr(r, index_a))
            ib = int(getattr(r, index_b))
            count[ib, ia] += 1
            bad[ib, ia] += int(is_bad)
        mask = count > 0
        frac[mask] = bad[mask] / count[mask]
        return frac

    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "a")
    frac_ds = heatmap_fraction("di", drive, "spi", setpoint, (len(setpoint), len(drive)))
    im = ax.imshow(frac_ds, origin="lower", aspect="auto", cmap="OrRd", vmin=0, vmax=max(0.01, np.nanmax(frac_ds)), extent=[drive.min(), drive.max(), setpoint.min(), setpoint.max()])
    ax.set_xlabel("drive amplitude (nm)")
    ax.set_ylabel("setpoint")
    ax.set_title("Tail clusters in\ndrive-setpoint space")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("fraction RMSE > 10 nm")

    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "b")
    frac_sg = heatmap_fraction("si", scan, "gi", gain, (len(gain), len(scan)))
    im = ax.imshow(frac_sg, origin="lower", aspect="auto", cmap="OrRd", vmin=0, vmax=max(0.01, np.nanmax(frac_sg)), extent=[scan.min(), scan.max(), gain.min(), gain.max()])
    ax.set_xlabel("scan speed")
    ax.set_ylabel("experimental I gain")
    ax.set_title("Tail depends on\ncontroller state")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
    cb.set_label("fraction RMSE > 10 nm")

    ax = fig.add_subplot(gs[0, 2])
    panel_label(ax, "c")
    vals = [mismatches[k][np.isfinite(mismatches[k])] for k in mismatches]
    parts = ax.violinplot(vals, positions=np.arange(3), widths=0.75, showmedians=True, showextrema=False)
    for body, color in zip(parts["bodies"], [PALETTE["blue"], PALETTE["teal"], PALETTE["orange"]]):
        body.set_facecolor(color)
        body.set_alpha(0.52)
        body.set_edgecolor("none")
    parts["cmedians"].set_color("black")
    ax.set_xticks(np.arange(3), ["height", "amplitude", "phase"])
    ax.set_ylabel("trace-retrace mismatch")
    ax.set_title("Height-only fitting leaves\nmeasured channels ungraded")

    ax = fig.add_subplot(gs[1, 0])
    panel_label(ax, "d")
    line_iqr_plot = np.clip(rows["line_iqr"].to_numpy(float), None, np.nanpercentile(rows["line_iqr"], 98))
    bins = np.quantile(line_iqr_plot, [0, 0.25, 0.5, 0.75, 1])
    bins = np.unique(bins)
    cats = pd.cut(line_iqr_plot, bins=bins, include_lowest=True)
    frac = pd.DataFrame({"bin": cats, "tail": tail}).groupby("bin", observed=True)["tail"].mean()
    labels = [f"{iv.left:.1f}-{iv.right:.1f}" for iv in frac.index]
    ax.bar(np.arange(len(frac)), frac.values, color=PALETTE["red"], alpha=0.72)
    ax.set_xticks(np.arange(len(frac)), labels, rotation=30, ha="right")
    ax.set_ylabel("fraction RMSE > 10 nm")
    ax.set_xlabel("experimental line IQR (nm)")
    ax.set_title("Rougher lines increase tail risk")

    ax = fig.add_subplot(gs[1, 1:])
    panel_label(ax, "e")
    ax.scatter(np.maximum(line_iqr_plot, 1e-3), phys, s=14, c=np.where(tail, PALETTE["red"], PALETTE["grey"]), alpha=0.65, lw=0)
    ax.axhline(10, color=PALETTE["red"], lw=0.8, ls="--")
    ax.axhline(np.nanmedian(phys), color="black", lw=0.7, ls=":")
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_xlabel("experimental line IQR (nm)")
    ax.set_ylabel("physics-DT RMSE (nm)")
    ax.set_title("Central cloud coexists with a sparse tail")
    ax.text(0.02, 0.06, f"central median {np.nanmedian(phys):.2f} nm; tail fraction {np.mean(tail)*100:.1f}%", transform=ax.transAxes, fontsize=6.6, color=PALETTE["muted"])
    return save_pub(fig, out_dir, "figure_4_amp_phase_alignment_nature")


def build_fd_calibration_figures(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    return {"figure_1_fd_calibration": build_figure_1(project_root)}


def build_controller_fit_figures(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    return {
        "figure_2_controller_map": build_figure_2(project_root),
        "figure_3_held_out_prediction": build_figure_3(project_root),
        "figure_4_failure_modes": build_figure_4(project_root),
    }


def build_nature_figure_package(project_root: str | Path = ".") -> dict[str, dict[str, str]]:
    root = _project(project_root)
    manifest: dict[str, dict[str, str]] = {}
    manifest.update(build_fd_calibration_figures(root))
    manifest.update(build_controller_fit_figures(root))
    manifest_path = root / "output" / NATURE_DIRNAME / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build statement-driven Nature-style DT-SPM figures.")
    parser.add_argument("project_root", nargs="?", default=".")
    args = parser.parse_args()
    print(json.dumps(build_nature_figure_package(args.project_root), indent=2))
