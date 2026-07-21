# MOBO-DKL

Code and compact experimental data for **Autonomous Physics Discovery of Polarization Switching Mechanisms in Ferroelectrics via Reward-Guided Multi-Objective Deep Learning**.

[![Open PZTO-(111) notebook in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RichardLiuCoding/Publications/blob/main/MOBO-DKL/PZTO111_MOBO_DKL_Colab.ipynb)

## Start here

Open `PZTO111_MOBO_DKL_Colab.ipynb` in Google Colab and run the cells from top to bottom. The notebook downloads the compact data from this folder automatically. A T4 GPU is useful for the optional VAE and DKL training sections but is not required for loading the data, validating switched area or reproducing the Pareto and descriptor analyses.

Local installation:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
jupyter lab
```

## Notebook map

| Notebook | Purpose | Colab |
|---|---|---|
| `PZTO111_MOBO_DKL_Colab.ipynb` | PZTO-(111) experiment replay, switched-area audit, pulse-dose Pareto front, descriptors, VAE, replay-mode MOBO-DKL and live-instrument adapter | Yes |
| `MOBO_DKL_RL_dev_simulation.ipynb` | Standalone simulated MOBO-DKL example | Yes |
| `MOBO_DKL_RL_dev_Experiment_data.ipynb` | Replay of the earlier PTKTO experiment data | Yes |
| `Figure_plots.ipynb` | Original figure and movie generation | Partial; uses embedded data |
| `Jupiter_MOBO_DKL_Domain_botorch_v6.ipynb` | Original Jupiter AFM control notebook and instrument template | No; requires an instrument connection |

## PZTO-(111) compact data

The two pre-poled regions are called **Area 1** and **Area 2**, matching the revised manuscript. The release contains 427 destructive structure-response measurements.

| File | Contents |
|---|---|
| `data/PZTO111_MOBO_DKL_maps_v1.npz` | Before/after lateral-PFM amplitude and phase maps, voltage, dwell, positions, full and localized masks, global maps and acquisition metadata |
| `data/PZTO111_MOBO_DKL_analysis_v1.npz` | Fifteen structural descriptors, manuscript VAE inputs/reconstructions/latents and decoded latent grid |
| `data/PZTO111_MOBO_DKL_events_v1.csv.gz` | Gzip-compressed event table with conditions, areas, efficiency, descriptors and VAE coordinates |
| `data/DATA_DICTIONARY.md` | Array shapes, units, definitions and provenance |
| `data/SHA256SUMS` | SHA256 checksums for release files |

The 32 x 32 local maps cover 500 nm x 500 nm. One pixel therefore corresponds to 15.625 nm and 0.000244140625 um^2.

## What the Colab notebook reproduces

1. **Switched-area reliability.** It independently recomputes the 45-degree phase-change and amplitude-gated masks, including the global 180-degree flip guard and center-localized connected-component rule. All 427 areas must agree exactly with the released values.
2. **Pulse-condition landscape.** It extracts the empirical Pareto front that minimizes the pulse-dose proxy `|V|t` while maximizing switched in-plane area, and plots switching probability and the voltage-dwell efficiency map.
3. **Structural descriptors.** It refits PCA to the 15 before-pulse descriptors and tests the wall-rich, weak-order coordinate against switched area.
4. **VAE analysis.** It visualizes the manuscript VAE outputs and provides the complete six-dimensional convolutional VAE training code. The VAE never receives voltage, dwell, switched area or efficiency.
5. **MOBO-DKL replay.** It trains independent reward-specific CNN-GP surrogates and uses qLogEHVI to recommend a held-out recorded candidate. This tests the learning and acquisition logic without requiring a microscope.
6. **Instrument hand-off.** A typed adapter defines the four operations that a laboratory must implement to connect the same loop to an SPM.

## Experimental settings

| Setting | Area 1 | Area 2 |
|---|---:|---:|
| Seed measurements | 15 | 12 |
| Active-learning measurements | 200 | 200 |
| Voltage magnitude | 3-6 V | 3-6 V |
| Dwell times | 0.5, 1, 2, 4, 6, 10 s | 0.5, 1, 2, 5, 10 s |
| Local map | 500 nm, 32 x 32 pixels | 500 nm, 32 x 32 pixels |

The manuscript reports `|V|t` as a pulse-dose proxy and area/(`|V|t`) as write-dose efficiency. These quantities are not electrical energy because current was not measured.

## Live deployment

The Colab workflow runs in replay mode. A live experiment additionally requires:

- an instrument control layer such as [AESPM](https://github.com/RichardLiuCoding/aespm);
- verified lateral-PFM channel names and units;
- implementations of tip motion, before/after imaging, pulse application and checkpointing;
- voltage, force, drift and contact-resonance safety checks; and
- validation on a sacrificial sample region before autonomous operation.

The original Jupiter notebook is retained for provenance, but it is intentionally not presented as a hardware-independent push-button workflow.

## Reproducibility

- Random seeds are fixed in the Colab notebook.
- The event table and NPZ files contain no Python object arrays and load with `allow_pickle=False` where applicable.
- Release-file checksums are listed in `data/SHA256SUMS`.
- `requirements.txt` records the tested numerical and MOBO package versions. PyTorch is bounded rather than force-reinstalled so the notebook remains compatible with the CUDA build supplied by Colab.

## Citation

Please cite the manuscript above and the final journal article when available. For the optimization stack, also cite GPyTorch and BoTorch as listed in the manuscript Methods.
