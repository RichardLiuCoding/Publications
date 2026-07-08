# Notebook guide

Both notebooks share the same SETUP cell: on Google Colab it downloads and unpacks
`DT-SPM_data.zip` from the Google Drive file id you paste into `GDRIVE_FILE_ID`; locally it
uses the `DT-SPM_data/` folder next to the notebook. Everything below the SETUP cell is
plain Python — no Colab-specific magic.

---

## 1 · `DT-SPM_reproduce_paper.ipynb` — reproduce all manuscript results

One notebook, run top to bottom, reproduces every number and figure in the manuscript from
the archived run artifacts in `DT-SPM_data/output/`. The heavy deterministic physics (RK45
force–distance fit, feedback-scanner simulation) is **not** re-run here — its outputs are
loaded from `.npz` and are the canonical reference; the full pipeline lives in
`DT-SPM_full_digital_twin.ipynb`.

| Section | What it reproduces | Expected result |
|---|---|---|
| 0 | loads every artifact and prints shapes | all files found |
| 1 | Step 1 — the locked 18-descriptor FD vocabulary + tier weights | vocabulary table |
| 2 | Step 2 — PINN encoder held-out descriptor recovery | tier-weighted MAE(z) **0.172** (Multi-75) / **0.187** (Tap-300) vs train-median prior 1.285 / 0.672 |
| 3a | fidelity mechanism on Tap-300/AlScN | Spearman: control-only kNN **+0.86**, deterministic twin **−0.14**, global-gain re-sim **+0.03**, zero-fit amplification factor **+0.38** |
| 3b | Q_align CNN-LSTM correction | Tap-300 median error **10.4 → 0.6 nm**, Spearman **+0.23 → +0.67** |
| 3b (force) | force-based Q_safety from amplitude+phase — **full re-fit, ~30 s** | held-out Spearman **+0.92 → +0.97** |
| 4 | physics vs data-driven vs hybrid (Multi-75 grating, manuscript Fig. 7) | scalar MAE 7.3 / 8.3 / 8.9 nm; line RMSE 48 / 20 / 20 nm |
| 5 | supplementary phase-channel decoupling | held-out phase error **−76 % / −82 %** vs null |
| 6 | regenerates all 14 manuscript figures into `DT-SPM_data/output/pub_figures/` | Fig 1–7, ED 1–5, Supp 1–2 displayed inline |

**Knobs** (in the second code cell):

- `RETRAIN_PINN = False` — set `True` to re-fit a *compact* Step-2 encoder (~1 min). It
  lands in the same regime but does not match the tuned canonical model to the decimal;
  the saved predictions are the reference.
- `RETRAIN_S3B = False` — same for a compact Step-3b Q_align correction (~30 s).

The force-Q_safety model always re-fits and *does* reproduce the manuscript value.

**Runtime**: ~1–3 min CPU with default flags; +2 min with both retrain flags on.

---

## 2 · `DT-SPM_full_digital_twin.ipynb` — run the full digital twin

The complete descriptor-aligned framework, end-to-end, on the Tap-300 / AlScN system
(the manuscript's main dataset). No GPU is required — every model is compact and trains
on CPU. Structure:

1. **Setup + user-input schema** — cantilever constants (`UserInputs`: k = 25 N/m,
   f₀ = 270 kHz, Q = 200) that the framework treats as ground truth.
2. **Data registry (Section 1.2)** — *the single place data is wired in*: `fd_curves`
   (.npz FD library), `fd_fit_bundle` (.joblib RK45 calibration), `scan_bundle`
   (.npz scan archive), `fig_dir` (output directory).
3. **TRANSFER PLAYBOOK + CONFIG cell** — the recipe for adapting to a new (probe, sample)
   system, with all proven knobs in one `parameters`-tagged cell.
4. **Stage 1** — RK45 physical FD model + descriptor recovery (sim vs exp).
5. **Stage 2** — controller calibration in descriptor space, operating points.
6. **Stages 3–8** — scan descriptors, regime detection, non-ideality diagnosis,
   chain-consistency Jacobian.
7. **Section 9 (Step 2)** — PINN descriptor encoder, 1500 epochs (one of the two
   heaviest cells; a couple of minutes on CPU).
8. **Section 9b (Step 3a)** — PINN-wired deterministic scanner.
9. **Section 10 (Step 3b)** — CNN-LSTM residual correction of the scan-quality
   descriptors against experiment (250 epochs).
10. **Sections 11–13** — cross-stage evolution plots, operator reward, long-term-memory
    stub, transfer-learning warm-start helpers.

All outputs (diagnostic figures, `pinn_step2_predictions.npz`, model checkpoints `.pt`,
corrected-Q tables) are written to `DT-SPM_data/output/descriptor_framework_Tap300/`.
**On Colab this directory is ephemeral** — download anything you want to keep, or copy it
to your mounted Drive.

### Running it on new results

Follow the TRANSFER PLAYBOOK cell inside the notebook. In short:

1. Export your new FD library as an `.npz` with keys `drive`, `amp`, `height`, `phase`
   (shape `(N_curves, n_points)`), and your scan archive bundle with control keys
   (`drive`, `setpoint`, `igain`), `traces_exp`, and train/test indices — the registry
   table in Section 1.2 documents the exact schema and accepted key aliases.
2. Point `DATA` (Section 1.2) at the new files, update `UserInputs` (cantilever k, f₀, Q,
   `cantilever_id`, `sample_id`).
3. Revisit the CONFIG cell knobs — defaults are the values proven on held-out data for
   this system: `PINN_RELOBRALO=False`, `S3B_HUBER=1.0`, `S3B_RECAL=True` for
   Tap-300/AlScN (the Multi-75 grating counterparts are `True / 0.0 / False`; guidance
   for choosing is in the CONFIG cell comments).
4. Optionally warm-start the PINN from the shipped checkpoint (Section 13) — freeze the
   backbone, ~150 epochs instead of 1500.

The data package also includes the Multi-75 / calibration-grating inputs
(`output/cali_fd.npz`, `output/fd_calibration_cali_fd_results.joblib`,
`output/calibration_grating_v2_figures/figure_45_data_bundle.npz`), so the registry can be
re-pointed at a second complete worked example without any new data.

**Expected key results** (REPORT cells print `[OK]`/`[CHECK]` verdicts): Step-2 PINN
held-out tier-weighted MAE(z) ≈ 0.19; Step-3b corrected Q_align beats the scanner-only
prior on held-out conditions (Spearman ≈ +0.67).

**Runtime**: ~4 min end-to-end on a recent laptop CPU (verified); expect ~10–20 min on
a Colab CPU runtime. Outputs land in `DT-SPM_data/output/descriptor_framework_Tap300_run/`
— a separate directory, so the canonical manuscript artifacts (what the reproduction
notebook reads) are never overwritten.
