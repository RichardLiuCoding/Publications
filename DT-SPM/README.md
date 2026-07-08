# DT-SPM — descriptor-aligned digital twins for scanning probe microscopy

This package accompanies the manuscript *"[TITLE — descriptor-aligned digital twin
framework for SPM]"* (submitted to *Digital Discovery*). It contains everything needed to
(i) **reproduce every number and figure in the paper** and (ii) **run the full digital
twin end-to-end**, on Google Colab or locally.

## What is in this package

```
DT-SPM_colab/
├── README.md                       ← this file
├── NOTEBOOKS.md                    ← per-notebook documentation (sections, knobs, runtimes)
├── DATA_AVAILABILITY.md            ← data availability statement + data inventory
├── requirements.txt                ← Python dependencies (local runs only)
├── DT-SPM_reproduce_paper.ipynb    ← notebook 1: reproduce all manuscript results
├── DT-SPM_full_digital_twin.ipynb  ← notebook 2: run the full digital-twin pipeline
├── DT-SPM_data.zip                 ← the data package (upload this to Google Drive)
└── DT-SPM_data/                    ← the same data package, unzipped (for local runs)
    ├── codes/                      ← Python modules (RK45 FD solver, figure code, Q_safety model)
    └── output/                     ← all measured-data artifacts (.npz/.csv/.joblib), ~45 MB
```

## The framework in one paragraph

Measured force–distance (FD) curves and a grid-scan archive are reduced to a locked
vocabulary of **operational descriptors** (18 FD descriptors + 5 scan-quality descriptors
Q_align, Q_stab, Q_grad, Q_safety, Q_range). A physics-informed **PINN encoder** (Step 2)
recovers the FD descriptors from raw amplitude/phase curves; the descriptors
re-parameterise a deterministic **feedback-scanner simulator** (Step 3a); and compact
**CNN-LSTM corrections** (Step 3b) close the remaining gap to experiment, predicting the
scan-quality descriptors on held-out conditions. Two probe/sample systems are included:
**Tap-300 / AlScN** (900 scan conditions) and **Multi-75 / calibration grating**.

## Quick start — Google Colab

1. Upload `DT-SPM_data.zip` to your own Google Drive.
2. Right-click it → *Share* → General access: **Anyone with the link**, and copy the link.
   The file id is the part between `/d/` and `/view` in the link.
3. Open either notebook in Colab (upload it at <https://colab.research.google.com>, or open
   it from your Drive).
4. Paste the file id into `GDRIVE_FILE_ID = ''` in the first code (SETUP) cell.
5. *Runtime → Run all.* No GPU is needed — all networks in the framework are compact
   and train on CPU in minutes.

## Quick start — local

```bash
pip install -r requirements.txt
# keep DT-SPM_data/ (unzipped) next to the notebooks, then:
jupyter lab DT-SPM_reproduce_paper.ipynb
```

The SETUP cell in each notebook auto-detects whether it is running on Colab (downloads the
data via `gdown`) or locally (uses the adjacent `DT-SPM_data/` folder). No other
configuration is needed.

## Which notebook do I want?

| Notebook | Use it to… | Runtime (CPU) |
|---|---|---|
| `DT-SPM_reproduce_paper.ipynb` | verify every manuscript number and regenerate all 14 manuscript figures from the archived run artifacts; optionally re-fit compact versions of the learned models | ~1–3 min (default flags) |
| `DT-SPM_full_digital_twin.ipynb` | run the complete digital-twin pipeline (FD physics → descriptors → PINN → scanner → CNN-LSTM corrections) end-to-end, and adapt it to **new measurements** via the TRANSFER PLAYBOOK + CONFIG cell | ~4 min on a recent laptop; expect ~10–20 min on a Colab CPU runtime |

See `NOTEBOOKS.md` for a section-by-section guide, the tunable knobs, and the expected
outputs of each notebook.

## Citing

If you use this code or data, please cite the manuscript (citation to be added on
acceptance) and the archived dataset ([Zenodo DOI placeholder]).
