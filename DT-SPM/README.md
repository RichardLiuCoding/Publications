# DT-SPM: code for the revised manuscript

This folder contains the notebooks, analysis scripts and environment records for *Coupled Sample and Instrument Digital Twins for Predictive Amplitude-Modulation Atomic Force Microscopy* (Digital Discovery, DD-ART-07-2026-000467).

- Code: [Publications/DT-SPM on GitHub](https://github.com/RichardLiuCoding/Publications/tree/main/DT-SPM)
- Dataset: [DT-SPM_R1_data_2026-09-30.zip on Google Drive](https://drive.google.com/file/d/1ckGptfEbkKzbnl_eHDzDHCAU6Hjbhyce/view?usp=sharing) (668 MB download; about 942 MB extracted)

The code and dataset use the package identifier `R1-repro-2026-09-30`. A final Git release tag, commit and archive DOIs remain to be recorded. Licence and creator metadata require author confirmation; see [RIGHTS_AND_RELEASE_STATUS.txt](RIGHTS_AND_RELEASE_STATUS.txt).

## Download and run

Clone the repository and enter this folder:

```bash
git clone https://github.com/RichardLiuCoding/Publications.git
cd Publications/DT-SPM
```

If you already have a local copy, open a terminal in its `DT-SPM` folder. Use CPython 3.10.19 for the recorded environment. On macOS or Linux:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python environment/install_environment.py
python verify_package.py --part code
python download_dataset.py
python verify_package.py
```

On Windows, create the environment with `py -3.10 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1` in PowerShell. The installer checks the exact Python version. Other platforms must be checked against the supplied numerical reports; the recorded validation used macOS on Apple Silicon with CPU PyTorch.

`download_dataset.py` retrieves the linked ZIP, checks its size and SHA-256, and installs its contents directly into this folder. It removes the archive's `DT-SPM_R1/` prefix during extraction. Existing files with matching checksums are retained; changed files must be moved aside before installation. A second call verifies the installed data and skips the download. Allow about 3 GB of free space for the download and extraction, plus space for the Python environment and new analysis outputs.

Run a short FD preprocessing check first, or execute all analysis stages:

```bash
python run_reproduction.py --stage fd --run-dir runs/fd_check
python run_reproduction.py --run-dir runs/my_run
python compare_results.py runs/my_run
```

The full analysis takes several minutes to tens of minutes, depending on hardware. Each stage writes logs and an exit status under the selected run directory. Archived inputs and reference results remain separate from new outputs. The comparison report retains small deviations in the historical neural audit; see [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for the tolerances and scope.

For a notebook workflow, open [DT-SPM_R1_reproduce.ipynb](DT-SPM_R1_reproduce.ipynb) with this environment. Register it as a kernel if needed:

```bash
python -m ipykernel install --user --name dt-spm-r1 --display-name "DT-SPM R1"
```

Select `DT-SPM R1` in your Jupyter installation. The pinned environment includes a kernel and notebook execution libraries; it does not include a Jupyter web application. [NOTEBOOKS.md](NOTEBOOKS.md) distinguishes the tested reproduction notebook from historical source notebooks.

The environment has one recorded package-metadata conflict: `aespm==1.1.4` declares `numpy<2.0`, whereas the revised analyses used `numpy==2.2.6`. The installer uses the complete pin list with `--no-deps`, checks the installed environment, and rejects any additional conflict. The supplied workflow was tested with this combination. See [environment/README.md](environment/README.md).

## Manual dataset download

If Google Drive blocks an automated request or imposes a download quota, download the ZIP through the dataset link above. Then run:

```bash
python download_dataset.py --archive "/path/to/DT-SPM_R1_data_2026-09-30.zip"
python verify_package.py
```

The local-archive route uses only the Python standard library. Downloading directly from Drive uses `gdown==6.1.0`, which is included in the pinned environment. Both routes check the same archive identity:

```text
File:   DT-SPM_R1_data_2026-09-30.zip
Bytes:  668283428
SHA256: 0c8f3788aee370c07b29fa8d337efd8eb6d76c7a7b622f4088e48bec794748e5
```

[dataset_config.json](dataset_config.json) records the URL and checksums. The dataset includes the measured archives, calibration records, processed libraries, reference results and verification reports. These files are excluded from Git by `.gitignore`. `DATA_README.md` and `MANIFEST_data.sha256` are included with the code so the dataset can be inspected and checked before download. The dataset ZIP retains its original draft deposition metadata; current access links are recorded in `dataset_config.json` and `metadata/hosting.json`.

## What each folder contains

| Path | Contents |
|---|---|
| `data/` | Measured AlScN scan grid, grating acquisition archive, raw IBW force–distance files and reference images |
| `output/` | Archived processed FD libraries, submitted-model arrays and fitted FD parameters used as inputs |
| `calibration_cache/` | Archived per-condition controller fits and submitted prediction records |
| `codes/` | Scanner, calibration, descriptor and plotting functions used by the notebooks and revision scripts |
| `revision_2026-09/codes/` | Revised benchmark, audit, CV, bundle and figure producers |
| `reference/revised/` | Original saved revised-analysis outputs and figures, kept as comparison targets |
| `reference/current_submission_figures/` | Exact images embedded in the current manuscript and supplementary document |
| `splits/` | Condition-level split assignments and FD-curve cross-validation assignments |
| `verification/` | Fresh-run status, environment, comparison reports and regenerated numerical outputs |
| `metadata/` | Source-file lineage, data-array inventory, figure links and draft archive metadata |

See `DATA_README.md` for variables, units, exclusions and data lineage. `REPRODUCTION_MAP.md` links manuscript items to their inputs and producers. `UPLOAD_INSTRUCTIONS.md` describes the GitHub upload; `DEPOSITION_CHECKLIST.md` tracks release identifiers and archive metadata.

## Reproduce selected stages

```bash
python run_reproduction.py --stage fd --run-dir runs/fd_check
python run_reproduction.py --stage bundles --verify-local 3 --run-dir runs/bundle_check
python run_reproduction.py --stage benchmark --run-dir runs/my_run
python run_reproduction.py --stage invariance --run-dir runs/my_run
```

The default full run executes FD preprocessing, bundle reconstruction with three local grating refits, the submitted-correction audit, the AlScN benchmark, mechanism analysis, learning curves, grating comparison, both descriptor CV analyses, the invariance check, split manifests, revised figures, supplementary tables and historical supplementary panels. Mechanism analysis requires the benchmark; figures and tables require their preceding analysis outputs. Individual stages do not automatically run their dependencies.

Figures 1 and 2 are author-edited schematics. Their editable presentation and exact submitted PNGs are included under `reference/revised/figures/`; they have no numerical model to rerun. Supplementary Figure 1 is a historical architecture schematic. Historical supplementary plots retain their archived terminology; the revised manuscript explains their scope.

## Interpretation and provenance

The revised benchmark excludes the target scan and fits scanner calibration outside each outer test partition. It is a retrospective evaluation under a declared calibration-availability assumption. The AlScN FD library was acquired after the scan grid, so the package does not establish an executed pre-acquisition experiment. Scanner calibration is fixed during inner regressor selection, and inner selection is conditional on that calibration. The supplied invariance test covers one blocked fold, height-line and Qalign perturbations, and four predictors: the scanner, GBM, hybrid GBM and hybrid ridge.

The submitted CNN–LSTM corrections use measured target-condition signals. They are retained for the audit and historical supplementary panels. Qsafety is a dimensionless interaction-load proxy; it is not a calibrated force or damage probability. The package preserves these variable names for code compatibility.

The main reproduction route starts from measured archives and supplied calibration records. It rebuilds the FD libraries and intermediate plot bundles, then refits the revised predictive models. The expensive historical calibration fits are included as explicit inputs. Their source notebooks and functions are supplied; three grating controller fits are checked during bundle regeneration. The package does not claim a fresh refit of all historical FD and controller parameters. FD calibration and exploratory notebooks are provenance sources; the documented driver defines the tested execution route.

The validation environment is recorded independently from the September revised-analysis record. Package installation dates do not establish the environment used for the original submission. Exact file hashes identify the supplied inputs and reference outputs; numerical comparisons use stated tolerances because trained models and linear algebra can vary across platforms. `VERIFICATION_REPORT.md` lists the small differences in the historical neural audit and grating bundle reconstruction; these are retained explicitly in the reports.
