# Manuscript-to-code map

Run commands from the package root. `run_reproduction.py` sets the output directory and calls the named producers. Every numerical result remains available in the reference arrays and reports even where the revised manuscript describes the result qualitatively.

| Manuscript item | Producer and inputs | Saved output |
|---|---|---|
| Main Figures 1–2 | Author-edited schematics; editable PowerPoint and exact submitted images included | `reference/revised/figures/DT-SPM_figures_rev1.pptx`, `Fig1_rev.png`, `Fig2_rev.png` |
| Main Figure 3 | `rv_figures.py fig3`; archived FD descriptor/phase fields and scan bundles | `figures/Fig3_rev.png` |
| Main Figure 4; Table S6 | `rv_step2_cv.py tap300` and `multi75`; measured FD libraries, archived FD parameter fits, fixed submitted encoder settings | `output/step2_cv_*.json`, `output/step2_cv_*/cv_predictions.npz` |
| Main Figure 5 | `rv_mechanism.py`; raw AlScN grid, FD library, fold-specific scanner calibration and benchmark outputs | `output/mechanism_block5.json`, `.npz` |
| Main Figure 6; Tables S3–S4 | `rv_audit.py` and `rv_run_tap300.py`; submitted notebook, archived arrays and revised raw-grid loaders | `output/audit_summary.json`, `output/tap300_benchmark_*` |
| Main Figure 7; Table S5 | `rv_run_tap300.py`, `rv_grating.py`, `rv_learning_curve.py` | `output/grating_benchmark.*`, `output/tap300_learning_curve.csv` |
| Supplementary Figure 1 | `rv_legacy_figures.py`, calling `_make_pro_figures.make_fig2_pro`; historical architecture schematic | `figures/legacy_supplement/fig2_pro.png` |
| Supplementary Figures 2, 4, 5, 7 | `rv_legacy_figures.py`, calling `_make_comparison_figures.make_c1` through `make_c4`; archived submitted arrays | `figures/legacy_supplement/c1_*.png` through `c4_*.png` |
| Supplementary Figures 3, 6, 8 | `rv_legacy_figures.py`, executing `_make_pub_figures.py`; archived submitted arrays | `figures/legacy_supplement/r1_step2_pinn.png`, `r3_correction.png`, `r4_decoupling.png` |
| Supplementary Figures 9–10 | `rv_figures.py si`; learning curves, benchmark predictions and audit results | `figures/FigS9_learning_curves.*`, `FigS10_audit_regimes.*` |
| Tables S2–S7 | `rv_si_tables.py`; revised output files and recorded acquisition metadata | `manuscript/si_tables.json`; contains table text and layout records |
| Table S1 / inference contract | Method specification in the manuscript and `rv_tap300.py`; not a computed result | Supporting condition and calibration manifests |
| FD libraries | `rv_build_fd.py`; raw IBW files and recorded conversion factors | `output/fd_libraries/*.npz`, `fd_regeneration_report.json` |
| Plot bundles | `rv_build_bundles.py --verify-local 3`; measured archives, FD libraries and cached local fits | `output/bundles/*.npz`, `bundle_regeneration_report.json` |
| Candidate-input invariance | `rv_invariance_test.py`; one blocked fold, four tested predictors | `output/invariance_test.json` |
| Condition splits | `rv_manifests.py` | `release_R1/splits/*.csv` inside the run directory |

`metadata/figure_sources.csv` links the exact images in the current manuscript and SI to their matching local source images by SHA-256. Exact embedded images are retained even when a plotting backend changes rasterization or a historical panel was edited for the manuscript. Numerical reproducibility is assessed separately from image identity.

The package contains original exploratory/calibration notebooks for source inspection. They can include historical local paths and optional instrument-related code. Use the documented driver or the R1 reproduction notebook for the tested offline analysis. The driver neither acquires data from an instrument nor runs the exploratory notebooks from start to finish.
