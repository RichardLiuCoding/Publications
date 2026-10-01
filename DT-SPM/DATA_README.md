# Data accompanying the DT-SPM R1 analyses

The package contains two probe–sample systems: an AlScN film and a calibration grating. File and variable names such as `Tap300`, `Multi75`, `cali_fd`, and `Qsafety` are retained from the analysis code. These labels do not resolve the probe-identity questions flagged in the manuscript; the instrument and probe descriptions remain subject to author confirmation.

## Measured data and processed libraries

| File or group | Content and use |
|---|---|
| `data/260507-300kHz-AlScN.npz` | AlScN scan grid, acquired 7–8 May 2026; source of scan-quality and interaction-load targets |
| `data/Image0002.ibw` | Reference image and instrument header; AmpInvOLS supplies the drive conversion used by the loader |
| `data/260514/Tap300/AlScN_FD*.ibw` | 31 FD files from 14 May 2026; the preprocessing retains the first 30 sorted files as curve rows |
| `output/Tap300_AlScN.npz` | Processed AlScN FD library: approach/retract height, amplitude and phase arrays |
| `data/250315/pickles/250315_Cali1_MOBO.pickle` | 60 grating conditions in acquisition order, measured controls and scan lines |
| `data/250315/pickles/250315_Cali1_MOBO training.pickle` | Historical acquisition/training archive; its `factor` field supplies the recorded grating drive conversion |
| `data/250315/CaliSample01/Cali_FD*.ibw` | 15 grating FD files |
| `data/250315/CaliSample01/Cali_res1_0001.ibw` | Grating reference image; its AmpInvOLS header enters the FD drive conversion |
| `output/cali_fd.npz` | Processed grating FD library |
| `output/fd_calibration_*results.joblib` | Archived fitted FD model parameters loaded by the descriptor notebooks |
| `calibration_cache/` | Local PI fits and submitted prediction banks, with source hashes in `metadata/source_inventory.json` |

Raw instrument files are retained in IBW format. Numerical arrays use NPZ, summaries and manifests use CSV/JSON, and historical fitted objects use joblib/pickle/PyTorch formats. Load the supplied serialized Python objects only after verifying their hashes. They require the pinned scientific environment, including gpytorch/botorch for the acquisition archive.

## Array definitions

`metadata/array_inventory.json` lists every archived NPZ key, dtype and shape. The principal axes and units are:

| Array | Axes or definition | Unit |
|---|---|---|
| AlScN grid `data` | `(scan speed=5, drive=11, setpoint=8, integral gain=5, line=3, channel=8, pixel=256)` | Channel dependent |
| Grid height channels 0, 1 | Trace and retrace height; the revised loader selects line index 1 and gain indices 0–2 | metres in archive, converted to nm |
| Grid amplitude channels 2, 3 | Trace and retrace oscillation amplitude | metres in archive, converted to nm |
| Grid phase channels 4, 5 | Trace and retrace phase; wrapped to the specified convention when computing the load proxy | degrees |
| Grid channels 6, 7 | Additional recorded channels, unused by the revised loader | Not assigned by this package |
| `scan_rate` | Five nominal scan-rate settings; used as scan-speed controls | Hz in acquisition settings |
| `drives` | Eleven drive settings; converted using `(258.8/2.14) * AmpInvOLS * 1e9` | recorded instrument drive setting; converted to nm |
| `setpoints` | Amplitude setpoint fractions | dimensionless |
| `i_gain` | Instrument integral-gain settings | controller setting; no SI conversion asserted |
| Grating `traces` | `(condition=60, line=5, channel=8, pixel=256)`; final line and height channels 0, 1 used | metres for height |
| Grating `x_measured` | Three recorded controls: drive, amplitude setpoint, integral gain; analysis uses second column divided by first for the setpoint fraction | native control units; preserved as recorded |
| FD `height`, `height2` | Offset approach and retract distance coordinates | nm |
| FD `amp`, `amp2` | Approach and retract oscillation amplitudes | nm |
| FD `phase`, `phase2` | Approach and retract phase | degrees |
| FD `drive` | Drive converted with the recorded header and acquisition factor | nm |
| `Q_align` / `q_exp` | Centred trace–retrace RMS difference on the interior pixels | nm |
| `Q_safety` / `Qsafety` | Amplitude-suppression/repulsive-phase interaction-load proxy, defined in the manuscript | dimensionless |

The AlScN FD arrays have 30 curve rows and 1000 points per curve, while the archived `drive` vector has 31 entries. This is the original preprocessing convention: the last sorted FD file is excluded from the curve matrices but retained in the drive metadata. The revised loaders derive their operating drive values from the measured amplitudes. The package preserves this mismatch and documents it rather than silently dropping metadata. The grating library has 15 rows, 50 points per row and 15 drive entries.

NaN denotes an unavailable descriptor, excluded prediction, or uncomputed value according to the array. It does not denote zero. In the submitted bundle, data-driven predictions are populated only for held-out conditions. In revised cross-validation arrays, predictions are indexed by the analysis condition, with split-specific test masks where needed. The manifest condition ID is the row in the corresponding 900-condition AlScN or 60-condition grating bundle.

## Processing and splits

`rv_build_fd.py` reproduces the notebook FD slicing, unit conversion and array orientation, then compares each reconstructed array with its archived library. It writes a separate library under the selected run directory. The forward/reverse orientation and 31-to-30 AlScN selection are retained exactly.

The full AlScN grid contains more conditions than the scored benchmark. The revised scanner loader keeps three gains, giving a 1320-condition calibration universe. The submitted bundle identifies the 900 scored conditions. `rv_tap300.build_table()` checks that their measured height lines and Qalign values agree with the raw grid. Scanner calibration can use permitted conditions from the larger grid outside the outer test partition; regressors use the training portion of the 900 scored conditions.

The AlScN manifests record speed–drive block folds, unseen-speed folds, adjacent-setpoint-pair folds and the submitted random split. The grating manifest records the submitted split, five random CV folds and the last 20 acquisitions as the chronological test set. `splits/fd_*_split_manifest.csv` records descriptor-CV assignments and the original descriptor split. The revised five-fold descriptor assessment keeps the previously selected configuration; it does not constitute independent model selection.

The AlScN FD library postdates its scan grid. The grating archive preserves condition order; acquisition timestamps for the AlScN grid are insufficient for a comparable chronological split. Data and model interpretations must retain these chronology limits.

## Calibration lineage and excluded material

The AlScN local controller fits originate from `Fit DT controller parameters to experimental scans_v2.ipynb`, using `codes/dt_gp_static_calibration_v3.py`. The grating local fits originate from `codes/cali_v2_refit_with_multiobjective_loss.py`; this historical script refers to development `/tmp` files. The portable bundle producer reconstructs the manuscript-used grating arrays directly from the acquisition archive, FD library and supplied local fits, and can refit selected local conditions without those temporary files.

Development diagnostics named `loss_*`, `demo_*`, `example_*`, `three_examples_json` and `clean_*` in the grating bundle are retained in the archived input but are outside the portable producer's manuscript-used array comparison. The bundle report lists this exclusion explicitly. The AlScN bundle producer assembles cached calibration/prediction records; rebuilding that bundle does not refit all upstream calibration objects.

Unrelated PTO datasets, experimental branches, archive ZIP files, and the unused `260501-75kHz-grid2.npz` are excluded. The manuscript author contributions, conflict declaration, instrument model and probe identities require author confirmation. Code and data rights are recorded as pending in `RIGHTS_AND_RELEASE_STATUS.txt`.
